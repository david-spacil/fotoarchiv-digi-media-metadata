## ADDED Requirements

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
- **WHEN** akce má skupiny `DOD 2015_Lenka` (21 souborů)
  a `DOD 2015_Olga` (66 souborů) a je zvoleno Po skupinách
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
- **WHEN** uživatel klikne na řádek skupiny `DOD 2015_Olga`
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
- **WHEN** mřížka ukazuje konec skupiny `DOD 2015_Lenka` a celou
  skupinu `DOD 2015_Olga`
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
- **WHEN** 10 souborů skupiny `DOD 2015_Lenka` nemá datum ani zděděné
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
- **WHEN** 12 souborů bez GPS má místo `Zkušebná` a `souradnice_mist`
  ho neobsahuje
- **THEN** řádek Akce ukáže `Zkušebná` bez souřadnic a kliknutí vybere
  12 souborů a otevře volbu souřadnic

#### Scenario: Všechny soubory mají GPS
- **WHEN** všechny soubory s místem `Vzorkov` mají GPS z EXIF
- **THEN** řádek Akce `Vzorkov` neukazuje

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

## MODIFIED Requirements

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
- **WHEN** akce má skupiny `DOD 2015_Lenka` a `DOD 2015_Olga`
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
- **WHEN** jeden soubor má autora `Příkladný, Daniel` a jiný `prikladny, daniel`
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

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci; je to jediné
tlačítko plochy, které zapisuje sidecary. Dokončení SHALL
uložit neuložené změny a zkontrolovat úplnost podle chybějících údajů
(viz Chybějící údaje v navigátoru) a nálezy kontroly akce (viz
`event-consistency`); chybí-li něco nebo je-li nález, MUST ukázat co a dokončit jen po dalším potvrzení.
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

### Requirement: Osoby jen pro čtení
Formulář souboru SHALL ukázat jména z jeho `obliceje` jako pole jen pro
čtení s poznámkou, že pochází z Immiche; MUST NOT jít upravit.
U výběru více souborů SHALL ukázat jména všech vybraných. Formulář
skupiny ani akce pole osob MUST NOT nabízet. Není-li Immich nastaven,
pole SHALL místo osob uvést, že Immich není napojen. Chybějící osoby
MUST NOT být mezi chybějícími údaji v navigátoru.

#### Scenario: Soubor s obličeji
- **WHEN** uživatel vybere soubor s obličejem `Ukázková, Věra`
- **THEN** formulář ukáže `Ukázková, Věra` zašedle s poznámkou
  „z Immiche“ a pole nejde upravit

#### Scenario: Formulář skupiny
- **WHEN** uživatel vybere skupinu v navigátoru
- **THEN** formulář pole osob nemá

## REMOVED Requirements

### Requirement: Lišta chybějících údajů
**Reason**: Chybějící údaje se přesunuly do navigátoru, rozepsané po
oddílech; v liště akce zůstávají jen nálezy kontroly, počet k vyřazení
a ovládací prvky.
**Migration**: Viz Chybějící údaje v navigátoru.

### Requirement: Místa bez souřadnic v liště
**Reason**: Místa bez souřadnic se nedají rozpočítat na oddíly, patří
k řádku Akce v navigátoru.
**Migration**: Viz Místa bez souřadnic v navigátoru.
