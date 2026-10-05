## Why

Metadata akcí zatím žijí jen v `_metadata.json`, který Immich nečte.
Bez XMP sidecarů nejde archiv napojit do Immiche a akci nejde dokončit.

## What Changes

- Generátor XMP sidecaru pro každý soubor akce (`foto.jpg.xmp` vedle
  souboru) z rozepsaných (zděděných) hodnot podle mapování v README,
  doplněný o tag `akce/<složka akce>`. Výstup je deterministický
  (skládaný v Pythonu, bez časových razítek a verze nástroje).
- `datum` bez zóny dostane zónu Europe/Prague podle data (zimní/letní
  čas).
- Sidecar se zapíše, jen když chybí nebo se obsah liší.
- Na pracovní ploše tlačítka **Dokončit akci** (kontrola úplnosti,
  export, `dokonceno`) a **Exportovat**. Nahrazuje upozornění, že
  prototyp nedokončuje ani neexportuje.
- CLI `python -m fotoarchiv exportovat` pro dávkový export jedné nebo
  všech akcí (např. po změně mapování).
- Ve vývojovém režimu jdou sidecary do `.work/xmp/<akce>/`, do archivu
  jen s `--zapis-do-archivu`.
- **Odchylka od README:** `sha256` sidecaru se neukládá do
  `_metadata.json`; změna se pozná porovnáním s obsahem sidecaru na disku.

## Capabilities

### New Capabilities

- `xmp-export`: obsah sidecaru, zápis jen změněných, umístění podle
  režimu, dávkový export.

### Modified Capabilities

- `metadata-workspace`: dokončení akce a export místo upozornění
  prototypu.
- `archive-browsing`: počet souborů akce nezapočítává sidecary.

## Impact

- Nový modul `fotoarchiv/xmp.py`; `app.py` (endpointy exportu
  a dokončení), `__main__.py` (podpříkaz `exportovat`), `archive.py`
  (počítání souborů, cesta exportu).
- `static/app.js` (tlačítka, výsledek exportu).
- `README.md` (Výstupy, Ukládání a export, Příkazy v `AGENTS.md`).
- `zoneinfo` ze standardní knihovny; na Windows navíc balíček `tzdata`
  (jen pro Windows v `requirements.txt`).
- Navazuje `discard-files`: sidecar vyřazeného souboru.
