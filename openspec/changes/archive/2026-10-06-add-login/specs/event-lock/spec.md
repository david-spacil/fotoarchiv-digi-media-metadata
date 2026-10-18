## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Vynucené uvolnění zámku
Admin SHALL moci uvolnit zámek akce, kterou drží jiná relace. Klient
dosavadního držitele SHALL při dalším heartbeatu přepnout akci jen ke
čtení s upozorněním, že zámek uvolnil admin; neuložené změny MUST
server po uvolnění odmítnout.

#### Scenario: Opuštěná rozdělaná práce
- **WHEN** admin uvolní zámek akce, kterou drží Modelová
- **THEN** admin může akci otevřít a Modelová vidí upozornění, že akci
  má jen ke čtení
