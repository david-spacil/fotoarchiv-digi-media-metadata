## MODIFIED Requirements

### Requirement: Účty uživatelů
Uživatelé SHALL být definováni v souboru `uzivatele.json` v pracovním
adresáři: login → kanonické jméno `Příjmení, Jméno`, volitelně e-mail
a role (`"role": "admin"` nebo `"role": "archivar"`; bez role běžný
uživatel). Aplikace MUST tento soubor jen číst a MUST NOT nabízet
správu uživatelů. Uživatel odebraný ze souboru MUST přijít o přístup
nejpozději při dalším požadavku; změna role MUST platit nejpozději při
dalším požadavku.

Záznam s klíčem `admin` (dřívější zápis role) nebo s neznámou hodnotou
`role` je chybný. Při startu serveru i u příkazu pro jednorázové heslo
MUST takový soubor vést k odmítnutí s chybou, která vypíše chybné
loginy a jak záznam opravit (`"admin": true` → `"role": "admin"`).
Objeví-li se chybný záznam za běhu, server MUST pokračovat, chybný
login MUST NOT mít přístup (401) a server SHALL chybu zapsat do logu.

#### Scenario: Odebraný uživatel
- **WHEN** správce odebere login z `uzivatele.json`, zatímco je
  uživatel přihlášený
- **THEN** jeho další požadavek skončí 401

#### Scenario: Odebraná role archiváře
- **WHEN** správce archiváři odebere roli, zatímco je přihlášený
- **THEN** jeho další pokus uložit akci, v jejímž `upravili` není,
  skončí 403

#### Scenario: Starý zápis admina při startu
- **WHEN** `uzivatele.json` obsahuje
  `{"prikladny": {"jmeno": "Příkladný, Daniel", "admin": true}}` a server se
  spouští
- **THEN** server nenastartuje a vypíše login `prikladny` s návodem
  nahradit `"admin": true` za `"role": "admin"`

#### Scenario: Chybný záznam za běhu
- **WHEN** správce za běhu serveru zapíše uživateli `"role": "spravce"`
- **THEN** jeho další požadavek skončí 401, ostatní uživatelé pracují
  dál a log uvádí chybný login

### Requirement: Role admin
Nastavení serveru (připojení k Immichi včetně synchronizace na
požádání, kontakt pro Nominatim) MUST server povolit jen adminovi;
ostatním (včetně archiváře) vrátí 403. Klient SHALL Nastavení
uživateli bez role admin nezobrazit.

#### Scenario: Běžný uživatel a nastavení
- **WHEN** uživatel bez role admin pošle změnu nastavení Immiche
- **THEN** server vrátí 403 a nastavení se nezmění

#### Scenario: Archivář a nastavení
- **WHEN** archivář otevře aplikaci
- **THEN** odkaz Nastavení nevidí a změnu nastavení Nominatimu mu
  server odmítne s 403

## ADDED Requirements

### Requirement: Role archivář
Přehled složky `přetřídit` s importem z ní a vynucené uvolnění zámku
akce MUST server povolit jen adminovi a archiváři; ostatním vrátí 403.
Klient SHALL tyto prvky ostatním uživatelům nezobrazit.

#### Scenario: Běžný uživatel a přetřídit
- **WHEN** uživatel bez role požádá o přehled `přetřídit`
- **THEN** server vrátí 403 a seznam akcí mu odkaz Přetřídit neukáže

#### Scenario: Archivář uvolní zámek
- **WHEN** archivář otevře akci, jejíž zámek drží jiný uživatel
- **THEN** může zámek vynuceně uvolnit

### Requirement: Oprávnění k úpravě akce
Prohlížet SHALL smět každý přihlášený uživatel každou akci včetně
náhledů a originálů. Upravit akci (zámek, uložení metadat, dokončení,
úklid, import do ní) SHALL smět:
- admin a archivář každou akci,
- ostatní uživatelé jen akci, v jejímž `upravili` (viz
  `metadata-model`) je jejich jméno; jména se porovnávají bez ohledu na
  diakritiku, velikost písmen a pořadí slov.

Server MUST zámek akce uživateli bez oprávnění odmítnout s 403
a MUST odmítnout s 403 i úpravu pod zámkem, o jehož oprávnění uživatel
mezitím přišel. Akce bez `_metadata.json` nebo bez `upravili` SHALL
smět upravit jen admin a archivář. Výpis akcí SHALL u každé akce uvést,
zda ji přihlášený uživatel smí upravit. Klient SHALL akci bez oprávnění
otevřít jen ke čtení s vysvětlením, proč ji nelze upravit, a nenabídnout
v ní akce, které ji mění. Bez přihlášení (vývojový režim) smí upravit
každý všechno.

#### Scenario: Vlastní import
- **WHEN** uživatel Modelová, Zuzana bez role naimportuje novou akci
  a otevře ji
- **THEN** získá zámek a může akci upravovat

#### Scenario: Cizí akce
- **WHEN** uživatel bez role otevře akci, v jejímž `upravili` není
- **THEN** vidí plochu jen ke čtení s vysvětlením a server mu zámek
  odmítne s 403

#### Scenario: Archivář
- **WHEN** archivář otevře akci bez `upravili`
- **THEN** získá zámek a může ji upravit i dokončit

#### Scenario: Jméno bez diakritiky
- **WHEN** v `upravili` je `Modelova, Zuzana` a přihlášený uživatel má
  jméno `Modelová, Zuzana`
- **THEN** akci smí upravit
