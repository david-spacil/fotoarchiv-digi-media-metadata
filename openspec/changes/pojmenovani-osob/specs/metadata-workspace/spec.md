## MODIFIED Requirements

### Requirement: Osoby jen pro čtení
Formulář souboru SHALL ukázat jména z jeho `obliceje` jako pole jen pro
čtení s poznámkou, že pochází z Immiche; MUST NOT jít upravit.
U výběru více souborů SHALL ukázat jména všech vybraných. Formulář
skupiny ani akce pole osob MUST NOT nabízet. Není-li Immich nastaven,
pole SHALL místo osob uvést, že Immich není napojen. Soubory bez osob
MUST NOT být mezi chybějícími údaji v navigátoru; nepojmenované osoby
akce ano (viz Chybějící údaje v navigátoru).

#### Scenario: Soubor s obličeji
- **WHEN** uživatel vybere soubor s obličejem `Lečbychová, Olga`
- **THEN** formulář ukáže `Lečbychová, Olga` zašedle s poznámkou
  „z Immiche“ a pole nejde upravit

#### Scenario: Formulář skupiny
- **WHEN** uživatel vybere skupinu v navigátoru
- **THEN** formulář pole osob nemá

### Requirement: Chybějící údaje v navigátoru
Navigátor SHALL průběžně ukazovat, co chybí (soubory označené
k vyřazení MUST NOT být započítány):

- **Řádek Akce:** chybějící název nebo data akce, místa bez souřadnic
  (viz Místa bez souřadnic v navigátoru) a počet nepojmenovaných osob
  podle posledního zjištění osob akce (viz `immich-people`).
- **Řádek oddílu:** počet souborů bez autorů, bez data a bez místa
  (bez místa jen pokud má akce víc míst); v zobrazení podle data
  i počet souborů bez skupiny. Oddíl „Bez data“ neukazuje „bez data“
  a oddíl „Bez skupiny“ neukazuje „bez skupiny“.
- **Skupina bez autorů:** skupina, která nemá výsledné autory a aspoň
  jeden její soubor je nepřepisuje, SHALL mít místo počtu souborů bez
  autorů zvýrazněné „bez autorů“. Skupina, jejíž všechny soubory jsou
  označené k vyřazení, mezi ně nepatří.

Každý chybějící údaj SHALL být ikona s počtem a titulkem slovy
(„30 souborů bez místa“). Klik na údaj SHALL vybrat dotčené soubory
a posunout na ně mřížku; u skupiny bez autorů SHALL vybrat skupinu.
Klik na nepojmenované osoby SHALL archiváři a adminovi otevřít nástroj
pojmenování osob (viz `person-naming`), ostatním je jen ukázat.
Bez zámku akce (jen ke čtení) SHALL údaje zůstat vidět a klik vybírat.

#### Scenario: Skupina bez autorů
- **WHEN** skupina nemá autory a žádný její soubor je nepřepisuje
- **THEN** její řádek ukáže zvýrazněné „bez autorů“ a klik na ně
  vybere skupinu

#### Scenario: Soubory bez data ve skupině
- **WHEN** 10 souborů skupiny `DOD 2015_Jana` nemá datum ani zděděné
- **THEN** řádek skupiny ukáže ikonu data s počtem 10 a klik na ni
  vybere těch 10 souborů

#### Scenario: Soubory bez místa
- **WHEN** akce má dvě místa a 30 souborů skupiny nemá místo zadané
  u sebe ani u skupiny
- **THEN** řádek skupiny ukáže ikonu místa s počtem 30

#### Scenario: Jedno místo akce
- **WHEN** akce má jedno místo
- **THEN** žádný řádek neukazuje soubory bez místa

#### Scenario: Označený soubor bez data
- **WHEN** soubor bez data je označený k vyřazení
- **THEN** řádek jeho oddílu ho mezi soubory bez data nepočítá

#### Scenario: Chybějící datum akce
- **WHEN** akce nemá vyplněné datum do
- **THEN** řádek Akce ukáže, že chybí datum do, a klik na řádek
  zruší výběr

#### Scenario: Bez skupiny podle data
- **WHEN** v zobrazení podle data leží pod jedním dnem 6 souborů bez
  skupiny
- **THEN** řádek dne ukáže ikonu skupiny s počtem 6

#### Scenario: Nepojmenované osoby
- **WHEN** akce má podle posledního zjištění 2 nepojmenované osoby
  a plochu otevře archivář
- **THEN** řádek Akce ukáže ikonu osoby s počtem 2 („2 nepojmenované
  osoby“) a klik na ni otevře nástroj pojmenování osob

#### Scenario: Akce bez alba
- **WHEN** akce nemá album v Immichi nebo Immich není nastaven
- **THEN** řádek Akce nepojmenované osoby neukazuje
