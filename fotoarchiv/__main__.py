"""Spuštění: python -m fotoarchiv --archiv CESTA [--work .work]
[--zapis-do-archivu], převzetí: python -m fotoarchiv prevzit --archiv …,
export XMP: python -m fotoarchiv exportovat [AKCE] --archiv …,
jednorázové heslo: python -m fotoarchiv heslo LOGIN --work …."""

import argparse
import logging
import sys
from pathlib import Path

from . import auth, geocode, immich, importer, index, xmp
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
        result = xmp.export(ws, name, obliceje=args.obliceje)
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["prevzit"]:
        return prevzit(argv[1:])
    if argv[:1] == ["exportovat"]:
        return exportovat(argv[1:])
    if argv[:1] == ["heslo"]:
        return heslo(argv[1:])
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv",
        description="Průvodce metadaty fotoarchivu. Převzetí metadat "
                    "z pracovního adresáře: python -m fotoarchiv prevzit, "
                    "export XMP: python -m fotoarchiv exportovat, "
                    "jednorázové heslo: python -m fotoarchiv heslo.")
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
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    if args.zapis_do_archivu and args.bez_prihlaseni:
        sys.exit("Produkční režim (--zapis-do-archivu) bez přihlášení "
                 "nejde spustit.")

    archiv, work = paths(args)
    work.mkdir(parents=True, exist_ok=True)
    migrate_contact(work, args.kontakt)
    # Provedené operace úklidu jdou do logu serveru.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    removed = importer.Imports(work).purge()
    if removed:
        print(f"Smazané importy neaktivní přes 7 dní: {len(removed)}")

    app = create_app(archiv, work, zapis=args.zapis_do_archivu,
                     immich_interval=immich.INTERVAL,
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
    app.run(host=args.host, port=args.port, debug=args.debug,
            threaded=True)


if __name__ == "__main__":
    main()
