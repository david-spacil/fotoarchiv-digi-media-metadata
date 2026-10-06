"""Generovaný index akcí archivu: `_INDEX.html` a `_INDEX.md`.

`collect` sebere záznamy akcí (čistá data) týmiž funkcemi, které používá
aplikace (stav, dědění, soubory kořene), `render_md` a `render_html`
z nich udělají text a `write` oba soubory zapíše, jen když se liší.
Obsah nemá časové razítko, aby opakované generování nesahalo na disk.
"""

import base64
import html
import logging
import urllib.parse
from collections import Counter
from datetime import date

from tabulate import tabulate

from . import model, scan, thumbs, xmp
from .archive import EVENT_RE

NAMES = ("_INDEX.html", "_INDEX.md")
TITLE = "Fotoarchiv ARÚB – index akcí"
STAV = {"nezpracovano": "nezpracováno", "rozpracovano": "rozpracováno",
        "hotovo": "hotovo"}

log = logging.getLogger(__name__)


def short_name(name):
    """`Příjmení, Jméno` → `Příjmení J.`; jméno bez čárky beze změny."""
    prijmeni, comma, krestni = name.partition(",")
    krestni = krestni.strip()
    if not comma or not krestni:
        return name
    return f"{prijmeni.strip()} {krestni[0]}."


def by_count(counter):
    """[(jméno, počet)] sestupně podle počtu, při shodě podle jména."""
    return sorted(counter.items(), key=lambda x: (-x[1], x[0]))


def first_jpeg(media):
    for name, _ in media:
        if scan.extension(name) in ("jpg", "jpeg"):
            return name
    return None


def preview(ws, path):
    """Náhled z cache jako base64, nebo None."""
    try:
        thumb = thumbs.thumbnail(path, ws.work / "cache")
        return base64.b64encode(thumb.read_bytes()).decode() if thumb \
            else None
    except OSError:
        return None


def collect(ws):
    """Záznamy všech akcí archivu, seřazené podle data sestupně."""
    records = []
    for event in ws.list_events():
        name = event["nazev"]
        date_, title = EVENT_RE.match(name).groups()
        media, _ = scan.root_files(ws.archiv / name)
        video = sum(scan.is_video(n) for n, _ in media)
        jpeg = first_jpeg(media)
        record = {
            "slozka": name, "stav": event["stav"],
            "datum_od": date_, "datum_do": date_, "nazev": title,
            "popis": "", "mista_akce": [], "mista": [], "autori": [],
            "ucastnici": [], "osoby": [], "pristroje": [],
            "foto": len(media) - video, "video": video,
            "nahled": preview(ws, ws.archiv / name / jpeg) if jpeg else None,
        }
        doc, _ = ws.load(name)
        if doc is not None:
            record.update(details(doc))
            record["nazev"] = record["nazev"] or title
            record["datum_od"] = record["datum_od"] or date_
            record["datum_do"] = record["datum_do"] or record["datum_od"]
        records.append(record)
    return records


def details(doc):
    """Údaje akce z `_metadata.json`; autoři, místa a přístroje
    z výsledných (zděděných) hodnot souborů."""
    akce = doc.get("akce") or {}
    authors, faces = Counter(), Counter()
    places, devices = set(), set()
    for filename, record in (doc.get("soubory") or {}).items():
        values = model.resolve(doc, filename)
        for author in set((values.get("autori") or {}).get("hodnota")
                          or []):
            authors[author] += 1
        place = (values.get("misto") or {}).get("hodnota")
        if place:
            places.add(place)
        device = (values.get("pristroj") or {}).get("hodnota")
        if device:
            devices.add(device)
        for face in record.get("obliceje") or []:
            faces[face["jmeno"]] += 1
    mista_akce = list(akce.get("mista") or [])
    return {
        "nazev": akce.get("nazev") or "",
        "datum_od": akce.get("datum_od") or "",
        "datum_do": akce.get("datum_do") or "",
        "popis": akce.get("popis") or "",
        "mista_akce": mista_akce,
        "mista": mista_akce + sorted(places - set(mista_akce)),
        "autori": by_count(authors),
        "ucastnici": list(akce.get("ucastnici") or []),
        "osoby": by_count(faces),
        "pristroje": sorted(devices),
    }


def authors_text(record):
    return "; ".join(short_name(name) for name, _ in record["autori"])


# --- Markdown ------------------------------------------------------------

MD_HEADER = f"""# {TITLE}

> **Generováno automaticky, neupravovat.** Ruční úpravy se při dalším
> generování přepíšou. Údaje se opravují v aplikaci Fotoarchiv (zdroj:
> `_metadata.json` ve složce akce).

"""


def render_md(records):
    rows = [[r["datum_od"], r["nazev"], "; ".join(r["mista_akce"]),
             authors_text(r), r["foto"], r["video"]] for r in records]
    table = tabulate(rows, ["Datum", "Akce", "Místa", "Fotili", "Foto",
                            "Video"], tablefmt="fancy_grid",
                     disable_numparse=True,
                     colalign=("left",) * 4 + ("right",) * 2)
    return MD_HEADER + table + "\n"


# --- HTML ----------------------------------------------------------------

def date_text(od, do):
    """Datum akce česky: `8. 9. 2026`, `8.–10. 9. 2026`,
    `30. 9. – 2. 10. 2026`, přes rok s rokem u obou."""
    try:
        a = date.fromisoformat(od)
        b = date.fromisoformat(do or od)
    except ValueError:
        return od
    if a == b:
        return f"{a.day}. {a.month}. {a.year}"
    if (a.year, a.month) == (b.year, b.month):
        return f"{a.day}.–{b.day}. {b.month}. {b.year}"
    if a.year == b.year:
        return f"{a.day}. {a.month}. – {b.day}. {b.month}. {b.year}"
    return f"{a.day}. {a.month}. {a.year} – {b.day}. {b.month}. {b.year}"


def card(r, href):
    e = html.escape
    href = e(href)
    img = (f'<img src="data:image/jpeg;base64,{r["nahled"]}" alt="">'
           if r["nahled"] else '<div class="noimg">bez náhledu</div>')
    head = (f'<a class="foto" href="{href}">{img}</a>\n'
            f'<div class="text"><p class="kdy">'
            f'{e(date_text(r["datum_od"], r["datum_do"]))}'
            f' <span class="stav">{STAV[r["stav"]]}</span></p>\n'
            f'<h3><a href="{href}">{e(r["nazev"])}</a></h3>')
    rozsah = f'foto {r["foto"]} · video {r["video"]}'
    if r["pristroje"]:
        rozsah += " · " + e(", ".join(r["pristroje"]))
    rows = [(k, e(v)) for k, v in (
        ("Kde", "; ".join(r["mista"])),
        ("Fotili", authors_text(r)),
        ("Účastníci", "; ".join(map(short_name, r["ucastnici"]))),
    ) if v]
    if r["osoby"]:
        rows.append(("Na fotkách", "; ".join(
            f"{e(short_name(n))} <small>{c}×</small>"
            for n, c in r["osoby"])))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    body = (f'<p class="popis">{e(r["popis"])}</p>' if r["popis"] else "")
    body += f"\n<dl>{dl}</dl>" if dl else ""
    compact = " kompakt" if r["stav"] == "nezpracovano" else ""
    return (f'<article class="karta{compact}" '
            f'data-rok="{e(r["datum_od"][:4])}" data-stav="{r["stav"]}">\n'
            f'{head}{body}\n<p class="rozsah">{rozsah}</p></div></article>')


HTML_HEAD = """<!doctype html>
<html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<!--
  GENEROVÁNO AUTOMATICKY – NEUPRAVOVAT.
  Ruční úpravy se při dalším generování přepíšou. Zdrojem údajů je
  _metadata.json ve složce akce; opravy patří do aplikace Fotoarchiv.
-->
<style>
:root { --bg:#f6f3ee; --fg:#22201c; --mut:#6d675d; --line:#ddd6ca;
  --card:#fffdf9; --acc:#2f5d62; color-scheme:light dark }
@media (prefers-color-scheme: dark) { :root { --bg:#1b1a18;
  --fg:#ece7de; --mut:#a39b8e; --line:#38342e; --card:#24221f;
  --acc:#8cc3c7 } }
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.5 system-ui, "Segoe UI", sans-serif }
header, main { max-width:68rem; margin:0 auto; padding:0 1rem }
header { padding-top:2rem }
h1 { font:600 1.9rem/1.2 Georgia, "Times New Roman", serif; margin:0 }
.sub { color:var(--mut); margin:.3rem 0 1.2rem }
.filtry { display:flex; gap:.5rem; flex-wrap:wrap; margin-bottom:1.5rem }
.filtry[hidden] { display:none }
.filtry input, .filtry select { font:inherit; padding:.35rem .6rem;
  border:1px solid var(--line); border-radius:4px; background:var(--card);
  color:var(--fg) }
.filtry input { flex:1; min-width:12rem }
.karta { display:grid; grid-template-columns:200px 1fr; gap:1.2rem;
  background:var(--card); border:1px solid var(--line); border-radius:6px;
  padding:1rem; margin-bottom:1rem }
.karta[hidden] { display:none }
.karta.kompakt { opacity:.75; grid-template-columns:110px 1fr;
  padding:.6rem 1rem }
.foto img, .noimg { width:100%; aspect-ratio:4/3; object-fit:cover;
  border-radius:3px; display:block; background:var(--line) }
.noimg { display:grid; place-items:center; color:var(--mut);
  font-size:.8rem }
.kdy { margin:0; color:var(--mut); font-variant-numeric:tabular-nums }
.stav { margin-left:.5rem; font-size:.75rem; text-transform:uppercase;
  letter-spacing:.06em; border:1px solid var(--line); padding:0 .4rem;
  border-radius:3px }
h3 { margin:.1rem 0 .5rem; font:600 1.25rem Georgia, serif }
h3 a { color:inherit; text-decoration:none }
h3 a:hover { color:var(--acc); text-decoration:underline }
.popis { margin:.2rem 0 }
dl { display:grid; grid-template-columns:max-content 1fr;
  gap:.15rem .9rem; margin:.4rem 0 }
dt { color:var(--mut) } dd { margin:0 }
small { color:var(--mut) }
.rozsah { color:var(--mut); font-size:.85rem; margin:.3rem 0 0 }
@media (max-width:600px) { .karta, .karta.kompakt {
  grid-template-columns:1fr } }
</style></head><body>
"""

HTML_SCRIPT = r"""<script>
const q = document.getElementById("q"), rok = document.getElementById("rok"),
  stav = document.getElementById("stav");
const bez = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "")
  .toLowerCase();
function filtr() {
  const t = bez(q.value);
  for (const k of document.querySelectorAll(".karta"))
    k.hidden = !(bez(k.textContent).includes(t)
      && (!rok.value || k.dataset.rok === rok.value)
      && (!stav.value || k.dataset.stav === stav.value));
}
[q, rok, stav].forEach((x) => x.addEventListener("input", filtr));
document.querySelector(".filtry").hidden = false;
</script></body></html>
"""


def render_html(records, odkaz):
    """`odkaz(složka)` vrací href na složku akce."""
    counts = Counter(r["stav"] for r in records)
    sub = f"Akcí: {len(records)} · " + " · ".join(
        f"{label} {counts[key]}" for key, label in STAV.items())
    roky = sorted({r["datum_od"][:4] for r in records}, reverse=True)
    options = "".join(f"<option>{html.escape(y)}</option>" for y in roky)
    stavy = "".join(f'<option value="{key}">{label}</option>'
                    for key, label in STAV.items())
    karty = "\n".join(card(r, odkaz(r["slozka"])) for r in records)
    return (HTML_HEAD.replace("{title}", TITLE)
            + f'<header><h1>Fotoarchiv ARÚB</h1>\n<p class="sub">{sub}</p>\n'
            '<div class="filtry" hidden>\n'
            '<input id="q" type="search" '
            'placeholder="hledat název, místo, osobu…">\n'
            '<select id="rok"><option value="">všechny roky</option>'
            f'{options}</select>\n'
            '<select id="stav"><option value="">všechny stavy</option>'
            f'{stavy}</select></div></header>\n'
            f'<main>\n{karty}\n</main>\n' + HTML_SCRIPT)


# --- zápis ---------------------------------------------------------------

def target_dir(ws):
    """Produkce kořen archivu, vývoj `<work>/index/`."""
    return ws.archiv if ws.zapis else ws.work / "index"


def link(ws):
    if ws.zapis:
        return lambda name: f"./{urllib.parse.quote(name)}/"
    return lambda name: (ws.archiv / name).as_uri() + "/"


def write(ws):
    """Přegeneruje oba soubory indexu; zapíše jen chybějící či změněné.

    Vrací seznam varování (prázdný = v pořádku); selhání nevyhazuje.
    """
    try:
        records = collect(ws)
        contents = {"_INDEX.html": render_html(records, link(ws)),
                    "_INDEX.md": render_md(records)}
    except Exception as e:
        log.exception("index: generování selhalo")
        return [f"Index se nepodařilo vygenerovat: {e}"]
    warnings = []
    for name in NAMES:
        path = target_dir(ws) / name
        data = contents[name].encode("utf-8")
        try:
            try:
                if path.read_bytes() == data:
                    continue
            except FileNotFoundError:
                pass
            xmp.write_atomic(path, data, mode=0o644)
        except Exception as e:
            log.warning("index: zápis %s selhal: %s", path, e)
            warnings.append(f"{name} se nepodařilo zapsat: {e}")
    return warnings
