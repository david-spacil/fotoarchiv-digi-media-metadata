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
- **WHEN** synchronizace zapíše obličej `Hlava, Miloš`
- **THEN** `Hlava, Miloš` se nabízí při zadávání autorů

### Requirement: Našeptávání
Při psaní do pole autora nebo účastníka SHALL formulář nabízet jména ze
seznamu, která odpovídají vstupu bez ohledu na diakritiku a velikost
písmen. Účastníci otevřené akce SHALL být nabízeni přednostně.

#### Scenario: Bez diakritiky
- **WHEN** uživatel napíše `spac`
- **THEN** formulář nabídne `Spáčil, David`

#### Scenario: Účastník akce první
- **WHEN** akce má mezi účastníky `Kopáčová, Zuzana` a uživatel u autora
  skupiny napíše `k`
- **THEN** `Kopáčová, Zuzana` je první z návrhů
