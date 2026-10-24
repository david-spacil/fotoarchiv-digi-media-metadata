## 1. Ověření na Linuxu (agent na Linuxu, před implementací)

- [x] 1.1 Zapsat distribuci a desktopové prostředí; připojit telefon
  (přenos souborů, odemčený) a zjistit, kde se objeví (`gio mount -l`,
  `/run/user/$UID/gvfs/`), případně kio-mtp u KDE
- [x] 1.2 Ověřit, že je vidět `DCIM/Camera`, a změřit výpis
  (počet položek, čas); porovnat s Windows (871 položek za 1,3 s)
- [x] 1.3 Zkopírovat jednu fotku `PXL_*.jpg` (se svolením uživatele,
  reálná data) do scratch adresáře; ověřit SHA-256 proti kopii
  z Windows a GPS `exiftool -n -GPSLatitude -GPSLongitude`
- [x] 1.4 Ověřit čtení jen začátku souboru přes gvfs (EXIF náhled
  bez stažení celé fotky) a jeho rychlost
- [x] 1.5 Podle výsledků potvrdit adaptér gvfs, nebo přejít na libmtp;
  doplnit design.md (Context, Open Questions) a issue #69

## 2. Kostra klienta

- [ ] 2.1 Adresář `klient/` s balíčkem, `requirements.txt` s pevnými
  verzemi (PySide6, `winrt-*` s markerem `sys_platform == "win32"`,
  PyInstaller), spuštění `python -m klient`
- [ ] 2.2 Rozhraní zdroje médií a podvržený zdroj pro testy
- [ ] 2.3 Konfigurace klienta (adresa serveru, login) v adresáři
  konfigurace uživatele

## 3. Adaptéry zdroje

- [ ] 3.1 Windows: `Windows.Media.Import`, výběr zařízení (přeskočit
  zdroje bez položek a s chybou), filtr camera roll, náhled,
  kopie do dočasné složky bez podsložky s datem
- [ ] 3.2 Linux: gvfs, výpis složky (výchozí `DCIM/Camera`), strom
  složek úložiště, náhled z EXIF hlavičky, kopie; čekání na připojení
  telefonu (sledování svazků)
- [ ] 3.4 Windows: výběr jiné složky (cesta položky z
  `IMAGES_AND_VIDEOS`, nebo Shell MTP); ověřit na telefonu
- [ ] 3.3 Hlášky: žádné zařízení, zamčený telefon, odpojení za běhu

## 4. Evidence, výběr a upload

- [ ] 4.1 Evidence nahraných po zařízení (složka + název + velikost
  + datum) a poslední otevřená složka, testy
- [ ] 4.2 Přihlášení, založení importu, nahrání po jednom se `mtime`,
  odmítnutí HTTP mimo localhost; testy proti testovacímu serveru
  aplikace (Flask test client nebo živý cheroot na localhostu)
- [ ] 4.3 Ověřit, že import na serveru přijme soubory z klienta beze
  změny serveru (přehled, plán, poloha neodebraná)
- [ ] 4.4 Po nahrání otevřít prohlížeč na `<server>/#/import/<id>`;
  smazat dočasné kopie

## 5. UI

- [ ] 5.1 Mřížka náhledů od nejnovějších, líné načítání náhledů;
  zástupný náhled a dopočet z celého souboru u položek bez EXIF
  náhledu (jen viditelné)
- [ ] 5.4 Volba složky telefonu (strom), průběh pomalého výpisu
- [ ] 5.2 Výběr jednotlivě, rozsahem, „vybrat nové“; počet a velikost
- [ ] 5.3 Průběh nahrávání a souhrn nenahraných

## 6. Spuštění po připojení a sestavení

- [ ] 6.1 `--registrovat` / `--odregistrovat`: AutoPlay v HKCU
  (Windows), `.desktop` pro menu aplikací (Linux, bez nabídky
  po připojení – MTP svazek nehlásí `x-content`); ověřit ručně
- [ ] 6.2 PyInstaller onefile pro Windows a Linux, workflow
  v `.github/workflows/`
- [ ] 6.3 Dokumentace: `docs/navod/` (použití klienta),
  `docs/provoz/` (sestavení, registrace), rozcestník `docs/README.md`
