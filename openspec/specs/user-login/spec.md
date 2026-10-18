# user-login Specification

## Purpose

Omezit přístup ke sdílenému serveru na přihlášené uživatele, dát zámku
akce ověřenou identitu a vyhradit nastavení serveru adminovi.

## Requirements

### Requirement: Povinné přihlášení
V produkčním režimu MUST server odmítnout každý požadavek na stránky
i API bez platného přihlášení; stránky přesměruje na přihlášení, API
vrátí 401. Bez přihlášení smí server běžet jen ve vývojovém režimu
s výslovným přepínačem; pak je každý uživatel admin.

#### Scenario: Nepřihlášený požadavek na API
- **WHEN** klient bez přihlášení pošle uložení metadat
- **THEN** server vrátí 401 a archiv zůstane beze změny

#### Scenario: Produkce bez přihlášení
- **WHEN** se server spustí s `--zapis-do-archivu` a `--bez-prihlaseni`
- **THEN** server odmítne start s chybou

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

### Requirement: Uložení hesel
Hesla MUST být uložena jen jako hash se solí v souboru `hesla.json`
v pracovním adresáři s právy jen pro vlastníka, odděleně od
`uzivatele.json`. Heslo ani hash MUST NOT být zapsány do archivu,
logu ani vráceny do prohlížeče.

#### Scenario: Obsah souboru hesel
- **WHEN** uživatel nastaví heslo `tajne-heslo-1`
- **THEN** `hesla.json` obsahuje hash a text `tajne-heslo-1` v něm není

### Requirement: Jednorázové heslo
Příkaz na serveru SHALL pro zadaný login vygenerovat náhodné
jednorázové heslo, vypsat ho a uložit jeho hash s příznakem povinné
změny. Po přihlášení jednorázovým heslem MUST server odmítat všechny
požadavky kromě změny hesla a odhlášení. Vydání nového hesla MUST
zneplatnit stávající relace uživatele.

#### Scenario: První přihlášení
- **WHEN** uživatel se přihlásí jednorázovým heslem
- **THEN** aplikace ukáže jen změnu hesla a akce nejdou otevřít, dokud
  heslo nezmění

#### Scenario: Zapomenuté heslo
- **WHEN** správce vydá uživateli nové jednorázové heslo
- **THEN** staré heslo přestane platit a jeho otevřené relace skončí

### Requirement: Změna hesla
Přihlášený uživatel SHALL si moci v aplikaci změnit heslo zadáním
stávajícího a nového hesla. Nové heslo MUST mít aspoň 10 znaků a lišit
se od stávajícího. Změna MUST zneplatnit ostatní relace uživatele;
relace, ze které změna proběhla, zůstane přihlášená.

#### Scenario: Změna hesla
- **WHEN** uživatel zadá správné stávající heslo a nové heslo
- **THEN** příště se přihlásí jen novým heslem a jeho přihlášení
  v jiném prohlížeči skončí

#### Scenario: Špatné stávající heslo
- **WHEN** uživatel zadá chybné stávající heslo
- **THEN** heslo se nezmění a aplikace ohlásí chybu

### Requirement: Ochrana přihlášení
Odpověď na neúspěšné přihlášení MUST NOT prozradit, zda login existuje.
Po opakovaných chybných pokusech na jeden login SHALL server další
pokusy zdržovat.

#### Scenario: Neexistující login
- **WHEN** se někdo přihlašuje neexistujícím loginem
- **THEN** dostane stejnou chybu jako při špatném heslu

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

### Requirement: Identita u zámku
Jméno držitele zámku SHALL server brát z přihlášení (kanonické jméno
z `uzivatele.json`), ne z požadavku klienta.

#### Scenario: Držitel zámku
- **WHEN** přihlášený uživatel otevře volnou akci
- **THEN** ostatní vidí jako držitele jeho kanonické jméno bez ohledu
  na to, co klient poslal

### Requirement: Odhlášení
Uživatel SHALL se moci odhlásit; odhlášení MUST uvolnit zámek jeho
relace.

#### Scenario: Odhlášení s otevřenou akcí
- **WHEN** uživatel s otevřenou akcí se odhlásí
- **THEN** zámek akce se uvolní

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
