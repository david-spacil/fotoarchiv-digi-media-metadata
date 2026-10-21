## ADDED Requirements

### Requirement: Image z GitHubu
Workflow GitHub Actions SHALL u pushe do `main`, tagu `v*` a pull
requestu spustit testy Pythonu a JS a teprve po jejich úspěchu postavit
image z `Dockerfile`. U `main` a tagů `v*` SHALL image nahrát do
`ghcr.io/david-spacil/fotoarchiv-digi-media-metadata`; u pull requestu
MUST NOT nic nahrát. Verze v hlavičce image SHALL být `git describe
--tags` buildovaného commitu.

#### Scenario: Release z tagu
- **WHEN** se pushne tag `v0.4.0` a testy projdou
- **THEN** v GHCR je image `0.4.0` a `0.4`, hlavička ukazuje `v0.4.0`

#### Scenario: Push do main
- **WHEN** se pushne commit do `main` a testy projdou
- **THEN** v GHCR je image `latest` a `sha-<hash>` tohoto commitu

#### Scenario: Neúspěšné testy
- **WHEN** na pushnutém commitu v `main` neprojde test
- **THEN** se image nestaví a `latest` v GHCR zůstane předchozí

#### Scenario: Pull request
- **WHEN** se otevře pull request
- **THEN** proběhnou testy a build image, do GHCR se nic nenahraje

### Requirement: Nasazení z GHCR i z pracovní kopie
`compose.yaml` SHALL používat image z GHCR (`latest`) a zároveň
umožnit build image z pracovní kopie pod stejným jménem.

#### Scenario: Nasazení releasu
- **WHEN** správce spustí `docker compose pull && docker compose up -d`
- **THEN** kontejner běží z image `latest` z GHCR

#### Scenario: Build větve na serveru
- **WHEN** správce v pracovní kopii přepne větev a spustí
  `docker compose up -d --build`
- **THEN** kontejner běží z image postaveného z checkoutu a hlavička
  ukazuje verzi tohoto commitu

#### Scenario: Návrat na release
- **WHEN** po buildu větve správce spustí `docker compose pull &&
  docker compose up -d`
- **THEN** kontejner běží znovu z image `latest` z GHCR
