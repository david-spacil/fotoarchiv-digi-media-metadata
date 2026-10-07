## MODIFIED Requirements

### Requirement: Seznam akcí
Aplikace SHALL zobrazit seznam složek první úrovně archivu, jejichž
název odpovídá vzoru `YYYY-MM-DD název`, seřazený podle data sestupně.
Ostatní složky a soubory první úrovně MUST být ignorovány a nesmí se
měnit. Výjimkou jsou soubory indexu `_INDEX.html` a `_INDEX.md`, které
v produkčním režimu zapisuje aplikace (viz `archive-index`), a složka
`přetřídit`, ze které v produkčním režimu přesouvá soubory import (viz
`unsorted-import`). Seznam SHALL obsahovat odkaz na stránku Přetřídit.

#### Scenario: Složky mimo vzor
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky…`, `přetřídit`
  a `_metadata.xlsx`
- **THEN** seznam obsahuje jen `2026-04-28 kontrola Stezky…`

#### Scenario: Index v kořeni archivu
- **WHEN** kořen archivu obsahuje `_INDEX.html` a `_INDEX.md`
- **THEN** seznam akcí je neuvádí a `_metadata.xlsx` zůstane beze změny

#### Scenario: Jiné složky mimo akce
- **WHEN** uživatel provede import ze složky `přetřídit`
- **THEN** `fotky mimo akce` a `přednášky SKLEP TIC` zůstanou beze
  změny
