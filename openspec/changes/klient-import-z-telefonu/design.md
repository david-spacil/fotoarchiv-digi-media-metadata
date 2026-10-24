# Design

## Context

Viz proposal.md – Why. Server už má vše potřebné: přihlášení cookie
relací (`POST /api/prihlaseni`), založení importu (`POST /api/import`)
a nahrání souboru syrovým tělem (`POST /api/import/<id>/soubor
?cesta=…&mtime=…`). Import patří loginu (`owner()` z relace), takže
ho prohlížeč téhož uživatele otevře na `#/import/<id>`.

Ověřeno 2026-10-24 na Windows 11 (Pixel 8a, USB, přenos souborů),
skripty ve scratchpadu relace, ne v repu:

- `Windows.Media.Import` jde volat z nebaleného Pythonu 3.13 přes
  pywinrt (`winrt-Windows.Media.Import` 10.0.28000), bez MSIX.
- `find_items_async(IMAGES_AND_VIDEOS_FROM_CAMERA_ROLL, SELECT_ALL)`:
  871 položek za 1,3 s; `IMAGES_AND_VIDEOS`: 5582 za 18,7 s.
- `SELECT_NEW` vrací `E_INVALIDARG` (0x80070057) u každého filtru.
- Čtečka SD karet bez karty je také zdroj; výběr zdroje podle modelu.
- Náhled položky: JPEG ~15 kB. Datum položky z camera roll odpovídá
  času pořízení (UTC).
- `import_items_async` jedné fotky do zadané složky: kopie bajtově
  shodná s originálem (SHA-256), GPS zachovaná. API samo zakládá
  podsložku s datem (`2026-10-24 001`).
- Kopie stejné fotky přes aplikaci Fotky také GPS zachovala.

Linux zatím neověřen (viz Open Questions).

## Goals / Non-Goals

**Goals:** jeden kód UI, výběru, evidence a uploadu pro obě platformy;
platformní je jen zdroj médií.

**Non-Goals:** zápis do telefonu (mazání po importu), iPhone (neověřeno,
nevylučuje se), změny serveru, mobilní UI (`mobilni-verze`).

## Decisions

### Python + PySide6, PyInstaller
Stejný jazyk jako server, testy v pytestu. Alternativy: C# + Avalonia
(lepší dokumentace WinRT, ale druhý ekosystém), Tauri (malá binárka,
ale Rust a pracnější WinRT). Python ověřen na Windows sondou.

### Zdroj médií jako rozhraní se dvěma adaptéry
`Zdroj`: seznam zařízení, výpis položek (klíč, název, datum, velikost,
typ), náhled, kopie položky do dočasné složky.
- **Windows:** `Windows.Media.Import` s filtrem camera roll;
  `subfolder_creation_mode` vypnout, cílová složka dočasná.
- **Linux:** telefon připojený přes gvfs jako složka
  (`/run/user/<uid>/gvfs/mtp:host=…`), procházení `DCIM/Camera`,
  náhled z EXIF hlavičky (čte se jen začátek souboru), kopie běžným
  čtením. Alternativa: libmtp přímo — jen když gvfs nebude stačit.
Testy UI, evidence a uploadu běží proti podvrženému zdroji.

### Evidence nahraných na straně klienta
`SELECT_NEW` mimo zabalené aplikace nefunguje, a i kdyby, eviduje
importy přes Fotky, ne do archivu. Klient si vede soubor v konfiguraci
uživatele (`%APPDATA%\fotoarchiv-klient\`, `~/.config/fotoarchiv-klient/`)
po zařízení: klíč položky = název + velikost + datum. Duplicity vůči
archivu dál řeší plán importu na serveru.

### Upload přes stávající API
Klient se přihlásí, založí import s `celkem` = součet velikostí
a nahrává po jednom (jako prohlížeč 2–3 souběžně), `mtime` z data
položky. Adresa serveru v konfiguraci klienta, login předvyplněný,
heslo jen pro relaci. Po dokončení otevře `<server>/#/import/<id>`.

### Spuštění po připojení
- **Windows:** registrace AutoPlay handleru v HKCU (událost pro WPD
  zařízení s obrázky); klient přijme ID zařízení z argumentů. Klíče
  ověřit při implementaci.
- **Linux:** `.desktop` soubor s `MimeType=x-content/image-dcf;`
  v `~/.local/share/applications/`.
Registraci dělá klient sám přepínačem (`--registrovat` /
`--odregistrovat`), ne instalátor.

## Risks / Trade-offs

- [pywinrt API se mezi verzemi mění] → pevné verze v
  `klient/requirements.txt`.
- [PyInstaller onefile ~60–80 MB, falešné poplachy antiviru] →
  přijatelné; případně onedir v zipu.
- [gvfs nemusí být na všech prostředích (KDE používá kio-mtp)] →
  ověřit na cílovém Linuxu; fallback libmtp.
- [MTP čtení celých souborů kvůli náhledům je pomalé] → náhled jen
  z EXIF hlavičky, líně při posunu mřížky.
- [Session cookie přes HTTP] → klient MUST odmítnout jiné než HTTPS
  kromě `127.0.0.1`/`localhost`.

## Migration Plan

Nic se nemigruje; server beze změny. Binárky z CI jako příloha
releasu nebo artefakt workflow.

## Open Questions

- Linux (doplní agent na Linuxu): distribuce a prostředí, kde se
  telefon připojí, jestli gvfs vystaví `DCIM/Camera`, rychlost výpisu,
  shoda SHA-256 a GPS kopie. Dle výsledku potvrdit gvfs, nebo libmtp.
- Přesné klíče registru pro AutoPlay u MTP zařízení.
