"""Nahrání výběru: kopie z telefonu do dočasné složky, upload, zápis
do evidence, smazání kopie. Bez UI, průběh přes zpětná volání."""

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .server import Chyba

SOUBEZNE = 3


@dataclass
class Vysledek:
    id: str
    nahrane: list = field(default_factory=list)
    chyby: list = field(default_factory=list)  # [(Polozka, zpráva)]


def nahrat(zdroj, zar, polozky, server, evidence, prubeh=None,
           hotovo=None, zruseno=None, souber=SOUBEZNE):
    """Nahraje `polozky` do nového importu; vrátí `Vysledek`.

    `prubeh(bajty)` hlásí přenesené bajty, `hotovo(polozka, chyba)`
    každý dokončený soubor, `zruseno()` se ptá na přerušení. Do evidence
    jde jen úspěšně nahrané; dočasné kopie se mažou vždy."""
    jmena = [p.nazev for p in polozky]
    if len(set(jmena)) != len(jmena):
        raise Chyba("stejne_jmeno")
    vysledek = Vysledek(server.zalozit_import(sum(p.velikost
                                                  for p in polozky)))

    def jeden(p, tmp):
        if zruseno and zruseno():
            raise Chyba("zruseno", "Přerušeno.")
        kopie = zdroj.kopirovat(zar, p, tmp)
        try:
            server.nahrat(vysledek.id, p.nazev, kopie, p.datum * 1000,
                          prubeh)
        finally:
            kopie.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="fotoarchiv-klient-") as tmp, \
            ThreadPoolExecutor(souber) as pool:
        uloha = {pool.submit(jeden, p, tmp): p for p in polozky}
        for f in as_completed(uloha):
            p = uloha[f]
            try:
                f.result()
            except (Chyba, OSError) as e:
                vysledek.chyby.append((p, str(e)))
                if hotovo:
                    hotovo(p, str(e))
                continue
            evidence.pridat(zar.id, [p])
            vysledek.nahrane.append(p)
            if hotovo:
                hotovo(p, None)
    return vysledek
