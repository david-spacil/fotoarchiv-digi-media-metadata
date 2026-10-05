## Purpose

Najít v archivu složky akcí, ukázat jejich stav zpracování a umožnit
vybrat akci, se kterou se bude pracovat.

## ADDED Requirements

### Requirement: Seznam akcí
Aplikace SHALL zobrazit seznam složek první úrovně archivu, jejichž
název odpovídá vzoru `YYYY-MM-DD název`, seřazený podle data sestupně.
Ostatní složky a soubory první úrovně MUST být ignorovány a nesmí se
měnit.

#### Scenario: Složky mimo vzor
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky…`, `přetřídit`
  a `_metadata.xlsx`
- **THEN** seznam obsahuje jen `2026-04-28 kontrola Stezky…`

### Requirement: Stav akce
U každé akce SHALL seznam uvádět počet souborů v kořeni (bez
`Thumbs.db`) a stav: *nezpracováno* (bez `_metadata.json`),
*rozpracováno* (`_metadata.json` existuje, akce není dokončená) nebo
*hotovo*.

#### Scenario: Akce bez metadat
- **WHEN** složka akce nemá `_metadata.json`
- **THEN** seznam ji ukáže jako *nezpracováno*

#### Scenario: Akce s metadaty
- **WHEN** k akci existuje `_metadata.json` a akce není označená jako
  dokončená
- **THEN** seznam ji ukáže jako *rozpracováno*

### Requirement: Archiv jen pro čtení
V prototypu aplikace MUST NOT zapisovat, přesouvat ani mazat nic
v archivu. `_metadata.json` SHALL číst i ukládat v pracovním adresáři
mimo archiv, který zrcadlí názvy složek akcí.

#### Scenario: Uložení v prototypu
- **WHEN** uživatel uloží metadata akce
- **THEN** soubor vznikne v pracovním adresáři pod názvem složky akce
  a archiv zůstane beze změny
