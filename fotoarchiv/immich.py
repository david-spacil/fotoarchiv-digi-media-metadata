"""Pojmenované obličeje z Immiche do `_metadata.json` (pole `obliceje`).

Immich osoby rozpoznává a pojmenovává autoritativně; synchronizace je
čte a zapisuje do souborů akcí, které už mají `_metadata.json`. Klient
umí i zápis (alba akcí, knihovny, fronty, pojmenování osob) pro nástroj
pojmenování. Nastavení (adresa, klíč, knihovna) je v pracovním adresáři
(`immich.json`, práva 0600), nikdy v archivu ani v prohlížeči.
"""

import json
import logging
import os
import tempfile
import threading
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import model, names, xmp

TIMEOUT = 30
PAGE = 1000
WORKERS = 4
INTERVAL = 15 * 60
RELACE = "immich-sync"
JMENO = "Immich (synchronizace)"
# Hlídač po dokončení akce (albums.Hlidac): dotaz na assety po
# `HLIDAC_INTERVAL` s, celkový limit `HLIDAC_LIMIT` s. V testech
# zkrátitelné parametry hlídače.
HLIDAC_INTERVAL = 20
HLIDAC_LIMIT = 60 * 60
# Fronty, které musí stát, než lze ohlásit „obličeje rozpoznány“.
FRONTY_ML = ("faceDetection", "facialRecognition")

# Oprávnění klíče pro alba akcí (i smazání alba akce vysypané z koše),
# sken knihovny, stav rozpoznávání a nástroj pojmenování (klíč s `all`
# má vše).
OPRAVNENI = ("person.read", "asset.read", "face.read", "asset.view",
             "person.update", "person.merge", "album.read", "album.create",
             "album.delete", "albumAsset.create", "albumAsset.delete", "library.read",
             "library.update", "queue.read")

log = logging.getLogger(__name__)


class ImmichError(Exception):
    """Immich neodpověděl nebo vrátil chybu (`status` = HTTP kód, 403…)."""

    def __init__(self, text, status=None):
        super().__init__(text)
        self.status = status


# --- nastavení -------------------------------------------------------------

class Settings:
    """`<work>/immich.json` = {adresa, klic, knihovna?}."""

    def __init__(self, work):
        self.path = Path(work) / "immich.json"

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not data.get("adresa") or not data.get("klic"):
            return None
        return {"adresa": data["adresa"].rstrip("/"), "klic": data["klic"],
                "knihovna": data.get("knihovna") or None}

    def save(self, adresa, klic, knihovna=None):
        """Zapíše nastavení; bez `knihovny` se id do souboru nezapíše."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".immich-",
                                   suffix=".tmp")
        data = {"adresa": adresa, "klic": klic}
        if knihovna:
            data["knihovna"] = knihovna
        try:
            os.chmod(tmp, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def delete(self):
        self.path.unlink(missing_ok=True)


def key_hint(klic):
    return f"…{klic[-4:]}"


# --- klient ----------------------------------------------------------------

def fetch_json(method, url, klic, body=None):
    """JSON odpověď; prázdné tělo (204) snese a vrátí None."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "x-api-key": klic, "Accept": "application/json",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise ImmichError(f"HTTP {e.code} {url}", status=e.code) from e
    except OSError as e:
        raise ImmichError(f"{e} ({url})") from e
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError as e:
        raise ImmichError(f"{e} ({url})") from e


def fetch_binary(method, url, klic):
    """Binární odpověď jako (bytes, content_type) (zmenšeniny)."""
    req = urllib.request.Request(url, method=method,
                                 headers={"x-api-key": klic})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read(), resp.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        raise ImmichError(f"HTTP {e.code} {url}", status=e.code) from e
    except OSError as e:
        raise ImmichError(f"{e} ({url})") from e


class Client:
    def __init__(self, adresa, klic, fetch=None, fetch_bytes=None):
        self.adresa = adresa.rstrip("/")
        self.klic = klic
        self.fetch = fetch or fetch_json
        self.fetch_bytes = fetch_bytes or fetch_binary

    def _call(self, method, path, body=None):
        return self.fetch(method, self.adresa + path, self.klic, body)

    def _call_bytes(self, method, path):
        return self.fetch_bytes(method, self.adresa + path, self.klic)

    def version(self):
        v = self._call("GET", "/api/server/version")
        text = f"{v['major']}.{v['minor']}.{v['patch']}"
        if v.get("prerelease"):
            text += f"-rc{v['prerelease']}"
        return text

    def people(self, size=PAGE, page=1, all_pages=True):
        """(osoby, celkem) včetně skrytých."""
        result, total = [], None
        while True:
            query = urllib.parse.urlencode(
                {"page": page, "size": size, "withHidden": "true"})
            r = self._call("GET", f"/api/people?{query}")
            result += r.get("people") or []
            total = r.get("total", total)
            if not all_pages or not r.get("hasNextPage"):
                return result, total
            page += 1

    def person(self, person_id):
        """Jedna osoba (`GET /api/people/{id}`): `name`, `isHidden`.

        Čte se před vrácením kroku v nástroji pojmenování (kontrola,
        že osoba má pořád stav po kroku).
        """
        return self._call("GET", f"/api/people/{person_id}")

    def assets(self, person_id=None, size=PAGE, all_pages=True):
        """Assety osoby (nebo libovolné bez `person_id`)."""
        result, page = [], 1
        while page:
            body = {"page": page, "size": size}
            if person_id:
                body["personIds"] = [person_id]
            r = self._call("POST", "/api/search/metadata", body)["assets"]
            result += r.get("items") or []
            if not all_pages:
                break
            page = int(r["nextPage"]) if r.get("nextPage") else None
        return result

    def faces(self, asset_id):
        query = urllib.parse.urlencode({"id": asset_id})
        return self._call("GET", f"/api/faces?{query}")

    # --- zápis a správa (alba, knihovny, fronty, osoby) --------------------

    def api_key_permissions(self):
        """Seznam oprávnění klíče (`all` = vše)."""
        r = self._call("GET", "/api/api-keys/me")
        return (r or {}).get("permissions") or []

    def update_people(self, people):
        """Hromadný zápis osob; položky {id, name?, isHidden?}."""
        return self._call("PUT", "/api/people", {"people": list(people)})

    def merge_people(self, target_id, ids):
        """Sloučení osob do `target_id`; v těle je cíl jako první id."""
        others = [i for i in ids if i != target_id]
        return self._call("POST", "/api/people/merge",
                          {"ids": [target_id, *others]})

    def albums(self):
        return self._call("GET", "/api/albums")

    def album(self, album_id):
        return self._call("GET", f"/api/albums/{album_id}")

    def create_album(self, name, asset_ids):
        return self._call("POST", "/api/albums",
                          {"albumName": name, "assetIds": list(asset_ids)})

    def delete_album(self, album_id):
        """Smaže album (assety zůstanou); jen pro vysypání koše."""
        return self._call("DELETE", f"/api/albums/{album_id}")

    def add_album_assets(self, album_id, asset_ids):
        return self._call("PUT", f"/api/albums/{album_id}/assets",
                          {"ids": list(asset_ids)})

    def remove_album_assets(self, album_id, asset_ids):
        return self._call("DELETE", f"/api/albums/{album_id}/assets",
                          {"ids": list(asset_ids)})

    def _search_paged(self, body, size=PAGE, all_pages=True):
        """Stránkované `POST /api/search/metadata` (další `nextPage`)."""
        result, page = [], 1
        while page:
            r = self._call("POST", "/api/search/metadata",
                           {**body, "page": page, "size": size})["assets"]
            result += r.get("items") or []
            if not all_pages:
                break
            page = int(r["nextPage"]) if r.get("nextPage") else None
        return result

    def search_album(self, album_id, size=PAGE, all_pages=True):
        """Assety alba s osobami i EXIF (jeden stránkovaný dotaz)."""
        return self._search_paged({"albumIds": [album_id],
                                   "withPeople": True, "withExif": True},
                                  size=size, all_pages=all_pages)

    def album_asset_ids(self, album_id):
        """Id assetů alba (`AlbumResponseDto` je v Immichi 3 neobsahuje,
        proto přes vyhledávání s `albumIds`)."""
        return [a["id"] for a in self._search_paged({"albumIds": [album_id]})]

    def search_path(self, original_path, size=PAGE, all_pages=True):
        """Assety, jejichž cesta v Immichi obsahuje `original_path`
        (filtr je podřetězec — výsledek se dofiltruje přes `file_key`)."""
        return self._search_paged({"originalPath": original_path},
                                  size=size, all_pages=all_pages)

    def thumbnail(self, asset_id):
        """Zmenšenina `preview` jako (bytes, content_type)."""
        query = urllib.parse.urlencode({"size": "preview"})
        return self._call_bytes(
            "GET", f"/api/assets/{asset_id}/thumbnail?{query}")

    def person_thumbnail(self, person_id):
        """Náhled osoby (cíl nabídky sloučení) jako (bytes,
        content_type)."""
        return self._call_bytes("GET", f"/api/people/{person_id}/thumbnail")

    def libraries(self):
        """Knihovny Immiche (jen admin; jinak 403)."""
        return self._call("GET", "/api/libraries")

    def scan_library(self, library_id):
        """Spustí asynchronní sken knihovny; odpověď může být prázdná."""
        return self._call("POST", f"/api/libraries/{library_id}/scan")

    def queue(self, name):
        """Statistiky fronty úloh (`statistics.active`, `waiting`, …)."""
        return self._call("GET", f"/api/queues/{name}")


def test_connection(client, knihovna=None):
    """Verze, čtení osob a obličejů, oprávnění klíče a role admina.

    Vrací {"verze", "osob", "varovani": [texty], "chybi": [oprávnění]};
    selhání čtení → ImmichError s krokem v textu. Chybějící oprávnění,
    klíč uživatele bez role admin a nevybraná knihovna jsou varování:
    test připojení i tak projde.
    """
    def step(label, fn):
        try:
            return fn()
        except ImmichError as e:
            raise ImmichError(f"{label}: {e}") from e
    verze = step("verze", client.version)
    people, total = step("osoby", lambda: client.people(
        size=1, all_pages=False))
    found = step("assety", lambda: client.assets(
        people[0]["id"] if people else None, size=1, all_pages=False))
    if found:
        step("obličeje", lambda: client.faces(found[0]["id"]))
    varovani, chybi = [], []
    permissions = step("oprávnění", client.api_key_permissions)
    if "all" not in permissions:
        chybi = [p for p in OPRAVNENI if p not in permissions]
    if chybi:
        varovani.append("Čtení osob a obličejů funguje, ale klíči chybí "
                        "oprávnění: " + ", ".join(chybi) + ". Alba akcí, "
                        "sken knihovny, stav rozpoznávání nebo pojmenování "
                        "osob proto nemusí být dostupné.")
    try:
        client.libraries()
    except ImmichError as e:
        if e.status == 403:
            varovani.append("Klíč patří uživateli Immiche bez role "
                            "admin: sken knihovny a stav rozpoznávání "
                            "nebudou dostupné, ostatní funkce fungují.")
        else:
            raise ImmichError(f"knihovny: {e}") from e
    if not knihovna:
        varovani.append("V nastavení není vybraná knihovna Immiche: "
                        "dokončení akce nespustí sken. Vyberte ji na "
                        "stránce nastavení.")
    return {"verze": verze, "osob": total, "varovani": varovani,
            "chybi": chybi}


# --- převod ----------------------------------------------------------------

def area(face):
    """Oblast MWG `[x, y, w, h]` (střed a velikost, podíly 0–1).

    Immich vztahuje obdélník ke zmenšenině už otočené fotky
    (`imageWidth/Height`), takže podíly platí pro fotku zobrazenou se
    správnou orientací v libovolném rozlišení.
    """
    w, h = face["imageWidth"], face["imageHeight"]
    x1, y1 = face["boundingBoxX1"], face["boundingBoxY1"]
    x2, y2 = face["boundingBoxX2"], face["boundingBoxY2"]
    return [round((x1 + x2) / 2 / w, 4), round((y1 + y2) / 2 / h, 4),
            round((x2 - x1) / w, 4), round((y2 - y1) / h, 4)]


def _nfc(text):
    return unicodedata.normalize("NFC", text)


def file_key(original_path):
    """(složka akce, soubor) z posledních dvou částí cesty v Immichi."""
    parts = PurePosixPath(original_path).parts
    if len(parts) < 2:
        return None
    return _nfc(parts[-2]), _nfc(parts[-1])


def collect(client, workers=WORKERS):
    """{(akce, soubor): [{jmeno, oblast}]} pojmenovaných obličejů.

    Jakákoli chyba dotazu propadne jako ImmichError: neúplná mapa by
    obličeje mazala.
    """
    people, _ = client.people()
    named = [p for p in people if (p.get("name") or "").strip()]
    paths = {}
    for person in named:
        for asset in client.assets(person["id"]):
            paths[asset["id"]] = asset["originalPath"]
    ids = sorted(paths)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        all_faces = list(pool.map(client.faces, ids))
    result = {}
    for asset_id, faces in zip(ids, all_faces):
        key = file_key(paths[asset_id])
        if key is None:
            continue
        for face in faces:
            jmeno = ((face.get("person") or {}).get("name") or "").strip()
            if jmeno:
                result.setdefault(key, []).append(
                    {"jmeno": jmeno, "oblast": area(face)})
    return result


def faces_for(found, akce, record_names, known):
    """{název záznamu: obličeje} akce; jména v tvaru ze seznamu jmen."""
    result = {}
    for name in record_names:
        faces = found.get((_nfc(akce), _nfc(name)))
        if faces:
            faces = [{"jmeno": names.known_form(f["jmeno"], known),
                      "oblast": f["oblast"]} for f in faces]
            result[name] = sorted(faces, key=lambda f: (f["jmeno"],
                                                        f["oblast"][0]))
    return result


def apply(doc, faces):
    """Zapíše obličeje do dokumentu; vrátí True, když se něco změnilo."""
    changed = False
    for name, record in (doc.get("soubory") or {}).items():
        new = faces.get(name)
        if (record.get("obliceje") or None) == new:
            continue
        changed = True
        if new:
            record["obliceje"] = new
        else:
            record.pop("obliceje", None)
    return changed


# --- synchronizace ---------------------------------------------------------

def _now():
    return datetime.now().isoformat(timespec="seconds")


class Sync:
    """Synchronizace v serveru: jeden běh najednou, stav posledního běhu."""

    def __init__(self, ws, locks, settings, known_names, fetch=None,
                 fetch_bytes=None, interval=INTERVAL):
        from . import albums     # albums importuje immich (cyklus jen
                                 # v modulech, ne při importu)
        self.ws = ws
        self.locks = locks
        self.settings = settings
        self.known_names = known_names
        self.fetch = fetch
        self.fetch_bytes = fetch_bytes
        self.interval = interval
        self.alba = albums.Stavy(ws.work)
        self.osoby = albums.Osoby(ws.work)
        self._running = threading.Lock()
        self._thread = None
        self._start_lock = threading.Lock()
        self.last = None
        self.last_ok = None

    def status(self):
        return {"bezi": self._running.locked(), "posledni": self.last,
                "posledni_uspesny": self.last_ok}

    def client(self):
        s = self.settings.load()
        if not s:
            return None
        return Client(s["adresa"], s["klic"], self.fetch, self.fetch_bytes)

    def run(self):
        """Jeden běh; když už běží jiný, jen vrátí stav."""
        if not self._running.acquire(blocking=False):
            return self.status()
        try:
            client = self.client()
            if client is None:
                return self.status()
            started = _now()
            try:
                found = collect(client)
            except ImmichError as e:
                log.warning("immich: synchronizace selhala: %s", e)
                self.last = {"cas": started, "ok": False, "chyba": str(e),
                             "zmenene": [], "preskocene": []}
                return self.status()
            changed, skipped = self.write(found)
            try:
                self.udrzet_alba(client)
            except Exception:  # noqa: BLE001 — alba nesmí shodit obličeje
                log.exception("immich: údržba alb selhala")
            self.last = self.last_ok = {
                "cas": started, "ok": True, "chyba": None,
                "zmenene": changed, "preskocene": skipped}
            if changed or skipped:
                log.info("immich: změněno %s, přeskočeno %s", changed,
                         skipped)
        finally:
            self._running.release()
        return self.status()

    def write(self, found):
        """Zapíše obličeje do akcí; vrátí (změněné, přeskočené)."""
        known = self.known_names()
        changed, skipped = [], []
        for akce in self.ws.event_names():
            try:
                doc, _ = self.ws.load(akce)
            except KeyError:  # kolize přípony `.ignored`
                continue
            if doc is None:
                continue
            records = list((doc.get("soubory") or {}))
            if not apply(doc, faces_for(found, akce, records, known)):
                continue
            ok, _ = self.locks.acquire(akce, RELACE, JMENO)
            if not ok:
                skipped.append(akce)
                continue
            try:
                # Pod zámkem znovu z aktuální verze.
                doc, version = self.ws.load(akce)
                records = list((doc.get("soubory") or {}))
                apply(doc, faces_for(found, akce, records, known))
                model.clean(doc)
                exported = self.ws.export_version(akce) == version
                new_version = self.ws.save(akce, doc, version)
                if exported:
                    # Obličeje běžné sidecary nemění.
                    record = {"version": new_version, "zapis": self.ws.zapis}
                    xmp.write_atomic(self.ws.export_record_path(akce),
                                     json.dumps(record).encode("utf-8"))
                changed.append(akce)
            except Exception as e:  # noqa: BLE001 — jiná akce může projít
                log.warning("immich: zápis %s selhal: %s", akce, e)
                skipped.append(akce)
            finally:
                self.locks.release(akce, RELACE)
        return changed, skipped

    def udrzet_alba(self, client):
        """Údržba alb všech dokončených akcí (bez skenu) + počty osob.

        Společná cesta s hlídačem po dokončení (`albums.Hlidac`);
        chyba u jedné akce nezastaví ostatní ani zápis obličejů.
        """
        from . import albums
        for akce in self.ws.event_names():
            try:
                doc, _ = self.ws.load(akce)
            except KeyError:  # kolize přípony `.ignored`
                continue
            if doc is None or not doc.get("dokonceno"):
                continue
            try:
                album_id = albums.udrzet_album(client, self.ws, self.alba,
                                               akce)
            except Exception:  # noqa: BLE001 — jiná akce může projít
                log.warning("immich: údržba alba %s selhala", akce,
                            exc_info=True)
                continue
            if album_id:
                self.zapsat_osoby(client, akce, album_id)

    def zapsat_osoby(self, client, akce, album_id):
        """Uloží počty osob akce z alba; chyba dotazu nic nepíše.

        Předchozí stav v `.work/immich-osoby.json` tak zůstává zachován
        (specifikace: selže-li zjištění osob, SHALL zůstat předchozí
        stav). Akce bez alba se nezapisuje.
        """
        from . import albums     # cyklus jen v modulech, ne při importu
        try:
            pocty = albums.pocty_osob(client.search_album(album_id))
        except ImmichError as e:
            log.warning("immich: zjištění osob %s selhalo: %s", akce, e)
            return
        self.osoby.nastav(akce, pocty["pojmenovane"], pocty["celkem"])

    def trigger(self):
        """Běh na pozadí na požádání; vrátí stav."""
        if not self._running.locked():
            threading.Thread(target=self.run, daemon=True).start()
        status = self.status()
        status["bezi"] = True
        return status

    def start(self):
        """Pravidelné běhy (hned a pak po `interval`), nejvýš jedno vlákno."""
        with self._start_lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self._loop, daemon=True,
                                            name="immich-sync")
            self._thread.start()

    def _loop(self):
        stop = threading.Event()
        while True:
            try:
                self.run()
            except Exception:  # noqa: BLE001 — vlákno nesmí umřít
                log.exception("immich: neočekávaná chyba synchronizace")
            stop.wait(self.interval)
