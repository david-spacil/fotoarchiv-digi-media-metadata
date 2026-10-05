## ADDED Requirements

### Requirement: Metadata ve složce akce
V produkčním režimu SHALL aplikace číst i ukládat `_metadata.json`
přímo ve složce akce v archivu. Ve vývojovém režimu (výchozím) SHALL
číst i ukládat v pracovním adresáři mimo archiv, který zrcadlí názvy
složek akcí, a MUST NOT do archivu nic zapisovat, přesouvat ani mazat.
Režim MUST být při spuštění zvolen výslovně a vypsán.

#### Scenario: Uložení v produkčním režimu
- **WHEN** uživatel v produkčním režimu uloží metadata akce
- **THEN** soubor `_metadata.json` vznikne nebo se změní ve složce akce

#### Scenario: Uložení ve vývojovém režimu
- **WHEN** uživatel ve vývojovém režimu uloží metadata akce
- **THEN** soubor vznikne v pracovním adresáři pod názvem složky akce
  a archiv zůstane beze změny

### Requirement: Atomické uložení
Uložení `_metadata.json` MUST být atomické: soubor je vždy buď celý
starý, nebo celý nový, i při výpadku během zápisu.

#### Scenario: Výpadek při zápisu
- **WHEN** server spadne uprostřed ukládání
- **THEN** ve složce akce zůstane předchozí platný `_metadata.json`

### Requirement: Převzetí z pracovního adresáře
Aplikace SHALL nabídnout jednorázové převzetí `_metadata.json`
z pracovního adresáře prototypu do archivu. Převzetí MUST přeskočit
akce, které už `_metadata.json` v archivu mají, a vypsat je.

#### Scenario: Akce už má metadata v archivu
- **WHEN** akce má `_metadata.json` v pracovním adresáři i v archivu
- **THEN** převzetí ji přeskočí, archivní soubor nezmění a akci vypíše

## REMOVED Requirements

### Requirement: Archiv jen pro čtení
**Reason**: Produkční režim ukládá metadata do archivu a provádí úklid.
**Migration**: Chování zůstává ve vývojovém režimu, viz požadavek
„Metadata ve složce akce“; rozpracovaná metadata převezme „Převzetí
z pracovního adresáře“.
