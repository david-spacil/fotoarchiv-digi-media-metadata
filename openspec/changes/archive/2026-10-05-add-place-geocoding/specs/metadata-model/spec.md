## ADDED Requirements

### Requirement: GPS ze souřadnic místa
Výsledné `gps` souboru SHALL být jeho vlastní nebo zděděné `gps`; pokud
žádné není a výsledné `misto` má v `souradnice_mist` souřadnice,
výsledné `gps` SHALL být tyto souřadnice s úrovní `misto`. Souřadnice
místa MUST NOT přepsat GPS z EXIF ani ručně zadané GPS na kterékoli
úrovni a MUST NOT se ukládat k souboru.

#### Scenario: Fotka bez GPS
- **WHEN** soubor nemá `gps`, jeho místo je `Vzorkov`
  a `souradnice_mist` má pro `Vzorkov` [49.1234, 16.4321]
- **THEN** výsledné `gps` souboru je [49.1234, 16.4321] z úrovně
  `misto`

#### Scenario: Fotka s GPS z EXIF
- **WHEN** soubor má `gps` z EXIF a místo se souřadnicemi
- **THEN** výsledné `gps` je to z EXIF

#### Scenario: Místo bez souřadnic
- **WHEN** `souradnice_mist` má pro místo `null`
- **THEN** soubor bez vlastního GPS nemá výsledné `gps`
