# person-naming Specification

## Purpose
Provést archiváře po jedné nepojmenovanými osobami Immiche, které mají
obličej na fotkách akce, a pojmenovat, odložit nebo skrýt je přímo
v Immichi, odkud jména přebírá synchronizace.

## Requirements

### Requirement: Otevření nástroje
Nástroj SHALL jít otevřít z karty akce v seznamu, z plochy akce
a klikem na chybějící údaj „nepojmenované osoby“ v navigátoru. SHALL
se otevřít jako překryv nad plochou dané akce, nikoli jako nová stránka:
plocha pod ním SHALL zůstat vidět rozmazaná a zmatněná. Zavření SHALL
vrátit uživatele na plochu akce. Odkaz ze seznamu SHALL otevřít plochu
akce rovnou s nástrojem. Odkazy SHALL být jen u akce, která má album
v Immichi a aspoň jednu osobu k pojmenování. Dokud stav akce v Immichi
není *obličeje rozpoznány* (viz `immich-people`), SHALL nástroj
upozornit, že seznam osob ještě nemusí být úplný.

#### Scenario: Otevření ze seznamu
- **WHEN** archivář na kartě akce
  `2026-09-08 Konference Dějiny archeologie` klikne na odkaz
  nepojmenovaných osob
- **THEN** otevře se plocha akce s nástrojem přes ni a plocha je pod
  nástrojem rozmazaná

#### Scenario: Zavření
- **WHEN** archivář nástroj zavře
- **THEN** zůstane na ploše téže akce

#### Scenario: Rozpoznávání ještě probíhá
- **WHEN** archivář otevře nástroj u akce ve stavu „Rozpoznávání
  obličejů probíhá“
- **THEN** nástroj nabídne dosud známé osoby a upozorní, že další
  mohou přibýt

#### Scenario: Akce bez alba
- **WHEN** akce v Immichi album nemá (např. není dokončená)
- **THEN** karta, plocha ani navigátor odkaz na nástroj nenabízejí

### Requirement: Osoby k pojmenování
Nástroj SHALL nabízet po jedné osoby Immiche, které nemají jméno, nejsou
skryté a mají aspoň jeden obličej na fotce v albu akce. Osoby odložené
v aktuálním kole (viz Odložení osoby) MUST NOT nabízet. Pořadí SHALL
být podle počtu obličejů osoby na fotkách akce sestupně. Nástroj SHALL
ukazovat, kolikátá osoba z kolika zbývajících je.

#### Scenario: Nepojmenovaná osoba
- **WHEN** album akce obsahuje fotku s obličejem osoby bez jména
- **THEN** nástroj tu osobu nabídne

#### Scenario: Pojmenovaná a skrytá osoba
- **WHEN** osoba má jméno `Vzorný, Tomáš`, nebo je v Immichi skrytá
- **THEN** nástroj ji nenabídne

#### Scenario: Pořadí
- **WHEN** jedna nepojmenovaná osoba má v akci 12 obličejů a druhá 2
- **THEN** nástroj nabídne nejdřív tu s 12 obličeji

### Requirement: Náhledy obličeje
U osoby SHALL nástroj ukázat až 3 výřezy jejího obličeje, každý z jiné
fotky akce. Výřez SHALL odpovídat obdélníku obličeje z Immiche na
zmenšenině fotky se správnou orientací. Náhledy SHALL jít přes server
aplikace, klíč Immiche MUST NOT opustit server. Server MUST vydat
náhled jen pro fotku z alba akce.

#### Scenario: Tři fotky
- **WHEN** osoba má obličej na 5 fotkách akce
- **THEN** nástroj ukáže 3 výřezy ze 3 různých fotek

#### Scenario: Jedna fotka
- **WHEN** osoba má obličej jen na jedné fotce akce
- **THEN** nástroj ukáže jeden výřez

#### Scenario: Cizí fotka
- **WHEN** prohlížeč požádá o náhled fotky, která v albu akce není
- **THEN** server vrátí 404

### Requirement: Metadata zdrojové fotky
U každého výřezu SHALL nástroj ukázat metadata fotky, ze které je:
z Immiche název souboru a datum pořízení a z archivu (po zdědění)
skupinu, datum, místo a autory souboru. Soubor, který nejde spárovat se
souborem akce, SHALL mít jen údaje z Immiche.

#### Scenario: Spárovaná fotka
- **WHEN** výřez je z `P9109996.JPG` ve skupině `DOD 2015_Jana`
- **THEN** nástroj u něj ukáže `P9109996.JPG`, datum pořízení
  a skupinu `DOD 2015_Jana` s jejím místem a autory

### Requirement: Pojmenování osoby
Nástroj SHALL nabídnout pole jména s našeptáváním ze seznamu jmen
a s kontrolou tvaru jako ostatní pole jmen (viz `person-names`).
Do Immiche SHALL zapsat jméno v kanonickém tvaru `Příjmení, Jméno`:
jméno ze seznamu ve tvaru ze seznamu, nové jméno po převodu, který
uživatel potvrdí. Prázdné jméno MUST NOT jít uložit. Po uložení SHALL
nástroj nabídnout další osobu.

#### Scenario: Jméno ze seznamu
- **WHEN** archivář napíše `Tomáš Vzorný` a seznam jmen obsahuje
  `Vzorný, Tomáš`
- **THEN** nástroj nabídne `Vzorný, Tomáš` a po potvrzení zapíše osobě
  v Immichi jméno `Vzorný, Tomáš`

#### Scenario: Nové jméno
- **WHEN** archivář napíše `Věra Ukázková`, které v seznamu není
- **THEN** nástroj nabídne převod na `Ukázková, Věra` a zapíše ho až
  po potvrzení

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

### Requirement: Odložení osoby
Volba „odložit“ SHALL osobu odložit: v aktuálním kole se už nenabídne.
Odložené osoby SHALL být uložené v pracovním adresáři zvlášť pro
každého uživatele a akci a MUST NOT jít do archivu ani do Immiche.
Kolo SHALL skončit, když nezbývá žádná neodložená osoba. Nástroj pak
SHALL nabídnout projít odložené znovu (nové kolo, odložení se
vymaže). Zavření nástroje a nové otevření kolo neukončí.

#### Scenario: Odložit
- **WHEN** archivář u osoby zvolí „odložit“
- **THEN** nástroj nabídne další osobu a odloženou v tomto kole už ne

#### Scenario: Znovuotevření
- **WHEN** archivář nástroj zavře a znovu otevře
- **THEN** odložené osoby se dál nenabízejí

#### Scenario: Konec kola
- **WHEN** zbývají jen odložené osoby
- **THEN** nástroj to oznámí a nabídne je projít znovu

#### Scenario: Jiný uživatel
- **WHEN** jeden archivář osobu odložil a druhý otevře nástroj nad
  stejnou akcí
- **THEN** druhému se osoba nabídne

### Requirement: Skrytí osoby
Volba „skrýt“ SHALL osobu v Immichi skrýt (vratně, obličeje zůstanou).
Skrytá osoba se v nástroji MUST NOT dál nabízet a MUST NOT se počítat
do osob akce v kompletnosti.

#### Scenario: Irelevantní obličej
- **WHEN** archivář skryje osobu z davu v pozadí
- **THEN** osoba je v Immichi skrytá a nástroj ani hotovost akce ji
  nepočítají

### Requirement: Klávesové zkratky nástroje
Volby nástroje SHALL jít ovládat z klávesnice i s kurzorem v poli
jména: Enter uloží jméno, a je-li nabídnuté sloučení, potvrdí ho;
PageDown osobu odloží, Alt+Delete ji skryje a Esc nástroj zavře.
Zkratky MUST NOT kolidovat s editací jména v poli ani se zkratkami
prohlížeče a tlačítka je SHALL uvádět v popisku; Enter SHALL ukazovat
ikonka u tlačítka, které právě stiskne („Sloučit“, je-li sloučení
nabídnuté, jinak „Uložit“). Dokud se zápis volby nevyřídí, další volba MUST NOT
odejít (podržená klávesa ani dvojklik nevyřídí víc osob).

#### Scenario: Sloučení Enterem
- **WHEN** nástroj po uložení jména nabídne sloučení a archivář
  v poli jména stiskne Enter
- **THEN** osoba se sloučí stejně jako tlačítkem „Sloučit“; ikonka
  Enteru je u „Sloučit“, ne u „Uložit“

#### Scenario: Úprava jména ruší sloučení
- **WHEN** archivář po nabídce sloučení jméno v poli upraví
- **THEN** nabídka sloučení zmizí a Enter jméno znovu uloží; ikonka
  Enteru je zpět u „Uložit“

#### Scenario: Odložení klávesou
- **WHEN** archivář s kurzorem v poli jména stiskne PageDown
- **THEN** osoba se odloží stejně jako tlačítkem „Odložit“

#### Scenario: Skrytí klávesou
- **WHEN** archivář stiskne Alt+Delete
- **THEN** osoba se skryje stejně jako tlačítkem „Skrýt“; klávesa
  v poli jména nic nesmaže

#### Scenario: Podržená klávesa
- **WHEN** archivář podrží PageDown
- **THEN** odloží se jen nabídnutá osoba, další se nabídne a nic víc

### Requirement: Oprávnění nástroje
Nástroj i jeho endpointy MUST server povolit jen adminovi a archiváři;
ostatním vrátí 403 a klient jim odkazy nezobrazí. Nástroj MUST NOT
vyžadovat zámek akce a MUST NOT měnit `_metadata.json`. Do Immiche
SHALL zapisovat v produkčním i vývojovém režimu. Klíč Immiche MUST NOT
být v žádné odpovědi serveru.

#### Scenario: Běžný uživatel
- **WHEN** uživatel bez role pošle pojmenování osoby
- **THEN** server vrátí 403 a v Immichi se nic nezmění

#### Scenario: Akce zamčená jiným
- **WHEN** akci drží zámkem jiný uživatel
- **THEN** archivář nástroj otevře a osoby pojmenovat může

### Requirement: Chyba Immiche v nástroji
Selže-li zápis do Immiche, SHALL nástroj ukázat chybu a ponechat osobu
jako aktuální; odložení ani posun na další osobu MUST NOT nastat.
Nedostupný Immich při otevření SHALL nástroj oznámit místo seznamu osob.

#### Scenario: Selhané pojmenování
- **WHEN** Immich při uložení jména vrátí chybu
- **THEN** nástroj chybu ukáže a osoba zůstane nabídnutá s vyplněným
  jménem

### Requirement: Převzetí jmen po zavření
Pojmenoval-li nebo skryl-li uživatel v nástroji aspoň jednu osobu, SHALL
server po zavření nástroje spustit synchronizaci na pozadí, aby se jména
dostala do `obliceje` a do počtů osob akce bez čekání na pravidelný
běh.

#### Scenario: Pojmenování a zavření
- **WHEN** archivář pojmenuje osobu na `P9109996.JPG` a nástroj zavře
- **THEN** server spustí synchronizaci a po jejím doběhnutí má soubor
  v `obliceje` nové jméno

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
