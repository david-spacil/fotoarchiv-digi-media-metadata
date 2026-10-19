# Design

## Context

Stav produkce k 19. 10. 2026 (read-only průzkum `_metadata.json` všech
11 akcí, jen počty klíčů):

| Úroveň | Klíč | Výskyt |
|---|---|---|
| akce | `autori` | 0 akcí |
| skupina | `autori` | 15 skupin v 8 akcích |
| soubor | `autori` | 47 souborů ve 4 akcích |
| kterákoli | `osoby` | 0 |
| skupina | `datum_od`, `datum_do` | 0 |
| soubor | `sha256` | 0 |
| `souradnice_mist[]` | `osm` | 16 míst v 6 akcích |

Čtyři akce mají soubory úplně bez autora (ve skupině ani u souboru),
dvě z nich dokončené. Dokončení akce tedy autory nevynucuje
a odebrání autorů akce nic nerozbije.

Kdo `akce.autori` dnes zapisuje a čte:

- průvodce prvním otevřením, krok skupiny a autoři (`app.js`, pole
  „Celá akce“),
- průvodce importu (`importdesc.js` výchozí `akce_autori`, krok skupin
  importu, souhrn „Autoři celé akce“),
- server: detail importu (`akce_autori` z `cil_autori`), zápis popisu
  importu (`write_description`: nová akce, akce s `_metadata.json`,
  návrh skupin), převzetí návrhu při prvním otevření (`app.py`
  ~ř. 275),
- dědění (`model.resolve`, `inherit.js`), kontrola skupin bez autorů
  (`inherit.missing` přes `resolveGroup`).

`skupina.datum_od/datum_do` nabízí jen `FIELDS.skupina` ve formuláři.
Do souborů se zdědí jako `datum_od/datum_do`, ale export, chybějící
údaje i zobrazení podle data čtou jen `datum`. Pole tedy nemá účinek.

Verzi schématu kontroluje jen `akce_save` (400 při neshodě), načtení
ji nekontroluje. Záznam o exportu (`.work/export/…`) drží hash
`_metadata.json`. Podle něj plocha ukazuje „neexportované změny“.

## Goals / Non-Goals

**Goals:**

- Autoři jen u skupiny a souboru, v datech, UI i dědění.
- Schéma `/2` bez klíčů, které nic nečte, a jednorázový převod archivu.
- Převod nesmí dokončené akce zbytečně označit jako neexportované.

**Non-Goals:**

- Rozepsání existujících `akce.autori` do skupin (uživatel zvolil
  zahodit, v produkci žádné nejsou).
- `datum` u skupiny jako záložní datum pro soubory bez EXIF (případná
  samostatná změna).
- Využití `osm` (issue #46) a `sha256` u souboru (zůstává beze změny).
- Převod přechodných dat importu v `.work/import/` (viz Decisions).

## Decisions

### Vypuštěné klíče na jednom místě, převod při načtení

`model` dostane výčet klíčů vypuštěných ve `/2` po úrovních:
`akce: {autori, osoby}`, `skupina: {datum_od, datum_do, osoby}`,
`soubor: {osoby}`. Používá ho:

- `resolve` (a `inherit.js`): vypuštěné klíče přeskočí, nedědí se,
- `clean` před uložením: odstraní je (navazuje na dnešní mazání `osoby`),
- `upgrade(doc)`: dokument `/1` převede na `/2` (odebere klíče, nastaví
  `schema`) a vrátí, co odebral,
- `Workspace.load`: dokument `/1` vrátí převedený přes `upgrade`. Verze
  (hash) zůstává hashem souboru na disku, takže ochrana proti souběžné
  změně funguje beze změny.

Server tak `/1` nikdy neodmítne. Jakýkoli zápis (plocha, dokončení,
synchronizace Immiche, import) uloží `/2`. Klient dostane `/2` a jeho
uložení projde kontrolou schématu.

*Alternativa:* server `/1` odmítne (409 „spusťte migraci“), dokud
správce nespustí `migrovat`. Pak by akci do migrace nešlo otevřít a
každý zapisující kód (Immich, import) by potřeboval vlastní kontrolu.
Převod při načtení je jedno místo a žádný stav „nejde otevřít“.

*Alternativa:* zůstat na `/1` a klíče jen ignorovat. Uživatel chce
`/2`. Číslo verze dává externím čtenářům JSONu (skripty, Immich
konvence) jasný signál, že klíče zmizely.

### Příkaz `migrovat`

Podle `skryt`: bez `--zapis-do-archivu` jen výpis (akce a odebrané
klíče s počty), nic nezapisuje. S přepínačem projde všechny akce
archivu s `_metadata.json` ve verzi `/1` a uloží je převedené
(`Workspace(zapis=True)`, `save` s verzí, takže souběžná změna skončí
konfliktem a akce se vypíše jako selhaná). Spouští se při zastaveném
serveru, stejně jako `skryt`. Akce už ve `/2` se přeskočí, takže
opakované spuštění nic nezmění.

Vývojový režim: pracovní kopie v `.work/` převede server při dalším
uložení. Příkaz je bez přepínače nemění, protože bez
`--zapis-do-archivu` je jen výpis.

*Alternativa:* převod při startu serveru. Odmítnuto (pravidlo projektu):
start by sahal na data při každém spuštění.

### Záznam o exportu po převodu

Převod mění hash, takže by všechny dokončené akce ukázaly
„neexportované změny“. Sidecary se ale mění, jen když akce měla
`akce.autori` (soubory bez vlastních autorů a bez autorů skupiny je
dědily). Ostatní vypuštěné klíče se do sidecarů nedostanou. Pravidlo:

- záznam o exportu ukazoval na verzi před převodem **a** akce neměla
  `akce.autori` → `migrovat` ho přepíše na novou verzi (sidecary
  zůstávají aktuální),
- jinak se záznam nemění. Akce s `akce.autori` ukáže „neexportované
  změny“ a `migrovat` ji vypíše s počtem souborů, které autory zdědily
  a po převodu je nemají.

Převod při načtení na serveru záznam o exportu nemění (jeho první
uložení akci označí jako změněnou). To je očekávaný stav, proto
`docs/provoz/docker.md` říká spustit `migrovat` hned po nasazení.

### Přechodná data importu

Návrhy skupin (`.work/import/…/navrh`) a rozpracované popisy importu
mohou obsahovat `akce.autori` / `akce_autori`. Server je přestane číst
i zapisovat. Staré hodnoty se tiše ignorují a při dalším zápisu návrhu
zmizí. Žádná migrace.

### Upozornění na skupinu bez autorů

Beze změny pravidla. Skupina bez autorů (a ne všechny její soubory
autory přepisují) se hlásí v navigátoru, při dokončení průvodce i před
importem a import se provede po druhém potvrzení. Mění se jen to, že
skupina už nemůže autory dědit z akce.

## Risks / Trade-offs

- [Akce s `akce.autori` mimo produkci (testovací archivy, `.work`)
  ztratí autory u souborů, které je jen dědily] → `migrovat` je vypíše
  s počty. Navigátor je ukáže jako skupiny bez autorů a dají se
  doplnit.
- [Starší verze aplikace (rollback) narazí na `/2`] → `akce_save` staré
  verze odmítne uložit (400). Rollback znamená vrátit soubory ze zálohy
  nebo ručně přepsat `schema` na `/1`. Obsah `/2` je podmnožinou `/1`,
  takže stará verze ho jinak přečte.
- [Externí čtenáři `_metadata.json` kontrolují `/1`] → v repozitáři
  žádní nejsou, změna verze je uvedená v `README.md` (Datový model).

## Migration Plan

1. Nasadit (`git pull && docker compose up -d --build`).
2. `docker compose stop fotoarchiv`.
3. `docker compose run --rm fotoarchiv migrovat --archiv /archiv
   --work /work` → kontrola výpisu.
4. Totéž s `--zapis-do-archivu`.
5. `docker compose start fotoarchiv`. Plocha dokončených akcí nemá
   ukazovat „neexportované změny“.

Rollback: vrátit image a `_metadata.json` ze zálohy archivu.
