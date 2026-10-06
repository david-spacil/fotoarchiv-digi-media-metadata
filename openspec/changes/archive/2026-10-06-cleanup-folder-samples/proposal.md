## Why

V kroku Úklid průvodce u podsložky ukáže jen název a počet souborů
(issue #1). Bez pohledu dovnitř nejde rozhodnout, jestli ji přesunout
mezi soubory akce, nebo ponechat stranou.

## What Changes

- U každé podsložky pás až 8 náhledů rovnoměrně z jejích fotek a videí,
  pod každým název souboru.
- Klik na náhled ho ukáže zvětšený (1600 px).
- Bez fotek a videí ve složce se ukážou jen názvy vybraných souborů.
- Nový endpoint náhledu souboru v podsložce akce; archiv jen čte.

## Capabilities

### New Capabilities

### Modified Capabilities
- `event-cleanup`: nový požadavek „Ukázky obsahu podsložky“.

## Impact

- `fotoarchiv/cleanup.py` (`subfolders` vrací `ukazky`),
  `fotoarchiv/app.py` (endpoint `uklid/nahled`).
- `fotoarchiv/static/app.js` (`renderCleanup`), `style.css`.
- Testy `tests/test_cleanup.py`, `tests/test_app.py`.
- `README.md`, popis kroku Úklid.
