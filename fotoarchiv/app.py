"""Flask server: JSON API a statický klient.

Dokument `_metadata.json` drží klient a ukládá ho celý (PUT) s verzí,
ze které vycházel. Jediný stav serveru jsou zámky akcí v paměti (`lock`),
proto server smí běžet jen jako jeden proces.
"""

import json
from datetime import date
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file

from . import (cleanup, geocode, importer, lock, model, names, scan, thumbs,
               xmp)
from .archive import SCHEMA, Conflict, Workspace

STATIC = Path(__file__).parent / "static"


def create_app(archiv, work, zapis=False, locks=None, kontakt=None,
               geocoder=None):
    """`kontakt` zapne geokódování (User-Agent pro Nominatim)."""
    ws = Workspace(archiv, work, zapis)
    locks = locks or lock.Locks()
    cache_dir = ws.work / "cache"
    if geocoder is None and kontakt:
        geocoder = geocode.Geocoder(cache_dir, kontakt)
    name_index = names.NameIndex(ws.metadata_files)
    imports = importer.Imports(ws.work)
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["WORKSPACE"] = ws
    app.config["LOCKS"] = locks
    app.config["IMPORTS"] = imports

    def event_dir(nazev):
        try:
            return ws.event_dir(nazev)
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
                "geokodovani": geocoder is not None,
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
            doc = model.new_document(nazev, files,
                                     scan.propose_groups(files))
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
        ok, info = locks.acquire(nazev, body_field(body, "relace"),
                                 body_field(body, "jmeno").strip())
        if not ok:
            return {"chyba": "obsazeno", "drzitel": info}, 409
        return {"zamek": info}

    @app.put("/api/akce/<nazev>/zamek")
    def zamek_heartbeat(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
        if not locks.heartbeat(nazev, body_field(body, "relace")):
            return {"chyba": "ztracen", "drzitel": locks.holder(nazev)}, 409
        return {"zamek": locks.holder(nazev)}

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
        try:
            version = ws.save(nazev, doc, body.get("version"))
        except Conflict as e:
            return {"chyba": "konflikt", "version": e.current_version}, 409
        return {"version": version}

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
        return dict(result, export_version=ws.export_version(nazev))

    @app.post("/api/akce/<nazev>/dokoncit")
    def akce_finish(nazev):
        """Uloží `dokonceno`, exportuje; při chybě exportu ho vrátí."""
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
            if result["chyby"]:
                doc["dokonceno"] = None
                version = ws.save(nazev, doc, version)
        except Conflict as e:
            return {"chyba": "konflikt", "version": e.current_version}, 409
        return dict(result, dokonceno=doc["dokonceno"], version=version,
                    export_version=ws.export_version(nazev))

    @app.post("/api/akce/<nazev>/uklid")
    def akce_cleanup(nazev):
        path = event_dir(nazev)
        body = request.get_json(silent=True) or {}
        return cleanup.plan(path, body.get("volby"),
                            body.get("raw_v_koreni", True))

    @app.post("/api/akce/<nazev>/uklid/provest")
    def akce_cleanup_execute(nazev):
        path = event_dir(nazev)
        if not ws.zapis:
            return {"chyba": "vyvojovy_rezim"}, 403
        body = request.get_json(force=True)
        denied = require_lock(nazev, body)
        if denied:
            return denied
        return cleanup.execute(path, body.get("volby"),
                               body.get("raw_v_koreni", True))

    def root_file(nazev, soubor):
        """Soubor v kořeni akce; podsložky a skryté soubory nejsou."""
        path = event_dir(nazev)
        if "/" in soubor or "\\" in soubor or soubor.startswith("."):
            abort(404)
        src = path / soubor
        if not src.is_file():
            abort(404)
        return src

    @app.get("/api/akce/<nazev>/nahled/<soubor>")
    def akce_thumb(nazev, soubor):
        size = request.args.get("velikost", str(thumbs.SIZE))
        if size not in map(str, thumbs.SIZES):
            abort(400)
        src = root_file(nazev, soubor)
        thumb = thumbs.thumbnail(src, cache_dir, int(size))
        if thumb is None:
            abort(404)
        response = send_file(thumb, mimetype="image/jpeg")
        response.cache_control.max_age = 3600
        return response

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

    @app.get("/api/import")
    def import_list():
        return {"importy": imports.owned(request.args.get("jmeno"))}

    @app.post("/api/import")
    def import_create():
        body = request.get_json(force=True)
        celkem = body.get("celkem", 0)
        if not isinstance(celkem, int) or celkem < 0:
            abort(400)
        try:
            id = imports.create(body_field(body, "jmeno").strip(), celkem)
        except importer.Refused as e:
            return refused(e, 507)
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
                               "malo_mista": 507,
                               "probiha": 409}.get(e.code, 400))
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

    @app.post("/api/import/<id>/provest")
    def import_execute(id):
        """Stream průběhu provedení, nakonec `vysledek`. Odmítnutí před
        začátkem kopírování je obyčejná JSON odpověď."""
        body = request.get_json(force=True)
        jmeno = body.get("jmeno")
        record = check_import(id, jmeno)
        if not ws.zapis:
            return {"chyba": "vyvojovy_rezim"}, 403
        relace = body_field(body, "relace")
        try:
            imports.check_idle(id)
            nazev, path = import_target(body)
            created = path is None
            if created:
                path = importer.create_event(ws.archiv, nazev)
                # Novou akci nikdo neotevře uprostřed přenosu; zámek pak
                # přebírá klient, který ji otevírá.
                locks.acquire(nazev, relace, record["jmeno"])
        except importer.Refused as e:
            return refused(e)
        denied = require_lock(nazev, body)
        if denied:
            return denied
        finished = False

        def release():
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
                if event["typ"] == "vysledek":
                    event["cil"] = nazev
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

    @app.get("/api/geokodovani")
    def geokodovani():
        if geocoder is None:
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
