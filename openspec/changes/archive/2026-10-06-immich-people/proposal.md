## Why

Osoby na fotkách umí Immich rozpoznat a pojmenovat automaticky;
ruční vyplňování v aplikaci je zbytečná práce a vedlo by ke dvěma
zdrojům, které se rozcházejí. Export osob do tagů `osoba/…` byl od
začátku chybou: Immich z nich osoby (`Person`) nevytvoří a v Immichi by
byly dvakrát. Immich zároveň neumí obličeje zapsat ven (diskuze
#15083), takže pojmenované obličeje nemají jinou zálohu než jeho
databázi.

## What Changes

- **BREAKING** Osoby na fotkách se v aplikaci už nezadávají. Pole
  `osoby` z modelu mizí; u souboru se ukládají pojmenované obličeje
  `obliceje: [{jmeno, oblast}]` s oblastí normalizovanou ve tvaru MWG.
  Formulář souboru ukáže jména jen pro čtení; u skupiny a akce nic.
- Server pravidelně (a na tlačítko) načte z Immiche pojmenované
  obličeje a zapíše je do `_metadata.json`. Akce zamčené uživatelem
  přeskočí, nepojmenované obličeje ignoruje.
- **BREAKING** Sidecary už neobsahují tagy `osoba/…`.
- Volba `exportovat --obliceje` pro obnovu: přidá do sidecarů oblasti
  obličejů (MWG), aby je Immich s „Import faces from metadata“ načetl
  zpět i s osobami.
- Nastavení připojení k Immichi (adresa, API klíč jen pro čtení)
  v aplikaci; klíč se ukládá do pracovního adresáře a do prohlížeče se
  nevrací.
- Ručně zadané osoby se zahodí: `osoby` na kterékoli úrovni se
  ignorují a při uložení odstraní.

## Capabilities

### New Capabilities
- `immich-people`: připojení k Immichi, synchronizace pojmenovaných
  obličejů do `_metadata.json`, párování souborů a jmen.

### Modified Capabilities
- `metadata-model`: místo `osoby` jen `obliceje` u souboru, nedědí se,
  zapisuje je jen synchronizace.
- `metadata-workspace`: jména z obličejů jen pro čtení, jen u souboru.
- `xmp-export`: bez tagů `osoba/…`; oblasti obličejů jen s volbou pro
  obnovu; synchronizace nemění stav exportu.
- `person-names`: jména i z obličejů; našeptávání už jen u autorů
  a účastníků.

## Impact

- Nový modul `fotoarchiv/immich.py` (klient API, synchronizace),
  vlákno v serveru, nové API nastavení v `app.py`.
- `xmp.py` (bez osob, MWG regiony s volbou), `__main__.py`
  (`exportovat --obliceje`), `model.py` + `static/inherit.js` a jejich
  fixtury, `names.py`, `static/app.js` (pole osob, stránka nastavení).
- Rozměry originálu při exportu pro obnovu (Pillow, už závislost).
- Nový soubor `.work/immich.json` (adresa, klíč, práva `0600`).
- Klíč potřebuje oprávnění ke čtení osob, assetů a obličejů
  (`face.read`).
- Odchozí HTTP na server Immiche; testy na něj nesahají.
- README (datový model, Výstupy, Aplikace), AGENTS.md (invarianty).
- Souvisí s `add-login`: dokud není přihlášení, nastavení může změnit
  kdokoli, kdo na server dosáhne.
