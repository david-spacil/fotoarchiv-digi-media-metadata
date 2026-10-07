## Why

Ve složce `přetřídit` v kořeni archivu čeká po zploštění a deduplikaci
(issue #5) 36 nezatříděných akcí. Dnešní import umí jen nahrát soubory
z prohlížeče do `.work/import/`: složky by se musely stáhnout přes VPN
a nahrát zpět, v archivu by vznikly kopie a z `přetřídit` by nebylo
poznat, co je hotové.

## What Changes

- Nová stránka **Přetřídit** (odkaz ze seznamu akcí): tabulka složek
  první úrovně `přetřídit` — počty fotek, videí, RAWů a ostatních
  souborů, podsložky, rozsah dat z EXIF, datum z názvu, navržená akce
  `YYYY-MM-DD název`. Údaje z EXIF se cachují; výpočet ukazuje průběh.
  Složky s příponou `.ignored` (`_duplicity.ignored`) se nenabízejí.
- Klik na složku založí import se **zdrojem ve složce `přetřídit`**
  (bez nahrávání) a otevře průvodce na přehledu s předvyplněnou novou
  akcí. Totéž jde zvolit v kroku Soubory průvodce („ze složky
  přetřídit“).
- Jednotka importu je celá složka první úrovně. Její podsložky se berou
  jako dnes u nahrané složky (zploštění, skupiny podle podsložek, RAWy
  do `RAW.ignored/`); podsložky `*.ignored` ve zdroji se přeskočí.
- Provedení importu ze zdroje soubory **přesouvá** (přejmenování na
  stejném svazku), nekopíruje. Duplicity, blokované a nepodporované
  soubory zůstanou ve zdroji. Vyprázdněné podsložky a zdrojová složka
  (prázdné, nebo jen s `Thumbs.db`) se smažou; složka se zbytky
  v přehledu zůstane.
- Zdrojovou složku během provedení drží zámek, aby ji dva importy
  nepřesouvaly souběžně.
- Ve vývojovém režimu přehled i plán fungují, provedení ne (archiv
  zůstává jen ke čtení).

## Capabilities

### New Capabilities

- `unsorted-import`: přehled složky `přetřídit`, import ze zdrojové
  složky v archivu přesunem, úklid zdroje a zámek zdroje.

### Modified Capabilities

- `photo-import`: průvodce má kromě nahrání druhý zdroj souborů
  (složka v `přetřídit`); výsledek a zahození importu se zdrojem
  v archivu nemažou nic z pracovního adresáře ani ze zdroje.
- `archive-browsing`: složka `přetřídit` přestává být nedotknutelná
  (mění ji import), seznam akcí odkazuje na stránku Přetřídit.

## Impact

- `fotoarchiv/importer.py` (záznam importu se zdrojem, plán nad
  soubory zdroje, přesun místo kopie, úklid prázdných složek),
  nový modul pro přehled `přetřídit` (výpis, data z názvu, cache),
  `fotoarchiv/app.py` (endpointy přehledu a založení importu ze zdroje,
  zámek zdroje), `fotoarchiv/static/app.js` (stránka Přetřídit, krok
  Soubory), `README.md` (Archiv, Import, Souběh).
- Mění se jen cesty souborů v `přetřídit` (Immich ji vynechává),
  obsah originálů ne. Přesun nikdy nepřepíše existující soubor.
- Nová závislost žádná.
