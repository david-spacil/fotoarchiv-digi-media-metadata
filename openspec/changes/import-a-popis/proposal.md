## Why

Import a popis jsou dnes dva průvodci, které na sebe navazují jen
přes návrh skupin. Skupiny se volí v importu a znovu v průvodci akce,
název a datum nové akce se zadávají dvakrát, úklid po importu je
prázdný. Import do existující (i dokončené) akce nevynucuje žádný
popis: nové soubory skončí bez autorů. Autory přitom nejlíp zná ten,
kdo zrovna nahrává, a právě tam se na ně nikdo neptá. Průvodce je
nejúčinnější způsob, jak fotky aspoň základně popsat, takže se nemá
zrušit, ale svázat s importem.

## What Changes

- **Import a popis jako jeden průvodce:** soubory → přehled → cíl →
  plán → skupiny a autoři → výsledek. Plán (duplicity, blokované) je
  před popisem, aby se popisovalo jen to, co se opravdu přenese.
- **Cíl** u nové akce sbírá i údaje akce (název, datum od–do, popis,
  místa, účastníci), předvyplněné jako dnes v průvodci akce.
- **Nový krok Skupiny a autoři** v importu: mřížka náhledů přenášených
  médií s výchozím rozdělením (dosavadní volba skupin), ruční úpravy
  skupin jako v průvodci (přejmenovat, sloučit, nová skupina z výběru,
  přesun), připojení ke skupinám cílové akce a autoři každé skupiny
  i celé akce. Volba rozdělení a připojení se přesouvají sem z kroků
  cíl a plán. **BREAKING** (tok importu): plán už skupiny neukazuje.
- **Zápis při provedení:** u nové akce server založí `_metadata.json`
  rovnou s údaji akce, skupinami a autory; akce vzniklá importem
  průvodce akce nepotřebuje. U akce s `_metadata.json` se zapíšou nové
  skupiny s autory, stávající údaje zůstanou. U existující akce bez
  `_metadata.json` jde popis dál do návrhu skupin (nově i s autory)
  a použije ho průvodce akce.
- **Náhledy souborů importu:** nový endpoint pro náhledy nahraných
  souborů i souborů zdroje v `přetřídit`.
- **Průvodce akce:** úklid (a načtení) → údaje akce → skupiny a autoři.
  Kroky „načtení a skupiny“ a „autoři skupin“ se slučují do jednoho.
- Ve vývojovém režimu se import neprovede, popis se tedy nezapíše;
  plán a krok skupin fungují.
- Importujícího aplikace jako autora nepředvyplňuje.

## Capabilities

### New Capabilities

(žádné)

### Modified Capabilities

- `photo-import`: kroky průvodce a jejich pořadí, údaje nové akce
  v cíli, nový krok skupiny a autoři (volba a úprava skupin,
  připojení, autoři), plán bez skupin, zápis `_metadata.json` u nové
  akce, náhledy souborů importu.
- `metadata-workspace`: průvodce prvním otevřením (pořadí kroků,
  sloučený krok skupiny a autoři), skupiny a autoři z návrhu importu
  v průvodci.
- `archive-index`: nová akce z importu je v indexu *rozpracovaná*
  s údaji z importu (scénář okamžiků generování).

## Impact

- `fotoarchiv/importer.py` — zápis popisu při provedení, založení
  `_metadata.json` u nové akce, návrh skupin s autory, uložení
  rozpracovaného popisu v `import.json`.
- `fotoarchiv/app.py` — API importu (uložení popisu, náhledy),
  provedení s popisem.
- `fotoarchiv/thumbs.py` — náhledy souborů mimo akci (pracovní adresář
  importu, zdroj v `přetřídit`).
- `fotoarchiv/static/app.js` — kroky importu, sdílený krok skupiny
  a autoři pro import i průvodce akce, pořadí kroků průvodce.
- `README.md`, oddíly Tok práce a Import.
- Datový model `_metadata.json` beze změny; mění se jen pracovní
  soubory v `.work` (`import.json`, návrh skupin).
