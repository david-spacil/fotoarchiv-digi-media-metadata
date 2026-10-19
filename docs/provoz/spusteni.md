[← Dokumentace](../README.md)

# Lokální spuštění

Potřeba: Python 3, `exiftool`, `ffmpeg` (bez něj videa nemají náhled)
a připojený archiv (na Fedoře např. `dnf install perl-Image-ExifTool
ffmpeg`).

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m fotoarchiv \
  --archiv /mnt/x/fotoarchiv/FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB
```

Aplikace běží na <http://127.0.0.1:5000> na produkčním WSGI serveru cheroot
v jediném procesu s obslužnými vlákny. Bez dalších přepínačů je to
vývojový režim: archiv se jen čte, metadata a cache jdou do `.work/`.
Server spouštět jen jednou (zámky akcí jsou v paměti procesu).
Přístup vyžaduje přihlášení (viz [Přihlášení a role](prihlaseni.md)).
Hlavička ukazuje verzi běžícího kódu podle `git describe --tags
--always --dirty` (např. `v0.2.0-1-g5609826`), zjištěnou při startu
serveru; po `git pull` ji ukáže až restart.

Volitelné přepínače:

- `--zapis-do-archivu` — produkční režim, `_metadata.json` se ukládá do
  složek akcí a provádí se úklid a import.
- `--bez-prihlaseni` — vývojový režim bez přihlášení: každý je admin
  a jméno u zámku se zadává v prohlížeči. S `--zapis-do-archivu` server
  odmítne start.
- `--vlakna N` — počet obslužných vláken serveru (výchozí 32).
- `--debug` — vývojový server Werkzeugu s reloaderem pro ladění kódu.
- `--https` — cookie relace jen přes HTTPS (za reverzní proxy s HTTPS).
- `--work CESTA` — jiný pracovní adresář než `.work`.
- `--host`, `--port` — adresa a port (výchozí `127.0.0.1:5000`).

Jednorázové skrytí nedokončených akcí před Immichem (viz
[Archiv](../navrh/archiv.md)), při zastaveném serveru:

```sh
.venv/bin/python -m fotoarchiv skryt --archiv … --zapis-do-archivu
```

Kontrola poškozených souborů v archivu (viz [Poškozené
soubory](../navrh/poskozene-soubory.md)), archiv jen čte:

```sh
.venv/bin/python -m fotoarchiv zkontrolovat [AKCE] --archiv … --work .work
# → kontrola poškození souborů; navíc vypíše nálezy konzistence akcí
#   (nepodporované soubory, osiřelé sidecary, RAWy, podsložky,
#   záznamy bez souboru); --rychle jen konzistenci, --zapis-do-archivu
#   po potvrzení převede nálezy s nápravou do .ignored složek
```

Napojení na Immich (obličeje) a kontakt pro Nominatim (geokódování
míst) nastavuje admin v aplikaci; uloží se do `.work/immich.json`
a `.work/nominatim.json`. Zastaralý přepínač `--kontakt` server při
startu převezme do `.work/nominatim.json`, pokud ještě neexistuje.
