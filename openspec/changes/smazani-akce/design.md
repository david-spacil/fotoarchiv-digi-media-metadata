## Context

Motivace viz proposal.md. Dnes aplikace nic v archivu nemaže: vyřazené
soubory přesouvá do `k_odstraneni.ignored`, podsložky přejmenovává na
`*.ignored` a přesun nikdy nepřepíše existující soubor. Složku akce na
disku skládá jen `Workspace.event_dir` (přípona `.ignored` u nedokončené
akce). Immich čte archiv jako externí knihovnu a vylučuje
`**/*.ignored/**`; album akce vede `albums.py` a nikdy ho nemaže.
Server běží jako jeden proces, zámky akcí jsou v paměti (`lock.py`).

## Goals / Non-Goals

**Goals:**
- Jediné trvalé mazání v aplikaci je vysypání koše; vše ostatní je
  přesun na stejném svazku, vratný do 7 dní.
- Koš je soběstačný: z obsahu `_kos.ignored` jde poznat, co je to za
  akci a kdy smí zmizet, i bez `.work`.

**Non-Goals:**
- Přejmenování a sloučení akcí (řeší jiný problém, i když by část
  omylů pokryly).
- Mazání assetů v Immichi — po vysypání je Immich sám označí jako
  offline a vyřadí podle svého nastavení.
- Nastavitelná lhůta koše a okamžité vysypání.
- Smazání jednotlivých souborů (to zůstává vyřazení a úklid).

## Decisions

### Koš ve složce `_kos.ignored` v kořeni archivu
Přesun `os.rename` na stejném svazku je okamžitý a atomický i pro
gigabajtové akce; kopie do `.work` by byla pomalá, mohla selhat
v polovině a `.work` nemusí mít místo. Název nesplňuje vzor
`YYYY-MM-DD název`, takže ho seznam akcí i index ignorují bez další
logiky, a přípona `.ignored` ho skryje Immichi.
*Alternativa:* příznak v `_metadata.json` — Immich by akci dál viděl
a akce *nezpracováno* `_metadata.json` nemá. *Alternativa:* přípona
`.ignored` u složky akce — ta už znamená „nedokončená“ a akce zůstává
v seznamu.

### Složka v koši pod unikátním ID, původní název v záznamu
`_kos.ignored/<ID>/`, ID = čas smazání `YYYYMMDDTHHMMSS` + krátký
náhodný sufix (např. `20261019T143012-7f3a`). Dvě smazání téhož názvu
tak nikdy nekolidují a výpis na NAS je seřazený podle času. Přesun
přesto použije pravidlo „nikdy nepřepsat“ (cíl nesmí existovat).

### Záznam `_smazano.json` uvnitř složky v koši
Obsah: `nazev`, `slozka` (původní název složky včetně `.ignored`),
`smazal` (jméno z relace), `smazano` (ISO čas), `duvod`, verze schématu.
Zapisuje se atomicky **do složky akce před přesunem**; selže-li
přesun, záznam se smaže a akce zůstane beze změny. Záznam ve složce
akce v kořeni archivu je mezistav jen na dobu operace pod zámkem.
O vysypání rozhoduje výhradně `smazano` v záznamu — ne ID, ne mtime;
složka bez čitelného záznamu se nikdy nesmaže a stránka Koš ji ukáže
jako neznámou (řeší ji správce ručně).
*Alternativa:* záznam ve `.work` — ztráta `.work` by koš osiřela
a hrozilo by mazání naslepo nebo věčné ležení.

### Obnovení pod původní název složky
Vrací se `slozka` ze záznamu: nedokončená akce zůstane skrytá před
Immichem, dokončená se vrátí bez přípony a Immich ji při skenu najde
na stejné cestě. Kontrola obsazenosti porovnává název akce s příponou
i bez (jako kolize přípony). `.work` akce (cache, export, stav alba) se
během pobytu v koši nemaže, takže obnova je úplná včetně vazby na
album.

### Vysypání v serveru i příkazem
Server spustí vysypání při startu a pak jednou za 24 h ve vlastním
daemon vlákně (stejný vzor jako pravidelná synchronizace Immiche).
Příkaz `vysypat` dělá totéž pro provoz bez běžícího serveru nebo pro
kontrolu; bez `--zapis-do-archivu` jen vypíše. Ve vývojovém režimu
vlákno nic nemaže (koš v archivu stejně nevznikne).
Mazání složky: `shutil.rmtree` jen pod `_kos.ignored`, s ověřením, že
cesta je přímý potomek koše (žádné symlinky ven).

### Pořadí při vysypání
1. smazat album v Immichi (je-li vazba a Immich nastaven),
2. smazat složku z koše,
3. uklidit `.work` akce — ale vazbu na album jen, když se album
   smazalo (jinak zůstane a další vysypání smazání alba zopakuje i bez
   složky).
`.work` je klíčovaný názvem akce; pokud mezitím vznikla nová akce
stejného názvu, úklid `.work` se **vynechá** (patří nové akci)
a smazání alba se provede jen podle vazby, kterou záznam zachytil
v okamžiku smazání (`album` ID v `_smazano.json`), ne podle názvu.

### Smazání alba = výjimka v `albums.py`
Nová funkce smazání alba podle ID; synchronizace ani udržování alba
dál nic nemažou. Akce v koši nejsou v `list_events`, takže je
synchronizace nevidí a jejich album nemění. Test připojení přidá do
oprávnění pro alba akcí `album.delete`.

### Oprávnění a zámek
Endpointy `/api/kos…` jdou do `ADMIN_PREFIXES`; smazání akce
(`DELETE /api/akce/<nazev>` nebo `POST …/smazat`) kontroluje admina
samo, protože prefix `/api/akce` je společný. Smazání získá zámek akce
pro relaci admina (odmítne cizí platný zámek), provede přesun
a zámek uvolní. Běžící import s cílem v mazané akci selže při provedení
jako u neexistující akce.

### Vývojový režim
Dialog proběhne celý, server vrátí plán (cílová cesta, datum vysypání)
a nic nezapíše — stejně jako úklid ve vývojovém režimu.

## Risks / Trade-offs

- [Obnova dokončené akce: Immich mezitím assety označí offline
  a po své lhůtě je vyřadí do koše Immiche] → V rámci 7 dní by sken
  měl assety na původní cestě vrátit včetně obličejů; ověřit proti
  skutečnému Immichi před nasazením (úkol v tasks). Pokud se nevrátí,
  zdokumentovat, že obnova dokončené akce znamená nové rozpoznání.
- [Vysypání je nevratné] → Lhůta 7 dní, opisování názvu, důvod v logu,
  vysypání jen se záznamem; zálohy NAS jsou mimo aplikaci.
- [Server neběží déle než 7 dní] → Vysypání proběhne při startu;
  zpoždění nevadí.
- [Selhání v půlce `rmtree` (soubor drží jiný počítač)] → Složka
  i záznam zůstanou (záznam se maže poslední), další běh to zopakuje;
  log uvede chybu.
- [Záznam `_smazano.json` v kořeni akce při pádu serveru mezi zápisem
  a přesunem] → Kontrola akce ho nahlásí jako nepodporovaný soubor;
  přesun se pak dá zopakovat smazáním, nic se neztratí.
- [Nový invariant „aplikace maže album“] → Omezeno na jediné místo
  a na album podle uloženého ID; aktualizovat AGENTS.md.

## Migration Plan

Žádná migrace dat. Klíč Immiche potřebuje oprávnění `album.delete`;
bez něj vysypání smaže složku a album nechá (chyba v logu, test
připojení ji ukáže). Rollback: starší verze `_kos.ignored` ignoruje
(nesplňuje vzor akce), koš lze vyprázdnit nebo obnovit ručně
přesunem.
