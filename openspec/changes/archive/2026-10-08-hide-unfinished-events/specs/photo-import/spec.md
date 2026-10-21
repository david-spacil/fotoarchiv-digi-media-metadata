## MODIFIED Requirements

### Requirement: Volba cíle
Uživatel SHALL zvolit jako cíl stávající akci, nebo novou akci. U nové
akce SHALL průvodce předvyplnit datum nejstarším dnem z nahraných
souborů a vyžádat název. Název složky nové akce MUST odpovídat vzoru
`YYYY-MM-DD název`, MUST NOT obsahovat `/` ani `\`, MUST NOT končit na
`.ignored` a složka stejného názvu MUST NOT existovat s příponou
`.ignored` ani bez ní. V produkčním režimu SHALL import složku nové
akce založit s příponou `.ignored` (viz `event-visibility`). U dokončené
akce SHALL průvodce upozornit, že akce dostane nové soubory bez metadat
a Immich je uvidí hned.

#### Scenario: Návrh data nové akce
- **WHEN** nahrané fotky mají EXIF datum 28. a 29. 4. 2026
- **THEN** průvodce předvyplní datum `2026-04-28`

#### Scenario: Existující název
- **WHEN** uživatel zadá novou akci s názvem složky, která už v archivu
  je
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

#### Scenario: Existující skrytá akce
- **WHEN** archiv obsahuje `2026-04-28 kontrola Naučné stezky.ignored`
  a uživatel zadá novou akci `2026-04-28 kontrola Naučné stezky`
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

#### Scenario: Nová akce skrytá
- **WHEN** uživatel v produkčním režimu importuje do nové akce
  `2026-04-28 kontrola Naučné stezky`
- **THEN** soubory leží ve složce `2026-04-28 kontrola Naučné stezky.ignored`
