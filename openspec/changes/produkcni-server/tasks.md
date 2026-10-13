# Tasks

## 1. Příprava

- [x] 1.1 Nainstalovat závislosti a spustit výchozí testy
      (`.venv/bin/python -m pytest -q`, `node --test
      tests/js/*.test.mjs`); ověřit nenulové počty testů a že vše
      prochází

## 2. Server

- [x] 2.1 Přidat `cheroot` do `requirements.txt`; ověřit instalaci
      `.venv/bin/pip install -r requirements.txt`
- [x] 2.2 Funkce `serve(app, host, port, threads)` v
      `fotoarchiv/__main__.py` (cheroot `wsgi.Server`, Ctrl+C →
      `stop()`); `main()` ji volá bez `--debug`, s `--debug` dál
      `app.run(debug=True, threaded=True)`; testy, které podvrhují
      `Flask.run`, upravit na podvržení `serve` a ověřit, že prochází
- [x] 2.3 Přepínač `--vlakna` (výchozí 32, < 1 → chyba); testy na
      předání hodnoty do `serve` a odmítnutí `--vlakna 0`
- [x] 2.4 Pod `--debug` bez `WERKZEUG_RUN_MAIN` předat
      `immich_interval=None`; test, že hlídací proces synchronizaci
      nespustí a obslužný ano

## 3. Ověření se skutečným serverem

- [x] 3.1 Test se cheroot na volném portu (vlákno): upload těla po
      blocích dorazí do `add_file` průběžně (`prijato` roste před
      koncem těla) a soubor nad 1 MiB se uloží celý; ověřit, že
      prochází
- [x] 3.2 Test: NDJSON odpověď chodí po řádcích a zavření spojení
      uprostřed streamu zavře generátor (`GeneratorExit`); ověřit, že
      prochází
- [x] 3.3 Test: `GET` média s hlavičkou `Range` vrátí 206 se správným
      rozsahem; ověřit, že prochází

## 4. Ruční ověření

- [ ] 4.1 `python -m fotoarchiv` i `docker compose up -d --build`: log
      bez varování vývojového serveru, `ps` ukáže jeden proces
      aplikace, `docker compose stop` skončí hned
- [ ] 4.2 Import s průběhem a přerušením zavřením stránky (rozkopírovaný
      soubor v archivu nezůstane), upload souboru nad 1 GiB s průběhem
      v jiné záložce, přehrávání a přetáčení videa v lupě,
      synchronizace Immiche (v logu jednou)
- [ ] 4.3 `--debug`: reloader po změně souboru restartuje server,
      synchronizace Immiche běží jen jednou

## 5. Dokumentace

- [x] 5.1 README (Lokální spuštění: server, `--vlakna`, `--debug`;
      Docker; Souběh: jeden proces s vlákny) a AGENTS.md (Příkazy,
      Stav); ověřit, že odpovídají chování
