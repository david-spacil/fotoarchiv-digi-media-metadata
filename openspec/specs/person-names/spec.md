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
- **WHEN** synchronizace zapíše obličej `Vzorný, Tomáš`
- **THEN** `Vzorný, Tomáš` se nabízí při zadávání autorů

### Requirement: Našeptávání
Při psaní do pole autora nebo účastníka SHALL formulář nabízet jména ze
seznamu, která odpovídají vstupu bez ohledu na diakritiku a velikost
písmen. Účastníci otevřené akce SHALL být nabízeni přednostně.

#### Scenario: Bez diakritiky
- **WHEN** uživatel napíše `prikl`
- **THEN** formulář nabídne `Příkladný, Daniel`

#### Scenario: Účastník akce první
- **WHEN** akce má mezi účastníky `Modelová, Zuzana` a uživatel u autora
  skupiny napíše `k`
- **THEN** `Modelová, Zuzana` je první z návrhů

### Requirement: Návrh opravy
Když zadané jméno odpovídá jménu ze seznamu po odstranění diakritiky,
sjednocení velikosti písmen a seřazení slov, formulář SHALL nabídnout
„Mysleli jste `…`?“ a kliknutím propsat kanonický tvar.

#### Scenario: Jiné pořadí slov
- **WHEN** uživatel zadá `Daniel Příkladný` a v seznamu je `Příkladný, Daniel`
- **THEN** formulář nabídne „Mysleli jste `Příkladný, Daniel`?“

#### Scenario: Chybějící diakritika
- **WHEN** uživatel zadá `Prikladny, Daniel`
- **THEN** formulář nabídne `Příkladný, Daniel`

### Requirement: Kanonický tvar
Nové jméno SHALL být ukládáno ve tvaru `Příjmení, Jméno`. Zadání bez
čárky se dvěma slovy SHALL aplikace nabídnout převést (`Jan Novák` →
`Novák, Jan`).

#### Scenario: Jméno bez čárky
- **WHEN** uživatel zadá nové jméno `Jan Novák`
- **THEN** formulář nabídne uložit `Novák, Jan`

### Requirement: Zobrazení návrhů
Seznam návrhů jmen SHALL ležet nad obsahem stránky a MUST NOT ho
oříznout okno ani panel, ve kterém je pole jména; SHALL být celý
vidět a zarovnaný s polem. Otevírá se pod polem; nevejde-li se tam do
viditelné části okna (např. nad klávesnici telefonu), SHALL se otevřít
nad polem. Platí pro všechna pole jmen osob: nástroj pojmenování
i autory a účastníky v panelu. Posun obsahu pod seznamem SHALL seznam
zavřít.

#### Scenario: Pole dole v okně nástroje
- **WHEN** archivář v nástroji pojmenování napíše do pole jména `vz`
  a server vrátí 10 návrhů
- **THEN** všech 10 návrhů je vidět bez posouvání okna nástroje, i ty,
  které sahají pod jeho dolní okraj

#### Scenario: Málo místa pod polem
- **WHEN** pod polem jména zbývá do konce viditelné části okna méně
  místa, než seznam potřebuje, a nad polem víc
- **THEN** seznam se otevře nad polem

#### Scenario: Klávesnice telefonu
- **WHEN** na telefonu klávesnice zakrývá spodní polovinu obrazovky
  a pole jména je těsně nad ní
- **THEN** seznam se otevře nad polem a není schovaný pod klávesnicí

#### Scenario: Pole v panelu
- **WHEN** archivář píše autora skupiny do pole u dolního okraje
  panelu
- **THEN** seznam návrhů není panelem oříznutý a panel se kvůli němu
  neposune

#### Scenario: Posun pod seznamem
- **WHEN** je seznam otevřený a archivář posune panel nebo okno
- **THEN** seznam se zavře a v poli zůstane rozepsaný text

### Requirement: Počet návrhů
Nástroj pojmenování SHALL nabídnout tolik návrhů, kolik jich vrátí
server (nejvýš 10). Panel nabízí návrhy beze změny počtu.

#### Scenario: Deset shod
- **WHEN** na dotaz v nástroji pojmenování odpovídá 12 jmen ze seznamu
- **THEN** nástroj nabídne 10 návrhů
