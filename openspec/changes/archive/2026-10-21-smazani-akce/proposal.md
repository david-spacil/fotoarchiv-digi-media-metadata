## Why

Akci dnes nejde z aplikace odstranit. Vzniká přitom omylem (import pod
špatným názvem nebo datem, prázdná akce), jako duplicita jiné akce nebo
s obsahem, který do archivu nepatří; jediná cesta je ruční zásah na úložišti
archivu a v Immichi. Mazání celé akce je zároveň jediná nevratná hromadná
operace v archivu, proto potřebuje pojistku. Issue #28.

## What Changes

- Admin může na ploše akce akci **smazat**: dialog vyžaduje opsat název
  akce a uvést důvod. Smazání nikdy nemaže hned — složka akce se celá
  (i s `_metadata.json`) přesune do koše `_kos.ignored/` v kořeni
  archivu pod unikátní ID a vedle obsahu vznikne záznam
  `_smazano.json` (původní název akce a složky, kdo, kdy, důvod).
- Akce v koši se nezobrazuje v seznamu akcí, v indexu ani v návrzích
  jmen a Immich ji nevidí (přípona `.ignored`).
- Admin vidí stránku **Koš** se smazanými akcemi (název, kdo, kdy,
  důvod, zbývající dny) a může akci **obnovit** pod původní složku.
- Po **7 dnech** od smazání se akce z koše **automaticky trvale smaže**
  (server při startu a jednou denně; ručně příkazem
  `python -m fotoarchiv vysypat`). Bez platného záznamu se nic nesmaže.
- Při trvalém smazání aplikace smaže v Immichi **album akce** a uklidí
  stav akce v pracovním adresáři (cache, stav alba a osob, odložené
  osoby, záznam exportu). **Mění invariant**, že aplikace v Immichi
  nikdy nemaže album.
- Smazání i obnovení dokončené akce spustí na pozadí **sken knihovny**
  v Immichi (assety hned offline, resp. zpět); obnovení i hlídání
  alba jako po dokončení. **Mění invariant**, že sken spouští jen
  hlídač po dokončení.
- Index se přegeneruje i po smazání, obnovení a vysypání.
- Ve vývojovém režimu smazání jen ukáže, co by se stalo; archiv se
  nemění.

## Capabilities

### New Capabilities

- `event-trash`: smazání akce do koše, záznam o smazání, stránka Koš,
  obnovení, automatické vysypání po 7 dnech a úklid pracovního
  adresáře; oprávnění jen pro admina.

### Modified Capabilities

- `archive-browsing`: Seznam akcí — složka koše `_kos.ignored` na první
  úrovni je výjimka ze zákazu měnit ostatní složky; odkaz na Koš pro
  admina.
- `immich-people`: Album akce — výjimka ze zákazu mazat album pro akci
  vysypanou z koše.
- `archive-index`: Okamžiky generování — index se přegeneruje i po
  smazání, obnovení a vysypání akce.

## Impact

- `fotoarchiv/archive.py` (koš: přesun, záznam, obnovení, vysypání),
  nový modul pro koš, `app.py` (endpointy, admin kontrola, denní
  vysypání), `__main__.py` (příkaz `vysypat`), `albums.py` (smazání
  alba), `index.py`, `lock.py` (zámek při mazání).
- Klient `fotoarchiv/static/`: tlačítko a dialog na ploše, stránka Koš.
- Immich: nové oprávnění klíče `album.delete`; test připojení ho má
  hlásit.
- AGENTS.md (invariant o albech a mazání), `docs/` (návod, návrh
  archivu, příkazy), testy Pythonu i JS.
- Originály se dál nemění; jediné trvalé mazání je vysypání koše.
