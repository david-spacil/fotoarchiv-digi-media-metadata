## Why

Image `latest` v GHCR se dnes přestaví po každém pushi do `main`, tedy
po každém sloučeném pull requestu. `compose.yaml` stahuje právě
`latest`, takže `docker compose pull` na serveru přinese poslední stav
`main`, ne poslední release. Aktualizace na serveru mají brát jen
vydané verze.

## What Changes

- `latest` v GHCR SHALL vznikat jen z release tagu `vX.Y.Z` bez
  předverze (např. `v2.3.1`, ne `v2.4.0-rc1`).
- Push do `main` nahraje image pod tagem `main` (a `sha-<hash>`),
  `latest` nemění.
- `compose.yaml` vybírá tag image z proměnné `FOTOARCHIV_TAG` v `.env`
  (výchozí `latest`); správce tak může zkusit `main` nebo zůstat na
  konkrétní verzi (`2.3`, `2.3.1`).
- Vydání jako patch verze `v2.3.1`, které zároveň přepíše současný
  `latest` (poslední build z `main`) na release.

## Capabilities

### New Capabilities

- (žádné)

### Modified Capabilities

- `app-server`: tagy image v GHCR (`latest` jen z releasu, nový tag
  `main`) a volba tagu v `compose.yaml`.

## Impact

- `.github/workflows/docker.yml` (tagy `docker/metadata-action`),
  `compose.yaml`, `.env.example`.
- Dokumentace: `docs/provoz/docker.md`, `README.md` (nasazení přes
  Docker).
- Kód aplikace ani testy se nemění.
