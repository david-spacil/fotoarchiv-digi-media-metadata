"""Spuštění: `python -m klient` (okno), `--registrovat` /
`--odregistrovat` (menu aplikací)."""

import argparse
import sys

from . import registrace


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="klient", description="Import fotek z telefonu do Fotoarchivu")
    ap.add_argument("--registrovat", action="store_true",
                    help="přidat klienta do menu aplikací")
    ap.add_argument("--odregistrovat", action="store_true",
                    help="odebrat klienta z menu aplikací")
    ap.add_argument("--gvfs", metavar="ADRESAR",
                    help="kořen gvfs místo /run/user/<uid>/gvfs (testování "
                         "bez telefonu)")
    args = ap.parse_args(argv)
    if args.registrovat:
        print(f"Zapsáno: {registrace.registrovat()}")
        return
    if args.odregistrovat:
        print(f"Odebráno: {registrace.odregistrovat()}")
        return

    if sys.platform == "win32":
        raise SystemExit("Zdroj pro Windows zatím není.")
    from PySide6.QtWidgets import QApplication

    from .evidence import Evidence, Konfigurace
    from .gvfs import Gvfs
    from .ui import Okno

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Fotoarchiv – import z telefonu")
    zdroj = Gvfs(args.gvfs, gio=args.gvfs is None)
    okno = Okno(zdroj, Konfigurace(), Evidence())
    okno.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
