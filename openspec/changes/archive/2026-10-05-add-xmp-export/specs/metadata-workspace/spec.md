## ADDED Requirements

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci. Dokončení SHALL
uložit neuložené změny a zkontrolovat úplnost podle lišty chybějících
údajů; chybí-li něco, MUST ukázat co a dokončit jen po dalším
potvrzení. Pak SHALL akci exportovat a nastavit `dokonceno` na datum
dokončení. Selže-li zápis některého sidecaru, akce MUST NOT být
označena jako dokončená. Dokončení vyžaduje zámek akce.

#### Scenario: Úplná akce
- **WHEN** akci nic nechybí a uživatel ji dokončí
- **THEN** sidecary jsou zapsané, `dokonceno` je nastavené a seznam
  akcí ji ukazuje jako *hotovo*

#### Scenario: Neúplná akce
- **WHEN** 14 souborů nemá datum a uživatel klikne na Dokončit akci
- **THEN** plocha ukáže „14 souborů bez data“ a dokončí až po
  potvrzení

### Requirement: Export z plochy
Pracovní plocha SHALL nabídnout tlačítko Exportovat, které uloží
neuložené změny, akci exportuje bez kontroly úplnosti a bez změny
`dokonceno` a ukáže počty zapsaných, nezměněných a selhaných sidecarů.
Ve vývojovém režimu SHALL plocha uvést, že sidecary jdou do pracovního
adresáře.

#### Scenario: Export rozpracované akce
- **WHEN** uživatel u rozpracované akce klikne na Exportovat
- **THEN** sidecary se zapíšou a akce zůstane *rozpracováno*

### Requirement: Stav exportu na ploše
Při otevření akce SHALL plocha u tlačítka Exportovat ukázat výsledek
kontroly nanečisto („12 sidecarů neaktuálních“, nebo že je vše
aktuální). Po každém uložení, které změní verzi `_metadata.json` oproti
záznamu o exportu, SHALL plocha ukázat „neexportované změny“, dokud se
akce znovu neexportuje.

#### Scenario: Otevření neaktuální akce
- **WHEN** uživatel otevře akci, u které 12 sidecarů chybí nebo se liší
- **THEN** plocha ukáže „12 sidecarů neaktuálních“

#### Scenario: Úprava po exportu
- **WHEN** uživatel u exportované akce změní popis a změna se uloží
- **THEN** plocha ukáže „neexportované změny“ až do dalšího exportu

## REMOVED Requirements

### Requirement: Dokončení akce v prototypu
**Reason**: Dokončení a export jsou nově implementované.
**Migration**: Požadavky Dokončení akce a Export z plochy.
