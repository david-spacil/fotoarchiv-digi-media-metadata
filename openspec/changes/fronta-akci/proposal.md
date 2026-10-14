## Why

Seznam akcí je tabulka: stav a chybějící údaje jsou drobné štítky
a z řádku není vidět, jak daleko je akce od dokončení, kdo na ní
pracuje ani co obsahuje. Dokončení akce je tlačítko na ploše
a kontrola úplnosti se ukáže až v dialogu.

## What Changes

Odsouhlasený směr (varianta C z porovnání 2026-10-13):

- **Seznam akcí jako fronta práce:** karty místo tabulky — pruh
  několika náhledů, ukazatel hotovosti (autoři, data, místa, export),
  kdo akci drží (zámek) a stav (*nezpracováno*, *rozpracováno*,
  *hotovo*, *nekompletní*, *k vyřešení*, *změněno po exportu*).
- **Filtry:** „moje rozpracované“, „k dokončení“, „nezpracované“
  (případně další po odsouhlasení).
- **Dokončení akce jako kontrolní stránka:** místo dialogu seznam
  kontrol (chybějící údaje, nálezy kontroly akce, poškozené soubory,
  stav exportu) s odkazy na nápravu a tlačítkem dokončení.

## Capabilities

### New Capabilities

(upřesní se se specifikací)

### Modified Capabilities

- `archive-browsing`: seznam akcí, stavy a filtry.
- `metadata-workspace`: dokončení akce.

## Impact

- `fotoarchiv/static/app.js`, `style.css` (seznam akcí, dokončení).
- `fotoarchiv/app.py` — seznam akcí může potřebovat ukázkové náhledy
  a míru hotovosti (upřesní se).
- `README.md`, oddíl Aplikace.

## Otevřené otázky (před specifikací)

Nejdřív informační architektura a data karty, pak vzhled; varianty
jako funkční prototyp s reálnými daty.

- Jak počítat „hotovost“ akce a jestli ji server počítá pro všechny
  akce při výpisu (cena čtení `_metadata.json` a náhledů na SMB).
- Které filtry a řazení; zůstane možnost tabulkového zobrazení?
- Kontrolní stránka dokončení: samostatná adresa, nebo krok nad
  plochou?
- Pořadí: po `import-a-popis` a `plocha-navigator`.
