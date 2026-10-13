# Proposal

## Why

Server běží na vývojovém serveru Werkzeugu (`app.run(threaded=True)`),
takže log v Dockeru i při ručním spuštění hlásí „WARNING: This is
a development server. Do not use it in a production deployment.“
(issue #8). Je potřeba produkční WSGI server, který přitom zachová jeden
proces: zámky akcí, běžící importy a synchronizace Immiche jsou v paměti
procesu.

## What Changes

- `python -m fotoarchiv` (a tím i kontejner z `compose.yaml`) spustí
  aplikaci na WSGI serveru **cheroot** — čistý Python, funguje i na
  Windows, jeden proces s pevným počtem vláken. Varování vývojového
  serveru zmizí.
- Nový přepínač `--vlakna N` (výchozí 32) pro počet obslužných vláken.
- `--debug` dál spouští vývojový server Werkzeugu s reloaderem.
- Synchronizace Immiche na pozadí se pod `--debug` spustí jen
  v obslužném procesu reloaderu (dnes běží dvakrát).
- `cheroot` přibude do `requirements.txt`.
- README (Lokální spuštění, Docker, Souběh) a AGENTS.md popíší nový
  server a přepínač.

Chování API se nemění: nahrávání souborů importu se dál čte ze streamu
po blocích (bez mezibufferu celého těla), NDJSON průběh se posílá
průběžně, přerušené spojení dál zastaví kopírování a videa v lupě dál
podporují Range (206).

Zvažovaná waitress (návrh v issue) se nehodí: tělo požadavku celé
načte, než ho předá aplikaci (nad 512 KB do `/tmp`, výchozí limit
1 GiB), takže 20GB upload by se nejdřív celý uložil mimo `.work`
a kontroly místa, velikosti i průběh nahrávání by přišly až po něm.

## Capabilities

### New Capabilities

- `app-server`: spuštění webového serveru aplikace — produkční WSGI
  server v jednom procesu, počet vláken, streamované požadavky
  a odpovědi, vývojový režim `--debug`.

### Modified Capabilities

Žádné.

## Impact

- `fotoarchiv/__main__.py` (spuštění serveru, `--vlakna`, `--debug`),
  případně `fotoarchiv/app.py` (spuštění synchronizace Immiche).
- `requirements.txt` (`cheroot`); `Dockerfile` ani `compose.yaml` se
  mění nanejvýš v komentářích.
- Testy `tests/test_app.py`, `tests/test_import.py` (dnes podvrhují
  `Flask.run`), nový test se skutečným serverem na volném portu.
- README, AGENTS.md. Datový model, archiv ani export se nemění.
