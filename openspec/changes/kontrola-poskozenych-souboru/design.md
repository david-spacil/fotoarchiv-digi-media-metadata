# Design

## Context

Viz proposal.md – Why. Stav kódu, který přístup určuje:

- Přehled importu (`Imports.overview`, `GET /api/import/<id>`) je
  obyčejná odpověď bez streamu; údaje bere jen z exiftoolu (`scan.scan`,
  u zdroje `scan_source`), soubory se nedekódují.
- Plán a provedení už streamují NDJSON s průběhem po souborech a po
  `STEP` = 64 MB (`_iter_hashes`, `_sha256_steps`); hashe se cachují
  v `.work/cache/sha256/<jméno>.json` podle (klíč, velikost, mtime_ns).
- Pillow se dnes používá jen v náhledech (`thumbs.py`, `draft`);
  neúspěch se uloží jako `.failed` bez důvodu.
- Upload ověřuje délku proti `Content-Length` a ukládá sha256; kopie do
  archivu (`_copy`) počítá sha256 čtených dat proti uloženému a dělá
  `fsync`. Import z `přetřídit` je `os.rename` na stejném svazku.
- Měření na vzorcích z issue a uměle poškozených kopiích:

  | vada | exiftool | Pillow | test nul |
  |---|---|---|---|
  | nuly na začátku | ano | ano | ano |
  | nuly na konci (šedý pruh) | ne | 2 z 5 | ano |
  | nuly uprostřed (64–128 KiB) | ne | 0 ze 4 | ano |
  | useknutý soubor | ne | 3 ze 4 | ne |

  Pillow u nul na konci zachytil skutečný `20151107_135155.jpg` a jen
  jednu ze čtyř umělých kopií (každá v několika polohách se stejným
  výsledkem).

  `draft` zachytil totéž co plné dekódování, ~3× rychleji. Zdravé
  obrázky na stroji (250 souborů) měly nejdelší zarovnaný úsek nul pod
  24 KiB (Photoshop, PNG s plochou barvou).

## Goals / Non-Goals

**Goals:**
- Jedna funkce kontroly souboru pro import i příkaz, s cache a průběhem.
- Kontrola zdroje v `přetřídit` čte každý soubor přes SMB nejvýš jednou
  za import, i když potřebuje i sha256.

**Non-Goals:**
- Odznak v aplikaci, kontrola v náhledech a přesun poškozených souborů
  akce (varianta C, samostatný change po průchodu archivem).
- Oprava poškozených souborů nebo ořez šedého pruhu.
- Plné dekódování videa (`ffmpeg -f null`): cena odpovídá délce videa.
- Kontrola při ukládání metadat nebo při otevření akce.

## Decisions

### Nový modul `fotoarchiv/integrity.py`
Čistá funkce `check(path, kind) -> {stav, duvody, nuly}` a generátor
`iter_check(path, kind)` s průběhem po `STEP`, který zároveň spočítá
sha256. Soubor se čte po blocích 4 KiB zarovnaně (přes `CHUNK` jako
násobek 4 KiB), počítá se běžící úsek nul, nejdelší úsek a jeho poloha;
bajty fotky se drží v paměti a Pillow je dostane přes `BytesIO`. Video
a RAW se v paměti nedrží.
*Alternativa:* rozšířit `thumbs.py` nebo `scan.py` – odmítnuto, kontrola
je samostatná schopnost a C ji pak volá i z náhledů.

### Klasifikace
- *nečitelný*: 0 B; soubor jen z nul; Pillow soubor nerozpozná
  (`UnidentifiedImageError`); `ffprobe` nenajde video proud nebo skončí
  chybou.
- *podezřelý*: zarovnaný úsek nul ≥ 64 KiB; Pillow ohlásí useknutý nebo
  chybný obraz při `load()`; varování `ffprobe`.
- Důvody jsou česky pro uživatele, např. „768 KiB nul od začátku“,
  „119 KiB nul na konci“, „obraz je neúplný“.
- Práh 64 KiB a zarovnání 4 KiB jsou konstanty v modulu. Fotka
  z fotoaparátu má kvůli šumu snímače entropii, která 16 bloků nul
  prakticky vylučuje; ověří se prvním průchodem archivem (report).
*Alternativa:* spoléhat jen na Pillow – odmítnuto podle měření výše.

### Bez chyb z exiftoolu
Původní návrh počítal s `Error` z exiftoolu. Při volání se seznamem tagů
(jako `scan.py`) exiftool chybu do JSON nevrátí (jde jen na stderr)
a 1bajtový CR2 ani NEF z náhodných dat za chybu nepovažoval; jediný
případ, který poznal (nuly na začátku), zachytí test nul. Kontrola ho
proto nevolá, RAW se posuzuje jen testem nul.
*Alternativa:* samostatné volání exiftoolu po složkách – odmítnuto,
nic by nepřidalo a stálo by start Perlu.

### Fotky dekódovat s `draft`
Stejné měřítko jako náhled 1600 px. Chyby dekódování vychází stejně
jako u plného dekódování a je to ~3× rychlejší. Pillow MUST mít vypnuté
`LOAD_TRUNCATED_IMAGES` (výchozí stav), jinak useknutý obraz projde.

### Cache `.work/cache/kontrola/<jméno>.json`
Stejný tvar a klíč jako `.work/cache/sha256/` (klíč, velikost,
mtime_ns), jméno souboru cache stejné jako u hashů (`import-<id>`,
`pretridit-<sha1>`, název akce). Záznam drží výsledek i sha256; když
kontrola sha256 spočítá, zapíše ho i do cache hashů, takže plán zdroj
nečte znovu.
*Alternativa:* jeden společný soubor cache – odmítnuto, rostl by
s celým archivem a přepisoval se při každém importu.

### Stream `POST /api/import/<id>/kontrola`
Přehled zůstane rychlý GET; průvodce po jeho zobrazení otevře stream
kontroly (`kontrola`, `kontrola_prubeh`, nakonec `kontrola_hotovo`
s výsledky). Výsledky z cache přijdou hned. Tlačítko na plán je do
konce zablokované. `overview` vrací výsledky z cache, pokud jsou, aby
návrat k importu nečekal.
*Alternativa:* kontrola uvnitř streamu plánu – odmítnuto, uživatel má
o poškozených souborech rozhodnout před volbou cíle.

### Volba u podezřelých a smazání
- Volba se ukládá do `import.json` jako `povolene_poskozene: [cesta]`
  přes `POST /api/import/<id>/poskozene`.
- `DELETE /api/import/<id>/soubor` s `cesta`: server znovu zjistí
  výsledek z cache pro aktuální (velikost, mtime); smaže jen *podezřelý*
  nebo *nečitelný*. Nahraný soubor kdykoli mimo provedení; soubor
  zdroje jen v produkčním režimu, pod zámkem zdroje relace a se
  shodným snímkem velikosti a času změny. Smazání se zaloguje jako
  operace úklidu.
- Plán sestavuje (a provedení znovu sestaví) seznam poškozených
  z cache, změněný soubor zkontroluje znovu. Poškozený nepovolený soubor
  dostane v plánu `poskozeny: duvod` a nepřenáší se.

### U videa nuly jen v obrazových datech (modul `fotoarchiv/mp4.py`)
První průchod archivem (8. 10. 2026, 1320 souborů) nahlásil 5 videí,
nezávislé ověření (rozbor atomů) ukázalo, že všech 5 je zdravých:
nuly ležely v atomu `free` (Telč, rezerva pro `moov`) a v pevně velkých
`udta`/`meta` (Panasonic). Panasonic navíc ukládá zvuk jako PCM
(`pcm_s16be`): ticho je doslova řada nul, 1 s stereo 48 kHz je
~188 KiB, takže delší ticho by práh přesáhlo i v `mdat` (v archivu
52–55 KiB, rezerva ~10 KiB). Ověřeno na MOV z ffmpeg s tichým PCM po
1 s: dnešní kontrola ho hlásila čtyřmi úseky ~184 KiB.

Kontrola proto z tabulek vzorků (`moov` → stopy s `hdlr` = `vide` →
`stco`/`co64`, `stsc`, `stsz`) sestaví rozsahy obrazových dat a úseky
nul počítá jen v nich, součtem částí (úsek přes střídající se obraz
a zvuk). Snímky H.264/HEVC obsahují zabraňovací bajty, blok 4 KiB nul
v nich platně nevznikne. Parser čte jen hlavičky (seek na atomy, `moov`
do 256 MiB), ne data; rozsahy musí ležet v `mdat`, jinak (vynulované
nebo cizí tabulky), u fragmentovaného MP4 (`moof`) a při jakékoli chybě
vrací None a test nul běží přísně přes celý soubor. Ověřeno proti
pozicím paketů z `ffprobe` (MOV s `moov` na konci i na začátku, HEVC
v MP4): shoda bajt po bajtu. `VERSION` cache 2 zneplatní výsledky
první verze.
*Alternativy:* (B) u videa test nul vypnout a spoléhat na `ffprobe` –
odmítnuto, `ffprobe` čte jen hlavičky a vynulované bloky uprostřed
videa by nenašel; (C) vynechat jen výplňové atomy a u videa zvýšit
práh – odmítnuto, ticho delší než ~11 s by práh přesáhlo vždy a menší
skutečné poškození by se nehlásilo.

### Ověření po přenosu jen velikostí
Po `os.rename` v `_copy` i `_move` server zjistí `os.stat` cíle
a porovná velikost s originálem; nesoulad = chyba souboru ve výsledku,
soubor zůstane v archivu (smazat ho by bylo horší než ponechat).
*Alternativa:* zpětné čtení obsahu z archivu – odmítnuto: zdvojnásobí
provoz na SMB, CIFS klient může čtení obsloužit z vlastní page cache
(kontrola by nic neověřila), a obsah je už ověřený sha256 při kopii
a přes TCP/SMB podpis. Vada, kterou issue řeší, vzniká na kartě, ne
přenosem.

### Příkaz `zkontrolovat`
`python -m fotoarchiv zkontrolovat [AKCE] --archiv … --work …`, stejné
`common()` jako `exportovat`. Prochází složky akcí první úrovně, v nich
média kořene a `RAW.ignored/`, přeskakuje `Thumbs.db` a ostatní
podsložky. Průběh po akcích na stderr, nálezy na stdout, report
`.work/kontrola/report-<YYYYMMDD-HHMMSS>.json` (akce, soubor, stav,
důvody, nejdelší úsek nul). Exit kód 0 i s nálezy, 1 při chybě běhu.
Přerušitelné Ctrl+C bez ztráty cache (cache se zapisuje po akcích).

## Risks / Trade-offs

- [Zdravá fotka s dlouhým úsekem nul (černá obloha, přeexponovaná
  plocha v PNG)] → report s nejdelšími úseky pod prahem; práh je
  konstanta a jde upravit po průchodu archivem. Podezřelý soubor import
  nezahodí, jen se uživatele zeptá.
- [Kontrola zdroje přes SMB čte celé soubory] → průběh po bajtech,
  cache, sdílený výpočet sha256; import z `přetřídit` se dělá jednou.
- [Fotka se drží v paměti kvůli Pillow] → jen fotky (desítky MB);
  limit uploadu 20 GB se týká hlavně videí, ta se v paměti nedrží.
- [Smazání ze zdroje je první nevratná operace v aplikaci] → jen
  poškozené soubory, potvrzovací dialog se jménem a důvodem, kontrola
  snímku a zámku, produkční režim, log.
- [`ffprobe` chybí] → video jen testem nul, s poznámkou ve výsledku.
- [Vynulovaný blok přes malé snímky střídané velkým zvukem PCM: část
  v obrazových datech může zůstat pod prahem] → známé omezení, cena za
  ticho bez falešných poplachů; velké vynulované bloky se do obrazu
  trefí i tak.
- [Video bez obrazové stopy (jen zvuk v MOV) nebo jiný kodek bez
  zabraňovacích bajtů (MJPEG)] → bez obrazové stopy přísný test přes
  celý soubor; u MJPEG nejsou dlouhé nuly v datech snímku obvyklé, nic
  se zvlášť neřeší.
- [Useknutý JPEG zakončený značkou `FFD9` dekodér přijme (ověřeno na
  vzorku)] → známé omezení; zachytil by ho jen `ffmpeg` za cenu
  dalšího dekódování. Vada z issue (vynulované bloky) ho nemá.

## Migration Plan

Bez migrace dat. Cache vzniká postupně. Po nasazení správce spustí
`zkontrolovat` nad celým archivem a report poslouží k ověření prahu
a k rozhodnutí o rozsahu varianty C.

## Open Questions

- Varianta C: úklid akce už umí vyřazení (`vyradit: true` → přesun do
  `k_odstraneni.ignored`, sidecar, smazání záznamu). Zda poškozené
  soubory akce půjdou tudy, nebo do samostatné `POSKOZENE.ignored/`,
  se rozhodne v navazujícím changi; tento change složky v archivu
  nezakládá.
