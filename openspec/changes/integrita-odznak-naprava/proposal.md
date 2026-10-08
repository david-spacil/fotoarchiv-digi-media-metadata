# Proposal

## Why

Kontrola poškozených souborů (issue #10, varianta A/B) umí poškození
poznat při importu a příkazem `zkontrolovat`, ale v prohlížené akci se
nic nevidí: poškozený soubor v archivu nemá žádnou stopu v UI, nemá jak
ho z archivu decentně dostat a u falešné pozitivity dekodéru nemá jak
rozhodnout „soubor je přesto v pořádku“.

## What Changes

- **Kontrola při generování náhledu:** při miss cache náhledů se soubor
  stejně čte — controla integrity se spustí a výsledek se uloží do
  cache integrity. Prohlížením akce se zásobník výsledků plní sám.
  Při hitu obou cache se soubor nečte vůbec.
- **Odznak „N poškozených“:** v seznamu akcí i na ploše akce, počet
  z cache integrity (bez souborů ručně potvrzených a bez vyřazených).
  Dlaždice poškozeného souboru se vizuálně označí s důvodem v tooltipu.
- **Ruční přehodnocení:** u souboru označeného jako poškozený může
  uživatel potvrdit „v pořádku“ (falešná pozitivita dekodéru). Potvrzení
  se uloží jako příznak u záznamu souboru v `_metadata.json`,
  přehodnocený soubor se nepočítá do odznaku ani neoznačuje dlaždice.
- **Náprava poškozeného souboru v aplikaci:** poškozený soubor lze
  vyřadit po stávající cestě `vyradit` → `k_odstraneni.ignored/`
  (sidecar, zápis metadat, zámek akce, produkční režim) — žádné nové
  složky ani nový mechanismus. Záznam se z `_metadata.json` odstraní
  stejně jako u ručního vyřazení.

## Capabilities

### New Capabilities

(žádná)

### Modified Capabilities

- `file-integrity`: spouštění kontroly při generování náhledu, souhrn
  poškozených z cache pro seznam akcí a detail akce, ruční přehodnocení
  *poškozený → v pořádku* s uložením do metadat.
- `archive-browsing`: odznak počtu poškozených v seznamu akcí a na
  ploše akce, označení dlaždice poškozeného souboru, dialog
  přehodnocení.
- `metadata-model`: nový příznak u záznamu souboru
  `overeno` (viz design D3) — ani odznak ani
  kontrola ho nepočítají jako poškozený.

## Impact

- Kód: `app.py` (kontrola v `thumb_response`, souhrny v listu/detailu,
  dlaždice), `archive.py` (`list_events` o počet), `integrity.py`
  (čtení souhrnu z cache), `model.py` + `static/inherit.js` (příznak),
  `static/app.js` + `style.css` (odznak, dlaždice, dialog).
- Data: `_metadata.json` o nepovinný příznak u souboru; sidecary se
  příznakem nezapínají (náprava používá stávající cestu discard).
- Cache: `.work/cache/kontrola/<akce>.json` se nově plní i z náhledů.
- Testy: Python (souhrny, příznak, kontrola při náhledu) + JS
  (odznak, přehodnocení).
