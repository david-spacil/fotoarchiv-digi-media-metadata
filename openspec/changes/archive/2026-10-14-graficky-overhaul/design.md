## Context

Klient je bez build kroku: `index.html` načte `style.css` a ES modul
`app.js` (~4200 řádků, DOM přes pomocnou `h()`). Stránky přihlášení
a změny hesla (`prihlaseni.html`, `heslo.html`) sdílejí `style.css`.
`style.css` (~280 řádků) má barvy natvrdo; jediné proměnné jsou paleta
osob `--p0…--p7` a šrafa `--noauth`. Volby zobrazení si klient pamatuje
v `localStorage` (`zobrazeni`, `jmeno`). Náhledy mají dvě velikosti ze
serveru: 320 px a velký (`thumbs.SIZES`). Motivace viz proposal.md.

## Goals / Non-Goals

**Goals:**
- Vzhled jde měnit jen hodnotami tokenů; varianty B a C jsou jen jiné
  hodnoty, ne jiné CSS komponent.
- Varianty jde porovnat v běžící aplikaci nad reálnými akcemi.
- Změny rozvržení bez zásahu do toku práce, ukládání a zámků.

**Non-Goals:**
- CSS framework, preprocesor, build krok, webfonty z CDN.
- Mobilní telefony (pod 1280 px se nic nezaručuje).
- Přepis `app.js` na komponenty nebo rozdělení na moduly nad rámec
  toho, co změna potřebuje.

## Decisions

**Dvě vrstvy tokenů v `style.css`.** Základní paleta (odstíny šedé,
akcentu, stavových barev) a nad ní sémantické tokeny, které jediné
používají komponenty: `--bg`, `--surface`, `--surface-2`, `--border`,
`--text`, `--text-muted`, `--accent`, `--accent-text`, `--selected`,
`--ok`, `--warn`, `--danger`, `--stage` (pozadí kolem fotek),
`--loupe-bg`, `--src-inherited`, `--src-mixed`, `--src-own`,
`--src-place`, k tomu `--radius`, `--space-*`, `--font-ui`,
`--font-heading`. Varianta přepisuje jen sémantické tokeny pod
`:root[data-vzhled="b"]` / `"c"`.
*Proč:* odstranění nevybrané varianty = smazání jednoho bloku.
*Alternativa:* samostatné soubory `vzhled-b.css` — víc požadavků
a riziko, že se do nich dostanou i komponenty.

**Tmavý režim jen ve výchozím vzhledu.** Blok
`@media (prefers-color-scheme: dark)` platí pro
`:root:not([data-vzhled])`. B je vždy tmavá, C vždy světlá — porovnávají
se jako celky.

**Volba vzhledu klasickým skriptem v `<head>`.** Nový
`static/vzhled.js` (bez `type="module"`, synchronně před `style.css`)
přečte `?vzhled=`, uloží do `localStorage` (`vzhled`) a nastaví
`data-vzhled` na `<html>`. Načtou ho všechny tři HTML stránky.
*Proč:* modul se spouští až po vykreslení a stránka by problikla ve
výchozím vzhledu. Přístup k `localStorage` v `try/catch` (vypnuté
úložiště = výchozí vzhled).

**Lupa zůstává tmavá ve všech variantách** (`--loupe-bg`): posouzení
fotky potřebuje neutrální tmavé okolí. Mřížka bere `--stage`, takže
v B je tmavá, v A a C světlá.

**Velikost dlaždic proměnnou `--tile`.** `<input type="range">` v liště
akce (100–300 px, krok 10, výchozí 150) nastaví `--tile` na `.grid`;
CSS dlaždic počítá z ní šířku i výšku náhledu (poměr 4 : 3). Uloží se
do `localStorage` (`dlazdice`). Spodní mez 100 px: při 120 px se do
okna 1280 px s panelem vejde jen 7 dlaždic, požadavek chce 8. Strop
300 px, protože náhled ze serveru má 320 px; větší by byl rozmazaný.
Po změně se aktuální soubor v mřížce posune do zorného pole
(`revealCurrent()` hlídá jen filmový pás lupy). Výběr tažením počítá s polohou dlaždic z DOM, takže
ho velikost neovlivní.

**Jedna lišta akce.** `renderWorkspace` vloží `#bar` do `.eventbar`
jako prvek s `flex: 1 1 auto` a `flex-wrap`; `renderBar` dál plní jen
`#bar`, jeho logika se nemění. Akce vpravo (Importovat, stav exportu,
Dokončit) mají `flex: none` a `margin-left: auto`, takže se zalamují
čipy, ne tlačítka. Hlavička aplikace (`header`) zůstává jednořádková
se stálou výškou.

**Panel `width: clamp(320px, 24vw, 420px)`, sbalení třídou.**
`.workspace.panel-sbaleny` skryje obsah panelu a nechá úzký pruh
s tlačítkem rozbalení. Stav v `localStorage` (`panel`). Klávesa `P` se
přidá do stávajícího globálního `keydown` se stejnou ochranou textových
polí jako Del. Lupa se po změně šířky překreslí (`renderBig`).

**Zdroj hodnoty u pole z existujícího stavu.** Pole už počítá
`inherited`, `mixed`, `anyOwn` a `from` (`LEVEL[s.from]`) a třídy
`inherited`/`mixed`/`own`/`from-place`. Doplní se jen prezentace:
proužek vlevo (`border-left` v barvě `--src-*`), štítek místo kurzívy
a tlačítko „vrátit na zděděné“ u `own` na úrovni skupiny/souborů, které
zavolá týž `update` jako vyprázdnění pole. Žádná nová logika dědění,
takže `inherit.js` a jeho testy se nemění.

**Kontrast ověřuje test.** `tests/js/contrast.test.mjs` načte
`style.css`, vytáhne hodnoty tokenů pro každý vzhled a režim a spočítá
kontrast dvojic (`--text`/`--bg`, `--text-muted`/`--surface`,
`--accent-text`/`--accent` …) podle WCAG. Tokeny musí být hexy, aby
šly číst bez prohlížeče.

## Risks / Trade-offs

- [Zásahy do 4200řádkového `app.js` rozbijí chování] → měnit jen
  `header`, `renderWorkspace`, prezentaci pole, keydown; běží stávající
  testy a ruční průchod plochou, průvodcem a importem.
- [Velké dlaždice na HiDPI rozmazané (náhled 320 px)] → strop 300 px;
  větší náhled ze serveru je samostatná změna, pokud bude potřeba.
- [Zalomená lišta mění výšku nad mřížkou při změně chybějících údajů] →
  požadavek na stálou výšku platí pro hlavičku aplikace, ne lištu akce;
  pokud skákání bude rušit, vyhradí se liště minimální výška dvou řádků.
- [Prototyp variant zůstane v kódu napořád] → poslední skupina úkolů
  po výběru variantu odstraní a přepínač zruší.

## Migration Plan

Čistě klientská změna, nasazení s další verzí. Uložené volby
v `localStorage` jsou nové klíče; staré (`zobrazeni`, `jmeno`) se
nemění. Návrat = předchozí verze `static/`.

## Výběr varianty (2026-10-14)

Uživatel po prohlídce prototypu zvolil **B – Temná pracovna** jako
výchozí vzhled s přepínačem do světlého režimu. Dopad na úkoly 6.x:

- Tokeny B jsou hodnoty `:root`; světlý režim je blok
  `:root[data-rezim="svetly"]` se světlými hodnotami z A. Bloky A
  (tmavý `@media`) a C se mažou.
- Výchozí je tmavý režim bez ohledu na systém; `prefers-color-scheme`
  se nepoužije (na světlém systému by se B jinak neukázala).
- Přepínač světlý/tmavý v hlavičce aplikace. `vzhled.js` zůstává jen
  pro režim: přečte `localStorage` (`rezim`) a nastaví `data-rezim`
  na `<html>` dřív, než se načte CSS. Parametr `?vzhled=` a klíč
  `vzhled` zanikají.
- Lupa zůstává tmavá v obou režimech.
