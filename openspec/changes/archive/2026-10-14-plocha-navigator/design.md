## Context

Plocha dnes kreslí oddíly v `renderGrid()` (`fotoarchiv/static/app.js`)
jako `<section>` s hlavičkou `.ghead`; klik na hlavičku vybírá skupinu
nebo soubory dne a stejné hlavičky hledají `missingItems()` a další
místa přes `#grid .ghead[data-group=…]`. Chybějící údaje počítá
`missing()` v `inherit.js` (seznamy souborů a skupin) a `missingItems()`
z nich skládá položky lišty i dialogu dokončení. Oddíly podle data
dělá `byDay()` v `sections.js`, barvy osob `personIndex()`
a `stripeStops()` tamtéž. Průvodce (krok skupiny a autoři) má vlastní
mřížku s hlavičkami a poli autorů.

Odsouhlasený vzhled řádku je varianta „Řádek“ z prototypu (artifacts,
`Navigátor akce`, verze 2; data DOD 2015 a syntetická akce).

## Goals / Non-Goals

**Goals:**
- Navigátor nad stejnými oddíly jako mřížka a pás — jeden zdroj
  oddílů pro všechny tři.
- Chybějící údaje za oddíl bez nového výpočtu dědění.
- Mřížka bez popisků a hlaviček, hustší při stejné velikosti náhledu.

**Non-Goals:**
- Kaskáda dědění ve formuláři (samostatná změna).
- Průvodce: krok skupiny a autoři si nechává hlavičky s poli autorů.
- Přepínání mezi akcemi z plochy.
- Sbalování navigátoru (lze doplnit, až bude potřeba místo).

## Decisions

**Oddíly jako data, ne DOM.** `sections()` už vrací `{gid, key, title,
files}`; doplní se o počty chybějících údajů a autory a z toho se kreslí
navigátor, mřížka i pás. Místo hledání `.ghead` se skáče na
`#grid .section[data-key=…]`. Alternativa — číst stav z DOM mřížky —
by v lupě nefungovala (mřížka je skrytá).

**Chybějící údaje za oddíl průnikem.** `missing()` zůstane beze změny
(sdílí fixtury s `model.py`); nová čistá funkce v `sections.js` vezme
jeho výsledek a soubory oddílu a vrátí počty a seznamy pro řádek.
Soubory bez autorů `missing()` nevrací — spočítají se z výsledných
hodnot, které plocha už má pro značku autorů. Testuje se v
`tests/js` jako ostatní funkce `sections.js`. Alternativa — rozšířit
`missing()` — by vynutila změnu i v Pythonu a fixturách.

**Dialog dokončení beze změny.** `missingItems()` dál skládá souhrnné
položky pro dialog Dokončit akci; lišta je jen přestane kreslit.
Přepis dokončení řeší změna `fronta-akci`.

**Viditelné oddíly přes IntersectionObserver** nad sekcemi mřížky
(prototyp počítal `getBoundingClientRect` při scrollu; observer je
levnější a reaguje i na změnu velikosti dlaždic a sbalení panelu).
V lupě se vyznačuje oddíl aktuálního souboru.

**Skok s předělem** přes `scroll-margin-top` na sekci (o výšku předělu
a mezery), ne ruční výpočet posunu.

**Tažení přes HTML5 drag and drop.** Výběr tažením myši (gumička) už
začíná jen mimo dlaždice, takže tažení dlaždice s ním nekoliduje.
Přesun volá stávající `moveFiles()` a `dropEmptyGroups()`, takže
pravidla prázdné skupiny platí beze změny. Bez zámku se `draggable`
nenastaví.

**Ikony jako inline SVG** v jednom modulu (`icons.js`, funkce vracející
element), `stroke="currentColor"`, aby braly barvu z tokenů. Každé
tlačítko jen s ikonou dostane `aria-label` a `title`. Ikonami se
nahradí jen tlačítka v liště a navigátoru, kde je text zbytný (panel,
mřížka/lupa); textová tlačítka formuláře zůstanou.

**Překryv dlaždice** jen CSS (`:hover`, `:focus-visible`); obsah
překryvu je v DOM dlaždice, takže titulek a čtečky fungují bez myši.

## Risks / Trade-offs

- [Šířka: navigátor ~250 px + panel 280 px v okně 1280 px] → mřížce
  zbude ~750 px; požadavek Velikost dlaždic (8 na řádek) se ověří na
  1280 px, případně se navigátor zúží.
- [Velké akce: stovky souborů, desítky řádků] → navigátor se posouvá
  samostatně; přepočet za oddíl je lineární ve velikosti akce, stejně
  jako dnešní `missing()`.
- [Dlaždice bez popisku: název souboru je vidět až při najetí] →
  titulek dlaždice, překryv i pro fokus z klávesnice; v lupě je název
  vidět vždy.
- [Tažení na dotykových zařízeních HTML5 DnD nefunguje] → přesun přes
  formulář (Úprava skupin) zůstává.
