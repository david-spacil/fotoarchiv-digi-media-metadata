"""Geokódování názvů míst přes veřejný Nominatim (OpenStreetMap).

Podmínky provozu (operations.osmfoundation.org/policies/nominatim): nejvýš
1 dotaz/s, identifikující User-Agent, povinná cache, žádné našeptávání.
Cache (`<cache>/geokodovani.json`, normalizovaný dotaz → kandidáti) je
jen odpověď služby, smazatelná bez ztráty dat; volba kandidáta patří do
`souradnice_mist` v `_metadata.json` akce. Kontakt provozovatele do
User-Agent je jeden pro server (`<work>/nominatim.json`, nastavuje admin);
bez něj je geokódování vypnuté.
"""

import json
import logging
import os
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .auth import write_private

URL = "https://nominatim.openstreetmap.org/search"
APP = "fotoarchiv-digi-media-metadata"
INTERVAL = 1.1
TIMEOUT = 10
LIMIT = 10

log = logging.getLogger(__name__)


class GeocodeError(Exception):
    """Služba neodpověděla nebo vrátila chybu."""


def normalize(query):
    """Klíč cache: NFC, bez rozdílu velikosti písmen a nadbytečných mezer."""
    return " ".join(unicodedata.normalize("NFC", query).casefold().split())


def fetch_nominatim(query, user_agent):
    params = urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "limit": LIMIT,
        "accept-language": "cs",
    })
    req = urllib.request.Request(f"{URL}?{params}",
                                 headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except (OSError, ValueError) as e:
        raise GeocodeError(str(e)) from e


def candidate(item):
    return {
        "nazev": item.get("name") or item["display_name"].split(",")[0],
        "popis": item["display_name"],
        "gps": [float(item["lat"]), float(item["lon"])],
        "osm": f"{item.get('osm_type')}/{item.get('osm_id')}",
        "typ": item.get("addresstype") or item.get("type"),
    }


class Contact:
    """`<work>/nominatim.json` = {kontakt}."""

    def __init__(self, work):
        self.path = Path(work) / "nominatim.json"

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return str(data.get("kontakt") or "").strip() or None

    def save(self, kontakt):
        write_private(self.path, {"kontakt": kontakt})

    def delete(self):
        self.path.unlink(missing_ok=True)


class Geocoder:
    """Dotazy na Nominatim s cache; každý dotaz odejde nejvýš jednou.

    `kontakt` je text, nebo funkce, která ho vrátí při každém dotazu
    (změna platí bez restartu).
    """

    def __init__(self, cache_dir, kontakt, fetch=None,
                 clock=time.monotonic, sleep=time.sleep):
        self.path = Path(cache_dir) / "geokodovani.json"
        self.kontakt = kontakt if callable(kontakt) else lambda: kontakt
        self.fetch = fetch or fetch_nominatim
        self.clock = clock
        self.sleep = sleep
        self.lock = threading.Lock()
        self.last = None
        self.cache = self._load()

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _store(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    @property
    def enabled(self):
        return bool(self.kontakt())

    def search(self, query):
        """(kandidáti, z_cache). Chyba služby → GeocodeError, necachuje se;
        bez kontaktu GeocodeError bez dotazu."""
        key = normalize(query)
        # Zámek drží i čekání a dotaz: souběžné požadavky jdou po jednom
        # a druhý stejný dotaz už najde odpověď v cache.
        with self.lock:
            if key in self.cache:
                return self.cache[key]["kandidati"], True
            kontakt = self.kontakt()
            if not kontakt:
                raise GeocodeError("kontakt není nastaven")
            if self.last is not None:
                wait = self.last + INTERVAL - self.clock()
                if wait > 0:
                    self.sleep(wait)
            log.info("geokódování: dotaz na Nominatim: %s", key)
            try:
                items = self.fetch(key, f"{APP} ({kontakt})")
            finally:
                self.last = self.clock()
            found = [candidate(item) for item in items]
            now = datetime.now(timezone.utc)
            self.cache[key] = {"kandidati": found,
                               "cas": now.isoformat(timespec="seconds")}
            self._store()
            return found, False
