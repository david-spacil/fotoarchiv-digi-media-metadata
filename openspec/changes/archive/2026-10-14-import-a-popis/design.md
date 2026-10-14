## Context

Import (`importer.py`, `app.py` `/api/import/…`, klient v `app.js`) má
kroky soubory → přehled → cíl → plán → výsledek. Volbu rozdělení
skupin posílá klient s plánem (`POST …/plan`, pole `skupiny`), server
ji ukládá k importu (`set_target`) a skupiny počítá `group_plan`.
Připojení ke skupinám cílové akce (`pripojit`) se posílá až
s provedením. Po přenosu `plan_groups` zapíše skupiny do
`_metadata.json`, nebo u akce bez něj do návrhu
`.work/navrhy-skupin/<akce>.json`, který použije průvodce akce
(`apply_proposal`).

Průvodce akce (`renderWizard`) má kroky úklid → načtení a skupiny →
údaje akce → autoři skupin. Krok skupin používá mřížku a panel plochy
(`renderGrid`, `renderPanel` → `renderWizardPanel`) nad `state.doc`,
krok autorů vykresluje `fieldRow` pro `autori` skupin a akce. Autoři
jsou měkce povinní: dokončení s chybějícími autory chce druhé
potvrzení.

Import nemá náhledy souborů; náhledy umí jen soubor akce
(`/api/akce/<n>/nahled/<soubor>`) a ukázky podsložek pro úklid.
Motivace viz proposal.md.

## Goals / Non-Goals

**Goals:**
- Jeden krok „skupiny a autoři“ (mřížka + panel), sdílený importem
  a průvodcem akce, nad stejnou logikou úprav skupin a dědění.
- Popis importu přežije zavření stránky a návrat k importu.
- Do archivu se nic nezapíše dřív než při provedení.

**Non-Goals:**
- Popis jednotlivých souborů (datum, místo, popis souboru) v importu;
  zůstává na ploše.
- Změna formátu `_metadata.json` nebo XMP.
- Popis importu ve vývojovém režimu do archivu (import se neprovádí).
- Úprava toku stránky Přetřídit; ta jen zakládá import jako dosud.

## Decisions

**Popis importu jako dokument ve tvaru `_metadata.json`.** Klient
drží popis jako `{akce, skupiny, soubory: {nazev: {skupina}},
pripojit}` — stejný tvar, jaký čte `inherit.js`, `fieldRow`
a `renderGrid`. Ukládá ho průběžně (`PUT /api/import/<id>/popis`,
s prodlevou jako ukládání akce) do `import.json` pod klíčem `popis`.
Provedení bere popis z `import.json`, ne z požadavku.
*Proč:* dědění, návrhy jmen, kontrola jmen a úpravy skupin se
použijí beze změny a jeden zdroj popisu znamená, že návrat
k importu ukáže totéž, co se zapíše.
*Alternativa:* posílat popis až s provedením — návrat k importu by
ho ztratil.

**Výchozí rozdělení samostatným endpointem.** Plán přestane brát
volbu skupin (`POST …/plan` bez pole `skupiny`). Nový
`POST /api/import/<id>/skupiny` s volbou vrátí výchozí rozdělení
přenášených médií z posledního plánu (`group_plan`, včetně shod
s existujícími skupinami pro volbu připojení). Klient z něj sestaví
popis; změna volby s ručními úpravami chce potvrzení.
*Proč:* plán (sha256 na SMB, minuty) se nemusí počítat znovu při
každé změně rozdělení, a plán tak nezávisí na skupinách.

**Sladění popisu s plánem.** Po novém plánu klient z popisu vyhodí
soubory, které se nepřenesou, a nové přenášené soubory zařadí podle
výchozího rozdělení (endpoint výše). Skupina bez souborů v popisu
zůstane jen v klientu do provedení; server zapíše jen skupiny
s přenesenými soubory.

**Sdílený krok skupiny a autoři.** Nová funkce kroku vykreslí mřížku
(`renderGrid`) a panel: nahoře nástroje skupin pro výběr (jako dnes
`groupTools`/`mergeTools`), pod nimi blok „Celá akce“ s autory akce
a pro každou skupinu řádek s několika náhledy a polem autorů
(`fieldRow`, jako dnešní krok autorů). Průvodce akce ji volá nad
`state.doc` akce, import nad popisem importu. Rozdíly (zdroj náhledů,
cíl ukládání, tlačítko dalšího kroku, existující skupiny jen ke
čtení s volbou připojení) nese parametr kontextu.
*Proč:* jeden kód pro úpravy skupin a autory, žádné kopie.
*Alternativa:* samostatná mřížka importu — dvojí logika výběru
a skupin v už tak velkém `app.js`.

**Kontext mřížky místo nového stavu.** Mřížka čte `state.doc`,
`state.present`, `state.scan` a `thumbUrl(f)`. Krok importu nastaví
`state.mode = "import"`, `state.doc` na popis a `thumbUrl` přes
kontext na náhledy importu; při odchodu z kroku stav vrátí.
Ukládání akce (`save`) se v režimu `import` nespouští.

**Náhledy souborů importu.** `GET /api/import/<id>/nahled/<soubor>`
(volitelně velký) najde soubor v pracovním adresáři importu, nebo
u importu ze zdroje v `přetřídit/<zdroj>`, a vrátí náhled přes
`thumbs.thumbnail` se stávající cache v `.work/cache/`. Přístup
hlídá stejná kontrola majitele jako ostatní endpointy importu.

**Zápis při provedení.** Po přenosu nová funkce v `importer.py`
převede popis na zápis podle cíle:
- nová akce: `_metadata.json` = `akce` z popisu + skupiny s alespoň
  jedním přeneseným souborem + záznamy přenesených souborů
  s technickými údaji (jako dnes `plan_groups`); index se přegeneruje
  jako po každém importu;
- akce s `_metadata.json`: nové skupiny, `pripojit` na existující,
  přiřazení přenesených souborů; `akce.autori` jen při rozdílu proti
  uloženému stavu v době načtení plánu; stávající záznamy beze změny;
- akce bez `_metadata.json`: `merge_proposal` doplní skupiny
  s autory a `akce.autori`; `apply_proposal` je v průvodci předá do
  `state.doc`.
Zápis běží pod zámkem importu jako dnes.

**Pořadí průvodce akce.** Úklid → údaje akce → skupiny a autoři.
Načtení souborů (`loadDetail`) se přesune na potvrzení úklidu, aby
krok údaje akce mohl předvyplnit data z fotek. Krok údaje akce
autory dál neukazuje (jsou v kroku skupiny a autoři).

**Měkká povinnost autorů jako v průvodci.** Import s přenášenou
skupinou bez autorů (ani zděděných) upozorní a provede se až po
druhém kliknutí, stejně jako dnes dokončení průvodce akce.
*Proč:* jednotné chování; tvrdý zákaz by zablokoval import fotek
neznámého autora.

## Risks / Trade-offs

- [Sdílený globální `state` mezi importem a plochou] → režim `import`
  vypne ukládání akce a zámek; kontext se vrací při odchodu z kroku;
  testy JS pro sladění popisu s plánem.
- [Popis odkazuje na soubory, které při provedení selžou] → server
  zapisuje jen přenesené soubory a skupiny s nimi; výsledek uvede
  nepřenesené.
- [Akce mezi plánem a provedením změnila `_metadata.json` (jiná
  relace)] → zápis jen přidává nové skupiny a soubory; autoři akce se
  zapíšou jen při změně v kroku; selhání zápisu = soubory bez skupiny
  a hlášení ve výsledku jako dnes.
- [Velké importy (stovky souborů) a náhledy ze SMB] → náhledy líně
  (`loading="lazy"`) a cache; posuvník velikosti dlaždic platí i tady.

## Migration Plan

Rozpracované importy bez `popis` v `import.json`: krok skupiny
a autoři sestaví popis z uložené volby rozdělení. Starší návrhy skupin
bez autorů fungují jako dosud. Návrat = předchozí verze; nový klíč
`popis` stará verze ignoruje.
