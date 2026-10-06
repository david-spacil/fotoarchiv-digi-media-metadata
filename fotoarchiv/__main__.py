"""Spuštění: python -m fotoarchiv --archiv CESTA [--work .work]
[--zapis-do-archivu], převzetí: python -m fotoarchiv prevzit --archiv …,
export XMP: python -m fotoarchiv exportovat [AKCE] --archiv …."""

import argparse
import logging
import sys
from pathlib import Path

from . import importer, xmp
from .app import create_app
from .archive import Workspace, adopt


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
                    "s _metadata.json (jen chybějící a změněné). Zámky "
                    "akcí nekontroluje.")
    common(parser)
    parser.add_argument("akce", nargs="?",
                        help="název složky akce (bez něj všechny)")
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="produkční režim: sidecary vedle souborů "
                             "v archivu (jinak do pracovního adresáře)")
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
        result = xmp.export(ws, name)
        if result is None:
            print(f"přeskočeno: {name} (bez _metadata.json)")
            continue
        print(f"{name}: zapsáno {result['zapsano']}, nezměněno "
              f"{result['nezmeneno']}, selhalo {len(result['chyby'])}")
        for error in result["chyby"]:
            print(f"  {error['soubor']}: {error['chyba']}")
        failed = failed or bool(result["chyby"])
    if failed:
        sys.exit(1)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["prevzit"]:
        return prevzit(argv[1:])
    if argv[:1] == ["exportovat"]:
        return exportovat(argv[1:])
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv",
        description="Průvodce metadaty fotoarchivu. Převzetí metadat "
                    "z pracovního adresáře: python -m fotoarchiv prevzit, "
                    "export XMP: python -m fotoarchiv exportovat.")
    common(parser)
    parser.add_argument("--zapis-do-archivu", action="store_true",
                        help="produkční režim: _metadata.json ve složkách "
                             "akcí, úklid se provádí")
    parser.add_argument("--kontakt",
                        help="e-mail nebo URL do User-Agent pro Nominatim "
                             "(OSM); bez něj je geokódování míst vypnuté")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    archiv, work = paths(args)
    work.mkdir(parents=True, exist_ok=True)
    # Provedené operace úklidu jdou do logu serveru.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    removed = importer.Imports(work).purge()
    if removed:
        print(f"Smazané importy neaktivní přes 7 dní: {len(removed)}")

    app = create_app(archiv, work, zapis=args.zapis_do_archivu,
                     kontakt=args.kontakt)
    print(f"Archiv: {archiv.resolve()}")
    print(f"Pracovní adresář: {work.resolve()}")
    if args.zapis_do_archivu:
        print("Režim: PRODUKČNÍ — metadata a úklid zapisují do archivu.")
    else:
        print("Režim: vývojový — do archivu se nezapisuje.")
    if not args.kontakt:
        print("Geokódování míst vypnuto (chybí --kontakt).")
    # Zámek akcí je v paměti: server smí běžet jen jako jeden proces.
    app.run(host=args.host, port=args.port, debug=args.debug,
            threaded=True)


if __name__ == "__main__":
    main()
