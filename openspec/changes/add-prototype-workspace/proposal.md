## Why

Návrh v README je odsouhlasený na úrovni datového modelu a toku práce,
ale rozhodnutí o obrazovkách se má dělat nad funkčním prototypem
s reálnými daty, ne nad popisem. Prototyp nad akcí
`2026-04-28 kontrola Stezky Drahanskou vrchovinou` (G9, Samsung, RAW,
video, podsložky) ověří tok „průvodce, pak pracovní plocha“ dřív, než se
staví export a zámky.

## What Changes

- Nová lokální webová aplikace (Python + Flask, čistý JS bez build kroku)
  spouštěná nad složkou archivu.
- Seznam akcí `YYYY-MM-DD *` se stavem a počty souborů.
- Průvodce při prvním otevření akce:
  - úklid **nasucho** — ukáže, co by se stalo s podsložkami a RAWy
    v kořeni (přesun do kořene, přejmenování na `*.ignored` /
    `RAW.ignored`), ale nic nepřesune;
  - načtení metadat přes `exiftool` a návrh skupin podle přístroje
    a vzoru názvu, s možností skupiny upravit;
  - údaje akce předvyplněné z názvu složky a EXIF;
  - autoři skupin.

  Průvodce provede vším, co je pro akci povinné; plocha slouží
  k doplňování a opravám.
- Pracovní plocha: mřížka náhledů po skupinách, formulář podle výběru
  (akce / skupina / soubory) se zděděnými hodnotami a možností je
  přepsat, lišta chybějících údajů.
- Našeptávání a kontrola jmen osob (bez ohledu na diakritiku, velikost
  písmen a pořadí slov).
- Průběžné ukládání `_metadata.json` s kontrolou souběžné změny.
- Prototyp **nezapisuje do archivu**: archiv čte, `_metadata.json`
  ukládá do lokálního pracovního adresáře mimo archiv.

Mimo rozsah (další změny): zápis XMP sidecarů a export, zámek
`_metadata.lock`, skutečné provedení úklidu, CSV index, vzhled.

## Capabilities

### New Capabilities

- `archive-browsing`: nalezení složek akcí v archivu, jejich stav
  a výběr akce ke zpracování.
- `event-cleanup`: rozpoznání podsložek a RAWů v kořeni akce a plán
  úklidu (v prototypu jen náhled bez provedení).
- `media-scan`: čtení metadat souborů přes `exiftool`, datum
  z názvu u WhatsAppu, náhledy s lokální cache, návrh skupin.
- `metadata-model`: `_metadata.json` — struktura, dědění akce → skupina
  → soubor, přepisování na nižší úrovni, ukládání s kontrolou souběžné
  změny.
- `metadata-workspace`: průvodce prvním otevřením a pracovní plocha
  s mřížkou, výběrem, formulářem a lištou chybějících údajů.
- `person-names`: otevřený seznam jmen z archivu, kanonický tvar
  `Příjmení, Jméno` a návrhy oprav při zadávání.

### Modified Capabilities

<!-- žádné, specifikace zatím neexistují -->

## Impact

- Nový kód v repu: balíček `fotoarchiv/` (server, sken, model),
  `fotoarchiv/static/` (HTML/JS/CSS), spouštěcí skript.
- Nové závislosti: Flask, Pillow (`requirements.txt`, venv `.venv/`
  mimo git); systémový `exiftool`; `ffmpeg` pro náhledy videí, pokud
  je dostupný (jinak video bez náhledu).
- Archiv na SMB (`/mnt/x`) se jen čte. Cache náhledů a pracovní kopie
  `_metadata.json` leží lokálně mimo archiv.
