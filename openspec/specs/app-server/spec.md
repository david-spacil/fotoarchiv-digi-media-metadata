# app-server Specification

## Purpose

Spouštět webový server aplikace produkčně a přitom v jediném procesu,
protože zámky akcí, běžící importy a synchronizace Immiche jsou
v paměti procesu.

## Requirements

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

### Requirement: Image z GitHubu
Workflow GitHub Actions SHALL u pushe do `main`, tagu `v*` a pull
requestu spustit testy a po jejich úspěchu postavit image
z `Dockerfile`. U `main` a tagů `v*` SHALL image nahrát do GHCR, u pull
requestu MUST NOT nic nahrát. `latest` SHALL vzniknout jen z tagu
`vX.Y.Z` bez předverze, push do `main` SHALL nahrát image `main`. Verze
v hlavičce image SHALL být `git describe --tags` commitu.

#### Scenario: Release z tagu
- **WHEN** se pushne tag `v0.4.0` a testy projdou
- **THEN** v GHCR je image `latest`, `0.4.0` a `0.4`, hlavička ukazuje
  `v0.4.0`

#### Scenario: Předverze
- **WHEN** se pushne tag `v0.5.0-rc1` a testy projdou
- **THEN** v GHCR je image `0.5.0-rc1` a `latest` zůstane předchozí
  release

#### Scenario: Push do main
- **WHEN** se pushne commit do `main` a testy projdou
- **THEN** v GHCR je image `main` a `sha-<hash>` tohoto commitu
  a `latest` zůstane předchozí release

#### Scenario: Neúspěšné testy
- **WHEN** na pushnutém commitu v `main` neprojde test
- **THEN** se image nestaví a `main` v GHCR zůstane předchozí

#### Scenario: Pull request
- **WHEN** se otevře pull request
- **THEN** proběhnou testy a build image, do GHCR se nic nenahraje

### Requirement: Nasazení z GHCR i z pracovní kopie
`compose.yaml` SHALL používat image z GHCR s tagem z proměnné
`FOTOARCHIV_TAG` (výchozí `latest`, tedy poslední release) a zároveň
umožnit build image z pracovní kopie pod stejným jménem.

#### Scenario: Nasazení releasu
- **WHEN** správce bez `FOTOARCHIV_TAG` spustí `docker compose pull &&
  docker compose up -d`
- **THEN** kontejner běží z image `latest` z GHCR, tedy z posledního
  releasu

#### Scenario: Vyzkoušení main
- **WHEN** správce nastaví v `.env` `FOTOARCHIV_TAG=main` a spustí
  `docker compose pull && docker compose up -d`
- **THEN** kontejner běží z posledního buildu větve `main`

#### Scenario: Build větve na serveru
- **WHEN** správce v pracovní kopii přepne větev a spustí
  `docker compose up -d --build`
- **THEN** kontejner běží z image postaveného z checkoutu a hlavička
  ukazuje verzi tohoto commitu

#### Scenario: Návrat na release
- **WHEN** po buildu větve správce spustí `docker compose pull &&
  docker compose up -d`
- **THEN** kontejner běží znovu z image z GHCR podle `FOTOARCHIV_TAG`
