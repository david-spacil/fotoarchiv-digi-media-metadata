# metadata-workspace Specification

## Purpose

Provést uživatele prvním zpracováním akce a pak nabídnout pracovní
plochu pro přiřazování metadat akci, skupinám a jednotlivým souborům.

## Requirements

### Requirement: Průvodce prvním otevřením
Při otevření akce bez `_metadata.json` SHALL aplikace spustit průvodce
v pořadí: úklid → údaje akce → skupiny a autoři. Potvrzení úklidu SHALL
načíst soubory kořene (technické údaje a návrh skupin). Krok skupiny
a autoři SHALL ukázat mřížku náhledů po skupinách s úpravou skupin
(viz Úprava skupin) a u každé skupiny pole autorů. Průvodce MUST pokrýt
všechny povinné údaje akce a skupin; údaje jednotlivých souborů do něj
nepatří. Po dokončení průvodce SHALL otevřít pracovní plochu. Akce
s `_metadata.json` (i akce založená importem) SHALL otevřít rovnou
pracovní plochu.

#### Scenario: První otevření
- **WHEN** uživatel otevře akci ve stavu *nezpracováno*
- **THEN** začne průvodce krokem úklid

#### Scenario: Autoři skupin v průvodci
- **WHEN** uživatel v průvodci dokončí údaje akce
- **THEN** následuje krok, kde vidí skupiny s náhledy, může je upravit
  a každé zadat autory, a teprve pak se otevře pracovní plocha

#### Scenario: Náhledy v kroku autoři skupin
- **WHEN** průvodce ukáže krok skupiny a autoři
- **THEN** soubory jsou v mřížce náhledů po skupinách a každá skupina
  má u sebe pole autorů

#### Scenario: Úprava skupiny i autorů bez přepínání kroků
- **WHEN** uživatel v kroku skupiny a autoři přesune vybrané soubory do
  nové skupiny
- **THEN** nová skupina má v témže kroku vlastní pole autorů

#### Scenario: Akce z importu
- **WHEN** uživatel otevře novou akci, kterou založil import s popisem
- **THEN** otevře se rovnou pracovní plocha

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
podle dnů (viz Zobrazení podle data). Oddíly SHALL být v mřížce
oddělené předělem bez hlavičky; název a počet oddílu nese navigátor
(viz Navigátor akce). Uživatel SHALL moci vybrat jeden soubor
kliknutím, přidat do výběru s modifikátorem, vybrat rozsah se Shiftem,
vybrat tažením myši z místa mimo dlaždice a celý oddíl kliknutím na
jeho řádek v navigátoru.

#### Scenario: Výběr rozsahu
- **WHEN** uživatel klikne na první soubor a se Shiftem na pátý
- **THEN** je vybráno pět souborů

#### Scenario: Rozsah v zobrazení podle data
- **WHEN** v zobrazení podle data uživatel klikne na první soubor a se
  Shiftem na pátý a soubory patří do dvou různých skupin
- **THEN** je vybráno pět souborů, které jsou v mřížce mezi nimi

#### Scenario: Předěl místo hlavičky
- **WHEN** akce má skupiny `DOD 2015_Jana` a `DOD 2015_Pavla`
- **THEN** v mřížce jsou soubory obou skupin oddělené předělem a název
  skupiny je jen v navigátoru

### Requirement: Formulář podle výběru
Formulář vedle mřížky SHALL upravovat akci, když není nic vybráno,
skupinu, když je v navigátoru vybrána skupina, a vybrané soubory, když
je vybrán jeden nebo více souborů. Zděděné hodnoty SHALL být viditelně
odlišené od zadaných a MUST jít přepsat i vrátit na zděděné. Vyprázdnění
pole SHALL znamenat vrácení na zděděné (pole se smaže); přepsání na
prázdnou hodnotu aplikace nepodporuje.

Každé pole SHALL ukazovat zdroj své hodnoty štítkem a barevným
proužkem: zděděná („z akce“, „ze skupiny“, „z místa“), rozdílná ve
výběru („rozdílné“) a zadaná na dané úrovni. Pole se zadanou hodnotou
u skupiny nebo souborů SHALL mít tlačítko „vrátit na zděděné“, které
hodnotu z dané úrovně smaže (stejně jako vyprázdnění pole). U akce
tlačítko není (akce nic nedědí). Bez zámku akce (jen ke čtení) MUST
NOT jít tlačítko použít.

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

#### Scenario: Štítek zdroje
- **WHEN** uživatel vybere soubor, jehož skupina má autora a soubor
  autory nepřepisuje
- **THEN** pole autoři ukazuje autora skupiny se štítkem „ze skupiny“

#### Scenario: Vrácení na zděděné
- **WHEN** soubor má zadaný vlastní popis a uživatel u pole klikne na
  „vrátit na zděděné“
- **THEN** popis zmizí ze záznamu souboru, pole ukáže zděděný popis se
  štítkem zdroje a změna se uloží jako ostatní

#### Scenario: Vrácení u výběru
- **WHEN** 5 vybraných souborů má zadané místo a uživatel klikne na
  „vrátit na zděděné“
- **THEN** žádný z 5 souborů nemá místo zadané u sebe

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci; to uloží
neuložené změny a otevře kontrolní stránku dokončení (viz Kontrolní
stránka dokončení). Tlačítko Dokončit na kontrolní stránce je jediné
místo aplikace mimo příkaz `exportovat`, které zapisuje sidecary.
Dokončení SHALL zkontrolovat úplnost podle chybějících údajů (viz
Chybějící údaje v navigátoru) a nálezy kontroly akce (viz
`event-consistency`); chybí-li něco nebo je-li nález, MUST to kontrolní
stránka ukázat a dokončit jen po výslovném potvrzení.
Pak SHALL akci exportovat, v produkčním režimu odebrat ze
složky akce příponu `.ignored` (viz `event-visibility`) a nastavit
`dokonceno` na datum dokončení. Má-li akce `dokonceno` už nastavené,
dokončení ho MUST NOT změnit: `dokonceno` je datum prvního dokončení.
Selže-li u akce bez `dokonceno` zápis některého sidecaru nebo
přejmenování složky, akce MUST NOT být označena jako dokončená.
Selže-li u akce s `dokonceno`, akce MUST zůstat dokončená se stejným
datem a kontrolní stránka SHALL chybu ukázat.
Dokončení vyžaduje zámek akce.

U dokončené akce SHALL být tlačítko na ploše i na kontrolní stránce
neaktivní, dokud není co dokončovat: žádné neuložené ani
neexportované změny, žádné neaktuální sidecary a poslední export
neselhal. Jakmile něco z toho nastane, tlačítko SHALL být znovu
aktivní. Text tlačítka na ploše se nemění.

#### Scenario: Úplná akce
- **WHEN** akci nic nechybí a uživatel na kontrolní stránce klikne na
  Dokončit
- **THEN** sidecary jsou zapsané, `dokonceno` je nastavené a seznam
  akcí ji ukazuje jako *hotovo*

#### Scenario: Neúplná akce
- **WHEN** 14 souborů nemá datum a uživatel klikne na ploše na
  Dokončit akci
- **THEN** kontrolní stránka ukáže „14 souborů bez data“ a dokončí až
  po výslovném potvrzení

#### Scenario: Akce s nepodporovaným souborem
- **WHEN** kořen akce obsahuje `zprava.pdf` a uživatel otevře
  kontrolní stránku
- **THEN** stránka ukáže „1 nepodporovaný soubor v kořeni“ a po
  potvrzení akci dokončí; `zprava.pdf` zůstane v kořeni

#### Scenario: Selhání přejmenování
- **WHEN** sidecary se zapíšou, ale složku akce nejde přejmenovat
- **THEN** akce nemá `dokonceno` a kontrolní stránka ukáže, že akci
  nešlo zveřejnit

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
  jako *hotovo*, kontrolní stránka ukáže chybu u `foto.jpg`
  a tlačítko Dokončit zůstane aktivní

#### Scenario: Rozpracovaná akce
- **WHEN** akce ještě nemá `dokonceno`
- **THEN** tlačítko Dokončit akci je aktivní (má-li uživatel zámek)

### Requirement: Kontrolní stránka dokončení
Aplikace SHALL mít pro každou akci kontrolní stránku dokončení na
vlastní adrese (`#/akce/<název>/dokonceni`), dostupnou z plochy
tlačítkem Dokončit akci i přímým odkazem. Stránka SHALL ukázat seznam
kontrol, každou se stavem v pořádku / k vyřešení a počtem:

- **Údaje akce:** chybějící název nebo data akce.
- **Chybějící údaje souborů:** skupiny bez autorů, soubory bez
  autorů, bez data, bez místa (bez místa jen pokud má akce víc míst),
  místa bez souřadnic; počty stejné jako v navigátoru.
- **Nálezy kontroly akce** po druzích (viz `event-consistency`).
- **Poškozené soubory** bez rozhodnutí (viz `file-integrity`).
- **Soubory k vyřazení**, které ještě nejsou přesunuté.
- **Stav exportu:** výsledek kontroly nanečisto (počet neaktuálních
  sidecarů, „neexportované změny“, nebo vše aktuální) a ve vývojovém
  režimu poznámka, že sidecary jdou do pracovního adresáře.

Každá kontrola k vyřešení SHALL mít odkaz na nápravu, který otevře
plochu akce a vybere dotčené soubory nebo skupinu, případně skočí na
oddíl nebo otevře dialog Uklidit…. Návrat z plochy SHALL být možný
tlačítkem Dokončit akci. Tlačítko Dokončit SHALL při kontrolách
k vyřešení nést text „Přesto dokončit“; bez nich „Dokončit“. Po
dokončení SHALL stránka ukázat počty zapsaných, nezměněných
a selhaných sidecarů, chyby u jednotlivých souborů a odkaz zpět na
seznam akcí.

Stránka SHALL používat zámek akce stejně jako plocha: přechod mezi
plochou a stránkou zámek MUST NOT uvolnit; bez zámku je stránka jen
pro čtení s uvedeným držitelem a tlačítko Dokončit je neaktivní.
Akci bez `_metadata.json` stránka SHALL přesměrovat na plochu
(průvodce).

#### Scenario: Přechod z plochy
- **WHEN** uživatel na ploše s neuloženou změnou klikne na Dokončit
  akci
- **THEN** změna se uloží, otevře se kontrolní stránka a zámek akce
  zůstane uživateli

#### Scenario: Náprava chybějícího data
- **WHEN** kontrolní stránka ukazuje „14 souborů bez data“
  a uživatel klikne na odkaz nápravy
- **THEN** otevře se plocha akce se 14 vybranými soubory

#### Scenario: Vše v pořádku
- **WHEN** akci nic nechybí, nemá nálezy ani poškozené soubory
- **THEN** všechny kontroly jsou v pořádku a tlačítko nese text
  „Dokončit“

#### Scenario: Přímý odkaz bez zámku
- **WHEN** uživatel otevře `#/akce/<název>/dokonceni` akce, kterou
  drží Kopáčová, Zuzana
- **THEN** stránka ukáže kontroly, uvede „upravuje Kopáčová, Zuzana“
  a tlačítko Dokončit je neaktivní

#### Scenario: Nezpracovaná akce
- **WHEN** uživatel otevře kontrolní stránku akce bez `_metadata.json`
- **THEN** aplikace otevře plochu akce s průvodcem

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
průvodce prvním otevřením v kroku skupiny a autoři použít jeho skupiny
(i s autory) a přiřazení pro soubory, které návrh uvádí a jsou
v kořeni akce, a autory celé akce z návrhu. Ostatní soubory SHALL
dostat automatický návrh podle přístroje a vzoru názvu. Po prvním
uložení `_metadata.json` SHALL server návrh smazat. Chybí-li návrh
(např. smazaný pracovní adresář), průvodce SHALL postupovat jako
dosud.

#### Scenario: Podsložky z importu jako skupiny
- **WHEN** uživatel otevře existující akci bez `_metadata.json`, do
  které importoval `DOD 2015` s rozdělením „podle podsložek“ a autory
  skupin
- **THEN** krok skupiny a autoři ukáže skupiny `DOD 2015_Bara Tesar`,
  `DOD 2015_Jana`, `DOD 2015_Pavla` a `DOD 2015_Verca` s autory
  zadanými při importu

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
MUST NOT být mezi chybějícími údaji v navigátoru.

#### Scenario: Soubor s obličeji
- **WHEN** uživatel vybere soubor s obličejem `Lečbychová, Olga`
- **THEN** formulář ukáže `Lečbychová, Olga` zašedle s poznámkou
  „z Immiche“ a pole nejde upravit

#### Scenario: Formulář skupiny
- **WHEN** uživatel vybere skupinu v navigátoru
- **THEN** formulář pole osob nemá

### Requirement: Autoři akce v průvodci
Krok skupiny a autoři průvodce SHALL nad skupinami nabídnout pole
autoři celé akce, které upravuje `autori` akce a ukazuje jejich
uloženou hodnotu. Skupina bez vlastních autorů SHALL v tomto kroku
ukázat autory akce jako zděděné a MUST se nepočítat mezi skupiny bez
autorů. Autoři akce se MUST NOT kopírovat do skupin; skupina je SHALL
moci přepsat vlastními. Krok údaje akce pole autorů neukazuje.

#### Scenario: Autoři celé akce
- **WHEN** uživatel v kroku skupiny a autoři zadá autory celé akce
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
  v průvodci vrátí ke kroku skupiny a autoři
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
rozdělené předěly po kalendářních dnech. Řádek dne v navigátoru SHALL
ukázat den v týdnu, datum a počet souborů. Soubory bez data SHALL být
na konci v oddílu „Bez data“. Klik na řádek dne nebo „Bez data“
v navigátoru SHALL vybrat soubory oddílu.

#### Scenario: Dva přístroje téhož dne
- **WHEN** akce má skupiny `Panasonic DC-G9` a `samsung SM-A528B`
  a obě obsahují fotky z 28. 4. 2026
- **THEN** v oddílu `út 28. 4. 2026` jsou fotky obou skupin
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
- **WHEN** uživatel klikne v navigátoru na řádek `út 28. 4. 2026`
- **THEN** jsou vybrané všechny soubory toho dne a formulář upravuje
  soubory

### Requirement: Značka autorů na dlaždici
Na pracovní ploše SHALL dlaždice v mřížce i v pásu nést pruh
podle výsledných autorů souboru. Každá osoba akce MUST mít jednu barvu;
pruh se dělí na stejné úseky v barvách autorů, nejvýš tři, další autoři
SHALL tvořit jeden šedý úsek. Soubor bez autorů SHALL mít šrafovaný
pruh. Soubor k vyřazení a průvodce značku nemají.

Dlaždice v mřížce SHALL nemít popisek pod náhledem. Název souboru,
datum pořízení a příjmení autorů SHALL ukázat překryv při najetí myší;
titulek dlaždice SHALL uvést všechna jména autorů. Soubor bez data
a soubor bez místa (jen pokud má akce víc míst) SHALL mít v rohu
náhledu ikonu, soubor k vyřazení ikonu vyřazení místo nich.

#### Scenario: Autor ze skupiny
- **WHEN** skupina `Panasonic DC-G9` má autora `Testová, Jana`
  a soubory skupiny autory nepřepisují
- **THEN** všechny dlaždice skupiny mají jednobarevný pruh téže barvy
  a překryv při najetí uvede `Testová`

#### Scenario: Dva autoři
- **WHEN** soubor má autory `Testová, Jana` a `Zkušební, Petr`
- **THEN** pruh má dva stejně dlouhé úseky v barvách obou osob, tytéž
  barvy mají jejich ostatní soubory

#### Scenario: Víc než tři autoři
- **WHEN** soubor má pět autorů
- **THEN** pruh má tři barevné úseky a jeden šedý, překryv uvede tři
  příjmení a `+2` a titulek dlaždice všech pět jmen

#### Scenario: Soubor bez autorů
- **WHEN** soubor nemá autory ani zděděné od skupiny či akce
- **THEN** jeho pruh je šrafovaný a v překryvu je `bez autorů`

#### Scenario: Jiný zápis téže osoby
- **WHEN** jeden soubor má autora `Spáčil, David` a jiný `spacil, david`
- **THEN** oba pruhy mají tutéž barvu

#### Scenario: Změna autorů skupiny
- **WHEN** uživatel u skupiny přidá autora
- **THEN** pruhy souborů skupiny, které autory nepřepisují, i pruh
  v řádku skupiny v navigátoru se hned překreslí

#### Scenario: Soubor k vyřazení
- **WHEN** soubor je označený k vyřazení
- **THEN** jeho dlaždice nemá pruh autorů a má v rohu ikonu vyřazení

#### Scenario: Soubor bez data
- **WHEN** soubor nemá datum ani zděděné
- **THEN** jeho dlaždice má v rohu ikonu data

#### Scenario: Autoři v zobrazení podle data
- **WHEN** v zobrazení podle data leží pod jedním dnem soubory dvou
  skupin s různými autory
- **THEN** jejich dlaždice mají pruhy v barvách svých autorů a překryv
  neuvádí název skupiny

### Requirement: Verze aplikace v hlavičce
Hlavička stránky SHALL ukazovat verzi běžící aplikace vedle názvu
aplikace. Verze SHALL být ta, se kterou byl server spuštěn: v pracovní
kopii gitu popis podle posledního tagu (tag, počet commitů po něm,
hash a příznak neuložených změn), v Docker image popis zapsaný při
buildu. Když verzi nejde zjistit, hlavička SHALL ukázat „verze
neznámá“. Zobrazení verze MUST NOT měnit výšku hlavičky.

#### Scenario: Pracovní kopie po vydání
- **WHEN** server běží z pracovní kopie jeden commit za tagem `v0.2.0`
- **THEN** hlavička ukazuje verzi `v0.2.0-1-g5609826`

#### Scenario: Neuložené změny
- **WHEN** pracovní kopie má neuložené změny
- **THEN** verze končí `-dirty`

#### Scenario: Docker image
- **WHEN** server běží v image postaveném z commitu s tagem `v0.3.0`
- **THEN** hlavička ukazuje verzi `v0.3.0`, přestože image neobsahuje
  `.git`

#### Scenario: Verze se po startu nemění
- **WHEN** se po startu serveru v pracovní kopii udělá `git pull`
- **THEN** hlavička dál ukazuje verzi, se kterou server startoval

#### Scenario: Neznámá verze
- **WHEN** server neběží z gitu ani nemá verzi z buildu
- **THEN** hlavička ukazuje „verze neznámá“

### Requirement: Velikost dlaždic
Pracovní plocha SHALL mít ovladač velikosti náhledů v mřížce
s rozsahem od malých (aspoň 8 dlaždic na řádek v okně 1280 px s panelem)
po velké (náhled aspoň 280 px na šířku). Změna SHALL se projevit hned,
výběr a aktuální soubor MUST zůstat zachované a aktuální soubor vidět.
Volba SHALL platit v tomtéž prohlížeči pro další akce a po obnovení.
Filmový pás lupy velikost nemění.

#### Scenario: Zvětšení náhledů
- **WHEN** uživatel posune ovladač k velkým náhledům
- **THEN** dlaždice v mřížce se zvětší a vybrané soubory zůstanou
  vybrané

#### Scenario: Volba přetrvá
- **WHEN** uživatel nastaví malé náhledy a otevře jinou akci
- **THEN** mřížka nové akce má malé náhledy

### Requirement: Skládací panel formuláře
Panel formuláře na pracovní ploše SHALL jít sbalit a znovu rozbalit
tlačítkem a klávesou `P` (mimo textové pole). Sbalený panel SHALL
uvolnit šířku mřížce nebo lupě a ukazovat jen tlačítko pro rozbalení.
Stav panelu SHALL platit v tomtéž prohlížeči pro další akce a po
obnovení. Sbalení MUST NOT měnit výběr ani zahodit neuložené změny.
V průvodci se panel nesbaluje.

#### Scenario: Sbalení v lupě
- **WHEN** uživatel v lupě stiskne `P`
- **THEN** panel zmizí a velká fotka se roztáhne na uvolněnou šířku

#### Scenario: P v textovém poli
- **WHEN** je kurzor v poli popis a uživatel napíše `P`
- **THEN** píše se text a panel zůstane

#### Scenario: Rozbalení
- **WHEN** je panel sbalený a uživatel klikne na tlačítko rozbalení
- **THEN** panel ukáže formulář pro aktuální výběr

### Requirement: Navigátor akce
Pracovní plocha SHALL mít vlevo od mřížky navigátor akce: nahoře řádek
Akce, pod ním řádek pro každý oddíl mřížky (skupiny, nebo dny podle
přepínače zobrazení) ve stejném pořadí jako mřížka. V zobrazení po
skupinách SHALL být soubory bez skupiny posledním oddílem „Bez
skupiny“, v zobrazení podle data soubory bez data oddílem „Bez data“
(viz Zobrazení podle data). Navigátor SHALL se posouvat nezávisle na
mřížce.

Řádek oddílu SHALL ukázat název oddílu, počet jeho souborů, pruh
autorů a chybějící údaje oddílu (viz Chybějící údaje v navigátoru).
Pruh autorů SHALL být rozdělený v poměru počtu souborů jednotlivých
výsledných autorů v oddílu, v barvách osob z Značky autorů na dlaždici;
nejvýš tři nejčastější autoři barevně, ostatní jedním šedým úsekem,
soubory bez autorů šrafovaným úsekem. Titulek pruhu SHALL uvést jména
a počty. Soubory k vyřazení se do pruhu nepočítají.

Klik na řádek Akce SHALL zrušit výběr (formulář upravuje akci). Klik na
řádek skupiny SHALL vybrat skupinu, klik na řádek dne, „Bez data“ nebo
„Bez skupiny“ SHALL vybrat soubory oddílu. Klik na řádek oddílu SHALL
posunout mřížku na začátek oddílu tak, aby byl vidět i předěl nad ním.
Vybraný oddíl SHALL být v navigátoru odlišený. Každý oddíl, který je
v mřížce aspoň zčásti vidět, SHALL mít v navigátoru vyznačený okraj,
průběžně při posouvání mřížky.

#### Scenario: Oddíly po skupinách
- **WHEN** akce má skupiny `DOD 2015_Jana` (21 souborů)
  a `DOD 2015_Pavla` (66 souborů) a je zvoleno Po skupinách
- **THEN** navigátor pod řádkem Akce ukáže řádky obou skupin s počty
  21 a 66

#### Scenario: Oddíly podle data
- **WHEN** je zvoleno Podle data a soubory akce jsou z 6. a 7. 11. 2015
  a 10 souborů nemá datum
- **THEN** navigátor ukáže řádky `pá 6. 11. 2015`, `so 7. 11. 2015`
  a „Bez data“

#### Scenario: Pruh autorů oddílu
- **WHEN** skupina má 30 souborů, 20 s autorem `Testová, Jana`
  a 10 s autorem `Zkušební, Petr`
- **THEN** pruh v řádku skupiny má dva úseky v barvách obou osob
  v poměru 2 : 1

#### Scenario: Výběr skupiny z navigátoru
- **WHEN** uživatel klikne na řádek skupiny `DOD 2015_Pavla`
- **THEN** skupina je vybraná, formulář upravuje skupinu a mřížka je
  posunutá na její první soubory s předělem nad nimi

#### Scenario: Výběr dne z navigátoru
- **WHEN** v zobrazení podle data uživatel klikne na řádek
  `so 7. 11. 2015`
- **THEN** jsou vybrané všechny soubory toho dne a formulář upravuje
  soubory

#### Scenario: Řádek Akce
- **WHEN** je vybraná skupina a uživatel klikne na řádek Akce
- **THEN** výběr je prázdný a formulář upravuje akci

#### Scenario: Viditelné oddíly
- **WHEN** mřížka ukazuje konec skupiny `DOD 2015_Jana` a celou
  skupinu `DOD 2015_Pavla`
- **THEN** oba řádky mají v navigátoru vyznačený okraj, ostatní ne

### Requirement: Chybějící údaje v navigátoru
Navigátor SHALL průběžně ukazovat, co chybí (soubory označené
k vyřazení MUST NOT být započítány):

- **Řádek Akce:** chybějící název nebo data akce a místa bez souřadnic
  (viz Místa bez souřadnic v navigátoru).
- **Řádek oddílu:** počet souborů bez autorů, bez data a bez místa
  (bez místa jen pokud má akce víc míst); v zobrazení podle data
  i počet souborů bez skupiny. Oddíl „Bez data“ neukazuje „bez data“
  a oddíl „Bez skupiny“ neukazuje „bez skupiny“.
- **Skupina bez autorů:** skupina, která nemá výsledné autory a aspoň
  jeden její soubor je nepřepisuje, SHALL mít místo počtu souborů bez
  autorů zvýrazněné „bez autorů“. Skupina, jejíž všechny soubory jsou
  označené k vyřazení, mezi ně nepatří.

Každý chybějící údaj SHALL být ikona s počtem a titulkem slovy
(„30 souborů bez místa“). Klik na údaj SHALL vybrat dotčené soubory
a posunout na ně mřížku; u skupiny bez autorů SHALL vybrat skupinu.
Bez zámku akce (jen ke čtení) SHALL údaje zůstat vidět a klik vybírat.

#### Scenario: Skupina bez autorů
- **WHEN** skupina nemá autory a žádný její soubor je nepřepisuje
- **THEN** její řádek ukáže zvýrazněné „bez autorů“ a klik na ně
  vybere skupinu

#### Scenario: Soubory bez data ve skupině
- **WHEN** 10 souborů skupiny `DOD 2015_Jana` nemá datum ani zděděné
- **THEN** řádek skupiny ukáže ikonu data s počtem 10 a klik na ni
  vybere těch 10 souborů

#### Scenario: Soubory bez místa
- **WHEN** akce má dvě místa a 30 souborů skupiny nemá místo zadané
  u sebe ani u skupiny
- **THEN** řádek skupiny ukáže ikonu místa s počtem 30

#### Scenario: Jedno místo akce
- **WHEN** akce má jedno místo
- **THEN** žádný řádek neukazuje soubory bez místa

#### Scenario: Označený soubor bez data
- **WHEN** soubor bez data je označený k vyřazení
- **THEN** řádek jeho oddílu ho mezi soubory bez data nepočítá

#### Scenario: Chybějící datum akce
- **WHEN** akce nemá vyplněné datum do
- **THEN** řádek Akce ukáže, že chybí datum do, a klik na řádek
  zruší výběr

#### Scenario: Bez skupiny podle data
- **WHEN** v zobrazení podle data leží pod jedním dnem 6 souborů bez
  skupiny
- **THEN** řádek dne ukáže ikonu skupiny s počtem 6

### Requirement: Místa bez souřadnic v navigátoru
Řádek Akce v navigátoru SHALL ukázat názvy míst, o jejichž souřadnicích
není rozhodnuto a které jsou výsledným místem aspoň jednoho souboru bez
GPS. Kliknutí na místo SHALL vybrat dotčené soubory a otevřít volbu
souřadnic.

#### Scenario: Nerozhodnuté místo
- **WHEN** 12 souborů bez GPS má místo `Vysočany` a `souradnice_mist`
  ho neobsahuje
- **THEN** řádek Akce ukáže `Vysočany` bez souřadnic a kliknutí vybere
  12 souborů a otevře volbu souřadnic

#### Scenario: Všechny soubory mají GPS
- **WHEN** všechny soubory s místem `Holštejn` mají GPS z EXIF
- **THEN** řádek Akce `Holštejn` neukazuje

### Requirement: Lišta akce
Pracovní plocha SHALL mít pod hlavičkou aplikace jednu lištu akce
s názvem akce, přepínači zobrazení, tlačítky Importovat a Dokončit
akci, počtem souborů k vyřazení a nálezy kontroly akce. Chybějící
údaje v liště nejsou (viz Chybějící údaje v navigátoru). Nevejdou-li
se položky na řádek, SHALL se zalomit na další řádek lišty; ovládací
prvky lišty MUST zůstat vidět.

#### Scenario: Nálezy v liště
- **WHEN** kořen akce obsahuje podsložku `RAW` a 2 soubory jsou
  označené k vyřazení
- **THEN** lišta akce ukáže nález podsložky a „2 soubory k vyřazení“
  vedle tlačítka Dokončit akci

#### Scenario: Chybějící údaje mimo lištu
- **WHEN** akci chybí autoři dvou skupin
- **THEN** lišta akce je neuvádí, ukazují je řádky obou skupin
  v navigátoru

#### Scenario: Mnoho položek na úzkém okně
- **WHEN** v okně 1280 px šířky má lišta nálezy tří druhů a počet
  k vyřazení
- **THEN** položky se zalomí na další řádek lišty a tlačítko Dokončit
  akci zůstane vidět

### Requirement: Přesun do skupiny tažením
Na pracovní ploše SHALL jít soubory přesunout do skupiny tažením
dlaždice z mřížky na řádek skupiny v navigátoru. Táhne-li uživatel
vybranou dlaždici, SHALL se přesunout celý výběr, jinak jen tažený
soubor. Cílem MUST být jen řádek skutečné skupiny; řádky dnů, „Bez
data“, „Bez skupiny“ a Akce MUST NOT tažení přijmout a během tažení
SHALL být odlišené jako nepřijímající. Přesun SHALL se uložit jako
ostatní změny a pro skupinu, která zůstane prázdná, platí totéž co
v Úpravě skupin. Bez zámku akce MUST NOT jít tažením nic přesunout.

#### Scenario: Přesun výběru
- **WHEN** jsou vybrané 3 soubory skupiny A a uživatel táhne jeden
  z nich na řádek skupiny B
- **THEN** všechny 3 soubory patří do skupiny B a počty v řádcích obou
  skupin se hned změní

#### Scenario: Přesun nevybraného souboru
- **WHEN** jsou vybrané 3 soubory a uživatel táhne jiný, nevybraný
  soubor na řádek skupiny B
- **THEN** do skupiny B se přesune jen tažený soubor

#### Scenario: Tažení na den
- **WHEN** v zobrazení podle data uživatel táhne soubor na řádek dne
- **THEN** řádek tažení nepřijme a soubor se nezmění

#### Scenario: Bez zámku
- **WHEN** akci drží jiný uživatel a uživatel táhne dlaždici na řádek
  skupiny
- **THEN** nic se nepřesune
