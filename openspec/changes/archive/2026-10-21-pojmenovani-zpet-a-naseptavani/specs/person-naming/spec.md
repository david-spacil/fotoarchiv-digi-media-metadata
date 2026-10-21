## ADDED Requirements

### Requirement: Krok zpět
Po pojmenování, skrytí nebo odložení osoby SHALL nástroj nabídnout volbu
„Zpět“, která ten krok vrátí: osobě v Immichi smaže jméno, zruší
skrytí, nebo ji odebere z odložených. Osobu pak SHALL nabídnout znovu
jako aktuální, po pojmenování s předvyplněným jménem. Vrátit SHALL jít
jen poslední krok, jednou a jen do zavření nástroje. Po sloučení MUST
NOT nástroj Zpět nabízet.

#### Scenario: Překlep ve jménu
- **WHEN** archivář osobu pojmenuje `Vzroný, Tomáš` a zvolí „Zpět“
- **THEN** osoba v Immichi nemá jméno, nástroj ji znovu nabídne a pole
  jména obsahuje `Vzroný, Tomáš` k opravě

#### Scenario: Skrytí omylem
- **WHEN** archivář osobu skryje a zvolí „Zpět“
- **THEN** osoba v Immichi není skrytá a nástroj ji znovu nabídne

#### Scenario: Odložení omylem
- **WHEN** archivář osobu odloží a zvolí „Zpět“
- **THEN** osoba není mezi odloženými a nástroj ji znovu nabídne

#### Scenario: Ponechat samostatně
- **WHEN** archivář odmítne sloučení („Ponechat samostatně“) a zvolí
  „Zpět“
- **THEN** krok se vrátí jako pojmenování: osoba v Immichi nemá jméno
  a nástroj ji znovu nabídne

#### Scenario: Jen jeden krok
- **WHEN** archivář pojmenuje dvě osoby za sebou a dvakrát zvolí „Zpět“
- **THEN** vrátí se jen pojmenování druhé osoby; po prvním vrácení
  volba „Zpět“ není dostupná

#### Scenario: Po sloučení
- **WHEN** archivář osobu sloučí se stejnojmennou osobou
- **THEN** volba „Zpět“ není dostupná

#### Scenario: Poslední osoba kola
- **WHEN** archivář pojmenuje poslední osobu a nástroj ukáže konec kola
- **THEN** volba „Zpět“ je dostupná i tam a vrácení nabídne tu osobu
  znovu

#### Scenario: Po zavření
- **WHEN** archivář osobu pojmenuje, nástroj zavře a znovu otevře
- **THEN** volba „Zpět“ není dostupná

#### Scenario: Nové kolo
- **WHEN** archivář osobu odloží a zvolí „Projít odložené znovu“
- **THEN** volba „Zpět“ není dostupná

### Requirement: Ovládání kroku zpět
Volba Zpět SHALL jít tlačítkem i zkratkou Alt+Backspace, i s kurzorem
v poli jména; tam zkratka MUST NOT smazat text. Platí pro ni pravidla
klávesových zkratek nástroje: tlačítko uvádí zkratku v popisku,
podržená klávesa nic neopakuje a dokud se zápis nevyřídí, další volba
MUST NOT odejít. Když Zpět dostupný není, tlačítko SHALL být neaktivní
a zkratka nic neudělá.

#### Scenario: Zpět klávesou
- **WHEN** archivář s kurzorem v prázdném poli jména další osoby
  stiskne Alt+Backspace
- **THEN** vrátí se poslední krok stejně jako tlačítkem „Zpět“

#### Scenario: Zkratka v rozepsaném jménu
- **WHEN** pole jména obsahuje `Vzorná, J` a archivář stiskne
  Alt+Backspace
- **THEN** vrátí se poslední krok a text z pole se nesmaže po písmenu
  ani po slově; pole převezme vrácenou osobu

#### Scenario: Bez kroku
- **WHEN** archivář nástroj právě otevřel a nic nevyřídil
- **THEN** tlačítko „Zpět“ je neaktivní a Alt+Backspace nic neudělá

### Requirement: Zpět jen bez cizí změny
Server SHALL krok vrátit, jen když osoba v Immichi pořád má stav, který
krok zapsal (to jméno, resp. skrytí). Jinak MUST NOT do Immiche nic
zapsat a nástroj SHALL oznámit, že osobu mezitím změnil někdo jiný;
Zpět pak zmizí. Selže-li zápis do Immiche, SHALL nástroj ukázat chybu
a Zpět ponechat. Po vrácení SHALL server přepočítat počty osob akce
a poznamenat změnu pro synchronizaci po zavření jako po kroku.

#### Scenario: Někdo osobu mezitím přejmenoval
- **WHEN** archivář osobu pojmenuje `Vzorný, Tomáš`, jiný archivář ji
  v Immichi přejmenuje na `Vzorná, Jana` a první zvolí „Zpět“
- **THEN** osoba v Immichi má dál jméno `Vzorná, Jana` a nástroj
  oznámí, že ji mezitím změnil někdo jiný

#### Scenario: Chyba Immiche při vrácení
- **WHEN** Immich při vrácení pojmenování vrátí chybu
- **THEN** nástroj chybu ukáže, aktuální osoba se nezmění a „Zpět“ je
  dál dostupné

#### Scenario: Synchronizace po vrácení
- **WHEN** archivář osobu pojmenuje, krok vrátí a nástroj zavře
- **THEN** server spustí synchronizaci jako po pojmenování

## MODIFIED Requirements

### Requirement: Sloučení se stejnojmennou osobou
Shoduje-li se zadané jméno podle porovnání jmen (bez diakritiky,
velikosti písmen a pořadí slov) se jménem jiné osoby v Immichi, SHALL
nástroj před uložením nabídnout sloučení s ní a ukázat její náhled.
Nabídka SHALL upozornit, že sloučení nejde v nástroji vrátit. Po
potvrzení SHALL osobu sloučit do existující osoby. Při odmítnutí SHALL
osobu jen pojmenovat a ponechat jako samostatnou.

#### Scenario: Sloučení
- **WHEN** archivář zadá `Vzorný, Tomáš` a Immich už osobu
  `Vzorný, Tomáš` má
- **THEN** nástroj nabídne sloučení a po potvrzení zůstane v Immichi
  jediná osoba `Vzorný, Tomáš` s obličeji obou

#### Scenario: Odmítnuté sloučení
- **WHEN** archivář sloučení odmítne
- **THEN** v Immichi jsou dvě osoby se jménem `Vzorný, Tomáš`

#### Scenario: Upozornění na nevratnost
- **WHEN** nástroj nabídne sloučení
- **THEN** u nabídky stojí, že sloučení nejde v nástroji vrátit
