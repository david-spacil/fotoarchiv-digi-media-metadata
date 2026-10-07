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
aktuální soubor: naposledy kliknutý nebo vybraný, jinak první soubor
akce.

#### Scenario: Dvojklik na dlaždici
- **WHEN** uživatel v mřížce dvakrát klikne na `P1503720.JPG`
- **THEN** otevře se lupa s touto fotkou a fotka je vybraná

#### Scenario: Návrat do mřížky
- **WHEN** uživatel v lupě vybere tři soubory a stiskne Esc
- **THEN** zobrazí se mřížka se stejnými třemi vybranými soubory
  a aktuální soubor je vidět

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
Šipka vpravo/vlevo SHALL v lupě přejít na další/předchozí soubor v pořadí
pásu přes hranice skupin a výběr nastavit jen na něj. Shift+šipka SHALL
přejít na další/předchozí soubor a výběr rozšířit od kotvy. Klávesy
MUST NOT přepínat soubory, když je kurzor v poli formuláře.

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

### Requirement: Formulář v lupě
Formulář vedle lupy SHALL fungovat stejně jako vedle mřížky: upravuje
vybrané soubory, a když není nic vybráno, akci. Změny SHALL se ukládat
průběžně stejně jako v mřížce.

#### Scenario: Popis při procházení
- **WHEN** uživatel u fotky v lupě zapíše popis, přejde šipkou na další
  a zpět
- **THEN** formulář u původní fotky ukazuje zapsaný popis
