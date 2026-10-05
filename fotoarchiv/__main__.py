"""Spuštění: python -m fotoarchiv --archiv CESTA [--work .work]."""

import argparse
import sys
from pathlib import Path

from .app import create_app


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m fotoarchiv",
        description="Prototyp průvodce metadaty fotoarchivu.")
    parser.add_argument("--archiv", required=True,
                        help="složka archivu se složkami akcí")
    parser.add_argument("--work", default=".work",
                        help="pracovní adresář pro _metadata.json a cache "
                             "(výchozí .work)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    archiv = Path(args.archiv)
    if not archiv.is_dir():
        sys.exit(f"Archiv nenalezen nebo to není složka: {archiv}")
    work = Path(args.work)
    if work.resolve().is_relative_to(archiv.resolve()):
        sys.exit("Pracovní adresář nesmí ležet v archivu (prototyp do "
                 "archivu nezapisuje).")
    work.mkdir(parents=True, exist_ok=True)

    app = create_app(archiv, work)
    print(f"Archiv: {archiv.resolve()}")
    print(f"Pracovní adresář: {work.resolve()}")
    app.run(host=args.host, port=args.port, debug=args.debug,
            threaded=True)


if __name__ == "__main__":
    main()
