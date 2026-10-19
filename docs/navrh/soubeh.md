[← Dokumentace](../README.md)

# Souběh

Aplikace běží jako jeden sdílený server (cheroot); zámek otevřené akce drží
server v paměti (kdo, relace prohlížeče, od kdy, poslední heartbeat).
Proto **server smí běžet jen jako jeden proces** (vlákna ano — výchozí 32,
víc workerů ne). Do archivu se žádný soubor zámku nezapisuje.

- Při otevření akce klient požádá o zámek. Drží-li akci někdo jiný,
  otevře ji jen ke čtení s upozorněním „Akci upravuje …“.
- Klient zámek obnovuje heartbeatem (~1 min), dokud je akce otevřená;
  při odchodu z akce nebo zavření stránky ho uvolní.
- Zámek bez heartbeatu ~5 min (podle hodin serveru) je opuštěný a jde
  převzít. Kdo o zámek přijde, přepne se jen ke čtení.
- Uložení, provedení úklidu a import do stávající akce bez zámku
  server odmítne; kontrola verze `_metadata.json` platí i pro
  držitele zámku.
- Restart serveru zámky zahodí; klient je při dalším heartbeatu získá
  znovu, pokud je akce volná.
- „Kdo“ je kanonické jméno přihlášeného uživatele (jméno poslané
  klientem server ignoruje); jen bez přihlášení (`--bez-prihlaseni`)
  jméno zadané v prohlížeči.
- Bez oprávnění k úpravě
  (viz [Přihlášení a role](../provoz/prihlaseni.md)) klient zámek nežádá a server
  ho odmítne; přijde-li uživatel o oprávnění během držení zámku, server
  odmítne i jeho další změny.
- Admin a archivář mohou zámek jiné relace vynuceně uvolnit (opuštěná rozdělaná
  práce, tlačítko u hlášky „Akci upravuje …“). Původní držitel při
  dalším heartbeatu přejde jen ke čtení s upozorněním, kdo zámek
  uvolnil; jeho neuložené změny server odmítne.
- Odhlášení uvolní zámky, které relace přihlášení drží.
- Rozpracovaný import patří jménu, ne záložce; vidí ho jen jeho
  vlastník. Během provedení importu server odmítne nahrávání,
  zahození i další provedení téhož importu (příznak v paměti); nahrávat
  z víc záložek najednou lze. Průvodce v jiné záložce upozorní, že se
  import právě nahrává nebo kopíruje jinde.
- Drží-li zámek akce jiná záložka téhož jména, hláška místo „Akci
  upravuje …“ radí zavřít původní záložku. Zámek nové akce, který
  server vzal pro provedení importu, se při přerušení provedení uvolní.
- Provedení importu ze složky `přetřídit` drží navíc zámek zdroje
  `přetřídit/<složka>` (vlastní relace vedle zámku cílové akce,
  heartbeat po přesunutém souboru). Jiné provedení importu téže složky
  server odmítne s uvedením, kdo ji přesouvá; po skončení nebo
  přerušení se zámek uvolní.
