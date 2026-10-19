[← Dokumentace](../README.md)

# Ukládání a export

- `_metadata.json` se ukládá průběžně, atomicky (dočasný soubor
  a přejmenování), v produkčním režimu do složky akce, ve vývojovém do
  `.work/metadata/<akce>/`. Rozpracovaná metadata z `.work` převezme do
  archivu jednorázově `python -m fotoarchiv prevzit` (jen u akcí, které
  `_metadata.json` v archivu ještě nemají).
- XMP sidecary se zapisují při dokončení akce (i opakovaném)
  a dávkově `python -m fotoarchiv exportovat [AKCE]` (bez akce všechny
  s `_metadata.json`; zámky nekontroluje). **Přepisují se
  jen změněné:** obsah sidecaru se generuje deterministicky (bez
  časových razítek) a porovná s obsahem na disku; zapíše se atomicky,
  jen když chybí nebo se liší. Sidecar vznikne jen k souborům se
  záznamem, v kořeni a neoznačeným k vyřazení; jiné `.xmp` se nemažou.
  Ve vývojovém režimu jdou sidecary do `.work/xmp/<akce>/`.
- Po exportu bez chyb se do `.work/export/<akce>.json` zapíše verze
  (sha256) `_metadata.json`, ze které export vznikl. Liší-li se od
  aktuální, akce má neexportované změny; bez záznamu je stav neznámý.
  Do archivu ani do `_metadata.json` se nic z toho nezapisuje.
- Před uložením `_metadata.json` aplikace ověří, že ho mezitím nezměnil
  někdo jiný; jinak uložení odmítne a nabídne znovunačtení.
