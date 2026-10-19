[← Dokumentace](../README.md)

# Podsložky a RAW

Zpracovává se jen kořen složky akce. Kořen má zůstat čistý pro
prohlížení: jen fotky a videa, která patří do Immiche.

- **Podsložky:** u každé podsložky bez přípony `.ignored` se průvodce
  zeptá, např. *„Složka `Video` obsahuje 22 souborů. Přesunout je mezi
  soubory akce, nebo složku ponechat stranou?“* Pro rozhodnutí ukáže až
  8 souborů rovnoměrně z jejích fotek a videí (náhled s názvem, klikem
  zvětšit); bez fotek a videí jen názvy ostatních souborů.
  - *Přesunout:* obsah jde do kořene, prázdná složka (včetně
    `Thumbs.db`) se smaže.
  - *Ponechat:* složka se přejmenuje na `název.ignored` a dál se jí
    průvodce nevšímá.
- **Přípona `.ignored` je jediný záznam o ignorování** — nikde jinde se
  seznam ignorovaných složek nevede. Immich ji vyloučí jedním vzorem.
- **RAW** (`rw2`, `cr2`, `cr3`, `nef`, `arw`, `dng`, `orf`, `raf`, bez
  ohledu na velikost písmen) do Immiche nejde a nepáruje se s JPG.
  - Podsložka, kde RAWy tvoří většinu souborů, se při ponechání
    přejmenuje na `RAW.ignored` bez ohledu na původní název (`raw`,
    `RAWy`, …).
  - RAWy v kořeni průvodce nabídne přesunout do `RAW.ignored`.
- **Vyřazené soubory** (nepovedené fotky, duplicity) se nemažou: soubory
  označené na pracovní ploše úklid přesune do `k_odstraneni.ignored`
  v kořeni akce. Před přesunem zapíše vedle cíle sidecar s rozepsanými
  údaji souboru (bez tagu o vyřazení — vyřazení značí jen složka),
  sidecar v kořeni odstraní a po přesunu smaže záznam souboru
  z `_metadata.json`. Blokuje i existující `<soubor>.xmp` v cíli;
  selže-li zápis sidecaru, soubor zůstane v kořeni i se záznamem.
  Vrácení: soubor ručně přesunout zpět, příští načtení ho přidá jako
  nový soubor bez ručních údajů.
- **Ostatní soubory** v kořeni — nepodporované (PDF, dokumenty, zipy,
  TIFF…) a osiřelé sidecary (`<soubor>.xmp` bez souboru) — úklid
  přesune do `ostatni.ignored` v kořeni akce; v průvodci je přesun
  předem zapnutý. Sidecar, jehož soubor přijde do kořene z podsložky,
  osiřelý není.
- Přesun nikdy nepřepíše existující soubor; operace se shodou názvů se
  přeskočí a nahlásí, ostatní proběhnou a podsložka, ze které něco
  zbylo, se nesmaže. Pokud `RAW.ignored`, `k_odstraneni.ignored` nebo
  `ostatni.ignored` už existuje, soubory se do ní přidají.
- Přesuny a přejmenování mění cesty, které by Immich bral jako nové
  assety. Proto se mají udělat před napojením archivu do Immiche.

## Kontrola akce

Kontrola kořene akce najde, co v něm nepatří nebo si odporuje: soubor,
který není fotka, video ani RAW (*nepodporovaný*), osiřelý sidecar,
RAW v kořeni, podsložku bez `.ignored` a záznam v `_metadata.json`, ke
kterému v kořeni není soubor. Čte jen výpis kořene a `_metadata.json`
(ne obsah souborů), takže běží i při každém načtení seznamu akcí.
Nehlásí `Thumbs.db`, `_metadata.json`, sidecary se souborem, dočasné
soubory aplikace ani obsah podsložek. Názvy porovnává bez ohledu na
velikost písmen a NFC/NFD (`a.JPG.xmp` patří k `a.jpg`).

Seznam akcí ukáže u akce s nálezy štítek „k vyřešení“ (počty
v popisku), lišta pracovní plochy nálezy po druzích (klik vypíše názvy)
a kontrolní stránka dokončení je uvede mezi kontrolami k vyřešení —
dokončit jde i s nimi. Všechno kromě záznamu
bez souboru napraví **Uklidit…**
(viz [Vyřazení a úklid](../navod/vyrazeni-a-uklid.md)); záznam bez souboru
zůstává i s ručními údaji, vrácený soubor se k němu znovu připojí.
