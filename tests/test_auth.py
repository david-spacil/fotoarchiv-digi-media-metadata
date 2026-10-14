import json
import os

from fotoarchiv import auth


def users(work, data):
    work.mkdir(exist_ok=True)
    path = work / "uzivatele.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


SPACIL = {"spacil": {"jmeno": "Spáčil, David", "role": "admin"}}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_hash_not_password_in_file(tmp_path):
    users(tmp_path, SPACIL)
    a = auth.Auth(tmp_path)
    a.passwords.set("spacil", "tajne-heslo-1")
    path = tmp_path / "hesla.json"
    assert "tajne-heslo-1" not in path.read_text(encoding="utf-8")
    assert os.stat(path).st_mode & 0o777 == 0o600
    user, err = a.login("Spacil ", "tajne-heslo-1")
    assert err is None
    assert user == {"login": "spacil", "jmeno": "Spáčil, David",
                    "email": None, "role": "admin"}


def test_removed_user_loses_access(tmp_path):
    path = users(tmp_path, SPACIL)
    a = auth.Auth(tmp_path)
    a.passwords.set("spacil", "tajne-heslo-1")
    assert a.users.get("spacil")
    path.write_text("{}", encoding="utf-8")
    os.utime(path, ns=(1, 1))  # jiný mtime i při rychlém přepisu
    assert a.users.get("spacil") is None
    assert a.login("spacil", "tajne-heslo-1") == (None, "neplatne")


def test_roles(tmp_path):
    users(tmp_path, {"a": {"jmeno": "A, A", "role": "admin"},
                     "b": {"jmeno": "B, B", "role": "archivar"},
                     "c": {"jmeno": "C, C"}})
    u = auth.Users(tmp_path)
    assert [u.get(x)["role"] for x in "abc"] == ["admin", "archivar", None]
    assert u.problems() == []
    assert auth.rights("admin") == {"admin": True, "archivar": True}
    assert auth.rights("archivar") == {"admin": False, "archivar": True}
    assert auth.rights(None) == {"admin": False, "archivar": False}


def test_old_admin_key_and_unknown_role_refused(tmp_path):
    users(tmp_path, {"spacil": {"jmeno": "Spáčil, David", "admin": True},
                     "kopacova": {"jmeno": "Kopáčová, Jana",
                                  "role": "spravce"},
                     "novak": {"jmeno": "Novák, Petr"}})
    u = auth.Users(tmp_path)
    assert u.problems() == [
        ("spacil", 'klíč "admin" (dřívější zápis role)'),
        ("kopacova", 'neznámá role "spravce"')]
    assert u.get("spacil") is None and u.get("kopacova") is None
    assert u.get("novak")["role"] is None
    text = auth.problems_message(u)
    assert "spacil" in text and '"role": "admin"' in text


def test_bad_record_at_runtime(tmp_path, caplog):
    path = users(tmp_path, dict(SPACIL, novak={"jmeno": "Novák, Petr"}))
    a = auth.Auth(tmp_path)
    a.passwords.set("novak", "tajne-heslo-1")
    a.passwords.set("spacil", "tajne-heslo-1")
    assert a.users.get("novak")
    path.write_text(json.dumps(dict(
        SPACIL, novak={"jmeno": "Novák, Petr", "role": "spravce"})),
        encoding="utf-8")
    os.utime(path, ns=(1, 1))
    with caplog.at_level("WARNING"):
        assert a.login("novak", "tajne-heslo-1") == (None, "neplatne")
    assert "novak" in caplog.text
    assert a.login("spacil", "tajne-heslo-1")[1] is None


def test_change_password_changes_fingerprint(tmp_path):
    users(tmp_path, SPACIL)
    a = auth.Auth(tmp_path)
    a.passwords.set("spacil", "tajne-heslo-1")
    before = a.passwords.fingerprint("spacil")
    assert a.change("spacil", "spatne", "nove-heslo-22") == "spatne_heslo"
    assert a.change("spacil", "tajne-heslo-1", "kratke") == "kratke_heslo"
    assert a.change("spacil", "tajne-heslo-1",
                    "tajne-heslo-1") == "stejne_heslo"
    assert a.passwords.fingerprint("spacil") == before
    assert a.change("spacil", "tajne-heslo-1", "nove-heslo-22") is None
    assert a.passwords.fingerprint("spacil") != before
    assert a.login("spacil", "tajne-heslo-1")[1] == "neplatne"
    assert a.login("spacil", "nove-heslo-22")[1] is None


def test_one_time_password_must_change(tmp_path):
    users(tmp_path, SPACIL)
    a = auth.Auth(tmp_path)
    assert a.issue("nikdo") is None
    heslo = a.issue("spacil")
    assert a.passwords.must_change("spacil")
    assert a.login("spacil", heslo)[1] is None
    assert a.change("spacil", heslo, "vlastni-heslo") is None
    assert not a.passwords.must_change("spacil")


def test_unknown_login_same_error(tmp_path):
    users(tmp_path, SPACIL)
    a = auth.Auth(tmp_path)
    a.passwords.set("spacil", "tajne-heslo-1")
    assert a.login("nikdo", "x") == a.login("spacil", "x") == \
        (None, "neplatne")


def test_throttle_after_failures(tmp_path):
    users(tmp_path, SPACIL)
    clock = Clock()
    a = auth.Auth(tmp_path, clock=clock)
    a.passwords.set("spacil", "tajne-heslo-1")
    for _ in range(auth.FREE_ATTEMPTS - 1):
        assert a.login("spacil", "x") == (None, "neplatne")
    assert a.login("spacil", "x") == (None, "neplatne")
    # Po pátém chybném pokusu se čeká, i se správným heslem.
    assert a.login("spacil", "tajne-heslo-1") == (None, 1)
    clock.t += 1
    assert a.login("spacil", "x") == (None, "neplatne")
    assert a.login("spacil", "x") == (None, 2)
    # Neexistující login se zdržuje stejně.
    for _ in range(auth.FREE_ATTEMPTS):
        a.login("nikdo", "x")
    assert a.login("nikdo", "x") == (None, 1)
    clock.t += 2
    assert a.login("spacil", "tajne-heslo-1")[1] is None
    assert a.throttle.wait("spacil") == 0


def test_secret_key_persists(tmp_path):
    key = auth.secret_key(tmp_path)
    assert auth.secret_key(tmp_path) == key and len(key) == 64
    assert os.stat(tmp_path / "relace.key").st_mode & 0o777 == 0o600
