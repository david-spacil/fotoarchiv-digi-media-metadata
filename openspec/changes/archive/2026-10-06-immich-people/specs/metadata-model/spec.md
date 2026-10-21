## MODIFIED Requirements

### Requirement: Dědění hodnot
Výsledná hodnota pole pro soubor SHALL být hodnota zadaná u souboru,
jinak u jeho skupiny, jinak u akce. Každé pole akce i skupiny MUST jít
přepsat na nižší úrovni, včetně `autori`. Do `_metadata.json` se SHALL
ukládat jen hodnoty zadané na dané úrovni, ne zděděné.

Výjimky, které se nedědí: `ucastnici` akce (výčet lidí na akci, ne
osoby na každé fotce), `mista` akce (výčet míst akce; skupina a soubor
mají jedno `misto`), `nazev` skupiny (čitelný název skupiny, ne
název akce) a u souboru `skupina`, `sha256` a `obliceje`. Název akce
proto nejde přepsat na úrovni skupiny, jen u souboru.

`obliceje` SHALL existovat jen u souboru a zapisuje je jen
synchronizace z Immiche. Osoby na fotce jsou jména z `obliceje`. Pole
`osoby` na kterékoli úrovni MUST být ignorováno a při uložení
odstraněno, stejně jako `obliceje` u akce nebo skupiny.

#### Scenario: Autor přepsaný u fotky
- **WHEN** skupina má `autori` = [`Příkladný, Daniel`, `Modelová, Zuzana`]
  a jeden soubor má `autori` = [`Modelová, Zuzana`]
- **THEN** výslední autoři toho souboru jsou jen `Modelová, Zuzana`
  a ostatních souborů skupiny oba

#### Scenario: Zrušení přepsání
- **WHEN** uživatel u souboru přepsání pole zruší
- **THEN** pole zmizí ze záznamu souboru a hodnota se znovu dědí

#### Scenario: Účastníci akce
- **WHEN** akce má `ucastnici` = [`Příkladný, Daniel`, `Modelová, Zuzana`]
  a soubor nemá `obliceje`
- **THEN** soubor nemá žádné osoby

#### Scenario: Starší pole osoby
- **WHEN** starší `_metadata.json` má `osoby` u skupiny i u souboru
  a uživatel akci uloží
- **THEN** soubory osoby z `osoby` nemají a pole `osoby` po uložení
  v `_metadata.json` není

#### Scenario: Název skupiny
- **WHEN** akce má `nazev` = `kontrola Naučné stezky` a skupina `nazev`
  = `Panasonic DC-G9`
- **THEN** výsledný `nazev` souborů skupiny je `kontrola Naučné stezky`
