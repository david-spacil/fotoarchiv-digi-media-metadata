## 1. Čisté funkce

- [x] 1.1 Vytvořit `fotoarchiv/static/obliceje.js` s převodem
  `oblast` → `{left, top, width, height}` v procentech a rozdělením
  jmen vybraných souborů na „na aktuální fotce“ a ostatní (seřazené
  podle `localeCompare(…, "cs")`), s hlavičkovým komentářem jako
  u `pohyb.js`.
- [x] 1.2 Napsat `tests/js/obliceje.test.mjs`: `[0.5, 0.4, 0.1, 0.2]`
  → left 45 %, top 30 %, 10 % × 20 %; osoba dvakrát na fotce (jedno
  jméno); výběr dvou fotek (jméno z druhé mezi ostatními); soubor bez
  `obliceje`. `node --test tests/js/*.test.mjs` projde.

## 2. Rámečky v lupě

- [x] 2.1 V `renderBig` zabalit fotku do `.frame` s `aspect-ratio`
  z prvního načteného náhledu a vložit rámečky `.face[data-jmeno]`
  se štítkem; video, chybějící soubor a zástupné texty beze změny.
  Ověření: v lupě s dummy akcí (fotka s `obliceje`) jsou rámečky na
  obličejích při kurzoru nad fotkou, mimo fotku ne.
- [x] 2.2 CSS v `style.css`: `.media` `container-type: size`, `.frame`
  se šířkou `min(100cqw, 100cqh * W / H)`, skrytý rámeček, ukázání
  přes `.frame:hover` a `.focus-name .face.hl`, štítek jen u rámečku
  pod kurzorem, barvy z tokenů lupy. Ověření: zúžení okna a přepnutí
  na fotku na výšku i na šířku nechá rámečky na obličejích; fotka bez
  obličejů vypadá jako dřív.
- [x] 2.3 Ověřit otočenou fotku: dummy JPEG s EXIF orientací 6
  a `oblast` vůči otočené fotce má rámeček na značce (ručně v lupě).

## 3. Propojení s formulářem

- [x] 3.1 `facesRow`: jména jako `<span data-jmeno>`; v lupě s víc
  vybranými soubory ztlumit (`.off`) jména mimo aktuální fotku;
  překreslit při přepnutí mřížka/lupa. Ověření: scénáře „Výběr dvou
  fotek“ a „Mřížka“ ze specu.
- [x] 3.2 Najetí na jméno (ne `.off`) ukáže jen rámečky toho jména,
  najetí na rámeček zvýrazní jméno ve formuláři; odjetí vše vrátí.
  Ověření: scénáře „Najetí na jméno“, „Osoba na fotce dvakrát“,
  „Najetí na rámeček“ a „Najetí na ztlumené jméno“.
- [x] 3.3 Přechod šipkou na další fotku s kurzorem nad fotkou ukáže
  rámečky nové fotky a formulář ztlumení přepočítá.

## 4. Dokumentace a kontrola

- [x] 4.1 Popsat rámečky v lupě v `docs/navod/pracovni-plocha.md`.
- [x] 4.2 `node --test tests/js/*.test.mjs` a `.venv/bin/python -m
  pytest -q` projdou; `tests/js/contrast.test.mjs` pokrývá nové
  dvojice barev, pokud přibyly tokeny.

## Workflow follow-up

- Po implementaci `/opsx:archive ramecky-obliceju` (sync specu
  `loupe-view`).
