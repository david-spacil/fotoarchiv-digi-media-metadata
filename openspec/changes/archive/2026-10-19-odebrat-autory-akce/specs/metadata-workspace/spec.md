## MODIFIED Requirements

### Requirement: Skupiny z importu v průvodci
Existuje-li k akci bez `_metadata.json` návrh skupin z importu, SHALL
průvodce prvním otevřením v kroku skupiny a autoři použít jeho skupiny
(i s autory) a přiřazení pro soubory, které návrh uvádí a jsou
v kořeni akce. Autory celé akce ze staršího návrhu MUST NOT převzít.
Ostatní soubory SHALL dostat automatický návrh podle přístroje a vzoru
názvu. Po prvním uložení `_metadata.json` SHALL server návrh smazat.
Chybí-li návrh (např. smazaný pracovní adresář), průvodce SHALL
postupovat jako dosud.

#### Scenario: Podsložky z importu jako skupiny
- **WHEN** uživatel otevře existující akci bez `_metadata.json`, do
  které importoval `DOD 2015` s rozdělením „podle podsložek“ a autory
  skupin
- **THEN** krok skupiny a autoři ukáže skupiny `DOD 2015_Bara Pokusna`,
  `DOD 2015_Lenka`, `DOD 2015_Olga` a `DOD 2015_Mira` s autory
  zadanými při importu

#### Scenario: Soubor mimo návrh
- **WHEN** v kořeni akce je kromě importovaných souborů i soubor, který
  návrh neuvádí
- **THEN** ten soubor dostane automaticky navrženou skupinu

#### Scenario: Návrh po uložení
- **WHEN** uživatel v průvodci poprvé uloží `_metadata.json`
- **THEN** návrh skupin z importu přestane existovat a další otevření
  ho nepoužije

#### Scenario: Starší návrh s autory akce
- **WHEN** návrh skupin z dřívějšího importu obsahuje autory celé akce
  `Příkladný, Daniel` a uživatel akci poprvé uloží
- **THEN** `_metadata.json` nemá `akce.autori`

## REMOVED Requirements

### Requirement: Autoři akce v průvodci
**Reason**: Autoři celé akce jsou ze schématu `/2` vypuštěni (issue
#43); fotky akce pocházejí obvykle od víc lidí a pole přepisovalo
autory dědících skupin.
**Migration**: Autory zadat u skupin (krok skupiny a autoři) nebo
u souborů na ploše; existující `akce.autori` převod na `/2` zahodí
(viz `metadata-model`, Příkaz migrovat).
