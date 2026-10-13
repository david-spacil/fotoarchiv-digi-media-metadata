## Context

`main()` v `fotoarchiv/__main__.py` sestaví aplikaci `create_app(...)`
a spustí ji `app.run(threaded=True)`. `create_app` rovnou spouští
vlákno synchronizace Immiche (`immich.Sync.start`), proto pod
`--debug` běží synchronizace v hlídacím procesu reloaderu i v podprocesu.
Upload importu čte `request.stream` po 1 MiB a průběžně hlásí `prijato`
(`importer.Imports.add_file`); NDJSON odpovědi jsou generátory
s `call_on_close(events.close)` (`app.ndjson`). Testy podvrhují
`Flask.run`, aby `main()` nespustil server.

## Goals / Non-Goals

**Goals:**
- Produkční WSGI server bez změny chování API a bez změny klienta.
- Jeden proces, stejně jednoduché spuštění na Linuxu i Windows.

**Non-Goals:**
- Reverzní proxy, TLS na serveru, `ProxyFix` — aplikace nečte
  `remote_addr` ani schéma, `--https` jen nastavuje
  `SESSION_COOKIE_SECURE`.
- Access log jednotlivých požadavků (Werkzeug ho psal, cheroot ne);
  lze doplnit později jako WSGI middleware.
- Gunicorn/uWSGI konfigurace v repozitáři.

## Decisions

**cheroot jako server.** `cheroot.wsgi.Server((host, port), app,
numthreads=N)`. Čte tělo požadavku líně ze socketu (bez limitu, výchozí
`max_request_body_size = 0`), zápis odpovědi flushuje po každém kusu
(`nodelay`), nečinná keep-alive spojení drží selektor, ne obslužné
vlákno. Funguje na Windows.
Alternativy: *waitress* — tělo bufferuje celé před předáním aplikaci
(nad 512 KB v `/tmp`, limit 1 GiB), což rozbije 20GB upload, kontrolu
místa a průběh nahrávání; *gunicorn* `-w 1 --threads N` — nefunguje na
Windows a nabízí zvýšení `-w`.

**Spuštění v samostatné funkci.** `main()` volá `serve(app, host, port,
threads)`, která vytvoří server, zaloguje adresu a blokuje
v `server.start()`; `KeyboardInterrupt` → `server.stop()`. Testy pak
podvrhují `serve` (místo `Flask.run`). SIGTERM v kontejneru dál řeší
`init: true` (výchozí akce SIGTERM proces ukončí).

**`--vlakna`, výchozí 32.** Dlouho držená vlákna: uploady (2–3 na
klienta), NDJSON streamy (kontrola, plán, provedení, přetřídit), čtení
videa v lupě. Heartbeaty a náhledy jsou krátké. 32 vláken s rezervou
pokryje jednotky souběžných uživatelů; víc lze nastavit bez změny kódu.
Hodnota < 1 → `parser.error`.

**`--debug` beze změny serveru.** Zůstává `app.run(debug=True,
threaded=True)` s reloaderem. Aby synchronizace Immiche běžela jen
v obslužném procesu, `main()` předá `immich_interval=None`, když běží
s `--debug` a není nastavené `WERKZEUG_RUN_MAIN` (hlídací proces
reloaderu). Úklid starých importů (`purge`) může proběhnout dvakrát,
je idempotentní.

**Odpojení klienta.** Cheroot při zápisu do zavřeného socketu vyhodí
chybu, ukončí požadavek a zavolá `close()` iterátoru odpovědi → Flask
zavolá `call_on_close` → `events.close()` → `GeneratorExit`
v kopírování, které smaže rozkopírovaný soubor. Ověřit testem se
skutečným serverem na volném portu (spojení zavřené uprostřed NDJSON
streamu → generátor zavřen).

## Risks / Trade-offs

- [Odpojení se pozná až při zápisu; první zápis po zavření může ještě
  projít do bufferu jádra] → nejhůř o jednu událost později, tj. pořád
  v řádu dalších 64 MB; ověří integrační test a ruční zkouška.
- [Vyčerpání vláken dlouhými streamy] → `--vlakna`, výchozí 32; nové
  požadavky čekají ve frontě (`request_queue_size`), nepadají.
- [`timeout` cheroot (10 s) na nečinný socket] → při pomalém uploadu
  je to timeout jednoho `recv`, ne celého požadavku; zkontrolovat ruční
  zkouškou velkého uploadu.
- [Ztráta access logu Werkzeugu] → chyby aplikace se logují dál
  (Flask logger); access log lze doplnit později.

## Migration Plan

`git pull && docker compose up -d --build` (nový balíček se nainstaluje
při buildu); lokálně `.venv/bin/pip install -r requirements.txt`.
Přepínače se nemění, jen přibude `--vlakna`. Návrat: předchozí verze
image/kódu.
