## MODIFIED Requirements

### Requirement: Přepínání mřížka a lupa
Pracovní plocha SHALL mít dva režimy: mřížku a lupu. Do lupy SHALL vést
Enter, dvojklik na dlaždici a přepínač režimu; zpět do mřížky Esc
a přepínač. Výběr MUST zůstat při přepnutí zachován. Lupa SHALL ukázat
aktuální soubor: naposledy kliknutý, vybraný nebo klávesnicí
fokusovaný, jinak první soubor akce.

#### Scenario: Dvojklik na dlaždici
- **WHEN** uživatel v mřížce dvakrát klikne na `P1503720.JPG`
- **THEN** otevře se lupa s touto fotkou a fotka je vybraná

#### Scenario: Návrat do mřížky
- **WHEN** uživatel v lupě vybere tři soubory a stiskne Esc
- **THEN** zobrazí se mřížka se stejnými třemi vybranými soubory
  a aktuální soubor je vidět

#### Scenario: Enter na fokusované dlaždici
- **WHEN** uživatel klikne na první soubor akce, tabulátorem přejde na
  dlaždici `P1503720.JPG` a stiskne Enter
- **THEN** otevře se lupa s fotkou `P1503720.JPG`

### Requirement: Ovládání klávesnicí
V lupě SHALL šipka vpravo/vlevo přejít na další/předchozí soubor
v pořadí pásu přes hranice oddílů, šipka nahoru na první soubor oddílu
(na jeho začátku na předchozí oddíl), šipka dolů na první soubor
dalšího oddílu, Home/End na první/poslední soubor akce
a PageUp/PageDown o tolik souborů, kolik se vejde do pásu. Bez Shiftu
SHALL výběr být jen cílový soubor, se Shiftem rozsah od kotvy. Ctrl+A
SHALL vybrat všechny soubory. Klávesy MUST NOT přepínat soubory, když je
kurzor v poli formuláře.

#### Scenario: Další fotka
- **WHEN** aktuální je poslední fotka skupiny a uživatel stiskne šipku
  vpravo
- **THEN** aktuální je první soubor další skupiny a je jediný vybraný

#### Scenario: Rozšíření výběru
- **WHEN** aktuální je pátá fotka a uživatel třikrát stiskne Shift+šipku
  vpravo
- **THEN** vybrané jsou čtyři fotky (pátá až osmá) a aktuální je osmá

#### Scenario: Psaní do formuláře
- **WHEN** uživatel v lupě píše popis a stiskne šipku vlevo
- **THEN** kurzor se posune v textu a aktuální fotka se nezmění

#### Scenario: Skok na další oddíl
- **WHEN** v lupě je aktuální třetí soubor skupiny `DOD 2015_Lenka`
  a uživatel stiskne šipku dolů
- **THEN** aktuální a jediný vybraný je první soubor skupiny
  `DOD 2015_Olga` a pás ho ukazuje

#### Scenario: Šipka nahoru uprostřed oddílu
- **WHEN** v lupě je aktuální třetí soubor skupiny `DOD 2015_Olga`
  a uživatel dvakrát stiskne šipku nahoru
- **THEN** po prvním stisku je aktuální první soubor `DOD 2015_Olga`,
  po druhém první soubor `DOD 2015_Lenka`

#### Scenario: Konec akce
- **WHEN** v lupě je aktuální první soubor akce a uživatel stiskne
  Shift+End
- **THEN** vybrané jsou všechny soubory akce a aktuální je poslední

#### Scenario: O šířku pásu
- **WHEN** do pásu se vejde deset souborů, aktuální je druhý soubor
  akce a uživatel stiskne PageDown
- **THEN** aktuální a jediný vybraný je dvanáctý soubor akce

#### Scenario: Vybrat vše v lupě
- **WHEN** v lupě je aktuální pátý soubor a uživatel stiskne Ctrl+A
- **THEN** vybrané jsou všechny soubory akce a aktuální zůstává pátý
