## 1. Čistá logika (testovatelná)

- [ ] 1.1 Nový modul `static/gestures.js`: rozlišení ťuknutí / dlouhého
  stisku / posunu (500 ms, 10 px) a přejetí vlevo / vpravo / nic
  (50 px, převaha vodorovné složky); ověřit testy
  `tests/js/gestures.test.mjs`

## 2. Rozvržení na úzké obrazovce

- [ ] 2.1 `style.css`: media query < 700 px pro hlavičku (bez cest),
  lišty (zalamování), dlaždice podle šířky, `.wnav` připnutá dole,
  dotykové plochy ≥ 40 px; ověřit v DevTools (412 px) na seznamu,
  Přetřídit, importu, průvodci akce, ploše, nastavení a přihlášení,
  že stránka nejde posunout do strany
- [ ] 2.2 Seznam akcí jako karty na úzké obrazovce; ověřit v DevTools
  412 px a že na 1400 px je tabulka beze změny

## 3. Průvodce importem

- [ ] 3.1 Přehled, cíl, plán a výsledek na úzké obrazovce: souhrn
  nahoře, seznamy souborů sbalené, poškozené soubory jako karty
  s volbou a Smazat; ověřit v DevTools nad importem s poškozeným
  souborem (fixtures z testů kontroly)

## 4. Dotyková plocha

- [ ] 4.1 Dotykový výběr v mřížce (plocha i krok skupin průvodce):
  ťuknutí → lupa (v průvodci jen výběr), dlouhý stisk → režim výběru,
  v něm přepínání a hlavičky oddílů, posun nevybírá, potlačené
  `contextmenu`; myš beze změny; ověřit dotykovou emulací DevTools
  a na telefonu, myší na desktopu
- [ ] 4.2 Lišta režimu výběru (počet, Vyřadit, Upravit (N), Zrušit
  výběr) místo lišty chybějících údajů; ověřit, že Vyřadit dělá totéž
  co Del a Zrušit výběr režim ukončí
- [ ] 4.3 Spodní list: `#panel` na úzké obrazovce jako vysouvací list,
  tlačítko „Upravit akci / skupinu / (N)“, zavírání; položky lišty
  chybějících údajů list otevřou; ověřit uložení autorů tří souborů
  přes list
- [ ] 4.4 Lupa dotykem: přejetí přepíná (v režimu výběru rozšiřuje),
  ťuknutí v pásu vybírá bez opuštění lupy, tlačítko zpět do mřížky,
  `touch-action: pan-y`, video bez zachytávání gesta; ověřit
  na telefonu s fotkou i videem
- [ ] 4.5 Lišta akce na úzké obrazovce: zpět, název, mřížka/lupa,
  Dokončit akci; zbytek v menu „⋯“ (`details`), na desktopu beze
  změny; ověřit na 412 px a 1400 px

## 5. Dokumentace a ověření

- [ ] 5.1 README, oddíl Aplikace: mobilní ovládání (ťuknutí, dlouhý
  stisk, přejetí, list, ⋯)
- [ ] 5.2 `.venv/bin/python -m pytest -q` a
  `node --test tests/js/*.test.mjs` projdou
