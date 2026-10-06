## MODIFIED Requirements

### Requirement: Dotaz na geokódovací službu
Server SHALL hledat název místa ve veřejném Nominatimu (OpenStreetMap)
a vrátit kandidáty s názvem, popisem (hierarchie správních celků)
a souřadnicemi. Dotaz MUST nést User-Agent s názvem aplikace
a kontaktem provozovatele; kontakt je jeden pro celý server (ne po
uživatelích), nastavuje ho admin v nastavení aplikace a ukládá se
v pracovním adresáři mimo archiv. Bez kontaktu je geokódování vypnuté.
Změna kontaktu SHALL platit bez restartu serveru. Server MUST posílat
nejvýš jeden dotaz za sekundu a MUST NOT se ptát během psaní, jen na
potvrzený název.

#### Scenario: Nejednoznačný název
- **WHEN** se hledá `Vysočany`
- **THEN** výsledek obsahuje kandidáty z okresů Blansko, Znojmo
  i Prahy 9

#### Scenario: Služba nedostupná
- **WHEN** Nominatim neodpoví
- **THEN** aplikace ukáže chybu s možností zkusit znovu a práce
  s ostatními poli pokračuje

#### Scenario: Nastavení kontaktu
- **WHEN** admin uloží kontakt `archiv@example.cz` a jiný uživatel
  pak hledá místo
- **THEN** dotaz na Nominatim nese v User-Agent `archiv@example.cz`
  bez ohledu na to, kdo hledá

#### Scenario: Bez kontaktu
- **WHEN** kontakt není nastaven
- **THEN** volba místa nabídne jen ruční souřadnice a „bez souřadnic“
