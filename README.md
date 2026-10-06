# fotoarchiv-digi-media-metadata

Průvodce obohacením metadat digitální fotodokumentace ARÚB
(`FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB`). Lokální webová
aplikace s náhledy, ve které se fotkám a videím přiřazují metadata
jednotlivě nebo po skupinách.

Stav: **prototyp** se dvěma režimy. Výchozí vývojový archiv jen čte
a `_metadata.json` ukládá do pracovního adresáře `.work/` mimo archiv;
produkční (`--zapis-do-archivu`) ukládá `_metadata.json` do složky akce
a úklid provádí. Spuštění a testy viz `AGENTS.md`.

## Archiv

- Na první úrovni složky akcí `YYYY-MM-DD název`. Zpracovávají se jen
  ty; ostatní (`přetřídit`, `přednášky SKLEP TIC`) se nechávají beze
  změny.
- Ve složkách jsou JPG, mp4, RW2, občas png/zip a `Thumbs.db`
  (ignorovat). Některé akce mají podsložky (`RAW`, `Video`, …), viz
  [Podsložky a RAW](#podsložky-a-raw).
- Zdroje se liší kvalitou metadat:

  | vzor názvu            | přístroj          | EXIF                   |
  |-----------------------|-------------------|------------------------|
  | `P*.JPG`              | Panasonic DC-G9   | datum, bez GPS         |
  | `YYYYMMDD_HHMMSS.jpg` | Samsung SM-A528B  | datum, GPS             |
  | `IMG-YYYYMMDD-WA*.jpg`| WhatsApp          | žádný, datum jen v názvu |
  | `IMG_####.jpg`        | ?                 | neověřeno              |

## Podsložky a RAW

Zpracovává se jen kořen složky akce. Kořen má zůstat čistý pro
prohlížení: jen fotky a videa, která patří do Immiche.

- **Podsložky:** u každé podsložky bez přípony `.ignored` se průvodce
  zeptá, např. *„Složka `Video` obsahuje 22 souborů. Přesunout je mezi
  soubory akce, nebo složku ponechat stranou?“*
  - *Přesunout:* obsah jde do kořene, prázdná složka (včetně
    `Thumbs.db`) se smaže.
  - *Ponechat:* složka se přejmenuje na `název.ignored` a dál se jí
    průvodce nevšímá.
- **Přípona `.ignored` je jediný záznam o ignorování** — nikde jinde se
  seznam ignorovaných složek nevede. Immich ji vyloučí jedním vzorem.
- **RAW** (`rw2`, `cr2`, `cr3`, `nef`, `arw`, `dng`, `orf`, `raf`, bez
  ohledu na velikost písmen) do Immiche nejde a nepáruje se s JPG.
  - Podsložka, kde RAWy tvoří většinu souborů, se při ponechání
    přejmenuje na `RAW.ignored` bez ohledu na původní název (`raw`,
    `RAWy`, …).
  - RAWy v kořeni průvodce nabídne přesunout do `RAW.ignored`.
- Přesun nikdy nepřepíše existující soubor; operace se shodou názvů se
  přeskočí a nahlásí, ostatní proběhnou a podsložka, ze které něco
  zbylo, se nesmaže. Pokud `RAW.ignored` už existuje, soubory se do ní
  přidají.
- Přesuny a přejmenování mění cesty, které by Immich bral jako nové
  assety. Proto se mají udělat před napojením archivu do Immiche.

## Datový model

Zdroj pravdy je **jeden `_metadata.json` v každé složce akce**. Vše
ostatní (XMP sidecary, index) se z něj generuje.

Hodnoty se dědí **akce → skupina → soubor**; nižší úroveň přepisuje
vyšší. **Každé pole jde přepsat na kterékoli nižší úrovni**, včetně
autorů u jednotlivé fotky. Výjimkou jsou účastníci a místa akce (viz
níže). Skupiny průvodce navrhne automaticky podle
přístroje a vzoru názvu, uživatel je může upravit.

```json
{
  "schema": "fotoarchiv-digi-media-metadata/1",
  "akce": {
    "nazev": "kontrola Stezky Drahanskou vrchovinou",
    "popis": "…",
    "datum_od": "2026-04-28",
    "datum_do": "2026-04-28",
    "mista": ["Vysočany", "Holštejn"],
    "ucastnici": ["Spáčil, David", "Kopáčová, Zuzana"]
  },
  "souradnice_mist": {
    "Vysočany": {"gps": [49.43, 16.804],
                 "popis": "Vysočany, okres Blansko, …",
                 "osm": "relation/…"},
    "u rybníka": null
  },
  "skupiny": {
    "g9": {
      "autori": ["Spáčil, David", "Kopáčová, Zuzana"],
      "pristroj": "Panasonic DC-G9"
    }
  },
  "soubory": {
    "P1503712.JPG": {
      "skupina": "g9",
      "datum": "2026-04-28T09:44:36",
      "gps": null,
      "misto": "Holštejn",
      "popis": "…",
      "osoby": ["…"],
      "sha256": "…"
    }
  }
}
```

- **Účastníci akce (`ucastnici`) se nedědí.** Jsou to důležití lidé,
  kteří byli na akci, a přednostní návrhy při označování osob na
  fotkách — ne předpoklad, že jsou na každé fotce. Osoby na fotkách
  (`osoby`) se zadávají u souborů, případně u skupiny.
- **Místa akce (`mista`) jsou výčet**, fotka nebo skupina má jedno
  `misto`. Jediné místo akce se na fotky dědí; při víc místech se místo
  doplňuje u skupiny nebo fotky (návrhy z míst akce).
- **Souřadnice míst (`souradnice_mist`)** jsou rozhodnutí pro akci:
  přesný název `misto` → `{gps, popis}`, nebo `null` = „bez souřadnic“.
  Nedědí se, platí pro všechny fotky akce s tím místem. Výsledné `gps`
  fotky je vlastní nebo zděděné `gps`, jinak souřadnice jejího místa
  (úroveň `misto`); k souboru se neukládají a GPS z EXIF nepřepisují.
  Kandidáty hledá server v Nominatimu (OSM) až po otevření volby,
  odpovědi cachuje v `.work/cache/geokodovani.json` (sdílené všemi
  akcemi, smazatelné). Předvybraný je kandidát nejbližší fotkám akce
  s GPS; potvrzuje ho uživatel. Přejmenování místa rozhodnutí
  nepřenese.
- **Autorů může být víc.** `autori` znamená „fotil někdo z uvedených“;
  zpětně se nedá zjistit, kdo kdy držel foťák.
- Údaje z EXIF (datum, přístroj, GPS) zapisuje průvodce, u WhatsAppu
  datum z názvu souboru. Ruční údaje doplňuje uživatel.
- `sha256` slouží k odhalení přejmenovaných nebo změněných souborů.
- Originály se nemění.

## Jména osob

Žádný předem daný seznam. **Otevřený seznam návrhů** vzniká ze jmen
použitých ve všech `_metadata.json` v archivu a roste s tagováním.

- Kanonický tvar `Příjmení, Jméno`.
- Při zadání jména formulář porovná vstup se seznamem bez ohledu na
  diakritiku, velikost písmen a pořadí slov. Při shodě nabídne
  „Mysleli jste `Spáčil, David`?“ a kliknutím opravený tvar propíše do
  pole (např. pro `Spacil, David` nebo `David Spáčil`).
- Nové jméno, které nic nepřipomíná, se přijme a od té doby je
  v seznamu.
- Platí pro osoby na fotkách i pro autory.

## Výstupy

- **XMP sidecary** pro import do Immich: `foto.jpg.xmp` vedle souboru,
  s rozepsanými zděděnými hodnotami. Generují se z `_metadata.json`,
  ručně se needitují. Co Immich nemá vlastní pole, jde do hierarchických
  tagů `digiKam:TagsList` podle konvencí repa
  [arubrno/archiv-immich](https://github.com/arubrno/archiv-immich)
  (kořen malými písmeny, `/` v názvu → `-`):

  | `_metadata.json` | XMP sidecar |
  |------------------|-------------|
  | `popis`          | `dc:description` |
  | `datum`          | `xmp:CreateDate` s časovou zónou |
  | `gps`, jinak souřadnice `misto` | `exif:GPSLatitude` + `exif:GPSLongitude` |
  | `autori`         | `digiKam:TagsList` > `autor/…` |
  | `osoby`          | `digiKam:TagsList` > `osoba/…` |
  | název složky akce | `digiKam:TagsList` > `akce/…` |

  Datum s časem dostane zónu Europe/Prague platnou v daný okamžik
  (`+01:00` / `+02:00`; při podzimní dvojí hodině letní čas), samotné
  datum (WhatsApp) zůstane bez času a zóny. GPS ve formátu XMP
  `DDD,MM.mmmmmmK` (např. `49,24.378000N`). Prázdná pole se
  nezapisují; místo, přístroj, účastníci ani skupina do sidecaru
  nejdou. Sidecar skládá aplikace sama (ne exiftool), takže obsah
  závisí jen na `_metadata.json` a názvu složky akce.

  Ověřeno na Immichi 3.2 (5. 10. 2026): osoby (`Person`) vznikají jen
  z obličejů se souřadnicemi, které nemáme — `PersonInImage` se
  ignoruje. Autora Immich nezobrazuje (autor = kdo nahrál). Místo
  (`photoshop:City`, `Iptc4xmpCore:Location`) Immich zahodí i u fotek
  bez GPS a obec bere jen z GPS. Fotky bez GPS proto dostanou
  souřadnice svého místa, geokódované přes Nominatim (OSM) s cache
  a volbou kandidáta (OpenSpec změna `add-place-geocoding`); název
  místa se do sidecaru nezapisuje. U výsledků Nominatimu aplikace
  uvádí „© OpenStreetMap contributors“.
- **Immich** bude archiv číst jako externí knihovnu jen pro čtení
  s výjimkami `**/*.ignored/**` a nezpracovávanými složkami první úrovně
  (`přetřídit`, `přednášky SKLEP TIC`). Zatím nenapojeno.
- **Index** celého archivu (CSV, jeden řádek na akci) nahrazuje ručně
  vedený `_metadata.xlsx`. Generuje se, needituje.

## Aplikace

Lokální webová aplikace spouštěná nad složkou archivu.

### Tok práce

1. **Seznam akcí** se stavem (nezpracováno / rozpracováno / hotovo)
   a chybějícími údaji. Nové fotky a videa se do archivu dostanou
   **importem** (viz Import) do nové nebo stávající akce.
2. **Při prvním otevření akce průvodce:** úklid (podsložky, RAW) →
   načtení a skupiny → údaje akce → autoři skupin. Průvodce provede
   vším povinným; údaje jednotlivých souborů se doplňují na ploše.
3. **Pak pracovní plocha** (i při každém dalším otevření): vlevo mřížka
   náhledů po skupinách, vpravo formulář podle výběru — nic vybráno =
   akce, hlavička skupiny = skupina, vybrané soubory = soubory. Zděděné
   hodnoty jsou ve formuláři vidět a jdou přepsat. Lišta ukazuje, co
   chybí („2 skupiny bez autorů, 14 souborů bez data“).

   Místo mřížky jde přepnout na **lupu** (Enter, dvojklik na dlaždici
   nebo přepínač; zpět Esc): velká fotka nebo přehrávač videa a pod ní
   filmový pás celé akce se skupinami oddělenými předělem. Šipky
   přepínají aktuální soubor a vyberou jen jej, Shift+šipky výběr
   rozšiřují; klik do pásu vybírá jako v mřížce. Výběr i formulář jsou
   s mřížkou společné.
4. **Dokončení akce** uloží změny, zkontroluje úplnost (co chybí,
   ukáže a dokončí až po potvrzení), zapíše sidecary a nastaví
   `dokonceno`. Selže-li zápis některého sidecaru, akce dokončená
   není. Tlačítko **Exportovat** zapíše sidecary bez kontroly
   a bez dokončení. U tlačítka plocha ukazuje, kolik sidecarů je
   neaktuálních, a po úpravě „neexportované změny“; seznam akcí
   u dokončené akce upravené po exportu uvede „změněno po exportu“.

Našeptávání a kontrola jmen viz výše.

### Import

Průvodce importem se spouští ze seznamu akcí (bez cíle) nebo z plochy
akce (s ní jako předvybraným cílem). Kroky: soubory → přehled → cíl →
plán → výsledek.

- **Soubory:** jednotlivé soubory i celá složka, výběrem nebo
  přetažením; soubory z podsložek se berou, jako by ležely v jedné
  úrovni. Nahrávají se po jednom (2–3 souběžně, s průběhem) do
  `.work/import/<id>/`, ne do archivu; zavření stránky archiv nezmění.
  Adresa `#/import/<id>` přežije reload. Limit 20 GB na soubor, server
  před nahráním kontroluje volné místo. Import patří jménu uživatele
  (porovnání jako u návrhů jmen), ne záložce: seznam akcí ukazuje
  „Moje rozpracované importy“ (založeno, počet a velikost souborů,
  zamýšlený cíl, poslední aktivita) s tlačítky Pokračovat a Zahodit.
  Cizí import není vidět a jeho adresa hlásí „nenalezen“.
- **Přehled:** počty fotek, videí a RAWů, rozsah dat z EXIF (WhatsApp
  z názvu), přístroje, nepodporované soubory. Přijímají se média
  aplikace (jpg, jpeg, png, mp4, mov) a RAWy; `Thumbs.db` se tiše
  přeskočí, ostatní se vypíšou a nepřenesou.
- **Cíl:** stávající akce, nebo nová — datum se předvyplní nejstarším
  dnem z EXIF, název doplní uživatel; složka `YYYY-MM-DD název` bez
  `/` a `\` a nesmí existovat (bez ohledu na velikost písmen; jinak
  průvodce nabídne zvolit ji jako stávající). U dokončené akce
  upozorní, že nové soubory budou bez metadat.
- **Plán:** média do kořene, RAWy do `RAW.ignored/`. Jméno, které
  v cíli existuje nebo ho má víc souborů výběru, se blokuje.
  Duplicita (stejný sha256 jako soubor v kořeni cílové akce nebo jiný
  soubor výběru) se přeskočí; hashe akce se počítají jen u souborů
  shodné velikosti a cachují se v `.work/cache/sha256/`. Na SMB to
  může trvat minuty, proto server posílá průběh porovnání (stream
  NDJSON, po souboru a u velkých po 64 MB; hashe z cache jsou hned
  hotové) a tlačítko je do konce výpočtu zablokované. Zvolený cíl se
  uloží k importu a po návratu se předvyplní.
- **Provedení** (jen produkční režim, ve vývojovém se plán jen ukáže):
  plán se sestaví znovu, soubor se zkopíruje do dočasného
  `.import-*.tmp` v cílové složce, dostane čas změny originálu
  a přejmenuje se, jen pokud cíl pořád neexistuje. Selhání jednoho
  souboru ostatní nezastaví. Import do stávající akce vyžaduje zámek
  akce; nová akce vznikne jen, pokud složka mezitím nevznikla, a zámek
  na ni dostane relace importu. Průběh jde streamem (NDJSON) po
  souborech a u velkých po 64 MB; ukazatel se posouvá podle bajtů.
  Přenesený soubor zmizí z pracovního adresáře hned. Zavření stránky
  kopírování zastaví nejpozději po dalších 64 MB: rozkopírovaný
  dočasný soubor se smaže, přenesené zůstanou v archivu, zbytek
  v pracovním adresáři. Když dočasný soubor smazat nejde (výpadek
  SMB), smaže ho další import do téže akce: před kopírováním odstraní
  `.import-*.tmp` starší než hodinu v kořeni a v `RAW.ignored/`
  a uvede je ve výsledku.
- **Výsledek:** přenesené, blokované, duplicitní a selhané soubory;
  přenesené zmizí z pracovního adresáře, ostatní tam zůstanou, dokud
  uživatel import nezahodí. Importy neaktivní přes 7 dní server smaže
  při startu. Průvodce nabídne otevřít akci; nové soubory jsou mezi
  „novými od posledního otevření“, metadata se doplňují běžně.

### Ukládání a export

- `_metadata.json` se ukládá průběžně, atomicky (dočasný soubor
  a přejmenování), v produkčním režimu do složky akce, ve vývojovém do
  `.work/metadata/<akce>/`. Rozpracovaná metadata z `.work` převezme do
  archivu jednorázově `python -m fotoarchiv prevzit` (jen u akcí, které
  `_metadata.json` v archivu ještě nemají).
- XMP sidecary se zapisují při dokončení akce, samostatným tlačítkem
  Exportovat a dávkově `python -m fotoarchiv exportovat [AKCE]` (bez
  akce všechny s `_metadata.json`; zámky nekontroluje). **Přepisují se
  jen změněné:** obsah sidecaru se generuje deterministicky (bez
  časových razítek) a porovná s obsahem na disku; zapíše se atomicky,
  jen když chybí nebo se liší. Sidecar vznikne jen k souborům se
  záznamem, v kořeni a neoznačeným k vyřazení; jiné `.xmp` se nemažou.
  Ve vývojovém režimu jdou sidecary do `.work/xmp/<akce>/`.
- Po exportu bez chyb se do `.work/export/<akce>.json` zapíše verze
  (sha256) `_metadata.json`, ze které export vznikl. Liší-li se od
  aktuální, akce má neexportované změny; bez záznamu je stav neznámý.
  Do archivu ani do `_metadata.json` se nic z toho nezapisuje.
- Před uložením `_metadata.json` aplikace ověří, že ho mezitím nezměnil
  někdo jiný; jinak uložení odmítne a nabídne znovunačtení.

### Souběh

Aplikace běží jako jeden sdílený server; zámek otevřené akce drží
server v paměti (kdo, relace prohlížeče, od kdy, poslední heartbeat).
Proto **server smí běžet jen jako jeden proces** (vlákna ano, víc
workerů ne). Do archivu se žádný soubor zámku nezapisuje.

- Při otevření akce klient požádá o zámek. Drží-li akci někdo jiný,
  otevře ji jen ke čtení s upozorněním „Akci upravuje …“.
- Klient zámek obnovuje heartbeatem (~1 min), dokud je akce otevřená;
  při odchodu z akce nebo zavření stránky ho uvolní.
- Zámek bez heartbeatu ~5 min (podle hodin serveru) je opuštěný a jde
  převzít. Kdo o zámek přijde, přepne se jen ke čtení.
- Uložení, provedení úklidu a import do stávající akce bez zámku
  server odmítne; kontrola verze `_metadata.json` platí i pro
  držitele zámku.
- Restart serveru zámky zahodí; klient je při dalším heartbeatu získá
  znovu, pokud je akce volná.
- „Kdo“ je do zavedení přihlašování jméno zadané v prohlížeči.
- Rozpracovaný import patří jménu, ne záložce; vidí ho jen jeho
  vlastník. Během provedení importu server odmítne nahrávání,
  zahození i další provedení téhož importu (příznak v paměti); nahrávat
  z víc záložek najednou lze. Průvodce v jiné záložce upozorní, že se
  import právě nahrává nebo kopíruje jinde.
- Drží-li zámek akce jiná záložka téhož jména, hláška místo „Akci
  upravuje …“ radí zavřít původní záložku. Zámek nové akce, který
  server vzal pro provedení importu, se při přerušení provedení uvolní.

Metadata (JPG, mp4) čte `exiftool`. Náhledy
(320 px do mřížky, 1600 px do lupy) se cachují lokálně mimo archiv —
archiv leží na SMB; lupa si sousední fotky načítá předem. Videa se do
lupy posílají přímo z archivu, jen ke čtení.

Primárně Linux (Fedora). Kolegové na Windows jsou žádoucí, ale ne
priorita: snadné spuštění na Windows se řeší, jen pokud nebude stát
dny práce.
