"""Flask server: JSON API a statický klient.

Server je bezstavový; dokument `_metadata.json` drží klient a ukládá ho
celý (PUT) s verzí, ze které vycházel.
"""

from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

from . import cleanup, model, names, scan, thumbs
from .archive import SCHEMA, Conflict, Workspace

STATIC = Path(__file__).parent / "static"


def create_app(archiv, work):
    ws = Workspace(archiv, work)
    cache_dir = ws.work / "cache"
    name_index = names.NameIndex(ws.metadata_files)
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["WORKSPACE"] = ws

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
                "work": str(ws.work.resolve())}

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
        }

    @app.put("/api/akce/<nazev>/metadata")
    def akce_save(nazev):
        event_dir(nazev)
        body = request.get_json(force=True)
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

    @app.get("/api/akce/<nazev>/nahled/<soubor>")
    def akce_thumb(nazev, soubor):
        path = event_dir(nazev)
        if "/" in soubor or "\\" in soubor or soubor.startswith("."):
            abort(404)
        src = path / soubor
        if not src.is_file():
            abort(404)
        thumb = thumbs.thumbnail(src, cache_dir)
        if thumb is None:
            abort(404)
        response = send_file(thumb, mimetype="image/jpeg")
        response.cache_control.max_age = 3600
        return response

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
