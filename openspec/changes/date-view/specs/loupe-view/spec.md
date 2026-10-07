## MODIFIED Requirements

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
  každého dne a dlaždice nesou proužek barvy své skupiny

#### Scenario: Autoři v pásu
- **WHEN** je zvoleno zobrazení po skupinách a soubor má dva autory
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
