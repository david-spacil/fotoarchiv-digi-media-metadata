## Context

Workflow `.github/workflows/docker.yml` tvoří tagy přes
`docker/metadata-action@v6`: `type=raw,value=latest` pro výchozí větev,
`type=semver` (`{{version}}`, `{{major}}.{{minor}}`) pro tagy `v*`
a `type=sha`. U pull requestu se image jen postaví (`PUSH` je
`false`). `compose.yaml` má pevně `image: …:latest`.

## Goals / Non-Goals

**Goals:**
- `docker compose pull` stáhne jen vydanou verzi.
- Poslední stav `main` zůstane dostupný v GHCR pod vlastním tagem.

**Non-Goals:**
- Automatické vydávání verzí nebo GitHub Release z workflow.
- Mazání starých image v GHCR.

## Decisions

### `latest` z `flavor: latest=auto`, `main` přes `type=edge`

Řádek `type=raw,value=latest,…` odpadne. Výchozí `flavor: latest=auto`
v `metadata-action` přidá `latest` jen k události, kde vzniká tag
`type=semver` z verze bez předverze; u větve ani u `v2.4.0-rc1` ne.
Pro `main` se přidá `type=edge,branch=main` (tag `main`).

Alternativa: ponechat `type=raw,value=latest` s podmínkou
`enable=${{ startsWith(github.ref, 'refs/tags/v') }}`. Zavrženo:
nerozliší předverze a duplikuje logiku, kterou akce už má.

### Tag image v `compose.yaml` z `.env`

`image: …:${FOTOARCHIV_TAG:-latest}`. Výchozí chování se pro
stávající `.env` bez proměnné nemění. Build z pracovní kopie
(`--build`) dostane jméno se stejným tagem, takže návrat je dál
`docker compose pull`.

## Risks / Trade-offs

- [Do vydání `v2.3.1` ukazuje `latest` v GHCR na poslední build
  z `main`] → vydat patch verzi hned po sloučení změny.
- [Kdo dnes stahuje `latest` kvůli novinkám z `main`, je dostane až
  s releasem] → přepnout `FOTOARCHIV_TAG=main` v `.env`.
