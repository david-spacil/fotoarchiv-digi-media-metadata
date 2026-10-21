## 1. Workflow

- [x] 1.1 Vytvořit `.github/workflows/docker.yml`: spouštění na push do
  `main`, tag `v*`, pull request a ručně; job `test` (Python 3.12, apt
  `libimage-exiftool-perl` a `ffmpeg`, `pip install -r
  requirements.txt`, `pytest -q`, Node, `node --test
  tests/js/*.test.mjs`); job `image` s `needs: test`, checkout
  s `fetch-depth: 0`, `metadata-action` (latest z výchozí větve, semver,
  sha), login do GHCR mimo pull request, `build-push-action` s `context:
  .`, `push` mimo pull request, cache `gha`. Oprávnění `contents: read`,
  `packages: write` jen u jobu `image`.
- [x] 1.2 Ověřit syntaxi workflow (actionlint nebo parsování YAML)
  a že lokálně projdou oba příkazy testů z jobu `test`.

## 2. Compose a dokumentace

- [x] 2.1 `compose.yaml`: `image:
  ghcr.io/david-spacil/fotoarchiv-digi-media-metadata:latest`, ponechat
  `build: .`, upravit hlavičkový komentář. Ověřit `docker compose
  config`, je-li Docker k dispozici.
- [x] 2.2 `docs/provoz/docker.md`: první nasazení přes `pull`,
  aktualizace (`docker compose pull && docker compose up -d`), build
  větve na serveru a návrat na release, verze v hlavičce u image
  z GitHubu, zveřejnění balíčku v GHCR.
- [x] 2.3 `AGENTS.md`: příkaz nasazení v oddílu Příkazy.

## 3. Ověření

- [x] 3.1 Po pushi zkontrolovat běh workflow na GitHubu (testy a build
  bez pushe image u větve/pull requestu).
