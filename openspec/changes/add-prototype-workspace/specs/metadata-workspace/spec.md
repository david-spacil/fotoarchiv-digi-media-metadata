## Purpose

Provést uživatele prvním zpracováním akce a pak nabídnout pracovní
plochu pro přiřazování metadat akci, skupinám a jednotlivým souborům.

## ADDED Requirements

### Requirement: Průvodce prvním otevřením
Při otevření akce bez `_metadata.json` SHALL aplikace spustit průvodce
v pořadí: úklid → načtení a skupiny → údaje akce → autoři skupin.
Průvodce MUST pokrýt všechny povinné údaje akce a skupin; údaje
jednotlivých souborů do něj nepatří. Po dokončení průvodce SHALL otevřít
pracovní plochu. Akce s `_metadata.json` SHALL otevřít
rovnou pracovní plochu.

#### Scenario: První otevření
- **WHEN** uživatel otevře akci ve stavu *nezpracováno*
- **THEN** začne průvodce krokem úklid

#### Scenario: Autoři skupin v průvodci
- **WHEN** uživatel v průvodci dokončí údaje akce
- **THEN** následuje krok, kde každé skupině zadá autory, a teprve pak
  se otevře pracovní plocha

#### Scenario: Náhledy v kroku autoři skupin
- **WHEN** průvodce ukáže krok autoři skupin
- **THEN** u každé skupiny je pás několika náhledů jejích souborů

#### Scenario: Další otevření
- **WHEN** uživatel otevře akci ve stavu *rozpracováno*
- **THEN** otevře se rovnou pracovní plocha

### Requirement: Úprava skupin
V průvodci i na pracovní ploše SHALL jít skupinu přejmenovat, sloučit
s jinou, vytvořit novou a přesunout do ní vybrané soubory.

#### Scenario: Sloučení skupin
- **WHEN** uživatel sloučí dvě navržené skupiny
- **THEN** všechny jejich soubory patří do výsledné skupiny a ruční
  údaje u souborů zůstanou

#### Scenario: Skupina zůstane prázdná
- **WHEN** uživatel přesune poslední soubor ze skupiny jinam
- **THEN** skupina bez vlastních údajů (kromě názvu a přístroje) se
  smaže; skupinu se zadanými údaji aplikace nabídne smazat nebo ponechat

### Requirement: Údaje akce
Údaje akce SHALL být název, datum od–do, popis, místa, účastníci
a autoři. Místa a účastníci SHALL být seznamy zadávané jako štítky.
Účastníci jsou výčet důležitých lidí na akci a přednostní návrhy při
označování osob; MUST NOT se dědit na skupiny ani soubory.

#### Scenario: Více míst
- **WHEN** uživatel do pole místo napíše `Molenburk, Housko`
- **THEN** akce má dvě místa `Molenburk` a `Housko`

### Requirement: Předvyplnění údajů akce
Krok údaje akce SHALL předvyplnit název z názvu složky (bez data)
a `datum_od`/`datum_do` z nejstaršího a nejnovějšího data souborů, nebo
z data v názvu složky, pokud soubory datum nemají.

#### Scenario: Předvyplnění
- **WHEN** průvodce dojde ke kroku údaje akce u
  `2026-04-28 kontrola Stezky Drahanskou vrchovinou`
- **THEN** název je `kontrola Stezky Drahanskou vrchovinou` a datum
  od–do odpovídá datům fotek

### Requirement: Mřížka a výběr
Pracovní plocha SHALL zobrazit náhledy rozdělené podle skupin. Uživatel
SHALL moci vybrat jeden soubor kliknutím, přidat do výběru
s modifikátorem, vybrat rozsah se Shiftem, vybrat tažením myši
a vybrat celou skupinu kliknutím na její hlavičku.

#### Scenario: Výběr rozsahu
- **WHEN** uživatel klikne na první soubor a se Shiftem na pátý
- **THEN** je vybráno pět souborů

### Requirement: Formulář podle výběru
Formulář vedle mřížky SHALL upravovat akci, když není nic vybráno,
skupinu, když je vybrána hlavička skupiny, a vybrané soubory, když je
vybrán jeden nebo více souborů. Zděděné hodnoty SHALL být viditelně
odlišené od zadaných a MUST jít přepsat i vrátit na zděděné. Vyprázdnění
pole SHALL znamenat vrácení na zděděné (pole se smaže); přepsání na
prázdnou hodnotu prototyp nepodporuje.

#### Scenario: Hromadné přepsání
- **WHEN** uživatel vybere 12 souborů a zadá popis
- **THEN** všech 12 souborů má tento popis zadaný na úrovni souboru

#### Scenario: Rozdílné hodnoty ve výběru
- **WHEN** vybrané soubory mají v poli různé hodnoty
- **THEN** formulář to u pole vyznačí a pole nezmění, dokud do něj
  uživatel nezapíše

#### Scenario: Vyprázdnění pole
- **WHEN** uživatel u souboru smaže celý zadaný popis
- **THEN** pole zmizí ze záznamu souboru a zobrazí se zděděný popis

### Requirement: Dokončení akce v prototypu
Prototyp akci nedokončuje ani neexportuje XMP. Pracovní plocha SHALL
to uživateli trvale ukazovat spolu s tím, že se změny ukládají
průběžně.

#### Scenario: Hledání dokončení
- **WHEN** uživatel má vyplněné všechny údaje
- **THEN** plocha ukazuje, že dokončení a export v prototypu nejsou

### Requirement: Lišta chybějících údajů
Pracovní plocha SHALL průběžně ukazovat, co chybí: akce bez názvu nebo
data, skupiny bez autorů, soubory bez data a soubory bez skupiny.
Kliknutí na položku SHALL vybrat dotčené soubory nebo skupiny.

#### Scenario: Skupina bez autorů
- **WHEN** skupina nemá autory a žádný její soubor je nepřepisuje
- **THEN** lišta ukáže „1 skupina bez autorů“
