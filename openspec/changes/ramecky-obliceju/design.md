# Design

## Context

| Místo | Dnes |
|---|---|
| `renderBig()` (`app.js:2408`) | `.media` s jedním `<img>`; nejdřív náhled 320 px, po načtení 1600 px; přestaví se jen při změně souboru (`big.dataset.file`) |
| `.big img` (`style.css:662`) | `width/height: 100 %` a `object-fit: contain`, tedy prázdné pruhy kolem fotky uvnitř `<img>` |
| `facesRow(files)` (`app.js:2524`) | jména z `obliceje` vybraných souborů jako jeden text spojený `; ` |
| `thumbs.make_image_thumb` | `ImageOps.exif_transpose`: náhledy jsou už otočené |
| `oblast` | `[x, y, w, h]` (střed a velikost, 0–1) vůči otočené fotce (`immich-people`) |

Protože náhledy i `oblast` se vztahují k otočené fotce, rámeček je
prostý přepočet na procenta bez ohledu na EXIF orientaci. Potíž je jen
v tom, že `<img>` s `object-fit: contain` je větší než viditelná fotka,
takže procenta vůči němu by mířila do pruhů.

## Goals / Non-Goals

**Goals:**
- Rámečky v lupě, které sedí při jakékoli velikosti okna bez
  přepočtu v JavaScriptu.
- Propojení rámečků a jmen ve formuláři oběma směry (viz spec).

**Non-Goals:**
- Rámečky v mřížce a pásu, u videa, dotykové ovládání.
- Nepojmenované obličeje (nejsou v `_metadata.json`) a čerstvá data
  z Immiche bez znovunačtení akce.

## Decisions

### Obal s rozměrem fotky z jednotek kontejneru

`.media` dostane `container-type: size`. Fotka je v obalu `.frame`
s `position: relative`, `aspect-ratio: W / H` a šířkou
`min(100cqw, 100cqh * W / H)`. Obal má tak přesně rozměr viditelné
fotky a `<img>` ho vyplní. Rámečky jsou absolutně umístěné děti obalu
v procentech:

```
left = x - w/2, top = y - h/2, width = w, height = h   (vše × 100 %)
```

Při změně velikosti okna přepočítá obal prohlížeč sám. `W / H` je
poměr načteného náhledu (`naturalWidth/Height` 320 px). Náhled
1600 px má stejný poměr, takže výměna za něj nic neposune. Do načtení
prvního náhledu se rámečky nevykreslí.

Zvažované alternativy:
- *Výpočet obdélníku fotky v JS a `ResizeObserver`*: víc kódu
  a překreslování při každé změně rozložení (panel, okno, pás).
- *SVG s `viewBox` a `preserveAspectRatio="xMidYMid meet"`*: stejný
  letterbox jako `object-fit`, ale štítek se jménem by se škáloval
  s fotkou a hover by se řešil na `<rect>`; HTML prvky jdou stylovat
  stejně jako zbytek aplikace.
- *`aspect-ratio` s `max-width/max-height: 100 %`*: při uplatnění
  jednoho omezení se poměr rozbije, nespolehlivé.

### Viditelnost přes CSS, propojení přes data atributy

- Rámeček je skrytý; `.frame:hover .face` ho ukáže. Kurzor nad
  pruhy kolem fotky se nepočítá (je mimo obal). Při přechodu šipkou
  na další fotku zůstane kurzor nad novým obalem a `:hover` platí dál.
- Rámeček nese `data-jmeno`, jméno ve formuláři je samostatný `<span>`
  se stejným `data-jmeno`. Najetí na jméno přidá obalu třídu
  `.focus-name` a odpovídajícím rámečkům `.hl`; jen ty jsou pak vidět.
  Najetí na rámeček zvýrazní `<span>` se stejným jménem a ukáže štítek
  u rámečku (`.face:hover .label`).
- Párování podle jména (ne indexu) pokryje osobu na fotce víckrát
  i výběr více souborů. Hledání prvků přes `CSS.escape(jmeno)`.

### Ztlumení jmen mimo aktuální fotku

`facesRow` v lupě s výběrem více souborů porovná jména s `obliceje`
souboru `state.current` a ostatním dá třídu `.off` (bez hover reakce).
Formulář se dnes překresluje při změně výběru; v lupě se aktuální
soubor mění vždy spolu s výběrem (`moveTo`, `clickFile`), kromě
Ctrl+kliku, který formulář překreslí také. Přepnutí mřížka/lupa
formulář překreslí, aby se ztlumení přidalo nebo odebralo.

### Čistá logika v modulu

Převod `oblast` na styl rámečku a výpočet „jména na aktuální fotce /
ostatní“ jdou do malého modulu `static/obliceje.js` s testy
`tests/js/obliceje.test.mjs` (vzor `pohyb.js`). DOM a CSS zůstávají
v `app.js` a `style.css`.

## Risks / Trade-offs

- [Jednotky kontejneru vyžadují novější prohlížeč (2023+)] → aplikace
  už cílí na moderní prohlížeče (ES moduly bez build kroku); bez
  podpory se jen nezobrazí rámečky správně, fotka zůstane.
- [`container-type: size` vyžaduje, aby `.media` mělo výšku z
  rozložení, ne z obsahu] → `.media` už je `flex: 1; min-height: 0`;
  ověřit, že se fotka nezhroutí na nulu.
- [Obal mění rozvržení velké fotky] → `.vmsg`, zástupný text
  a video zůstávají přímo v `.media` bez obalu.
- [Rámeček s `oblast` mimo 0–1 (chyba dat)] → ořízne ho `overflow:
  hidden` obalu.
