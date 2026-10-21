## Context

Server je jeden proces Flasku (`app.run`, vlákna), archiv leží na SMB,
pracovní adresář `.work/` lokálně. Úklid (`cleanup.py`) už řeší
přesuny bez přepsání: plán s příznakem `blocked`, porovnání jmen přes
`_key` (NFC + casefold, SMB nerozlišuje velikost písmen), kontrolu
těsně před `os.rename` a souběh vylučuje zámek akce. Média čte `scan`
přes `exiftool` s cache v `.work/cache/scan/`. `sha256` je v datovém
modelu, ale zatím se nepočítá.

Rozhodnuté varianty (s uživatelem): nahrání přes staging, ve vývojovém
režimu jen plán, duplicity jen v cílové akci.

## Goals / Non-Goals

**Goals:**
- Přerušený upload ani pád serveru nenechá v archivu polovičatý stav.
- Stejná pravidla pro kolize jako úklid, sdílený kód porovnání jmen.
- Fungovat s desítkami GB (videa) bez načítání souborů do paměti.

**Non-Goals:**
- Navazování přerušeného uploadu uprostřed souboru (soubor se pošle
  znovu celý; hotové soubory zůstávají).
- Duplicity napříč archivem, import z karty/telefonu mimo prohlížeč.
- Vyplňování metadat v průvodci importu — to dělá průvodce akce po
  otevření.
- Přejmenování souborů při kolizi (blokuje se, jako u úklidu).

## Decisions

**Staging `.work/import/<id>/`.** `id` = náhodný token (`secrets`),
uvnitř `soubory/` a `import.json` (relace, jméno, čas poslední
aktivity, seznam souborů s původní relativní cestou, velikostí,
`lastModified` a sha256). Staging je mimo archiv, takže vývojový režim
ho používá beze změny. *Alternativa:* přímý zápis do akce — zamítnuto
(polovičatý stav v archivu, plán až po zápisu).

**Upload po jednom souboru.** `POST /api/import/<id>/soubor` s tělem
souboru streamovaným na disk (`request.stream` po blocích, sha256
počítaný při zápisu), jméno a `lastModified` v hlavičkách/query.
Klient posílá 2–3 souběžně a ukazuje průběh (XHR `upload.onprogress`).
Soubor se píše do dočasného jména a přejmenuje se až po dokončení, takže
přerušený přenos v `import.json` není. *Alternativa:* jeden multipart se
vším — zamítnuto (bez průběhu po souborech, při chybě vše znovu,
Werkzeug bufferuje multipart do temp souborů). `MAX_CONTENT_LENGTH` se
nenastavuje globálně; limit na soubor (např. 20 GB) kontroluje
endpoint.

**Ploché jméno.** Z relativní cesty (`webkitRelativePath`) se bere jen
poslední část; dvě stejná jména ve výběru (`_key`) se blokují
v plánu, ne při uploadu — uživatel je uvidí v přehledu.

**Přehled = `scan` nad stagingem.** Sken `soubory/` stávajícím
`scan.scan` s cache pod klíčem `import-<id>` dává data, přístroje
a WhatsApp data z názvu. RAWy a nepodporované soubory se počítají
podle přípony (`cleanup.is_raw`, `scan.MEDIA_EXT`). Navržené datum nové
akce = nejstarší den z `datum`; bez dat se nepředvyplní.

**Plán (`importer.plan`).** Vstup: staging, cílová složka (nebo
`None` pro novou akci). Pro každý podporovaný soubor cíl `kořen/jméno`
nebo `RAW.ignored/jméno`, stav `ok` / `blocked` (kolize s existujícím
souborem nebo jiným souborem výběru) / `duplicita`. Duplicita: hash
souborů v kořeni cílové akce, ale jen těch se stejnou velikostí jako
některý nahraný soubor (na SMB se čte jen málo dat); hashe se cachují
v `.work/cache/sha256/<akce>.json` podle (jméno, velikost, mtime).
`RAW.ignored/` se do porovnání duplicit nezahrnuje, jen do kolizí.
Plán je stejný tvar jako u úklidu (seznam operací s `blocked`
a důvodem), takže klient může sdílet vykreslení.

**Provedení (`importer.execute`).** Plán se sestaví znovu. Staging
a archiv jsou na různých souborových systémech, takže `os.rename`
nejde: soubor se zkopíruje do dočasného `.import-<token>.tmp` v cílové
složce (`shutil.copyfileobj`, `fsync`), nastaví se mtime z
`lastModified`, a pak se jako v `cleanup._move` zkontroluje cíl
a přejmenuje. Selhání → dočasný soubor se smaže, chyba do výsledku,
pokračuje se dalším. Po úspěchu se soubor ze stagingu smaže;
prázdný staging se smaže celý. *Alternativa:* `os.link` bez přepsání —
na SMB/CIFS nespolehlivé.

**Čekání na server.** Každá akce průvodce, která čeká na server (plán,
nahrávání, provedení, zahození), zablokuje své tlačítko a ukáže, co
se děje; dvojklik tak nespustí druhý požadavek. Výpočet plánu do
stávající akce může na SMB trvat minuty (hash souborů shodné velikosti
na pomalém síťovém úložišti), proto
`POST /api/import/<id>/plan` odpovídá stejně jako provedení streamem
NDJSON: `{"typ":"hash", souboru, bajtu}` na začátku porovnání,
`{"typ":"hash_prubeh", hotovo_souboru, hotovo_bajtu}` po každém souboru
(u velkých i po 64 MB), nakonec `{"typ":"plan", …}`. Odmítnutí
(neplatný nebo existující název, 409) zůstává obyčejnou JSON odpovědí.
Hashe z cache se do průběhu počítají hned jako hotové.

**Průběh provedení.** `POST /api/import/<id>/provest` odpovídá streamem
NDJSON: `{"typ":"start", souboru, bajtu}`, po každém souboru
`{"typ":"soubor", operace}`, u souborů nad 64 MB navíc po každých 64 MB
`{"typ":"prubeh", z, bajtu}`, nakonec `{"typ":"vysledek", …}` (dosavadní
tvar výsledku). Odmítnutí před začátkem kopírování (403, 409, 423) zůstává
obyčejnou JSON odpovědí se stavovým kódem. Klient čte stream
(`response.body.getReader()`) a posouvá ukazatel podle bajtů. Přenesený
soubor se ze stagingu a `import.json` odebere hned po přenosu, ne až na
konci. Přerušení spojení ukončí generátor: rozkopírovaný soubor se smaže
(dočasné jméno), přenesené zůstanou, zbytek čeká ve stagingu.
*Alternativy:* provedení po souborech z klienta — zamítnuto (plán, zámek
a duplicity ve výběru by se počítaly v každém volání); úloha na pozadí
s dotazováním — zamítnuto (nový stav serveru, pro pár uživatelů zbytečné).

**Nová akce.** Název se validuje `EVENT_RE` + zákaz `/`, `\`, úvodní
tečky; složka vzniká `os.mkdir` (selže, pokud existuje, porovnání
existence přes `_key` proti `event_names`, kvůli SMB). Po vytvoření
server pro relaci získá zámek nové akce (aby ji mezitím nikdo neotevřel
uprostřed přenosu) a po importu ho ponechá klientovi, který akci
otevírá.

**Zámek.** Import do stávající akce: klient před potvrzením požádá
o zámek stávajícím `POST /api/akce/<akce>/zamek`; `execute` vyžaduje
`locks.holds` jako `uklid/provest`. Bez zámku 423, staging zůstane.

**Dočasné soubory v archivu.** Prefix `.import-` se přidá do
`archive.is_metadata`, aby ho sken, počty v seznamu ani export
nepovažovaly za médium (stejně jako `.metadata-`, `.xmp-`).
Při výpadku SMB může selhat i smazání rozkopírovaného dočasného
souboru (ověřeno: `Host is down` nechal v akci dva prázdné
`.import-*.tmp`). Pojistka: provedení importu, které drží zámek akce,
nejdřív smaže `.import-*.tmp` v kořeni akce a v `RAW.ignored/` starší
než 1 h (souběžné provedení do téže akce vylučuje zámek, hodina kryje
nepřesné hodiny SMB). Smazané se zapíší do logu a do výsledku.

**Úklid stagingů.** Při startu serveru (`__main__`) smazat
`.work/import/*` s poslední aktivitou starší 7 dní. Bez plánovače.

**API.**
- `POST /api/import` → `{id}` (relace, jméno)
- `POST /api/import/<id>/soubor?jmeno=…&mtime=…` (tělo = soubor)
- `GET /api/import/<id>` → přehled (soubory, typy, data, přístroje,
  nepodporované, navržené datum)
- `POST /api/import/<id>/plan` `{cil | nova}` → stream NDJSON
  (průběh porovnání, plán)
- `POST /api/import/<id>/provest` `{cil | nova, relace}` → stream NDJSON
  (průběh, výsledek); ve vývojovém režimu 403 `vyvojovy_rezim` jako úklid
- `DELETE /api/import/<id>` → zahození

**Vlastník importu = jméno uživatele.** Import patří jménu, pod kterým
vznikl (`jmeno` v `import.json`), ne relaci (záložce): do zavedení
přihlášení je „kdo“ jméno zadané v prohlížeči, stejně jako u zámků.
Porovnání jmen jako u návrhů jmen (`names.normalize`: bez diakritiky,
velikosti písmen a pořadí slov). Požadavky nesou `jmeno` místo `relace`;
cizí import vrací 404. `GET /api/import?jmeno=…` vrátí rozpracované
importy uživatele (id, založeno, poslední aktivita, počet a velikost
souborů, zamýšlený cíl). Zvolený cíl (`cil` / `nova`) se ukládá do
`import.json` při sestavení plánu, aby ho seznam ukázal a průvodce po
návratu předvyplnil. *Alternativy:* importy viditelné všem — zamítnuto
(omylem zahozený cizí import); vazba na záložku s převzetím — zamítnuto
(krok navíc i u vlastních importů ze zavřené záložky).

**Souběh nad jedním importem.** Dvě záložky stejného uživatele nesmí
zároveň nahrávat a provádět. Server drží v paměti příznak „provádí se“
(jako zámky akcí, jeden proces): během provedení odmítne upload,
zahození i druhé provedení (409 `probiha`). Souběžné uploady z víc
záložek zůstávají povolené (zápis `import.json` je pod mutexem).

**Klient.** Nová trasa `#/import` (a `#/import/<id>` po nahrání, aby
reload stránky nepřišel o staging). Kroky jako karty jednoho pohledu:
Soubory → Přehled → Cíl → Plán → Výsledek. Tlačítko „Importovat“
v hlavičce seznamu akcí a na ploše akce (`#/import?cil=<akce>`).
Na seznamu akcí nad tabulkou sekce „Moje rozpracované importy“
(jen když nějaké jsou): datum založení, počet a velikost souborů,
zamýšlený cíl, poslední aktivita, tlačítka Pokračovat (`#/import/<id>`)
a Zahodit.
Výběr přes `<input type=file multiple>`, `<input webkitdirectory>`
a drag&drop (`DataTransferItem.webkitGetAsEntry` pro složky).

## Risks / Trade-offs

- [Upload desítek GB přes HTTP vlákno Werkzeugu] → streamování po
  blocích, žádný multipart; dev server zvládne, ale pomalé spojení drží
  vlákno. Přijatelné pro pár uživatelů.
- [Místo na disku `.work`] → před uploadem kontrola `shutil.disk_usage`
  proti součtu velikostí ohlášených klientem; odmítnout s chybou.
- [Kontrola cíle a `os.rename` nejsou atomické] → stejné jako u úklidu,
  souběh vylučuje zámek akce; mimo aplikaci (ruční kopírování na SMB)
  zbývá malé okno.
- [Hash akce na SMB] → jen soubory stejné velikosti, cache podle mtime.
- [Prohlížeč nemusí dát `lastModified` složky / některé prohlížeče
  nepodporují `webkitdirectory`] → výběr jednotlivých souborů funguje
  vždy; chybějící mtime = čas uploadu (EXIF datum to neovlivní).
- [Nová akce bez souborů po selhání všech přenosů] → prázdná složka
  zůstane; výsledek to uvede (mazat složky v archivu import nesmí).
- [Werkzeug zjistí odpojení klienta až při zápisu do odpovědi] → průběh
  se posílá i uvnitř velkých souborů (po 64 MB), takže zavření záložky
  zastaví kopírování nejpozději po dalších 64 MB.

## Migration Plan

Bez migrace dat. Nasazení = nová verze serveru; `.work/import/` vznikne
při prvním importu. Návrat = starší verze, staging smazat ručně.

## Open Questions

- HEIC z iPhonů: `scan.MEDIA_EXT` ho nemá, import ho zatím odmítne
  jako nepodporovaný. Rozšíření je samostatná změna (náhledy, Immich).
- Podsložky výběru jako skupiny: podsložky mívají význam, např.
  `přetřídit/DOD 2015` je dělí podle fotografů. Import je zatím
  zplošťuje a cesta ve výběru (`cesta` v `import.json`) se po přenosu
  ztratí. Navázat lze samostatnou změnou: předat rozdělení podle
  podsložek průvodci akce jako návrh skupin (místo nebo vedle návrhu
  podle přístroje), u nové akce i stávající bez `_metadata.json`.
