## MODIFIED Requirements

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci; je to jediné
tlačítko plochy, které zapisuje sidecary. Dokončení SHALL
uložit neuložené změny a zkontrolovat úplnost podle lišty chybějících
údajů a nálezy kontroly akce (viz `event-consistency`); chybí-li něco
nebo je-li nález, MUST ukázat co a dokončit jen po dalším potvrzení.
Pak SHALL akci exportovat, v produkčním režimu odebrat ze
složky akce příponu `.ignored` (viz `event-visibility`) a nastavit
`dokonceno` na datum dokončení. Má-li akce `dokonceno` už nastavené,
dokončení ho MUST NOT změnit: `dokonceno` je datum prvního dokončení.
Selže-li u akce bez `dokonceno` zápis některého sidecaru nebo
přejmenování složky, akce MUST NOT být označena jako dokončená.
Selže-li u akce s `dokonceno`, akce MUST zůstat dokončená se stejným
datem a plocha SHALL chybu ukázat.
Dokončení vyžaduje zámek akce.

U dokončené akce SHALL být tlačítko neaktivní, dokud není co dokončovat:
žádné neuložené ani neexportované změny, žádné neaktuální sidecary
a poslední export neselhal. Jakmile něco z toho nastane, tlačítko SHALL
být znovu aktivní. Text tlačítka se nemění.

#### Scenario: Úplná akce
- **WHEN** akci nic nechybí a uživatel ji dokončí
- **THEN** sidecary jsou zapsané, `dokonceno` je nastavené a seznam
  akcí ji ukazuje jako *hotovo*

#### Scenario: Neúplná akce
- **WHEN** 14 souborů nemá datum a uživatel klikne na Dokončit akci
- **THEN** plocha ukáže „14 souborů bez data“ a dokončí až po
  potvrzení

#### Scenario: Akce s nepodporovaným souborem
- **WHEN** kořen akce obsahuje `zprava.pdf` a uživatel klikne na
  Dokončit akci
- **THEN** plocha ukáže „1 nepodporovaný soubor v kořeni“ a po
  potvrzení akci dokončí; `zprava.pdf` zůstane v kořeni

#### Scenario: Selhání přejmenování
- **WHEN** sidecary se zapíšou, ale složku akce nejde přejmenovat
- **THEN** akce nemá `dokonceno` a plocha ukáže, že akci nešlo
  zveřejnit

#### Scenario: Dokončená akce beze změn
- **WHEN** uživatel otevře dokončenou akci se všemi sidecary aktuálními
- **THEN** tlačítko Dokončit akci je neaktivní a u něj je „Dokončeno …“

#### Scenario: Úprava dokončené akce
- **WHEN** uživatel u dokončené akce změní popis souboru
- **THEN** tlačítko Dokončit akci je aktivní až do dalšího dokončení

#### Scenario: Opakované dokončení zachová datum
- **WHEN** akce dokončená 2026-10-01 se 8. 10. 2026 upraví a znovu
  dokončí
- **THEN** sidecary jsou aktuální a `dokonceno` je dál `2026-10-01`

#### Scenario: Selhání exportu u dokončené akce
- **WHEN** u akce dokončené 2026-10-01 při opakovaném dokončení selže
  zápis sidecaru `foto.jpg.xmp`
- **THEN** `dokonceno` je dál `2026-10-01`, seznam akcí ji ukazuje
  jako *hotovo*, plocha ukáže chybu u `foto.jpg` a tlačítko Dokončit
  akci zůstane aktivní

#### Scenario: Rozpracovaná akce
- **WHEN** akce ještě nemá `dokonceno`
- **THEN** tlačítko Dokončit akci je aktivní (má-li uživatel zámek)

### Requirement: Stav exportu na ploše
Při otevření akce SHALL plocha u tlačítka Dokončit akci ukázat výsledek
kontroly nanečisto („12 sidecarů neaktuálních“, nebo že je vše
aktuální). Po každém uložení, které změní verzi `_metadata.json` oproti
záznamu o exportu, SHALL plocha ukázat „neexportované změny“, dokud se
akce znovu nedokončí. Po dokončení SHALL plocha ukázat počty
zapsaných, nezměněných a selhaných sidecarů; ve vývojovém režimu SHALL
uvést, že sidecary jdou do pracovního adresáře.

#### Scenario: Otevření neaktuální akce
- **WHEN** uživatel otevře akci, u které 12 sidecarů chybí nebo se liší
- **THEN** plocha ukáže „12 sidecarů neaktuálních“

#### Scenario: Úprava po exportu
- **WHEN** uživatel u dokončené akce změní popis a změna se uloží
- **THEN** plocha ukáže „neexportované změny“ až do dalšího dokončení

#### Scenario: Dokončení ve vývojovém režimu
- **WHEN** uživatel ve vývojovém režimu dokončí akci
- **THEN** plocha ukáže počty sidecarů s poznámkou, že jdou do
  pracovního adresáře

## REMOVED Requirements

### Requirement: Export z plochy
**Reason**: Export rozpracované akce je od skrytí nedokončených akcí
před Immichem bez užitku a dokončenou akci aktualizuje opakované
dokončení, které teď zachová datum a stav akce (issue #20).
**Migration**: Po úpravě akce použít Dokončit akci; dávkový export bez
aplikace dál `python -m fotoarchiv exportovat [AKCE]`.
