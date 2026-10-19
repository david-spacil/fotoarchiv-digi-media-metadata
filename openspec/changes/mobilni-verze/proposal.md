## Why

Na telefonu je aplikace nepoužitelná (issue #23): panel má pevných
400 px vedle mřížky, lišty akce přetékají, seznam akcí je široká
tabulka a výběr souborů jde jen myší a klávesnicí (Ctrl/Shift+klik,
tažení, Enter, Esc, Del, šipky).

Původní hlavní cíl, **nahrání fotek z telefonu** v prohlížeči, se
odkládá: Android prohlížeči z fotek odebírá polohu (viz změna
`blokovat-odebranou-polohu`), takže takový import by se zablokoval.
Vrátí se k němu až s cestou, která polohu zachová (nativní aplikace,
Immich, Syncthing).

## What Changes

- Responzivní rozvržení pod šířkou ~700 px pro všechny obrazovky:
  seznam akcí jako karty, zalamované lišty, dlaždice podle šířky,
  hlavička bez cest k archivu.
- **Průvodce importem na telefonu** (hlavně import ze složky
  `přetřídit`, který polohu zachová): souhrny místo tabulek (detaily
  sbalené), poškozené soubory jako karty, navigace průvodce připnutá
  dole. Nahrávání souborů z telefonu se nepřidává ani neupravuje.
- **Dotyková plocha akce** (i krok skupin v průvodci akce):
  - jako galerie Androidu: ťuknutí na dlaždici otevře lupu se
    souborem (vybraný je jen on); dlouhý stisk zapne režim výběru,
    v něm ťuknutí soubor přidává/odebírá, hlavička oddílu vybere oddíl;
  - formulář jako spodní list, otevíraný tlačítkem „Upravit (N)“;
  - lupa: přejetí prstem přepíná soubory;
  - ovládací prvky dostupné bez klávesnice: Vyřadit, Zrušit výběr,
    Zpět do mřížky;
  - méně častá tlačítka lišty akce v menu „⋯“.
- Desktop (široké okno, myš) se chová beze změny.
- Datový model, API ani server se nemění.

## Capabilities

### New Capabilities
- `mobile-client`: rozvržení na úzké obrazovce a dotykové ovládání
  seznamu akcí, průvodce importem, průvodce akce a pracovní plochy
  včetně lupy.

### Modified Capabilities
<!-- Žádné: chování na desktopu se nemění, mobilní chování popisuje
     nová capability s odkazy na stávající. -->

## Impact

- `fotoarchiv/static/style.css` — media queries, spodní list, karty.
- `fotoarchiv/static/app.js` — dotykový výběr (pointer events,
  dlouhý stisk), swipe v lupě, spodní list, menu „⋯“, mobilní varianty
  kroků importu.
- `tests/js/` — testy čisté logiky (rozhodnutí o dlouhém stisku
  a swipe).
- `README.md` — oddíl Aplikace: mobilní ovládání.
- Cílová platforma Android/Chrome; iOS (HEIC) se neřeší.
