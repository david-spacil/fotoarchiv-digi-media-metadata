# metadata-workspace Specification

## Purpose

Provést uživatele prvním zpracováním akce a pak nabídnout pracovní
plochu pro přiřazování metadat akci, skupinám a jednotlivým souborům.

## Requirements

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
Místo skupiny a souboru SHALL být jedna hodnota s návrhy z míst akce.
Účastníci jsou výčet důležitých lidí na akci a přednostní návrhy při
označování osob; MUST NOT se dědit na skupiny ani soubory.

Položky seznamu SHALL oddělovat jen Enter; čárka je součást hodnoty
(adresy, jména).

#### Scenario: Více míst
- **WHEN** uživatel do pole místa napíše `Molenburk`, Enter, `Housko`,
  Enter
- **THEN** akce má dvě místa `Molenburk` a `Housko`

#### Scenario: Adresa s čárkou
- **WHEN** uživatel do pole místa napíše `Adamova 150, Adamov` a Enter
- **THEN** akce má jedno místo `Adamova 150, Adamov`

#### Scenario: Místo u fotky
- **WHEN** akce má místa `Molenburk` a `Housko` a uživatel u fotky
  zadává místo
- **THEN** formulář nabídne `Molenburk` a `Housko`

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

### Requirement: Lišta chybějících údajů
Pracovní plocha SHALL průběžně ukazovat, co chybí: akce bez názvu nebo
data, skupiny bez autorů, soubory bez data, soubory bez skupiny
a soubory bez místa, pokud má akce víc míst. Kliknutí na položku SHALL vybrat dotčené soubory nebo skupiny.
Soubory označené k vyřazení MUST NOT být v lištu započítány; skupina,
jejíž všechny soubory jsou označené, se nepočítá mezi skupiny bez
autorů.

#### Scenario: Skupina bez autorů
- **WHEN** skupina nemá autory a žádný její soubor je nepřepisuje
- **THEN** lišta ukáže „1 skupina bez autorů“

#### Scenario: Soubory bez místa
- **WHEN** akce má dvě místa a 30 souborů nemá místo zadané u sebe ani
  u skupiny
- **THEN** lišta ukáže „30 souborů bez místa“

#### Scenario: Označený soubor bez data
- **WHEN** soubor bez data je označený k vyřazení
- **THEN** lišta ho mezi soubory bez data nepočítá

### Requirement: Místa bez souřadnic v liště
Lišta chybějících údajů SHALL ukázat názvy míst, o jejichž souřadnicích
není rozhodnuto a které jsou výsledným místem aspoň jednoho souboru bez
GPS. Kliknutí SHALL vybrat dotčené soubory a otevřít volbu souřadnic.

#### Scenario: Nerozhodnuté místo
- **WHEN** 12 souborů bez GPS má místo `Vysočany` a `souradnice_mist`
  ho neobsahuje
- **THEN** lišta ukáže „1 místo bez souřadnic“ a kliknutí vybere
  12 souborů

#### Scenario: Všechny soubory mají GPS
- **WHEN** všechny soubory s místem `Holštejn` mají GPS z EXIF
- **THEN** lišta `Holštejn` neukazuje

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

### Requirement: Označení k vyřazení
Na pracovní ploše (mřížka i lupa) SHALL uživatel moci vybrané soubory
označit k vyřazení klávesou Del nebo tlačítkem. Jsou-li všechny vybrané
soubory už označené, Del a tlačítko SHALL označení zrušit. Označení
SHALL být uloženo u souboru v `_metadata.json` jako `"vyradit": true`
a průběžně ukládáno jako ostatní změny. Označit jde jen soubor, ne
skupinu ani akci. Bez zámku akce (jen ke čtení) MUST NOT jít označení
měnit.

#### Scenario: Hromadné označení
- **WHEN** uživatel vybere v mřížce 5 souborů a stiskne Del
- **THEN** všech 5 souborů má v `_metadata.json` `"vyradit": true`

#### Scenario: Zrušení označení
- **WHEN** uživatel vybere 2 označené soubory a stiskne Del
- **THEN** ani jeden už označení nemá

#### Scenario: Smíšený výběr
- **WHEN** výběr obsahuje označené i neoznačené soubory a uživatel
  stiskne Del
- **THEN** všechny vybrané soubory jsou označené

#### Scenario: Del v textovém poli
- **WHEN** je kurzor ve formulářovém poli a uživatel stiskne Del
- **THEN** maže se text, označení souborů se nemění

### Requirement: Zobrazení označených souborů
Soubory označené k vyřazení SHALL být v mřížce i pásu lupy vizuálně
odlišené a zůstávají na svém místě. Pracovní plocha SHALL ukazovat
počet označených souborů a nabídnout provedení úklidu.

#### Scenario: Označený soubor v mřížce
- **WHEN** soubor `P1503712.JPG` je označený k vyřazení
- **THEN** jeho dlaždice je odlišená a lišta ukazuje „1 soubor
  k vyřazení“ s tlačítkem úklidu

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
- **THEN** krok skupin ukáže skupiny `DOD 2015_Bara Tesar`,
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
