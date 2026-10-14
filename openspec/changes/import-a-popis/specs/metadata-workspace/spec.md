## MODIFIED Requirements

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
