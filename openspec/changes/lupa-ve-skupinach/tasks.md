## 1. Čistá logika pohybu

- [x] 1.1 `vLupeKroku(order, current, klavesa)` v `static/pohyb.js`:
  ←/→ ±1 bez přetečení, Home/End kraje, ostatní klávesy (↑/↓,
  PageUp/PageDown, Shift, Ctrl+A) `null`; bez aktuálního první soubor
- [x] 1.2 Testy v `tests/js/pohyb.test.mjs` (přes hranici skupin,
  kraje, ignorované klávesy, prázdné pořadí); `node --test
  tests/js/*.test.mjs` hlásí nenulový počet testů

## 2. Okno lehké lupy

- [x] 2.1 Funkce `stepLoupe(f)` v `static/app.js`: `<dialog
  class="steploupe">` s malým náhledem vyměněným za 1600 px,
  přednačtení sousedů ±1, popisek (název · i / N · video · vyloučeno),
  tlačítka ‹ › ×, v importu tlačítko Vyloučit / Vrátit do importu;
  zavření Esc, × a klikem na pozadí; po zavření `revealCurrent`
- [x] 2.2 Vlastní `keydown` okna přes `vLupeKroku`; nic, je-li nad
  oknem jiný dialog (dotaz na RAWy); Del jen v importu přes
  `toggleExcluded()` a překreslení stavu
- [x] 2.3 Otevření: Enter v globální obsluze kroku (místo „nic“),
  dvojklik na dlaždici v režimech `wizard` a `import`, tlačítko „Lupa“
  s ikonou v `groupTools` (aktuální, jinak první vybraný v pořadí)
- [x] 2.4 CSS `dialog.steploupe` v `static/style.css`: tmavé v obou
  režimech, fotka v rámci okna, vyloučený zašedlý, ovladatelné
  na úzké obrazovce

## 3. Dokumentace

- [x] 3.1 `docs/navod/import.md` (krok Skupiny a autoři) a
  `docs/navod/pruvodce-akce.md`: Enter / dvojklik / tlačítko Lupa,
  pohyb, Del v lupě importu, video jen náhled; P dál nic

## 4. Ověření

- [x] 4.1 Celé testy Pythonu a JS (baseline před změnou, po změně)
- [x] 4.2 Prohlížeč na dummy datech (generovaná akce a import
  v scratch, žádná reálná data): scénáře z delta specifikací (Enter,
  dvojklik, tlačítko, šipky přes skupinu a kraj, Esc a pozice mřížky,
  Del bez RAWu i s RAWem, Del v průvodci, video, P), světlý i tmavý
  režim, úzké okno ~400 px; lupa plochy beze změny. **Ručně
  neověřeno:** dotyk na skutečném telefonu (jen emulace šířky 400 px:
  okno se vejde, nic nepřetéká)
- [ ] 4.3 Ruční zkouška uživatelem na reálném importu
