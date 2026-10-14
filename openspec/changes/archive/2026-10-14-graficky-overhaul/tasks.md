## 1. Tokeny a výchozí vzhled (A)

- [x] 1.1 Zavést v `style.css` základní paletu a sémantické tokeny
  (viz design, Dvě vrstvy tokenů) a přepsat na ně všechny barvy
  komponent; ověřit, že `grep -E '#[0-9a-fA-F]{3,6}'` najde hexy jen
  v blocích definic tokenů
- [x] 1.2 Sjednotit komponenty (tlačítka, štítky stavu, čipy, pole,
  dialogy, upozornění, kroky průvodce s čísly a stavem) nad tokeny;
  ověřit ručně na seznamu akcí, průvodci, ploše, importu, nastavení
  a přihlášení
- [x] 1.3 Přidat tmavý režim přes `prefers-color-scheme` pro
  `:root:not([data-vzhled])`; ověřit v Chromu emulací tmavého režimu,
  že náhledy jsou beze změny
- [x] 1.4 Napsat `tests/js/contrast.test.mjs` (kontrast dvojic tokenů
  pro každý vzhled a režim podle WCAG); ověřit
  `node --test tests/js/*.test.mjs`

## 2. Přepínání vzhledu

- [x] 2.1 Vytvořit `static/vzhled.js` (parametr `?vzhled=`,
  `localStorage` v `try/catch`, `data-vzhled` na `<html>`) a načíst ho
  v `<head>` `index.html`, `prihlaseni.html`, `heslo.html` před
  `style.css`; ověřit scénáře požadavku Varianty vzhledu k porovnání
  (zapnutí, přetrvání, `a`, neznámá hodnota) a že stránka neproblikne
- [x] 2.2 Doplnit tokeny varianty B (Temná pracovna) pod
  `:root[data-vzhled="b"]`; ověřit test kontrastu a rozlišitelnost
  barev osob v pruhu autorů na tmavé mřížce
- [x] 2.3 Doplnit tokeny varianty C (Katalogová karta) pod
  `:root[data-vzhled="c"]` včetně `--font-heading` (systémové patkové
  písmo, bez webfontu); ověřit test kontrastu

## 3. Rozvržení plochy

- [x] 3.1 Sloučit `#bar` do lišty akce v `renderWorkspace` (čipy se
  zalamují, akce vpravo ne); ověřit scénáře „Jedna lišta“ a „Mnoho
  položek na úzkém okně“ v okně 1280 × 720 a že klik na čip dál
  vybírá soubory
- [x] 3.2 Přidat posuvník velikosti dlaždic (`--tile`, 100–300 px,
  `localStorage` `dlazdice`, aktuální soubor v zorném poli); ověřit scénáře
  požadavku Velikost dlaždic a výběr tažením při malé i velké velikosti
- [x] 3.3 Panel `clamp(320px, 24vw, 420px)` a jeho sbalení tlačítkem
  a klávesou `P` (ochrana textových polí jako u Del, `localStorage`
  `panel`, v průvodci ne); ověřit scénáře požadavku Skládací panel
  formuláře v mřížce i lupě a že se neztratí neuložená změna
- [x] 3.4 Ověřit požadavek Podporovaná šířka okna: plocha, průvodce
  a import v Chromu při 1280 × 720 a 2560 × 1440 bez vodorovného
  posuvníku, formulář na 2560 stejně široký jako na 1920

## 4. Zdroj hodnoty ve formuláři

- [x] 4.1 Proužek a štítek zdroje u polí (`inherited`, `mixed`, `own`,
  `from-place`, osoby z Immiche) místo kurzívní poznámky; ověřit
  scénář „Štítek zdroje“ u akce, skupiny, jednoho souboru a výběru
- [x] 4.2 Tlačítko „vrátit na zděděné“ u vlastní hodnoty skupiny
  a souborů (týž `update` jako vyprázdnění, vypnuté jen ke čtení);
  ověřit scénáře „Vrácení na zděděné“ a „Vrácení u výběru“ v uloženém
  `_metadata.json` ve `.work/`

## 5. Prototyp k výběru

- [x] 5.1 Spustit aplikaci ve vývojovém režimu nad archivem, projít
  stávající testy (`pytest -q`, `node --test tests/js/*.test.mjs`)
  a předat uživateli odkazy `?vzhled=a|b|c` k porovnání na notebooku
  i velkém monitoru
- [x] 5.2 Zapsat výběr varianty uživatelem a případné úpravy (např.
  „B, ale formulář světlý“) do `design.md`

## 6. Dokončení po výběru

- [x] 6.1 Udělat z vybrané varianty výchozí vzhled, smazat bloky
  ostatních variant, `vzhled.js` a jeho načítání (nebo ho ponechat jen
  pro tmavý/světlý režim, podle výběru v 5.2); ověřit, že
  `?vzhled=` nic nemění a test kontrastu prochází
- [x] 6.2 Upravit požadavek Varianty vzhledu k porovnání v delta specu
  `app-appearance` podle výsledku (odstranit, nebo popsat přepínač
  režimu); ověřit `openspec validate graficky-overhaul --strict`
- [x] 6.3 Aktualizovat README, oddíl Aplikace (jedna lišta, velikost
  dlaždic, sbalení panelu a klávesa `P`, zdroj hodnoty a vrácení na
  zděděné, tmavý režim); ověřit přečtením oproti specům
