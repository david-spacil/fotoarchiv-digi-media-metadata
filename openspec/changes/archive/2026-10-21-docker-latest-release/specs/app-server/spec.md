## MODIFIED Requirements

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
