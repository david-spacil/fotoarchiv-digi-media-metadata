## MODIFIED Requirements

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci. Dokončení SHALL
uložit neuložené změny a zkontrolovat úplnost podle lišty chybějících
údajů; chybí-li něco, MUST ukázat co a dokončit jen po dalším
potvrzení. Pak SHALL akci exportovat, v produkčním režimu odebrat ze
složky akce příponu `.ignored` (viz `event-visibility`) a nastavit
`dokonceno` na datum dokončení. Selže-li zápis některého sidecaru nebo
přejmenování složky, akce MUST NOT být označena jako dokončená.
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
  nebo exportu

#### Scenario: Rozpracovaná akce
- **WHEN** akce ještě nemá `dokonceno`
- **THEN** tlačítko Dokončit akci je aktivní (má-li uživatel zámek)
