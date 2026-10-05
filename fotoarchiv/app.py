"""Flask server: JSON API a statický klient.

Dokument `_metadata.json` drží klient a ukládá ho celý (PUT) s verzí,
ze které vycházel. Jediný stav serveru jsou zámky akcí v paměti (`lock`),
proto server smí běžet jen jako jeden proces.
"""

from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

from . import cleanup, lock, model, names, scan, thumbs
from .archive import SCHEMA, Conflict, Workspace

STATIC = Path(__file__).parent / "static"


def create_app(archiv, work, zapis=False, locks=None):
    ws = Workspace(archiv, work, zapis)
    locks = locks or lock.Locks()
    cache_dir = ws.work / "cache"
    name_index = names.NameIndex(ws.metadata_files)
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["WORKSPACE"] = ws
    app.config["LOCKS"] = locks

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
                "zapis": ws.zapis}

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

    @app.get("/api/jmena")
    def jmena():
        known = name_index.names()
        q = request.args.get("q", "")
        return {"navrhy": names.suggest(q, known) if q else known}

    @app.get("/api/jmena/kontrola")
    def jmena_kontrola():
        return names.check(request.args.get("jmeno", ""),
                           name_index.names())

    return app
