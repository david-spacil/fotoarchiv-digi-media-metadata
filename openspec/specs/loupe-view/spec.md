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
- **WHEN** v lupě je aktuální třetí soubor skupiny `DOD 2015_Jana`
  a uživatel stiskne šipku dolů
- **THEN** aktuální a jediný vybraný je první soubor skupiny
  `DOD 2015_Pavla` a pás ho ukazuje

#### Scenario: Šipka nahoru uprostřed oddílu
- **WHEN** v lupě je aktuální třetí soubor skupiny `DOD 2015_Pavla`
  a uživatel dvakrát stiskne šipku nahoru
- **THEN** po prvním stisku je aktuální první soubor `DOD 2015_Pavla`,
  po druhém první soubor `DOD 2015_Jana`

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
- **WHEN** v lupě je aktuální soubor skupiny `DOD 2015_Jana`
  a uživatel klikne na řádek `DOD 2015_Pavla`
- **THEN** aktuální a jediný vybraný je první soubor skupiny
  `DOD 2015_Pavla` a formulář upravuje tento soubor

#### Scenario: Skok na den v lupě
- **WHEN** v zobrazení podle data uživatel v lupě klikne na řádek
  `so 7. 11. 2015`
- **THEN** aktuální je první soubor toho dne a pás ho ukazuje

#### Scenario: Oddíl aktuálního souboru
- **WHEN** uživatel v lupě přejde šipkou z posledního souboru skupiny
  na první soubor další skupiny
- **THEN** okraj v navigátoru se přesune na řádek další skupiny
