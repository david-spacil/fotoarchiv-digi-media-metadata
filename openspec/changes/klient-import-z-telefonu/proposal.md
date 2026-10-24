# Proposal

## Why

Fotky z telefonu nahrané přes prohlížeč mají odebranou polohu (GPS
nulová, import je odmítá, viz `photo-import`). Dnes je jediná cesta
ruční kopie z telefonu do souborového systému a pak import — dva
kroky. Issue #69 chce jeden krok jako import v aplikaci Fotky ve
Windows: připojit telefon, vybrat fotky od nejnovějších, odeslat.

## What Changes

- Nový desktopový klient (Python, jeden spustitelný soubor bez
  instalace) pro Windows a Linux v novém adresáři `klient/`.
- Klient vypíše média z fotoaparátu připojeného telefonu (USB, MTP)
  s náhledy od nejnovějších; uživatel může otevřít i jinou složku
  telefonu, uživatel označí výběr a klient pošle
  originální bajty do stávajícího importu na serveru. Pak otevře
  prohlížeč na průvodci importem v kroku přehled.
- Klient si pamatuje, co z telefonu už nahrál, a nabízí výběr nových.
- Ve Windows ho jde spustit z nabídky AutoPlay po připojení telefonu;
  v Linuxu se spouští ručně a na připojení telefonu počká.
- Server se nemění: klient používá stávající přihlášení a API importu.

## Capabilities

### New Capabilities
- `phone-import-client`: desktopový klient, který z telefonu
  připojeného kabelem nahraje vybraná média s originálními metadaty
  do importu aplikace.

### Modified Capabilities

Žádné. Import na serveru přijme soubory od klienta stejně jako od
prohlížeče (ověřit v úkolech).

## Impact

- Nový adresář `klient/` s vlastními závislostmi
  (`klient/requirements.txt`: PySide6, `winrt-*` jen na Windows,
  PyInstaller na sestavení); server a jeho `requirements.txt` beze
  změny.
- Sestavení binárek pro Windows a Linux (CI v `.github/workflows/`).
- Dokumentace: `docs/navod/` (návod ke klientovi), `docs/provoz/`
  (sestavení a registrace v systému).
- Přihlášení klienta jde přes stávající `/api/prihlaseni`; heslo klient
  neukládá.
