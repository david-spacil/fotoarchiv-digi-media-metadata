## MODIFIED Requirements

### Requirement: Otevřený seznam jmen
Seznam návrhů SHALL obsahovat všechna jména z polí `autori`
a `ucastnici` a jména obličejů (`obliceje`) ve všech `_metadata.json`,
které aplikace vidí, a jména zadaná v tomto sezení. Neznámé jméno MUST
být přijato a od té doby SHALL být v seznamu.

#### Scenario: Nové jméno
- **WHEN** uživatel zadá jméno, které nic v seznamu nepřipomíná
- **THEN** jméno se uloží a příště se nabízí

#### Scenario: Jméno z Immiche
- **WHEN** synchronizace zapíše obličej `Vzorný, Tomáš`
- **THEN** `Vzorný, Tomáš` se nabízí při zadávání autorů

### Requirement: Našeptávání
Při psaní do pole autora nebo účastníka SHALL formulář nabízet jména ze
seznamu, která odpovídají vstupu bez ohledu na diakritiku a velikost
písmen. Účastníci otevřené akce SHALL být nabízeni přednostně.

#### Scenario: Bez diakritiky
- **WHEN** uživatel napíše `spac`
- **THEN** formulář nabídne `Příkladný, Daniel`

#### Scenario: Účastník akce první
- **WHEN** akce má mezi účastníky `Modelová, Zuzana` a uživatel u autora
  skupiny napíše `k`
- **THEN** `Modelová, Zuzana` je první z návrhů
