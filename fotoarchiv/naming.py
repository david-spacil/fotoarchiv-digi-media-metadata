"""Nástroj pojmenování osob v Immichi: osoby k pojmenování, výřezy,
odložené osoby.

`osoby_k_pojmenovani` sestaví ze stránky alba (`search_album`
s `people`) nepojmenované a neskryté osoby s obličejem na fotce akce,
bez osob odložených v aktuálním kole, seřazené podle počtu obličejů
sestupně. Ke každé nabídne až 3 výřezy z různých assetů s největším
obličejem (deterministicky podle plochy obdélníku a id) a metadata
zdrojové fotky z Immiche a z `_metadata.json` po zdědění
(`model.resolve`) přes `file_key`. `Odlozene` drží odložené osoby
uživatele v akci v `<work>/pojmenovani.json`. Bez Flasku; na Immich
mluví jen přes předaného klienta, do archivu nikdy nezapíše.
"""

import json
import threading
from pathlib import Path

from . import model
from .albums import _zapsat
from .immich import file_key

VYREZU = 3    # nejvýš 3 výřezy na osobu, vždy z jiného assetu


def _jmeno(person):
    return (person.get("name") or "").strip()


def assety_alba(assets):
    """Id assetů alba (kontrola, že náhled patří do akce)."""
    return {a["id"] for a in assets}


def nepojmene_ids(assets):
    """Id nepojmenovaných a neskrytých osob s obličejem v albu.

    `assets` je odpověď `search_album` (`people`): slouží k vyřazení
    odložených, která mezitím dostala jméno nebo byla skryta.
    """
    ids = set()
    for asset in assets:
        for person in asset.get("people") or []:
            if person.get("id") and not _jmeno(person) \
                    and not person.get("isHidden"):
                ids.add(person["id"])
    return ids


def _obliceje(faces, person_id):
    """Obličeje osoby v odpovědi `GET /api/faces` pro asset."""
    return [f for f in faces
            if (f.get("person") or {}).get("id") == person_id]


def _plocha(face):
    """Plocha obdélníku obličeje na zmenšenině (px)."""
    return ((face["boundingBoxX2"] - face["boundingBoxX1"])
            * (face["boundingBoxY2"] - face["boundingBoxY1"]))


def _immich_metadata(asset):
    """Název souboru a datum pořízení z Immiche; bez EXIF data
    `fileCreatedAt` (pole assetu, ne `exifInfo`)."""
    exif = asset.get("exifInfo") or {}
    return {"soubor": asset.get("originalFileName"),
            "datum": exif.get("dateTimeOriginal")
            or asset.get("fileCreatedAt")}


def _skupina(doc, record):
    """Název skupiny souboru (id jako poslední záchrana)."""
    gid = (record or {}).get("skupina")
    if not gid:
        return None
    group = (doc.get("skupiny") or {}).get(gid) or {}
    return group.get("nazev") or gid


def _archiv_metadata(doc, key):
    """Metadata z `_metadata.json` po zdědění pro spárovaný soubor.

    `key` je `file_key` (složka akce, soubor); bez záznamu
    v `doc[\"soubory\"]` vrátí None — nespárovaná fotka má jen údaje
    z Immiche.
    """
    if not key or not doc:
        return None
    soubor = key[1]
    record = (doc.get("soubory") or {}).get(soubor)
    if record is None:
        return None
    resolved = model.resolve(doc, soubor)

    def hodnota(pole):
        return (resolved.get(pole) or {}).get("hodnota")

    return {"soubor": soubor, "skupina": _skupina(doc, record),
            "datum": hodnota("datum"), "misto": hodnota("misto"),
            "autori": hodnota("autori")}


def _vyrez(face, asset, doc):
    """Výřez: obdélník na zmenšenině `sirka`×`vyska` + metadata."""
    return {"asset": asset["id"],
            "x1": face["boundingBoxX1"], "y1": face["boundingBoxY1"],
            "x2": face["boundingBoxX2"], "y2": face["boundingBoxY2"],
            "sirka": face["imageWidth"], "vyska": face["imageHeight"],
            "immich": _immich_metadata(asset),
            "archiv": _archiv_metadata(
                doc, file_key(asset.get("originalPath") or ""))}


def osoby_k_pojmenovani(client, assets, doc, odlozene):
    """Osoby k pojmenování z alba, sestupně podle počtu obličejů.

    `assets` je výsledek `client.search_album(album_id)` (s `people`),
    `doc` je `_metadata.json` akce (nebo None), `odlozene` jsou id
    osob odložených v aktuálním kole. Pořadí je deterministické
    (při shodě počtu podle id). Ke každé osobě až 3 výřezy z různých
    assetů s největším obličejem; `faces` se volá nejvýš jednou
    na asset (jen kandidáti).
    """
    kandidati = {}    # person_id → assety alba, na kterých osoba je
    for asset in assets:
        for person in asset.get("people") or []:
            pid = person.get("id")
            if not pid or _jmeno(person) or person.get("isHidden") \
                    or pid in odlozene:
                continue
            seznam = kandidati.setdefault(pid, [])
            if not any(a["id"] == asset["id"] for a in seznam):
                seznam.append(asset)
    cache = {}        # asset_id → obličeje (nejvýš jedno volání)

    def faces(asset_id):
        if asset_id not in cache:
            cache[asset_id] = client.faces(asset_id) or []
        return cache[asset_id]

    vysledky = []
    for pid, aset in kandidati.items():
        nejlepsi = {}     # asset_id → největší obličej osoby na assetu
        pocet = 0
        for a in aset:
            for f in _obliceje(faces(a["id"]), pid):
                pocet += 1
                best = nejlepsi.get(a["id"])
                if best is None or _plocha(f) > _plocha(best[0]):
                    nejlepsi[a["id"]] = (f, a)
        vyh = sorted(nejlepsi.values(),
                     key=lambda fa: (-_plocha(fa[0]), fa[1]["id"]))
        vysledky.append({"id": pid, "pocet": pocet,
                         "vyrezy": [_vyrez(f, a, doc)
                                    for f, a in vyh[:VYREZU]]})
    vysledky.sort(key=lambda o: (-o["pocet"], o["id"]))
    return vysledky


# --- odložené osoby ---------------------------------------------------------

class Odlozene:
    """`<work>/pojmenovani.json` = {login: {akce: [person_id, …]}}.

    Kolo = množina odložených: vymaže ho `nove_kolo` (volba „projít
    odložené znovu“), `vyradit` odebere id, která mezitím dostala
    jméno nebo byla skryta (volá se při načtení seznamu). Zavření
    nástroje kolo neukončí. Atomický zápis jako ostatní soubory
    ve `.work/`; poškozený nebo chybějící soubor = prázdný stav.
    """

    def __init__(self, work):
        self.path = Path(work) / "pojmenovani.json"
        self._lock = threading.Lock()

    def nacti(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def seznam(self, login, akce):
        """Id odložených osob (v pořadí odložení)."""
        with self._lock:
            return list((self.nacti().get(login) or {}).get(akce) or [])

    def odlozit(self, login, akce, person_id):
        """Odloží osobu; opakované odložení nic nedělá."""
        with self._lock:
            data = self.nacti()
            ids = data.setdefault(login, {}).setdefault(akce, [])
            if person_id not in ids:
                ids.append(person_id)
                _zapsat(self.path, data, prefix=".pojmenovani-")

    def nove_kolo(self, login, akce):
        """Konec kola: vymaže odložení uživatele v akci."""
        with self._lock:
            data = self.nacti()
            uzivatel = data.get(login) or {}
            if akce in uzivatel:
                del uzivatel[akce]
                data[login] = uzivatel
                _zapsat(self.path, data, prefix=".pojmenovani-")

    def vyjmout_akci(self, akce):
        """Odebere odložení všech uživatelů v akci a vrátí je
        ({login: [id, …]}); smazání akce je přenese do koše."""
        with self._lock:
            data = self.nacti()
            vyjmute = {login: uzivatel.pop(akce)
                       for login, uzivatel in data.items()
                       if isinstance(uzivatel, dict) and akce in uzivatel}
            if vyjmute:
                _zapsat(self.path, data, prefix=".pojmenovani-")
            return vyjmute

    def vlozit_akci(self, akce, odlozene):
        """Vrátí odložení z `vyjmout_akci` (obnovení z koše)."""
        if not odlozene:
            return
        with self._lock:
            data = self.nacti()
            for login, ids in odlozene.items():
                data.setdefault(login, {})[akce] = list(ids)
            _zapsat(self.path, data, prefix=".pojmenovani-")

    def zrusit(self, login, akce, person_id):
        """Zruší odložení jedné osoby (krok zpět); chybějící id
        nic nedělá."""
        with self._lock:
            data = self.nacti()
            odlozene = (data.get(login) or {}).get(akce) or []
            if person_id not in odlozene:
                return
            data[login][akce] = [i for i in odlozene if i != person_id]
            _zapsat(self.path, data, prefix=".pojmenovani-")

    def vyradit(self, login, akce, ids):
        """Odebere odložená id, která už nelze odložit."""
        without = set(ids)
        with self._lock:
            data = self.nacti()
            odlozene = (data.get(login) or {}).get(akce) or []
            if not any(i in without for i in odlozene):
                return
            data[login][akce] = [i for i in odlozene if i not in without]
            _zapsat(self.path, data, prefix=".pojmenovani-")
