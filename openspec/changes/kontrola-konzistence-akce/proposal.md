## Why

V kořeni akce končí i soubory, které tam nepatří: PDF, dokumenty, zipy,
osiřelé sidecary, RAWy a podsložky nechané po ručních zásazích. Aplikace
je dnes ukáže jen ve sbaleném řádku pod mřížkou a nic s nimi nenabídne;
seznam akcí ani dokončení o nich neví. Po dokončení akce je přitom
Immich vidí, a formáty, které umí (např. TIFF), načte jako assety bez
sidecarů (issue #11).

## What Changes

- Nová **kontrola akce** zjistí v kořeni akce nálezy pěti druhů:
  nepodporovaný soubor, RAW v kořeni, podsložka bez `.ignored`, záznam
  v `_metadata.json` bez souboru a osiřelý sidecar `.xmp` (bez média).
  Čte jen výpis kořene a `_metadata.json`, žádný obsah souborů.
- Seznam akcí u akce s nálezy ukáže štítek „k vyřešení“ s rozpisem.
- Lišta pracovní plochy ukáže nálezy po druzích (klik vypíše soubory);
  sbalený řádek „Nezpracované soubory v kořeni“ pod mřížkou zmizí.
- Úklid nově navrhne přesun nepodporovaných souborů a osiřelých sidecarů
  do `ostatni.ignored/` v kořeni akce (v průvodci i na ploše). Úklid
  z plochy nabídne i RAWy a podsložky, ne jen soubory k vyřazení.
  Nic se nemaže ani nepřepisuje.
- Dokončení akce nálezy kontroly ukáže spolu s chybějícími údaji
  a dokončí po potvrzení (jen varuje, neblokuje).
- Záznam bez souboru se jen hlásí; aplikace ho nemaže (ruční údaje).
- **Navazující krok (mimo tuto změnu):** CLI. Dohodnuto rozšířit příkaz
  `zkontrolovat` z issue #10 o nálezy kontroly akce a nápravu přesunem
  s `--zapis-do-archivu`; doplní se do této změny po sloučení #10.

## Capabilities

### New Capabilities

- `event-consistency`: kontrola konzistence kořene akce — druhy nálezů,
  co se nepočítá, kde se nálezy ukazují (seznam akcí, plocha) a jak se
  řeší.

### Modified Capabilities

- `event-cleanup`: přesun nepodporovaných souborů a osiřelých sidecarů
  do `ostatni.ignored/`; úklid z pracovní plochy zahrne všechny nálezy
  s nápravou.
- `metadata-workspace`: dokončení akce ukáže i nálezy kontroly.
- `media-scan`: nezpracované soubory uvádí kontrola akce místo
  samostatného výpisu.

## Impact

- Kód: nový modul `fotoarchiv/consistency.py` (čistá funkce kontroly),
  `archive.py` (`list_events`), `app.py` (detail akce, argumenty
  úklidu), `cleanup.py` (`ostatni.ignored`), `static/app.js` (seznam,
  lišta, dialog úklidu, dokončení).
- API: detail akce a seznam akcí mají pole `kontrola`; tělo úklidu nový
  příznak pro úklid z plochy. Pole `nezpracovane` v detailu zmizí.
- Výkon: seznam akcí navíc jen projde položky kořene, které už čte;
  `_metadata.json` už načítá.
- Dokumentace: README (Podsložky a RAW, Tok práce).
