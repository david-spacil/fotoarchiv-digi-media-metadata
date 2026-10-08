# Proposal

## Why

Aplikace běží na serveru v Dockeru i lokálně z různých větví a z rozhraní
nejde poznat, jaká verze kódu právě běží. Při hlášení chyby nebo ověřování
nasazení se to musí zjišťovat na serveru ručně (issue #12).

## What Changes

- Server při startu zjistí verzi aplikace: v pracovní kopii z gitu
  (`git describe --tags --always --dirty`, např. `v0.2.0-1-g5609826`),
  v Docker image ze souboru zapsaného při buildu; jinak je verze neznámá.
- `/api/info` vrací verzi v poli `verze` (`null`, když není známá).
- Hlavička stránky ukazuje verzi drobně vedle názvu aplikace
  („verze neznámá“, když ji server nezná).
- `Dockerfile` zjistí verzi v samostatné build stage z `.git`
  (do výsledného image se `.git` nedostane); `.dockerignore` proto
  `.git` nevylučuje.
- README (Lokální spuštění, Docker) popisuje, odkud se verze bere.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `metadata-workspace`: nový požadavek na verzi aplikace v hlavičce.

## Impact

- Nový modul `fotoarchiv/version.py`, úprava `fotoarchiv/app.py`
  (`/api/info`), `fotoarchiv/static/app.js` (`header`), `style.css`.
- `Dockerfile`, `.dockerignore`, `.gitignore` (soubor `fotoarchiv/VERZE`).
- Testy `tests/test_version.py`, `tests/test_app.py`.
- Datový model, archiv ani export se nemění.
