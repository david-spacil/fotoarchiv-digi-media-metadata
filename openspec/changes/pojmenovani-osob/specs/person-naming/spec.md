# Spec Delta

## Purpose
Provést archiváře po jedné nepojmenovanými osobami Immiche, které mají
obličej na fotkách akce, a pojmenovat, odložit nebo skrýt je přímo
v Immichi, odkud jména přebírá synchronizace.

## ADDED Requirements

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
Po potvrzení SHALL osobu sloučit do existující osoby. Při odmítnutí
SHALL osobu jen pojmenovat a ponechat jako samostatnou.

#### Scenario: Sloučení
- **WHEN** archivář zadá `Vzorný, Tomáš` a Immich už osobu
  `Vzorný, Tomáš` má
- **THEN** nástroj nabídne sloučení a po potvrzení zůstane v Immichi
  jediná osoba `Vzorný, Tomáš` s obličeji obou

#### Scenario: Odmítnuté sloučení
- **WHEN** archivář sloučení odmítne
- **THEN** v Immichi jsou dvě osoby se jménem `Vzorný, Tomáš`

### Requirement: Odložení osoby
Volba „nevím“ SHALL osobu odložit: v aktuálním kole se už nenabídne.
Odložené osoby SHALL být uložené v pracovním adresáři zvlášť pro
každého uživatele a akci a MUST NOT jít do archivu ani do Immiche.
Kolo SHALL skončit, když nezbývá žádná neodložená osoba. Nástroj pak
SHALL nabídnout projít odložené znovu (nové kolo, odložení se
vymaže). Zavření nástroje a nové otevření kolo neukončí.

#### Scenario: Nevím
- **WHEN** archivář u osoby zvolí „nevím“
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
