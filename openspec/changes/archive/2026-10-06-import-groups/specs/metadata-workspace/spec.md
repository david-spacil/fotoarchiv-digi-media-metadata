## ADDED Requirements

### Requirement: Skupiny z importu v průvodci
Existuje-li k akci bez `_metadata.json` návrh skupin z importu, SHALL
průvodce prvním otevřením v kroku načtení a skupiny použít jeho skupiny
a přiřazení pro soubory, které návrh uvádí a jsou v kořeni akce.
Ostatní soubory SHALL dostat automatický návrh podle přístroje a vzoru
názvu. Po prvním uložení `_metadata.json` SHALL server návrh smazat.
Chybí-li návrh (např. smazaný pracovní adresář), průvodce SHALL
postupovat jako dosud.

#### Scenario: Podsložky z importu jako skupiny
- **WHEN** uživatel otevře novou akci, do které importoval `DOD 2015`
  s volbou „podle podsložek“
- **THEN** krok skupin ukáže skupiny `DOD 2015_Bara Pokusna`,
  `DOD 2015_Jana`, `DOD 2015_Pavla` a `DOD 2015_Verca` a krok autorů
  skupin se ptá na autory každé z nich

#### Scenario: Soubor mimo návrh
- **WHEN** v kořeni akce je kromě importovaných souborů i soubor, který
  návrh neuvádí
- **THEN** ten soubor dostane automaticky navrženou skupinu

#### Scenario: Návrh po uložení
- **WHEN** uživatel v průvodci poprvé uloží `_metadata.json`
- **THEN** návrh skupin z importu přestane existovat a další otevření
  ho nepoužije
