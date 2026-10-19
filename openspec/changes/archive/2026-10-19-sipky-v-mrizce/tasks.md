## 1. Čisté funkce pohybu

- [x] 1.1 Vytvořit `fotoarchiv/static/pohyb.js` s funkcemi `klavesa`,
  `radek`, `stranka`, `oddil` a `naPas` (viz design) a hlavičkovým
  komentářem jako u `fronta.js`.
- [x] 1.2 Napsat `tests/js/pohyb.test.mjs` podle scénářů:
  pět sloupců a skupina se sedmi soubory (ze 4. dolů na 7., ze 7. dolů
  na 2. soubor další skupiny, z 12. nahoru na 7.), shoda vzdálenosti
  (levější), jediný řádek (bez pohybu), stránka o čtyři řádky (3.
  sloupec 1. řádku → 3. sloupec 5. řádku) i za koncem (poslední řádek),
  oddíly v lupě (dolů na další, nahoru uprostřed a na začátku oddílu),
  `naPas` (10 souborů na pás, nejméně 1) a `klavesa` (Ctrl+A i Cmd+A,
  Alt+šipka → `null`, Shift se předá).
- [x] 1.3 `node --test tests/js/*.test.mjs` projde a výpis ukazuje
  počet testů včetně nových.

## 2. Pohyb a výběr v mřížce i v lupě

- [x] 2.1 V `app.js` nahradit `step` funkcí `moveTo(f, extend)`
  (výběr, kotva, výchozí soubor bez aktuálního) a napojit na ni
  vodorovný pohyb v mřížce i v lupě.
- [x] 2.2 Rozšířit handler kláves: v mřížce šipky nahoru/dolů
  (`radek`), PageUp/PageDown (`stranka`, výška `#grid`), Home/End;
  v lupě nahoru/dolů (`oddil`) a PageUp/PageDown (`naPas`, šířka
  `#film` a dlaždice pásu); všude Ctrl+A.
- [x] 2.3 Po pohybu v mřížce fokus na aktuální dlaždici
  (`preventScroll`) a `scrollIntoView({ block: "nearest" })`.
- [x] 2.4 Handler pustit i v kroku „Skupiny a autoři“ (`wizard`,
  `import` s `#grid`): pohyb, Ctrl+A, Esc; Delete, Enter a P jen na
  ploše. Dlaždicím kroku přidat `tabindex="0"`.

## 3. Vyznačení aktuálního souboru

- [x] 3.1 Třída `current` na `#grid .tile` v `tile()` i `select()`.
  `focusin` na `#grid` udělá fokusovanou dlaždici aktuální bez změny
  výběru.
- [x] 3.2 Token `--current` pro tmavý i světlý režim a pravidlo
  `.tile.current` (vnitřní stín) ve `style.css`. Dvojice `--current`
  proti `--tile-surface`, `--selected` a `--stage` doplnit do grafiky
  v `tests/js/contrast.test.mjs` a ověřit, že test projde.

## 4. Dokumentace

- [x] 4.1 README (odstavec o lupě a mřížce, ř. ~695–712): ovládání
  klávesnicí v mřížce, vyznačení aktuálního souboru, nové klávesy
  v lupě a klávesy v kroku „Skupiny a autoři“ průvodce i importu.

## 5. Ověření

- [x] 5.1 Baseline před změnou a po ní: `.venv/bin/python -m pytest -q`
  a `node --test tests/js/*.test.mjs` (počty testů ve výpisu).
- [x] 5.2 Vygenerovat smyšlený testovací archiv ve scratch adresáři
  (mimo repozitář, žádná reálná data): akce se dvěma skupinami
  (jedna se sedmi soubory), dny přes víc datumů, ~500 souborů pro
  měření, nedokončená akce pro průvodce a složka k importu.
- [x] 5.3 V prohlížeči (vývojový režim, headless) projít scénáře
  specifikace: šipky ve všech směrech včetně 4 → 7 a přes předěl,
  Shift+šipky, PageUp/PageDown, Home/End, Ctrl+A v mřížce i v poli
  formuláře, návrat k odscrolovanému aktuálnímu souboru, Tab + Enter,
  lupa (nahoru/dolů po oddílech, PageDown o pás), průvodce i import
  (pohyb, Esc, Delete bez účinku) a zobrazení podle data. Snímky
  vyznačení aktuálního souboru v obou režimech vzhledu (s výběrem,
  bez výběru, s poškozeným souborem).
- [x] 5.4 Změřit dobu stisku šipky dolů na akci s ~500 soubory a zapsat
  ji do design.md (Risks); při znatelném zpoždění zúžit čtení obdélníků
  podle designu.
- [x] 5.5 Ruční ověření uživatelem na reálné akci (plocha, lupa,
  průvodce, import).
