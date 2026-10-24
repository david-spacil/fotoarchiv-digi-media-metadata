[← Dokumentace](../README.md)

# Import z telefonu

Fotky nahrané z telefonu přes prohlížeč mají odebranou polohu. Klient
na PC je čte z telefonu připojeného kabelem a pošle originály beze
změny (GPS zůstane) do [importu](import.md). Zatím jen Linux s gvfs
(GNOME); Windows se připravuje.

1. Telefon připojte kabelem, odemkněte a v oznámení „Nabíjení přes
   USB“ zvolte **Přenos souborů**. Vývojářský režim ani aplikace
   v telefonu nejsou potřeba.
2. Spusťte klient (menu aplikací, nebo `fotoarchiv-klient`). Bez
   telefonu na něj čeká; zamčený telefon hlásí výzvou k odemčení.
3. Klient otevře složku fotoaparátu (`DCIM/Camera`), od nejnovějších.
   **Jiná složka…** otevře jinou složku telefonu; klient si ji
   u telefonu zapamatuje. První výpis složky trvá (u 700 fotek kolem
   20 s), další jsou okamžité.
4. Označte média: klik, Ctrl+klik, Shift+klik pro rozsah, nebo
   **Vybrat nové** (co klient z tohoto telefonu ještě nenahrál).
   Nahraná mají štítek „✓ nahráno“.
5. **Nahrát do Fotoarchivu…** se poprvé zeptá na server, login
   a heslo (heslo jen do zavření klientu). Po nahrání otevře prohlížeč
   na průvodci importem; dál se pokračuje jako u běžného importu.

Náhledy se berou z hlavičky fotky. Fotka bez náhledu (např. HDR+)
a video ukážou zástupný obrázek, skutečný náhled se dopočítá
z celého souboru (video jen s nainstalovaným `ffmpeg`).

Nahrávají se jen typy, které import přijme (jpg, jpeg, png, mp4, mov
a RAWy). Dva soubory stejného jména z různých složek nejdou nahrát
naráz. Když se telefon během nahrávání odpojí, klient vypíše
nenahrané; v evidenci jsou jen úspěšně nahrané.

Evidence nahraných a nastavení jsou jen v počítači:
`~/.config/fotoarchiv-klient/` (`klient.json`, `nahrane.json`).
