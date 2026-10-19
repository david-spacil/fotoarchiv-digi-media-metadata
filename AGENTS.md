# AGENTS.md

Pokyny pro AI agenty (Claude Code, Codex aj.) pracující v tomto repozitáři.

## Pokyny

Agent bez výslovného svolení nepřistupuje k reálným datům (fotkám, obličejům, ...). Pokud je to potřeba, vytváří si dummy data. 

## Stav

Flask server v `fotoarchiv/` na WSGI serveru cheroot, klient
v `fotoarchiv/static/` (čisté ES moduly bez build kroku). Bez přepínače
vývojový režim: archiv jen čte, `_metadata.json` a cache ukládá do `.work/`.
S `--zapis-do-archivu` produkční: `_metadata.json` ve složce akce, úklid
a import se provádějí; cache a nahrané soubory importu (`.work/import/`)
zůstávají v `.work/`. Zámek akcí je v paměti serveru (`lock.py`) — **server
smí běžet jen jako jeden proces**.

Specifikace je `README.md` (úvod, struktura archivu, datový model)
spolu s `docs/` (rozcestník `docs/README.md`: návod, provoz, návrh).
Při změně návrhu je aktualizovat; tady je neopakovat.

Změny se vedou přes OpenSpec (`openspec/`, příkazy `/opsx:*`). Úpravy v
`openspec/` se řeší samostatnými commity, ne zároveň s kódem. Nové úpravy
agent dává do větve `agents/<agent>/<nazev-zmeny>`.

## Příkazy

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m fotoarchiv \
  --archiv /mnt/x/fotoarchiv/FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB
# → http://127.0.0.1:5000 (cheroot, 32 vláken), volitelně --work .work
#   --port 5000, --vlakna N, --zapis-do-archivu (produkční režim, zapisuje
#   do archivu), --bez-prihlaseni (jen vývojový režim, každý admin),
#   --debug (vývojový server Werkzeugu s reloaderem),
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
# → kontrola poškozených souborů + nálezy konzistence akcí;
#   --rychle jen konzistence, --zapis-do-archivu i náprava přesuny
# → poškozené soubory (nuly od 64 KiB, dekódování, ffprobe) jedné/všech
#   akcí; archiv jen čte, report do .work/kontrola/, cache v .work/cache/
cp .env.example .env && docker compose up -d --build
# → nasazení na server (produkční režim, ./work), viz docs/provoz/docker.md

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

Pravidla, která se táhnou přes víc částí specifikace a snadno se
poruší:

- **Zdroj pravdy je `_metadata.json` ve složce akce.** XMP sidecary a index
  (`_INDEX.html`, `_INDEX.md`, `index.py`) jsou čistě generované výstupy —
  nikdy z nich nečíst zpět a nikdy je needitovat ručně. Index se
  přegeneruje jen po importu a exportu.
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
- **Do Immiche zapisuje jen nástroj pojmenování** (`naming.py`
  a endpointy `/api/akce/<nazev>/osoby…`: jméno, skrytí, sloučení vždy
  jedné osoby), **dokončení a synchronizace** (`albums.py`: alba akcí
  se jen doplňují a odebírají z nich assety, nikdy se nemaže album ani
  asset; sken knihovny jen hlídač po dokončení, ne pravidelná
  synchronizace). Zapisuje se i ve vývojovém režimu, testy jen proti
  `FakeImmich`. Nástroj smí archivář a admin (`g.user["archivar"]`,
  ne `ADMIN_PREFIXES`), bez zámku akce a nikdy nemění `_metadata.json`.
  Stav nástroje a Immiche je jen ve `.work/`: `immich-alba.json` (akce →
  album a stav), `immich-osoby.json` (počty osob pro hotovost; výpis
  akcí se Immiche neptá), `pojmenovani.json` (odložené osoby podle
  loginu a akce).
- **`upravili` zapisuje jen server** (`model.touch` v `akce_save`,
  `akce_finish` a ve `write_description` po importu) jménem z relace;
  hodnotu od klienta zahazuje. Do sidecarů ani indexu nejde. Řídí
  oprávnění k úpravě akce: jediné rozhodnutí je `model.can_edit`,
  vynucené v `zamek_ziskat` a `require_lock`.
- **Role** v `uzivatele.json` jako `"role": "admin" | "archivar"`
  (`auth.rights`: admin ⊃ archivář). Nastavení jen admin
  (`ADMIN_PREFIXES`), přetřídit a vynucené uvolnění zámku archivář.
  Vlastník importu z relace (`owner()` v `app.py`), nikdy z požadavku.
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
  `arubrno/archiv-immich` (viz docs/navrh/vystupy.md).
- Datum u WhatsApp fotek (`IMG-YYYYMMDD-WA*`) jen z názvu souboru, EXIF
  nemají.