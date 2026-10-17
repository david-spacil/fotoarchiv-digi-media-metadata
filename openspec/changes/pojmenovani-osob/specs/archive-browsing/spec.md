## MODIFIED Requirements

### Requirement: Stav akce
U každé akce SHALL seznam uvádět počet souborů v kořeni (bez
`Thumbs.db`, `_metadata.json` a sidecarů `.xmp`) a stav:
*nezpracováno* (bez `_metadata.json`), *rozpracováno*
(`_metadata.json` existuje, akce není dokončená) nebo *hotovo*.
U akce *hotovo* s neexportovanými změnami SHALL seznam uvést „změněno
po exportu“. U akce *hotovo*, jejímž souborům v kořeni (kromě
označených k vyřazení) po zdědění chybí autoři, datum nebo místo, nebo
která má podle posledního zjištění osob akce nepojmenované osoby, SHALL
seznam uvést štítek „nekompletní“.

#### Scenario: Akce bez metadat
- **WHEN** složka akce nemá `_metadata.json`
- **THEN** seznam ji ukáže jako *nezpracováno*

#### Scenario: Akce s metadaty
- **WHEN** k akci existuje `_metadata.json` a akce není označená jako
  dokončená
- **THEN** seznam ji ukáže jako *rozpracováno*

#### Scenario: Exportovaná akce
- **WHEN** kořen akce obsahuje 50 fotek a 50 sidecarů `.xmp`
- **THEN** seznam u akce uvádí 50 souborů

#### Scenario: Dokončená akce upravená po exportu
- **WHEN** dokončená akce má neexportované změny
- **THEN** seznam ji ukáže jako *hotovo* s poznámkou „změněno po
  exportu“

#### Scenario: Dokončená nekompletní akce
- **WHEN** dokončené akci 3 soubory nemají místo
- **THEN** seznam ji ukáže jako *hotovo* se štítkem „nekompletní“

#### Scenario: Dokončená akce s nepojmenovanými osobami
- **WHEN** dokončená akce má všechna pole vyplněná, ale 2 nepojmenované
  osoby
- **THEN** seznam ji ukáže jako *hotovo* se štítkem „nekompletní“

#### Scenario: Skryté osoby
- **WHEN** dokončená akce má všechna pole vyplněná a jediná
  nepojmenovaná osoba je v Immichi skrytá
- **THEN** seznam štítek „nekompletní“ neukáže

### Requirement: Hotovost akce
Seznam SHALL u akce s `_metadata.json` uvádět hotovost po polích
autoři, datum a místo: počet souborů v kořeni (bez označených
k vyřazení), které mají pole po zdědění vyplněné, z jejich celkového
počtu. Pravidla dědění MUST být stejná jako u chybějících údajů na
ploše. Má-li akce zjištěné osoby (viz `immich-people`), SHALL hotovost
uvádět i osoby: pojmenované ze všech neskrytých. Při nepojmenovaných
osobách SHALL karta archiváři a adminovi nabídnout nástroj pojmenování
osob. U akce *hotovo* SHALL hotovost uvádět i stav exportu (aktuální,
nebo „změněno po exportu“). Akce *nezpracováno* hotovost nemá; karta
SHALL místo ní nabídnout zahájení zpracování (odkaz na plochu, která
spustí průvodce). Výpočet MUST NOT číst soubory archivu kromě
`_metadata.json` a výpisu složky ani se ptát Immiche.

#### Scenario: Rozpracovaná akce s mezerami
- **WHEN** akce má 40 souborů, 2 označené k vyřazení, všem autory
  dědí ze skupin, 30 má datum a 10 místo
- **THEN** karta uvádí autoři 38/38, datum 30/38, místo 10/38

#### Scenario: Místo zděděné z akce
- **WHEN** akce má jediné místo akce a 20 souborů bez vlastního místa
- **THEN** karta uvádí místo 20/20

#### Scenario: Nezpracovaná akce
- **WHEN** akce nemá `_metadata.json`
- **THEN** karta hotovost neuvádí a nabízí zahájení zpracování

#### Scenario: Osoby akce
- **WHEN** u akce je uloženo 4 pojmenované z 6 osob a kartu vidí
  archivář
- **THEN** karta uvádí osoby 4/6 a odkaz na nástroj pojmenování osob

#### Scenario: Akce bez zjištěných osob
- **WHEN** akce nemá album v Immichi
- **THEN** karta osoby neuvádí a do hotovosti je nepočítá
