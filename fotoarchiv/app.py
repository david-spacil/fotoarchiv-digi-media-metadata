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
from datetime import date
from pathlib import Path

from flask import (Flask, Response, abort, g, jsonify, make_response,
                   redirect, request, send_file, session)

from . import (auth, cleanup, geocode, immich, importer, lock, model, names,
               scan, thumbs, unsorted, xmp)
from . import index as archive_index
from .archive import SCHEMA, UNSORTED, Collision, Conflict, Workspace

STATIC = Path(__file__).parent / "static"

# Bez relace dostupné; s povinnou změnou hesla navíc jen PASSWORD_PATHS.
OPEN_PATHS = {"/prihlaseni", "/api/prihlaseni", "/api/odhlaseni"}
PASSWORD_PATHS = {"/heslo", "/api/heslo", "/api/ja"}
ADMIN_PREFIXES = ("/api/immich", "/api/nominatim")
# Bez přihlášení (jen vývojový režim) je každý admin.
NOBODY = {"login": None, "jmeno": None, "email": None, "admin": True,
          "zmenit_heslo": False}


def create_app(archiv, work, zapis=False, locks=None, geocoder=None,
               immich_fetch=None, immich_interval=None, prihlaseni=True,
               https=False):
    """`immich_interval` (s) zapne pravidelnou synchronizaci obličejů
    z Immiche, jakmile je nastavené připojení; None = jen na požádání.

    `prihlaseni=False` jen ve vývojovém režimu (hlídá CLI); `https`
    posílá cookie relace jen přes HTTPS.
    """
    ws = Workspace(archiv, work, zapis)
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
                       fetch=immich_fetch, interval=immich_interval)
    if immich_interval and immich_settings.load():
        sync.start()
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["WORKSPACE"] = ws
    app.config["LOCKS"] = locks
    app.config["IMPORTS"] = imports
    app.config["IMMICH"] = sync
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
                    zmenit_heslo=accounts.passwords.must_change(login))

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
                "jmeno": u["jmeno"], "admin": u["admin"],
                "zmenit_heslo": u["zmenit_heslo"]}

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
                "import_limit": importer.MAX_FILE}

    @app.get("/api/akce")
    def akce_list():
        return jsonify(ws.list_events())

    @app.get("/api/akce/<nazev>")
    def akce_detail(nazev):
        path = event_dir(nazev)
        files, other = scan.scan(path, cache_dir)
        doc, version = ws.load(nazev)
        novy = doc is None
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
            "nezpracovane": other,
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

    def body_field(body, key):
        value = body.get(key)
        if not isinstance(value, str) or not value.strip():
            abort(400)
        return value

    def require_lock(nazev, body):
        """Odpověď 423, když relace z těla požadavku nedrží zámek akce."""
        if not locks.holds(nazev, body.get("relace")):
            return {"chyba": "bez_zamku",
                    "drzitel": locks.holder(nazev)}, 423
        return None

    @app.post("/api/akce/<nazev>/zamek")
    def zamek_ziskat(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
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
        """Admin uvolní zámek jiné relace (opuštěná rozdělaná práce)."""
        event_dir(nazev)
        if not g.user["admin"]:
            return {"chyba": "jen_admin"}, 403
        return {"uvolneno": locks.force_release(
            nazev, g.user["jmeno"] or "admin")}

    @app.delete("/api/akce/<nazev>/zamek")
    @app.post("/api/akce/<nazev>/zamek/uvolnit")  # navigator.sendBeacon
    def zamek_uvolnit(nazev):
        event_dir(nazev)
        body = request.get_json(force=True, silent=True) or {}
        locks.release(nazev, body_field(body, "relace"))
        return {}

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

    @app.post("/api/akce/<nazev>/export")
    def akce_export(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
        denied = require_lock(nazev, body)
        if denied:
            return denied
        result = xmp.export(ws, nazev)
        if result is None:
            return {"chyba": "bez_metadat"}, 409
        return dict(result, export_version=ws.export_version(nazev),
                    index=archive_index.write(ws))

    @app.post("/api/akce/<nazev>/dokoncit")
    def akce_finish(nazev):
        """Uloží `dokonceno`, exportuje a zveřejní složku akce pro Immich
        (odebere `.ignored`); při chybě exportu nebo přejmenování
        `dokonceno` vrátí."""
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
        doc["dokonceno"] = date.today().isoformat()
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
            if result["chyby"] or result.get("zverejneni"):
                doc["dokonceno"] = None
                version = ws.save(nazev, doc, version)
        except Conflict as e:
            return {"chyba": "konflikt", "version": e.current_version}, 409
        return dict(result, dokonceno=doc["dokonceno"], version=version,
                    export_version=ws.export_version(nazev),
                    index=archive_index.write(ws))

    def cleanup_args(path, doc, body):
        """(volby, RAWy z kořene, k vyřazení) pro plán úklidu.

        Označení k vyřazení se čte z uloženého `_metadata.json`.
        `jen_vyradit` (úklid z pracovní plochy) vynechá podsložky a RAWy.
        """
        discard = [name for name, record in
                   ((doc or {}).get("soubory") or {}).items()
                   if record.get("vyradit")]
        if body.get("jen_vyradit"):
            return ({f["nazev"]: None for f in cleanup.subfolders(path)},
                    False, discard)
        return body.get("volby"), body.get("raw_v_koreni", True), discard

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

    def thumb_response(src):
        size = request.args.get("velikost", str(thumbs.SIZE))
        if size not in map(str, thumbs.SIZES):
            abort(400)
        thumb = thumbs.thumbnail(src, cache_dir, int(size))
        if thumb is None:
            abort(404)
        response = send_file(thumb, mimetype="image/jpeg")
        response.cache_control.max_age = 3600
        return response

    @app.get("/api/akce/<nazev>/nahled/<soubor>")
    def akce_thumb(nazev, soubor):
        return thumb_response(root_file(nazev, soubor))

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

    def existing_groups(nazev, path):
        """Skupiny cíle importu: `_metadata.json`, jinak návrh."""
        if path is None:
            return {}
        doc, _ = ws.load(nazev)
        if doc is not None:
            return doc.get("skupiny") or {}
        return (imports.proposal(nazev) or {}).get("skupiny") or {}

    def write_groups(nazev, path, had_doc, groups):
        """Zapíše skupiny přenesených médií do `_metadata.json` (akce ho
        má), jinak do návrhu. Vrátí {"zapsano": bool, "navrh": bool,
        "chyba"?}."""
        if not groups["prirazeni"]:
            return {"zapsano": True, "navrh": not had_doc}
        try:
            if not had_doc:
                imports.add_proposal(nazev, groups)
                return {"zapsano": True, "navrh": True}
            doc, version = ws.load(nazev)
            if doc is None:
                raise Conflict(None)
            files, _ = scan.scan(path, cache_dir)
            model.merge_scan(doc, files)
            skupiny = doc.setdefault("skupiny", {})
            for gid in groups["nove"]:
                skupiny[gid] = groups["skupiny"][gid]
            for name, gid in groups["prirazeni"].items():
                record = doc["soubory"].get(name)
                if record is not None and not record.get("skupina"):
                    record["skupina"] = gid
            ws.save(nazev, doc, version)
        except Conflict:
            return {"zapsano": False, "navrh": False, "chyba": "konflikt"}
        except (OSError, ValueError) as e:
            return {"zapsano": False, "navrh": not had_doc, "chyba": str(e)}
        return {"zapsano": True, "navrh": False}

    @app.get("/api/pretridit")
    def pretridit():
        """Stream NDJSON přehledu `přetřídit`: `vypis`, pak `slozka` po
        složkách (údaje z EXIF). `exif=0` = jen výpis."""
        exif = request.args.get("exif") != "0"
        events = unsorted.iter_overview(unsorted_root, cache_dir, exif=exif)
        return ndjson(events)

    @app.get("/api/import")
    def import_list():
        return {"importy": imports.owned(request.args.get("jmeno"))}

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
        try:
            id = imports.create(body_field(body, "jmeno").strip(), celkem,
                                zdroj=zdroj, cil=cil,
                                nova=bool(body.get("nova")))
        except importer.Refused as e:
            return refused(e, 400 if e.code == "neplatny_zdroj" else 507)
        return {"id": id, "limit": importer.MAX_FILE}

    @app.post("/api/import/<id>/soubor")
    def import_file(id):
        """Tělo = obsah souboru (bez multipartu), čte se po blocích."""
        jmeno = request.args.get("jmeno")
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
        jmeno = request.args.get("jmeno")
        check_import(id, jmeno)
        return imports.overview(id, jmeno,
                                relace=request.args.get("relace"))

    @app.post("/api/import/<id>/plan")
    def import_plan(id):
        """Stream průběhu porovnání s cílovou akcí, nakonec `plan`."""
        body = request.get_json(force=True)
        jmeno = body.get("jmeno")
        check_import(id, jmeno)
        volba = body.get("skupiny")
        try:
            nazev, path = import_target(body)
            existing = existing_groups(nazev, path)
            importer.check_groups(volba, existing)
        except importer.Refused as e:
            return refused(e)
        imports.set_target(id, jmeno, nazev, path is None, volba)

        def events():
            for event in imports.plan(id, jmeno, path, existing, volba):
                if event["typ"] == "plan":
                    event.update(cil=nazev, nova=path is None)
                yield event
        return ndjson(events())

    @app.post("/api/import/<id>/provest")
    def import_execute(id):
        """Stream průběhu provedení, nakonec `vysledek`. Odmítnutí před
        začátkem kopírování je obyčejná JSON odpověď.

        Import ze zdroje drží po dobu provedení zámek `přetřídit/<složka>`
        (obsazený = 409 `zdroj_obsazen` s držitelem). Zámek má vlastní
        relaci: jedna relace drží nejvýš jeden zámek a ta drží cílovou
        akci."""
        body = request.get_json(force=True)
        jmeno = body.get("jmeno")
        record = check_import(id, jmeno)
        if not ws.zapis:
            return {"chyba": "vyvojovy_rezim"}, 403
        relace = body_field(body, "relace")
        volba = body.get("skupiny")
        pripojit = body.get("pripojit")
        if pripojit is not None and not isinstance(pripojit, dict):
            abort(400)
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
            existing = existing_groups(nazev, path)
            importer.check_groups(volba, existing)
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
        denied = require_lock(nazev, body)
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

        events = imports.execute(id, jmeno, path, relace, existing, volba,
                                 pripojit)
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
                    event["skupiny"] = dict(
                        write_groups(nazev, path, had_doc, event["skupiny"]),
                        **event["skupiny"])
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
        jmeno = body.get("jmeno")
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
        return {"nastaveno": s is not None,
                "adresa": s["adresa"] if s else None,
                "klic": immich.key_hint(s["klic"]) if s else None,
                "synchronizace": sync.status()}

    @app.get("/api/immich")
    def immich_get():
        return immich_state()

    @app.put("/api/immich")
    def immich_put():
        """Adresa a klíč; bez klíče jen beze změny adresy (klíč zůstane)."""
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
        immich_settings.save(adresa, klic)
        if immich_interval:
            sync.start()
        return immich_state()

    @app.delete("/api/immich")
    def immich_delete():
        immich_settings.delete()
        return immich_state()

    @app.post("/api/immich/test")
    def immich_test():
        client = sync.client()
        if client is None:
            return {"chyba": "nenastaveno"}, 409
        try:
            return dict(immich.test_connection(client), ok=True)
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
