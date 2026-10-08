# Spec Delta

## ADDED Requirements

### Requirement: Kontrola při generování náhledu
Při vytváření nového náhledu z originálu SHALL aplikace spustit
kontrolu integrity tohoto souboru a výsledek uložit do cache kontroly
akce. Při nezměněném souboru s platným výsledkem v cache kontroly
MUSÍ zůstat i při dalším vytváření náhledu (jiné velikosti) originál
nekontrolován. Chyba kontroly MUST NOT zastavit vytváření náhledu;
soubor musí zůstat beze změny.

#### Scenario: Prohlížení plní cache
- **WHEN** uživatel poprvé otevře náhled poškozené fotky akce, kterou
  příkaz `zkontrolovat` ještě neprošel
- **THEN** výsledek kontroly je v cache akce a odznak poškozených ji
  začíná počítat

#### Scenario: Druhý náhled bez čtení
- **WHEN** totéž foto má v cache kontroly platný výsledek a generuje
  se náhled větší velikosti
- **THEN** kontrola se znovu nespustí

#### Scenario: Video
- **WHEN** se vytváří náhled videa
- **THEN** kontrola proběhne stejně jako u fotky (ffprobe, nuly jen
  v obrazových datech)

### Requirement: Souhrn poškozených pro akci
Aplikace SHALL z cache kontroly akce umět spočítat počet souborů
s výsledkem *podezřelý* nebo *nečitelný*, bez čtení souborů archivu.
Do počtu (odznak) MUST nepatřit soubory označené k vyřazení
(`vyradit`) a soubory s ručním potvrzením v pořádku (`overeno`, viz
`metadata-model`) ani soubory, které už v kořeni akce nejsou. Detail
akce SHALL kromě počtu poskytnout i seznam poškozených souborů včetně
těch s příznaky (pro zobrazení v dialogu úklidu).
Pro akci bez cache kontrol SHALL být počet nulový.

#### Scenario: Akce po průchodu kontrolou
- **WHEN** má akce v cache dva *nečitelné* a jeden *podezřelý*
  výsledek a žádný z nich nemá `overeno`
- **THEN** souhrn pro akci je 3 poškozené

#### Scenario: Potvrzený soubor se nepočítá
- **WHEN** u jednoho z nich uživatel potvrdí „v pořádku“
- **THEN** souhrn je 2 a seznam ho stále uvádí se značkou `overeno`

#### Scenario: Bez cache
- **WHEN** akce nemá žádnou cache kontroly
- **THEN** souhrn je 0 a seznam akcí se chová jako dosud
