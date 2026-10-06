"""Flask server: JSON API a statický klient.

Dokument `_metadata.json` drží klient a ukládá ho celý (PUT) s verzí,
ze které vycházel. Jediný stav serveru jsou zámky akcí v paměti (`lock`),
proto server smí běžet jen jako jeden proces.
"""

import json
from datetime import date
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file

from . import (cleanup, geocode, immich, importer, lock, model, names, scan,
               thumbs, xmp)
from . import index as archive_index
from .archive import SCHEMA, Conflict, Workspace

STATIC = Path(__file__).parent / "static"


def create_app(archiv, work, zapis=False, locks=None, kontakt=None,
               geocoder=None, immich_fetch=None, immich_interval=None):
    """`kontakt` zapne geokódování (User-Agent pro Nominatim).

    `immich_interval` (s) zapne pravidelnou synchronizaci obličejů
    z Immiche, jakmile je nastavené připojení; None = jen na požádání.
    """
    ws = Workspace(archiv, work, zapis)
    locks = locks or lock.Locks()
    cache_dir = ws.work / "cache"
    if geocoder is None and kontakt:
        geocoder = geocode.Geocoder(cache_dir, kontakt)
    name_index = names.NameIndex(ws.metadata_files)
    imports = importer.Imports(ws.work)
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
        začátkem kopírování je obyčejná JSON odpověď."""
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
        try:
            imports.check_idle(id)
            nazev, path = import_target(body)
            existing = existing_groups(nazev, path)
            importer.check_groups(volba, existing)
            had_doc = path is not None and ws.load(nazev)[0] is not None
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
