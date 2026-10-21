[← Dokumentace](../README.md)

# Archiv

- Na první úrovni složky akcí `YYYY-MM-DD název`. Zpracovávají se jen
  ty; ostatní (`přednášky SKLEP TIC`, `fotky mimo akce`) se nechávají
  beze změny. Výjimkou je generovaný index `_INDEX.html` a `_INDEX.md`
  (viz [Výstupy](vystupy.md)) a `přetřídit`, ze které v produkčním
  režimu přesouvá soubory import
  (viz [Import ze složky přetřídit](../navod/import-z-pretridit.md)),
  a koš smazaných akcí `_kos.ignored` (níže).
- **Nedokončená akce je skrytá před Immichem** (issue #13): její složka
  má příponu `.ignored` (`2026-04-28 kontrola Naučné stezky.ignored`), takže ji
  Immich vynechá stejným vzorem jako ignorované podsložky. Akce se
  v aplikaci, v URL, u zámku i v `.work` jmenuje bez přípony; přípona je
  jen vlastnost složky. Import zakládá novou akci rovnou skrytou,
  dokončení příponu odebere
  (viz [Dokončení akce](../navod/dokonceni-akce.md)) a dokončená
  akce ji už znovu nedostane. Stávající nedokončené akce (a akce
  nakopírované do archivu mimo aplikaci) skryje jednorázově
  `python -m fotoarchiv skryt --archiv … --zapis-do-archivu` při
  zastaveném serveru; bez přepínače jen vypíše, co by přejmenoval.
  Akce, kterou Immich už načetl, z něj skrytím zmizí i s obličeji
  a po dokončení se načte znovu jako nové assety. Existuje-li složka
  s příponou i bez ní, aplikace akci ukáže jako *kolize složek*
  a nepracuje s ní, dokud jednu správce archivu neodstraní nebo
  nesloučí; nic sama nepřesouvá.
- **Smazaná akce leží 7 dní v koši** (issue #28). Smazat smí jen
  admin (viz [Smazání akce](../navod/smazani-akce.md)); celá složka
  akce se i s `_metadata.json` přesune do `_kos.ignored/<ID>/`, kde
  ID je čas smazání a náhodná přípona (`20261019T143012-7f3a`), takže
  dvě smazání stejného názvu nikdy nekolidují. Vedle obsahu je záznam
  `_smazano.json`: název akce, původní název složky (i s `.ignored`),
  kdo, kdy, důvod a stav akce vyjmutý z `.work` (vazba na album, stav
  v Immichi, počty osob, záznam exportu, odložené osoby). Nová akce
  stejného názvu tak začíná s čistým stavem a obnovení stav vrátí.
  Koš nesplňuje vzor akce a má příponu `.ignored`: seznam akcí, index,
  návrhy jmen ani Immich ho nevidí.
  - **Smazání a obnovení dokončené akce** (složka bez `.ignored`)
    spustí na pozadí sken knihovny v Immichi (viz [Immich](immich.md)):
    po smazání Immich assety hned označí offline a přesune do svého
    koše, po obnovení je při skenu vrátí. Obnova s obličeji tedy
    předpokládá, že koš Immiche drží assety déle než 7 dní (výchozí
    30 dní); při vypnutém koši Immiche nebo kratší lhůtě se akce po
    obnovení rozpozná znovu.
  - **Obnovení** vrátí složku pod původní název; když mezitím vznikla
    akce stejného názvu (s příponou i bez), odmítne se.
  - **Vysypání** je jediné trvalé mazání v aplikaci: server při startu
    a pak jednou denně (nebo příkaz `python -m fotoarchiv vysypat
    --zapis-do-archivu`) smaže akce, jejichž záznam je starší než
    7 dní, náhledy jejich souborů z cache a album akce v Immichi
    (assety nemaže; viz [Immich](immich.md)). O stáří rozhoduje jen čas
    v záznamu; složku bez platného záznamu nesmaže nikdy (řeší ji
    správce ručně). Záznam se maže poslední, přerušené vysypání
    dokončí další běh. Ve vývojovém režimu se nic nemaže.
- `přetřídit` drží nezatříděné akce k importu, `fotky mimo akce`
  materiál, který akcí není (sbírky, portréty, výběry pro web, podklady
  na večírky). Kopie, které při zploštění `přetřídit` vyšly jako
  duplicity, leží v `přetřídit/_duplicity.ignored/` (viz issue #5);
  složky a podsložky s příponou `.ignored` import nenabízí ani
  nepřesouvá.
- Ve složkách jsou JPG, mp4, RW2, občas png/zip a `Thumbs.db`
  (ignorovat). Některé akce mají podsložky (`RAW`, `Video`, …), viz
  [Podsložky a RAW](podslozky-a-raw.md).
- Zdroje se liší kvalitou metadat:

  | vzor názvu            | přístroj          | EXIF                   |
  |-----------------------|-------------------|------------------------|
  | `P*.JPG`              | Panasonic DC-G9   | datum, bez GPS         |
  | `YYYYMMDD_HHMMSS.jpg` | Samsung SM-A528B  | datum, GPS             |
  | `IMG-YYYYMMDD-WA*.jpg`| WhatsApp          | žádný, datum jen v názvu |
  | `IMG_####.jpg`        | ?                 | neověřeno              |
