## Context

Úklid (`cleanup.py`) dnes plánuje a provádí přesuny podsložek a RAWů
a běží jen v průvodci při prvním otevření akce. Plán se staví ze stavu
disku a voleb klienta, server ho před provedením sestaví znovu. Mřížka
už umí hromadný výběr (klik, Ctrl, Shift, tažení), lupa sdílí výběr.
XMP sidecary README popisuje, ale kód je zatím negeneruje.

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
- **`VYRAZENE = "vyrazene.ignored"`** vedle `RAW_DIR`; `_move()` zakládá
  cílovou složku pro obě. Název bez diakritiky a bez úvodní tečky (glob
  `*` v `**/*.ignored/**` nebere jména začínající tečkou).
- **Úklid z plochy = stávající dialog/krok úklidu** v režimu, kde
  podsložky a RAWy z kořene nejsou ve hře (`volby` prázdné,
  `raw_v_koreni: false`), jen vyřazení. Průvodce při prvním otevření
  vyřazení nemá (bez `_metadata.json` nic označené není).
- **Del** v obsluze `keydown` vedle Enter/Esc, se stejnými výjimkami
  (formulářová pole, otevřený dialog); funguje v mřížce i lupě.

## Risks / Trade-offs

- [Ztráta ručních údajů vyřazeného souboru: záznam se odstraní a sidecar
  zatím nevzniká] → Implementovat až po změně generování XMP, nebo do té
  doby záznam neodstraňovat (viz Open Questions).
- [Neuložená změna označení mezi zobrazením plánu a provedením] → Server
  staví plán znovu z uloženého stavu; klient ukládá před plánem
  i před provedením.
- [Přesun mění cestu, Immich by bral jako smazaný asset] → Žádoucí
  (soubor se má z Immiche ztratit); stejně platí „dělat před
  napojením“.

## Open Questions

- **XMP sidecar k vyřazenému souboru.** Před odstraněním záznamu se má
  zapsat `vyrazene.ignored/<soubor>.xmp` s rozepsanými hodnotami
  generátorem ze změny `add-xmp-export`; existující sidecar v kořeni se
  má přesunout se souborem. Tahle změna se proto implementuje až po
  `add-xmp-export`; přesná podoba (sidecar i ve vývojovém režimu?, tag
  `vyrazeno`?) se doladí tehdy.
