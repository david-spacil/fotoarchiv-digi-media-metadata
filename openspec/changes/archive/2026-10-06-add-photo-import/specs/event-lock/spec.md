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

### Requirement: Obsazená akce
Drží-li akci jiná relace, server zámek nepřidělí a vrátí jméno držitele
a čas posledního heartbeatu. Klient SHALL akci otevřít jen ke čtení
s upozorněním, kdo ji upravuje. Je-li držitelem stejné jméno (jiná
záložka téhož uživatele), upozornění SHALL radit zavřít původní
záložku. Zámek nové akce, který server vzal pro provedení importu,
MUST server uvolnit, když se provedení přeruší dřív, než klient dostal
výsledek.

#### Scenario: Druhý uživatel
- **WHEN** Modelová otevře akci, kterou drží Příkladný
- **THEN** vidí akci jen ke čtení a upozornění „Akci upravuje Příkladný,
  Daniel“

#### Scenario: Vlastní jiná záložka
- **WHEN** Příkladný otevře akci, kterou drží jeho jiná záložka
- **THEN** vidí upozornění „Akci máte otevřenou v jiné záložce. Pokud
  chcete pokračovat v práci zde, zavřete původní záložku.“

#### Scenario: Přerušený import do nové akce
- **WHEN** uživatel během provedení importu do nové akce zavře stránku
- **THEN** akce není zamčená a jde hned otevřít
