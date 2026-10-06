## Why

Přehled akcí v kořeni archivu je dnes ručně vedený `_metadata.xlsx`,
který zastarává a duplikuje údaje z `_metadata.json`. README slibuje
generovaný CSV index, ten ale neexistuje a pro člověka, který archiv
prochází v Průzkumníku, se nehodí (varování jen jako řádek dat,
středník a BOM v Excelu).

## What Changes

- Aplikace generuje do kořene archivu dva indexy všech akcí:
  - `_INDEX.html`: katalog s titulní fotkou, údaji akce, hledáním
    a filtry podle roku a stavu, odkazem do složky akce. Jeden soubor
    bez závislostí, čitelný i bez JavaScriptu.
  - `_INDEX.md`: hlavička s upozorněním, že je soubor generovaný
    a úpravy nemají smysl, a tabulka akcí (`tabulate`, `fancy_grid`).
- Autoři v obou indexech jsou seřazení podle počtu jejich souborů
  v akci.
- Index se přegeneruje po importu do archivu, po exportu XMP (tlačítko
  Exportovat, dokončení akce) a po příkazu `exportovat`; zapíše se jen
  při změně obsahu. Při běžném ukládání `_metadata.json` ne.
- Ve vývojovém režimu jde index do pracovního adresáře, v produkčním
  do kořene archivu.
- Plán CSV indexu z README se ruší. Ruční `_metadata.xlsx` aplikace
  nechává beze změny; smazat ho je na člověku.

## Capabilities

### New Capabilities
- `archive-index`: generovaný index akcí archivu (HTML a Markdown),
  obsah, řazení, okamžiky generování a umístění podle režimu.

### Modified Capabilities
- `archive-browsing`: soubory první úrovně se nemění, s výjimkou
  indexu, který zapisuje aplikace.

## Impact

- Nový modul `fotoarchiv/index.py`; volání z `app.py` (export,
  dokončení, import) a z `__main__.py` (`exportovat`).
- Náhledy přes stávající cache v `thumbs.py`, dědění autorů přes
  `model.py`.
- Nová závislost `tabulate` v `requirements.txt`.
- README: sekce Výstupy (index místo CSV).
