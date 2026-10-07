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
Pracovní plocha SHALL zobrazit náhledy rozdělené podle skupin, nebo
podle dnů (viz Zobrazení podle data). Uživatel SHALL moci vybrat jeden
soubor kliknutím, přidat do výběru s modifikátorem, vybrat rozsah se
Shiftem, vybrat tažením myši a v zobrazení po skupinách vybrat celou
skupinu kliknutím na její hlavičku.

#### Scenario: Výběr rozsahu
- **WHEN** uživatel klikne na první soubor a se Shiftem na pátý
- **THEN** je vybráno pět souborů

#### Scenario: Rozsah v zobrazení podle data
- **WHEN** v zobrazení podle data uživatel klikne na první soubor a se
  Shiftem na pátý a soubory patří do dvou různých skupin
- **THEN** je vybráno pět souborů, které jsou v mřížce mezi nimi

### Requirement: Formulář podle výběru
Formulář vedle mřížky SHALL upravovat akci, když není nic vybráno,
skupinu, když je vybrána hlavička skupiny, a vybrané soubory, když je
vybrán jeden nebo více souborů. Zděděné hodnoty SHALL být viditelně
odlišené od zadaných a MUST jít přepsat i vrátit na zděděné. Vyprázdnění
pole SHALL znamenat vrácení na zděděné (pole se smaže); přepsání na
prázdnou hodnotu aplikace nepodporuje.

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

### Requirement: Kalendář u data pořízení
Pole Datum pořízení SHALL mít dva samostatné vstupy: den a čas
(hodiny, minuty, sekundy), oba s nativním výběrem prohlížeče. Uložená
hodnota SHALL mít tvar `RRRR-MM-DD`, nebo `RRRR-MM-DDTHH:MM[:SS]`, je-li
zadán čas. Prázdný čas SHALL znamenat hodnotu jen s datem. Smazání času
SHALL ponechat datum; smazání dne SHALL smazat celou hodnotu. Čas bez
dne MUST NOT jít uložit.

Ve výběru více souborů SHALL změna dne přepsat datum u všech vybraných
souborů, každému se zachováním jeho vlastního času (nebo jeho absence),
a změna času SHALL přepsat čas u všech vybraných souborů s datem,
každému se zachováním jeho dne. Vstup dne SHALL ukazovat den, je-li
u všech vybraných souborů stejný, jinak SHALL zůstat prázdný; totéž
platí pro čas. Při rozdílných hodnotách SHALL vedle vstupů stát text
„rozdílné hodnoty – zápisem přepíšete vše“.

#### Scenario: Změna dne se zachováním času
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel zvolí den
  29. 4. 2026
- **THEN** datum souboru je `2026-04-29T09:44:36`

#### Scenario: Datum bez času
- **WHEN** WhatsApp fotka má datum `2026-04-28` a uživatel zvolí den
  30. 4. 2026
- **THEN** datum souboru je `2026-04-30` a vstup času zůstane prázdný

#### Scenario: Prázdné datum
- **WHEN** soubor nemá datum a uživatel zvolí den 28. 4. 2026
- **THEN** datum souboru je `2026-04-28`

#### Scenario: Doplnění času
- **WHEN** soubor má datum `2026-04-28` a uživatel zadá čas 14:05:10
- **THEN** datum souboru je `2026-04-28T14:05:10`

#### Scenario: Smazání času
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel čas smaže
- **THEN** datum souboru je `2026-04-28`

#### Scenario: Smazání dne
- **WHEN** soubor má datum `2026-04-28T09:44:36` a uživatel smaže den
- **THEN** soubor nemá datum zadané

#### Scenario: Čas bez dne
- **WHEN** soubor nemá datum
- **THEN** vstup času nejde vyplnit

#### Scenario: Rozdílné časy ve výběru
- **WHEN** vybrané soubory mají `2026-04-28T09:44:36`
  a `2026-04-28T10:02:11`
- **THEN** vstup dne ukazuje 28. 4. 2026, vstup času je prázdný a vedle
  vstupů stojí „rozdílné hodnoty – zápisem přepíšete vše“

#### Scenario: Nový čas ve výběru
- **WHEN** vybrané soubory mají `2026-04-28T09:44:36`
  a `2026-04-29T10:02:11` a uživatel zadá čas 12:00:00
- **THEN** soubory mají `2026-04-28T12:00:00` a `2026-04-29T12:00:00`

#### Scenario: Nový den ve výběru
- **WHEN** vybrané soubory mají `2026-04-28T09:44:36` a `2026-04-28`
  a uživatel zvolí den 1. 5. 2026
- **THEN** soubory mají `2026-05-01T09:44:36` a `2026-05-01`

### Requirement: Stálá výška hlavičky
Změna stavu ukládání (Uloženo, Neuloženo, Ukládám…, Neuloženo –
konflikt, Jen ke čtení) MUST NOT měnit výšku hlavičky stránky.

#### Scenario: Přepnutí na Neuloženo
- **WHEN** uživatel změní pole a stav se přepne z „Uloženo“ na
  „Neuloženo“ a zpět
- **THEN** hlavička ani obsah pod ní neposkočí

### Requirement: Osoby jen pro čtení
Formulář souboru SHALL ukázat jména z jeho `obliceje` jako pole jen pro
čtení s poznámkou, že pochází z Immiche; MUST NOT jít upravit.
U výběru více souborů SHALL ukázat jména všech vybraných. Formulář
skupiny ani akce pole osob MUST NOT nabízet. Není-li Immich nastaven,
pole SHALL místo osob uvést, že Immich není napojen. Chybějící osoby
MUST NOT být v liště chybějících údajů.

#### Scenario: Soubor s obličeji
- **WHEN** uživatel vybere soubor s obličejem `Lečbychová, Olga`
- **THEN** formulář ukáže `Lečbychová, Olga` zašedle s poznámkou
  „z Immiche“ a pole nejde upravit

#### Scenario: Formulář skupiny
- **WHEN** uživatel vybere hlavičku skupiny
- **THEN** formulář pole osob nemá

### Requirement: Autoři akce v průvodci
Krok autoři skupin průvodce SHALL nad skupinami nabídnout pole autoři
celé akce, které upravuje `autori` akce a ukazuje jejich uloženou
hodnotu. Skupina bez vlastních autorů SHALL v tomto kroku ukázat autory
akce jako zděděné a MUST se nepočítat mezi skupiny bez autorů. Autoři
akce se MUST NOT kopírovat do skupin; skupina je SHALL moci přepsat
vlastními. Krok údaje akce pole autorů neukazuje.

#### Scenario: Autoři celé akce
- **WHEN** uživatel v kroku autoři skupin zadá autory celé akce
  `Spáčil, David` a `Kopáčová, Zuzana`
- **THEN** akce má `autori` = [`Spáčil, David`, `Kopáčová, Zuzana`]
  a skupina `g9` bez vlastních autorů je ukazuje jako zděděné z akce

#### Scenario: Dokončení bez upozornění
- **WHEN** akce má autory a žádná skupina vlastní autory nemá
- **THEN** dokončení průvodce neupozorní na skupiny bez autorů
  a skupiny se uloží bez pole `autori`

#### Scenario: Skupina s vlastními autory
- **WHEN** akce má autory `Spáčil, David` a skupina `g9` má vlastní
  autory `Kopáčová, Zuzana`
- **THEN** skupina `g9` si ponechá `Kopáčová, Zuzana` jako zadané
  u skupiny

#### Scenario: Předvyplnění
- **WHEN** akce už má autory (zadané dřív na ploše) a uživatel se
  v průvodci vrátí ke kroku autoři skupin
- **THEN** pole autoři celé akce je ukazuje

### Requirement: Přepínač zobrazení
Pracovní plocha SHALL mít přepínač Po skupinách / Podle data, který
platí pro mřížku i filmový pás. Výběr a aktuální soubor MUST zůstat při
přepnutí zachované. Volba SHALL platit v tomtéž prohlížeči i pro další
otevřené akce a po obnovení stránky. Průvodce prvním otevřením SHALL
zobrazovat soubory vždy po skupinách.

#### Scenario: Přepnutí s výběrem
- **WHEN** jsou v zobrazení po skupinách vybrané tři soubory a uživatel
  přepne na Podle data
- **THEN** mřížka ukáže soubory podle data a tytéž tři soubory jsou
  vybrané

#### Scenario: Volba přetrvá
- **WHEN** uživatel zvolí Podle data, vrátí se na seznam akcí
  a otevře jinou akci
- **THEN** plocha nové akce je v zobrazení podle data

#### Scenario: Průvodce
- **WHEN** je zvoleno Podle data a uživatel poprvé otevře akci
- **THEN** krok Načtení a skupiny ukazuje soubory po skupinách

### Requirement: Zobrazení podle data
V zobrazení podle data SHALL plocha ukázat všechny soubory akce v jednom
pořadí podle zděděného data pořízení, při shodě podle názvu souboru,
rozdělené předěly po kalendářních dnech. Hlavička dne SHALL ukázat den
v týdnu, datum a počet souborů. Soubory bez data SHALL být na konci
v oddílu „Bez data“. Klik na hlavičku dne nebo „Bez data“ SHALL vybrat
soubory oddílu.

#### Scenario: Dva přístroje téhož dne
- **WHEN** akce má skupiny `Panasonic DC-G9` a `samsung SM-A528B`
  a obě obsahují fotky z 28. 4. 2026
- **THEN** pod hlavičkou `út 28. 4. 2026` jsou fotky obou skupin
  promíchané podle času pořízení

#### Scenario: Vícedenní akce
- **WHEN** soubory akce mají data 27. a 28. 4. 2026
- **THEN** mřížka má dva oddíly, nejdřív 27. 4., pak 28. 4.

#### Scenario: Soubor bez data
- **WHEN** soubor nemá datum pořízení ani zděděné od skupiny či akce
- **THEN** je v posledním oddílu „Bez data“

#### Scenario: Datum bez času
- **WHEN** soubor `IMG-20260428-WA0003.jpg` má datum `2026-04-28` bez
  času
- **THEN** je v oddílu 28. 4. 2026 před soubory téhož dne s časem

#### Scenario: Výběr dne
- **WHEN** uživatel klikne na hlavičku `út 28. 4. 2026`
- **THEN** jsou vybrané všechny soubory toho dne a formulář upravuje
  soubory

### Requirement: Značka autorů na dlaždici
Na pracovní ploše SHALL dlaždice v mřížce i v pásu nést pruh
podle výsledných autorů souboru. Každá osoba akce MUST mít jednu barvu;
pruh se dělí na stejné úseky v barvách autorů, nejvýš tři, další autoři
SHALL tvořit jeden šedý úsek. Soubor bez autorů SHALL mít šrafovaný
pruh. Popisek dlaždice v mřížce SHALL uvést příjmení autorů. Soubor
k vyřazení a průvodce značku nemají.

#### Scenario: Autor ze skupiny
- **WHEN** skupina `Panasonic DC-G9` má autora `Testová, Jana`
  a soubory skupiny autory nepřepisují
- **THEN** všechny dlaždice skupiny mají jednobarevný pruh téže barvy
  a v popisku `Testová`

#### Scenario: Dva autoři
- **WHEN** soubor má autory `Testová, Jana` a `Zkušební, Petr`
- **THEN** pruh má dva stejně dlouhé úseky v barvách obou osob, tytéž
  barvy mají jejich ostatní soubory

#### Scenario: Víc než tři autoři
- **WHEN** soubor má pět autorů
- **THEN** pruh má tři barevné úseky a jeden šedý, popisek uvede tři
  příjmení a `+2` a titulek dlaždice všech pět jmen

#### Scenario: Soubor bez autorů
- **WHEN** soubor nemá autory ani zděděné od skupiny či akce
- **THEN** jeho pruh je šrafovaný a v popisku je `bez autorů`

#### Scenario: Jiný zápis téže osoby
- **WHEN** jeden soubor má autora `Spáčil, David` a jiný `spacil, david`
- **THEN** oba pruhy mají tutéž barvu

#### Scenario: Změna autorů skupiny
- **WHEN** uživatel u skupiny přidá autora
- **THEN** pruhy souborů skupiny, které autory nepřepisují, se hned
  překreslí

#### Scenario: Soubor k vyřazení
- **WHEN** soubor je označený k vyřazení
- **THEN** jeho dlaždice nemá pruh autorů

#### Scenario: Autoři v zobrazení podle data
- **WHEN** v zobrazení podle data leží pod jedním dnem soubory dvou
  skupin s různými autory
- **THEN** jejich dlaždice mají pruhy v barvách svých autorů a popisek
  neuvádí název skupiny
