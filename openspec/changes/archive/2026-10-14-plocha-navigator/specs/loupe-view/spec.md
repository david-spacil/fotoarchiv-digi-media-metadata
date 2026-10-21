## ADDED Requirements

### Requirement: Navigátor v lupě
Navigátor akce (viz `metadata-workspace`, Navigátor akce) SHALL být
vidět i v lupě se stejnými řádky a chybějícími údaji. Klik na řádek
oddílu SHALL v lupě udělat první soubor oddílu aktuálním a jediným
vybraným a posunout pás tak, aby byl vidět; skupinu MUST NOT vybrat
(formulář v lupě upravuje jen soubory, nebo akci). Klik na řádek Akce
SHALL zrušit výběr a aktuální soubor ponechat. Okrajem SHALL být
vyznačený oddíl aktuálního souboru.

#### Scenario: Skok na skupinu v lupě
- **WHEN** v lupě je aktuální soubor skupiny `DOD 2015_Lenka`
  a uživatel klikne na řádek `DOD 2015_Olga`
- **THEN** aktuální a jediný vybraný je první soubor skupiny
  `DOD 2015_Olga` a formulář upravuje tento soubor

#### Scenario: Skok na den v lupě
- **WHEN** v zobrazení podle data uživatel v lupě klikne na řádek
  `so 7. 11. 2015`
- **THEN** aktuální je první soubor toho dne a pás ho ukazuje

#### Scenario: Oddíl aktuálního souboru
- **WHEN** uživatel v lupě přejde šipkou z posledního souboru skupiny
  na první soubor další skupiny
- **THEN** okraj v navigátoru se přesune na řádek další skupiny
