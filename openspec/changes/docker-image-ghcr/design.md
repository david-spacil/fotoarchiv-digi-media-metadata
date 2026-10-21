## Context

Motivace viz proposal.md. `Dockerfile` má stage `verze`, která
z `.git` v kontextu buildu zapíše `git describe --tags --always` do
`fotoarchiv/VERZE`; `.dockerignore` `.git` nevylučuje. `compose.yaml`
má `build: .` a lokální `image: fotoarchiv-digi-media-metadata:latest`.
Testy Pythonu potřebují `exiftool` a `ffmpeg` (bez exiftoolu jich padá
přes 50), testy JS jen `node`.

## Goals / Non-Goals

**Goals:**
- Na GHCR se nedostane image z commitu, na kterém neprošly testy.
- Image z GitHubu ukazuje v hlavičce stejnou verzi jako lokální build
  téhož commitu.
- Lokální build z checkoutu funguje beze změny postupu.

**Non-Goals:**
- Image pro větve a pull requesty v registru (testování větve je build
  na serveru).
- Jiné architektury než `linux/amd64`.
- Automatické nasazení na server, mazání starých image v GHCR.

## Decisions

### Jeden workflow: testy, pak build

Job `test` (Python 3.12 jako v image, apt `libimage-exiftool-perl`
a `ffmpeg`, `pytest -q`, `node --test`) a job `image` s `needs: test`.
Alternativa samostatného workflow pro testy by build nevázala na jejich
výsledek.

### Kontext buildu z checkoutu s celou historií

`actions/checkout` s `fetch-depth: 0` (historie i tagy, jinak
`git describe` dá jen hash) a `docker/build-push-action` s `context: .`.
Výchozí git kontext akce by `.git` do buildu nepředal a verze by byla
„neznámá“.

### Tagy přes `docker/metadata-action`

`latest` jen z výchozí větve, `type=semver` pro `{{version}}`
a `{{major}}.{{minor}}`, `type=sha` pro dohledání commitu. Push jen
mimo pull request; přihlášení `GITHUB_TOKEN` s `packages: write`.
Cache vrstev `type=gha`.

### `compose.yaml`: GHCR image a `build: .` zároveň

Pevně `:latest`, bez proměnné pro tag. Lokální build dostane stejné
jméno a nahradí stažený image; `docker compose pull` ho zase nahradí
releasem. Rozlišení zajišťuje verze v hlavičce (tag, počet commitů,
hash), proto další tag (`dev`) není potřeba.

## Risks / Trade-offs

- Po lokálním buildu `docker compose up -d` bez `pull` dál spouští
  lokální build → v dokumentaci postup návratu přes `pull`.
- Nový balíček na GHCR je ve výchozím stavu soukromý → po prvním
  buildu ho zveřejnit v nastavení balíčku (zapsáno v docs).
