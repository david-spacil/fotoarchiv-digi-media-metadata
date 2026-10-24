"""Klient stávajícího API aplikace: přihlášení cookie relací, založení
importu a nahrání souboru syrovým tělem (jako prohlížeč)."""

import json
import os
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

MISTNI = {"127.0.0.1", "localhost", "::1"}

ZPRAVY = {
    "neplatne": "Neplatný login nebo heslo.",
    "zdrzeno": "Příliš mnoho pokusů, zkuste to za chvíli.",
    "zmenit_heslo": "Nejdřív si v prohlížeči změňte heslo.",
    "neprihlasen": "Přihlášení vypršelo, přihlaste se znovu.",
    "malo_mista": "Na serveru není dost místa.",
    "prilis_velky": "Soubor je větší, než server přijme.",
    "stejne_jmeno": "Ve výběru jsou dva soubory se stejným názvem "
                    "z různých složek; nahrajte je zvlášť.",
}


class Chyba(Exception):
    def __init__(self, kod, zprava=None):
        super().__init__(zprava or ZPRAVY.get(kod) or kod)
        self.kod = kod


def adresa(text):
    """Ověřená adresa serveru bez lomítka na konci. HTTP jen
    na tomto počítači (cookie relace by šla po síti nešifrovaně)."""
    text = text.strip().rstrip("/")
    if "://" not in text:
        text = "https://" + text
    u = urlsplit(text)
    if u.scheme == "https" and u.hostname:
        return text
    if u.scheme == "http" and u.hostname in MISTNI:
        return text
    raise Chyba("adresa", "Adresa serveru musí začínat https:// "
                "(http jen pro 127.0.0.1 a localhost).")


class _Citac:
    """Souborový objekt, který hlásí přečtené bajty (průběh)."""

    def __init__(self, f, prubeh):
        self.f, self.prubeh = f, prubeh

    def read(self, n=-1):
        data = self.f.read(n)
        if data and self.prubeh:
            self.prubeh(len(data))
        return data


class Server:
    def __init__(self, url):
        self.url = adresa(url)
        self.jmeno = None
        self._http = build_opener(HTTPCookieProcessor(CookieJar()))

    def _volat(self, metoda, cesta, telo=None, data=None, hlavicky=None,
               timeout=60):
        hlavicky = dict(hlavicky or {})
        if telo is not None:
            data = json.dumps(telo).encode()
            hlavicky["Content-Type"] = "application/json"
        req = Request(self.url + cesta, data=data, method=metoda,
                      headers=hlavicky)
        try:
            with self._http.open(req, timeout=timeout) as r:
                return json.loads(r.read() or b"{}")
        except HTTPError as e:
            try:
                odpoved = json.loads(e.read())
            except ValueError:
                odpoved = {}
            kod = odpoved.get("chyba") or f"http_{e.code}"
            raise Chyba(kod, ZPRAVY.get(kod)
                        or f"Server odmítl požadavek ({e.code} {kod}).") \
                from None
        except (URLError, OSError) as e:
            raise Chyba("spojeni", f"Spojení se serverem selhalo: "
                        f"{getattr(e, 'reason', e)}") from None

    def prihlasit(self, login, heslo):
        """Přihlásí uživatele; server bez přihlášení (vývojový režim)
        přijme kohokoli. Nastaví `jmeno` (vlastník importu)."""
        try:
            self._volat("POST", "/api/prihlaseni",
                        {"login": login, "heslo": heslo})
        except Chyba as e:
            if e.kod != "bez_prihlaseni":
                raise
        ja = self._volat("GET", "/api/ja")
        if ja.get("zmenit_heslo"):
            raise Chyba("zmenit_heslo")
        self.jmeno = ja.get("jmeno")
        return ja

    def zalozit_import(self, celkem):
        """Nový import; vrátí jeho id."""
        r = self._volat("POST", "/api/import",
                        {"jmeno": self.jmeno, "celkem": celkem})
        return r["id"]

    def nahrat(self, id, nazev, soubor, mtime_ms, prubeh=None):
        """Nahraje soubor `soubor` do importu `id` pod jménem `nazev`."""
        q = urlencode({"jmeno": self.jmeno or "", "cesta": nazev,
                       "mtime": int(mtime_ms)})
        with open(soubor, "rb") as f:
            return self._volat(
                "POST", f"/api/import/{quote(id)}/soubor?{q}",
                data=_Citac(f, prubeh),
                hlavicky={"Content-Type": "application/octet-stream",
                          "Content-Length": str(os.fstat(f.fileno())
                                                .st_size)},
                timeout=600)

    def adresa_importu(self, id):
        return f"{self.url}/#/import/{quote(id)}"
