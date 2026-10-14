## 1. Data oddílů

- [ ] 1.1 Přidat do `sections.js` čistou funkci, která z oddílu
  (`files`), výsledku `missing()` a výsledných autorů souborů vrátí
  počty a seznamy chybějících údajů oddílu (bez autorů, bez data, bez
  místa, bez skupiny, skupina bez autorů; bez souborů k vyřazení)
  a autory s počty souborů; ověřit novými testy v
  `tests/js/sections.test.mjs` podle scénářů požadavku Chybějící údaje
  v navigátoru a `node --test tests/js/*.test.mjs`
- [ ] 1.2 Přidat funkci pro úseky pruhu autorů oddílu (poměr souborů,
  tři nejčastější, zbytek šedě, šrafovaný úsek bez autorů); ověřit
  testem scénáře „Pruh autorů oddílu“ (2 : 1)
- [ ] 1.3 Doplnit `sections()` v `app.js` o výsledky 1.1 a 1.2, ať je
  navigátor, mřížka i pás berou z jednoho místa; ověřit, že
  mřížka a pás vypadají jako dřív (ručně na DOD 2015)

## 2. Navigátor

- [ ] 2.1 Vytvořit `static/icons.js` (inline SVG, `currentColor`:
  datum, místo, osoba, skupina, souřadnice, vyřazení, panel,
  mřížka/lupa); ověřit, že se moduly načtou bez chyby v konzoli
- [ ] 2.2 Přidat sloupec navigátoru do rozvržení plochy (vlevo,
  samostatný scroll) s řádkem Akce a řádky oddílů (název, počet, pruh
  autorů, ikonky chybějících údajů s počtem a titulkem slovy); ověřit
  scénáře „Oddíly po skupinách“, „Oddíly podle data“, „Skupina bez
  autorů“, „Jedno místo akce“
- [ ] 2.3 Klik na řádek: Akce zruší výběr, skupina vybere skupinu,
  den/Bez data/Bez skupiny vybere soubory; mřížka skočí na oddíl
  s předělem (`scroll-margin-top`); ověřit scénáře „Výběr skupiny
  z navigátoru“, „Výběr dne z navigátoru“, „Řádek Akce“
- [ ] 2.4 Klik na chybějící údaj vybere dotčené soubory (u skupiny bez
  autorů skupinu), místo bez souřadnic navíc otevře volbu souřadnic;
  ověřit scénáře „Soubory bez data ve skupině“, „Nerozhodnuté místo“
  a že klik funguje i bez zámku
- [ ] 2.5 Vyznačit okrajem viditelné oddíly (IntersectionObserver nad
  sekcemi mřížky); ověřit scénář „Viditelné oddíly“ při posouvání,
  změně velikosti dlaždic a sbalení panelu
- [ ] 2.6 Přesměrovat skoky, které dnes hledají `#grid .ghead`
  (`missingItems()` aj.), na sekce mřížky; ověřit
  `grep -n ghead fotoarchiv/static/app.js` (zbude jen průvodce)

## 3. Mřížka, lišta a dlaždice

- [ ] 3.1 Odstranit hlavičky oddílů z mřížky plochy (průvodce si je
  nechá), mezi oddíly předěl; ověřit scénář „Předěl místo hlavičky“
  a že výběr tažením myši (gumička) dál funguje
- [ ] 3.2 Lišta akce bez chybějících údajů (zůstanou nálezy, počet
  k vyřazení, ovládání); ověřit scénáře požadavku Lišta akce v okně
  1280 px
- [ ] 3.3 Dlaždice bez popisku: pruh autorů dole, ikony bez data /
  bez místa / vyřazení v rohu, překryv s názvem, datem a příjmením
  autorů při najetí i fokusu; ověřit scénáře požadavku Značka autorů
  na dlaždici a požadavek Velikost dlaždic (8 na řádek při 1280 px
  s panelem a navigátorem)
- [ ] 3.4 Nahradit ikonami textová tlačítka lišty, kde je text zbytný
  (panel, mřížka/lupa), s `aria-label` a `title`; ověřit klávesnicí
  a test kontrastu `node --test tests/js/contrast.test.mjs`

## 4. Přesun tažením

- [ ] 4.1 Tažení dlaždice (celý výběr, nebo jen tažený soubor) na řádek
  skupiny přes `moveFiles()` a `dropEmptyGroups()`; ostatní řádky
  tažení odmítnou a jsou odlišené; bez zámku dlaždice nejdou táhnout;
  ověřit scénáře požadavku Přesun do skupiny tažením včetně prázdné
  skupiny se zadanými údaji

## 5. Lupa

- [ ] 5.1 Navigátor v lupě: klik na oddíl udělá první soubor aktuálním
  a jediným vybraným, pás ho ukáže; okraj u oddílu aktuálního souboru;
  ověřit scénáře požadavku Navigátor v lupě

## 6. Dokumentace a ověření

- [ ] 6.1 Aktualizovat `README.md`, oddíl Aplikace (navigátor, lišta
  akce, dlaždice s překryvem, tažení do skupiny); ověřit, že README
  nezmiňuje lištu chybějících údajů ani hlavičky skupin na ploše
- [ ] 6.2 Projít plochu na DOD 2015 a jedné velké akci ve vývojovém
  režimu v obou režimech vzhledu (tmavý, světlý), zobrazení po
  skupinách i podle data, mřížka i lupa; spustit
  `.venv/bin/python -m pytest -q` a `node --test tests/js/*.test.mjs`
