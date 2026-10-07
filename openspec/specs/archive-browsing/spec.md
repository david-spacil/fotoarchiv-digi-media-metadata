# archive-browsing Specification

## Purpose

Najít v archivu složky akcí, ukázat jejich stav zpracování a umožnit
vybrat akci, se kterou se bude pracovat.

## Requirements

### Requirement: Seznam akcí
Aplikace SHALL zobrazit seznam složek první úrovně archivu, jejichž
název odpovídá vzoru `YYYY-MM-DD název`, seřazený podle data sestupně.
Ostatní složky a soubory první úrovně MUST být ignorovány a nesmí se
měnit. Výjimkou jsou soubory indexu `_INDEX.html` a `_INDEX.md`, které
v produkčním režimu zapisuje aplikace (viz `archive-index`).

#### Scenario: Složky mimo vzor
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky…`, `přetřídit`
  a `_metadata.xlsx`
- **THEN** seznam obsahuje jen `2026-04-28 kontrola Stezky…`

#### Scenario: Index v kořeni archivu
- **WHEN** kořen archivu obsahuje `_INDEX.html` a `_INDEX.md`
- **THEN** seznam akcí je neuvádí a `_metadata.xlsx` zůstane beze změny

### Requirement: Stav akce
U každé akce SHALL seznam uvádět počet souborů v kořeni (bez
`Thumbs.db`, `_metadata.json` a sidecarů `.xmp`) a stav:
*nezpracováno* (bez `_metadata.json`), *rozpracováno*
(`_metadata.json` existuje, akce není dokončená) nebo *hotovo*.
U akce *hotovo* s neexportovanými změnami SHALL seznam uvést „změněno
po exportu“.

#### Scenario: Akce bez metadat
- **WHEN** složka akce nemá `_metadata.json`
- **THEN** seznam ji ukáže jako *nezpracováno*

#### Scenario: Akce s metadaty
- **WHEN** k akci existuje `_metadata.json` a akce není označená jako
  dokončená
- **THEN** seznam ji ukáže jako *rozpracováno*

#### Scenario: Exportovaná akce
- **WHEN** kořen akce obsahuje 50 fotek a 50 sidecarů `.xmp`
- **THEN** seznam u akce uvádí 50 souborů

#### Scenario: Dokončená akce upravená po exportu
- **WHEN** dokončená akce má neexportované změny
- **THEN** seznam ji ukáže jako *hotovo* s poznámkou „změněno po
  exportu“

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
z pracovního adresáře do archivu. Převzetí MUST přeskočit
akce, které už `_metadata.json` v archivu mají, a vypsat je.

#### Scenario: Akce už má metadata v archivu
- **WHEN** akce má `_metadata.json` v pracovním adresáři i v archivu
- **THEN** převzetí ji přeskočí, archivní soubor nezmění a akci vypíše
