# Design

## Context

Motivace viz proposal.md. Rozhodnutí o souřadnicích místa je dnes
vidět jen ve dvou částech klienta (`fotoarchiv/static/app.js`):

- `placeBlock`: fieldset „Souřadnice místa …“ v panelu výběru. U
  rozhodnutého místa ukáže `gps` a `popis`.
- `placeChooser`: radio seznam kandidátů z `/api/geokodovani`, každý
  jako `<label class="candidate">` s názvem, popisem a souřadnicemi.
  Pod seznamem je atribuce OSM.

Lišta míst a kontrolní stránka dokončení ukazují jen místa bez
rozhodnutí, odkaz by tam nikdy nebyl. Hodnotu `osm` skládá
`geocode.candidate` jako `f"{osm_type}/{osm_id}"` bez kontroly.
Kandidáti se cachují už v tomto tvaru (`.work/cache/geokodovani.json`),
takže stará cache může obsahovat cokoli, co tehdy vzniklo.

## Goals / Non-Goals

**Goals:**
- Odkaz vzniká z dat (`_metadata.json`, cache) jen přes jednu
  ověřovací funkci. Do `href` se nikdy nedostane jiná hodnota než URL
  na openstreetmap.org.
- Funkce je čistá a testovatelná v `node --test` bez DOM.

**Non-Goals:**
- Nepromítat `osm` do XMP, indexu ani na kontrolní stránku.
- Nemigrovat ani nečistit existující `_metadata.json` a cache.
- Nedotahovat k objektu OSM nic dalšího (náhled mapy, Wikidata).

## Decisions

### Ověření tvaru v samostatném modulu `osm.js`

`osmUrl(osm)` vrátí `https://www.openstreetmap.org/<typ>/<id>`, jen
když hodnota je řetězec odpovídající `^(node|way|relation)/[1-9]\d*$`,
jinak `null`. Modul s jedinou funkcí a hlavičkovým komentářem podle
vzoru `fronta.js` či `pohyb.js` a test `tests/js/osm.test.mjs`.

*Alternativy:* přímo v `app.js` (netestovatelné, `app.js` se v Node
neimportuje), nebo jen prefix bez kontroly. Pevný prefix by sice
zabránil `javascript:` URL, ale hodnota `None/None` nebo cesta
s `../` by vedla na nesmyslnou či jinou stránku OSM.

### Odkaz v nové kartě

`target="_blank" rel="noopener noreferrer"`. Plocha drží neuložené
změny a zámek akce, takže odchod ze stránky by je ohrozil. `noreferrer`
nepošle OSM adresu interní aplikace.

*Alternativa:* stejná karta s varováním `beforeunload`. Zbytečné
tření u čistě informativního odkazu.

### Umístění a text odkazu

- `placeBlock`: za `popis` na stejném řádku `p.meta` krátký odkaz
  „OSM“ s `title` „Objekt na OpenStreetMap (relation/439179)“.
  Tlačítko Změnit zůstává tam, kde je.
- `placeChooser`: na konci textu kandidáta (za souřadnicemi) stejný
  odkaz „OSM“. Odkaz je uvnitř `<label>`. Klik na interaktivní
  potomek labelu podle HTML neaktivuje radio, takže odkaz kandidáta
  nevybere. Ověřuje se v prohlížeči (úkol 3.2), stačí bez
  `stopPropagation`.

Krátký text drží řádek kandidáta úzký i v mobilní verzi (změna
`mobilni-verze`). Plnou hodnotu ukáže `title`.

*Alternativa:* ikona místo textu. V `icons.js` vhodná ikona není
a text „OSM“ zároveň odkazuje na atribuci pod seznamem.

### Server: `osm` jen s typem i id

`geocode.candidate` přidá `osm` jen když `osm_type` i `osm_id` jsou
neprázdné. Zbytek kandidáta se nemění. Validace tvaru zůstává na
klientovi: server jen přestane vyrábět `None/None` a nové hodnoty
v cache i v archivu budou čisté.

*Alternativa:* stejný regex i na serveru. Duplikuje pravidlo, které
klient potřebuje stejně kvůli staré cache a starým `_metadata.json`.

## Risks / Trade-offs

- [Stará cache s `None/None`] → klient odkaz neukáže. Cache jde
  smazat, Nominatim se zeptá znovu.
- [OSM objekt mezitím smazán nebo sloučen] → odkaz vede na stránku
  OSM s historií či chybou. Pro traceback je to správně: ukazuje, co
  bylo zdrojem. Souřadnice v archivu se nemění.
- [Odkaz v labelu nedopatřením změní výběr kandidáta] → ověřit
  v prohlížeči. Kdyby ano, odkaz přesunout za `<label>`.

## Migration Plan

Žádná migrace. Nasazení = nová verze klienta a serveru. Návrat
na starší verzi jen odkazy skryje, data se nemění.
