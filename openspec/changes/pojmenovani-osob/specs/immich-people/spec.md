## MODIFIED Requirements

### Requirement: Nastavení připojení
Aplikace SHALL nabídnout adminovi stránku nastavení s adresou serveru
Immich a API klíčem. Nastavení SHALL být uloženo v pracovním adresáři
s právy jen pro vlastníka, MUST NOT být zapsáno do archivu a klíč MUST
NOT být nikdy vrácen do prohlížeče (zobrazí se jen, že je nastaven,
a jeho poslední 4 znaky). Změna adresy MUST vyžadovat zadání klíče
znovu. Stránka SHALL umět připojení otestovat a nastavení smazat. Test
SHALL ověřit čtení osob a obličejů a vypsat chybějící oprávnění pro
alba akcí a nástroj pojmenování osob. Uložení, test, smazání
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

#### Scenario: Běžný uživatel
- **WHEN** uživatel bez příznaku admina pošle uložení nastavení
- **THEN** server vrátí 403 a nastavení se nezmění

## ADDED Requirements

### Requirement: Album akce
Synchronizace SHALL pro každou dokončenou akci, jejíž fotky Immich už
zná, vést v Immichi album pojmenované jako akce. Album SHALL obsahovat
assety spárované se soubory v kořeni akce (viz Párování souborů).
Chybějící assety SHALL doplnit a assety, které už k akci nepatří,
z alba odebrat. Assety ani album samotné MUST NOT mazat. Vazba akce na
album SHALL být v pracovním adresáři. Nedokončená akce album MUST NOT
dostat.

#### Scenario: Nově dokončená akce
- **WHEN** akce `2026-09-08 Konference Dějiny archeologie` je dokončená
  a Immich už její fotky proskenoval
- **THEN** po synchronizaci má Immich album
  `2026-09-08 Konference Dějiny archeologie` se všemi jejími fotkami

#### Scenario: Immich fotky ještě nezná
- **WHEN** akce je dokončená, ale Immich ještě žádný její asset nemá
- **THEN** synchronizace album nezaloží a zkusí to při dalším běhu

#### Scenario: Album smazané v Immichi
- **WHEN** uložené album v Immichi už neexistuje
- **THEN** synchronizace založí nové a uloží jeho vazbu

#### Scenario: Klíč bez oprávnění k albům
- **WHEN** klíč nemá oprávnění zakládat alba
- **THEN** synchronizace obličeje zapíše jako dosud a stránka nastavení
  ukáže, že alba nejde vést

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
