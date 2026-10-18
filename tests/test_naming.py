"""Nástroj pojmenování osob: výběr osob, výřezy, metadata, odložené.

Čistý modul `fotoarchiv/naming.py` — bez Flasku, proti `FakeImmich`
jako `fetch` skutečného `Clienta`.
"""

from fotoarchiv import immich
from fotoarchiv.immich import Client
from fotoarchiv.naming import (Odlozene, assety_alba, nepojmene_ids,
                               osoby_k_pojmenovani)

from .test_immich import ROOT, URL, KEY, FakeImmich, oblicej, osoba

AKCE = "2026-04-28 Výzkum"
ALBUM = "alb-1"


def client(fake):
    return Client(URL, KEY, fake)


def naplun(fake, asset_id, *osoby):
    """Asset v albu s obličeji zadaných osob (jeden obličej na osobu)."""
    fake.add(asset_id, f"{ROOT}/{AKCE}/{asset_id}.jpg",
             *[oblicej(o) for o in osoby])
    if ALBUM not in fake.albums:
        fake.albums[ALBUM] = {"id": ALBUM, "albumName": AKCE,
                              "assetIds": []}
    fake.albums[ALBUM]["assetIds"].append(asset_id)


def assets(fake):
    return client(fake).search_album(ALBUM)


def test_nepojmenovana_nabiduta_jmena_a_skryta_ne():
    """Scénář Osoby k pojmenování: nepojmenovaná ano, pojmenovaná
    a skrytá ne; odložená ne."""
    fake = FakeImmich()
    nep = osoba("p-nep")
    naplun(fake, "a1", nep, osoba("p-jmena", "Vzorný, Tomáš"),
           osoba("p-skryta", None, skryta=True))
    vysl = osoby_k_pojmenovani(client(fake), assets(fake), {}, [])
    assert [o["id"] for o in vysl] == ["p-nep"]
    assert vysl[0]["pocet"] == 1
    # Odložená se nenabídne.
    assert osoby_k_pojmenovani(client(fake), assets(fake), {}, ["p-nep"]) \
        == []


def test_poradi_podle_poctu_obliceju():
    """Scénář Pořadí: 12 obličejů se nabídne před 2."""
    fake = FakeImmich()
    velka, mala = osoba("p-velka"), osoba("p-mala")
    for i in range(12):
        naplun(fake, f"v{i}", velka)
    for i in range(2):
        naplun(fake, f"m{i}", velka, mala)
    # deterministicky i při obráceném pořadí odpovědi (id assetů se
    # ve fake řadí, ale osoby ne: zadáme menší id až jako druhou)
    naplun(fake, "z1", velka, osoba("a-druha"))
    vysl = osoby_k_pojmenovani(client(fake), assets(fake), {}, [])
    assert [(o["id"], o["pocet"]) for o in vysl] == [
        ("p-velka", 15), ("p-mala", 2), ("a-druha", 1)]


def test_poradi_pri_shode_podle_id():
    fake = FakeImmich()
    naplun(fake, "a1", osoba("p-b"), osoba("p-a"))
    vysl = osoby_k_pojmenovani(client(fake), assets(fake), {}, [])
    assert [o["id"] for o in vysl] == ["p-a", "p-b"]


def test_vyrezy_tri_z_peti_nejvetsi_obliceje():
    """Scénář Náhledy: 5 fotek → 3 výřezy z různých assetů s největšími
    obličeji; 1 fotka → 1 výřez."""
    fake = FakeImmich()
    p = osoba("p-1")
    # plochy (x2-x1)*(y2-y1): a5 > a4 > a3 > a2 > a1
    velikosti = {"a1": 100, "a2": 200, "a3": 300, "a4": 400, "a5": 500}
    for aid, strana in velikosti.items():
        fake.add(aid, f"{ROOT}/{AKCE}/{aid}.jpg",
                 {"imageWidth": 1000, "imageHeight": 750,
                  "boundingBoxX1": 0, "boundingBoxY1": 0,
                  "boundingBoxX2": strana, "boundingBoxY2": 1,
                  "sourceType": "machine-learning", "person": p})
        fake.albums.setdefault(
            ALBUM, {"id": ALBUM, "albumName": AKCE, "assetIds": []})
        fake.albums[ALBUM]["assetIds"].append(aid)
    vysl = osoby_k_pojmenovani(client(fake), assets(fake), {}, [])
    [položka] = vysl
    assert položka["pocet"] == 5
    assert [v["asset"] for v in položka["vyrezy"]] == ["a5", "a4", "a3"]
    v = položka["vyrezy"][0]
    assert v["sirka"] == 1000 and v["vyska"] == 750
    assert (v["x1"], v["y1"], v["x2"], v["y2"]) == (0, 0, 500, 1)
    # faces se volá nejvýš jednou na asset
    volani = [url for _, url in fake.calls if "/api/faces" in url]
    assert len(volani) == len(set(volani)) == 5


def test_vyrez_jedne_fotky_dva_obliceje():
    """Jeden výřez z jedné fotky i s dvěma obličeji; počet je 2."""
    fake = FakeImmich()
    p = osoba("p-1")
    fake.add("a1", f"{ROOT}/{AKCE}/a1.jpg", oblicej(p), oblicej(p))
    fake.albums[ALBUM] = {"id": ALBUM, "albumName": AKCE,
                          "assetIds": ["a1"]}
    vysl = osoby_k_pojmenovani(client(fake), assets(fake), {}, [])
    assert vysl[0]["pocet"] == 2
    assert [v["asset"] for v in vysl[0]["vyrezy"]] == ["a1"]


def test_metadata_sparovane_a_nesparovane_fotky():
    """Scénář Metadata: spárovaná `P9109996.JPG` ve skupině
    `DOD 2015_Jana` se zděděným místem a autory; nespárovaná fotka má
    jen údaje z Immiche (archiv null)."""
    fake = FakeImmich()
    p = osoba("p-1")
    fake.add("a1", f"{ROOT}/{AKCE}/P9109996.JPG", oblicej(p))
    fake.add("a2", f"{ROOT}/{AKCE}/cizi.jpg", oblicej(p))
    fake.albums[ALBUM] = {"id": ALBUM, "albumName": AKCE,
                          "assetIds": ["a1", "a2"]}
    fake.exify["a2"] = {}           # bez EXIF data
    fake.vytvoreno["a2"] = "2015-06-01T09:00:00.000Z"
    doc = {"schema": 1,
           "akce": {"nazev": "Výzkum", "mista": ["Brno"]},
           "skupiny": {"g1": {"nazev": "DOD 2015_Jana",
                              "autori": ["Novák, Petr"]}},
           "soubory": {"P9109996.JPG": {"skupina": "g1",
                                         "datum": "2015-05-01"}}}
    [polozka] = osoby_k_pojmenovani(client(fake), assets(fake), doc, [])
    sparovana, nesparovana = polozka["vyrezy"]
    assert sparovana["immich"] == {
        "soubor": "P9109996.JPG",
        "datum": "2026-04-28T10:00:00.000Z"}
    assert sparovana["archiv"] == {
        "soubor": "P9109996.JPG", "skupina": "DOD 2015_Jana",
        "datum": "2015-05-01", "misto": "Brno",
        "autori": ["Novák, Petr"]}
    # Nespárovaná: datum z fileCreatedAt, archiv None
    assert nesparovana["immich"] == {"soubor": "cizi.jpg",
                                     "datum": "2015-06-01T09:00:00.000Z"}
    assert nesparovana["archiv"] is None


def test_metadata_bez_dokumentu():
    """Akce bez `_metadata.json` (`doc` None): jen údaje z Immiche."""
    fake = FakeImmich()
    naplun(fake, "a1", osoba("p-1"))
    [polozka] = osoby_k_pojmenovani(client(fake), assets(fake), None, [])
    assert polozka["vyrezy"][0]["archiv"] is None


def test_assety_alba_a_nepojmene_ids():
    fake = FakeImmich()
    naplun(fake, "a1", osoba("p-1"), osoba("p-2", "Vzorný, Tomáš"))
    a = assets(fake)
    assert assety_alba(a) == {"a1"}
    assert nepojmene_ids(a) == {"p-1"}


# --- odložené osoby -----------------------------------------------------------

def test_odlozene_prezijou_novou_instanci(tmp_path):
    """Scénář Znovuotevření: odložení přežije novou instanci."""
    od = Odlozene(tmp_path)
    od.odlozit("novak", AKCE, "p-1")
    od.odlozit("novak", AKCE, "p-1")       # duplicita nic nedělá
    assert Odlozene(tmp_path).seznam("novak", AKCE) == ["p-1"]


def test_odlozene_konec_kola(tmp_path):
    """Scénář Konec kola: nové kolo vymaže odložení."""
    od = Odlozene(tmp_path)
    od.odlozit("novak", AKCE, "p-1")
    od.nove_kolo("novak", AKCE)
    assert od.seznam("novak", AKCE) == []
    assert Odlozene(tmp_path).seznam("novak", AKCE) == []


def test_odlozene_jiny_uzivatel_a_akce(tmp_path):
    """Scénář Jiný uživatel: odložení je per login a akce."""
    od = Odlozene(tmp_path)
    od.odlozit("novak", AKCE, "p-1")
    assert od.seznam("prikladny", AKCE) == []
    assert od.seznam("novak", "2026-05-01 jina") == []
    od.nove_kolo("prikladny", AKCE)           # cizí výmaz nic nezmění
    assert od.seznam("novak", AKCE) == ["p-1"]


def test_odlozene_vyradeni_pojmenovane(tmp_path):
    """Vyřadí se id, která mezitím dostala jméno nebo byla skryta."""
    od = Odlozene(tmp_path)
    od.odlozit("novak", AKCE, "p-1")
    od.odlozit("novak", AKCE, "p-2")
    od.vyradit("novak", AKCE, ["p-1"])
    assert od.seznam("novak", AKCE) == ["p-2"]
    od.vyradit("novak", AKCE, ["p-2"])
    assert od.seznam("novak", AKCE) == []


def test_odlozene_poruseny_soubor_prazdny(tmp_path):
    """Poškozený soubor = prázdný stav (jako ostatní `.work/`)."""
    (tmp_path / "pojmenovani.json").write_text("{", encoding="utf-8")
    assert Odlozene(tmp_path).seznam("novak", AKCE) == []
