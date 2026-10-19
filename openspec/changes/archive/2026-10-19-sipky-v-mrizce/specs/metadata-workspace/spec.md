## ADDED Requirements

### Requirement: Ovládání klávesnicí v mřížce
Mřížka plochy a kroku „Skupiny a autoři“ průvodce prvním otevřením
i importu SHALL jít ovládat klávesnicí: šipka vlevo/vpravo přejde na
předchozí/další soubor v pořadí mřížky, šipka nahoru/dolů na vodorovně
nejbližší dlaždici v řádku nad/pod (i přes předěl oddílů), Home/End na
první/poslední soubor a PageUp/PageDown o výšku mřížky. Bez Shiftu SHALL
výběr být jen cílový soubor, se Shiftem rozsah od kotvy. Ctrl+A SHALL
vybrat všechny soubory.

#### Scenario: Šipka dolů do kratšího řádku
- **WHEN** v řádku mřížky je pět dlaždic, skupina `DOD 2015_Jana` má
  sedm souborů, aktuální je její čtvrtý soubor a uživatel stiskne šipku
  dolů
- **THEN** aktuální a jediný vybraný je sedmý soubor `DOD 2015_Jana`

#### Scenario: Šipka dolů přes předěl
- **WHEN** v řádku mřížky je pět dlaždic, aktuální je sedmý (poslední)
  soubor skupiny `DOD 2015_Jana` ve druhém sloupci a uživatel stiskne
  šipku dolů
- **THEN** aktuální je druhý soubor skupiny `DOD 2015_Pavla`

#### Scenario: Šipka vpravo přes předěl
- **WHEN** aktuální je poslední soubor skupiny `DOD 2015_Jana`
  a uživatel stiskne šipku vpravo
- **THEN** aktuální a jediný vybraný je první soubor `DOD 2015_Pavla`

#### Scenario: Rozšíření výběru dolů
- **WHEN** v řádku mřížky je pět dlaždic, aktuální je první soubor akce
  a uživatel stiskne Shift+šipku dolů
- **THEN** vybraných je šest souborů (první až šestý) a aktuální je
  šestý

#### Scenario: O výšku mřížky
- **WHEN** mřížka ukazuje čtyři řádky, aktuální je soubor ve třetím
  sloupci prvního řádku a uživatel stiskne PageDown
- **THEN** aktuální je soubor ve třetím sloupci pátého řádku a mřížka
  ho ukazuje

#### Scenario: Konec akce v mřížce
- **WHEN** uživatel v mřížce stiskne End
- **THEN** aktuální a jediný vybraný je poslední soubor akce a mřížka
  je posunutá k němu

#### Scenario: Vybrat vše
- **WHEN** fokus je v mřížce a uživatel stiskne Ctrl+A
- **THEN** vybrané jsou všechny soubory akce a formulář upravuje výběr

#### Scenario: Klávesy v poli formuláře
- **WHEN** uživatel píše popis ve formuláři vedle mřížky a stiskne
  šipku dolů nebo Ctrl+A
- **THEN** klávesa působí jen v poli a výběr ani aktuální soubor se
  nezmění

#### Scenario: Šipky v průvodci
- **WHEN** v kroku „Skupiny a autoři“ průvodce prvním otevřením je
  aktuální poslední soubor první skupiny a uživatel stiskne šipku
  vpravo
- **THEN** aktuální a jediný vybraný je první soubor další skupiny;
  hlavičku skupiny pohyb přeskočí

### Requirement: Aktuální soubor v mřížce
Aktuální soubor SHALL být v mřížce vyznačený odlišně od výběru, i když
je fokus mimo mřížku. Pohyb klávesou SHALL přesunout fokus na aktuální
dlaždici a posunout mřížku tak, aby byla vidět. Fokus dlaždice
tabulátorem ji SHALL udělat aktuální bez změny výběru. Pohyb SHALL
vycházet z aktuálního souboru, i když je mimo obrazovku; bez
aktuálního souboru SHALL šipky a PageUp/PageDown přejít na první soubor
akce.

#### Scenario: Vyznačení při psaní
- **WHEN** uživatel klikne na `P1503720.JPG` a pak do pole popisu
- **THEN** dlaždice `P1503720.JPG` je dál vyznačená jako aktuální

#### Scenario: Návrat k aktuálnímu souboru
- **WHEN** uživatel klikne na první soubor akce, kolečkem posune mřížku
  na konec a stiskne šipku vpravo
- **THEN** aktuální a jediný vybraný je druhý soubor akce a mřížka je
  posunutá k němu

#### Scenario: První klávesa po otevření
- **WHEN** uživatel otevře akci a bez kliknutí stiskne šipku dolů
- **THEN** aktuální a jediný vybraný je první soubor akce

#### Scenario: Tabulátor nemění výběr
- **WHEN** jsou vybrané tři soubory a uživatel tabulátorem přejde na
  dlaždici jiného souboru
- **THEN** ten soubor je aktuální a vybrané zůstávají tytéž tři soubory

### Requirement: Klávesy v kroku skupin
V kroku „Skupiny a autoři“ průvodce prvním otevřením i importu SHALL
Esc zrušit výběr souborů i skupiny. Delete, Enter a P tam MUST NOT nic
dělat: krok nekreslí označení k vyřazení a nemá lupu ani skládací
panel.

#### Scenario: Esc po výběru všeho
- **WHEN** uživatel v kroku „Skupiny a autoři“ importu stiskne Ctrl+A
  a pak Esc
- **THEN** žádný soubor ani skupina nejsou vybrané

#### Scenario: Delete v průvodci
- **WHEN** v průvodci prvním otevřením jsou vybrané dva soubory
  a uživatel stiskne Delete
- **THEN** soubory nejsou označené k vyřazení a výběr zůstává
