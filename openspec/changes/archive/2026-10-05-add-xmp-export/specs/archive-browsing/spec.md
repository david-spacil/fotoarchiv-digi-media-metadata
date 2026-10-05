## MODIFIED Requirements

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
