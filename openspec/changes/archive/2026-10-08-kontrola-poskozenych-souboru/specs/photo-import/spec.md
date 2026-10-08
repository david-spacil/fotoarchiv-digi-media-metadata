# Spec Delta

## ADDED Requirements

### Requirement: Kontrola souborů v přehledu
Po zobrazení přehledu SHALL průvodce spustit kontrolu podporovaných
souborů importu (podle `file-integrity`) a ukazovat její průběh po
souborech. Přehled SHALL uvést počet podezřelých a nečitelných souborů
a u každého důvod. Pokračovat na plán SHALL jít až po dokončení
kontroly.

#### Scenario: Import s poškozenou fotkou
- **WHEN** uživatel nahraje 40 JPG, mezi nimi `20151107_140851.jpg`
  s nulami na začátku
- **THEN** přehled po kontrole uvede jeden nečitelný soubor s důvodem
  a 39 v pořádku

#### Scenario: Návrat k importu
- **WHEN** uživatel se k rozpracovanému importu vrátí beze změny
  souborů
- **THEN** přehled ukáže výsledky kontroly hned bez nového čtení

### Requirement: Volba u podezřelých souborů
Nečitelný soubor MUST NOT import přenést. Podezřelý soubor MUST NOT
import přenést, pokud ho uživatel v přehledu výslovně nepovolí. Volbu
SHALL server uložit k importu a průvodce ji po návratu předvyplní.

#### Scenario: Výchozí stav
- **WHEN** přehled uvede `20151107_135155.jpg` jako podezřelý
  a uživatel nic nezmění
- **THEN** plán soubor nepřenese

#### Scenario: Povolení
- **WHEN** uživatel u `20151107_135155.jpg` zvolí „přesto importovat“
- **THEN** plán soubor přenese jako ostatní média

### Requirement: Smazání poškozeného souboru importu
U podezřelého i nečitelného souboru SHALL průvodce nabídnout smazání,
které MUST uživatel potvrdit v dialogu se jménem souboru a důvodem.
Nahraný soubor MUST server smazat z pracovního adresáře importu. Smazat
MUST jít jen soubor, který kontrola označila jako poškozený, a jen
dokud se od kontroly nezměnil. Smazání během provedení importu MUST
server odmítnout.

#### Scenario: Smazání nahraného souboru
- **WHEN** uživatel u nečitelného nahraného `20151107_140851.jpg`
  potvrdí smazání
- **THEN** soubor zmizí z pracovního adresáře i z přehledu a archiv se
  nezmění

#### Scenario: Zdravý soubor nejde smazat
- **WHEN** klient pošle požadavek na smazání souboru, který kontrola
  označila jako v pořádku
- **THEN** server požadavek odmítne a soubor zůstane

### Requirement: Poškozené soubory v plánu a výsledku
Plán SHALL server sestavit s výsledky kontroly; soubor, který se od
kontroly změnil, MUST zkontrolovat znovu. Plán i výsledek SHALL uvést
nepřenesené poškozené soubory jako samostatnou skupinu s důvodem.
Nepřenesené poškozené soubory MUST zůstat v pracovním adresáři, dokud
uživatel import nezahodí nebo je nesmaže.

#### Scenario: Výsledek s poškozeným souborem
- **WHEN** import 40 JPG s jedním nečitelným skončí
- **THEN** výsledek uvede 39 přenesených a jeden poškozený nepřenesený
  soubor s důvodem

### Requirement: Ověření velikosti po přenosu
Po přenosu každého souboru SHALL server porovnat velikost souboru
v cíli s velikostí originálu. Nesoulad MUST výsledek uvést u souboru
jako chybu přenosu; soubor v archivu MUST NOT server smazat.

#### Scenario: Nesouhlasná velikost
- **WHEN** soubor má po přenosu v cíli jinou velikost než originál
- **THEN** výsledek ho uvede s chybou „velikost v cíli nesouhlasí“
  a soubor zůstane v archivu
