# Design

## Context

Kontrola integrity (`integrity.py`) umí klasifikovat soubor a cachuje
výsledky per-akce do `.work/cache/kontrola/<akce>.json` (klíč =
relativní cesta, záznam `verze/size/mtime_ns/vysledek`). Náhody počítá
`thumbs.thumbnail()` s vlastní cache; při miss čte originál (fotka
Pillow s `draft`, video ffmpeg). Seznam akcí (`archive.list_events`)
už počítá per-akci `kontrola` z nálezů konzistence — stejný vzor
použijeme pro počet poškozených. Vyřazení souboru (`vyradit` →
`k_odstraneni.ignored/`, sidecar, smazání záznamu, zámek, produkční
režim) je hotové a testované.

## Goals / Non-Goals

**Goals:**
- Plnit cache integrity pasivně při prohlížení (miss náhledu).
- Vidět poškozené v seznamu i na ploše; rozlišit je od vyřazených.
- Umožnit ruční přehodnocení *poškozený → v pořádku* se stopou
  v `_metadata.json`.
- Nápravu vést výhradně stávající cestou `vyradit` (rozhodnutí ze
  zadání: žádné nové složky).

**Non-Goals:**
- Žádná nová `.ignored` složka (`POSKOZENE.ignored` se nezavádí).
- Žádné automatické mazání souborů; náprava zůstává potvrzené
  vyřazení v úklidu.
- Žádný hromadný přepočet archivem při startu serveru.

## Decisions

### D1: Kontrola při miss náhledu, ne při hitu
V `thumb_response` se před voláním `thumbs.thumbnail()` podívá do
cache kontroly akce (`integrity.cached`); je-li výsledek platný,
nic se neděje. Při miss náhledu *i* miss kontroly se kontrola
spustí na celém souboru a výsledek zapíše do cache akce.
Alternativa (kontrolovat vždy) by četla soubor u každého náhledu —
vyloučeno. Cena: první náhled velké fotky je pomalejší o jedno
průchodové čtení; únosné, `zkontrolovat` dělá totéž.
Výjimka: náhled z podsložky při úklidu (`uklid/nahled`) se
nekontroluje — mimo kořen akce, mimo dosah cache i odznaku.

### D2: Souhrn počítá `list_events` z cache JSONu
`list_events` přídá klíč `poskozene: N`: načte
`<work>/cache/kontrola/<nazev>.json`, spočítá záznamy
`vysledek.stav != "ok"` a odečte `overeno`/`vyradit` ze
`_metadata.json`, který pro list čte už dnes. Detail akce přidá
`poskozene: {název: {stav, duvody}}` pro dlaždice. Žádné staty
souborů, žádná I/O nad mez — precedens: dnešní `kontrola`
konzistence. Cache importu (`import-*`, `pretridit-*`) se do
souhrnů nemísí.

### D3: Příznak `overeno` u záznamu souboru
Jméno `overeno` (krátce, vedle `vyradit`); je v `LOCAL_KEYS["soubor"]`
(nedědí se), xmp/index ho ignorují jako `vyradit`. Klient ho přepíná
jako `vyradit` přes běžný autosave — žádný nový endpoint. Server
při uložení bere `overeno` jako běžné ruční pole (na rozdíl od
`obliceje`).

### D4: Náprava = existing discard
Chybí jakýkoli nový endpoint: dlaždice poškozeného soubora má v
menu „Vyřadit…“, které nastaví `vyradit: true`; úklid z plochy
(`z_plochy`) odnese soubor do `k_odstraneni.ignored/` i se sidecarem
a maže záznam (včetně `overeno`) stávajícím kódem. Odznak pak
soubor nepřestane počítat automaticky: vyřazené se ze souhrnu
odečítají (D2).

### D5: UI bez nového endpointu
Odznak v seznamu: `badge poskozene` (barva `#fed7aa` jako
`nekompletni`? — ne, výraznější červená `#feb2b2`, text
„N poškozené/é/ých“). Plocha: v liště `span.info.poskozene`
jako dnešní „N souborů k vyřazení“, dlaždice třída `damaged`
+ `title` s důvodem, přepínač „Považovat za v pořádku“ v akci
dlaždice vedle „Označit k vyřazení“.

## Risks / Trade-offs

- [První náhled je pomalejší o celé čtení souboru] → jen jednou na
  soubor; cache podle size+mtime; videos kontrola potřebuje ffprobe
  stejně jako náhled ffmpeg.
- [Odznak je matoucí, dokud se cache neplní] → CLI `zkontrolovat`
  existuje a plocha plní cache pasivně; nulový souhrn bez cache se
  navenek neliší (spec).
- [`overeno` zakryje reálné poškození po obnově souboru ze zálohy] →
  cache kontroly je vázaná na size+mtime, nový soubor se vyhodnotí
  znovu, ale `overeno` v metadatech zůstane; to je záměr —
  rozhodnutí uživatele váže na konkrétní záznam, nová verze souboru
  má nový záznam po skenu.
- [Video miss náhledu + kontrola = ffmpeg i ffprobe] → akceptováno,
  obojí v řádu setin sekund na běžném HW.

## Open Questions

- Text odznaku pro 1/2-4/množné tvary — dořešit v kódu podle vzoru
  `plural()` v `app.js`.
