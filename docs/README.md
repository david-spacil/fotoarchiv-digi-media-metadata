[← Zpět na README](../README.md)

# Dokumentace

Úvod, struktura archivu a datový model jsou v [README](../README.md).
Pokyny pro vývoj a testy jsou v [AGENTS.md](../AGENTS.md).

## Návod k použití

Práce s akcí od importu po dokončení, v pořadí, jak jde za sebou.

1. [Import](navod/import.md) — nahrání nových fotek a videí do nové
   nebo stávající akce.
   - [Import ze složky přetřídit](navod/import-z-pretridit.md) —
     převzetí nezatříděných složek (admin a archivář).
2. [Seznam akcí](navod/seznam-akci.md) — fronta práce, hotovost,
   filtry a hledání.
3. [Průvodce akcí](navod/pruvodce-akce.md) — první otevření akce:
   úklid, údaje akce, skupiny a autoři.
4. [Pracovní plocha](navod/pracovni-plocha.md) — mřížka, lupa,
   navigátor, formulář a klávesnice.
5. [Vyřazení a úklid](navod/vyrazeni-a-uklid.md) — označení
   nepovedených a poškozených souborů a jejich přesun stranou.
6. [Dokončení akce](navod/dokonceni-akce.md) — kontrolní stránka,
   zápis sidecarů a zveřejnění pro Immich.
7. [Pojmenování osob](navod/pojmenovani-osob.md) — jména obličejů
   rozpoznaných Immichem (admin a archivář).
8. [Smazání akce](navod/smazani-akce.md) — koš smazaných akcí,
   obnovení a trvalé smazání po 7 dnech (admin).

Výchozí je tmavý režim; přepínač v hlavičce přepne do světlého
(pamatuje si ho prohlížeč, platí i pro přihlášení). Lupa je tmavá
v obou režimech. Plocha je stavěná na okna od 1280 × 720 CSS px
(notebook se škálováním) po široké monitory.

## Provoz

- [Lokální spuštění](provoz/spusteni.md) — požadavky, přepínače,
  vývojový a produkční režim.
- [Přihlášení a role](provoz/prihlaseni.md) — účty, hesla, admin
  a archivář, oprávnění k úpravě akce.
- [Docker](provoz/docker.md) — nasazení na server.
- [Nastavení Immiche](provoz/nastaveni-immich.md) — adresa, API klíč
  a jeho oprávnění, knihovna.
- [Příkazy](provoz/prikazy.md) — přehled příkazů `python -m fotoarchiv`.

## Návrh

Pravidla, podle kterých aplikace pracuje. Spolu s README jsou
specifikací projektu.

- [Archiv](navrh/archiv.md) — složky akcí, skrytí nedokončených akcí,
  zdroje fotek.
- [Podsložky a RAW](navrh/podslozky-a-raw.md) — čistý kořen akce,
  přípona `.ignored`, kontrola akce.
- [Poškozené soubory](navrh/poskozene-soubory.md) — test nul,
  dekódování, výsledky a cache.
- [Jména osob](navrh/jmena-osob.md) — kanonický tvar a otevřený
  seznam návrhů.
- [Výstupy](navrh/vystupy.md) — XMP sidecary, obnova obličejů, index
  archivu.
- [Immich](navrh/immich.md) — alba akcí, stav akce, synchronizace
  obličejů.
- [Ukládání a export](navrh/ukladani-a-export.md) — zápis
  `_metadata.json` a sidecarů.
- [Souběh](navrh/soubeh.md) — zámky akcí a importů.
- [Platforma a náhledy](navrh/platforma.md) — exiftool, cache náhledů,
  podporované systémy.
