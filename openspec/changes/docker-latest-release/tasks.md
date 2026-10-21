## 1. Workflow a compose

- [ ] 1.1 `.github/workflows/docker.yml`: odebrat `type=raw,value=latest`,
  přidat `type=edge,branch=main`, upravit úvodní komentář; ověřit
  čtením diffu proti dokumentaci `docker/metadata-action`
  (`flavor: latest=auto`)
- [ ] 1.2 `compose.yaml` s `${FOTOARCHIV_TAG:-latest}` a `.env.example`
  s `FOTOARCHIV_TAG`; ověřit `docker compose config`, je-li Docker
  k dispozici, jinak čtením

## 2. Dokumentace

- [ ] 2.1 `docs/provoz/docker.md` (tagy v GHCR, volba tagu, aktualizace
  a vyzkoušení `main`) a `README.md` (nasazení přes Docker); ověřit
  čtením diffu

## 3. Vydání

- [ ] 3.1 Po sloučení do `main` vydat tag `v2.3.1`; ověřit v GHCR, že
  `latest` ukazuje na `2.3.1`
