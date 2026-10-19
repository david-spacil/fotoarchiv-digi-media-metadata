[← Dokumentace](../README.md)

# Archiv

- Na první úrovni složky akcí `YYYY-MM-DD název`. Zpracovávají se jen
  ty; ostatní (`přednášky SKLEP TIC`, `fotky mimo akce`) se nechávají
  beze změny. Výjimkou je generovaný index `_INDEX.html` a `_INDEX.md`
  (viz [Výstupy](vystupy.md)) a `přetřídit`, ze které v produkčním
  režimu přesouvá soubory import
  (viz [Import ze složky přetřídit](../navod/import-z-pretridit.md)).
- **Nedokončená akce je skrytá před Immichem** (issue #13): její složka
  má příponu `.ignored` (`2026-04-28 kontrola Stezky.ignored`), takže ji
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
