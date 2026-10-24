[← Dokumentace](../README.md)

# Klient pro import z telefonu

Kód v `klient/`, vlastní závislosti v `klient/requirements.txt`
(PySide6, PyInstaller); server se nemění, klient používá stávající
`/api/prihlaseni` a `/api/import`. Adresa serveru musí být HTTPS
(HTTP jen `127.0.0.1` a `localhost`, cookie relace by šla po síti
nešifrovaně).

## Vývoj a testy

```sh
python -m venv klient/.venv
klient/.venv/bin/pip install -r requirements.txt \
  -r klient/requirements.txt pytest
klient/.venv/bin/python -m klient          # okno
klient/.venv/bin/python -m klient --gvfs DIR  # strom místo telefonu
QT_QPA_PLATFORM=offscreen klient/.venv/bin/python -m pytest -q \
  tests/test_klient.py tests/test_klient_ui.py
```

Testy logiky (`tests/test_klient.py`) běží i v serverovém `.venv`
(proti skutečnému serveru na localhostu), testy okna jen s PySide6.

## Sestavení

```sh
klient/.venv/bin/pyinstaller --onefile --windowed \
  --name fotoarchiv-klient --paths . klient/spustit.py
# → dist/fotoarchiv-klient (~65 MB)
```

Workflow `.github/workflows/klient.yml` spustí testy a binárku pro
Linux nahraje jako artefakt.

## Registrace v systému

`fotoarchiv-klient --registrovat` zapíše
`~/.local/share/applications/fotoarchiv-klient.desktop` (menu
aplikací), `--odregistrovat` ho smaže. Nabídka po připojení telefonu
na Linuxu není: MTP svazek nehlásí `x-content/image-dcf`, klient proto
na telefon čeká sám (hlídá `/run/user/<uid>/gvfs/`, nepřipojený MTP
svazek zkusí připojit `gio mount`).
