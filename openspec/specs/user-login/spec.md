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
a příznak admina. Aplikace MUST tento soubor jen číst a MUST NOT
nabízet správu uživatelů. Uživatel odebraný ze souboru MUST přijít
o přístup nejpozději při dalším požadavku.

#### Scenario: Odebraný uživatel
- **WHEN** správce odebere login z `uzivatele.json`, zatímco je
  uživatel přihlášený
- **THEN** jeho další požadavek skončí 401

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
požádání, kontakt pro Nominatim) a vynucené uvolnění zámku MUST server
povolit jen adminovi; ostatním vrátí 403. Klient SHALL tyto prvky
běžnému uživateli nezobrazit.

#### Scenario: Běžný uživatel a nastavení
- **WHEN** uživatel bez příznaku admina pošle změnu nastavení Immiche
- **THEN** server vrátí 403 a nastavení se nezmění

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
