## Context

`Workspace` (`archive.py`) skládá cestu k `_metadata.json` jedinou
metodou `metadata_path` a ukládá atomicky (temp soubor + `os.replace`)
s kontrolou verze (sha256 obsahu). `cleanup.plan` vrací seznam operací
`move` / `rename` / `delete` s příznakem `blocked`; klient ho jen
zobrazí. Server běží jako vlákenný Flask, bezstavový.

Cílové nasazení: jeden server (Debian) ve firemní síti, archiv připojený
přes SMB nebo NFS se zápisem. Přihlašování zatím není (změna
`add-login`).

## Goals / Non-Goals

**Goals:**
- Přepnutí kořene metadat na archiv bez změny formátu dokumentu.
- Zámek, který nevyžaduje sdílené hodiny ani soubor na SMB.
- Úklid, který nikdy nic nepřepíše a po chybě nechá archiv
  v konzistentním, ručně dořešitelném stavu.

**Non-Goals:**
- Přihlašování a oprávnění (`add-login`).
- Balení a nasazení serveru (systemd, reverzní proxy) — samostatná
  změna; tady jen požadavek „jeden proces“.
- Export XMP a dokončení akce.
- Vícenásobné instance serveru nad stejným archivem.

## Decisions

### Režim volí přepínač `--zapis-do-archivu`
Bez něj zůstává chování prototypu (metadata v `--work`, úklid nasucho).
`Workspace` dostane kořen metadat: archiv, nebo `work/metadata`.
Výchozí je bezpečný režim, aby vývojové spuštění nad ostrým archivem
nic nezměnilo. Kontrola „pracovní adresář nesmí ležet v archivu“
zůstává (cache do archivu nepatří).
*Alternativa:* konfigurační soubor — zbytečný pro jeden přepínač.

### Zámek v paměti serveru (S1)
Nový modul `lock.py`: slovník `akce → {jmeno, relace, ziskan,
heartbeat}` pod `threading.Lock`, čas z `time.monotonic()` serveru.
Opuštěnost se vyhodnocuje líně při každém dotazu (žádné vlákno
na úklid). Relace je náhodný token z `crypto.randomUUID()` v
`sessionStorage` (jedna záložka = jedna relace).

API:
- `POST /api/akce/<n>/zamek` `{relace, jmeno}` → 200 se zámkem, nebo
  409 `{drzitel, heartbeat_pred_s}`.
- `PUT /api/akce/<n>/zamek` `{relace}` (heartbeat) → 200, nebo 409,
  když zámek relace už nedrží.
- `DELETE /api/akce/<n>/zamek` `{relace}`; klient volá
  `navigator.sendBeacon` při `pagehide` (proto i `POST
  …/zamek/uvolnit` — beacon umí jen POST).
- `PUT …/metadata` a `POST …/uklid/provest` vyžadují `relace`
  a vrací 423, když ji zámek nemá.

Ve vývojovém režimu zámek funguje stejně — testuje se tím stejný kód.
*Alternativa:* souborový `_metadata.lock` z README — potřebný jen pro
víc procesů nad archivem, což S1 vylučuje; přinášel by rozdílné hodiny
a zbytky po pádu.
*Důsledek:* restart serveru zámky zahodí. Neuložená data tím neztratí
nikdo — klient při dalším heartbeatu zámek znovu získá (je volný),
a kontrola verze stejně chrání před přepsáním.

### Jméno uživatele z prohlížeče
Dialog s našeptáváním z `/api/jmena`, uložení do `localStorage`.
Server jméno nebere jako ověřené, jen ho zobrazuje. `add-login` ho
nahradí identitou z přihlášení beze změny API zámku (jméno se pak
doplní serverem).

### Provedení úklidu na serveru z voleb, ne z plánu klienta
`POST /api/akce/<n>/uklid/provest` přijme stejné `volby`
a `raw_v_koreni` jako náhled, plán sestaví znovu a provede.
Klient tak nemůže poslat libovolné cesty a kolize vzniklé mezi náhledem
a potvrzením se odhalí. Provedení (`cleanup.execute`):
- Operace v pořadí plánu. Před každým přesunem/přejmenováním znovu
  ověřit, že cíl neexistuje (porovnání jako v plánu: NFC + casefold
  vůči výpisu cílové složky), pak `os.rename`. Na Linuxu `rename`
  přepisuje, proto kontrola těsně před ním; souběh vylučuje zámek akce.
- `RAW.ignored` se vytvoří `mkdir` (bez `exist_ok`), když ho plán
  potřebuje a neexistuje.
- `delete` jen pro složku, ve které zbyl nejvýš `Thumbs.db`
  (ten se smaže, pak `rmdir`); jinak operace selže.
- Selhaný přesun zablokuje `delete` své podsložky; ostatní běží dál.
- Výsledek: seznam operací se stavem `hotovo` / `blokovano` /
  `chyba` + text chyby; zapíše se i do logu serveru.

### Převzetí z `.work` jako příkaz CLI
`python -m fotoarchiv prevzit --archiv … --work …` zkopíruje
`work/metadata/<akce>/_metadata.json` do složky akce, jen když tam
soubor není (`open(…, "xb")`), a vypíše převzaté / přeskočené.
Spouští se jednou před přepnutím serveru do produkčního režimu.
*Alternativa:* automaticky při startu — skryté a nevratné zápisy do
archivu při každém spuštění.

## Risks / Trade-offs

- [`os.replace` přes SMB/NFS nemusí být atomický nebo může selhat při
  přepisu cíle] → úloha v tasks ověří uložení a přejmenování na
  skutečném připojení serveru; při selhání záloha `.bak` + rename.
- [Práva a vlastník nových souborů na SMB/NFS] → ověřit na serveru
  s účtem služby; zdokumentovat volby připojení.
- [Restart serveru uprostřed úklidu] → archiv zůstane v mezistavu, ale
  nic se nepřepíše; nový náhled plánu ukáže zbytek, provede se znovu.
- [Jméno v prohlížeči jde podvrhnout] → přijatelné do `add-login`;
  server je jen ve firemní síti.
- [Server spuštěný omylem ve víc procesech (gunicorn workers)] → zámek
  by neplatil; v README a v nasazení výslovně 1 proces, vlákna ano.

## Migration Plan

1. Nasadit novou verzi ve vývojovém režimu, ověřit zámek ve dvou
   prohlížečích.
2. `prevzit` z `.work` do archivu.
3. Spustit s `--zapis-do-archivu`.
4. Návrat: spustit bez přepínače; metadata v archivu zůstanou a vývojový
   režim je ignoruje.

## Open Questions

- SMB, nebo NFS pro server — výsledek ovlivní jen volby připojení
  a ověřovací úlohu, ne kód.
