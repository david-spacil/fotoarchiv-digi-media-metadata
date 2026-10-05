## Context

`model.resolve()` už vrací výsledné hodnoty včetně GPS z místa. `datum`
je `YYYY-MM-DDTHH:MM:SS` bez zóny, u WhatsAppu `YYYY-MM-DD`; `gps` je
`[lat, lon]` v desetinných stupních. `dokonceno` je v dokumentu od
začátku (`null`) a seznam akcí podle něj ukazuje *hotovo*. Konvence
tagů a formát GPS přebíráme z `arubrno/archiv-immich` (README, oddíl
Skript pro obohacení XMP sidecarů).

## Goals / Non-Goals

**Goals:**
- Jeden generátor pro server i CLI, testovatelný bez exiftoolu.

**Non-Goals:**
- Čtení sidecarů zpět, mazání osiřelých sidecarů, napojení Immiche.
- Sidecar vyřazených souborů (změna `discard-files`).

## Decisions

- **XML skládané v Pythonu (`fotoarchiv/xmp.py`), ne exiftool.**
  exiftool zapisuje `x:xmptk` se svou verzí a spouští proces na soubor;
  obojí vadí determinismu a rychlosti nad SMB. Šablona je pevná:
  `x:xmpmeta` > `rdf:RDF` > jeden `rdf:Description` s jmennými prostory
  `dc`, `xmp`, `exif`, `digiKam`; `dc:description` jako `rdf:Alt`
  s `xml:lang="x-default"`, tagy jako `rdf:Bag`. Escapování přes
  `xml.sax.saxutils`. Bez `<?xpacket?>` obalu (u sidecaru se nepoužívá).
  Správnost ověřit jednou ručně `exiftool -X` nad vzorkem.
- **Pořadí tagů:** `akce/`, `autor/`, `osoba/`; uvnitř skupiny v pořadí
  z dokumentu (je stálé a odpovídá zadání uživatelem), duplicity pryč.
- **GPS ve formátu XMP `DDD,MM.mmmmmmK`** (stupně, minuty na 6 míst,
  N/S/E/W), jako v `archiv-immich`. Pevný počet desetinných míst drží
  determinismus.
- **Zóna přes `zoneinfo.ZoneInfo("Europe/Prague")`**: `datetime`
  s `tzinfo` dá posun podle data automaticky. Při podzimním posunu
  (hodina 2:00–3:00 dvakrát) bere `fold=0`, tedy letní čas; EXIF
  rozlišení nenese.
- **Změna = porovnání s obsahem na disku**, ne `sha256` v
  `_metadata.json` (odchylka od README). Export pak nemění
  `_metadata.json` (žádné konflikty verzí s otevřeným klientem) a pozná
  i smazaný nebo ručně upravený sidecar. Cena: přečtení malého souboru
  na SMB na každý soubor akce.
- **Atomický zápis** stejně jako u `_metadata.json` (dočasný soubor ve
  stejné složce a `os.replace`). Dočasný soubor začíná tečkou, aby ho
  sken ani počítání nebraly.
- **Endpointy** `POST /api/akce/<akce>/export` a `…/dokoncit`; oba
  vyžadují zámek, dokončení navíc nastaví `dokonceno` (ISO datum)
  uložením s kontrolou verze, jen když export neměl chyby. Kontrolu
  úplnosti dělá klient (`missing()` v `inherit.js`), server ji
  neopakuje — Python `missing` nemá a dokončení s potvrzením stejně
  povoluje neúplnou akci.
- **CLI `exportovat`** v `__main__.py` vedle `prevzit`, volitelný
  poziční název akce, `--zapis-do-archivu` jako u serveru. Zámky
  nekontroluje (jsou v paměti serveru); sidecary jsou odvozené, souběh
  s editací nic nerozbije, jen může exportovat starší stav.
- **Úpravy po dokončení `dokonceno` nenulují**, jen se ukáže „změněno
  po exportu“; uživatel znovu exportuje.
- **Záznam o exportu = verze `_metadata.json` (`version_of`, sha256
  obsahu) v `work/export/<akce>.json`**, zapsaný jen po exportu bez
  chyb. Alternativa „`_metadata.json` novější než nejnovější sidecar“
  (mtime) selže, když export nic nezapíše, protože se změnilo jen pole,
  které do sidecaru nejde. Záznam je jen v pracovním adresáři: archiv
  nemění a ztráta znamená stav *neznámý*, ne chybu. CLI používá stejný
  `--work`, takže se záznamy shodují.
- **Dokončení:** nejdřív uložit `dokonceno`, pak exportovat (export čte
  uložený dokument, záznam tak odpovídá finální verzi); při chybě
  exportu `dokonceno` vrátit na `null`.
- **Kontrola nanečisto** sdílí kód s exportem (parametr „nezapisovat“);
  volá se při otevření akce, ne po každém uložení — mezi exporty stačí
  porovnání verzí, které klient zná z odpovědi na uložení.
- **Seznam akcí** porovnává jen verze (žádné čtení sidecarů), takže
  zůstává rychlý.

## Risks / Trade-offs

- [Immich nemusí některý prvek přečíst (formát GPS, `rdf:Alt`)] →
  Před napojením ověřit na vzorku v Immichi; formát odpovídá
  `archiv-immich`, který je ověřený.
- [Zastaralé sidecary po úpravě dokončené akce] → Tlačítko Exportovat
  a CLI; zápis jen změněných je levný.
- [Osiřelé sidecary po přejmenování/vyřazení souboru] → `discard-files`
  přesune sidecar se souborem; jiné přejmenování aplikace nedělá.
- [`zoneinfo` na Windows bez systémové databáze zón] → `tzdata`
  v `requirements.txt` jen pro Windows (environment marker).
