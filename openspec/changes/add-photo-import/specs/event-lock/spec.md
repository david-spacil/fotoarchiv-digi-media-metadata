## MODIFIED Requirements

### Requirement: Zápis jen s zámkem
Uložení `_metadata.json`, provedení úklidu a provedení importu do
stávající akce MUST server odmítnout, pokud žádající relace nedrží
zámek akce. Kontrola verze dokumentu při uložení SHALL platit i pro
držitele zámku.

#### Scenario: Uložení bez zámku
- **WHEN** relace bez zámku pošle uložení metadat
- **THEN** server uložení odmítne a archiv zůstane beze změny

#### Scenario: Import do akce, kterou upravuje jiný
- **WHEN** uživatel potvrdí import do akce, jejíž zámek drží jiná
  relace
- **THEN** server import odmítne, průvodce ukáže, kdo akci upravuje,
  a nahrané soubory zůstanou v pracovním adresáři
