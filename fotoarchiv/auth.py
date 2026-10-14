"""Přihlášení lokálními účty.

`<work>/uzivatele.json` píše ručně správce, aplikace ho jen čte:
login → {jmeno, email?, role?}. `<work>/hesla.json` píše jen aplikace:
login → {hash, zmenit}. Oddělené, aby zápis aplikace nekolidoval
s ruční editací a hash nebyl v souboru, který se kopíruje a upravuje.

Relace nese otisk hashe; nové heslo (změna nebo jednorázové od
správce) tak zneplatní ostatní relace uživatele.
"""

import hashlib
import json
import logging
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

MIN_LENGTH = 10
FREE_ATTEMPTS = 5  # chybné pokusy na login bez zdržení
MAX_DELAY = 300

# Role v `uzivatele.json`; bez role běžný uživatel.
ROLES = ("admin", "archivar")

log = logging.getLogger(__name__)

# Ověření neexistujícího loginu trvá stejně dlouho jako existujícího.
_DUMMY_HASH = generate_password_hash("neexistujici-login")


def write_private(path, data):
    """Atomický zápis JSONu s právy jen pro vlastníka."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}-",
                               suffix=".tmp")
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def secret_key(work):
    """Tajný klíč relací; vytvoří se při prvním spuštění (přežije
    restart, relace zůstanou platné)."""
    path = Path(work) / "relace.key"
    try:
        return path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        pass
    key = secrets.token_hex(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(key)
    return key


def one_time_password():
    return secrets.token_urlsafe(9)  # 12 znaků


def rights(role):
    """Odvozená oprávnění role: admin ⊃ archivář (správa archivu),
    Nastavení jen admin."""
    return {"admin": role == "admin", "archivar": role in ROLES}


def _problem(user):
    """Důvod, proč je záznam chybný, nebo None."""
    if "admin" in user:
        return 'klíč "admin" (dřívější zápis role)'
    role = user.get("role")
    if role is not None and role not in ROLES:
        return f"neznámá role {json.dumps(role, ensure_ascii=False)}"
    return None


def _parse(data):
    """({login: záznam}, [(login, důvod)]); chybné záznamy nejsou mezi
    platnými."""
    users, problems = {}, []
    if not isinstance(data, dict):
        return users, problems
    for login, user in data.items():
        if not isinstance(user, dict) or not user.get("jmeno"):
            continue
        login = str(login).strip().lower()
        reason = _problem(user)
        if reason:
            problems.append((login, reason))
        else:
            users[login] = user
    return users, problems


class Users:
    """`uzivatele.json`, čte se znovu při změně mtime."""

    def __init__(self, work):
        self.path = Path(work) / "uzivatele.json"
        self._mtime = None
        self._users = {}
        self._mutex = threading.Lock()

    def _read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}  # rozepsaný soubor: nikdo, než ho správce opraví

    def _current(self):
        with self._mutex:
            try:
                mtime = self.path.stat().st_mtime_ns
            except FileNotFoundError:
                self._mtime, self._users = None, {}
                return self._users
            if mtime != self._mtime:
                self._users, problems = _parse(self._read())
                for login, reason in problems:
                    # Za běhu nepadat: chybný login nemá přístup, ostatní
                    # pracují dál.
                    log.warning("%s: login %s nemá přístup: %s",
                                self.path, login, reason)
                self._mtime = mtime
            return self._users

    def problems(self):
        """[(login, důvod)] chybných záznamů (dřívější `admin`, neznámá
        `role`); kontrola při startu, nic nezapisuje do logu."""
        return _parse(self._read())[1]

    def get(self, login):
        """{jmeno, email, role}, nebo None; role None = běžný uživatel."""
        user = self._current().get(login)
        if user is None:
            return None
        return {"jmeno": user["jmeno"], "email": user.get("email"),
                "role": user.get("role")}


def problems_message(users):
    """Text chyby pro CLI, nebo None, když je `uzivatele.json` v pořádku."""
    problems = users.problems()
    if not problems:
        return None
    lines = [f"Chybné záznamy v {users.path}:"]
    lines += [f"  {login}: {reason}" for login, reason in problems]
    lines.append('Roli zapište jako "role": "admin" nebo "role": "archivar" '
                 '(místo "admin": true → "role": "admin"); bez role je '
                 "uživatel běžný.")
    return "\n".join(lines)


class Passwords:
    """`hesla.json` = login → {hash, zmenit}."""

    def __init__(self, work):
        self.path = Path(work) / "hesla.json"
        self._mutex = threading.Lock()

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def set(self, login, heslo, zmenit=False):
        with self._mutex:
            data = self._load()
            data[login] = {"hash": generate_password_hash(heslo),
                           "zmenit": zmenit}
            write_private(self.path, data)

    def check(self, login, heslo):
        record = self._load().get(login)
        ok = check_password_hash(record["hash"] if record else _DUMMY_HASH,
                                 heslo)
        return ok and record is not None

    def must_change(self, login):
        record = self._load().get(login)
        return bool(record and record.get("zmenit"))

    def fingerprint(self, login):
        """Otisk hashe pro relace; None bez hesla."""
        record = self._load().get(login)
        if record is None:
            return None
        return hashlib.sha256(record["hash"].encode()).hexdigest()[:16]


class Throttle:
    """Zdržování po opakovaných chybných pokusech na jeden login (v paměti,
    server běží jako jeden proces)."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._failures = {}  # login → (počet, zdržet do)
        self._mutex = threading.Lock()

    def wait(self, login):
        """Sekundy do dalšího povoleného pokusu (0 = hned)."""
        with self._mutex:
            _, until = self._failures.get(login, (0, 0))
            return max(0, until - self.clock())

    def failed(self, login):
        with self._mutex:
            count, _ = self._failures.get(login, (0, 0))
            count += 1
            delay = 0
            if count >= FREE_ATTEMPTS:
                delay = min(2 ** (count - FREE_ATTEMPTS), MAX_DELAY)
            self._failures[login] = (count, self.clock() + delay)

    def succeeded(self, login):
        with self._mutex:
            self._failures.pop(login, None)


class Auth:
    def __init__(self, work, clock=time.monotonic):
        self.users = Users(work)
        self.passwords = Passwords(work)
        self.throttle = Throttle(clock)

    def login(self, login, heslo):
        """(uživatel, None), nebo (None, "neplatne" | sekundy čekání).

        Neexistující login a špatné heslo dávají stejný výsledek.
        """
        login = str(login or "").strip().lower()
        wait = self.throttle.wait(login)
        if wait > 0:
            return None, wait
        ok = self.passwords.check(login, str(heslo or ""))
        user = self.users.get(login)
        if not ok or user is None:
            self.throttle.failed(login)
            return None, "neplatne"
        self.throttle.succeeded(login)
        return dict(user, login=login), None

    def change(self, login, stavajici, nove):
        """Změní heslo; vrátí kód chyby, nebo None."""
        if not self.passwords.check(login, str(stavajici or "")):
            return "spatne_heslo"
        nove = str(nove or "")
        if len(nove) < MIN_LENGTH:
            return "kratke_heslo"
        if nove == stavajici:
            return "stejne_heslo"
        self.passwords.set(login, nove)
        return None

    def issue(self, login):
        """Jednorázové heslo pro login z `uzivatele.json`, nebo None."""
        login = login.strip().lower()
        if self.users.get(login) is None:
            return None
        heslo = one_time_password()
        self.passwords.set(login, heslo, zmenit=True)
        return heslo
