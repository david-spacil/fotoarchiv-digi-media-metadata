## ADDED Requirements

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
