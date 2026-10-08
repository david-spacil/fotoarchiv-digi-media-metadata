# Spec Delta

## ADDED Requirements

### Requirement: Odznak poškozených souborů
Seznam akcí SHALL u akce s nenulovým souhrnem poškozených (viz
`file-integrity`) zobrazit odznak „N poškozených“. Plocha akce SHALL
tentýž souhrn zobrazovat v liště. Odznak MUST být čistě informační —
nezabraňuje prohlížení ani ukládání.

#### Scenario: Odznak v seznamu
- **WHEN** akce má 2 poškozené soubory v souhrnu
- **THEN** řádek akce v seznamu má odznak „2 poškozené“

#### Scenario: Žádný výsledek
- **WHEN** akce nemá žádnou cache kontroly nebo je souhrn nulový
- **THEN** seznam ani plocha akce odznak nezobrazují

### Requirement: Označení dlaždice poškozeného souboru
Pracovní plocha akce SHALL dlaždici souboru, jehož výsledek kontroly
je *podezřelý* nebo *nečitelný* a který nemá `overeno` ani `vyradit`,
vizuálně odlišit a v tooltipu uvést stav a důvod kontroly. Dlaždice
potvrzeného (`overeno`) nebo vyřazeného (`vyradit`) souboru se odlišovat
MUST NOT, s výjimkou stávajícího označení vyřazení.

#### Scenario: Nula na dlaždici
- **WHEN** plocha zobrazuje nečitelnou fotku
- **THEN** dlaždice je odlišená a tooltip uvádí *nečitelný* s důvodem

#### Scenario: Po přehodnocení
- **WHEN** uživatel u fotky potvrdí „v pořádku“ a uloží
- **THEN** dlaždice je běžná a souhrn akce fotku nepočítá

### Requirement: Potvrzení „v pořádku“
Plocha akce SHALL u dlaždice s poškozeným souborem nabídnout akci
„Považovat za v pořádku“. Potvrzení se uloží do záznamu souboru
jako `overeno` (viz `metadata-model`) a projeví se v odznaku,
souhrnu i dlaždici po uložení. Zrušení potvrzení MUST být možné
stejnou akcí.

#### Scenario: Falešná pozitivita
- **WHEN** *podezřelá* fotka je podle uživatele v pořádku a uživatel
  potvrdí „Považovat za v pořádku“
- **THEN** odznak akce fotku nadále nepočítá a po opětovném kliknutí
  ji počítá znovu

### Requirement: Vyřazení poškozených v dialogu úklidu
Dialog „Uklidit…“ SHALL zobrazit sekci „Poškozené soubory“ se
seznamem poškozených souborů kořene (název, stav, důvod), i když
akce nemá žádné jiné nálezy; tlačítko „Uklidit…“ se SHALL objevit
i v tom případě. Zaškrtnutí souboru SHALL označit `vyradit` a uložit
(jako při označení z dlaždice) a plán se SHALL přepočítat tak, aby
přesun souboru obsahoval. Soubory s `overeno` nebo už označené
SHALL být v seznamu šedě, bez přepínače, s poznámkou. Potvrzení
„v pořádku“ dialog nabízet MUST NOT (zůstává na dlaždici).

#### Scenario: Jedno okno pro konzistenci i poškozené
- **WHEN** akce má osiřelý sidecar i poškozenou fotku a uživatel
  otevře „Uklidit…“
- **THEN** dialog obsahuje plán přesunů pro oba nálezy a fotku
  předzapnutou v sekci Poškozené soubory

#### Scenario: Bez ostatních nálezů
- **WHEN** akce má jen poškozené soubory
- **THEN** „Uklidit…“ se zobrazí, sekce Poškozené soubory je jediná
  a po zaškrtnutí a spuštění se soubory přesunou do
  `k_odstraneni.ignored` a zmizí z odznaku

#### Scenario: Potvrzený soubor v seznamu
- **WHEN** je jeden poškozený soubor potvrzený „v pořádku“
- **THEN** dialog ho zobrazí šedě s poznámkou bez přepínače
