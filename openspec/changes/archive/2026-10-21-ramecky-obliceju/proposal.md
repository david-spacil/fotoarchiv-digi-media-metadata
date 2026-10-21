## Why

Formulář souboru ukazuje jména osob z Immiche jen jako text, takže při
popisu fotky není vidět, kdo je kdo. Polohy obličejů už jsou
v `_metadata.json` (`obliceje[].oblast`), aplikace je ale nezobrazuje.
Issue #50.

## What Changes

- Lupa ukáže kolem pojmenovaných obličejů aktuální fotky rámečky,
  jen když je kurzor nad fotkou nebo nad jménem osoby ve formuláři;
  jinak fotka zůstane čistá.
- Najetí na rámeček ukáže u rámečku štítek se jménem a zvýrazní to
  jméno ve formuláři.
- Najetí na jméno ve formuláři ukáže a zvýrazní jen rámečky té osoby
  na aktuální fotce.
- Ve výběru více souborů formulář v lupě odliší (ztlumí) jména, která
  na aktuální fotce nejsou; na ně najetí nic neukáže.
- Rámečky sedí na fotce i po změně velikosti okna a u fotek s EXIF
  orientací.
- Mřížka, video a dotykové ovládání se nemění. Data, API ani server
  se nemění; rámečky se berou z načteného `_metadata.json`.

## Capabilities

### New Capabilities

(žádné)

### Modified Capabilities

- `loupe-view`: nový požadavek „Rámečky obličejů“ — zobrazení
  rámečků v lupě a propojení se jmény ve formuláři.

## Impact

- `fotoarchiv/static/app.js`: `renderBig` (obal fotky s rámečky),
  `facesRow` (jména jako samostatné položky, ztlumení, hover).
- Čistá logika (převod `oblast` na pozici rámečku, jména na aktuální
  fotce) v malém modulu s testy v `tests/js/`.
- `fotoarchiv/static/style.css`: obal fotky, rámeček, štítek,
  zvýraznění jména.
- `docs/navod/pracovni-plocha.md`: popis rámečků v lupě.
- Archiv, `_metadata.json`, sidecary, Immich ani server se nemění.
