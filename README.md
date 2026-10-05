# fotoarchiv-digi-media-metadata

Průvodce obohacením metadat digitální fotodokumentace ARÚB
(`FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB`). Lokální webová
aplikace s náhledy, ve které se fotkám a videím přiřazují metadata
jednotlivě nebo po skupinách.

Stav: **prototyp** — archiv jen čte, `_metadata.json` ukládá do
pracovního adresáře `.work/` mimo archiv; export XMP, zámek a provedení
úklidu zatím chybí. Spuštění a testy viz `AGENTS.md`.

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
- Přesun nikdy nepřepíše existující soubor; při shodě názvů se zastaví
  a nahlásí ji. Pokud `RAW.ignored` už existuje, soubory se do ní
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

  Ověřeno na Immichi 3.2 (5. 10. 2026): osoby (`Person`) vznikají jen
  z obličejů se souřadnicemi, které nemáme — `PersonInImage` se
  ignoruje. Autora Immich nezobrazuje (autor = kdo nahrál). Místo
  (`photoshop:City`, `Iptc4xmpCore:Location`) Immich zahodí i u fotek
  bez GPS a obec bere jen z GPS. Fotky bez GPS proto dostanou
  souřadnice svého místa, geokódované přes Nominatim (OSM) s cache
  a volbou kandidáta (OpenSpec změna `add-place-geocoding`); název
  místa se do sidecaru nezapisuje.
- **Immich** bude archiv číst jako externí knihovnu jen pro čtení
  s výjimkami `**/*.ignored/**` a nezpracovávanými složkami první úrovně
  (`přetřídit`, `přednášky SKLEP TIC`). Zatím nenapojeno.
- **Index** celého archivu (CSV, jeden řádek na akci) nahrazuje ručně
  vedený `_metadata.xlsx`. Generuje se, needituje.

## Aplikace

Lokální webová aplikace spouštěná nad složkou archivu.

### Tok práce

1. **Seznam akcí** se stavem (nezpracováno / rozpracováno / hotovo)
   a chybějícími údaji.
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
4. **Dokončení akce** zkontroluje úplnost a zapíše sidecary.

Našeptávání a kontrola jmen viz výše.

### Ukládání a export

- `_metadata.json` se ukládá průběžně.
- XMP sidecary se zapisují při dokončení akce a samostatným tlačítkem
  Exportovat. **Přepisují se jen změněné:** obsah sidecaru se generuje
  deterministicky (bez časových razítek) a jeho `sha256` se ukládá
  k souboru do `_metadata.json`; sidecar se zapíše, jen když chybí nebo
  se hash liší.
- Před uložením `_metadata.json` aplikace ověří, že ho mezitím nezměnil
  někdo jiný; jinak uložení odmítne a nabídne znovunačtení.

### Souběh

Otevřená akce se zamyká souborem `_metadata.lock` ve složce akce (kdo,
na jakém stroji, od kdy, počitadlo). Druhý uživatel dostane upozornění.

- Držitel zámku průběžně zvyšuje počitadlo (heartbeat, ~1 min), dokud
  je akce otevřená v prohlížeči; při zavření akce zámek smaže.
- Zámek, jehož počitadlo se nezměnilo ~5 min **podle hodin pozorovatele**,
  je opuštěný a jde převzít. Porovnává se obsah, ne čas souboru —
  hodiny strojů a SMB serveru se mohou rozcházet.
- Zavření prohlížeče bez odhlášení: server po výpadku heartbeatu
  z prohlížeče zámek sám uvolní.

Metadata (JPG, mp4) čte a XMP sidecary zapisuje `exiftool`. Náhledy
(320 px do mřížky, 1600 px do lupy) se cachují lokálně mimo archiv —
archiv leží na SMB; lupa si sousední fotky načítá předem. Videa se do
lupy posílají přímo z archivu, jen ke čtení.

Primárně Linux (Fedora). Kolegové na Windows jsou žádoucí, ale ne
priorita: snadné spuštění na Windows se řeší, jen pokud nebude stát
dny práce.
