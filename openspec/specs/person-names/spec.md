# person-names Specification

## Purpose

Udržet jména osob a autorů v jednotném tvaru bez pevného číselníku:
návrhy vznikají z dosud použitých jmen a opravují překlepy a jiné pořadí.

## Requirements

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

### Requirement: Návrh opravy
Když zadané jméno odpovídá jménu ze seznamu po odstranění diakritiky,
sjednocení velikosti písmen a seřazení slov, formulář SHALL nabídnout
„Mysleli jste `…`?“ a kliknutím propsat kanonický tvar.

#### Scenario: Jiné pořadí slov
- **WHEN** uživatel zadá `David Spáčil` a v seznamu je `Spáčil, David`
- **THEN** formulář nabídne „Mysleli jste `Spáčil, David`?“

#### Scenario: Chybějící diakritika
- **WHEN** uživatel zadá `Spacil, David`
- **THEN** formulář nabídne `Spáčil, David`

### Requirement: Kanonický tvar
Nové jméno SHALL být ukládáno ve tvaru `Příjmení, Jméno`. Zadání bez
čárky se dvěma slovy SHALL aplikace nabídnout převést (`Jan Novák` →
`Novák, Jan`).

#### Scenario: Jméno bez čárky
- **WHEN** uživatel zadá nové jméno `Jan Novák`
- **THEN** formulář nabídne uložit `Novák, Jan`
