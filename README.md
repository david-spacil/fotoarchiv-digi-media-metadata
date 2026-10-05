# fotoarchiv-digi-media-metadata

Průvodce obohacením metadat digitální fotodokumentace ARÚB
(`FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB`). Lokální webová
aplikace s náhledy, ve které se fotkám a videím přiřazují metadata
jednotlivě nebo po skupinách.

Stav: **návrh**, zatím bez kódu.

## Archiv

- Na první úrovni složky akcí `YYYY-MM-DD název`, bez dalšího zanoření.
- Složky `přetřídit` a `přednášky SKLEP TIC` se nezpracovávají.
- Ve složkách jsou JPG, mp4, občas png/zip a `Thumbs.db` (ignorovat).
- Zdroje se liší kvalitou metadat:

  | vzor názvu            | přístroj          | EXIF                   |
  |-----------------------|-------------------|------------------------|
  | `P*.JPG`              | Panasonic DC-G9   | datum, bez GPS         |
  | `YYYYMMDD_HHMMSS.jpg` | Samsung SM-A528B  | datum, GPS             |
  | `IMG-YYYYMMDD-WA*.jpg`| WhatsApp          | žádný, datum jen v názvu |
  | `IMG_####.jpg`        | ?                 | neověřeno              |

## Datový model

Zdroj pravdy je **jeden `_metadata.json` v každé složce akce**. Vše
ostatní (XMP sidecary, index) se z něj generuje.

Hodnoty se dědí **akce → skupina → soubor**; nižší úroveň přepisuje
vyšší. Skupiny průvodce navrhne automaticky podle přístroje a vzoru
názvu, uživatel je může upravit.

```json
{
  "schema": "fotoarchiv-digi-media-metadata/1",
  "akce": {
    "nazev": "kontrola Stezky Drahanskou vrchovinou",
    "popis": "…",
    "datum_od": "2026-04-28",
    "datum_do": "2026-04-28",
    "misto": ["Vysočany", "Holštejn"],
    "osoby": ["Spáčil, David", "Kopáčová, Zuzana"],
    "projekt": "R300012402"
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
      "popis": "…",
      "osoby": ["…"],
      "sha256": "…"
    }
  }
}
```

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
  s rozepsanými zděděnými hodnotami (`dc:creator`, `dc:description`,
  datum, GPS, osoby). Generují se z `_metadata.json`, ručně se
  needitují.
  - K ověření: jak Immich načítá osoby ze sidecaru. Nejspíš z oblastí
    obličejů, ne z `Iptc4xmpExt:PersonInImage`; osoby proto možná
    exportovat i jako tagy.
- **Index** celého archivu (CSV, jeden řádek na akci) nahrazuje ručně
  vedený `_metadata.xlsx`. Generuje se, needituje.

## Aplikace

Lokální webová aplikace spouštěná nad složkou archivu:

- mřížka náhledů akce, výběr jednotlivě, myší nebo celé skupiny;
- formulář vedle mřížky pro akci, skupinu nebo vybrané soubory;
- našeptávání a kontrola jmen (viz výše);
- uložení do `_metadata.json`, export sidecarů a indexu.

Primárně Linux (Fedora). Kolegové na Windows jsou žádoucí, ale ne
priorita: snadné spuštění na Windows se řeší, jen pokud nebude stát
dny práce.
