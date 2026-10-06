## 1. Rozdělení po dnech

- [x] 1.1 Vytvořit `fotoarchiv/static/sections.js` s `byDay(files,
  dateOf)` a `dayLabel(day)` podle design.md; ověřit novým testem
  `tests/js/sections.test.mjs` (víc dnů, datum bez času před časy,
  shoda času → název, soubory bez data na konci, `út 28. 4. 2026`)
  přes `node --test tests/js`

## 2. Zobrazení na ploše

- [x] 2.1 `state.layout` z `localStorage` (výchozí `skupiny`)
  a přepínač Po skupinách / Podle data v `.eventbar`; ověřit, že volba
  přežije reload a otevření jiné akce
- [x] 2.2 `sections()` vrací v pracovní ploše při `datum` oddíly dnů
  (průvodce vždy skupiny); hlavičky dnů v mřížce i pásu s datem
  a počtem; klik na hlavičku vybere soubory oddílu; ověřit v prohlížeči
  na testovacím archivu (scénáře Zobrazení podle data a Dny v pásu)
- [x] 2.3 Barevný proužek skupiny (`--gc`, paleta 8 barev) a název
  skupiny v popisku dlaždice jen v zobrazení podle data, styly
  v `style.css`; ověřit scénáře Značka skupiny v prohlížeči
- [x] 2.4 Přepnutí zachová výběr a aktuální soubor, zruší vybranou
  hlavičku skupiny; šipky a Shift-výběr jdou přes dny; ověřit scénáře
  Přepnutí s výběrem, Rozsah v zobrazení podle data a Šipka přes dny
- [x] 2.5 Aktualizovat `README.md` (Aplikace → Tok práce, pracovní
  plocha a lupa) o přepínač a zobrazení podle data

## 3. Testovací archiv a integrace

- [x] 3.1 Vygenerovat testovací archiv mimo repozitář (scratch): akce
  se dvěma skupinami/přístroji, dvěma dny, WhatsApp souborem bez času,
  souborem bez data, souborem bez skupiny a vyřazeným souborem;
  ověřit, že ho server načte ve vývojovém režimu
- [x] 3.2 Projít v prohlížeči všechny scénáře změny na testovacím
  archivu včetně průvodce u nové akce; `node --test tests/js`
  a `pytest -q` zelené
