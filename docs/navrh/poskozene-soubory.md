[← Dokumentace](../README.md)

# Poškozené soubory

Typická vada archivu (issue #10): bloky souboru jsou na kartě nebo
v souborovém systému vynulované a délka souboru zůstala. Nuly na
začátku znemožní soubor otevřít, nuly na konci nebo uprostřed fotky
dekodér často přijme jako platná data a ukáže šedý pruh. Exiftool ani
dekodér druhý případ nepoznají, proto hlavní kontrolou je test nul.

- **Kontrola souboru** přečte soubor jednou (zároveň spočítá sha256):
  - souvislý úsek nul aspoň **64 KiB** začínající na hranici bloku
    4 KiB (u fotek, videí i RAWů); kratší úseky mívají i zdravé
    soubory (metadata z Photoshopu, plochá barva);
  - fotka (jpg, jpeg, png) se dekóduje jako náhled (Pillow, `draft`):
    nerozpoznaný obrázek je nečitelný, useknutý obraz podezřelý;
    useknutý JPEG zakončený značkou konce (`FFD9`) dekodér přijme
    a kontrola ho nepozná;
  - video ověří `ffprobe` (bez čitelného video proudu, např. chybí
    `moov` po přerušeném nahrávání = nečitelné); bez `ffprobe` jen
    test nul s poznámkou; video se celé nedekóduje;
  - u videa MP4/MOV se nuly počítají **jen v obrazových datech** podle
    tabulek vzorků v `moov` (úsek přes obraz i zvuk součtem částí
    v obraze). Nuly mimo ně patří k formátu: výplň `free` (rezerva pro
    `moov`), pevně velké `udta`/`meta` (Panasonic) a ticho
    v nekomprimovaném zvuku PCM (Panasonic, ~188 KiB nul za sekundu).
    Bez čitelných tabulek (fragmentované MP4, poškozená hlavička) se
    počítá celý soubor;
  - RAW jen testem nul.
- **Výsledek:** *v pořádku*, *podezřelý* (otevře se, ale je poškozený),
  nebo *nečitelný* (prázdný, samé nuly, nejde otevřít), vždy s důvodem,
  např. „768 KiB nul od začátku“, „119 KiB nul na konci“.
- **Cache** výsledků je v `.work/cache/kontrola/` podle cesty,
  velikosti a času změny souboru; nezměněný soubor se znovu nečte.
  Změna pravidel kontroly cache zneplatní.
- **Aplikace:** při vytváření nového náhledu souboru z kořene akce se
  kontrola spustí a výsledek doplní do cache akce (prohlížením se
  zásobník plní sám; při hitu cache se soubor nečte). Odznak
  „N poškozených“ je v seznamu akcí i v liště plochy, dlaždice
  poškozeného souboru je červeně orámovaná s důvodem v tooltipu.
  U poškozeného souboru lze potvrdit „Považovat za v pořádku“
  v panelu dlaždice nebo hromadně v dialogu Uklidit…
  (falešná pozitivita dekodéru) — uloží se jako `overeno` a odznak ho
  nadále nepočítá; zrušení je stejné tlačítko. Náprava v archivu jde
  po cestě vyřazení: označit k vyřazení (dlaždice nebo dialog) a uklidit
  (do `k_odstraneni.ignored`, viz `vyradit` v
  [Datovém
  modelu](../../README.md#datový-model)); žádná zvlášť složka poškozených
  není.
- **Import** kontroluje soubory v kroku Přehled (viz
  [Import](../navod/import.md)); poškozené soubory nepřenese bez souhlasu.
- **Archiv:** příkaz `zkontrolovat` (viz [Lokální
  spuštění](../provoz/spusteni.md)) projde kořen a `RAW.ignored/` jedné nebo
  všech akcí (ostatní podsložky ne) a archiv jen čte. U každé akce
  vypíše a do reportu uloží i nálezy kontroly konzistence (viz
  [Kontrola
  akce](podslozky-a-raw.md#kontrola-akce)); s `--rychle` se obsah souborů
  nečte, s `--zapis-do-archivu` příkaz u akcí s nálezy navrhne nápravu
  přesuny (ostatní soubory do `ostatni.ignored`, RAWy do
  `RAW.ignored`, podsložky bez volby se nemění) a po potvrzení ji
  provede; záznamy bez souboru se jen vypíší.
  Vypíše podezřelé a nečitelné soubory s důvodem a souhrn po akcích,
  report uloží do `.work/kontrola/report-<datum-čas>.json`. Report
  uvádí i nejdelší úsek nul u souborů pod prahem, aby šel práh po
  prvním průchodu archivem ověřit; u videa s přečtenými tabulkami
  nejdelší úsek v obrazových datech (`nuly`) i v celém souboru
  (`nuly_soubor`). Přerušení (Ctrl+C) nevadí: hotové
  akce jsou v cache.
