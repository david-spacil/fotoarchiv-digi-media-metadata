# Spec Delta

## Purpose

Poznat poškozené soubory médií (vynulované bloky, useknutý obsah,
nečitelná hlavička) dřív, než se dostanou do archivu, a najít ty, které
už v archivu jsou, bez zásahu do originálů.

## ADDED Requirements

### Requirement: Kontrola souboru
Aplikace SHALL umět zkontrolovat soubor média a zařadit ho jako
*v pořádku*, *podezřelý* nebo *nečitelný*, vždy s důvodem. Kontrola MUST
soubor jen číst. Souvislý úsek nul aspoň 64 KiB začínající na násobku
4 KiB MUST soubor zařadit nejméně jako podezřelý, u fotek, RAWů
a u videí podle požadavku Nuly ve videu.

#### Scenario: Nuly na začátku
- **WHEN** se kontroluje `20151107_140851.jpg`, jehož prvních 768 KiB
  jsou nuly
- **THEN** výsledek je *nečitelný* s důvodem, že soubor nejde otevřít
  a obsahuje 768 KiB nul od začátku

#### Scenario: Šedý pruh
- **WHEN** se kontroluje `20151107_135155.jpg`, jehož posledních
  119 KiB jsou nuly a obraz se otevře se šedým pruhem dole
- **THEN** výsledek je *podezřelý* s důvodem, že soubor obsahuje
  119 KiB nul na konci

#### Scenario: Nuly uprostřed, které dekodér přijme
- **WHEN** fotka má uprostřed úsek 64 KiB nul na hranici 4 KiB a jde
  dekódovat bez chyby
- **THEN** výsledek je *podezřelý*

#### Scenario: Zdravá fotka s plochou barvou
- **WHEN** fotka obsahuje souvislý úsek 24 KB nul
- **THEN** výsledek je *v pořádku*

### Requirement: Kontrola podle typu souboru
Fotku (jpg, jpeg, png) SHALL kontrola dekódovat. Soubor, který nejde
rozpoznat jako obrázek, MUST být *nečitelný*; obrázek useknutý nebo
s chybou při dekódování MUST být nejméně *podezřelý*. Video SHALL
kontrola ověřit nástrojem `ffprobe`: bez čitelného video proudu MUST
být *nečitelné*. RAW SHALL kontrola posoudit jen testem nul. Prázdný soubor (0 B) MUST být *nečitelný*.

#### Scenario: Useknutá fotka
- **WHEN** fotka končí uprostřed obrazových dat
- **THEN** výsledek je *podezřelý* s důvodem, že obraz je neúplný

#### Scenario: Video bez indexu
- **WHEN** video `MOV_0012.mp4` po přerušeném nahrávání nemá čitelný
  video proud
- **THEN** výsledek je *nečitelný*

#### Scenario: Bez ffprobe
- **WHEN** na serveru chybí `ffprobe` a kontroluje se video bez úseků
  nul
- **THEN** výsledek je *v pořádku* s poznámkou, že video se ověřilo
  jen testem nul

### Requirement: Nuly ve videu
U videa MP4/MOV SHALL kontrola počítat úseky nul jen v datech obrazové
stopy podle tabulek vzorků souboru; úsek přes obrazová i jiná data
SHALL počítat součtem částí v obrazových datech. Nuly mimo ně
(výplňové a metadatové atomy, zvuk) MUST NOT soubor zařadit jako
podezřelý. Když tabulky vzorků nejdou přečíst nebo neleží v datech
souboru, MUST kontrola počítat úseky nul v celém souboru.

#### Scenario: Ticho v nekomprimovaném zvuku
- **WHEN** video `P1503720.MP4` (Panasonic, zvuk PCM) obsahuje v tichu
  souvislý úsek 184 KiB nul ve zvukových datech a obrazová data jsou
  bez nul
- **THEN** výsledek je *v pořádku*

#### Scenario: Výplň formátu
- **WHEN** video `VID_20260525_021039_381.mp4` má 384 KiB nul v atomu
  `free` před obrazovými daty
- **THEN** výsledek je *v pořádku*

#### Scenario: Nuly v obrazových datech
- **WHEN** v obrazových datech videa je vynulovaných 64 KiB na hranici
  4 KiB
- **THEN** výsledek je *podezřelý* s důvodem „64 KiB nul v obrazových
  datech“ a polohou

#### Scenario: Hlavička nejde přečíst
- **WHEN** video nemá čitelné tabulky vzorků (fragmentované MP4,
  poškozená hlavička)
- **THEN** úseky nul se počítají v celém souboru

### Requirement: Cache kontroly
Výsledek kontroly SHALL aplikace cachovat v pracovním adresáři podle
cesty, velikosti a času změny souboru. Nezměněný soubor MUST NOT být
při opakované kontrole znovu čten. Do archivu MUST NOT cache zapisovat.

#### Scenario: Opakovaná kontrola
- **WHEN** se tatáž nezměněná složka kontroluje podruhé
- **THEN** výsledky jsou hned k dispozici bez čtení souborů

#### Scenario: Změněný soubor
- **WHEN** se soubor po kontrole změní (velikost nebo čas změny)
- **THEN** další kontrola ho přečte znovu

#### Scenario: Změna pravidel kontroly
- **WHEN** nová verze aplikace změní pravidla kontroly
- **THEN** výsledky v cache z dřívější verze neplatí a soubory se
  zkontrolují znovu

### Requirement: Kontrola akcí z příkazové řádky
Příkaz `python -m fotoarchiv zkontrolovat` SHALL zkontrolovat zadanou
akci, nebo bez ní všechny akce archivu: média v kořeni a soubory
v `RAW.ignored/`; ostatní podsložky MUST přeskočit. V obou režimech MUST
archiv jen číst. SHALL vypsat podezřelé a nečitelné soubory s důvodem,
souhrn po akcích a uložit report do pracovního adresáře.

#### Scenario: Kontrola jedné akce
- **WHEN** správce spustí `zkontrolovat "2026-04-28 kontrola Stezky"`
- **THEN** příkaz vypíše poškozené soubory té akce s důvodem a počty
  v pořádku, podezřelých a nečitelných

#### Scenario: Celý archiv
- **WHEN** správce spustí `zkontrolovat` bez akce
- **THEN** zkontrolují se všechny složky akcí první úrovně, archiv
  zůstane beze změny a report je v pracovním adresáři

#### Scenario: Přerušení a pokračování
- **WHEN** správce průchod archivem přeruší a spustí znovu
- **THEN** už zkontrolované nezměněné soubory se znovu nečtou

### Requirement: Podklad pro ověření prahu
Report příkazu SHALL u každého souboru, který má aspoň jeden úplný
nulový blok 4 KiB, uvést délku a polohu nejdelšího úseku nul, i když
nedosahuje prahu. U videa s přečtenými tabulkami SHALL uvést
nejdelší započítaný úsek v obrazových datech i nejdelší úsek v celém
souboru.

#### Scenario: Soubor pod prahem
- **WHEN** zdravá fotka obsahuje úsek 8 KiB nul na hranici 4 KiB
- **THEN** report ji uvede jako *v pořádku* s nejdelším úsekem 8 KiB

#### Scenario: Video s tichem
- **WHEN** video má 184 KiB nul ve zvuku a obrazová data jsou bez nul
- **THEN** report ho uvede jako *v pořádku*, bez úseku v obrazových
  datech a s úsekem 184 KiB v celém souboru
