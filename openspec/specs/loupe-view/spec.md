# loupe-view Specification

## Purpose

Ukázat jednotlivé fotky a videa akce ve velkém zobrazení s rychlým
přepínáním, aby šlo údaje k jednotlivým souborům doplňovat podle toho,
co je na nich vidět.

## Requirements

### Requirement: Přepínání mřížka a lupa
Pracovní plocha SHALL mít dva režimy: mřížku a lupu. Do lupy SHALL vést
Enter, dvojklik na dlaždici a přepínač režimu; zpět do mřížky Esc
a přepínač. Výběr MUST zůstat při přepnutí zachován. Lupa SHALL ukázat
aktuální soubor: naposledy kliknutý, vybraný nebo klávesnicí
fokusovaný, jinak první soubor akce.

#### Scenario: Dvojklik na dlaždici
- **WHEN** uživatel v mřížce dvakrát klikne na `P1503720.JPG`
- **THEN** otevře se lupa s touto fotkou a fotka je vybraná

#### Scenario: Návrat do mřížky
- **WHEN** uživatel v lupě vybere tři soubory a stiskne Esc
- **THEN** zobrazí se mřížka se stejnými třemi vybranými soubory
  a aktuální soubor je vidět

#### Scenario: Enter na fokusované dlaždici
- **WHEN** uživatel klikne na první soubor akce, tabulátorem přejde na
  dlaždici `P1503720.JPG` a stiskne Enter
- **THEN** otevře se lupa s fotkou `P1503720.JPG`

### Requirement: Velká fotka a video
Lupa SHALL zobrazit aktuální fotku co největší v dostupném prostoru se
zachováním poměru stran a EXIF orientace. Video SHALL jít v lupě
přehrát; pokud ho prohlížeč přehrát neumí, SHALL lupa ukázat náhled
videa a informaci, že přehrání není možné.

#### Scenario: Video v lupě
- **WHEN** aktuální soubor je `20260428_144812.mp4`
- **THEN** lupa ukáže přehrávač a video jde spustit

### Requirement: Filmový pás
Lupa SHALL pod velkou fotkou ukázat filmový pás se všemi soubory akce
ve stejném pořadí jako mřížka. Oddíly mřížky (skupiny, nebo dny
v zobrazení podle data) MUST být v pásu vizuálně oddělené
a pojmenované. Aktuální soubor a vybrané soubory MUST být v pásu
odlišené a aktuální soubor SHALL být vždy vidět (pás se posouvá). Klik
do pásu SHALL vybírat stejně jako v mřížce (klik, Ctrl, Shift) a měnit
aktuální soubor.

#### Scenario: Skupiny v pásu
- **WHEN** akce má skupiny `Panasonic DC-G9` a `samsung SM-A528B`
- **THEN** pás ukáže soubory obou skupin za sebou s předělem
  a názvem každé skupiny

#### Scenario: Dny v pásu
- **WHEN** je zvoleno zobrazení podle data a soubory akce jsou z 27.
  a 28. 4. 2026
- **THEN** pás ukáže soubory obou dnů za sebou s předělem a datem
  každého dne a dlaždice nesou pruh v barvách svých autorů

#### Scenario: Autoři v pásu
- **WHEN** soubor má dva autory
- **THEN** dlaždice v pásu má pod sebou pruh ze dvou úseků v barvách
  autorů

#### Scenario: Šipka přes dny
- **WHEN** v zobrazení podle data je aktuální poslední soubor 27. 4.
  a uživatel stiskne šipku vpravo
- **THEN** aktuální je první soubor 28. 4. bez ohledu na jeho skupinu

#### Scenario: Klik do pásu
- **WHEN** uživatel v pásu klikne na fotku
- **THEN** fotka se stane aktuální, ukáže se velká a je jediná vybraná

#### Scenario: Ctrl+klik v pásu
- **WHEN** je vybraná jedna fotka a uživatel v pásu s Ctrl klikne na
  dvě další
- **THEN** jsou vybrané tři fotky a aktuální je naposledy kliknutá

#### Scenario: Shift+klik v pásu
- **WHEN** uživatel v pásu klikne na první fotku skupiny a se Shiftem
  na šestou
- **THEN** je vybráno šest fotek a aktuální je šestá

### Requirement: Ovládání klávesnicí
V lupě SHALL šipka vpravo/vlevo přejít na další/předchozí soubor
v pořadí pásu přes hranice oddílů, šipka nahoru na první soubor oddílu
(na jeho začátku na předchozí oddíl), šipka dolů na první soubor
dalšího oddílu, Home/End na první/poslední soubor akce
a PageUp/PageDown o tolik souborů, kolik se vejde do pásu. Bez Shiftu
SHALL výběr být jen cílový soubor, se Shiftem rozsah od kotvy. Ctrl+A
SHALL vybrat všechny soubory. Klávesy MUST NOT přepínat soubory, když je
kurzor v poli formuláře.

#### Scenario: Další fotka
- **WHEN** aktuální je poslední fotka skupiny a uživatel stiskne šipku
  vpravo
- **THEN** aktuální je první soubor další skupiny a je jediný vybraný

#### Scenario: Rozšíření výběru
- **WHEN** aktuální je pátá fotka a uživatel třikrát stiskne Shift+šipku
  vpravo
- **THEN** vybrané jsou čtyři fotky (pátá až osmá) a aktuální je osmá

#### Scenario: Psaní do formuláře
- **WHEN** uživatel v lupě píše popis a stiskne šipku vlevo
- **THEN** kurzor se posune v textu a aktuální fotka se nezmění

#### Scenario: Skok na další oddíl
- **WHEN** v lupě je aktuální třetí soubor skupiny `DOD 2015_Lenka`
  a uživatel stiskne šipku dolů
- **THEN** aktuální a jediný vybraný je první soubor skupiny
  `DOD 2015_Olga` a pás ho ukazuje

#### Scenario: Šipka nahoru uprostřed oddílu
- **WHEN** v lupě je aktuální třetí soubor skupiny `DOD 2015_Olga`
  a uživatel dvakrát stiskne šipku nahoru
- **THEN** po prvním stisku je aktuální první soubor `DOD 2015_Olga`,
  po druhém první soubor `DOD 2015_Lenka`

#### Scenario: Konec akce
- **WHEN** v lupě je aktuální první soubor akce a uživatel stiskne
  Shift+End
- **THEN** vybrané jsou všechny soubory akce a aktuální je poslední

#### Scenario: O šířku pásu
- **WHEN** do pásu se vejde deset souborů, aktuální je druhý soubor
  akce a uživatel stiskne PageDown
- **THEN** aktuální a jediný vybraný je dvanáctý soubor akce

#### Scenario: Vybrat vše v lupě
- **WHEN** v lupě je aktuální pátý soubor a uživatel stiskne Ctrl+A
- **THEN** vybrané jsou všechny soubory akce a aktuální zůstává pátý

### Requirement: Formulář v lupě
Formulář vedle lupy SHALL fungovat stejně jako vedle mřížky: upravuje
vybrané soubory, a když není nic vybráno, akci. Změny SHALL se ukládat
průběžně stejně jako v mřížce.

#### Scenario: Popis při procházení
- **WHEN** uživatel u fotky v lupě zapíše popis, přejde šipkou na další
  a zpět
- **THEN** formulář u původní fotky ukazuje zapsaný popis

### Requirement: Navigátor v lupě
Navigátor akce (viz `metadata-workspace`, Navigátor akce) SHALL být
vidět i v lupě se stejnými řádky a chybějícími údaji. Klik na řádek
oddílu SHALL v lupě udělat první soubor oddílu aktuálním a jediným
vybraným a posunout pás tak, aby byl vidět; skupinu MUST NOT vybrat
(formulář v lupě upravuje jen soubory, nebo akci). Klik na řádek Akce
SHALL zrušit výběr a aktuální soubor ponechat. Okrajem SHALL být
vyznačený oddíl aktuálního souboru.

#### Scenario: Skok na skupinu v lupě
- **WHEN** v lupě je aktuální soubor skupiny `DOD 2015_Lenka`
  a uživatel klikne na řádek `DOD 2015_Olga`
- **THEN** aktuální a jediný vybraný je první soubor skupiny
  `DOD 2015_Olga` a formulář upravuje tento soubor

#### Scenario: Skok na den v lupě
- **WHEN** v zobrazení podle data uživatel v lupě klikne na řádek
  `so 7. 11. 2015`
- **THEN** aktuální je první soubor toho dne a pás ho ukazuje

#### Scenario: Oddíl aktuálního souboru
- **WHEN** uživatel v lupě přejde šipkou z posledního souboru skupiny
  na první soubor další skupiny
- **THEN** okraj v navigátoru se přesune na řádek další skupiny

### Requirement: Rámečky obličejů
Lupa SHALL u aktuální fotky ukázat rámeček kolem každého obličeje
z jejích `obliceje`, a to jen tehdy, když je kurzor nad fotkou nebo nad
jménem osoby ve formuláři; jinak MUST NOT být rámečky vidět. Rámeček
SHALL ohraničit `oblast` vztaženou k fotce zobrazené se správnou
orientací a MUST sedět na fotce při jakékoli velikosti okna. Video
a soubor bez `obliceje` rámečky nemají.

#### Scenario: Kurzor nad fotkou
- **WHEN** aktuální fotka má obličeje `Vzorný, Tomáš`
  a `Ukázková, Věra` a uživatel najede kurzorem na fotku
- **THEN** lupa ukáže dva rámečky a po odjetí kurzoru z fotky zmizí

#### Scenario: Poloha rámečku
- **WHEN** fotka 2000 × 1000 má obličej s `oblast`
  `[0.5, 0.4, 0.1, 0.2]` a kurzor je nad ní
- **THEN** rámeček má střed na 1000, 400 a velikost 200 × 200 pixelů
  fotky

#### Scenario: Otočená fotka
- **WHEN** fotka má EXIF orientaci 6 (uložená na šířku, zobrazená na
  výšku) a obličej s `oblast` vztaženou k fotce na výšku
- **THEN** rámeček je na obličeji ve fotce zobrazené na výšku

#### Scenario: Změna velikosti okna
- **WHEN** jsou rámečky vidět a uživatel zúží okno tak, že se fotka
  zmenší
- **THEN** rámečky se zmenší s fotkou a zůstanou na obličejích

#### Scenario: Video
- **WHEN** aktuální soubor je video a kurzor je nad přehrávačem
- **THEN** lupa žádné rámečky neukáže

### Requirement: Rámeček a jméno ve formuláři
Při kurzoru nad rámečkem SHALL lupa u rámečku ukázat štítek se jménem
osoby a formulář SHALL to jméno zvýraznit; ostatní rámečky nemají
štítek. Při kurzoru nad jménem ve formuláři SHALL lupa ukázat
zvýrazněné jen rámečky té osoby na aktuální fotce, i je-li na ní víc
než jednou.

#### Scenario: Najetí na rámeček
- **WHEN** kurzor je nad rámečkem obličeje `Vzorný, Tomáš`
- **THEN** u rámečku je štítek `Vzorný, Tomáš`, u ostatních rámečků
  štítek není a formulář zvýrazní jméno `Vzorný, Tomáš`

#### Scenario: Najetí na jméno
- **WHEN** aktuální fotka má obličeje `Vzorný, Tomáš` a `Ukázková,
  Věra` a uživatel najede ve formuláři na jméno `Ukázková, Věra`
- **THEN** lupa ukáže zvýrazněný jen rámeček `Ukázková, Věra`

#### Scenario: Osoba na fotce dvakrát
- **WHEN** aktuální fotka má dva obličeje se jménem `Vzorný, Tomáš`
  a uživatel najede ve formuláři na to jméno
- **THEN** lupa ukáže oba rámečky `Vzorný, Tomáš`

### Requirement: Jména mimo aktuální fotku
Ve výběru více souborů SHALL formulář v lupě ztlumit jména osob, která
nejsou mezi obličeji aktuální fotky. Najetí na ztlumené jméno MUST NOT
ukázat žádný rámeček. Ve výběru jednoho souboru a v mřížce SHALL
formulář ukázat jména beze změny.

#### Scenario: Výběr dvou fotek
- **WHEN** v lupě jsou vybrané dvě fotky, aktuální má obličej
  `Vzorný, Tomáš` a druhá `Ukázková, Věra`
- **THEN** formulář ukáže obě jména, `Ukázková, Věra` ztlumené

#### Scenario: Najetí na ztlumené jméno
- **WHEN** uživatel ve výběru dvou fotek najede ve formuláři na
  ztlumené jméno `Ukázková, Věra`
- **THEN** lupa žádný rámeček neukáže

#### Scenario: Mřížka
- **WHEN** v mřížce jsou vybrané tytéž dvě fotky
- **THEN** formulář ukáže obě jména a žádné není ztlumené

### Requirement: Lupa v kroku skupin
V kroku „Skupiny a autoři“ průvodce prvním otevřením i importu SHALL
lehkou lupu otevřít Enter (aktuální soubor), dvojklik na dlaždici
(ten soubor) a tlačítko „Lupa“ v panelu u výběru (aktuální soubor,
jinak první vybraný). Lehká lupa SHALL být okno přes stránku s velkým
náhledem souboru, jeho názvem a pořadím v mřížce. Video MUST NOT
přehrávat, SHALL ukázat jeho náhled s označením „video“. Esc,
tlačítko zavřít a klik mimo fotku SHALL lupu zavřít; mřížka SHALL být
posunutá k aktuálnímu souboru.

#### Scenario: Dvojklik v importu
- **WHEN** uživatel v kroku „Skupiny a autoři“ importu dvakrát klikne
  na dlaždici `P1503721.JPG`
- **THEN** otevře se lehká lupa s velkým náhledem `P1503721.JPG`
  a ten je aktuální a jediný vybraný

#### Scenario: Tlačítko na dotyku
- **WHEN** uživatel v kroku vybere `P1503725.JPG` a v panelu stiskne
  „Lupa“
- **THEN** otevře se lehká lupa s `P1503725.JPG`

#### Scenario: Video
- **WHEN** lehká lupa ukazuje video `MVI_0042.MOV`
- **THEN** ukáže jeho náhled s označením „video“ a žádný přehrávač

#### Scenario: Zavření
- **WHEN** uživatel v lehké lupě přejde na `P1503725.JPG` a stiskne Esc
- **THEN** lupa je zavřená, `P1503725.JPG` je aktuální a jediný
  vybraný a mřížka ho ukazuje

### Requirement: Pohyb a vyloučení v lupě kroku
V lehké lupě SHALL šipka vpravo/vlevo a tlačítka vpřed/zpět přejít na
další/předchozí soubor v pořadí mřížky přes hranice skupin, Home/End
na první/poslední; za krajem MUST NOT pohyb přetéct. Zobrazený soubor
SHALL být aktuální a jediný vybraný. V importu SHALL Delete a tlačítko
v lupě přepnout vyloučení zobrazeného souboru (viz `photo-import`,
Vyloučení z importu) a vyloučený soubor SHALL být zašedlý
s označením. V průvodci MUST NOT Delete v lupě nic dělat.

#### Scenario: Další soubor přes skupinu
- **WHEN** lehká lupa ukazuje poslední soubor skupiny `DOD 2015_Lenka`
  a uživatel stiskne šipku vpravo
- **THEN** lupa ukazuje první soubor skupiny `DOD 2015_Olga` a ten je
  aktuální a jediný vybraný

#### Scenario: Konec mřížky
- **WHEN** lehká lupa ukazuje poslední soubor a uživatel stiskne šipku
  vpravo
- **THEN** lupa ukazuje dál poslední soubor

#### Scenario: Vyloučení v lupě
- **WHEN** lehká lupa v importu ukazuje `P1503721.JPG` bez RAWu
  a uživatel stiskne Delete
- **THEN** `P1503721.JPG` je vyloučený z importu, lupa ho ukazuje
  zašedlý s označením „vyloučeno z importu“ a tlačítko nabízí „Vrátit
  do importu“

#### Scenario: Vyloučení fotky s RAWem
- **WHEN** lehká lupa v importu ukazuje `P1503720.JPG`, výběr importu
  obsahuje `P1503720.RW2` a uživatel stiskne Delete
- **THEN** průvodce se zeptá, zda vyloučit i RAWy, a po volbě lupa
  ukazuje dál `P1503720.JPG` s novým stavem

#### Scenario: Delete v lupě průvodce
- **WHEN** lehká lupa v průvodci prvním otevřením ukazuje
  `P1503720.JPG` a uživatel stiskne Delete
- **THEN** nic se nezmění
