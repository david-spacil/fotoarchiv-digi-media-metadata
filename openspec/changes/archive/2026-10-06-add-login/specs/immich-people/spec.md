## MODIFIED Requirements

### Requirement: Nastavení připojení
Aplikace SHALL nabídnout adminovi stránku nastavení s adresou serveru
Immich a API klíčem. Nastavení SHALL být uloženo v pracovním adresáři
s právy jen pro vlastníka, MUST NOT být zapsáno do archivu a klíč MUST
NOT být nikdy vrácen do prohlížeče (zobrazí se jen, že je nastaven,
a jeho poslední 4 znaky). Změna adresy MUST vyžadovat zadání klíče
znovu. Stránka SHALL umět připojení otestovat (včetně oprávnění číst
osoby a obličeje) a nastavení smazat. Uložení, test, smazání
i synchronizaci na požádání MUST server povolit jen adminovi.

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

#### Scenario: Běžný uživatel
- **WHEN** uživatel bez příznaku admina pošle uložení nastavení
- **THEN** server vrátí 403 a nastavení se nezmění
