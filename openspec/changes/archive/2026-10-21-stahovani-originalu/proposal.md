## Why

Originály fotek a videí jde dnes z aplikace jen prohlížet v lupě;
stáhnout soubor, výběr nebo celou akci znamená ruční zásah na NAS.
Uživatel potřebuje originály předat dál (zpráva, publikace) i s popisem
z archivu. Issue #53.

## What Changes

- Na pracovní ploše akce tlačítko **Stáhnout** pro výběr souborů:
  jeden vybraný soubor se stáhne jako originál, víc vybraných jako ZIP.
  Ruční výběr se stáhne celý, i soubory označené k vyřazení.
- V přehledu akcí na každé kartě **ikona stažení** (mráček se šipkou
  dolů, bez textu), která stáhne ZIP celé akce: média z kořene akce
  bez označených k vyřazení.
- ZIP obsahuje kromě médií i `_metadata.json` akce a **XMP sidecary**
  stažených médií. Sidecary se generují v paměti z aktuálního
  `_metadata.json` (stejný obsah jako při exportu, bez oblastí
  obličejů), takže odpovídají JSONu v ZIPu i u rozpracované akce.
  Akce bez `_metadata.json` dá ZIP jen s médii.
- ZIP se streamuje bez komprese; na serveru nevzniká dočasný soubor
  a velikost akce není omezená.
- Stažení jen čte: nepotřebuje zámek ani roli (stačí přihlášení),
  funguje i u nedokončené akce (`.ignored`) a nic nezapisuje do
  archivu ani do `.work`.
- Mobilní ovládání (změna `mobilni-verze`) se neřeší.

## Capabilities

### New Capabilities

- `event-download`: stažení originálů akce — jednoho souboru, výběru
  a celé akce jako ZIP s `_metadata.json` a sidecary; obsah ZIPu,
  vstupní body na ploše a v přehledu akcí, oprávnění.

### Modified Capabilities

<!-- Žádné: stažení je nové chování nad stávajícími obrazovkami;
     požadavky seznamu akcí a pracovní plochy se nemění. -->

## Impact

- `fotoarchiv/app.py`: stažení originálu jako přílohy a endpoint ZIPu
  (GET celá akce, POST výběr); nový pomocný modul pro streamovaný ZIP.
- `fotoarchiv/xmp.py`: využití `sidecar()` bez zápisu na disk.
- Klient `fotoarchiv/static/`: tlačítko pro výběr (`app.js`), ikona
  `stahnout` (`icons.js`) na kartě akce, styly.
- Testy Pythonu (obsah ZIPu, výběr, vyřazené, akce bez JSONu, cesty
  mimo kořen) na dummy archivu.
- `docs/navod/` (seznam akcí, pracovní plocha), `README.md` oddíl
  Aplikace.
- Bez nových závislostí (`zipfile` ze standardní knihovny).
