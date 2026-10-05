## 1. Kostra projektu

- [ ] 1.1 Založit `requirements.txt` (Flask, Pillow, pytest), `.gitignore`
  (`.venv/`, `.work/`, `__pycache__/`) a balíček `fotoarchiv/`; ověřit,
  že `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
  projde.
- [ ] 1.2 Spouštěcí skript `python -m fotoarchiv --archiv … --work .work`
  s Flask serverem a prázdnou stránkou; ověřit, že `curl` na `/` vrátí
  HTML a že bez existující cesty archivu skript skončí srozumitelnou
  chybou.

## 2. Archiv a model

- [ ] 2.1 Seznam akcí (vzor `YYYY-MM-DD *`, počet souborů bez
  `Thumbs.db`, stav podle `_metadata.json` a `dokonceno`) a endpoint
  `/api/akce`; ověřit pytestem nad dočasným adresářem a `curl` nad
  reálným archivem.
- [ ] 2.2 Čtení a atomické uložení `_metadata.json` v pracovním adresáři
  s `version` (sha256) a odpovědí 409 při neshodě; ověřit pytestem
  (nový soubor, úspěšné uložení, konflikt, archiv beze změny).
- [ ] 2.3 Dědění akce → skupina → soubor v Pythonu a fixtury
  `tests/fixtures/inheritance/*.json` (přepsání autorů u souboru,
  zrušení přepsání, pole jen na akci); ověřit pytestem.

## 3. Úklid nasucho

- [ ] 3.1 Plán úklidu (podsložky bez `.ignored`, většina RAWů →
  `RAW.ignored`, RAWy z kořene, kolize jako `blocked`, existující
  `RAW.ignored`) a endpoint; ověřit pytestem na scénářích ze spec
  `event-cleanup` a `curl` nad akcí 2026-04-28 (čekáno: `RAW`
  → `RAW.ignored`, `Video` k rozhodnutí).

## 4. Sken a náhledy

- [ ] 4.1 Sken kořene akce jedním voláním `exiftool` (filtrování přípon,
  datum z WhatsApp názvu, `QuickTimeUTC`, cache podle názvu, velikosti
  a mtime); ověřit pytestem na parsování výstupu a ručně nad akcí
  2026-04-28 (datum G9, GPS Samsung, datum mp4 v místním čase).
- [ ] 4.2 Návrh skupin podle přístroje a vzoru názvu; ověřit pytestem
  (dva přístroje → dvě skupiny, WhatsApp bez přístroje → skupina podle
  vzoru).
- [ ] 4.3 Opakovaný sken: nové soubory bez skupiny, chybějící označené,
  ruční údaje zachované; ověřit pytestem.
- [ ] 4.4 Náhledy (Pillow s `draft` a EXIF orientací, `ffmpeg` pro
  video, zástupná ikona) s cache v `.work/cache/thumbs/`; ověřit, že
  druhé načtení akce nečte originály (počet volání v testu / čas
  v ručním běhu).

## 5. Jména osob

- [ ] 5.1 Normalizace, seznam jmen z `_metadata.json` (pracovní adresář
  i archiv), našeptávání, „Mysleli jste“ a převod `Jméno Příjmení`
  → `Příjmení, Jméno`; ověřit pytestem na scénářích ze spec
  `person-names`.

## 6. Klient

- [ ] 6.1 Seznam akcí a směrování průvodce / plocha podle stavu;
  ověřit v prohlížeči nad archivem.
- [ ] 6.2 Průvodce: krok úklid (zobrazení plánu, volby u podsložek),
  krok skupiny (přejmenovat, sloučit, nová, přesun souborů), krok údaje
  akce s předvyplněním, krok autoři skupin (pole jmen z 5.1); ověřit
  v prohlížeči nad akcí 2026-04-28.
- [ ] 6.3 Dědění v JS a `node --test` proti fixturám z 2.3; ověřit, že
  testy projdou.
- [ ] 6.4 Plocha: mřížka po skupinách, výběr (klik, Ctrl, Shift,
  tažení, hlavička skupiny); ověřit v prohlížeči.
- [ ] 6.5 Formulář podle výběru se zděděnými hodnotami, přepsáním,
  vrácením a vyznačením rozdílných hodnot; pole jmen s našeptáváním
  a „Mysleli jste“; ověřit v prohlížeči.
- [ ] 6.6 Průběžné ukládání (debounce) a dialog při 409; ověřit ručně
  úpravou `_metadata.json` v jiném editoru během práce.
- [ ] 6.7 Lišta chybějících údajů s výběrem dotčených položek; ověřit
  v prohlížeči.

## 7. Ověření celku

- [ ] 7.1 Projít celý tok nad akcí 2026-04-28 od seznamu po vyplněné
  údaje, znovu otevřít a zkontrolovat zachování; ověřit, že archiv je
  beze změny (`find -newer` na čas spuštění) a že `pytest` i
  `node --test` projdou.
- [ ] 7.2 Doplnit do `AGENTS.md` příkazy (instalace, spuštění, testy,
  jeden test) a do README stav „prototyp“.
