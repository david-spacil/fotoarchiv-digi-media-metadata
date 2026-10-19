# fotoarchiv-digi-media-metadata

Webová aplikace pro doplňování metadat do digitální fotodokumentace
ARÚB (`FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB`). Archiv
je sdílená složka s fotkami a videi z akcí ústavu, které samy nesou
nanejvýš datum, přístroj a někdy GPS. Kdo fotil, kde přesně a co je
na fotce, ví jen ten, kdo u toho byl.
Aplikace mu dovolí to rychle doplnit: po celé akci, po skupinách fotek
(např. podle fotoaparátu) nebo u jednotlivé fotky, s náhledy přímo
z archivu.

Údaje se ukládají do jednoho `_metadata.json` ve složce akce. Z něj
aplikace generuje XMP sidecary, ze kterých si je načte
[Immich](https://immich.app), kde se archiv prohlíží a prohledává,
a přehledný index archivu. Originály fotek a videí se nikdy nemění.

## Co aplikace umí

- **Fronta práce:** seznam akcí s hotovostí po polích (autoři, datum,
  místo, osoby), filtry, hledáním a štítky „nekompletní“ nebo
  „k vyřešení“.
- **Doplňování s děděním:** údaje zadané u akce platí pro skupiny
  a soubory, dokud je nižší úroveň nepřepíše; formulář ukazuje, odkud
  hodnota pochází. Mřížka náhledů a lupa jdou ovládat klávesnicí.
- **Úklid akce:** RAWy, podsložky, nepovedené a cizí soubory se
  přesunou stranou do složek `*.ignored`, nic se nemaže.
- **Import:** nahrání nových fotek do nové nebo stávající akce,
  nebo převzetí složky z `přetřídit`, s kontrolou duplicit
  a poškozených souborů a s rozdělením do skupin a autorů ještě před
  zápisem do archivu.
- **Napojení na Immich:** dokončená akce se Immichi zveřejní i se
  sidecary a dostane album; obličeje, které v Immichi někdo
  pojmenoval, se synchronizují zpět do `_metadata.json` jako záloha
  a nepojmenované osoby jde pojmenovat přímo z aplikace (viz
  [Immich](docs/navrh/immich.md)
  a [Pojmenování osob](docs/navod/pojmenovani-osob.md)).
- **Souřadnice míst:** fotkám bez GPS se doplní souřadnice místa akce
  vyhledané v OpenStreetMap (Nominatim).
- **Kontrola archivu:** hledání poškozených souborů (vynulované bloky
  z karty) a nesrovnalostí v akcích, v aplikaci i příkazem.
- **Index archivu:** `_INDEX.html` a `_INDEX.md` v kořeni archivu pro
  lidi, kteří archiv procházejí v Průzkumníku.
- **Víc lidí najednou:** přihlášení s rolemi (admin, archivář, běžný
  uživatel) a zámky akcí, aby si dva lidé nepřepsali práci.

Podrobnosti jsou v [dokumentaci](docs/README.md);
[návod k použití](docs/README.md#návod-k-použití) prochází akci od
importu po dokončení.

## Lokální spuštění

Potřeba: Python 3, `exiftool`, `ffmpeg` (bez něj videa nemají náhled)
a připojený archiv.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m fotoarchiv --archiv /cesta/k/archivu
# → http://127.0.0.1:5000
```

Bez dalších přepínačů je to **vývojový režim**: archiv se jen čte,
metadata, cache a sidecary jdou do `.work/`. **Produkční režim**
(`--zapis-do-archivu`) ukládá `_metadata.json` do složek akcí
a provádí úklid a import. Server smí běžet jen v jedné instanci.

Přístup vyžaduje přihlášení: správce zapíše účet do
`.work/uzivatele.json` a vydá jednorázové heslo (pro rychlé
vyzkoušení stačí `--bez-prihlaseni`, každý je pak admin):

```json
{"prikladny": {"jmeno": "Příkladný, Daniel", "role": "admin"}}
```

```sh
.venv/bin/python -m fotoarchiv heslo prikladny --work .work
```

Další přepínače, role a nasazení: [Lokální
spuštění](docs/provoz/spusteni.md), [Přihlášení a
role](docs/provoz/prihlaseni.md), [Docker](docs/provoz/docker.md),
[Příkazy](docs/provoz/prikazy.md). Testy viz `AGENTS.md`.

## Struktura archivu

Příklad s vymyšlenými názvy:

```text
fotoarchiv_fotodokumentace_digitalni_ARUB/
├── 2025-09-12 průzkum u Vzorova/            # dokončená akce
│   ├── _metadata.json                       # zdroj pravdy akce
│   ├── P1000123.JPG
│   ├── P1000123.JPG.xmp                     # sidecar pro Immich
│   ├── 20250912_101500.jpg
│   ├── IMG-20250912-WA0003.jpg              # WhatsApp, datum z názvu
│   ├── RAW.ignored/                         # RAWy, Immich je nevidí
│   ├── k_odstraneni.ignored/                # vyřazené soubory
│   └── ostatni.ignored/                     # PDF, zipy, osiřelé .xmp
├── 2026-03-05 exkurze Příkladov.ignored/    # nedokončená akce
├── přetřídit/                               # nezatříděné, k importu
│   └── fotky od Vzorného/
├── sbírka portrétů/                         # není akce, nezpracovává se
├── _INDEX.html                              # generovaný index
└── _INDEX.md
```

- Zpracovávají se jen složky akcí na první úrovni (`YYYY-MM-DD
  název`) a v nich jen kořen; ostatní složky aplikace nechává beze
  změny, `přetřídit` slouží jako zdroj importu.
- Kořen akce obsahuje jen fotky a videa, která patří do Immiche.
  Podsložky se buď sloučí s kořenem, nebo dostanou příponu
  `.ignored`, kterou Immich vynechá; přípona je jediný záznam
  o ignorování.
- **Nedokončená akce má v produkčním režimu příponu `.ignored`**
  i u složky akce, Immich ji tak uvidí až po dokončení i se sidecary.
  V aplikaci a v URL se akce jmenuje bez přípony.

Podrobně: [Archiv](docs/navrh/archiv.md), [Podsložky a
RAW](docs/navrh/podslozky-a-raw.md).

## Datový model

Zdroj pravdy je **jeden `_metadata.json` v každé složce akce**. Vše
ostatní (XMP sidecary, index) se z něj generuje.

Hodnoty se dědí **akce → skupina → soubor**; nižší úroveň přepisuje
vyšší. **Každé pole jde přepsat na kterékoli nižší úrovni**, včetně
autorů u jednotlivé fotky. Výjimkou jsou účastníci a místa akce (viz
níže). **Autoři jsou jen u skupiny a souboru**, akce je nemá: fotky
jedné akce bývají od víc lidí (issue #43). Skupiny průvodce navrhne
automaticky podle přístroje a vzoru názvu, uživatel je může upravit.

```json
{
  "schema": "fotoarchiv-digi-media-metadata/2",
  "akce": {
    "nazev": "průzkum u Vzorova",
    "popis": "…",
    "datum_od": "2025-09-12",
    "datum_do": "2025-09-12",
    "mista": ["Vzorov", "Příkladná Lhota"],
    "ucastnici": ["Příkladný, Daniel", "Modelová, Zuzana"]
  },
  "souradnice_mist": {
    "Vzorov": {"gps": [49.12, 16.58],
               "popis": "Vzorov, okres Vzorový, …",
               "osm": "relation/…"},
    "u rybníka": null
  },
  "skupiny": {
    "g9": {
      "autori": ["Příkladný, Daniel", "Modelová, Zuzana"],
      "pristroj": "Panasonic DC-G9"
    }
  },
  "soubory": {
    "P1503712.JPG": {
      "skupina": "g9",
      "datum": "2025-09-12T09:44:36",
      "gps": null,
      "misto": "Příkladná Lhota",
      "popis": "…",
      "obliceje": [{"jmeno": "Vzorný, Tomáš",
                    "oblast": [0.2725, 0.432, 0.041, 0.0747]}],
      "sha256": "…"
    },
    "P1503713.JPG": {"skupina": "g9", "vyradit": true}
  },
  "upravili": {"Příkladný, Daniel": "2025-09-14T10:15:02"}
}
```

- **Účastníci akce (`ucastnici`) se nedědí.** Jsou to důležití lidé,
  kteří byli na akci, a přednostní návrhy jmen — ne předpoklad, že jsou
  na každé fotce.
- **Osoby na fotkách jsou pojmenované obličeje z Immiche
  (`obliceje`).** Jen u souboru, nedědí se a v aplikaci se nezadávají:
  zapisuje je jen synchronizace (viz [Immich](docs/navrh/immich.md)). Položka je
  `{jmeno, oblast}`; `oblast` = `[x, y, w, h]` jako podíly rozměrů
  fotky zobrazené se správnou orientací (střed a velikost, tvar MWG),
  zaokrouhlené na 4 místa. Je to i záloha pojmenovaných obličejů,
  ze které jde Immich obnovit (viz
  [Výstupy](docs/navrh/vystupy.md)).
- **Schéma `/2`** proti `/1` vypustilo autory celé akce
  (`akce.autori`), starší pole `osoby` (všechny úrovně) a datum od/do
  u skupiny (`datum_od`, `datum_do`). Vypuštěné klíče se nedědí, do
  výstupů nejdou a uložení je odstraní; dokument `/1` server při
  načtení převede (soubor se přepíše až dalším uložením) a příkaz
  `migrovat` převede celý archiv naráz. U dokončené akce bez autorů
  celé akce převod sidecary nemění, takže zůstane exportovaná; akce
  s nimi ukáže neexportované změny (soubory, které autory jen dědily,
  je po převodu nemají).
- **Místa akce (`mista`) jsou výčet**, fotka nebo skupina má jedno
  `misto`. Jediné místo akce se na fotky dědí; při víc místech se místo
  doplňuje u skupiny nebo fotky (návrhy z míst akce).
- **Souřadnice míst (`souradnice_mist`)** jsou rozhodnutí pro akci:
  přesný název `misto` → `{gps, popis[, osm]}`, nebo `null` = „bez
  souřadnic“. `osm` (např. `relation/439179`) je objekt OpenStreetMap,
  ze kterého souřadnice pocházejí; ukládá ho jen volba kandidáta
  z Nominatimu, slouží k ověření zdroje (rozlišení stejnojmenných míst)
  a nejde do sidecarů ani indexu.
  Nedědí se, platí pro všechny fotky akce s tím místem. Výsledné `gps`
  fotky je vlastní nebo zděděné `gps`, jinak souřadnice jejího místa
  (úroveň `misto`); k souboru se neukládají a GPS z EXIF nepřepisují.
  Kandidáty hledá server v Nominatimu (OSM) až po otevření volby,
  odpovědi cachuje v `.work/cache/geokodovani.json` (sdílené všemi
  akcemi, smazatelné). User-Agent nese kontakt provozovatele, který
  nastavuje admin v Nastavení (jeden pro server, předvyplní se jeho
  e-mail); bez kontaktu je geokódování vypnuté. Předvybraný je kandidát nejbližší fotkám akce
  s GPS; potvrzuje ho uživatel. Každý kandidát i uložené místo s `osm`
  má odkaz „OSM“ na objekt na openstreetmap.org (otevře se v nové
  kartě). Přejmenování místa rozhodnutí nepřenese.
- **Autorů může být víc.** `autori` znamená „fotil někdo z uvedených“;
  zpětně se nedá zjistit, kdo kdy držel foťák.
- Údaje z EXIF (datum, přístroj, GPS) zapisuje průvodce, u WhatsAppu
  datum z názvu souboru. Ruční údaje doplňuje uživatel.
- `sha256` slouží k odhalení přejmenovaných nebo změněných souborů.
- **`vyradit: true`** označuje soubor k vyřazení (jen u souboru, nedědí
  se). Do XMP exportu takový soubor nejde, do chybějících údajů se
  nepočítá; úklid ho přesune do `k_odstraneni.ignored` a záznam smaže.
- **`overeno: true`** je ruční potvrzení, že soubor je i přes výsledek
  kontroly integrity v pořádku (jen u souboru, nedědí se, do sidecaru
  ani indexu nejde). Takový soubor se nepočítá do odznaku poškozených.
- **`upravili`** = kdo akci ukládal: jméno uživatele → čas jeho
  posledního uložení, dokončení nebo provedení importu do ní (ISO 8601,
  místní čas serveru, na sekundy; import zapisuje u nové akce i akce
  s `_metadata.json`). Zapisuje jen server jménem z přihlášené relace
  (stejné jako u zámku); hodnotu od klienta zahodí a vezme ji z uložené
  verze. Starší akce pole nemají, vznikne prvním uložením. Nedědí se, do
  sidecaru ani indexu nejde; slouží filtru „Moje rozpracované“, řazení
  seznamu akcí a oprávnění k úpravě akce (viz
  [Přihlášení a role](docs/provoz/prihlaseni.md)).
- **Osoby v kompletnosti akce** nejsou v `_metadata.json` (nejsou to
  údaje o fotkách a měnily by verzi akce). Počty pojmenovaných
  a neskrytých osob s obličejem v albu akce ukládá synchronizace (a po
  každém kroku nástroj pojmenování) do `.work/immich-osoby.json`
  `{akce: {pojmenovane, celkem, cas}}`. Hotovost je uvádí jen u akce
  s albem ve stavu *obličeje rozpoznány*; nepojmenované osoby dělají
  dokončenou akci „nekompletní“ (viz
  [Immich](docs/navrh/immich.md)).
- **Další soubory Immiche ve `.work/`** (nikdy v archivu):
  `immich.json` (adresa, klíč, knihovna; 0600), `immich-alba.json`
  `{akce: {album, stav, cas, chyba?}}` (vazba na album a stav akce
  v Immichi) a `pojmenovani.json` `{login: {akce: [id osoby]}}`
  (osoby odložené volbou „odložit“ v aktuálním kole).
- Originály se nemění.

## Dokumentace

- [Rozcestník dokumentace](docs/README.md)
- [Návod k použití](docs/README.md#návod-k-použití) — import, seznam
  akcí, průvodce, pracovní plocha, úklid, dokončení, pojmenování osob
- [Provoz](docs/README.md#provoz) — spuštění, přihlášení, Docker,
  Immich, příkazy
- [Návrh](docs/README.md#návrh) — pravidla archivu, výstupy, Immich,
  ukládání a souběh; spolu s datovým modelem výše specifikace projektu
- [AGENTS.md](AGENTS.md) — vývoj, testy a invarianty návrhu
