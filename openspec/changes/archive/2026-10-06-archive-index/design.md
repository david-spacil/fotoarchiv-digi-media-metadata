## Context

Kořen archivu obsahuje složky akcí, nezpracované složky (`přetřídit`,
`přednášky SKLEP TIC`) a ručně vedený `_metadata.xlsx`. Server
i příkaz `exportovat` pracují přes `Workspace` (`archive.py`), který
rozlišuje vývojový a produkční režim. Seznam akcí se stavem už počítá
`Workspace.list_events`, výsledné hodnoty souboru `model.resolve`,
soubory kořene `scan.root_files` a náhledy s cache `thumbs.py`.
Formát obou souborů byl odsouhlasen na mockupech nad reálným archivem
(motivace viz proposal.md).

## Goals / Non-Goals

**Goals:**
- Index vzniká z týchž funkcí, které používá aplikace (stav, dědění,
  počty souborů), aby se s nimi nerozcházel.
- Opakované generování bez změny nesahá na disk.

**Non-Goals:**
- Volba titulní fotky v aplikaci.
- Strojově čitelný index (CSV, JSON) — strojově se čte `_metadata.json`.
- Index jednotlivé akce ve složce akce.
- Úprava nebo smazání `_metadata.xlsx`.

## Decisions

**Nový modul `fotoarchiv/index.py`** se dvěma vrstvami: `collect(ws)`
vrátí seznam záznamů akcí (čistá data), `render_md(zaznamy)`
a `render_html(zaznamy, odkaz)` z nich udělají text a `write(ws)`
zapíše oba soubory. Rendery jsou čisté funkce, testují se bez disku.

**Volání v místech, ne v `xmp.export`.** `xmp.export` volá i kontrola
nanečisto a `exportovat` bez akce ho volá pro každou akci; generování
uvnitř by běželo zbytečně a opakovaně. Proto `write(ws)` volají
`akce_export`, `akce_finish` a `import_execute` v `app.py` po úspěchu
a `exportovat` v `__main__.py` jednou po smyčce. Výsledek (varování)
přidají do odpovědi pod klíčem `index`. Alternativa háček po uložení
`_metadata.json` zamítnuta: ukládá se příliš často.

**Zápis jen při změně.** Obsah bez časového razítka, zápis přes
`xmp.write_atomic` po porovnání s diskem — stejně jako sidecary.
Náhledy (base64 v HTML) jsou ze stejného JPEG souboru přes cache
deterministické; změní se jen při změně titulní fotky.

**Počty a stav.** Foto/video podle `scan.root_files` a `scan.is_video`
(bez `Thumbs.db`, metadat a sidecarů). Stav z `list_events`.

**Autoři.** Pro každý soubor v `soubory` výsledné `autori`
z `model.resolve`, počet na autora, řazení `(-počet, jméno)`. Zkrácení
`Příjmení, Jméno` → `Příjmení J.`; jméno bez čárky beze změny.

**Markdown přes `tabulate`** (`tablefmt="fancy_grid"`), nová závislost
v `requirements.txt`. Malá čistě pythonová knihovna; ruční zarovnání
tabulky s českými znaky by bylo křehčí. Svislé čáry tabulky nejsou
GFM, soubor se čte jako text (VS Code, Poznámkový blok); hlavička
nad tabulkou je běžný Markdown.

**HTML** se šablonou jako řetězcem v modulu (styl a skript inline),
podle mockupu: karty, hledání bez diakritiky, filtry rok a stav,
světlý a tmavý režim. Náhled `thumbs.SIZE` (320 px) z cache, vložený
jako `data:` URI. Odkazy: produkce relativní (`./<složka>/`), vývoj
`Path.as_uri()` do archivu.

**Umístění.** Produkce kořen archivu, vývoj `<work>/index/`.

## Risks / Trade-offs

- [Velikost HTML roste s počtem akcí, asi 25 kB na akci podle
  mockupu] → pro stovky akcí jednotky MB, přijatelné; při potížích
  menší náhled.
- [První generování počítá náhled pro každou akci] → jednorázově,
  dál z cache; jen první JPEG akce.
- [Zámek souboru na SMB, když má někdo `_INDEX.md` otevřený ve
  Windows] → zápis selže jen varováním, příště se zkusí znovu.
- [Index zastará mezi exporty, když se jen ukládá] → záměr; aktuální
  stav ukazuje aplikace.
- [Odkazy `file://` na složky prohlížeče na SMB nemusí otevřít
  v Průzkumníku] → odkaz aspoň ukáže výpis složky; ověřit ručně na
  Windows.

## Migration Plan

Žádná migrace dat. Po nasazení index vznikne při prvním exportu nebo
importu, případně hned `python -m fotoarchiv exportovat
--zapis-do-archivu`. `_metadata.xlsx` smaže člověk, až nebude potřeba.
