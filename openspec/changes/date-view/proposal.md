## Why

Skupiny pomáhají při editaci, ale při prohlížení akce rozhazují fotky:
snímky z různých přístrojů téže chvíle leží daleko od sebe (issue #3).
Chybí pohled, kde jsou všechny soubory akce za sebou podle data.

## What Changes

- Pracovní plocha dostane druhý přepínač **Po skupinách / Podle data**
  vedle přepínače Mřížka / Lupa. Volba platí pro mřížku i filmový pás
  a prohlížeč si ji pamatuje i pro další akce.
- V zobrazení podle data jsou všechny soubory akce v jednom pořadí
  podle data pořízení a rozdělené předěly po kalendářních dnech. Soubory
  bez data jsou na konci v oddílu „Bez data“.
- Klik na hlavičku dne vybere soubory toho dne (jako u „Bez skupiny“).
  Skupina jako celek jde vybrat jen v zobrazení po skupinách.
- V zobrazení podle data nese každá dlaždice v mřížce i v pásu barevný
  proužek své skupiny. Dlaždice v mřížce má navíc název skupiny
  v popisku. Soubor bez skupiny proužek nemá.
- Šipky, Shift-výběr a výběr tažením se řídí aktuálním zobrazeným
  pořadím. Výběr i aktuální soubor zůstanou při přepnutí zachované.
- Průvodce prvním otevřením zůstává po skupinách.

## Capabilities

### New Capabilities

### Modified Capabilities
- `metadata-workspace`: mřížka umí kromě skupin zobrazit soubory podle
  data s předěly po dnech a se značkou skupiny na dlaždici.
- `loupe-view`: filmový pás se řídí zvoleným zobrazením (předěly
  skupin, nebo dnů).

## Impact

- `fotoarchiv/static/app.js` (sestavení oddílů mřížky a pásu, přepínač,
  dlaždice), `fotoarchiv/static/style.css`, nový čistý modul pro
  rozdělení po dnech s testem v `tests/js`.
- `README.md` (Aplikace, pracovní plocha a lupa).
- Server, `_metadata.json` ani sidecary se nemění.
