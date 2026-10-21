# Spec Delta

## ADDED Requirements

### Requirement: Poškozené soubory ve zdroji
Poškozené soubory zdroje v `přetřídit`, které import nepřenese, MUST
zůstat ve zdroji a výsledek je SHALL uvést mezi tím, co ve zdroji
zůstalo. Smazání poškozeného souboru zdroje (podle `photo-import`) MUST
jít jen v produkčním režimu, jen pokud se soubor od kontroly nezměnil,
a MUST NOT probíhat, když zdroj drží zámek jiné relace.

#### Scenario: Poškozený soubor zůstane
- **WHEN** import složky `VZORNY` přesune všechna média kromě
  nečitelného `20151107_140851.jpg`
- **THEN** soubor zůstane v `přetřídit/VZORNY`, složka nezanikne
  a výsledek ho uvede jako poškozený

#### Scenario: Smazání ze zdroje
- **WHEN** uživatel v produkčním režimu potvrdí smazání nečitelného
  `20151107_140851.jpg` ze zdroje `VZORNY`
- **THEN** soubor zmizí z `přetřídit/VZORNY` a z přehledu importu

#### Scenario: Vývojový režim
- **WHEN** uživatel ve vývojovém režimu chce smazat poškozený soubor
  zdroje
- **THEN** průvodce smazání nenabídne a zdroj zůstane beze změny

### Requirement: Průběh kontroly zdroje
Kontrola zdroje v `přetřídit` SHALL ukazovat průběh podle přečtených
bajtů, i uvnitř velkých souborů. Tentýž průchod SHALL spočítat sha256
souborů a uložit ho do cache, aby plán soubory zdroje znovu nečetl.

#### Scenario: Plán po kontrole
- **WHEN** kontrola zdroje `VZORNY` doběhne a uživatel nechá ukázat
  plán
- **THEN** plán soubory zdroje znovu nečte
