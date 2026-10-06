## Context

Úklid (`cleanup.py`) dnes plánuje a provádí přesuny podsložek a RAWů
a běží jen v průvodci při prvním otevření akce. Plán se staví ze stavu
disku a voleb klienta, server ho před provedením sestaví znovu. Mřížka
už umí hromadný výběr (klik, Ctrl, Shift, tažení), lupa sdílí výběr.
XMP sidecary generuje `xmp.py` (změna `add-xmp-export`); soubory
s `vyradit` export vynechává.

## Goals / Non-Goals

**Goals:**
- Označení k vyřazení jako běžná, vratná úprava metadat.
- Fyzický přesun jen přes úklid se stávajícími zárukami (nic se
  nepřepíše, kolize, výsledek).

**Non-Goals:**
- Mazání souborů z disku.
- Vrácení již přesunutého souboru z aplikace (ručně: přesunout zpět,
  příští sken ho přidá jako nový soubor bez ručních údajů).
- Generování XMP sidecarů (samostatná změna).

## Decisions

- **Příznak `vyradit` v záznamu souboru, ne samostatný seznam.** Mizí
  spolu se záznamem, nedědí se (skupina ani akce ho nemají) a nemusí se
  udržovat při přejmenování skupin. Alternativa: oddíl `vyradit: [...]`
  — duplicitní stav.
- **Plán čte označení z `_metadata.json` na serveru**, ne z voleb
  klienta. Server tak pracuje s uloženým stavem; klient před plánem
  uloží neuložené změny. `plan()`/`execute()` dostanou množinu
  označených názvů jako další vstup; porovnání názvů přes `_key`
  (NFC, casefold) jako u ostatních cílů.
- **Odstranění záznamů dělá endpoint provedení** po `execute()`: načte
  dokument, smaže záznamy úspěšně přesunutých souborů a uloží s kontrolou
  verze. Klient pak dokument znovu načte. Alternativa (klient smaže
  záznamy sám) by při pádu klienta nechala záznamy souborů, které už
  v kořeni nejsou.
- **`K_ODSTRANENI = "k_odstraneni.ignored"`** vedle `RAW_DIR`; `_move()` zakládá
  cílovou složku pro obě. Název bez diakritiky a bez úvodní tečky (glob
  `*` v `**/*.ignored/**` nebere jména začínající tečkou).
- **Úklid z plochy = stávající dialog/krok úklidu** v režimu, kde
  podsložky a RAWy z kořene nejsou ve hře (`volby` prázdné,
  `raw_v_koreni: false`), jen vyřazení. Průvodce při prvním otevření
  vyřazení nemá (bez `_metadata.json` nic označené není).
- **Sidecar zapisuje provedení vyřazení, ne export.** Před odstraněním
  záznamu se vždy zapíše `xmp.sidecar()` (rozepsané hodnoty) do
  `k_odstraneni.ignored/<soubor>.xmp`; záznam existuje vždy, nese
  příznak `vyradit`. Sidecar v kořeni, pokud existuje, se odstraní (je
  to generovaný výstup). Tag vyřazení se nepíše — indikátorem je
  složka. Přesun je blokovaný,
  existuje-li v cíli soubor nebo jeho `.xmp`. Ve vývojovém režimu se
  nic nepřesouvá, a tedy ani nezapisuje.
- **Del** v obsluze `keydown` vedle Enter/Esc, se stejnými výjimkami
  (formulářová pole, otevřený dialog); funguje v mřížce i lupě.

## Risks / Trade-offs

- [Ztráta ručních údajů vyřazeného souboru: záznam se odstraní a export
  soubor s `vyradit` vynechává] → Sidecar zapíše provedení vyřazení
  před odstraněním záznamu; selže-li zápis, soubor se nepřesune
  a záznam zůstane.
- [Neuložená změna označení mezi zobrazením plánu a provedením] → Server
  staví plán znovu z uloženého stavu; klient ukládá před plánem
  i před provedením.
- [Přesun mění cestu, Immich by bral jako smazaný asset] → Žádoucí
  (soubor se má z Immiche ztratit); stejně platí „dělat před
  napojením“.

## Open Questions

Žádné.
