## ADDED Requirements

### Requirement: Místa bez souřadnic v liště
Lišta chybějících údajů SHALL ukázat názvy míst, o jejichž souřadnicích
není rozhodnuto a které jsou výsledným místem aspoň jednoho souboru bez
GPS. Kliknutí SHALL vybrat dotčené soubory a otevřít volbu souřadnic.

#### Scenario: Nerozhodnuté místo
- **WHEN** 12 souborů bez GPS má místo `Vysočany` a `souradnice_mist`
  ho neobsahuje
- **THEN** lišta ukáže „1 místo bez souřadnic“ a kliknutí vybere
  12 souborů

#### Scenario: Všechny soubory mají GPS
- **WHEN** všechny soubory s místem `Holštejn` mají GPS z EXIF
- **THEN** lišta `Holštejn` neukazuje
