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

### Requirement: Rozhodnutí o poškozených v dialogu úklidu
Dialog „Uklidit…“ SHALL zobrazit sekci „Poškozené soubory“ jako
tabulku poškozených souborů kořene (malý náhled nebo zástupná ikona,
název, stav, důvod) se dvěma výlučnými sloupci „Vyřadit“ a „V pořádku“,
i když akce nemá žádné jiné nálezy; tlačítko „Uklidit…“ se SHALL
objevit i tehdy, má-li akce poškozený soubor bez rozhodnutí. Každý
sloupec SHALL mít v hlavičce hromadné zaškrtnutí všech řádků. Výchozí
stav řádku SHALL odpovídat uloženým metadatům (potvrzený = V pořádku,
jinak nic); soubor bez volby MUST zůstat beze změny. Volby se SHALL
zapsat až potvrzením dialogu, zrušení dialogu MUST nic nezměnit:
Vyřadit nastaví `vyradit` (zruší `overeno`) a soubor se přesune spolu
s ostatními operacemi plánu, V pořádku nastaví `overeno`, odškrtnutí
potvrzeného `overeno` zruší. Bez přesunů SHALL tlačítko jen uložit.
Soubor už označený k vyřazení SHALL být v tabulce šedě bez přepínačů,
s poznámkou, že označení se ruší na dlaždici. Ve vývojovém režimu
SHALL být sloupec Vyřadit vypnutý.

#### Scenario: Jedno okno pro konzistenci i poškozené
- **WHEN** akce má osiřelý sidecar i poškozenou fotku a uživatel
  otevře „Uklidit…“
- **THEN** dialog obsahuje plán přesunů i tabulku Poškozené soubory
  a fotka nemá žádnou volbu

#### Scenario: Výlučné volby
- **WHEN** uživatel u souboru zaškrtne Vyřadit a pak V pořádku
- **THEN** zůstane zaškrtnuté jen V pořádku

#### Scenario: Hromadné potvrzení
- **WHEN** uživatel zaškrtne V pořádku v hlavičce a potvrdí „Uložit“
- **THEN** všechny poškozené soubory bez označení k vyřazení mají
  `overeno`, nic se nepřesune a odznak akce je 0

#### Scenario: Vyřazení a zrušení potvrzení najednou
- **WHEN** soubor A je bez volby, soubor B potvrzený; uživatel u A
  zaškrtne Vyřadit, u B odškrtne V pořádku a spustí úklid
- **THEN** A se přesune do `k_odstraneni.ignored` i se sidecarem a B
  zůstane v kořeni bez `overeno`

#### Scenario: Zrušení dialogu
- **WHEN** uživatel zaškrtne volby a dialog zruší
- **THEN** metadata se nezmění
