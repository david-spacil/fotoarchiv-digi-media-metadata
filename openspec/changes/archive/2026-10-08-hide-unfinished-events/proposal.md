## Why

Immich čte archiv jako externí knihovnu a načte každou složku akce hned,
jak vznikne — tedy dřív, než má akce metadata a sidecary. Asset pak
v Immichi vznikne bez popisů a míst a pozdější změna cesty by z něj
udělala nový asset bez obličejů. Nedokončené akce proto musí být před
Immichem skryté a zveřejnit se až dokončením (issue #13).

## What Changes

- Složka nedokončené akce nese na disku příponu `.ignored`
  (`2026-04-28 kontrola Naučné stezky.ignored`), kterou Immich vylučuje už
  dnešním vzorem `**/*.ignored/**`. Akce se v aplikaci jmenuje bez
  přípony; přípona je jen vlastnost složky na disku.
- Aplikace najde složku akce s příponou i bez ní; existují-li obě, akci
  odmítne otevřít a ohlásí kolizi, nic nepřesouvá.
- Import zakládá novou akci rovnou se složkou s příponou; nová akce
  nesmí kolidovat se složkou s příponou ani bez ní.
- Dokončení akce po úspěšném exportu odebere příponu. Selže-li
  přejmenování, akce MUST NOT být dokončená (jako při chybě exportu).
  Dokončená akce příponu znovu nedostane, ani po dalších úpravách.
- Nový příkaz `python -m fotoarchiv skryt` jednorázově označí všechny
  stávající nedokončené akce (*nezpracováno* i *rozpracováno*); bez
  `--zapis-do-archivu` jen vypíše, co by přejmenoval.
- Index odkazuje na skutečnou složku na disku (s příponou), název akce
  ukazuje bez ní.
- Vývojový režim archiv nepřejmenovává (import a dokončení se chovají
  jako dosud, příkaz `skryt` jen vypisuje).
- **BREAKING (provoz):** akce, které už Immich načetl a zatím nejsou
  dokončené, po spuštění `skryt` z Immiche zmizí i s obličeji; po
  dokončení se načtou znovu jako nové assety. Uživatel riziko přijal.

## Capabilities

### New Capabilities

- `event-visibility`: skrytí nedokončených akcí před Immichem příponou
  `.ignored` na složce akce — název akce vs. složka na disku, kolize,
  odebrání přípony při dokončení a jednorázové označení stávajících
  akcí.

### Modified Capabilities

- `archive-browsing`: seznam akcí ukazuje složky s příponou `.ignored`
  pod názvem bez přípony.
- `photo-import`: nová akce se zakládá se složkou s příponou; kontrola
  existujícího názvu bere v úvahu obě podoby; upozornění u dokončené
  akce zmíní, že nové soubory uvidí Immich hned.
- `metadata-workspace`: dokončení akce odebere příponu a při selhání
  přejmenování akci nedokončí.
- `archive-index`: odkaz z karty vede na skutečnou složku na disku.

## Impact

- Kód: `archive.py` (`EVENT_RE`, `event_names`, `event_dir`, nová
  funkce pro zveřejnění), `importer.py` (`check_new_name`,
  `create_event`, sha cache podle názvu akce), `scan.py` (cache podle
  názvu akce), `app.py` (`akce_finish`, chybová odpověď kolize),
  `index.py` (odkaz), `__main__.py` (příkaz `skryt`),
  `static/app.js` (hláška selhání přejmenování a kolize, text
  upozornění v průvodci importu).
- Cache náhledů je klíčovaná cestou; po dokončení akce se náhledy jednou
  vygenerují znovu.
- Immich: beze změny nastavení; synchronizace obličejů uvidí akci až
  po dokončení.
- Dokumentace: README (Archiv, Výstupy/Immich, Tok práce, příkazy),
  AGENTS.md (příkazy, invariant o `.ignored`).
