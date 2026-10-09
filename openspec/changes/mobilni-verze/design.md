## Context

Klient jsou čisté ES moduly bez build kroku (`fotoarchiv/static/`),
vykreslování přes `h()` v `app.js`, styly v jednom `style.css` bez
jediné media query. Výběr na ploše řeší `clickFile` (klik,
Ctrl, Shift), `setupGrid` (výběr tažením přes `mousedown`) a globální
`keydown` (Enter, Esc, Del, šipky). Mřížku a panel sdílí plocha
(`renderWorkspace`) i krok skupin průvodce akce. Průvodce importem má
rámec `importFrame` (lišta, kroky, `.wnav`) a pět kroků
(`renderPick` … `renderImportResult`). Server při opakovaném nahrání
stejné `cesta` předchozí soubor nahradí (`Importer.add_file`).

## Goals / Non-Goals

**Goals:**
- Jedna aplikace a jedny URL pro desktop i telefon; mobilní chování
  vzniká z CSS a z typu ukazatele, ne z jiné stránky.
- Desktopové chování bit po bitu stejné (stávající testy beze změny).

**Non-Goals:**
- Nahrávání souborů z telefonu (výběr z galerie, doplnění
  nenahraných, Wake Lock): Android prohlížeči odebírá polohu, viz
  `blokovat-odebranou-polohu`; vrátí se s jinou cestou přenosu.
- iOS/Safari, HEIC, PWA, offline režim, nativní aplikace.
- Gesta nad rámec dlouhého stisku a vodorovného přejetí (pinch zoom
  v lupě, tažení výběru prstem).
- Změny serveru a API.

## Decisions

### Rozvržení podle šířky, chování podle ukazatele
Rozvržení řeší CSS `@media (max-width: 699px)` (a v JS stejný
`matchMedia` tam, kde se mění DOM: spodní list, menu „⋯“, mobilní
krok Soubory). Dotykové chování výběru se rozhoduje podle
`PointerEvent.pointerType === "touch"` konkrétní události, ne podle
šířky ani `(pointer: coarse)`: tablet s myší i notebook s dotykovým
displejem pak dělají, co uživatel čeká. Alternativa „mobil =
úzká obrazovka“ by na širokém tabletu nechala dotyk bez výběru.

### Dlouhý stisk a ťuknutí přes pointer events
Na mřížce a pásu: `pointerdown` (touch) spustí časovač 500 ms;
`pointermove` o víc než 10 px nebo `pointercancel` (prohlížeč začal
posouvat) ho zruší. Doběhnutí = dlouhý stisk → režim výběru;
`contextmenu` se v mřížce potlačí. Ťuknutí se bere z `click`
s `pointerType` posledního `pointerdown`, takže posouvání (které click
nevyvolá) výběr nemění. `mousedown` výběr tažením zůstává jen pro myš.
Rozhodovací logika (ťuknutí / dlouhý stisk / posun; přejetí vlevo,
vpravo, nic) jde do nového modulu **`static/gestures.js`** jako čisté
funkce nad souřadnicemi a časy, aby šla testovat v `node --test`.
Alternativa knihovna gest (Hammer.js) — zbytečná závislost bez build
kroku kvůli dvěma gestům.

### Režim výběru jako stav
`state.selecting` (bool). Zapne ho dlouhý stisk, vypne Zrušit výběr,
Esc nebo prázdný výběr. Mimo režim ťuknutí = `current = f`,
`sel = {f}`, `setView("loupe")` (v průvodci bez lupy jen výběr).
V režimu ťuknutí = přepnutí jako Ctrl+klik. Lišta režimu výběru
(počet, Vyřadit, Upravit, Zrušit) nahradí na úzké obrazovce lištu
chybějících údajů, dokud režim trvá.

### Spodní list = stávající `#panel`
Na úzké obrazovce dostane `#panel` `position: fixed` u spodního
okraje, výšku ~70 vh a `transform` mimo obrazovku; třída `open` ho
vysune. Obsah a `renderPanel` se nemění, takže ukládání, našeptávání
a dědění fungují stejně. Tlačítko „Upravit …“ je v liště plochy, list
má zavírací pruh nahoře. Alternativa `<dialog>` by přesouvala DOM
panelu a rozbila odkazy `document.getElementById("panel")`.

### Menu „⋯“
`<details class="more">` s rozbalovacím obsahem: na úzké obrazovce se
do něj přesunou méně časté prvky lišty akce. Bez JS logiky, zavře se
po volbě. Na širokém okně se `details` nezobrazí a prvky zůstanou
v liště (stejné uzly, jen jiné CSS — `display: contents` na desktopu).

### Přejetí v lupě
`pointerdown`/`pointerup` na `.big .media` s `pointerType` touch;
vodorovný posun > 50 px a větší než svislý = `step(±1, selecting)`.
Na `<video>` se gesto nezachytává (ovládání přehrávače). CSS
`touch-action: pan-y` na velké fotce, aby prohlížeč vodorovné gesto
neposouval.

## Risks / Trade-offs

- [Dlouhý stisk koliduje s nativním menu obrázku] → `contextmenu`
  potlačit a `-webkit-touch-callout: none`, `user-select: none` na
  dlaždicích (už má mřížka).
- [Dvojí cesta kódu desktop/dotyk] → dotyková větev jen tam, kde se
  liší (klik, režim výběru, gesta); desktop testovat ručně stejně jako
  dosud a JS testy čisté logiky.
- [Spodní list zakryje mřížku] → list do ~70 vh, nad ním zůstane vidět
  pruh mřížky; zavírání pruhem i tlačítkem zpět prohlížeče se neřeší
  (zbytečná práce s historií).

## Migration Plan

Jen klient; nasazení obvyklým `docker compose up -d --build`. Návrat
= předchozí obraz. Data se nemění.
