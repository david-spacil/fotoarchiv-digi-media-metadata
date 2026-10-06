## MODIFIED Requirements

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci. Dokončení SHALL
uložit neuložené změny a zkontrolovat úplnost podle lišty chybějících
údajů; chybí-li něco, MUST ukázat co a dokončit jen po dalším
potvrzení. Pak SHALL akci exportovat a nastavit `dokonceno` na datum
dokončení. Selže-li zápis některého sidecaru, akce MUST NOT být
označena jako dokončená. Dokončení vyžaduje zámek akce.

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

## ADDED Requirements

### Requirement: Kalendář u data pořízení
Pole Datum pořízení SHALL vedle textového zadání nabídnout výběr dne
z kalendáře. Zvolený den SHALL nahradit datum a zachovat čas, pokud ho
hodnota má; hodnota bez času SHALL zůstat bez času. Ve výběru
s rozdílnými hodnotami SHALL zvolený den přepsat datum u všech
vybraných souborů, každému se zachováním jeho vlastního času.

#### Scenario: Změna dne se zachováním času
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel v kalendáři
  zvolí 29. 4. 2026
- **THEN** datum souboru je `2026-04-29T09:44:36`

#### Scenario: Datum bez času
- **WHEN** WhatsApp fotka má datum `2026-04-28` a uživatel zvolí
  30. 4. 2026
- **THEN** datum souboru je `2026-04-30`

#### Scenario: Prázdné datum
- **WHEN** soubor nemá datum a uživatel zvolí 28. 4. 2026
- **THEN** datum souboru je `2026-04-28`

### Requirement: Stálá výška hlavičky
Změna stavu ukládání (Uloženo, Neuloženo, Ukládám…, Neuloženo –
konflikt, Jen ke čtení) MUST NOT měnit výšku hlavičky stránky.

#### Scenario: Přepnutí na Neuloženo
- **WHEN** uživatel změní pole a stav se přepne z „Uloženo“ na
  „Neuloženo“ a zpět
- **THEN** hlavička ani obsah pod ní neposkočí
