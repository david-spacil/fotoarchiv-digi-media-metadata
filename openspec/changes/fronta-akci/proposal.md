## Why

Seznam akcí je tabulka: stav a chybějící údaje jsou drobné štítky
a z řádku není vidět, jak daleko je akce od dokončení, kdo na ní
pracuje ani co obsahuje. Dokončení akce je tlačítko na ploše
a kontrola úplnosti se ukáže až v dialogu.

## What Changes

Odsouhlasený směr (varianta C z porovnání 2026-10-13):

- **Seznam akcí jako fronta práce:** karty místo tabulky (tabulka
  zmizí) — pruh 4 náhledů, hotovost (podíl souborů s autory, datem
  a místem, stav exportu), kdo akci drží (zámek) a stav
  (*nezpracováno*, *rozpracováno*, *hotovo*, *nekompletní*,
  *k vyřešení*, *změněno po exportu*, poškozené).
- **Filtry:** Vše, Moje rozpracované, K dokončení, Nezpracované;
  hledání v názvu.
- **Řazení:** podle data akce (výchozí), hotovosti a poslední úpravy.
- **Kdo akci upravoval:** nové pole `upravili` v `_metadata.json`
  (jméno → čas posledního uložení), zapisuje ho jen server při uložení.
  Slouží filtru „Moje rozpracované“ a řazení podle poslední úpravy.
- **Dokončení akce jako kontrolní stránka** na samostatné adrese:
  místo dialogu seznam kontrol (chybějící údaje, nálezy kontroly akce,
  poškozené soubory, stav exportu) s odkazy na nápravu na ploše
  a tlačítkem dokončení.

## Capabilities

### New Capabilities

(žádné)

### Modified Capabilities

- `archive-browsing`: seznam akcí jako karty, hotovost, náhledy,
  držitel zámku, filtry, hledání a řazení.
- `metadata-workspace`: dokončení akce přes kontrolní stránku.
- `metadata-model`: pole `upravili`.

## Impact

- `fotoarchiv/archive.py` (`list_events`): hotovost pro všechny akce
  s metadaty, ukázkové soubory, `upravili`; `fotoarchiv/app.py`:
  držitel zámku ve výpisu, zápis `upravili` při uložení.
- `fotoarchiv/model.py` + `static/inherit.js`: hotovost po polích
  (sdílené fixtury dědění se nemění).
- `fotoarchiv/static/app.js`, `style.css`: seznam akcí, kontrolní
  stránka dokončení, směrování `#/akce/<název>/dokonceni`.
- `README.md`: Datový model (`upravili`), Aplikace (Tok práce).
- Výpis akcí počítá dědění u každé akce s metadaty (dnes jen
  u *hotovo*) — CPU nad už načteným JSONem, archiv se nečte víc.
  Náhledy karet: studená cache = jednorázové čtení originálů z SMB.

## Rozhodnutí (2026-10-14)

- Hotovost = podíl souborů, ne jen ano/ne; počítá server při výpisu.
- Náhledy: 4 rovnoměrně vybrané soubory, načítané líně.
- Tabulkové zobrazení se neponechává.
- Kontrolní stránka je samostatná adresa, ne krok nad plochou.
- „Moje“ = jméno v `upravili` v `_metadata.json` (ne záznam v `.work`).
- Vzhled karet se ověří funkčním prototypem s reálnými daty před
  implementací (první úkol).
