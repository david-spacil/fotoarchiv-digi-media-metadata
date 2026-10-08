# AGENTS.md

Pokyny pro AI agenty (Claude Code, Codex aj.) pracující v tomto repozitáři.

## Stav

Flask server v `fotoarchiv/`, klient v `fotoarchiv/static/` (čisté ES
moduly bez build kroku). Bez přepínače vývojový režim: archiv
jen čte, `_metadata.json` a cache ukládá do `.work/`. S
`--zapis-do-archivu` produkční: `_metadata.json` ve složce akce, úklid
a import se provádějí; cache a nahrané soubory importu
(`.work/import/`) zůstávají v `.work/`. Zámek akcí je v paměti serveru
(`lock.py`) — **server smí běžet jen jako jeden proces**.

`README.md` je specifikace (archiv, datový model, jména osob, výstupy,
aplikace). Při změně návrhu ho aktualizovat; tady ho neopakovat.

Změny se vedou přes OpenSpec (`openspec/`, příkazy `/opsx:*`). Úpravy v
`openspec/` se řeší samostatnými commity, ne zároveň s kódem.

## Příkazy

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m fotoarchiv \
  --archiv /mnt/x/fotoarchiv/FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB
# → http://127.0.0.1:5000, volitelně --work .work --port 5000,
#   --zapis-do-archivu (produkční režim, zapisuje do archivu),
#   --bez-prihlaseni (jen vývojový režim, každý admin),
#   --https (cookie relace jen přes HTTPS)
.venv/bin/python -m fotoarchiv heslo LOGIN --work .work
# → jednorázové heslo pro login z .work/uzivatele.json
.venv/bin/python -m fotoarchiv prevzit --archiv … --work .work
# → jednorázově převezme _metadata.json z .work do archivu
.venv/bin/python -m fotoarchiv exportovat [AKCE] --archiv … --work .work
# → XMP sidecary jedné/všech akcí (jen změněné); bez --zapis-do-archivu
#   do .work/xmp/; --obliceje přidá oblasti obličejů pro obnovu Immiche
.venv/bin/python -m fotoarchiv skryt --archiv … --work .work
# → skryje nedokončené akce před Immichem (přípona .ignored u složky);
#   bez --zapis-do-archivu jen výpis, spouštět při zastaveném serveru
.venv/bin/python -m fotoarchiv zkontrolovat [AKCE] --archiv … --work .work
# → poškozené soubory (nuly od 64 KiB, dekódování, ffprobe) jedné/všech
#   akcí; archiv jen čte, report do .work/kontrola/, cache v .work/cache/
cp .env.example .env && docker compose up -d --build
# → nasazení na server (produkční režim, ./work), viz README, Docker

.venv/bin/python -m pytest -q                       # testy Pythonu
.venv/bin/python -m pytest tests/test_cleanup.py::test_collision_blocks
node --test tests/js/*.test.mjs                     # testy JS
```

Systémově: `exiftool`, `ffmpeg` (bez něj video bez náhledu), `node` jen
na testy. Synchronizace obličejů potřebuje `.work/immich.json`
(nastavení v aplikaci) a HTTP na server Immich; testy na něj nesahají
(podvržený `fetch`). Geokódování potřebuje kontakt v `.work/nominatim.json` (nastaví admin
v aplikaci; User-Agent, podmínka Nominatimu) a odchozí HTTPS na `nominatim.openstreetmap.org`; bez nich
jdou souřadnice míst zadat jen ručně. Testy na službu nesahají
(podvržený `fetch`); skutečné dotazy jen jednotlivě, nikdy hromadně. Dědění je v Pythonu (`model.py`) i JS (`static/inherit.js`);
obě se testují proti `tests/fixtures/inheritance/*.json` — měnit spolu.

## Invarianty návrhu

Pravidla, která se táhnou přes víc částí README a snadno se poruší:

- **Zdroj pravdy je `_metadata.json` ve složce akce.** XMP sidecary a index
  (`_INDEX.html`, `_INDEX.md`, `index.py`) jsou čistě generované výstupy —
  nikdy z nich nečíst zpět a nikdy je needitovat ručně. Index se
  přegeneruje jen po importu a exportu, ne při uložení.
- **Originály fotek a videí se nemění** (žádný zápis EXIF/XMP do souboru).
- **Dědění akce → skupina → soubor**, nižší úroveň přepisuje vyšší. Sidecar
  obsahuje hodnoty už rozepsané (zděděné), JSON jen to, co je na dané úrovni
  zadané.
- `autori` = „fotil někdo z uvedených“, ne přiřazení konkrétní osoby.
- **`obliceje` zapisuje jen synchronizace z Immiche** (`immich.py`), jen
  u souboru, nedědí se. Klient je při ukládání neposílá, server je bere
  z uložené verze; starší `osoby` se ignorují a při uložení mažou.
  Klíč Immiche jen v `.work/immich.json`, nikdy v archivu ani
  v odpovědi API. MWG oblasti v exportu pro obnovu jsou vůči uloženému
  (neotočenému) obrázku, `oblast` v JSONu vůči otočenému.
- **Hesla jen jako hash v `.work/hesla.json`** (píše jen aplikace,
  0600); `uzivatele.json` píše jen správce, aplikace ho nikdy
  nezapisuje. Heslo ani hash nikdy do archivu, logu ani odpovědi API.
  Přihlášení hlídá jediná vstupní kontrola v `app.py`
  (`before_request`); jméno u zámku z relace, ne z požadavku. Admin
  endpointy kontroluje server, klient je jen skrývá.
- Jména v kanonickém tvaru `Příjmení, Jméno`; seznam návrhů se skládá ze
  všech `_metadata.json` v archivu, žádný pevný číselník. Porovnání ignoruje
  diakritiku, velikost písmen a pořadí slov.
- Zpracovávají se jen složky akcí na první úrovni (`YYYY-MM-DD název`)
  a v nich jen kořen. Podsložky se buď sloučí s kořenem, nebo dostanou
  příponu `.ignored` — ta je jediným záznamem o ignorování. RAWy do
  Immiche nejdou (`RAW.ignored`). `Thumbs.db` se přeskakuje.
- **Složka nedokončené akce má v produkci příponu `.ignored`** (Immich ji
  nevidí); dokončení ji po zápisu sidecarů odebere. Název akce je vždy
  bez přípony (URL, zámek, cache, `.work`); složku na disku skládá jen
  `Workspace.event_dir`, nikdy `archiv / název` přímo. Obě složky
  zároveň = kolize, nic se nepřesouvá.
- Přesun souborů nikdy nepřepíše existující soubor.
- Formát XMP: co Immich nemá vlastní pole, jde do tagů podle konvencí
  `arubrno/archiv-immich` (viz README, Výstupy).
- Datum u WhatsApp fotek (`IMG-YYYYMMDD-WA*`) jen z názvu souboru, EXIF
  nemají.

## Otevřené otázky

- Zdroj souborů `IMG_####.jpg` a jejich EXIF.
- Immich je napojený jen ke čtení obličejů; přesuny a přejmenování
  dělat před importem do produkčního Immiche (změna cesty = nový asset
  bez obličejů).

## Prostředí

Primárně Fedora. Windows u kolegů žádoucí, ale jen pokud to nestojí dny
práce — neobětovat kvůli tomu jednoduchost na Linuxu.
