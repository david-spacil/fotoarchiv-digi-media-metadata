"""Spuštění: python -m fotoarchiv --archiv CESTA [--work .work]
[--zapis-do-archivu], převzetí: python -m fotoarchiv prevzit --archiv …,
export XMP: python -m fotoarchiv exportovat [AKCE] --archiv …,
jednorázové heslo: python -m fotoarchiv heslo LOGIN --work …,
skrytí nedokončených akcí před Immichem: python -m fotoarchiv skryt
--archiv … [--zapis-do-archivu], kontrola poškozených souborů:
python -m fotoarchiv zkontrolovat [AKCE] --archiv …, převod
_metadata.json na schéma /2: python -m fotoarchiv migrovat --archiv …
[--zapis-do-archivu]."""

import argparse
import json
import logging
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

from cheroot import wsgi

from . import (auth, consistency, geocode, immich, importer, index,
               integrity, xmp)
from .app import create_app
from .archive import (IGNORED, METADATA_NAME, SCHEMA_V1, Collision,
                      Conflict, Workspace, adopt, event_name, upgrade,
                      version_of)


def paths(args):
    archiv = Path(args.archiv)
    if not archiv.is_dir():
        sys.exit(f"Archiv nenalezen nebo to není složka: {archiv}")
    work = Path(args.work)
    if work.resolve().is_relative_to(archiv.resolve()):
        sys.exit("Pracovní adresář nesmí ležet v archivu (cache do archivu "
                 "nepatří).")
    return archiv, work


def common(parser):
    parser.add_argument("--archiv", required=True,
                        help="složka archivu se složkami akcí")
    parser.add_argument("--work", default=".work",
                        help="pracovní adresář pro cache a _metadata.json "
                             "ve vývojovém režimu (výchozí .work)")


def prevzit(argv):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv prevzit",
        description="Převezme _metadata.json z pracovního adresáře do "
                    "složek akcí v archivu (jen kde ještě nejsou).")
    common(parser)
    archiv, work = paths(parser.parse_args(argv))
    adopted, skipped = adopt(archiv, work)
    for name, _ in adopted:
        print(f"převzato: {name}")
    for name, reason in skipped:
        print(f"přeskočeno: {name} ({reason})")
    print(f"Převzato {len(adopted)}, přeskočeno {len(skipped)}.")


def exportovat(argv):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv exportovat",
        description="Zapíše XMP sidecary zadané akce, nebo všech akcí "
                    "s _metadata.json (jen chybějící a změněné), a "
                    "přegeneruje index archivu. Zámky akcí nekontroluje.")
    common(parser)
    parser.add_argument("akce", nargs="?",
                        help="název složky akce (bez něj všechny)")
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="produkční režim: sidecary vedle souborů "
                             "v archivu (jinak do pracovního adresáře)")
    parser.add_argument("--obliceje", action="store_true",
                        help="obnova Immiche: přidá oblasti pojmenovaných "
                             "obličejů (MWG); záznam o exportu nemění, "
                             "běžný export pak sidecary vrátí")
    args = parser.parse_args(argv)
    archiv, work = paths(args)
    ws = Workspace(archiv, work, args.zapis_do_archivu)
    if args.akce:
        try:
            ws.event_dir(args.akce)
        except KeyError:
            sys.exit(f"Akce nenalezena: {args.akce}")
    failed = False
    for name in [args.akce] if args.akce else ws.event_names():
        try:
            result = xmp.export(ws, name, obliceje=args.obliceje)
        except Collision:
            print(f"přeskočeno: {name} (složka s příponou .ignored i bez "
                  "ní)")
            failed = True
            continue
        if result is None:
            print(f"přeskočeno: {name} (bez _metadata.json)")
            continue
        print(f"{name}: zapsáno {result['zapsano']}, nezměněno "
              f"{result['nezmeneno']}, selhalo {len(result['chyby'])}")
        for error in result["chyby"]:
            print(f"  {error['soubor']}: {error['chyba']}")
        failed = failed or bool(result["chyby"])
    warnings = index.write(ws)
    for warning in warnings:
        print(f"varování: {warning}")
    if not warnings:
        print(f"index: {index.target_dir(ws)}")
    if failed:
        sys.exit(1)


def skryt(argv):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv skryt",
        description="Skryje nedokončené akce před Immichem: přidá jejich "
                    "složkám příponu .ignored (odebere ji dokončení akce). "
                    "Bez --zapis-do-archivu jen vypíše, co by přejmenoval. "
                    "Spouštět, když server neběží.")
    common(parser)
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="složky v archivu opravdu přejmenovat")
    args = parser.parse_args(argv)
    archiv, work = paths(args)
    ws = Workspace(archiv, work, zapis=True)
    hidden, collisions, failed = 0, 0, False
    for event in ws.list_events():
        name = event["nazev"]
        if event["stav"] == "kolize":
            print(f"přeskočeno: {name} (složka s příponou .ignored i bez ní)")
            collisions += 1
            continue
        if event["stav"] == "hotovo" or ws.is_hidden(name):
            continue
        if not args.zapis_do_archivu:
            print(f"skryje: {name}")
            hidden += 1
            continue
        try:
            ws.hide(name)
        except (OSError, Collision) as e:
            print(f"selhalo: {name}: {e}")
            failed = True
            continue
        print(f"skryto: {name}")
        hidden += 1
    verb = "Skryto" if args.zapis_do_archivu else "Ke skrytí"
    print(f"{verb}: {hidden}, kolizí: {collisions}")
    if not args.zapis_do_archivu and hidden:
        print("Archiv beze změny; přejmenuje až --zapis-do-archivu.")
    if failed:
        sys.exit(1)


def _lost_authors(doc):
    """Počet souborů, které mají autory jen z `akce.autori` (po převodu
    na /2 budou bez autorů)."""
    if not (doc.get("akce") or {}).get("autori"):
        return 0
    groups = doc.get("skupiny") or {}
    return sum(
        1 for record in (doc.get("soubory") or {}).values()
        if not record.get("autori")
        and not (groups.get(record.get("skupina")) or {}).get("autori"))


def migrovat(argv):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv migrovat",
        description="Převede _metadata.json akcí v archivu ze schématu /1 "
                    "na /2 (odebere autory celé akce, starší osoby a datum "
                    "od/do u skupiny). Bez --zapis-do-archivu jen vypíše, "
                    "co by změnil. Spouštět, když server neběží.")
    common(parser)
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="_metadata.json v archivu opravdu přepsat")
    args = parser.parse_args(argv)
    archiv, work = paths(args)
    ws = Workspace(archiv, work, zapis=True)
    count, failed = 0, False
    for event in ws.list_events():
        name = event["nazev"]
        if event["stav"] == "kolize":
            print(f"přeskočeno: {name} (složka s příponou .ignored i bez ní)")
            continue
        path = ws.metadata_path(name)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            continue
        try:
            doc = json.loads(data)
        except ValueError as e:
            print(f"selhalo: {name}: {e}")
            failed = True
            continue
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_V1:
            continue
        lost = _lost_authors(doc)
        removed = upgrade(doc)
        detail = ", ".join(f"{k} {n}" for k, n in sorted(removed.items()))
        note = f" ({detail})" if detail else ""
        if lost:
            note += f"; souborů, které ztratí autory celé akce: {lost}"
        if not args.zapis_do_archivu:
            print(f"převede: {name}{note}")
            count += 1
            continue
        version = version_of(data)
        exported = ws.export_version(name) == version
        try:
            new = ws.save(name, doc, version)
            # Sidecary převod nemění, pokud akce neměla autory celé akce
            # (jiné vypuštěné klíče se do nich nedostanou).
            if exported and "akce.autori" not in removed:
                xmp.write_atomic(ws.export_record_path(name), json.dumps(
                    {"version": new, "zapis": ws.zapis}).encode("utf-8"))
        except Conflict:
            print(f"selhalo: {name}: soubor se mezitím změnil")
            failed = True
            continue
        except OSError as e:
            print(f"selhalo: {name}: {e}")
            failed = True
            continue
        print(f"převedeno: {name}{note}")
        count += 1
    verb = "Převedeno" if args.zapis_do_archivu else "K převodu"
    print(f"{verb}: {count}")
    if not args.zapis_do_archivu and count:
        print("Archiv beze změny; převede až --zapis-do-archivu.")
    if failed:
        sys.exit(1)


def check_users(work):
    """Chybný `uzivatele.json` (dřívější `admin`, neznámá role) zastaví
    start: tiché ignorování by z admina udělalo běžného uživatele."""
    message = auth.problems_message(auth.Users(work))
    if message:
        sys.exit(message)


def heslo(argv):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv heslo",
        description="Vydá uživateli z uzivatele.json jednorázové heslo "
                    "(úvodní nebo zapomenuté); po přihlášení ho musí "
                    "změnit. Stávající relace uživatele skončí.")
    parser.add_argument("login")
    parser.add_argument("--work", default=".work",
                        help="pracovní adresář (výchozí .work)")
    args = parser.parse_args(argv)
    work = Path(args.work)
    if not (work / "uzivatele.json").is_file():
        sys.exit(f"Chybí {work / 'uzivatele.json'}.")
    check_users(work)
    password = auth.Auth(work).issue(args.login)
    if password is None:
        sys.exit(f"Login {args.login} není v {work / 'uzivatele.json'}.")
    print(f"Jednorázové heslo pro {args.login.strip().lower()}: {password}")


def migrate_contact(work, kontakt):
    """Zastaralý `--kontakt`: převezme ho do nominatim.json, je-li prázdné."""
    if not kontakt:
        return
    settings = geocode.Contact(work)
    if settings.load() is None:
        settings.save(kontakt)
        print("Přepínač --kontakt je zastaralý; kontakt pro Nominatim "
              f"převzat do {settings.path}, dál se nastavuje v aplikaci.")
    else:
        print("Přepínač --kontakt je zastaralý a ignoruje se; kontakt pro "
              "Nominatim se nastavuje v aplikaci.")


STAV_TEXT = {integrity.SUSPECT: "PODEZŘELÝ", integrity.UNREADABLE: "NEČITELNÝ"}

# Druhy nálezů konzistence akce (issue #11) s textem pro výpis.
NALEZ_TEXT = {
    "nepodporovany": "nepodporovaný soubor",
    "sirotek_xmp": "osiřelý sidecar",
    "raw": "RAW v kořeni",
    "podslozka": "podsložka bez .ignored",
    "chybejici": "záznam bez souboru",
}


def _event_folders(ws, name):
    """[(složka, název cache)]; při kolizi obě složky (příkaz jen čte)."""
    try:
        folder = ws.event_dir(name)
        return [(folder, event_name(folder))]
    except Collision:
        return [(ws.archiv / n, n) for n in (name, name + IGNORED)]


def _write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.replace(tmp, path)


def _opravit_nalezy(ws, name, nalezy):
    """U akce s nálezy s nápravou navrhne úklid a po potvrzení ho provede.

    Podsložky bez volby se nemění, označené soubory (vyřazení) taky ne —
    ty patří na pracovní plochu. Nic se nepřepisuje.
    """
    from . import cleanup  # lazy: cleanup importuje archive
    if not any(n["druh"] in (consistency.NEPODPOROVANY,
                             consistency.SIROTEK_XMP, consistency.RAW)
               for n in nalezy):
        return
    folder = ws.event_dir(name)
    volby = {f["nazev"]: None for f in cleanup.subfolders(folder)}
    plan = cleanup.plan(folder, volby, True, (), True)
    todo = [o for o in plan["operace"] if not o["blocked"]]
    print("  náprava: " + ("; ".join(
        f"{cleanup.OPS_TEXT.get(o['typ'], o['typ'])} {o['z']} → {o['do']}"
        for o in todo) or "všechno je blokované"))
    odp = input("  Provést? [ne/aNo] ")
    if odp.strip().lower() not in ("a", "ano", "y", "yes"):
        print("  přeskočeno")
        return
    result = cleanup.execute(folder, volby, True, (), True)
    counts = Counter(o["stav"] for o in result["operace"])
    print(f"  hotovo {counts.get(cleanup.DONE, 0)}, "
          f"blokováno {counts.get(cleanup.BLOCKED, 0)}, "
          f"chyba {counts.get(cleanup.FAILED, 0)}")


def zkontrolovat(argv):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv zkontrolovat",
        description="Zkontroluje, zda soubory akce (média v kořeni, RAWy "
                    "v kořeni a v RAW.ignored) nejsou poškozené: úseky nul "
                    "od 64 KiB, dekódování fotky, ffprobe u videa. U každé "
                    "akce vypíše i nálezy kontroly konzistence "
                    "(nepodporované soubory, osiřelé sidecary, RAWy, "
                    "podsložky, záznamy bez souboru). Archiv jen čte; "
                    "výsledky cachuje v pracovním adresáři a report uloží "
                    "do <work>/kontrola/. S --zapis-do-archivu po potvrzení "
                    "převede nálezy s nápravou do .ignored složek.")
    common(parser)
    parser.add_argument("akce", nargs="?",
                        help="název složky akce (bez něj všechny)")
    parser.add_argument("--rychle", action="store_true",
                        help="jen konzistence akcí (výpis kořene "
                             "a _metadata.json), obsah souborů se nečte")
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="u akcí s nálezy navrhne nápravu přesuny "
                             "a po potvrzení ji provede")
    args = parser.parse_args(argv)
    archiv, work = paths(args)
    # zapis=True jen pro čtení metadat ze složek akcí (jako `skryt`);
    # samotný příkaz archiv nemění, ledaže uživatel potvrdí nápravu.
    ws = Workspace(archiv, work, zapis=True)
    if args.zapis_do_archivu and args.rychle:
        sys.exit("--zapis-do-archivu a --rychle nejde kombinovat.")
    if args.akce:
        try:
            _event_folders(ws, args.akce)
        except KeyError:
            sys.exit(f"Akce nenalezena: {args.akce}")
    if not shutil.which("ffprobe"):
        print("varování: chybí ffprobe, videa se ověří jen testem nul",
              file=sys.stderr)
    names = [args.akce] if args.akce else ws.event_names()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = Path(work) / "kontrola" / f"report-{stamp}.json"
    n = 1
    while path.exists():  # dva běhy v téže sekundě report nepřepíšou
        n += 1
        path = Path(work) / "kontrola" / f"report-{stamp}-{n}.json"
    report = {"archiv": str(ws.archiv), "zacatek": stamp,
              "prah_bajtu": None if args.rychle else integrity.THRESHOLD,
              "rychle": args.rychle, "dokonceno": False, "akce": []}
    totals = Counter()
    tty = sys.stderr.isatty()
    try:
        for i, name in enumerate(names, 1):
            for folder, cache_name in _event_folders(ws, name):
                label = folder.name
                # Nálezy konzistence: jen výpis kořene a _metadata.json
                # (issue #11). Při kolizi se nezdaří event_dir — vezme se
                # metadata ve složce, když je.
                try:
                    doc, _ = ws.load(event_name(folder))
                except Collision:  # obě složky: metadata vezmi z ní
                    path = folder / METADATA_NAME
                    try:
                        doc = json.loads(path.read_text())
                    except (OSError, ValueError):
                        doc = None
                except (OSError, ValueError):
                    doc = None
                nalezy = consistency.check(folder, doc)
                report_nalezy = [dict(n) for n in nalezy]
                if nalezy:
                    print(f"{label}: konzistence: " + "; ".join(
                        f"{NALEZ_TEXT[n['druh']]} {n['nazev']}"
                        for n in nalezy))
                if args.rychle:
                    totals["akci"] += 1
                    report["akce"].append({"akce": label,
                                           "nalezy": report_nalezy})
                    _write_report(path, report)
                    continue
                if args.zapis_do_archivu:
                    _opravit_nalezy(ws, name, nalezy)
                todo = integrity.event_files(folder)
                print(f"[{i}/{len(names)}] {label}: "
                      f"{len(todo)} souborů", file=sys.stderr)
                gen = integrity.iter_check_files(
                    todo, Path(work) / "cache" / "kontrola" /
                    f"{cache_name}.json")
                total = None
                while True:
                    try:
                        ev = next(gen)
                    except StopIteration as stop:
                        results = stop.value
                        break
                    if ev["typ"] == "kontrola":
                        total = ev
                    elif tty and total["bajtu"]:
                        print(f"\r  {ev['hotovo_souboru']}/"
                              f"{total['souboru']} souborů, "
                              f"{100 * ev['hotovo_bajtu'] // total['bajtu']} "
                              "%", end="", file=sys.stderr)
                if tty and todo:
                    print(file=sys.stderr)
                counts = Counter(r["stav"] for r in results.values())
                totals.update(counts)
                totals["akci"] += 1
                files = []
                for key in sorted(results):
                    r = results[key]
                    if r["stav"] != integrity.OK:
                        print(f"{label}/{key}: {STAV_TEXT[r['stav']]}: "
                              + "; ".join(r["duvody"]))
                    if r["stav"] != integrity.OK or r["nuly"] \
                            or r.get("nuly_soubor") or r.get("poznamka"):
                        files.append(dict(r, soubor=key))
                report["akce"].append({
                    "akce": label, "souboru": len(results),
                    "ok": counts[integrity.OK],
                    "podezrele": counts[integrity.SUSPECT],
                    "necitelne": counts[integrity.UNREADABLE],
                    "nalezy": report_nalezy,
                    "soubory": files})
                # Report po každé akci: přerušení nechá rozpracovaný.
                _write_report(path, report)
    except KeyboardInterrupt:
        report["preruseno"] = True
        _write_report(path, report)
        print(f"\nPřerušeno. Report: {path}", file=sys.stderr)
        sys.exit(130)
    report["dokonceno"] = True
    _write_report(path, report)
    if args.rychle:
        nalez = sum(len(a["nalezy"]) for a in report["akce"])
        print(f"Zkontrolováno {totals['akci']} akcí: nálezů konzistence "
              f"{nalez}.")
        print(f"report: {path}")
        return
    souboru = sum(a["souboru"] for a in report["akce"])
    print(f"Zkontrolováno {souboru} souborů v {totals['akci']} akcích: "
          f"podezřelých {totals[integrity.SUSPECT]}, "
          f"nečitelných {totals[integrity.UNREADABLE]}.")
    print(f"report: {path}")


def serve(app, host, port, threads):
    """Produkční WSGI server cheroot: jeden proces, `threads` vláken.

    Tělo požadavku čte průběžně ze spojení (upload importu bez
    mezibufferu) a odpověď posílá po kusech (NDJSON průběh).
    """
    server = wsgi.Server((host, port), app, numthreads=threads)
    print(f"Server: http://{host}:{port} ({threads} vláken)", flush=True)
    try:
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["prevzit"]:
        return prevzit(argv[1:])
    if argv[:1] == ["exportovat"]:
        return exportovat(argv[1:])
    if argv[:1] == ["heslo"]:
        return heslo(argv[1:])
    if argv[:1] == ["zkontrolovat"]:
        return zkontrolovat(argv[1:])
    if argv[:1] == ["skryt"]:
        return skryt(argv[1:])
    if argv[:1] == ["migrovat"]:
        return migrovat(argv[1:])
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv",
        description="Průvodce metadaty fotoarchivu. Převzetí metadat "
                    "z pracovního adresáře: python -m fotoarchiv prevzit, "
                    "export XMP: python -m fotoarchiv exportovat, "
                    "jednorázové heslo: python -m fotoarchiv heslo, "
                    "skrytí nedokončených akcí před Immichem: "
                    "python -m fotoarchiv skryt, kontrola poškozených "
                    "souborů: python -m fotoarchiv zkontrolovat, převod "
                    "na schéma /2: python -m fotoarchiv migrovat.")
    common(parser)
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="produkční režim: _metadata.json ve složkách "
                             "akcí, úklid se provádí")
    parser.add_argument("--bez-prihlaseni", action="store_true",
                        help="vývojový režim bez přihlášení (každý je "
                             "admin); s --zapis-do-archivu nejde")
    parser.add_argument("--https", action="store_true",
                        help="cookie relace jen přes HTTPS (za reverzní "
                             "proxy s HTTPS)")
    # Zastaralé: kontakt pro Nominatim se nastavuje v aplikaci.
    parser.add_argument("--kontakt", help=argparse.SUPPRESS)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--vlakna", type=int, default=32,
                        help="počet obslužných vláken serveru (výchozí 32)")
    parser.add_argument("--debug", action="store_true",
                        help="vývojový server Werkzeugu s reloaderem")
    args = parser.parse_args(argv)
    if args.vlakna < 1:
        parser.error("--vlakna musí být aspoň 1")
    if args.zapis_do_archivu and args.bez_prihlaseni:
        sys.exit("Produkční režim (--zapis-do-archivu) bez přihlášení "
                 "nejde spustit.")

    archiv, work = paths(args)
    if not args.bez_prihlaseni:
        check_users(work)
    work.mkdir(parents=True, exist_ok=True)
    migrate_contact(work, args.kontakt)
    # Provedené operace úklidu jdou do logu serveru.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    removed = importer.Imports(work).purge()
    if removed:
        print(f"Smazané importy neaktivní přes 7 dní: {len(removed)}")

    # Pod --debug běží hlídací proces reloaderu (bez WERKZEUG_RUN_MAIN)
    # a obslužný podproces; synchronizace Immiche jen v obslužném.
    watcher = args.debug and not os.environ.get("WERKZEUG_RUN_MAIN")
    app = create_app(archiv, work, zapis=args.zapis_do_archivu,
                     immich_interval=None if watcher else immich.INTERVAL,
                     prihlaseni=not args.bez_prihlaseni, https=args.https)
    print(f"Archiv: {archiv.resolve()}")
    print(f"Pracovní adresář: {work.resolve()}")
    if args.zapis_do_archivu:
        print("Režim: PRODUKČNÍ — metadata a úklid zapisují do archivu.")
    else:
        print("Režim: vývojový — do archivu se nezapisuje.")
    if args.bez_prihlaseni:
        print("Přihlášení vypnuto — každý je admin.")
    elif not auth.Users(work).path.is_file():
        print(f"Varování: chybí {work / 'uzivatele.json'}, nikdo se "
              "nepřihlásí.")
    if geocode.Contact(work).load() is None:
        print("Geokódování míst vypnuto (kontakt nastaví admin "
              "v aplikaci).")
    # Zámek akcí je v paměti: server smí běžet jen jako jeden proces.
    if args.debug:
        app.run(host=args.host, port=args.port, debug=True, threaded=True)
    else:
        serve(app, args.host, args.port, args.vlakna)


if __name__ == "__main__":
    main()
