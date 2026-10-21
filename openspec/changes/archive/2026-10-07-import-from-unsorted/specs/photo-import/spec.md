## MODIFIED Requirements

### Requirement: Výběr a nahrání souborů
Průvodce SHALL přijmout jednotlivé soubory i celou složku (přetažením
i výběrem), nebo jako zdroj složku v `přetřídit` (viz
`unsorted-import`). Soubory z podsložek vybrané složky SHALL zpracovat,
jako by ležely v jedné úrovni. Nahrané soubory MUST server uložit do
pracovního adresáře mimo archiv a do archivu MUST NOT zapisovat dřív,
než uživatel import potvrdí. Průvodce SHALL ukazovat průběh nahrávání.

#### Scenario: Přerušené nahrávání
- **WHEN** uživatel během nahrávání zavře stránku
- **THEN** archiv zůstane beze změny

#### Scenario: Složka s podsložkou
- **WHEN** uživatel vybere složku s `a.jpg` a `Video/b.mp4`
- **THEN** přehled obsahuje `a.jpg` i `b.mp4`

#### Scenario: Zdroj místo nahrání
- **WHEN** uživatel v kroku Soubory zvolí ze složky `přetřídit` složku
  `VZORNY`
- **THEN** průvodce nic nenahrává a přejde na přehled souborů
  `VZORNY`

### Requirement: Výsledek importu
Po provedení SHALL průvodce ukázat přenesené, blokované, duplicitní
a selhané soubory (s chybou). Selhání jednoho souboru MUST NOT zastavit
ostatní. Úspěšně přenesené soubory MUST server z pracovního adresáře
odstranit; nepřenesené SHALL zůstat, dokud uživatel import nezahodí.
U importu ze zdroje v `přetřídit` SHALL výsledek uvést, co ve zdroji
zůstalo a zda zdrojová složka zanikla; import, ve kterém nezůstal žádný
přenositelný soubor, SHALL server zrušit. Průvodce SHALL nabídnout
otevřít cílovou akci.

#### Scenario: Otevření akce po importu
- **WHEN** import do stávající akce s `_metadata.json` skončí
- **THEN** po otevření akce jsou přenesené soubory mezi novými soubory
  akce

#### Scenario: Zbytky zdroje ve výsledku
- **WHEN** import ze složky `DOD 2016` přesune všechna média a zbyde
  jeden `.docx`
- **THEN** výsledek uvede, že ve zdroji zůstal jeden soubor a složka
  `DOD 2016` zůstala

### Requirement: Zahození importu
Uživatel SHALL moci rozpracovaný import zahodit; server MUST pak
smazat jeho soubory z pracovního adresáře. U importu ze zdroje
v `přetřídit` MUST zahození zdroj ponechat beze změny. Importy
neaktivní déle než 7 dní SHALL server smazat při startu.

#### Scenario: Zahození před potvrzením
- **WHEN** uživatel po nahrání import zahodí
- **THEN** pracovní adresář importu je smazaný a archiv beze změny

#### Scenario: Zahození importu ze zdroje
- **WHEN** uživatel zahodí import ze složky `FotoKoule`
- **THEN** složka `přetřídit/FotoKoule` zůstane beze změny
