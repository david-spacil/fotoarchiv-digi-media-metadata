## Why

Skupiny pomáhají při editaci, ale při prohlížení akce rozhazují fotky:
snímky z různých přístrojů téže chvíle leží daleko od sebe (issue #3).
Chybí pohled, kde jsou všechny soubory akce za sebou podle data.
V žádném zobrazení navíc není vidět, kdo které fotky mohl pořídit a kde
autoři chybí.

## What Changes

- Pracovní plocha dostane druhý přepínač **Po skupinách / Podle data**
  vedle přepínače Mřížka / Lupa. Volba platí pro mřížku i filmový pás
  a prohlížeč si ji pamatuje i pro další akce.
- V zobrazení podle data jsou všechny soubory akce v jednom pořadí
  podle data pořízení a rozdělené předěly po kalendářních dnech. Soubory
  bez data jsou na konci v oddílu „Bez data“.
- Klik na hlavičku dne vybere soubory toho dne (jako u „Bez skupiny“).
  Skupina jako celek jde vybrat jen v zobrazení po skupinách.
- Šipky, Shift-výběr a výběr tažením se řídí aktuálním zobrazeným
  pořadím. Výběr i aktuální soubor zůstanou při přepnutí zachované.
- V obou zobrazeních nese dlaždice v mřížce i v pásu pruh podle
  výsledných (zděděných) autorů. Každá osoba akce má vlastní barvu
  a pruh se dělí na úseky v barvách autorů, nejvýš tři barevné, další
  autoři jako jeden šedý úsek. Soubor bez autorů má šrafovaný pruh,
  soubor k vyřazení žádný. Popisek dlaždice v mřížce uvede příjmení
  autorů s barvou.
- Průvodce prvním otevřením zůstává po skupinách a bez značek.

## Capabilities

### New Capabilities

### Modified Capabilities
- `metadata-workspace`: mřížka umí kromě skupin zobrazit soubory podle
  data s předěly po dnech; dlaždice nese značku autorů.
- `loupe-view`: filmový pás se řídí zvoleným zobrazením (předěly
  skupin, nebo dnů) a nese značky autorů.

## Impact

- `fotoarchiv/static/app.js` (sestavení oddílů mřížky a pásu, přepínač,
  dlaždice a jejich značky), `fotoarchiv/static/style.css`, nový čistý
  modul pro rozdělení po dnech a barvy značek s testem v `tests/js`.
- `README.md` (Aplikace, pracovní plocha a lupa).
- Server, `_metadata.json` ani sidecary se nemění.
