# immich-people Specification

## Purpose
Převzít pojmenované obličeje z Immiche, který je rozpoznává
a pojmenovává autoritativně, do `_metadata.json` souborů akcí jako
zálohu i podklad pro zobrazení osob.

## Requirements

### Requirement: Nastavení připojení
Aplikace SHALL nabídnout adminovi stránku nastavení s adresou serveru
Immich a API klíčem. Nastavení SHALL být uloženo v pracovním adresáři
s právy jen pro vlastníka, MUST NOT být zapsáno do archivu a klíč MUST
NOT být nikdy vrácen do prohlížeče (zobrazí se jen, že je nastaven,
a jeho poslední 4 znaky). Změna adresy MUST vyžadovat zadání klíče
znovu. Stránka SHALL umět připojení otestovat a nastavení smazat. Test
SHALL ověřit čtení osob a obličejů a vypsat chybějící oprávnění pro
alba akcí, sken knihovny, stav rozpoznávání a nástroj pojmenování osob.
Stránka SHALL nabídnout výběr knihovny Immiche, kterou dokončení akce
skenuje. Uložení, test, smazání
i synchronizaci ze stránky nastavení MUST server povolit jen adminovi.

#### Scenario: Uložení klíče
- **WHEN** admin zadá adresu a klíč a uloží je
- **THEN** stránka ukáže „klíč nastaven (…4No)“ a odpověď serveru
  klíč neobsahuje

#### Scenario: Změna adresy bez klíče
- **WHEN** admin změní adresu a klíč pole nechá prázdné
- **THEN** nastavení se neuloží a stránka požádá o klíč

#### Scenario: Test připojení
- **WHEN** admin klikne na Otestovat a Immich klíč přijme
- **THEN** stránka ukáže verzi Immiche a že připojení funguje

#### Scenario: Klíč bez oprávnění k obličejům
- **WHEN** klíč nemá oprávnění číst obličeje
- **THEN** test připojení to ohlásí jako chybu

#### Scenario: Klíč jen pro čtení
- **WHEN** klíč umí číst osoby a obličeje, ale nemá `person.update`
  ani `album.create`
- **THEN** test ohlásí, že čtení funguje, a vypíše chybějící oprávnění
  s tím, že alba akcí a pojmenování osob nebudou dostupné

#### Scenario: Klíč uživatele bez role admin v Immichi
- **WHEN** klíč má všechna oprávnění, ale patří uživateli Immiche bez
  role admin
- **THEN** test ohlásí, že sken knihovny a stav rozpoznávání nebudou
  dostupné, a ostatní funkce označí jako funkční

#### Scenario: Výběr knihovny
- **WHEN** admin na stránce nastavení vybere knihovnu ze seznamu
  knihoven Immiche a uloží ji
- **THEN** dokončení akce skenuje tuto knihovnu a test připojení už
  na chybějící knihovnu neupozorňuje

#### Scenario: Běžný uživatel
- **WHEN** uživatel bez příznaku admina pošle uložení nastavení
- **THEN** server vrátí 403 a nastavení se nezmění

### Requirement: Synchronizace obličejů
Je-li připojení nastaveno, server SHALL pravidelně a na požádání ze
stránky nastavení načíst z Immiche pojmenované obličeje a zapsat je do
pole `obliceje` souborů jako seznam `{jmeno, oblast}`. Synchronizace
SHALL zpracovat jen akce, které už mají `_metadata.json`, a zapisovat
podle režimu (archiv / pracovní adresář) jako ostatní ukládání.
Soubor, u kterého Immich žádný pojmenovaný obličej nemá, SHALL
`obliceje` ztratit. Nepojmenované obličeje MUST NOT být ukládány.
`_metadata.json` SHALL být přepsán jen tehdy, když se obličeje
některého souboru změnily.

#### Scenario: Nově pojmenovaný obličej
- **WHEN** uživatel v Immichi pojmenuje obličej na `P9109996.JPG`
  jako `Vzorný, Tomáš` a proběhne synchronizace
- **THEN** soubor má v `obliceje` položku s `jmeno` `Vzorný, Tomáš`
  a oblastí toho obličeje

#### Scenario: Odebraná osoba
- **WHEN** soubor má jeden obličej `Vzorný, Tomáš` a v Immichi už na
  něm žádný pojmenovaný obličej není
- **THEN** po synchronizaci soubor `obliceje` nemá

#### Scenario: Nepojmenovaný obličej
- **WHEN** Immich má na fotce tři obličeje a jen jeden je pojmenovaný
- **THEN** `obliceje` souboru má jednu položku

#### Scenario: Akce bez metadat
- **WHEN** Immich zná fotky akce, která nemá `_metadata.json`
- **THEN** synchronizace soubor nevytvoří a akce zůstane
  *nezpracováno*

#### Scenario: Immich nedostupný
- **WHEN** kterýkoli dotaz na Immich během běhu selže
- **THEN** synchronizace nic nezapíše a stránka nastavení ukáže chybu
  a čas posledního úspěšného běhu

### Requirement: Oblast obličeje
`oblast` SHALL být `[x, y, w, h]` jako podíly rozměrů fotky (0–1):
střed obličeje a jeho šířka a výška, ve tvaru oblastí MWG. Hodnoty
SHALL být přepočtené z obdélníku obličeje a rozměru obrázku, ke
kterému ho Immich vztahuje, a zaokrouhlené na 4 desetinná místa.
Oblast SHALL odpovídat fotce zobrazené se správnou orientací.

#### Scenario: Přepočet
- **WHEN** Immich vrátí obličej `x1=252, y1=296, x2=293, y2=352`
  na obrázku 1000 × 750
- **THEN** `oblast` je `[0.2725, 0.432, 0.041, 0.0747]`

#### Scenario: Jiné měřítko
- **WHEN** Immich vztahuje obličej ke zmenšenině 1440 × 1920 místo
  originálu 2736 × 3648
- **THEN** `oblast` je stejná, jako kdyby obdélník byl v originálu

### Requirement: Zámek při synchronizaci
Synchronizace MUST NOT zapisovat do akce, kterou drží zámkem uživatel;
takovou akci SHALL přeskočit a zpracovat při dalším běhu. Po dobu zápisu
SHALL synchronizace držet zámek akce sama, takže ji uživatel mezitím
otevře jen ke čtení.

#### Scenario: Zamčená akce
- **WHEN** uživatel má akci otevřenou se zámkem a proběhne synchronizace
- **THEN** její `_metadata.json` se nezmění a stránka nastavení ji uvede
  jako přeskočenou

### Requirement: Párování souborů
Asset z Immiche SHALL být přiřazen souboru podle posledních dvou částí
své původní cesty: názvu složky akce a názvu souboru. Kořen archivu
v Immichi MUST NOT být potřeba nastavovat.

#### Scenario: Jiný kořen v Immichi
- **WHEN** Immich vidí soubor jako
  `/immich/archiv/…/2026-09-08 Konference Příkladné metody/P9109996.JPG`
  a aplikace archiv na `/cesta/k/archivu/…`
- **THEN** obličeje se zapíšou k `P9109996.JPG` akce
  `2026-09-08 Konference Příkladné metody`

### Requirement: Tvar jmen z Immiche
Jméno osoby z Immiche, které se podle porovnání jmen (bez diakritiky,
velikosti písmen a pořadí slov) shoduje se jménem v seznamu jmen, SHALL
být zapsáno v kanonickém tvaru ze seznamu; jinak SHALL být zapsáno, jak
je v Immichi.

#### Scenario: Obrácené pořadí
- **WHEN** Immich má osobu `Tomáš Vzorný` a seznam jmen obsahuje
  `Vzorný, Tomáš`
- **THEN** do `jmeno` se zapíše `Vzorný, Tomáš`

### Requirement: Album akce
Dokončení akce SHALL po zveřejnění složky spustit na pozadí sken
knihovny vybrané v nastavení a hned odpovědět. Na Immich MUST NOT
čekat a chyba Immiche MUST NOT dokončení zabránit. Jakmile Immich zná
soubory akce, SHALL aplikace v Immichi založit album pojmenované jako
akce. Pravidelná synchronizace SHALL album každé dokončené akce, jejíž
fotky Immich zná, udržovat: chybějící assety doplnit a assety, které
už k akci nepatří, odebrat. Album SHALL obsahovat assety spárované se
soubory v kořeni akce (viz Párování souborů) kromě označených
k vyřazení. Assety MUST NOT mazat. Album samotné MUST NOT mazat,
s jedinou výjimkou: při trvalém smazání akce z koše (viz `event-trash`)
SHALL aplikace album akce v Immichi smazat; assety ani tehdy nemaže. Vazba akce na
album SHALL být v pracovním adresáři. Nedokončená akce album MUST NOT
dostat. Ve vývojovém režimu SHALL dokončení sken vynechat a album
založit jen tehdy, když Immich fotky akce už zná.

#### Scenario: Dokončení akce
- **WHEN** archivář dokončí akci `2026-09-08 Konference Příkladné metody` a
  Immich její složku po spuštěném skenu načte
- **THEN** Immich má album `2026-09-08 Konference Příkladné metody`
  se všemi jejími fotkami, aniž by se čekalo na pravidelnou
  synchronizaci

#### Scenario: Dokončení nečeká na Immich
- **WHEN** archivář dokončí akci a Immich je nedostupný
- **THEN** dokončení proběhne jako dosud a album založí pozdější
  synchronizace

#### Scenario: Immich fotky ještě nezná
- **WHEN** akce je dokončená, ale Immich ještě žádný její asset nemá
- **THEN** album se nezaloží a synchronizace to zkusí při dalším běhu

#### Scenario: Restart serveru během čekání
- **WHEN** server se po dokončení akce restartuje dřív, než Immich
  fotky načte
- **THEN** album založí nejbližší pravidelná synchronizace, která fotky
  najde

#### Scenario: Album smazané v Immichi
- **WHEN** uložené album v Immichi už neexistuje
- **THEN** synchronizace založí nové a uloží jeho vazbu

#### Scenario: Klíč bez oprávnění k albům
- **WHEN** klíč nemá oprávnění zakládat alba
- **THEN** synchronizace obličeje zapíše jako dosud a stránka nastavení
  ukáže, že alba nejde vést

#### Scenario: Vývojový režim
- **WHEN** akce se dokončí ve vývojovém režimu
- **THEN** sken se nespustí, a pokud Immich fotky akce zná, album se
  založí

#### Scenario: Akce vysypaná z koše
- **WHEN** vysypání koše trvale smaže akci
  `2026-09-08 Konference Příkladné metody`, která má v Immichi album
- **THEN** album v Immichi neexistuje a vazba akce na album
  v pracovním adresáři je odstraněná

#### Scenario: Akce v koši
- **WHEN** dokončená akce leží v koši a proběhne synchronizace
- **THEN** synchronizace její album nemění ani nemaže


### Requirement: Stav akce v Immichi
Aplikace SHALL u každé dokončené akce vést v pracovním adresáři stav
v Immichi: *načítá fotky*, *rozpoznávání obličejů probíhá*, *obličeje
rozpoznány* (s časem), nebo *fotky nenalezeny*. *Obličeje rozpoznány*
SHALL nastat, když mají všechny assety alba zmenšeninu a fronty
detekce i rozpoznávání obličejů v Immichi nemají aktivní ani čekající
úlohy. Stav SHALL vidět každý přihlášený uživatel na kartě akce i na
ploše akce. Plocha ho SHALL během načítání a rozpoznávání průběžně
obnovovat. Zobrazení stavu MUST NOT se ptát Immiche. Chyba spojení
nebo chybějící oprávnění MUST NOT stav měnit. Bez nastaveného Immiche
se stav nezobrazuje.

#### Scenario: Po dokončení
- **WHEN** archivář dokončí akci a Immich její fotky ještě nenačetl
- **THEN** plocha akce ukáže „Immich načítá fotky“ a bez obnovení
  stránky přejde na „Rozpoznávání obličejů probíhá“, až album vznikne

#### Scenario: Rozpoznání doběhlo
- **WHEN** všechny fotky alba mají zmenšeninu a fronty rozpoznávání
  obličejů jsou prázdné
- **THEN** karta i plocha akce ukážou „Obličeje rozpoznány“ s datem
  a synchronizace převezme obličeje a počty osob

#### Scenario: Běžný uživatel
- **WHEN** akci bez práv k úpravě otevře přihlášený uživatel bez role
  archivář
- **THEN** vidí stav akce v Immichi stejně jako archivář

#### Scenario: Immich fotky nenašel
- **WHEN** do vypršení hlídání Immich žádný soubor akce nenačetl
- **THEN** karta ukáže „Immich fotky akce zatím nenašel“ a pozdější
  synchronizace stav změní, jakmile fotky najde

### Requirement: Osoby akce
Synchronizace SHALL pro každou akci s albem uložit do pracovního
adresáře počet osob s obličejem na fotkách alba: pojmenovaných
a nepojmenovaných. Skryté osoby MUST NOT započítat. Selže-li zjištění
osob akce, SHALL zůstat uložený předchozí stav.

#### Scenario: Počty osob
- **WHEN** fotky alba akce mají obličeje 4 pojmenovaných osob,
  2 nepojmenovaných a 1 skryté
- **THEN** u akce je uloženo 4 pojmenované z 6 osob

#### Scenario: Pojmenování v Immichi
- **WHEN** uživatel pojmenuje jednu z nepojmenovaných osob a proběhne
  synchronizace
- **THEN** u akce je uloženo 5 pojmenovaných z 6 osob
