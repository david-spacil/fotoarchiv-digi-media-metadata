## Why

Při testování prototypu se ukázalo, že náhledy v mřížce (320 px) nestačí
na rozpoznání lidí a míst na fotce. Údaje k jednotlivým fotkám se tak
doplňují naslepo. Chybí pohled na jednu velkou fotku s rychlým
přepínáním, jak ho uživatelé znají z Lightroomu (lupa a filmový pás).

## What Changes

- Pracovní plocha dostane druhý režim **lupa** vedle stávající
  **mřížky**. Do lupy se přejde Enterem, dvojklikem na dlaždici nebo
  přepínačem; Esc nebo přepínač vrací do mřížky. Výběr se mezi režimy
  zachová.
- V lupě:
  - uprostřed velká fotka (nebo přehrávač videa);
  - dole filmový pás se všemi soubory akce v pořadí mřížky, se
    skupinami vizuálně oddělenými a pojmenovanými;
  - vpravo stávající formulář podle výběru (beze změny chování).
- Šipky vlevo/vpravo přepínají aktuální fotku a výběr se nastaví na
  ni; Shift+šipky výběr rozšiřují. Klik do pásu vybírá stejně jako
  v mřížce (klik, Ctrl, Shift).
- Větší náhledy (~1600 px) v lokální cache mimo archiv, generované líně;
  klient si předem načte sousední fotky, aby přepínání nečekalo na SMB.
- Video se v lupě přehraje přímo z archivu (jen čtení).

Mimo rozsah: přiblížení 1:1 a posun, porovnání dvou fotek, hodnocení
a štítky, změna vzhledu mřížky.

## Capabilities

### New Capabilities

- `loupe-view`: režim lupa na pracovní ploše — velká fotka, filmový
  pás s oddělenými skupinami, ovládání klávesnicí a vazba na výběr
  a formulář.

### Modified Capabilities

- `media-scan`: nový požadavek na velké náhledy fotek s cache
  a na přehrání videa z archivu bez zápisu.

## Impact

- Server (`fotoarchiv/thumbs.py`, `fotoarchiv/app.py`): velikost náhledu
  jako parametr, endpoint pro velký náhled a pro originál videa
  s podporou HTTP Range.
- Klient (`fotoarchiv/static/app.js`, `style.css`): režim lupa, filmový
  pás, klávesové ovládání, předběžné načítání.
- Cache `.work/cache/thumbs/` naroste o velké náhledy (řádově stovky kB
  na fotku). Archiv se dál jen čte.
- Bez nových závislostí.
