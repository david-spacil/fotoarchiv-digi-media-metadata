"""Flask server: JSON API a statický klient.

Dokument `_metadata.json` drží klient a ukládá ho celý (PUT) s verzí,
ze které vycházel. Jediný stav serveru jsou zámky akcí v paměti (`lock`),
proto server smí běžet jen jako jeden proces.

Přihlášení hlídá jediná vstupní kontrola (`before_request`): bez platné
relace stránky přesměruje na přihlášení, API vrátí 401.
"""

import json
import math
import secrets
import threading
from datetime import date, datetime
from pathlib import Path

from flask import (Flask, Response, abort, g, jsonify, make_response,
                   redirect, request, send_file, session)

from . import (albums, auth, cleanup, consistency, geocode, immich,
               importer, integrity, lock, model, naming, names, scan,
               thumbs, unsorted, version, xmp)
from . import index as archive_index
from .archive import SCHEMA, UNSORTED, Collision, Conflict, Workspace

STATIC = Path(__file__).parent / "static"

# Bez relace dostupné; s povinnou změnou hesla navíc jen PASSWORD_PATHS.
OPEN_PATHS = {"/prihlaseni", "/api/prihlaseni", "/api/odhlaseni"}
PASSWORD_PATHS = {"/heslo", "/api/heslo", "/api/ja"}
# Nastavení serveru; správu archivu (přetřídit, uvolnění zámku) hlídají
# endpointy podle role archivář.
ADMIN_PREFIXES = ("/api/immich", "/api/nominatim")
# Bez přihlášení (jen vývojový režim) je každý admin.
NOBODY = dict({"login": None, "jmeno": None, "email": None, "role": "admin",
               "zmenit_heslo": False}, **auth.rights("admin"))


def create_app(archiv, work, zapis=False, locks=None, geocoder=None,
               immich_fetch=None, immich_interval=None, prihlaseni=True,
               https=False, immich_hlidac_interval=None,
               immich_hlidac_limit=None, immich_fetch_bytes=None):
    """`immich_interval` (s) zapne pravidelnou synchronizaci obličejů
    z Immiche, jakmile je nastavené připojení; None = jen na požádání.

    `immich_hlidac_interval` a `immich_hlidac_limit` (s) zkracují
    hlídání akce po dokončení (`albums.Hlidac`) pro testy; ve výchozím
    nastavení jsou to konstanty `HLIDAC_INTERVAL` a `HLIDAC_LIMIT`.

    `immich_fetch_bytes` podvrhuje binární dotazy (zmenšeniny) pro
    testy nástroje pojmenování.

    `prihlaseni=False` jen ve vývojovém režimu (hlídá CLI); `https`
    posílá cookie relace jen přes HTTPS.
    """
    ws = Workspace(archiv, work, zapis)
    # Jednou při startu: po `git pull` musí dál ukazovat běžící kód.
    verze = version.app_version()
    locks = locks or lock.Locks()
    cache_dir = ws.work / "cache"
    contact = geocode.Contact(ws.work)
    if geocoder is None:
        geocoder = geocode.Geocoder(cache_dir, contact.load)
    accounts = auth.Auth(ws.work)
    name_index = names.NameIndex(ws.metadata_files)
    unsorted_root = ws.archiv / UNSORTED
    imports = importer.Imports(ws.work, source_root=unsorted_root)
    immich_settings = immich.Settings(ws.work)
    sync = immich.Sync(ws, locks, immich_settings, name_index.names,
                       fetch=immich_fetch, fetch_bytes=immich_fetch_bytes,
                       interval=immich_interval)
    # Hlídač alba a rozpoznávání po dokončení akce (na pozadí).
    hlidac = albums.Hlidac(
        sync,
        interval=immich_hlidac_interval or immich.HLIDAC_INTERVAL,
        limit=immich_hlidac_limit or immich.HLIDAC_LIMIT)
    if immich_interval and immich_settings.load():
        sync.start()
    # Nástroj pojmenování osob: odložené osoby per login+akce a příznak,
    # že relace v nástroji něco změnila (po zavření spustí synchronizaci).
    odlozene = naming.Odlozene(ws.work)
    jmena_zmeny = set()          # (login, akce)
    jmena_lock = threading.Lock()
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["WORKSPACE"] = ws
    app.config["LOCKS"] = locks
    app.config["IMPORTS"] = imports
    app.config["IMMICH"] = sync
    app.config["IMMICH_HLIDAC"] = hlidac
    app.config["AUTH"] = accounts
    app.config.update(SECRET_KEY=auth.secret_key(ws.work),
                      SESSION_COOKIE_NAME="fotoarchiv",
                      SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=https)

    # --- přihlášení --------------------------------------------------------

    def session_user():
        """Přihlášený uživatel z relace, nebo None (odebraný ze souboru,
        jiný otisk hesla)."""
        login = session.get("login")
        user = accounts.users.get(login) if login else None
        if user is None or \
                session.get("otisk") != accounts.passwords.fingerprint(login):
            return None
        return dict(user, login=login,
                    zmenit_heslo=accounts.passwords.must_change(login),
                    **auth.rights(user["role"]))

    @app.before_request
    def check_login():
        path = request.path
        api = path.startswith("/api/")
        if not prihlaseni:
            g.user = NOBODY
        elif path.startswith("/static/") or path in OPEN_PATHS:
            return None
        else:
            g.user = session_user()
            if g.user is None:
                session.clear()
                if api:
                    return {"chyba": "neprihlasen"}, 401
                return redirect("/prihlaseni")
            if g.user["zmenit_heslo"] and path not in PASSWORD_PATHS:
                if api:
                    return {"chyba": "zmenit_heslo"}, 403
                return redirect("/heslo")
        if path.startswith(ADMIN_PREFIXES) and not g.user["admin"]:
            return {"chyba": "jen_admin"}, 403
        return None

    def me():
        u = g.user
        return {"prihlaseni": prihlaseni, "login": u["login"],
                "jmeno": u["jmeno"], "role": u["role"], "admin": u["admin"],
                "archivar": u["archivar"], "zmenit_heslo": u["zmenit_heslo"]}

    @app.get("/prihlaseni")
    def login_page():
        if not prihlaseni:
            return redirect("/")
        return send_file(STATIC / "prihlaseni.html")

    @app.get("/heslo")
    def password_page():
        if not prihlaseni:
            return redirect("/")
        return send_file(STATIC / "heslo.html")

    @app.post("/api/prihlaseni")
    def login():
        if not prihlaseni:
            return {"chyba": "bez_prihlaseni"}, 409
        body = request.get_json(force=True, silent=True) or {}
        user, err = accounts.login(body.get("login"), body.get("heslo"))
        if user is None:
            # Stejná odpověď pro neexistující login i špatné heslo.
            if err == "neplatne":
                return {"chyba": "neplatne"}, 401
            return {"chyba": "zdrzeno", "za_s": math.ceil(err)}, 429
        session.clear()
        session["login"] = user["login"]
        session["otisk"] = accounts.passwords.fingerprint(user["login"])
        session["id"] = secrets.token_hex(8)  # zámky tohoto přihlášení
        g.user = session_user()
        return me()

    @app.post("/api/odhlaseni")
    def logout():
        locks.release_login(session.get("id"))
        session.clear()
        return {}

    @app.post("/api/heslo")
    def change_password():
        if not prihlaseni:
            return {"chyba": "bez_prihlaseni"}, 409
        body = request.get_json(force=True, silent=True) or {}
        login = g.user["login"]
        err = accounts.change(login, body.get("stavajici"), body.get("nove"))
        if err:
            return {"chyba": err}, 400
        # Ostatní relace mají starý otisk; tahle zůstane přihlášená.
        session["otisk"] = accounts.passwords.fingerprint(login)
        g.user = session_user()
        return me()

    @app.get("/api/ja")
    def ja():
        return me()

    def event_dir(nazev):
        try:
            return ws.event_dir(nazev)
        except Collision:
            abort(make_response({"chyba": "kolize_pripony"}, 409))
        except KeyError:
            abort(404)

    @app.get("/")
    def index():
        return send_file(STATIC / "index.html")

    @app.get("/api/info")
    def info():
        return {"archiv": str(ws.archiv.resolve()),
                "work": str(ws.work.resolve()),
                "zapis": ws.zapis,
                "geokodovani": geocoder.enabled,
                "immich": immich_settings.load() is not None,
                "import_limit": importer.MAX_FILE,
                "verze": verze}

    def immich_stav(polozka):
        """{stav, cas, album} ze záznamu `.work/immich-alba.json`; bez
        `chyba` (ta se ukazuje jen adminovi na Nastavení) a bez id alba
        (vrací se jen bool, že album existuje)."""
        entry = polozka or {}
        return {"stav": entry.get("stav"), "cas": entry.get("cas"),
                "album": bool(entry.get("album"))}

    @app.get("/api/akce")
    def akce_list():
        """Výpis akcí; `drzitel` je jméno z platného zámku a `vase`, zda
        ho drží relace z `?relace=` (relace sama se nevrací). `upravit`
        = smí ji přihlášený uživatel upravit (`model.can_edit`).
        `immich` je stav akce v Immichi (jen s nastaveným Immichem a
        se záznamem); čteno ze `.work/immich-alba.json`. Má-li akce
        album a `rozpoznano`, `hotovost` dostane i `osoby` [p, c] ze
        `.work/immich-osoby.json` a `chybi` u *hotovo* i `osoby` při
        nepojmenovaných. Výpis se Immiche neptá — jen soubory ve
        `.work/`."""
        relace = request.args.get("relace")
        events = ws.list_events()
        # Jedno čtení souboru pro celý výpis; Immiche se neptá.
        nastaveno = immich_settings.load() is not None
        alba = sync.alba.nacti() if nastaveno else {}
        osoby = sync.osoby.nacti() if nastaveno else {}
        for event in events:
            event["upravit"] = model.can_edit(g.user, event)
            holder = locks.holder(event["nazev"])
            event["drzitel"] = holder and {
                "jmeno": holder["jmeno"],
                "vase": locks.holds(event["nazev"], relace)}
            if event["nazev"] in alba:
                event["immich"] = immich_stav(alba[event["nazev"]])
            if event.get("hotovost") is not None:
                pocty = model.osoby(alba.get(event["nazev"]),
                                    osoby.get(event["nazev"]))
                if pocty:
                    event["hotovost"]["osoby"] = pocty
                    if event["stav"] == "hotovo" and pocty[0] < pocty[1] \
                            and "osoby" not in event["chybi"]:
                        event["chybi"].append("osoby")
        return jsonify(events)

    @app.get("/api/akce/<nazev>")
    def akce_detail(nazev):
        path = event_dir(nazev)
        files, _ = scan.scan(path, cache_dir)
        doc, version = ws.load(nazev)
        novy = doc is None
        # Nálezy kontroly kořene (issue #11); záznamy jen z uložené verze.
        nalezy = consistency.check(path, doc)
        nove, chybejici = [], []
        if novy:
            # Návrh skupin z importu má přednost před automatickým.
            proposal = imports.proposal(nazev)
            doc = model.new_document(
                nazev, files, importer.apply_proposal(files, proposal)
                if proposal else scan.propose_groups(files))
        else:
            nove, chybejici = model.merge_scan(doc, files)
        return {
            "nazev": nazev,
            "novy": novy,
            "metadata": doc,
            "version": version,
            "soubory": files,
            "kontrola": nalezy,
            # Poškozené soubory kořene z cache kontroly (issue #10):
            # {název: {stav, duvody, overeno?, vyradit?}} jen soubory,
            # které v kořeni jsou; odznak počítá `integrity.counted`.
            "poskozene": integrity.summary(
                integrity.event_cache_path(ws.work, nazev), doc,
                {f["nazev"] for f in files}),
            "nove": nove,
            "chybejici": chybejici,
            "pracovni_soubor": str(ws.metadata_path(nazev).resolve()),
            "zamek": locks.holder(nazev),
            # Kontrola nanečisto a verze `_metadata.json` posledního exportu.
            "export": {
                "kontrola": None if novy else xmp.export(ws, nazev,
                                                         nanecisto=True),
                "version": ws.export_version(nazev),
            },
        }

    @app.get("/api/akce/<nazev>/immich")
    def akce_immich_stav(nazev):
        """Stav akce v Immichi pro každého přihlášeného (není pod
        `/api/immich`, který je jen pro admina). Čte jen
        `<work>/immich-alba.json` a `<work>/immich-osoby.json`;
        Immiche se nikdy neptá. Bez nastaveného Immiche se stav
        neuvádí; `chyba` se nevrací (ukazuje se jen adminovi na
        Nastavení). `osoby` je [pojmenované, celkem] jen při albu se
        stavem `rozpoznano` a uložených počtech, jinak null."""
        event_dir(nazev)                     # neexistující akce = 404
        if immich_settings.load() is None:
            return {"nastaveno": False, "stav": None, "cas": None,
                    "album": False, "osoby": None}
        alba_polozka = sync.alba.polozka(nazev)
        return dict(nastaveno=True,
                    osoby=model.osoby(alba_polozka, sync.osoby.polozka(nazev)),
                    **immich_stav(alba_polozka))

    # --- nástroj pojmenování osob -------------------------------------------

    def jmena_klient(nazev):
        """(client, album_id) pro nástroj; smí jen archivář a výš.

        403 bez role, 404 pro neexistující akci, nenastavený Immich
        nebo akci bez alba. Zámek akce se nevyžaduje: nástroj
        `_metadata.json` nemění.
        """
        if not g.user["archivar"]:
            abort(make_response({"chyba": "jen_archivar"}, 403))
        event_dir(nazev)
        client = sync.client()
        if client is None:
            abort(make_response({"chyba": "immich_nenastaven"}, 404))
        album = (sync.alba.polozka(nazev) or {}).get("album")
        if not album:
            abort(make_response({"chyba": "bez_alba"}, 404))
        return client, album

    def jmena_assets(client, album):
        """Assety alba; chyba Immiche = 502 s textem."""
        try:
            return client.search_album(album)
        except immich.ImmichError as e:
            abort(make_response({"chyba": str(e)}, 502))

    def jmena_obraz(nahled):
        """Binární odpověď Immiche jako odpověď aplikace (502 při
        chybě); klíč Immiche ani adresa serveru ven neuniknou."""
        try:
            data, content_type = nahled()
        except immich.ImmichError as e:
            abort(make_response({"chyba": str(e)}, 502))
        return Response(data, mimetype=content_type or "image/jpeg")

    def jmena_precti(client, album, nazev):
        """Přepočte počty osob akce do `.work/immich-osoby.json`.

        Chyba přepočtu zápis osob do Immiche nevadí — vrátí None.
        """
        try:
            pocty = albums.pocty_osob(client.search_album(album))
        except immich.ImmichError:
            return None
        try:
            sync.osoby.nastav(nazev, pocty["pojmenovane"], pocty["celkem"])
        except OSError:
            return None
        return [pocty["pojmenovane"], pocty["celkem"]]

    @app.get("/api/akce/<nazev>/osoby")
    def osoby_list(nazev):
        """Osoby k pojmenování s výřezy a metadaty (jen archivář).

        Před výběrem vyřadí odložené, které mezitím dostaly jméno
        nebo byly skryty; přepočte a uloží počty osob akce. `stav`
        a `uplne` = stav akce v Immichi (nástroj upozorní, dokud
        nejsou obličeje rozpoznány). `odlozene` je počet odložených
        osob, které jsou v akci stále nepojmenované a neskryté.
        """
        client, album = jmena_klient(nazev)
        assets = jmena_assets(client, album)
        login = g.user["login"] or ""
        nezname = naming.nepojmene_ids(assets)
        seznam = odlozene.seznam(login, nazev)
        k_vyradeni = [i for i in seznam if i not in nezname]
        if k_vyradeni:
            odlozene.vyradit(login, nazev, k_vyradeni)
        platne = [i for i in seznam if i in nezname]
        doc, _ = ws.load(nazev)
        pocty = albums.pocty_osob(assets)
        try:
            sync.osoby.nastav(nazev, pocty["pojmenovane"], pocty["celkem"])
        except OSError:
            pass
        stav = (sync.alba.polozka(nazev) or {}).get("stav")
        return {"stav": stav, "uplne": stav == "rozpoznano",
                "odlozene": len(platne),
                "osoby": naming.osoby_k_pojmenovani(client, assets, doc,
                                                    platne)}

    @app.get("/api/akce/<nazev>/osoby/nahled/<asset_id>")
    def osoby_nahled(nazev, asset_id):
        """Proxy zmenšeniny fotky z alba akce (klíč Immiche zůstává
        na serveru); asset mimo album = 404."""
        client, album = jmena_klient(nazev)
        if asset_id not in naming.assety_alba(
                jmena_assets(client, album)):
            abort(404)
        return jmena_obraz(lambda: client.thumbnail(asset_id))

    @app.get("/api/akce/<nazev>/osoby/osoba/<person_id>/nahled")
    def osoby_osoba_nahled(nazev, person_id):
        """Proxy náhledu existující osoby (náhled při nabídce sloučení);
        povolen jen pro pojmenovanou osobu = cíl sloučení."""
        client, album = jmena_klient(nazev)
        try:
            people, _ = client.people()
        except immich.ImmichError as e:
            abort(make_response({"chyba": str(e)}, 502))
        osoba = next((p for p in people if p.get("id") == person_id
                      and (p.get("name") or "").strip()), None)
        if osoba is None:
            abort(404)
        return jmena_obraz(lambda: client.person_thumbnail(person_id))

    @app.post("/api/akce/<nazev>/osoby/<person_id>")
    def osoby_jednat(nazev, person_id):
        """Jedna volba nástroje: pojmenovat / sloučit / nevim / skryt.

        Zápis jde jen do Immiche; `_metadata.json` se nemění. Po
        zápisu se přepočtou počty osob a poznamená změna (`hotovo`
        pak spustí synchronizaci). Chyba Immiche = 502 a nic se
        neodloží ani nezapíše. Odložení per login z relace.
        """
        client, album = jmena_klient(nazev)
        body = request.get_json(force=True, silent=True) or {}
        akce = body.get("akce")
        if akce not in ("pojmenovat", "sloucit", "nevim", "skryt"):
            abort(400)
        # Osoba musí mít obličej v albu akce.
        assets = jmena_assets(client, album)
        if person_id not in {p["id"] for a in assets
                             for p in a.get("people") or []
                             if p.get("id")}:
            abort(404)
        login = g.user["login"] or ""
        if akce == "nevim":
            odlozene.odlozit(login, nazev, person_id)
            return {"ok": True, "osoby": None}
        jmeno = None
        if akce == "pojmenovat":
            jmeno = str(body.get("jmeno") or "").strip()
            if not jmeno:
                return {"chyba": "jmeno_povinne"}, 400
            kontrola = names.check(jmeno, name_index.names())
            if kontrola["prevod"]:
                # Klient převod potvrdí a pošle kanonický tvar.
                return {"chyba": "kanonicky_tvar",
                        "navrh": kontrola["prevod"]}, 400
            if not body.get("samostatne"):
                # Shoda s jinou osobou (bez diakritiky, velikosti písmen
                # a pořadí slov) → cíl nabídky sloučení.
                try:
                    people, _ = client.people()
                except immich.ImmichError as e:
                    return {"chyba": str(e)}, 502
                klic = names.normalize(jmeno)
                shoda = next((p for p in people
                              if p.get("id") != person_id
                              and (p.get("name") or "").strip()
                              and names.normalize(p["name"]) == klic),
                             None)
                if shoda:
                    return {"shoda": {"id": shoda["id"],
                                      "jmeno": shoda["name"]}}, 409
        if akce == "sloucit":
            # Cíl = existující jiná osoba s jménem.
            cil = body.get("cil")
            try:
                people, _ = client.people()
            except immich.ImmichError as e:
                return {"chyba": str(e)}, 502
            existujici = next((p for p in people
                               if p.get("id") == cil
                               and (p.get("name") or "").strip()), None)
            if not cil or cil == person_id or existujici is None:
                return {"chyba": "cil_slouceni"}, 400
        try:
            if akce == "pojmenovat":
                client.update_people([{"id": person_id, "name": jmeno}])
            elif akce == "sloucit":
                client.merge_people(body["cil"], [person_id])
            else:
                client.update_people([{"id": person_id,
                                       "isHidden": True}])
        except immich.ImmichError as e:
            return {"chyba": str(e)}, 502
        with jmena_lock:
            jmena_zmeny.add((login, nazev))
        return {"ok": True, "osoby": jmena_precti(client, album, nazev)}

    @app.post("/api/akce/<nazev>/osoby/kolo")
    def osoby_kolo(nazev):
        """Nové kolo: vymaže odložení uživatele v akci."""
        jmena_klient(nazev)
        odlozene.nove_kolo(g.user["login"] or "", nazev)
        return {"ok": True}

    @app.post("/api/akce/<nazev>/osoby/hotovo")
    def osoby_hotovo(nazev):
        """Zavření nástroje; po změně spustí synchronizaci, aby jména
        šla do `obliceje` a počtů bez čekání na pravidelný běh."""
        jmena_klient(nazev)
        klic = (g.user["login"] or "", nazev)
        with jmena_lock:
            meneno = klic in jmena_zmeny
            jmena_zmeny.discard(klic)
        if meneno:
            sync.trigger()
        return {"ok": True, "synchronizace": meneno}

    def body_field(body, key):
        value = body.get(key)
        if not isinstance(value, str) or not value.strip():
            abort(400)
        return value

    def may_edit(nazev):
        """Smí přihlášený uživatel akci upravit? Admin a archivář bez
        čtení dokumentu."""
        if g.user["archivar"]:
            return True
        return model.can_edit(g.user, ws.load(nazev)[0])

    def lock_denied(nazev, body):
        """Odpověď 423, když relace z těla požadavku nedrží zámek akce."""
        if not locks.holds(nazev, body.get("relace")):
            return {"chyba": "bez_zamku",
                    "drzitel": locks.holder(nazev)}, 423
        return None

    def require_lock(nazev, body):
        """423 bez zámku; 403, když uživatel o oprávnění k úpravě přišel
        během držení zámku (role, `upravili`)."""
        denied = lock_denied(nazev, body)
        if denied:
            return denied
        if not may_edit(nazev):
            return {"chyba": "jen_cteni"}, 403
        return None

    @app.post("/api/akce/<nazev>/zamek")
    def zamek_ziskat(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
        if not may_edit(nazev):
            return {"chyba": "jen_cteni"}, 403
        # Přihlášený: jméno z relace, poslané se ignoruje.
        jmeno = g.user["jmeno"] or body_field(body, "jmeno").strip()
        ok, info = locks.acquire(nazev, body_field(body, "relace"), jmeno,
                                 session.get("id"))
        if not ok:
            return {"chyba": "obsazeno", "drzitel": info}, 409
        return {"zamek": info}

    @app.put("/api/akce/<nazev>/zamek")
    def zamek_heartbeat(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
        relace = body_field(body, "relace")
        if not locks.heartbeat(nazev, relace):
            return {"chyba": "ztracen", "drzitel": locks.holder(nazev),
                    "uvolnil": locks.forced(relace)}, 409
        return {"zamek": locks.holder(nazev)}

    @app.post("/api/akce/<nazev>/zamek/vynutit")
    def zamek_vynutit(nazev):
        """Admin nebo archivář uvolní zámek jiné relace (opuštěná
        rozdělaná práce)."""
        event_dir(nazev)
        if not g.user["archivar"]:
            return {"chyba": "jen_archivar"}, 403
        return {"uvolneno": locks.force_release(
            nazev, g.user["jmeno"] or "admin")}

    @app.delete("/api/akce/<nazev>/zamek")
    @app.post("/api/akce/<nazev>/zamek/uvolnit")  # navigator.sendBeacon
    def zamek_uvolnit(nazev):
        event_dir(nazev)
        body = request.get_json(force=True, silent=True) or {}
        locks.release(nazev, body_field(body, "relace"))
        return {}

    def touch(nazev, doc, stored):
        """Zapíše do `upravili` přihlášeného uživatele (jméno jako u
        zámku; bez přihlášení jméno držitele zámku) a čas uložení."""
        jmeno = g.user["jmeno"] or locks.holder(nazev)["jmeno"]
        model.touch(doc, stored, jmeno,
                    datetime.now().isoformat(timespec="seconds"))

    @app.put("/api/akce/<nazev>/metadata")
    def akce_save(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
        denied = require_lock(nazev, body)
        if denied:
            return denied
        doc = body.get("metadata")
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
            abort(400)
        # Obličeje jen z uložené verze; ta odpovídá `version`, jinak
        # uložení stejně skončí konfliktem.
        stored, _ = ws.load(nazev)
        model.clean(model.keep_faces(doc, stored))
        touch(nazev, doc, stored)
        try:
            version = ws.save(nazev, doc, body.get("version"))
        except Conflict as e:
            return {"chyba": "konflikt", "version": e.current_version}, 409
        if body.get("version") is None:
            imports.drop_proposal(nazev)  # průvodce ho už použil
        return {"version": version}

    @app.get("/api/akce/<nazev>/skupiny")
    def akce_groups(nazev):
        """Skupiny akce bez skenu: z `_metadata.json`, jinak z návrhu
        importu, jinak `null`."""
        event_dir(nazev)
        doc, _ = ws.load(nazev)
        if doc is not None:
            return {"skupiny": doc.get("skupiny") or {}, "zdroj": "metadata"}
        proposal = imports.proposal(nazev)
        if proposal is not None:
            return {"skupiny": proposal["skupiny"], "zdroj": "navrh"}
        return {"skupiny": None, "zdroj": None}

    @app.post("/api/akce/<nazev>/dokoncit")
    def akce_finish(nazev):
        """Uloží `dokonceno`, exportuje a zveřejní složku akce pro Immich
        (odebere `.ignored`). `dokonceno` je datum prvního dokončení:
        opakované dokončení ho nemění a při chybě exportu nebo
        přejmenování se vrací jen u akce, která ho dosud neměla (#20)."""
        event_dir(nazev)
        body = request.get_json(force=True)
        denied = require_lock(nazev, body)
        if denied:
            return denied
        doc, version = ws.load(nazev)
        if doc is None:
            return {"chyba": "bez_metadat"}, 409
        if body.get("version") != version:
            return {"chyba": "konflikt", "version": version}, 409
        first = not doc.get("dokonceno")
        if first:
            doc["dokonceno"] = date.today().isoformat()
        touch(nazev, doc, doc)
        try:
            version = ws.save(nazev, doc, version)
            result = xmp.export(ws, nazev)
            if not result["chyby"]:
                try:
                    ws.publish(nazev)
                except OSError as e:
                    result["zverejneni"] = str(e)
                except Collision:
                    result["zverejneni"] = "kolize_pripony"
            if first and (result["chyby"] or result.get("zverejneni")):
                doc["dokonceno"] = None
                version = ws.save(nazev, doc, version)
        except Conflict as e:
            return {"chyba": "konflikt", "version": e.current_version}, 409
        if result and not result["chyby"] and not result.get("zverejneni"):
            # Alba a rozpoznávání hlídá pozadí: sken knihovny, album,
            # stav. Dokončení na Immich nečeká a jeho chybu nezaznamená.
            hlidac.spust(nazev)
        return dict(result, dokonceno=doc["dokonceno"], version=version,
                    export_version=ws.export_version(nazev),
                    index=archive_index.write(ws))

    def cleanup_args(path, doc, body):
        """(volby, RAWy z kořene, k vyřazení, ostatní) pro plán úklidu.

        Označení k vyřazení se čte z uloženého `_metadata.json`.
        `z_plochy` (úklid z pracovní plochy; dřív `jen_vyradit`) nebere
        návrhy voleb podsložek — podsložka bez volby v `volby` se nemění —
        a RAWy i ostatní soubory přesune vždy.
        """
        discard = [name for name, record in
                   ((doc or {}).get("soubory") or {}).items()
                   if record.get("vyradit")]
        if body.get("z_plochy") or body.get("jen_vyradit"):
            volby = {f["nazev"]: None for f in cleanup.subfolders(path)}
            volby.update(body.get("volby") or {})
            return volby, True, discard, True
        return (body.get("volby"), body.get("raw_v_koreni", True), discard,
                body.get("ostatni", True))

    @app.post("/api/akce/<nazev>/uklid")
    def akce_cleanup(nazev):
        path = event_dir(nazev)
        body = request.get_json(silent=True) or {}
        doc, _ = ws.load(nazev)
        return cleanup.plan(path, *cleanup_args(path, doc, body))

    @app.post("/api/akce/<nazev>/uklid/provest")
    def akce_cleanup_execute(nazev):
        """Provede úklid; záznamy vyřazených souborů odstraní
        z `_metadata.json` a vrátí jeho novou verzi."""
        path = event_dir(nazev)
        if not ws.zapis:
            return {"chyba": "vyvojovy_rezim"}, 403
        body = request.get_json(force=True)
        denied = require_lock(nazev, body)
        if denied:
            return denied
        doc, version = ws.load(nazev)
        result = cleanup.execute(
            path, *cleanup_args(path, doc, body),
            sidecar=lambda name: xmp.sidecar(doc, nazev, name))
        gone = [o["soubor"] for o in result["operace"]
                if o.get("vyradit") and o["stav"] == cleanup.DONE]
        if gone:
            # Ukládání drží klient se zámkem; konflikt = jeho souběžné
            # uložení, záznamy se odstraní z aktuální verze.
            while True:
                doc, version = ws.load(nazev)
                for name in gone:
                    doc["soubory"].pop(name, None)
                try:
                    version = ws.save(nazev, doc, version)
                    break
                except Conflict:
                    continue
        return dict(result, version=version)

    def child(path, name):
        """Přímý potomek `path`; cesty a skryté položky nejsou."""
        if "/" in name or "\\" in name or name.startswith("."):
            abort(404)
        return path / name

    def root_file(nazev, soubor):
        """Soubor v kořeni akce; podsložky a skryté soubory nejsou."""
        src = child(event_dir(nazev), soubor)
        if not src.is_file():
            abort(404)
        return src

    def thumb_response(src, kontrola=None):
        size = request.args.get("velikost", str(thumbs.SIZE))
        if size not in map(str, thumbs.SIZES):
            abort(400)
        if kontrola is not None:
            # Miss náhledu = soubor se stejně čte: kontrola integrity
            # zdarma doplní cache akce (issue #10, varianta C). Chyba
            # kontroly náhled nezastaví.
            try:
                integrity.ensure_event_file(src, kontrola)
            except Exception:
                pass
        thumb = thumbs.thumbnail(src, cache_dir, int(size))
        if thumb is None:
            abort(404)
        response = send_file(thumb, mimetype="image/jpeg")
        response.cache_control.max_age = 3600
        return response

    @app.get("/api/akce/<nazev>/nahled/<soubor>")
    def akce_thumb(nazev, soubor):
        # Kontrola integrity jen pro soubory kořene akce (stejná cache
        # jako příkaz `zkontrolovat`).
        return thumb_response(root_file(nazev, soubor),
                              integrity.event_cache_path(ws.work, nazev))

    @app.get("/api/akce/<nazev>/uklid/nahled/<slozka>/<soubor>")
    def akce_cleanup_thumb(nazev, slozka, soubor):
        # Ukázka z podsložky před úklidem; jen média, archiv jen čte.
        folder = child(event_dir(nazev), slozka)
        if not folder.is_dir() or scan.extension(soubor) not in scan.MEDIA_EXT:
            abort(404)
        src = child(folder, soubor)
        if not src.is_file():
            abort(404)
        return thumb_response(src)

    @app.get("/api/akce/<nazev>/soubor/<soubor>")
    def akce_original(nazev, soubor):
        # Originál jen pro čtení; send_file umí Range (206) pro přetáčení.
        src = root_file(nazev, soubor)
        if scan.extension(soubor) not in scan.MEDIA_EXT:
            abort(404)
        return send_file(src, conditional=True)

    # --- import ------------------------------------------------------------

    def refused(e, status=409):
        return dict({"chyba": e.code}, **e.detail), status

    def owner(source=None):
        """Vlastník importu: jméno z relace; bez přihlášení (vývojový
        režim) `jmeno` z těla (`source`), jinak z `?jmeno=`."""
        if prihlaseni:
            return g.user["jmeno"]
        return (request.args if source is None else source).get("jmeno")

    def check_import(id, jmeno):
        """Import patří jménu, pod kterým vznikl; jiní ho nevidí."""
        try:
            return imports.get(id, jmeno)
        except KeyError:
            abort(404)

    def import_target(body):
        """(název, složka) cíle z těla: stávající `cil`, nebo nová `nova`
        (složka None, dokud nevznikne)."""
        if body.get("cil"):
            return body["cil"], event_dir(body["cil"])
        nova = body_field(body, "nova")
        importer.check_new_name(ws.archiv, nova)
        return nova, None

    def ndjson(events, first=None):
        """Události generátoru jako stream NDJSON (řádek = JSON objekt).
        Přerušené spojení generátor zavře (smaže rozkopírovaný soubor)."""
        def lines():
            if first is not None:
                yield json.dumps(first, ensure_ascii=False) + "\n"
            for event in events:
                yield json.dumps(event, ensure_ascii=False) + "\n"
        response = Response(lines(), mimetype="application/x-ndjson")
        response.headers["Cache-Control"] = "no-cache"
        response.call_on_close(events.close)
        return response

    def target_groups(nazev, path):
        """Skupiny cíle importu: z `_metadata.json`, jinak z návrhu; nová
        akce žádné."""
        if path is None:
            return {}
        doc, _ = ws.load(nazev)
        if doc is None:
            doc = imports.proposal(nazev) or {}
        return doc.get("skupiny") or {}

    def write_description(nazev, path, created, had_doc, record, done,
                          jmeno):
        """Zapíše popis importu (`record["popis"]`) pro přenesená média
        `done`: nové akci založí `_metadata.json`, akci s ním doplní nové
        skupiny a přiřazení, akci bez něj návrh skupin. Autory celé akce
        (schéma /1, starší rozpracovaný import) nezapíše nikam. Do
        `upravili` zapíše `jmeno` (kdo import provedl; volá se ze streamu,
        mimo kontext požadavku). Vrátí výsledek `importer.describe`
        se {"zapsano", "navrh", "chyba"?}."""
        cas = datetime.now().isoformat(timespec="seconds")
        popis = record.get("popis") or {}
        akce = popis.get("akce") or {}
        known = set(record.get("existujici") or [])
        groups = importer.describe(popis, done, {}, set())
        try:
            if created:
                files, _ = scan.scan(path, cache_dir)
                doc = model.new_document(nazev, files, groups)
                doc["akce"].update(importer.event_fields(akce))
                model.touch(doc, None, jmeno, cas)
                ws.save(nazev, model.clean(doc), None)
                return dict(groups, zapsano=True, navrh=False)
            if not had_doc:
                proposal = imports.proposal(nazev) or {}
                groups = importer.describe(
                    popis, done, proposal.get("skupiny") or {}, known)
                if groups["prirazeni"]:
                    imports.add_proposal(nazev, groups)
                return dict(groups, zapsano=True, navrh=True)
            doc, version = ws.load(nazev)
            if doc is None:
                raise Conflict(None)
            groups = importer.describe(popis, done,
                                       doc.get("skupiny") or {}, known)
            files, _ = scan.scan(path, cache_dir)
            model.merge_scan(doc, files)
            doc.setdefault("skupiny", {}).update(groups["skupiny"])
            for name, gid in groups["prirazeni"].items():
                record = doc["soubory"].get(name)
                if record is not None and not record.get("skupina"):
                    record["skupina"] = gid
            model.touch(doc, doc, jmeno, cas)
            ws.save(nazev, doc, version)
        except Conflict:
            return dict(groups, zapsano=False, navrh=False, chyba="konflikt")
        except (OSError, ValueError) as e:
            return dict(groups, zapsano=False, navrh=not had_doc,
                        chyba=str(e))
        return dict(groups, zapsano=True, navrh=False)

    @app.get("/api/pretridit")
    def pretridit():
        """Stream NDJSON přehledu `přetřídit`: `vypis`, pak `slozka` po
        složkách (údaje z EXIF). `exif=0` = jen výpis. Jen admin
        a archivář."""
        if not g.user["archivar"]:
            return {"chyba": "jen_archivar"}, 403
        exif = request.args.get("exif") != "0"
        events = unsorted.iter_overview(unsorted_root, cache_dir, exif=exif)
        return ndjson(events)

    @app.get("/api/import")
    def import_list():
        return {"importy": imports.owned(owner())}

    @app.post("/api/import")
    def import_create():
        """Nový import; se `zdroj` (složka v `přetřídit`) bez nahrávání,
        případně s navrženým cílem (`cil`, `nova`)."""
        body = request.get_json(force=True)
        celkem = body.get("celkem", 0)
        if not isinstance(celkem, int) or celkem < 0:
            abort(400)
        zdroj, cil = body.get("zdroj"), body.get("cil")
        if cil is not None and not isinstance(cil, str):
            abort(400)
        if zdroj is not None and not g.user["archivar"]:
            return {"chyba": "jen_archivar"}, 403
        jmeno = owner(body)
        if not isinstance(jmeno, str) or not jmeno.strip():
            abort(400)
        try:
            id = imports.create(jmeno.strip(), celkem,
                                zdroj=zdroj, cil=cil,
                                nova=bool(body.get("nova")))
        except importer.Refused as e:
            return refused(e, 400 if e.code == "neplatny_zdroj" else 507)
        return {"id": id, "limit": importer.MAX_FILE}

    @app.post("/api/import/<id>/soubor")
    def import_file(id):
        """Tělo = obsah souboru (bez multipartu), čte se po blocích."""
        jmeno = owner()
        check_import(id, jmeno)
        mtime = request.args.get("mtime")
        try:
            mtime = int(mtime) if mtime else None
        except ValueError:
            abort(400)
        try:
            entry = imports.add_file(id, jmeno, request.args.get("cesta"),
                                     request.stream, request.content_length,
                                     mtime, request.args.get("relace"))
        except importer.Refused as e:
            return refused(e, {"bez_delky": 411, "prilis_velky": 413,
                               "malo_mista": 507, "probiha": 409,
                               "ma_zdroj": 409}.get(e.code, 400))
        except KeyError:
            abort(404)  # mezitím zahozeno
        return {"soubor": entry}

    @app.get("/api/import/<id>")
    def import_overview(id):
        jmeno = owner()
        check_import(id, jmeno)
        return imports.overview(id, jmeno,
                                relace=request.args.get("relace"))

    @app.post("/api/import/<id>/kontrola")
    def import_check(id):
        """Stream kontroly poškozených souborů importu (`kontrola`,
        `kontrola_prubeh`), nakonec `kontrola_hotovo` s `vysledky`
        {cesta: výsledek}; hotové z cache přijdou hned."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        record = check_import(id, jmeno)

        def events():
            results = yield from imports.iter_check(id, record)
            yield {"typ": "kontrola_hotovo", "vysledky": results}
        return ndjson(events())

    @app.post("/api/import/<id>/poskozene")
    def import_allowed(id):
        """Podezřelé soubory, které uživatel povolil importovat."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        check_import(id, jmeno)
        try:
            povolene = imports.set_allowed(id, jmeno, body.get("povolene"))
        except importer.Refused as e:
            return refused(e, 400 if e.code == "neplatna_volba" else 409)
        return {"povolene": povolene}

    @app.post("/api/import/<id>/vyloucene")
    def import_excluded(id):
        """Cesty, které uživatel vyloučil z importu (jen z výběru)."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        check_import(id, jmeno)
        try:
            vyloucene = imports.set_excluded(id, jmeno, body.get("vyloucene"))
        except importer.Refused as e:
            return refused(e, 400 if e.code == "neplatna_volba" else 409)
        return {"vyloucene": vyloucene}

    @app.delete("/api/import/<id>/soubor")
    def import_delete_damaged(id):
        """Smaže poškozený soubor importu (jen po kontrole, nezměněný).
        U zdroje v `přetřídit` jen v produkčním režimu a pod zámkem
        zdroje (jako provedení)."""
        body = request.get_json(force=True, silent=True) or {}
        jmeno = owner(body)
        record = check_import(id, jmeno)
        cesta = body.get("cesta")
        if not isinstance(cesta, str):
            abort(400)
        source_key = source_relace = None
        if record.get("zdroj"):
            if not ws.zapis:
                return {"chyba": "vyvojovy_rezim"}, 403
            try:
                # Před zámkem: provedení téže relace drží zámek zdroje
                # a uvolnění níže by ho vzalo i jemu.
                imports.check_idle(id)
            except importer.Refused as e:
                return refused(e)
            source_key = f"{UNSORTED}/{record['zdroj']}"
            source_relace = f"{body_field(body, 'relace')}#{UNSORTED}"
            ok, info = locks.acquire(source_key, source_relace,
                                     g.user["jmeno"] or record["jmeno"],
                                     session.get("id"))
            if not ok:
                return {"chyba": "zdroj_obsazen", "drzitel": info}, 409
        try:
            result = imports.delete_damaged(id, jmeno, cesta)
        except importer.Refused as e:
            return refused(e, 404 if e.code == "nenalezen" else 409)
        except OSError as e:
            return {"chyba": "smazani", "detail": str(e)}, 500
        finally:
            if source_key:
                locks.release(source_key, source_relace)
        return {"smazano": cesta, "kontrola": result}

    @app.post("/api/import/<id>/plan")
    def import_plan(id):
        """Stream průběhu porovnání s cílovou akcí, nakonec `plan`."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        check_import(id, jmeno)
        try:
            nazev, path = import_target(body)
        except importer.Refused as e:
            return refused(e)
        imports.set_target(id, jmeno, nazev, path is None)

        def events():
            for event in imports.plan(id, jmeno, path):
                if event["typ"] == "plan":
                    event.update(cil=nazev, nova=path is None)
                yield event
        return ndjson(events())

    @app.post("/api/import/<id>/skupiny")
    def import_groups(id):
        """Výchozí rozdělení přenášených médií posledního plánu podle
        volby `skupiny` (`Imports.defaults`), se skupinami cíle
        (`existujici`)."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        record = check_import(id, jmeno)
        if not record.get("cil"):
            return {"chyba": "bez_planu"}, 409
        nazev = record["cil"]
        path = None if record.get("nova") else event_dir(nazev)
        existing = target_groups(nazev, path)
        volba = body.get("skupiny")
        try:
            importer.check_groups(volba, existing)
            result = imports.defaults(id, jmeno, existing, volba)
        except importer.Refused as e:
            return refused(e)
        return dict(result, existujici=existing, cil=nazev,
                    nova=path is None)

    @app.put("/api/import/<id>/popis")
    def import_description(id):
        """Rozpracovaný popis importu (údaje akce, skupiny, autoři)."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        check_import(id, jmeno)
        try:
            imports.set_description(id, jmeno, body.get("popis"))
        except importer.Refused as e:
            return refused(e, 400 if e.code == "neplatny_popis" else 409)
        return {}

    @app.get("/api/import/<id>/nahled/<path:cesta>")
    def import_thumb(id, cesta):
        """Náhled souboru importu (nahraného i ve zdroji); nic nezapíše."""
        jmeno = owner()
        check_import(id, jmeno)
        src = imports.file_path(id, jmeno, cesta)
        if src is None or importer.kind(src.name) not in ("foto", "video") \
                or not src.is_file():
            abort(404)
        return thumb_response(src)

    @app.post("/api/import/<id>/provest")
    def import_execute(id):
        """Stream průběhu provedení, nakonec `vysledek`. Odmítnutí před
        začátkem kopírování je obyčejná JSON odpověď.

        Import ze zdroje drží po dobu provedení zámek `přetřídit/<složka>`
        (obsazený = 409 `zdroj_obsazen` s držitelem). Zámek má vlastní
        relaci: jedna relace drží nejvýš jeden zámek a ta drží cílovou
        akci."""
        body = request.get_json(force=True)
        jmeno = owner(body)
        record = check_import(id, jmeno)
        if not ws.zapis:
            return {"chyba": "vyvojovy_rezim"}, 403
        if record.get("zdroj") and not g.user["archivar"]:
            return {"chyba": "jen_archivar"}, 403
        relace = body_field(body, "relace")
        source_key = f"{UNSORTED}/{record['zdroj']}" \
            if record.get("zdroj") else None
        source_relace = f"{relace}#{UNSORTED}"
        created = False

        def release_source():
            if source_key:
                locks.release(source_key, source_relace)
        try:
            imports.check_idle(id)
            imports.check_plan(record)
            nazev, path = import_target(body)
            if source_key:
                ok, info = locks.acquire(source_key, source_relace,
                                         g.user["jmeno"] or record["jmeno"],
                                         session.get("id"))
                if not ok:
                    return {"chyba": "zdroj_obsazen", "drzitel": info}, 409
            had_doc = path is not None and ws.load(nazev)[0] is not None
            created = path is None
            if created:
                path = importer.create_event(ws.archiv, nazev)
                # Novou akci nikdo neotevře uprostřed přenosu; zámek pak
                # přebírá klient, který ji otevírá.
                locks.acquire(nazev, relace, record["jmeno"],
                              session.get("id"))
        except importer.Refused as e:
            release_source()
            return refused(e)
        # Novou akci zakládá tento import, oprávnění se u ní neověřuje.
        denied = lock_denied(nazev, body) if created \
            else require_lock(nazev, body)
        if denied:
            release_source()
            return denied
        if not created:
            # Složku zjistit až pod zámkem: dokončení ji mohlo zveřejnit.
            try:
                path = ws.event_dir(nazev)
            except KeyError:
                release_source()
                abort(404)
        finished = False

        def release():
            release_source()
            # Klient bez výsledku (zavřená záložka) zámek nové akce
            # nepřevezme ani neobnovuje: neblokovat akci do vypršení.
            if created and not finished:
                locks.release(nazev, relace)

        events = imports.execute(id, jmeno, path, relace)
        try:
            first = next(events)
        except importer.Refused as e:
            release()
            return refused(e)
        except KeyError:
            release()
            abort(404)

        def tagged():
            nonlocal finished
            for event in events:
                if event["typ"] == "soubor" and source_key:
                    locks.heartbeat(source_key, source_relace)
                if event["typ"] == "vysledek":
                    event["cil"] = nazev
                    # Zámek akce drží tato relace, klient akci nemá
                    # otevřenou: zápis nesouběží s plochou.
                    done = [o["do"] for o in event["operace"]
                            if o["stav"] == cleanup.DONE and importer.kind(
                                o["do"]) in ("foto", "video")]
                    groups = event["skupiny"] = write_description(
                        nazev, path, created, had_doc, record, done, jmeno)
                    for o in event["operace"]:
                        o["skupina"] = groups["prirazeni"].get(o["do"]) \
                            if o["stav"] == cleanup.DONE else None
                    event["index"] = archive_index.write(ws)
                yield event
                finished = event["typ"] == "vysledek"
        stream = tagged()
        response = ndjson(stream, first)
        response.call_on_close(events.close)
        response.call_on_close(release)
        return response

    @app.delete("/api/import/<id>")
    def import_discard(id):
        body = request.get_json(force=True, silent=True) or {}
        jmeno = owner(body)
        check_import(id, jmeno)
        try:
            imports.discard(id, jmeno)
        except importer.Refused as e:
            return refused(e)
        except KeyError:
            abort(404)
        return {}

    @app.get("/api/jmena")
    def jmena():
        known = name_index.names()
        q = request.args.get("q", "")
        return {"navrhy": names.suggest(q, known) if q else known}

    @app.get("/api/jmena/kontrola")
    def jmena_kontrola():
        return names.check(request.args.get("jmeno", ""),
                           name_index.names())

    # --- Immich ------------------------------------------------------------

    def immich_state():
        s = immich_settings.load()
        # Chyby alba (spojení, oprávnění) — jen na stránku nastavení;
        # stav akce kvůli nim nemění a běžný uživatel je nevidí.
        alba_chyby = [{"akce": akce, "chyba": entry["chyba"]}
                      for akce, entry in sorted(sync.alba.nacti().items())
                      if entry.get("chyba")]
        return {"nastaveno": s is not None,
                "adresa": s["adresa"] if s else None,
                "klic": immich.key_hint(s["klic"]) if s else None,
                "knihovna": s["knihovna"] if s else None,
                "synchronizace": sync.status(),
                "alba_chyby": alba_chyby}

    @app.get("/api/immich")
    def immich_get():
        return immich_state()

    @app.put("/api/immich")
    def immich_put():
        """Adresa a klíč; bez klíče jen beze změny adresy (klíč zůstane).

        `knihovna` (id) se uloží, jen když je v těle; bez ní zůstane
        dosavadní výběr.
        """
        body = request.get_json(force=True)
        adresa = str(body.get("adresa") or "").strip().rstrip("/")
        klic = str(body.get("klic") or "").strip()
        if not adresa.startswith(("http://", "https://")):
            return {"chyba": "spatna_adresa"}, 400
        current = immich_settings.load()
        if not klic:
            if not current or current["adresa"] != adresa:
                return {"chyba": "klic_povinny"}, 400
            klic = current["klic"]
        if "knihovna" in body:
            knihovna = str(body.get("knihovna") or "").strip() or None
        else:
            knihovna = current["knihovna"] if current else None
        immich_settings.save(adresa, klic, knihovna)
        if immich_interval:
            sync.start()
        return immich_state()

    @app.delete("/api/immich")
    def immich_delete():
        immich_settings.delete()
        return immich_state()

    @app.get("/api/immich/knihovny")
    def immich_knihovny():
        """Knihovny Immiche pro výběr (jen admin; klíč se nevrací)."""
        client = sync.client()
        if client is None:
            return {"chyba": "nenastaveno"}, 409
        try:
            libraries = client.libraries() or []
        except immich.ImmichError as e:
            return {"ok": False, "chyba": str(e)}, 502
        return {"knihovny": [{"id": l["id"], "name": l.get("name")}
                             for l in libraries]}

    @app.post("/api/immich/test")
    def immich_test():
        client = sync.client()
        if client is None:
            return {"chyba": "nenastaveno"}, 409
        s = immich_settings.load() or {}
        try:
            return dict(immich.test_connection(client, s.get("knihovna")),
                        ok=True)
        except immich.ImmichError as e:
            return {"ok": False, "chyba": str(e)}, 502

    @app.post("/api/immich/sync")
    def immich_sync():
        if immich_settings.load() is None:
            return {"chyba": "nenastaveno"}, 409
        return {"synchronizace": sync.trigger()}

    # --- Nominatim ----------------------------------------------------------

    def contact_state():
        # Prázdný formulář předvyplní e-mail přihlášeného admina; uloží se
        # ale jako jeden kontakt provozovatele.
        return {"kontakt": contact.load(), "navrh": g.user["email"]}

    @app.get("/api/nominatim")
    def nominatim_get():
        return contact_state()

    @app.put("/api/nominatim")
    def nominatim_put():
        body = request.get_json(force=True, silent=True) or {}
        kontakt = str(body.get("kontakt") or "").strip()
        if not kontakt:
            return {"chyba": "kontakt_povinny"}, 400
        contact.save(kontakt)
        return contact_state()

    @app.delete("/api/nominatim")
    def nominatim_delete():
        contact.delete()
        return contact_state()

    @app.get("/api/geokodovani")
    def geokodovani():
        if not geocoder.enabled:
            return {"chyba": "geokodovani_vypnuto"}, 503
        q = request.args.get("q", "").strip()
        if not q:
            abort(400)
        try:
            found, cached = geocoder.search(q)
        except geocode.GeocodeError as e:
            return {"chyba": "sluzba_nedostupna", "detail": str(e)}, 502
        return {"kandidati": found, "z_cache": cached}

    return app
