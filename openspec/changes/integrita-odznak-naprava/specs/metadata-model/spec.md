# Spec Delta

## ADDED Requirements

### Requirement: Ruční potvrzení integrity
Záznam souboru v `_metadata.json` MAY obsahovat `"overeno": true` —
ruční potvrzení uživatele, že soubor je i přes výsledek kontroly
integrity v pořádku. Příznak je pouze úrovňě souboru, nedědí se
a nezapisuje se do sidecaru ani indexu. Pole bez hodnoty se u záznamu
MUST NOT ukládat (ruční zrušení příznak odstraní).

#### Scenario: Uložení potvrzení
- **WHEN** uživatel potvrdí „v pořádku“ u *podezřelého* souboru
  a uloži
- **THEN** `soubory.<název>.overeno` je `true`

#### Scenario: Žádný vliv na export
- **WHEN** se akce s potvrzeným souborem exportuje
- **THEN** sidecar souboru o potvrzení neobsahuje žádné pole
