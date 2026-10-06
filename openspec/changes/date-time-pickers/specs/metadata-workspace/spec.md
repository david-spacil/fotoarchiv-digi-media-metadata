## MODIFIED Requirements

### Requirement: Kalendář u data pořízení
Pole Datum pořízení SHALL mít dva samostatné vstupy: den a čas
(hodiny, minuty, sekundy), oba s nativním výběrem prohlížeče. Uložená
hodnota SHALL mít tvar `RRRR-MM-DD`, nebo `RRRR-MM-DDTHH:MM[:SS]`, je-li
zadán čas. Prázdný čas SHALL znamenat hodnotu jen s datem. Smazání času
SHALL ponechat datum; smazání dne SHALL smazat celou hodnotu. Čas bez
dne MUST NOT jít uložit.

Ve výběru více souborů SHALL změna dne přepsat datum u všech vybraných
souborů, každému se zachováním jeho vlastního času (nebo jeho absence),
a změna času SHALL přepsat čas u všech vybraných souborů s datem,
každému se zachováním jeho dne. Vstup dne SHALL ukazovat den, je-li
u všech vybraných souborů stejný, jinak SHALL zůstat prázdný; totéž
platí pro čas. Při rozdílných hodnotách SHALL vedle vstupů stát text
„rozdílné hodnoty – zápisem přepíšete vše“.

#### Scenario: Změna dne se zachováním času
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel zvolí den
  29. 4. 2026
- **THEN** datum souboru je `2026-04-29T09:44:36`

#### Scenario: Datum bez času
- **WHEN** WhatsApp fotka má datum `2026-04-28` a uživatel zvolí den
  30. 4. 2026
- **THEN** datum souboru je `2026-04-30` a vstup času zůstane prázdný

#### Scenario: Prázdné datum
- **WHEN** soubor nemá datum a uživatel zvolí den 28. 4. 2026
- **THEN** datum souboru je `2026-04-28`

#### Scenario: Doplnění času
- **WHEN** soubor má datum `2026-04-28` a uživatel zadá čas 14:05:10
- **THEN** datum souboru je `2026-04-28T14:05:10`

#### Scenario: Smazání času
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel čas smaže
- **THEN** datum souboru je `2026-04-28`

#### Scenario: Smazání dne
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel smaže den
- **THEN** soubor nemá datum zadané

#### Scenario: Čas bez dne
- **WHEN** soubor nemá datum
- **THEN** vstup času nejde vyplnit

#### Scenario: Rozdílné časy ve výběru
- **WHEN** vybrané soubory mají `2026-04-28T09:44:36`
  a `2026-04-28T10:02:11`
- **THEN** vstup dne ukazuje 28. 4. 2026, vstup času je prázdný a vedle
  vstupů stojí „rozdílné hodnoty – zápisem přepíšete vše“

#### Scenario: Nový čas ve výběru
- **WHEN** vybrané soubory mají `2026-04-28T09:44:36`
  a `2026-04-29T10:02:11` a uživatel zadá čas 12:00:00
- **THEN** soubory mají `2026-04-28T12:00:00` a `2026-04-29T12:00:00`

#### Scenario: Nový den ve výběru
- **WHEN** vybrané soubory mají `2026-04-28T09:44:36` a `2026-04-28`
  a uživatel zvolí den 1. 5. 2026
- **THEN** soubory mají `2026-05-01T09:44:36` a `2026-05-01`
