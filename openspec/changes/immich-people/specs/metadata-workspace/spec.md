## ADDED Requirements

### Requirement: Osoby jen pro čtení
Formulář souboru SHALL ukázat jména z jeho `obliceje` jako pole jen pro
čtení s poznámkou, že pochází z Immiche; MUST NOT jít upravit.
U výběru více souborů SHALL ukázat jména všech vybraných. Formulář
skupiny ani akce pole osob MUST NOT nabízet. Není-li Immich nastaven,
pole SHALL místo osob uvést, že Immich není napojen. Chybějící osoby
MUST NOT být v liště chybějících údajů.

#### Scenario: Soubor s obličeji
- **WHEN** uživatel vybere soubor s obličejem `Lečbychová, Olga`
- **THEN** formulář ukáže `Lečbychová, Olga` zašedle s poznámkou
  „z Immiche“ a pole nejde upravit

#### Scenario: Formulář skupiny
- **WHEN** uživatel vybere hlavičku skupiny
- **THEN** formulář pole osob nemá
