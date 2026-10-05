## Purpose

Omezit přístup ke sdílenému serveru na přihlášené uživatele a dát zámku
akce ověřenou identitu místo jména zadaného v prohlížeči.

## ADDED Requirements

### Requirement: Povinné přihlášení
V produkčním režimu MUST server odmítnout každý požadavek na stránky
i API bez platného přihlášení; stránky přesměruje na přihlášení, API
vrátí 401.

#### Scenario: Nepřihlášený požadavek na API
- **WHEN** klient bez přihlášení pošle uložení metadat
- **THEN** server vrátí 401 a archiv zůstane beze změny

### Requirement: Identita u zámku
Jméno držitele zámku SHALL server brát z přihlášení, ne z požadavku
klienta. Identita SHALL být převedena na kanonické jméno
`Příjmení, Jméno`.

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
