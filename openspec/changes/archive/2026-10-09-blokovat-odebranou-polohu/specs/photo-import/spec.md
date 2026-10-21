## ADDED Requirements

### Requirement: Fotky s odebranou polohou
Fotka má **odebranou polohu**, když její EXIF obsahuje blok GPS
s `GPSVersionID` rovným `0 0 0 0` a bez číselné zeměpisné šířky
i délky. Import MUST NOT takovou fotku přenést, a to ani u importu
nahráním, ani ze složky `přetřídit`; uživatel ji MUST NOT moci povolit.
Přehled SHALL fotky s odebranou polohou vypsat s důvodem („telefon
odebral polohu“) a vysvětlením, že originál je potřeba předat jinou
cestou. Plán i výsledek SHALL je uvést jako samostatnou skupinu
nepřenesených. Nepřenesené MUST zůstat v pracovním adresáři, nebo ve
zdroji v `přetřídit`, dokud uživatel import nezahodí. Fotka bez bloku
GPS a fotka s číselnými souřadnicemi MUST se importovat jako dosud.

#### Scenario: Fotka z telefonu přes prohlížeč
- **WHEN** uživatel nahraje `PXL_20260917_132338497.MP.jpg`
  s `GPSVersionID` `0 0 0 0` a prázdnými souřadnicemi
- **THEN** přehled ji uvede jako fotku s odebranou polohou, plán ji
  nepřenese a výsledek ji uvede mezi nepřenesenými s důvodem

#### Scenario: WhatsApp bez polohy
- **WHEN** uživatel nahraje `IMG-20260428-WA0003.jpg` bez bloku GPS
- **THEN** přehled ji jako odebranou polohu neuvede a import ji přenese

#### Scenario: Fotka s polohou
- **WHEN** uživatel nahraje fotku s `GPSVersionID` `2 2 0 0`
  a souřadnicemi 49.13579 N, 16.24680 E
- **THEN** import ji přenese

#### Scenario: Smíšený import
- **WHEN** import obsahuje 30 fotek s polohou a 2 s odebranou polohou
- **THEN** plán přenese 30 fotek a 2 uvede jako nepřenesené s důvodem
  a tlačítko provedení je dostupné
