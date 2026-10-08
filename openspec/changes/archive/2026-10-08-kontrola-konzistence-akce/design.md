## Context

Kde dnes aplikace s obsahem kořene akce pracuje:

| Místo | Co dělá | Nepodporované soubory |
|---|---|---|
| `scan.root_files` | dělí kořen na média a „nezpracované“ | jen seznam názvů |
| detail akce (`app.py`) | vrací `nezpracovane`, `chybejici` | sbalený `<details>` pod mřížkou |
| `archive.list_events` | prochází kořen kvůli počtu, načte `_metadata.json` | nic |
| `cleanup.plan` | podsložky, RAWy v kořeni, vyřazené soubory | nic |
| úklid z plochy (`jen_vyradit`) | jen vyřazené; podsložky a RAWy vypne | nic |
| dokončení (`missingItems` v `app.js`) | chybějící údaje, potvrzení | nic |

`is_metadata` bere jako metadata každé `.xmp`, `_metadata.json`
a dočasné soubory (`.metadata-`, `.xmp-`, `.import-`); osiřelé sidecary
dnes nikde nevidět. Sidecar se jmenuje `<soubor>.xmp` (např.
`P1503712.JPG.xmp`). Záznamy bez souboru drží `model.merge_scan` a lišta
je hlásí („N souborů chybí v kořeni“).

Issue #10 (samostatná větev, zatím nesloučená) přidává modul
`integrity.py` a příkaz `zkontrolovat` pro poškozené soubory. Dohodnuto
jeden příkaz pro obě kontroly; CLI této změny navazuje po sloučení #10.

## Goals / Non-Goals

**Goals:**
- Jedna čistá funkce kontroly kořene akce, kterou volá seznam akcí,
  detail akce a později CLI.
- Každý nález s nápravou se dá vyřešit úklidem z plochy bez průvodce.

**Non-Goals:**
- Poškozené soubory (issue #10) a jejich nálezy na ploše.
- Podpora dalších formátů (TIFF, HEIF) jako médií.
- Nálezy v `_INDEX` a uvnitř podsložek `.ignored`.
- Zbylé dočasné soubory (`.metadata-*` aj.) — vznikají i za běhu
  operací, hlášení by bylo falešné.
- Mazání záznamů bez souboru.

## Decisions

### Nový modul `fotoarchiv/consistency.py`

`check(event_dir, doc) -> list[{"druh", "nazev"}]`, seřazené podle druhu
a názvu. Čte jen `os.scandir` kořene a předaný `doc`. Druhy:

| `druh` | Co | Náprava |
|---|---|---|
| `nepodporovany` | soubor, který není médium, RAW, `Thumbs.db` ani metadata | přesun do `ostatni.ignored/` |
| `sirotek_xmp` | `X.xmp`, k němuž `X` v kořeni není | přesun do `ostatni.ignored/` |
| `raw` | RAW v kořeni | přesun do `RAW.ignored/` (stávající) |
| `podslozka` | podsložka bez `.ignored` | volba přesunout/ponechat (stávající) |
| `chybejici` | záznam v `soubory` bez souboru v kořeni | žádná, jen hlášení |

Porovnání názvů přes `_key` (NFC + casefold) jako v úklidu — na SMB
`a.JPG.xmp` patří k `a.jpg`.

*Alternativa:* rozšířit `scan.root_files` nebo `cleanup.subfolders` —
odmítnuto: sken běží se exiftoolem a cache, úklid staví operace; kontrola
má být levná a bez vedlejších účinků, aby ji mohl volat seznam akcí.

### Osiřelý sidecar se přesouvá, nemaže

Sidecar je generovaný výstup a smazat by šel, ale pravidlo „nic se
nemaže“ platí pro úklid celé; osiřelý sidecar navíc může být jediný
záznam údajů souboru, který někdo ručně přesunul pryč. Jde do
`ostatni.ignored/` jako ostatní.

### Jedna složka `ostatni.ignored` pro všechno ostatní

Jméno vybral uživatel. `k_odstraneni.ignored` znamená „ke smazání“,
což se na PDF se zprávou z akce nehodí. Bez rozlišení podle typu —
volba po typech by přidala UI a stav za málo užitku.

### TIFF a další obrázky jsou nepodporované

Uživatel čeká v archivu spíš neobrazové soubory, TIFF se ale vyskytnout
může. Do `ostatni.ignored/` se přesune stejně (nic se neztratí);
podpora TIFF jako média je samostatná změna.

### Nálezy počítá server, klient je jen ukazuje

Detail akce vrací `kontrola` (seznam nálezů), seznam akcí u každé akce
`kontrola` jako počty podle druhu. Klient nálezy nepočítá — kontrola
potřebuje výpis disku, který klient nemá; po úklidu se detail načte
znovu jako dnes. Pole `nezpracovane` v detailu nahradí `kontrola`.

### Nálezy v liště, ne v novém panelu

Lišta chybějících údajů už je místo „co je s akcí špatně“ a hlásí
záznamy bez souboru. Přibudou položky po druzích („2 nepodporované
soubory v kořeni“); klik otevře dialog s názvy. Sbalený `<details>` pod
mřížkou zmizí. *Alternativa:* samostatný panel „Kontrola akce“ —
odmítnuto, dvě místa se stejnou rolí.

### Úklid z plochy pokrývá všechny nápravy

Dnes `jen_vyradit` vypíná podsložky i RAWy. Nově úklid z plochy
(příznak `z_plochy`, `jen_vyradit` zůstává jako alias) zahrne vyřazené,
`ostatni.ignored`, RAWy z kořene a podsložky. Podsložky v dialogu
dostanou stejnou volbu přesunout/ponechat jako v průvodci, bez výchozí
volby; nezvolená podsložka se nepřesune. Tlačítko „Uklidit…“ se ukáže,
je-li co vyřadit nebo je-li nález s nápravou.

### Průvodce: přesun ostatních souborů jako RAWy

Krok úklidu v průvodci dostane zaškrtávátko „Přesunout ostatní soubory
do `ostatni.ignored`“, výchozí zapnuté (jako RAWy v kořeni). Plán
přijímá parametr `ostatni` (výchozí `True`).

### Dokončení jen varuje

Nálezy kontroly se přidají do seznamu v potvrzení dokončení (sdílí ho
`missingItems`), dokončení po potvrzení proběhne. Štítek „k vyřešení“
v seznamu akcí zůstane i u dokončené akce, dokud nálezy trvají.

### Vývojový režim

Kontrola čte archiv (jen čtení), takže funguje i ve vývojovém režimu;
úklid jen ukáže plán, jako dnes. Osiřelé sidecary se hledají jen
v kořeni archivu, ne v `.work/xmp/`.

## Risks / Trade-offs

- [Soubory, které uživatel v kořeni chce (např. `zprava.pdf`)] → jdou
  do `ostatni.ignored/`, ne pryč; Immich je tam nevidí, v archivu
  zůstanou u akce.
- [`desktop.ini`, `.DS_Store` a podobné systémové soubory se budou
  hlásit] → přesun je neškodný; pokud budou otravovat, přidají se
  k `Thumbs.db` mezi přeskakované.
- [Sidecar přesunutý jako osiřelý, jehož médium se pak vrátí] → další
  export sidecar v kořeni zapíše znovu z `_metadata.json`.
- [Seznam akcí přes SMB] → kontrola nepřidává čtení souborů, jen
  položky výpisu, který `list_events` už dělá; podsložky se neotevírají.

## Migration Plan

Bez migrace. Po nasazení ukáže seznam akcí štítky u stávajících akcí;
úklid je ruční, akce po akci (hromadně až CLI po sloučení #10).
