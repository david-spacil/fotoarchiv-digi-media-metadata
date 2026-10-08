## Context

Immich čte archiv jako externí knihovnu s výjimkou `**/*.ignored/**`
(README, Výstupy). Složku akce dnes zakládá import
(`importer.create_event`, `os.mkdir`) pod konečným názvem, takže ji
Immich načte dřív, než má metadata a sidecary. Asset pak vznikne bez
popisů a změna cesty později znamená nový asset bez obličejů
(AGENTS.md, Otevřené otázky).

Název složky akce je v kódu klíčem pro mnoho věcí:

| co | klíč |
| --- | --- |
| zámek (`lock.py`) | název akce v paměti |
| URL `/api/akce/<nazev>` | název akce |
| cache skenu (`scan.py`) | `event_dir.name` |
| cache sha256 (`importer.Imports.sha_cache`) | `Path(event_dir).name` |
| metadata a XMP ve vývojovém režimu, záznam o exportu | název akce |
| cache náhledů (`thumbs.py`) | sha1 z úplné cesty, velikosti, mtime |
| Immich (`immich.file_key`) | předposlední část cesty v Immichi |
| index (`index.link`) | název složky |

Přímý přístup `archiv / název` mimo `Workspace.event_dir` je jen
v `archive.py` (počty souborů, cesta k metadatům a XMP v produkci),
`index.py` (soubory, náhled, odkaz) a `importer.create_event`.

`dokonceno` se nastavuje jen v `akce_finish` (`app.py`) a ruší jen při
chybě exportu tamtéž; akce se jinak na nedokončenou nevrací.

## Goals / Non-Goals

**Goals:**

- Nedokončená akce je v produkci na disku `název.ignored`, Immich ji
  nevidí; dokončení příponu odebere.
- Logický název akce se nemění, takže zámek, cache, URL a pracovní
  adresář přejmenování neovlivní.
- Jednorázově skrýt všechny stávající nedokončené akce.

**Non-Goals:**

- Ruční skrytí/zveřejnění z aplikace (varianta 3 zamítnutá).
- Opětovné skrytí dokončené akce.
- Zachování obličejů u akcí, které Immich už načetl a které `skryt`
  skryje — riziko přijal uživatel.
- Přenos cache náhledů na novou cestu.

## Decisions

### Přípona jen na disku, název akce bez ní

`Workspace` dostane jediné místo, které překládá název akce na složku:
`event_dir(name)` zkusí `archiv/name` a `archiv/name.ignored`.
`event_names()` vrací názvy bez přípony. Všechny přímé přístupy
`archiv / název` (viz Context) půjdou přes `event_dir`. `EVENT_RE`
zůstane, jen `event_dir` odmítne název končící na `.ignored`.

Alternativa — přípona jako součást názvu akce (varianta 2): přejmenování
při dokončení by muselo převést zámek, cache skenu a sha256, metadata
a XMP ve vývojovém režimu, záznam o exportu a klienta přesměrovat na
novou URL. Víc míst k rozbití bez přínosu pro uživatele.

### Kolize = chyba, nic se nepřesouvá

Existují-li obě složky, `event_dir` vyhodí `Collision` (nová výjimka
v `archive.py`); API vrátí 409 `kolize_pripony`, seznam akcí ukáže akci
jednou se `stav` doplněným o `kolize: true`. V souladu s invariantem
„přesun nikdy nepřepíše existující soubor“ aplikace nerozhoduje, která
složka je správná.

### Pořadí při dokončení: uložit → export → přejmenovat

Sidecary se zapíšou do skryté složky, teprve pak `os.rename` na název
bez přípony. Immich tak složku poprvé uvidí rovnou se sidecary.
Selže-li přejmenování (`OSError`, typicky soubor otevřený přes SMB), vrátí
se `dokonceno` na `None` stejně jako při chybě exportu a odpověď nese
`chyba: "zverejneni"`. Před přejmenováním se ověří, že cíl neexistuje
(`os.rename` na Linuxu prázdnou cílovou složku přepíše).

Alternativa — přejmenovat před exportem: při chybě exportu by akce byla
v Immichi viditelná bez sidecarů, a vrácení přípony je další přesun,
který může selhat.

Dokončení drží zámek akce a import do akce také, takže se přejmenování
nesrazí s probíhajícím importem. Import si cestu ke složce zjistí až
po získání zámku.

### Import zakládá skrytou složku

`create_event` v produkci vytvoří `název.ignored`; `check_new_name`
odmítne název končící na `.ignored` a název, ke kterému existuje složka
s příponou i bez ní. Ve vývojovém režimu import do archivu nesmí
(403 `vyvojovy_rezim`), takže větev pro vývoj není potřeba.

### Příkaz `skryt` místo automatiky při startu

Jednorázové označení je samostatný příkaz jako `prevzit`. Bez
`--zapis-do-archivu` jen vypíše, co by přejmenoval (vzor
`exportovat`). Automatika při startu serveru by při každém startu
sahala na archiv a skryla i akci, kterou kolega právě nakopíroval mimo
aplikaci a chce ji mít v Immichi. Příkaz lze spustit znovu po ručním
nakopírování.

### Cache podle názvu akce

`scan.scan` a `Imports.sha_cache` dostanou název akce místo
`event_dir.name`, aby po odebrání přípony zůstaly platné. Cache náhledů
se nemění: po dokončení se náhledy jednou vygenerují znovu.

## Risks / Trade-offs

- [Akce už načtené Immichem po `skryt` zmizí i s obličeji] → uživatel
  přijal; příkaz nejdřív vypíše seznam, zápis až s přepínačem.
- [Synchronizace obličejů uvidí akci až po dokončení] → odpovídá
  záměru: obličeje se pojmenovávají v Immichi po zveřejnění.
- [Přejmenování selže na SMB, protože soubor drží jiný počítač] → akce
  zůstane nedokončená, plocha ukáže chybu, dokončení lze zopakovat.
- [Složka nakopírovaná mimo aplikaci je hned viditelná v Immichi] →
  spustit `skryt` znovu; zdokumentovat v README.
- [Náhledy po dokončení znovu generované] → jednorázové, přijatelné.
