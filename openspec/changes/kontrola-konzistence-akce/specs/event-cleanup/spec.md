## ADDED Requirements

### Requirement: Ostatní soubory v kořeni
Plán úklidu SHALL nabídnout přesun nepodporovaných souborů a osiřelých
sidecarů z kořene akce (viz `event-consistency`) do `ostatni.ignored/`
v kořeni akce; průvodce nabídne přesun zapnutý. Složka vznikne, pokud
neexistuje, jinak se do ní soubory přidají. Platí pravidla kolizí.
Podsložka `ostatni.ignored` se jako ostatní `.ignored` při úklidu
přeskakuje.

#### Scenario: Zip v kořeni
- **WHEN** kořen akce obsahuje `prezentace.zip`
- **THEN** plán navrhne přesun do `ostatni.ignored/prezentace.zip`

#### Scenario: Osiřelý sidecar
- **WHEN** kořen obsahuje `P1503713.JPG.xmp` bez `P1503713.JPG`
- **THEN** plán navrhne přesun do `ostatni.ignored/P1503713.JPG.xmp`

#### Scenario: Kolize v ostatních
- **WHEN** `ostatni.ignored/zprava.pdf` už existuje a kořen obsahuje
  `zprava.pdf`
- **THEN** plán označí přesun `zprava.pdf` jako blokovaný kolizí

#### Scenario: Přesun vypnutý
- **WHEN** uživatel v průvodci přesun ostatních souborů vypne
- **THEN** plán `prezentace.zip` nepřesouvá

## MODIFIED Requirements

### Requirement: Úklid z pracovní plochy
Je-li v akci aspoň jeden soubor označený k vyřazení nebo nález kontroly
s nápravou (nepodporovaný soubor, osiřelý sidecar, RAW v kořeni,
podsložka; viz `event-consistency`), SHALL pracovní plocha nabídnout
úklid. Plán zahrne vyřazení, přesun ostatních souborů do
`ostatni.ignored`, přesun RAWů z kořene do `RAW.ignored` a u každé
podsložky volbu přesunout nebo ponechat bez výchozí hodnoty; podsložka
bez volby se nemění. Úklid v produkčním režimu po potvrzení plán
provede a ukáže výsledek podle požadavku Výsledek úklidu; ve vývojovém
režimu plán jen zobrazí. Provedení MUST vyžadovat zámek akce. Neuložené
změny `_metadata.json` SHALL být uloženy před sestavením plánu.

#### Scenario: Úklid z plochy
- **WHEN** uživatel na ploše se 3 označenými soubory spustí úklid
  a potvrdí plán
- **THEN** 3 soubory jsou ve `k_odstraneni.ignored` a výsledek ukáže
  3 provedené přesuny

#### Scenario: Ostatní soubory z plochy
- **WHEN** kořen akce obsahuje `zprava.pdf` a `P1503712.RW2`
  a uživatel na ploše spustí úklid a potvrdí plán
- **THEN** `zprava.pdf` je v `ostatni.ignored` a `P1503712.RW2`
  v `RAW.ignored`

#### Scenario: Podsložka bez volby
- **WHEN** kořen akce obsahuje podsložku `Video` a uživatel v úklidu
  z plochy u ní nic nezvolí
- **THEN** plán `Video` nepřesouvá ani nepřejmenovává
