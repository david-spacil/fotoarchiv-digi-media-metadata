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

Ověřeno 2026-10-24 na Fedoře 44 s GNOME (gvfs-mtp 1.60.3, týž
telefon):

- gvfs telefon připojí sám jako `/run/user/<uid>/gvfs/mtp:host=…/
  Interní sdílené úložiště/`; libmtp není potřeba.
- `DCIM/Camera`: 692 položek, první výpis 18,3 s, další 0,05 s (cache
  gvfs). V `DCIM` jsou i jiné složky (další přístroje
  a aplikace).
- Kopie přes `cp` (FUSE) i `gio copy`: shodný SHA-256 a velikost podle
  zařízení, GPS zachovaná u fotek i videa.
- EXIF náhled leží v prvních 64 KiB (offset 1297, ~9 kB); 30 hlaviček
  za 2,5 s. Jedna z 30 fotek (HDR+) náhled v EXIF nemá vůbec, videa
  také ne.
- MTP svazek telefonu nemá `x_content_types` (`x-content/image-dcf`
  hlásí jen čtečka SD karet), takže `.desktop` s tímto typem se
  po připojení telefonu nenabídne. Udev: `ID_MTP_DEVICE=1`.

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
`Zdroj`: seznam zařízení, seznam složek, výpis položek jedné složky
(klíč, název, datum, velikost, typ), náhled, kopie položky do dočasné
složky.
- **Windows:** `Windows.Media.Import`; výchozí složka = filtr camera
  roll, jiné složky z filtru `IMAGES_AND_VIDEOS` seskupené podle cesty
  položky (pomalejší, 18,7 s, proto až na vyžádání);
  `subfolder_creation_mode` vypnout, cílová složka dočasná.
- **Linux:** gvfs (ověřeno, libmtp se nepoužije); výchozí složka
  `DCIM/Camera`, procházení celého úložiště telefonu, kopie běžným
  čtením souboru.
Testy UI, evidence a uploadu běží proti podvrženému zdroji.

### Výběr složky
Výchozí je složka fotoaparátu (`DCIM/Camera`, ve Windows camera roll).
Uživatel může přejít do jiné složky telefonu (např. `DCIM/Export`,
`Pictures`, `Download`) přes strom složek; výpis ukazuje jen fotky
a videa přímo v ní. Poslední zvolenou složku si klient pamatuje
po zařízení (vedle evidence). Klíč položky v evidenci obsahuje
i složku, aby stejně pojmenované soubory z různých složek nesplynuly.

### Náhledy
Náhled se bere z EXIF hlavičky (prvních 64 KiB souboru). Když v ní
není (HDR+, některé aplikace, videa), klient zobrazí zástupnou ikonu
a skutečný náhled dopočítá líně z celého souboru (fotka zmenšením,
video snímkem přes ffmpeg, je-li k dispozici), jen pro položky
ve viditelné části mřížky.

### Evidence nahraných na straně klienta
`SELECT_NEW` mimo zabalené aplikace nefunguje, a i kdyby, eviduje
importy přes Fotky, ne do archivu. Klient si vede soubor v konfiguraci
uživatele (`%APPDATA%\fotoarchiv-klient\`, `~/.config/fotoarchiv-klient/`)
po zařízení: klíč položky = složka + název + velikost + datum. Duplicity vůči
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
- **Linux:** nabídka systému po připojení MTP telefonu nejde
  (svazek nehlásí `x-content/*`). Klient se spouští ručně (`.desktop`
  v `~/.local/share/applications/` pro menu aplikací) a když telefon
  připojený není, čeká na něj sledováním svazků gvfs. Pravidlo udev
  by vyžadovalo root a instalaci, proto ne.
Registraci dělá klient sám přepínačem (`--registrovat` /
`--odregistrovat`), ne instalátor.

## Risks / Trade-offs

- [pywinrt API se mezi verzemi mění] → pevné verze v
  `klient/requirements.txt`.
- [PyInstaller onefile ~60–80 MB, falešné poplachy antiviru] →
  přijatelné; případně onedir v zipu.
- [gvfs nemusí být na všech prostředích (KDE používá kio-mtp,
  neověřeno)] → klient hlásí, že telefon nenašel; podpora KDE až
  na požádání.
- [MTP čtení celých souborů kvůli náhledům je pomalé] → náhled
  z EXIF hlavičky, celý soubor jen u položek bez něj a jen viditelných.
- [První výpis složky přes gvfs trvá ~18 s na 700 položek] → průběh
  ve výpisu, položky přibývají postupně.
- [Session cookie přes HTTP] → klient MUST odmítnout jiné než HTTPS
  kromě `127.0.0.1`/`localhost`.

## Migration Plan

Nic se nemigruje; server beze změny. Binárky z CI jako příloha
releasu nebo artefakt workflow.

## Open Questions

- Přesné klíče registru pro AutoPlay u MTP zařízení.
- Windows: jestli `PhotoImportItem` vystaví cestu položky pro výběr
  složky; jinak procházet složky přes Shell (MTP).
- KDE (kio-mtp) neověřeno.
