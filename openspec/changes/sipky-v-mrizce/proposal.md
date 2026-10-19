# Proposal

## Why

Klávesnicí se dnes dá procházet jen lupa: šipky vlevo/vpravo přepínají
soubor a Shift+šipky rozšiřují výběr. V mřížce šipky jen posouvají
stránku a aktuální soubor není vidět, takže kdo chce rychle vybírat
a otevírat soubory bez myši, musí přepnout do lupy (#37).

## What Changes

- Šipky vlevo/vpravo SHALL v mřížce fungovat jako v lupě: další či
  předchozí soubor v pořadí, výběr jen na něj, se Shiftem rozšíření
  výběru od kotvy.
- Šipky nahoru/dolů SHALL v mřížce přejít na vodorovně nejbližší
  dlaždici v řádku nad/pod podle polohy na obrazovce, přes předěl
  oddílů.
- Home/End, PageUp/PageDown a Ctrl+A SHALL fungovat v mřížce i v lupě.
  V lupě skočí nahoru/dolů na první soubor předchozího/dalšího oddílu
  a PageUp/PageDown se posunou o šířku pásu.
- Aktuální soubor SHALL být v mřížce vyznačený stejně jako v pásu lupy.
  Pohyb klávesou přesune na dlaždici fokus prohlížeče, tabulátor
  udělá fokusovanou dlaždici aktuální a mřížka se posune tak, aby byl
  aktuální soubor vidět.
- Totéž ovládání SHALL platit v kroku „Skupiny a autoři“ průvodce
  prvním otevřením i importu. Esc tam zruší výběr, Delete, Enter a P
  tam nejsou.
- Šipky v mřížce už nebudou posouvat stránku nativně; posun
  obstarává pohyb aktuálního souboru.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `metadata-workspace`: nové požadavky Ovládání klávesnicí v mřížce
  a Aktuální soubor v mřížce (plocha i krok „Skupiny a autoři“).
- `loupe-view`: Ovládání klávesnicí se rozšíří o nahoru/dolů po
  oddílech, Home/End, PageUp/PageDown a Ctrl+A; Přepínání mřížka a lupa
  počítá aktuálním souborem i dlaždici fokusovanou klávesnicí.

## Impact

- `fotoarchiv/static/app.js`: globální handler kláves (dnes jen pro
  plochu), `step` zobecněný na cílový soubor, vyznačení `current`
  v `tile`/`select`, `tabindex` dlaždic v kroku skupin, posun mřížky.
- Nový modul `fotoarchiv/static/pohyb.js` (čisté funkce: soused
  nahoru/dolů a o stránku nad obdélníky dlaždic, začátky oddílů,
  mapování kláves) s testem `tests/js/pohyb.test.mjs`.
- `fotoarchiv/static/style.css`: vzhled `.tile.current`.
- `README.md`: odstavec o lupě a mřížce (ovládání klávesnicí).
- Server, data ani API se nemění.
