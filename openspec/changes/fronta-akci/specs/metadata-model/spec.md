## ADDED Requirements

### Requirement: Záznam o úpravách
`_metadata.json` SHALL obsahovat na nejvyšší úrovni pole `upravili`:
objekt jméno uživatele → datum a čas jeho posledního uložení akce
(ISO 8601, místní čas serveru, na sekundy). Pole SHALL zapisovat jen
server při každém úspěšném uložení metadat a při dokončení akce,
a to jménem z přihlášené relace (stejné jako u zámku), nikdy
z požadavku. Hodnotu, kterou pošle klient, server MUST ignorovat
a vzít `upravili` z uložené verze. Dokument bez `upravili` (starší
akce) MUST zůstat platný; pole vznikne prvním uložením. `upravili`
se MUST NOT exportovat do sidecarů ani indexu a nedědí se.

#### Scenario: První uložení
- **WHEN** uživatel Spáčil, David 2026-10-14 v 10:15:02 poprvé uloží
  akci bez `upravili`
- **THEN** `_metadata.json` obsahuje
  `"upravili": {"Spáčil, David": "2026-10-14T10:15:02"}`

#### Scenario: Druhý uživatel
- **WHEN** akci pak uloží uživatel Kopáčová, Zuzana
- **THEN** `upravili` obsahuje obě jména, každé s časem svého
  posledního uložení

#### Scenario: Podvržená hodnota
- **WHEN** klient pošle v metadatech `upravili` s jiným jménem
- **THEN** server ji zahodí a uloží jen záznam přihlášeného uživatele
  k uložené verzi

#### Scenario: Sidecar
- **WHEN** se akce s `upravili` exportuje
- **THEN** žádný sidecar ani index jména z `upravili` neobsahuje
