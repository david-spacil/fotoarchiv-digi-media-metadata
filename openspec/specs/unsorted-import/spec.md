# unsorted-import Specification

## Purpose

Importovat nezatříděné akce ze složky `přetřídit` v kořeni archivu
přímo na místě: přehled kandidátů, převzetí složky do průvodce importem
a přesun souborů do akce bez kopií a bez nahrávání přes prohlížeč.

## Requirements

### Requirement: Přehled složky přetřídit
Aplikace SHALL nabídnout adminovi a archiváři (viz `user-login`) ze
seznamu akcí stránku Přetřídit se seznamem složek první úrovně složky
`přetřídit` v kořeni archivu, seřazených podle názvu. Složky s příponou
`.ignored` a soubory první úrovně MUST NOT být nabídnuty. U každé složky
SHALL stránka ukázat počet fotek, videí, RAWů a ostatních souborů (bez
`Thumbs.db`, včetně podsložek), názvy podsložek, rozsah dat z EXIF (u
WhatsApp fotek z názvu souboru), datum rozpoznané z názvu složky a
navrženou akci `YYYY-MM-DD název`. Neexistuje-li složka `přetřídit`, SHALL
stránka ukázat prázdný seznam.

#### Scenario: Složka s duplicitami
- **WHEN** `přetřídit` obsahuje `DOD 2017`, `_duplicity.ignored`
  a `poznamky.txt`
- **THEN** stránka nabídne jen `DOD 2017`

#### Scenario: Podsložky v počtech
- **WHEN** `Stuchlík 70` má v kořeni 92 JPG a v podsložce `NEF`
  91 NEF
- **THEN** stránka uvede 92 fotek, 91 RAWů a podsložku `NEF`

#### Scenario: Uživatel bez role
- **WHEN** uživatel bez role admin ani archivář otevře seznam akcí
- **THEN** odkaz Přetřídit nevidí a server mu přehled odmítne s 403

### Requirement: Návrh data a názvu akce
Navržené datum akce SHALL být nejstarší den z EXIF médií složky; bez
něj datum rozpoznané z názvu složky; jinak SHALL návrh datum vynechat
a uživatel ho doplní. Z názvu MUST aplikace rozpoznat aspoň tvary
`d.m.yyyy`, `yyyy_mm_dd`, `yyyy_m_d` a `dd_mm_yyyy` (s jednocifernými
i dvoucifernými dny a měsíci); samotný rok MUST NOT dát celé datum.
Navržený název SHALL být název složky.

#### Scenario: Datum jen v názvu
- **WHEN** složka `komise_Mikulčice_31.8.2012` nemá EXIF datum
- **THEN** navržená akce je `2012-08-31 komise_Mikulčice_31.8.2012`

#### Scenario: EXIF má přednost
- **WHEN** složka `Praha 2017` má fotky s EXIF datem 14. a 15. 6. 2017
- **THEN** navržené datum je `2017-06-14`

#### Scenario: Jen rok
- **WHEN** složka `DOD 2017` nemá EXIF datum
- **THEN** návrh datum nemá a stránka uvede rok 2017 z názvu

### Requirement: Průběh a cache přehledu
Údaje z EXIF SHALL aplikace cachovat v pracovním adresáři podle jména,
velikosti a času změny souboru; nezměněná složka MUST NOT vyžadovat
nové čtení EXIF. Během čtení SHALL stránka ukazovat průběh po složkách
a složky s hotovými údaji ukázat hned.

#### Scenario: Druhé otevření
- **WHEN** uživatel otevře stránku Přetřídit podruhé beze změny složek
- **THEN** stránka ukáže všechny údaje bez nového čtení EXIF

### Requirement: Průběh kontroly zdroje
Kontrola zdroje v `přetřídit` SHALL ukazovat průběh podle přečtených
bajtů, i uvnitř velkých souborů. Tentýž průchod SHALL spočítat sha256
souborů a uložit ho do cache, aby plán soubory zdroje znovu nečetl.

#### Scenario: Plán po kontrole
- **WHEN** kontrola zdroje `HLOZEK` doběhne a uživatel nechá ukázat
  plán
- **THEN** plán soubory zdroje znovu nečte
### Requirement: Import ze složky přetřídit
Admin a archivář SHALL moci ze stránky Přetřídit i v kroku Soubory
průvodce importem zvolit jednu složku první úrovně `přetřídit` jako zdroj
importu. Import SHALL vzniknout bez nahrávání a průvodce SHALL otevřít
přehled. Ze stránky Přetřídit SHALL mít cíl předvyplněnou novou akci
s navrženým datem a názvem. Soubory všech podsložek zdroje SHALL import
brát jako nahranou složku (zploštění, skupiny podle podsložek, RAWy
do `RAW.ignored/`) s výjimkou podsložek s příponou `.ignored`, které
MUST přeskočit i s obsahem. Založení i provedení importu se zdrojem
MUST server ostatním uživatelům odmítnout s 403; průvodce jim volbu
zdroje v kroku Soubory SHALL nenabídnout.

#### Scenario: Import celé složky
- **WHEN** uživatel na stránce Přetřídit klikne na `Vánoční večírek
  2019_Pavlov` s podsložkami `Pavlov` a `Pavlov2`
- **THEN** průvodce ukáže přehled jejích 174 fotek, cíl nová akce
  s navrženým datem a názvem a předvolbu skupin podle podsložek

#### Scenario: Vyloučená podsložka
- **WHEN** `Procházka 60` obsahuje kořen, `JPEG orig.ignored` a `NEF`
- **THEN** import obsahuje fotky z kořene a RAWy z `NEF`, soubory
  z `JPEG orig.ignored` ne

#### Scenario: Import ze zdroje bez role
- **WHEN** uživatel bez role pošle založení importu se zdrojem
  `DOD 2017`
- **THEN** server vrátí 403 a import nevznikne

### Requirement: Přesun ze zdroje
V produkčním režimu SHALL provedení importu se zdrojem v `přetřídit`
soubory do akce přesunout, ne zkopírovat. Přesun MUST NOT přepsat
existující soubor a MUST zachovat obsah i čas změny. Plán SHALL server
při každém sestavení uložit k importu jako snímek souborů zdroje
(cesta, velikost, čas změny); měřítkem provedení je poslední plán.
Provedení bez uloženého plánu MUST server odmítnout. Soubor ze snímku,
který ve zdroji při provedení není, MUST výsledek uvést jako selhaný;
soubor, jehož velikost nebo čas změny se od plánu změnily, MUST zůstat
ve zdroji a výsledek ho uvede jako blokovaný. Soubor, který do zdroje
přibyl po plánu, MUST NOT server přesunout a výsledek ho SHALL uvést
zvlášť. Duplicity, blokované a nepodporované soubory MUST zůstat ve
zdroji. Ve vývojovém režimu MUST zdroj i archiv zůstat beze změny.

#### Scenario: Přesun do nové akce
- **WHEN** uživatel v produkčním režimu provede import `BONGO ZK`
  (40 JPG) do nové akce `2017-05-10 BONGO ZK`
- **THEN** 40 JPG je v kořeni akce se stejným obsahem a časem změny
  a ve složce `přetřídit/BONGO ZK` už nejsou

#### Scenario: Duplicita zůstane
- **WHEN** jeden soubor zdroje má stejný obsah jako soubor v kořeni
  cílové akce
- **THEN** zůstane ve zdroji a výsledek ho uvede jako duplicitu

#### Scenario: Zmizel po plánu
- **WHEN** po sestavení plánu někdo ze zdroje smaže `a.jpg`
- **THEN** výsledek uvede `a.jpg` jako selhaný („ve zdroji už není“)

#### Scenario: Přibyl po plánu
- **WHEN** po sestavení plánu přibude do zdroje `nova.jpg`
- **THEN** `nova.jpg` zůstane ve zdroji a výsledek ho uvede jako
  přibylý po plánu

#### Scenario: Změnil se po plánu
- **WHEN** se `b.jpg` po sestavení plánu změní velikost
- **THEN** `b.jpg` zůstane ve zdroji a výsledek ho uvede jako
  blokovaný („změnil se po plánu“)

### Requirement: Poškozené soubory ve zdroji
Poškozené soubory zdroje v `přetřídit`, které import nepřenese, MUST
zůstat ve zdroji a výsledek je SHALL uvést mezi tím, co ve zdroji
zůstalo. Smazání poškozeného souboru zdroje (podle `photo-import`) MUST
jít jen v produkčním režimu, jen pokud se soubor od kontroly nezměnil,
a MUST NOT probíhat, když zdroj drží zámek jiné relace.

#### Scenario: Poškozený soubor zůstane
- **WHEN** import složky `HLOZEK` přesune všechna média kromě
  nečitelného `20151107_140851.jpg`
- **THEN** soubor zůstane v `přetřídit/HLOZEK`, složka nezanikne
  a výsledek ho uvede jako poškozený

#### Scenario: Smazání ze zdroje
- **WHEN** uživatel v produkčním režimu potvrdí smazání nečitelného
  `20151107_140851.jpg` ze zdroje `HLOZEK`
- **THEN** soubor zmizí z `přetřídit/HLOZEK` a z přehledu importu

#### Scenario: Vývojový režim
- **WHEN** uživatel ve vývojovém režimu chce smazat poškozený soubor
  zdroje
- **THEN** průvodce smazání nenabídne a zdroj zůstane beze změny
### Requirement: Úklid zdroje
Po provedení SHALL server smazat podsložky zdroje a nakonec zdrojovou
složku, pokud jsou prázdné nebo obsahují jen `Thumbs.db`. Složka se
zbylými soubory MUST zůstat a stránka Přetřídit ji SHALL dál nabízet
se zbylými počty.

#### Scenario: Vyprázdněná složka
- **WHEN** import přesune všechny soubory složky `AMČR 21.3.2017`
  a zbyl v ní jen `Thumbs.db`
- **THEN** složka zmizí z `přetřídit` i ze stránky Přetřídit

#### Scenario: Zbytky
- **WHEN** po importu zbyde v `DOD 2016/DOD 2016 _ fb` jeden soubor
  `.docx`
- **THEN** `DOD 2016` i tato podsložka zůstanou a stránka uvede jeden
  ostatní soubor

### Requirement: Zámek zdroje
Během provedení importu ze zdroje MUST server zdrojovou složku držet
zamčenou pro tuto relaci; jiné provedení importu ze stejné složky MUST
odmítnout s uvedením, kdo ji drží. Po skončení nebo přerušení provedení
SHALL server zámek zdroje uvolnit.

#### Scenario: Dva importy téže složky
- **WHEN** Jana provádí import ze složky `DOD 2019` a Pavel spustí
  provedení svého importu ze stejné složky
- **THEN** Pavlův import server odmítne a uvede, že složku přesouvá
  Jana
