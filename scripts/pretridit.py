"""Jednorázové zplošťování a deduplikace složky `přetřídit` (issue #5).

Jen standardní knihovna, aby běžel i na serveru u archivu. Postup:

    plan      mapa přesunů + sha256 → plan.csv (nic nemění)
    provest   provede plan.csv, každý krok zapíše do logu
    zpet      vrátí kroky z logu v opačném pořadí
    kontrola  porovná sha256 před a po (stejný multiset obsahů)

Nic se nemaže: duplicity jdou do `_duplicity.ignored/<původní cesta>`,
existující soubor se nikdy nepřepíše. Hashe ve formátu `sha256sum`
s cestami relativními ke kořeni `přetřídit` (`./…` nebo bez tečky).
"""

import argparse
import collections
import csv
import os
import sys
from pathlib import PurePosixPath

DUPLICITY = "_duplicity.ignored"
SKIP = {"thumbs.db"}
PLAN_FIELDS = ["akce", "zdroj", "cil", "sha256", "velikost", "duvod"]
LOG_FIELDS = ["akce", "zdroj", "cil"]


def read_sha(path):
    """{relativní cesta: sha256} ze souboru `sha256sum`."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            digest, rel = line.rstrip("\n").split("  ", 1)
            out[rel[2:] if rel.startswith("./") else rel] = digest
    return out


def read_mapa(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return [(r["zdroj"].strip("/"), r["cil"].strip("/")) for r in rows]


def walk(koren):
    """Relativní cesty souborů pod kořenem kromě Thumbs.db a duplicit."""
    for top, dirs, files in os.walk(koren):
        rel_top = os.path.relpath(top, koren)
        if rel_top == ".":
            dirs[:] = [d for d in dirs if d != DUPLICITY]
        for name in files:
            if name.lower() not in SKIP:
                yield os.path.normpath(os.path.join(rel_top, name))


def mapped(rel, mapa):
    """Cílová cesta podle nejdelšího odpovídajícího `zdroj`."""
    best = None
    for zdroj, cil in mapa:
        if rel == zdroj or rel.startswith(zdroj + "/"):
            if best is None or len(zdroj) > len(best[0]):
                best = (zdroj, cil)
    if best is None:
        return rel
    return best[1] + rel[len(best[0]):]


def free_name(path, taken):
    p = PurePosixPath(path)
    n = 2
    while True:
        cand = str(p.with_name(f"{p.stem}_{n}{p.suffix}"))
        if cand not in taken:
            return cand
        n += 1


def make_plan(koren, sha, mapa, archiv_sha=None):
    """Řádky plánu a seznam obsahů sdílených víc složkami kořene."""
    files = sorted(walk(koren))
    missing = [f for f in files if f not in sha]
    if missing:
        raise SystemExit(f"bez sha256: {len(missing)} souborů, např. "
                         f"{missing[:3]}")
    in_archive = collections.defaultdict(list)
    for rel, digest in (archiv_sha or {}).items():
        in_archive[digest].append(rel)

    target = {f: mapped(f, mapa) for f in files}
    groups = collections.defaultdict(list)  # (složka kořene, sha) → soubory
    for f in files:
        groups[(target[f].split("/", 1)[0], sha[f])].append(f)

    def keep_order(f):
        # Nepřesouvaný soubor má přednost, pak mělčí cesta, pak abecedně.
        return (target[f] != f, target[f].count("/"), target[f])

    rows, keep = [], []
    for (_, digest), members in groups.items():
        members.sort(key=keep_order)
        if digest in in_archive:
            why = "v archivu: " + in_archive[digest][0]
            dups = members
        else:
            keep.append(members[0])
            why = "stejný obsah: " + target[members[0]]
            dups = members[1:]
        for f in dups:
            rows.append(["duplicita", f, f"{DUPLICITY}/{f}", digest, why])

    # Kolize jmen mezi ponechanými (stejné jméno, jiný obsah).
    taken = set()
    for f in sorted(keep, key=keep_order):
        dst = target[f]
        if dst in taken:
            new = free_name(dst, taken)
            rows.append(["prejmenovat", f, new, sha[f],
                         "jméno obsazené jiným obsahem: " + dst])
            dst = new
        elif dst != f:
            rows.append(["presun", f, dst, sha[f], ""])
        taken.add(dst)

    for row in rows:
        row.insert(4, os.path.getsize(os.path.join(koren, row[1])))
    rows.sort(key=lambda r: (r[0], r[1]))

    roots = collections.defaultdict(set)
    for f in keep:
        roots[sha[f]].add(target[f].split("/", 1)[0])
    shared = sorted((d, sorted(r)) for d, r in roots.items() if len(r) > 1)
    return rows, shared


def execute(koren, plan_rows, log_path):
    """Provede plán; zastaví se na první chybě. Vrací počet kroků."""
    done = 0
    with open(log_path, "a", encoding="utf-8", newline="") as log:
        writer = csv.writer(log, delimiter=";")
        if log.tell() == 0:
            writer.writerow(LOG_FIELDS)
        sources = set()
        for row in plan_rows:
            src = os.path.join(koren, row["zdroj"])
            dst = os.path.join(koren, row["cil"])
            if os.path.getsize(src) != int(row["velikost"]):
                raise SystemExit(f"změněná velikost: {row['zdroj']}")
            parent = os.path.dirname(dst)
            created = []
            probe = parent
            while not os.path.isdir(probe):
                created.append(probe)
                probe = os.path.dirname(probe)
            for d in reversed(created):
                os.mkdir(d)
                writer.writerow(["mkdir", "", os.path.relpath(d, koren)])
            # os.rename na Linuxu cíl přepíše: kontrola těsně před ním.
            if os.path.lexists(dst):
                raise SystemExit(f"cíl existuje: {row['cil']}")
            os.rename(src, dst)
            writer.writerow([row["akce"], row["zdroj"], row["cil"]])
            log.flush()
            os.fsync(log.fileno())
            sources.add(os.path.dirname(row["zdroj"]))
            done += 1
        # Prázdné zdrojové složky (Thumbs.db složku drží, ta zůstane).
        for rel in sorted(sources, key=lambda p: -p.count("/")):
            while rel:
                try:
                    os.rmdir(os.path.join(koren, rel))
                except OSError:
                    break
                writer.writerow(["rmdir", "", rel])
                rel = os.path.dirname(rel)
    return done


def undo(koren, log_path):
    with open(log_path, encoding="utf-8", newline="") as f:
        steps = list(csv.DictReader(f, delimiter=";"))
    for step in reversed(steps):
        if step["akce"] == "rmdir":
            os.makedirs(os.path.join(koren, step["cil"]), exist_ok=True)
        elif step["akce"] == "mkdir":
            os.rmdir(os.path.join(koren, step["cil"]))
        else:
            src = os.path.join(koren, step["zdroj"])
            if os.path.lexists(src):
                raise SystemExit(f"zdroj existuje: {step['zdroj']}")
            os.rename(os.path.join(koren, step["cil"]), src)
    return len(steps)


def compare(before, after):
    """Rozdíl multisetů obsahů (prázdné = nic se neztratilo ani nepřibylo)."""
    a = collections.Counter(before.values())
    b = collections.Counter(after.values())
    return a - b, b - a


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("plan")
    s.add_argument("--koren", required=True)
    s.add_argument("--sha", required=True)
    s.add_argument("--mapa", required=True)
    s.add_argument("--archiv-sha", help="sha256 akcí archivu; shodné soubory jdou do duplicit")
    s.add_argument("--vystup", required=True)
    s = sub.add_parser("provest")
    s.add_argument("--koren", required=True)
    s.add_argument("--plan", required=True)
    s.add_argument("--log", required=True)
    s = sub.add_parser("zpet")
    s.add_argument("--koren", required=True)
    s.add_argument("--log", required=True)
    s = sub.add_parser("kontrola")
    s.add_argument("--pred", required=True)
    s.add_argument("--po", required=True)
    args = p.parse_args(argv)

    if args.cmd == "plan":
        rows, shared = make_plan(
            args.koren, read_sha(args.sha), read_mapa(args.mapa),
            read_sha(args.archiv_sha) if args.archiv_sha else None)
        with open(args.vystup, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(PLAN_FIELDS)
            w.writerows(rows)
        counts = collections.Counter(r[0] for r in rows)
        print(", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        print(f"obsah ve víc složkách kořene (nepřesouvá se): {len(shared)}")
        for digest, roots in shared:
            print(f"  {digest[:12]}  {' | '.join(roots)}")
    elif args.cmd == "provest":
        with open(args.plan, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        print(f"provedeno {execute(args.koren, rows, args.log)} kroků")
    elif args.cmd == "zpet":
        print(f"vráceno {undo(args.koren, args.log)} kroků")
    else:
        lost, extra = compare(read_sha(args.pred), read_sha(args.po))
        print(f"chybí {sum(lost.values())}, navíc {sum(extra.values())}")
        return 1 if lost or extra else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
