## MODIFIED Requirements

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
