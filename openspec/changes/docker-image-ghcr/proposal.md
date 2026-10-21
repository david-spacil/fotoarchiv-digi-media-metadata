## Why

Image se dnes staví na serveru (`docker compose up -d --build`), takže
server potřebuje pracovní kopii repozitáře a build závislosti a nasazená
verze závisí na tom, co je zrovna v checkoutu. Image postavený na GitHubu
z `main` nebo z tagu je pro všechna nasazení stejný a ověřený testy.
V repozitáři zatím chybí jakékoli CI.

## What Changes

- Workflow GitHub Actions SHALL spustit testy Pythonu a JS u každého
  pushe do `main`, tagu `v*` a pull requestu.
- Po úspěšných testech SHALL workflow postavit image z `Dockerfile`
  a u `main` a tagů `v*` ho nahrát do GitHub Container Registry
  (`ghcr.io/david-spacil/fotoarchiv-digi-media-metadata`): `main` jako
  `latest`, tag `vX.Y.Z` jako `X.Y.Z` a `X.Y`, každý jako `sha-<hash>`.
  U pull requestu se image jen postaví (kontrola buildu), nenahraje se.
- Verze v hlavičce SHALL v image z GitHubu odpovídat `git describe
  --tags` jako u lokálního buildu (checkout s celou historií a tagy).
- `compose.yaml` SHALL odkazovat na image z GHCR a ponechat `build: .`:
  `docker compose pull && docker compose up -d` nasadí release,
  `docker compose up -d --build` postaví image z aktuálního checkoutu
  (testování větve na serveru před releasem). Návrat na release je
  znovu `pull`; co právě běží, ukazuje verze v hlavičce.
- Dokumentace provozu (`docs/provoz/docker.md`, `AGENTS.md`) SHALL
  popsat oba postupy.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `app-server`: nové požadavky Image z GitHubu (testy, build, tagy,
  verze) a Nasazení z GHCR i z pracovní kopie (`pull`, build větve).

## Impact

- Nový `.github/workflows/docker.yml`.
- `compose.yaml`: `image:` na GHCR místo lokálního jména.
- `docs/provoz/docker.md`, `AGENTS.md`: nasazení a aktualizace.
- Balíček na GHCR musí být veřejný (repozitář bude veřejný), jinak
  server potřebuje `docker login ghcr.io`. Kód aplikace, `Dockerfile`
  ani datový model se nemění.
