## Why

Import podsložky zploští a o skupinách nerozhoduje: u nové akce je
navrhne až průvodce podle přístroje a vzoru názvu, u stávající akce
skončí nové soubory „bez skupiny“. Podsložky ale často nesou dělení od
autora (např. `přetřídit/DOD 2015/DOD 2015_Jana`, `…_Pavla` = kdo
fotil) a dávka přidaná do stávající akce je obvykle sama o sobě
skupinou. Obojí se dnes musí na ploše dělat ručně.

## What Changes

- Průvodce importu se v kroku cíle zeptá, jak importované soubory
  rozdělit do skupin:
  - **podle podsložek** (jen má-li výběr podsložky): skupina = podsložka,
  - **jedna nová skupina** pro celý import,
  - **automaticky** podle přístroje a vzoru názvu,
  - **bez skupiny**,
  - **zařadit do skupiny …** (jen stávající akce se skupinami).
- Předvolba: podsložky → podle podsložek; jinak nová akce (nebo akce
  bez `_metadata.json`) → automaticky, stávající akce → jedna nová
  skupina.
- Plán importu ukáže, do jaké skupiny který soubor půjde.
- Akce s `_metadata.json`: import po přenosu zapíše skupiny a přiřazení
  přenesených souborů rovnou do `_metadata.json` (pod zámkem, který při
  provedení už drží).
- Akce bez `_metadata.json`: import uloží návrh skupin do pracovního
  adresáře; průvodce prvním otevřením ho použije místo automatického
  návrhu (pro soubory, které v návrhu nejsou, dál automaticky).

## Capabilities

### New Capabilities

(žádné)

### Modified Capabilities

- `photo-import`: volba skupin v průvodci, skupiny v plánu, zápis skupin
  nebo návrhu skupin při provedení.
- `metadata-workspace`: průvodce prvním otevřením přebírá návrh skupin
  z importu.

## Impact

- `fotoarchiv/importer.py` (rozdělení do skupin podle `cesta`, návrh
  v `.work/`), `fotoarchiv/app.py` (`/api/import/<id>/plan`,
  `/provest`, `/api/akce/<nazev>` u nové akce), `fotoarchiv/model.py`
  (sloučení skupin do dokumentu), `fotoarchiv/scan.py`
  (`propose_groups` pro podmnožinu souborů).
- `fotoarchiv/static/app.js`: krok cíle a plán importu.
- README (Import, Tok práce), testy `tests/test_import*.py`.
- Bez nových závislostí.
