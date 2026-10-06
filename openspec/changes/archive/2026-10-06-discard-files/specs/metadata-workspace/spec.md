## ADDED Requirements

### Requirement: Označení k vyřazení
Na pracovní ploše (mřížka i lupa) SHALL uživatel moci vybrané soubory
označit k vyřazení klávesou Del nebo tlačítkem. Jsou-li všechny vybrané
soubory už označené, Del a tlačítko SHALL označení zrušit. Označení
SHALL být uloženo u souboru v `_metadata.json` jako `"vyradit": true`
a průběžně ukládáno jako ostatní změny. Označit jde jen soubor, ne
skupinu ani akci. Bez zámku akce (jen ke čtení) MUST NOT jít označení
měnit.

#### Scenario: Hromadné označení
- **WHEN** uživatel vybere v mřížce 5 souborů a stiskne Del
- **THEN** všech 5 souborů má v `_metadata.json` `"vyradit": true`

#### Scenario: Zrušení označení
- **WHEN** uživatel vybere 2 označené soubory a stiskne Del
- **THEN** ani jeden už označení nemá

#### Scenario: Smíšený výběr
- **WHEN** výběr obsahuje označené i neoznačené soubory a uživatel
  stiskne Del
- **THEN** všechny vybrané soubory jsou označené

#### Scenario: Del v textovém poli
- **WHEN** je kurzor ve formulářovém poli a uživatel stiskne Del
- **THEN** maže se text, označení souborů se nemění

### Requirement: Zobrazení označených souborů
Soubory označené k vyřazení SHALL být v mřížce i pásu lupy vizuálně
odlišené a zůstávají na svém místě. Pracovní plocha SHALL ukazovat
počet označených souborů a nabídnout provedení úklidu.

#### Scenario: Označený soubor v mřížce
- **WHEN** soubor `P1503712.JPG` je označený k vyřazení
- **THEN** jeho dlaždice je odlišená a lišta ukazuje „1 soubor
  k vyřazení“ s tlačítkem úklidu

## MODIFIED Requirements

### Requirement: Lišta chybějících údajů
Pracovní plocha SHALL průběžně ukazovat, co chybí: akce bez názvu nebo
data, skupiny bez autorů, soubory bez data, soubory bez skupiny
a soubory bez místa, pokud má akce víc míst. Kliknutí na položku SHALL vybrat dotčené soubory nebo skupiny.
Soubory označené k vyřazení MUST NOT být v lištu započítány; skupina,
jejíž všechny soubory jsou označené, se nepočítá mezi skupiny bez
autorů.

#### Scenario: Skupina bez autorů
- **WHEN** skupina nemá autory a žádný její soubor je nepřepisuje
- **THEN** lišta ukáže „1 skupina bez autorů“

#### Scenario: Soubory bez místa
- **WHEN** akce má dvě místa a 30 souborů nemá místo zadané u sebe ani
  u skupiny
- **THEN** lišta ukáže „30 souborů bez místa“

#### Scenario: Označený soubor bez data
- **WHEN** soubor bez data je označený k vyřazení
- **THEN** lišta ho mezi soubory bez data nepočítá
