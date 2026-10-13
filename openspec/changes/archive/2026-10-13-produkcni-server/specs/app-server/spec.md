## Purpose

Spouštět webový server aplikace produkčně a přitom v jediném procesu,
protože zámky akcí, běžící importy a synchronizace Immiche jsou
v paměti procesu.

## ADDED Requirements

### Requirement: Produkční server v jednom procesu
Příkaz `python -m fotoarchiv` bez `--debug` SHALL obsluhovat aplikaci
produkčním WSGI serverem (cheroot) v jediném procesu s pevným počtem
obslužných vláken. Server MUST NOT spouštět víc procesů ani workerů
a MUST NOT při startu hlásit varování vývojového serveru. Platí to
i pro kontejner podle `compose.yaml`.

#### Scenario: Ruční spuštění
- **WHEN** správce spustí `python -m fotoarchiv --archiv …`
- **THEN** aplikace odpovídá na `--host`/`--port`, běží jako jeden
  proces a log neobsahuje „This is a development server“

#### Scenario: Kontejner
- **WHEN** správce spustí `docker compose up -d`
- **THEN** kontejner běží jako jeden proces aplikace bez varování
  vývojového serveru

#### Scenario: Zastavení
- **WHEN** server dostane SIGTERM nebo Ctrl+C
- **THEN** skončí bez čekání na timeout

### Requirement: Počet vláken
Přepínač `--vlakna N` SHALL nastavit počet obslužných vláken serveru;
výchozí hodnota SHALL být 32. Hodnota menší než 1 MUST být odmítnuta
při startu.

#### Scenario: Výchozí počet
- **WHEN** správce spustí server bez `--vlakna`
- **THEN** server obsluhuje požadavky 32 vlákny

#### Scenario: Neplatná hodnota
- **WHEN** správce spustí server s `--vlakna 0`
- **THEN** server odmítne start s chybovou hláškou

### Requirement: Streamované tělo požadavku
Server MUST předávat tělo požadavku aplikaci průběžně ze spojení, bez
předchozího uložení celého těla do paměti nebo dočasného souboru, a MUST
NOT omezovat velikost těla vlastním limitem (limit hlídá aplikace,
`MAX_FILE`).

#### Scenario: Velký upload
- **WHEN** uživatel nahrává do importu soubor větší než 1 GiB
- **THEN** soubor se zapisuje přímo do `.work/import/`, průběh
  nahrávání vidí jiné záložky průběžně a nikde jinde nevznikne jeho
  kopie

#### Scenario: Málo místa
- **WHEN** uživatel začne nahrávat soubor větší než volné místo
  v pracovním adresáři
- **THEN** server odmítne nahrávání (507) hned na začátku, ne až po
  přijetí celého těla

### Requirement: Streamované odpovědi
Server MUST odesílat části streamované odpovědi (NDJSON průběh) klientovi
hned, jak je aplikace vydá. Přerušené spojení klientem MUST ukončit
generátor odpovědi nejpozději při dalším zápisu, takže provádění importu
se zastaví nejpozději po dalších 64 MB. Odpovědi se souborem MUST dál
podporovat požadavky Range (206).

#### Scenario: Průběh importu
- **WHEN** uživatel provádí import velkého videa
- **THEN** ukazatel průběhu se posouvá během kopírování, ne až na konci

#### Scenario: Zavření stránky během importu
- **WHEN** uživatel během kopírování do archivu zavře stránku
- **THEN** kopírování se zastaví a rozkopírovaný soubor v archivu
  nezůstane

#### Scenario: Přetáčení videa
- **WHEN** lupa požádá o část videa hlavičkou Range
- **THEN** server odpoví 206 s požadovaným rozsahem

### Requirement: Vývojový server pro ladění
S přepínačem `--debug` SHALL `python -m fotoarchiv` spustit vývojový
server Werkzeugu s reloaderem. Pravidelná synchronizace Immiche MUST
běžet jen v procesu, který obsluhuje požadavky, ne v hlídacím procesu
reloaderu.

#### Scenario: Ladění
- **WHEN** vývojář spustí server s `--debug` a změní soubor v `fotoarchiv/`
- **THEN** server se sám restartuje

#### Scenario: Jedna synchronizace pod reloaderem
- **WHEN** vývojář spustí server s `--debug` a nastaveným Immichem
- **THEN** synchronizace obličejů běží v jediném vlákně jediného procesu
