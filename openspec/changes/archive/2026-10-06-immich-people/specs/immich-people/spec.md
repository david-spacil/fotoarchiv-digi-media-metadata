## Purpose

Převzít pojmenované obličeje z Immiche, který je rozpoznává
a pojmenovává autoritativně, do `_metadata.json` souborů akcí jako
zálohu i podklad pro zobrazení osob.

## ADDED Requirements

### Requirement: Nastavení připojení
Aplikace SHALL nabídnout stránku nastavení s adresou serveru Immich
a API klíčem. Nastavení SHALL být uloženo v pracovním adresáři
s právy jen pro vlastníka, MUST NOT být zapsáno do archivu a klíč MUST
NOT být nikdy vrácen do prohlížeče (zobrazí se jen, že je nastaven,
a jeho poslední 4 znaky). Změna adresy MUST vyžadovat zadání klíče
znovu. Stránka SHALL umět připojení otestovat (včetně oprávnění číst
osoby a obličeje) a nastavení smazat.

#### Scenario: Uložení klíče
- **WHEN** uživatel zadá adresu a klíč a uloží je
- **THEN** stránka ukáže „klíč nastaven (…4No)“ a odpověď serveru
  klíč neobsahuje

#### Scenario: Změna adresy bez klíče
- **WHEN** uživatel změní adresu a klíč pole nechá prázdné
- **THEN** nastavení se neuloží a stránka požádá o klíč

#### Scenario: Test připojení
- **WHEN** uživatel klikne na Otestovat a Immich klíč přijme
- **THEN** stránka ukáže verzi Immiche a že připojení funguje

#### Scenario: Klíč bez oprávnění k obličejům
- **WHEN** klíč nemá oprávnění číst obličeje
- **THEN** test připojení to ohlásí jako chybu

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
