# event-lock Specification

## Purpose

Zabránit tomu, aby dva lidé současně upravovali stejnou akci na sdíleném
serveru, a přitom nenechat akci zamčenou po zavřeném prohlížeči.

## Requirements

### Requirement: Získání zámku
Při otevření akce SHALL klient požádat o zámek akce. Zámek SHALL nést
jméno uživatele, identifikátor relace prohlížeče a čas získání. Je-li
akce volná, server zámek přidělí. Jedna relace MUST držet nejvýš jeden
zámek; otevření jiné akce zámek předchozí akce uvolní.

#### Scenario: Volná akce
- **WHEN** uživatel otevře akci, kterou nikdo nedrží
- **THEN** dostane zámek a akci může upravovat

#### Scenario: Přechod na jinou akci
- **WHEN** držitel zámku akce A otevře akci B
- **THEN** zámek akce A se uvolní

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

### Requirement: Heartbeat a uvolnění
Klient SHALL zámek obnovovat zhruba každou minutu, dokud je akce
otevřená. Při zavření akce nebo stránky SHALL zámek uvolnit. Zámek bez
heartbeatu déle než 5 minut je opuštěný: server ho MUST považovat za
volný a přidělit dalšímu žadateli.

#### Scenario: Zavřený prohlížeč
- **WHEN** držitel zavře prohlížeč bez uvolnění a uplyne 5 minut
- **THEN** další uživatel při otevření akce zámek dostane

#### Scenario: Ztracený zámek
- **WHEN** heartbeat relace dorazí poté, co zámek získal někdo jiný
- **THEN** server ho odmítne a klient přepne akci jen ke čtení
  s upozorněním

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

### Requirement: Jméno uživatele
Jméno držitele zámku SHALL server brát z přihlášení. Jen ve vývojovém
režimu bez přihlášení SHALL klient před prvním otevřením akce vyžádat
jméno uživatele v kanonickém tvaru `Příjmení, Jméno` s návrhy ze
známých jmen a pamatovat si ho v prohlížeči.

#### Scenario: Přihlášený uživatel
- **WHEN** přihlášený uživatel otevře akci
- **THEN** aplikace se na jméno neptá a zámek nese jeho kanonické jméno

#### Scenario: První návštěva
- **WHEN** ve vývojovém režimu bez přihlášení uživatel bez uloženého
  jména otevře akci
- **THEN** aplikace se zeptá na jméno a teprve pak požádá o zámek

### Requirement: Vynucené uvolnění zámku
Admin SHALL moci uvolnit zámek akce, kterou drží jiná relace. Klient
dosavadního držitele SHALL při dalším heartbeatu přepnout akci jen ke
čtení s upozorněním, že zámek uvolnil admin; neuložené změny MUST
server po uvolnění odmítnout.

#### Scenario: Opuštěná rozdělaná práce
- **WHEN** admin uvolní zámek akce, kterou drží Modelová
- **THEN** admin může akci otevřít a Modelová vidí upozornění, že akci
  má jen ke čtení
