[← Dokumentace](../README.md)

# Immich

**Alba dokončených akcí** vymezují fotky akce v Immichi (pro nástroj
pojmenování osob i pro prohlížení). Po dokončení (odebrání přípony
`.ignored`) spustí server hlídače na pozadí: spustí sken knihovny
vybrané v nastavení a pak co 20 s zjišťuje, zda Immich zná všechny
soubory akce; jakmile ano, založí album pojmenované jako akce a později
do něj doplňuje přibývající assety a cizí z alba odebírá. Album ani
asset se nikdy nemažou. Pravidelná synchronizace totéž opakuje pro
každou dokončenou akci (bez skenu), takže album dorovná i po restartu
serveru nebo smazání alba v Immichi; hlídač je jen zrychlení. Vazba
akce → id alba je v `.work/immich-alba.json`; při ztrátě souboru se
album dohledá podle názvu, takže nevznikne duplicitní.

**Stav akce v Immichi** vidí každý přihlášený uživatel na kartě akce
a na ploše akce; bez nastaveného Immiche se nezobrazuje. Hlídač
i synchronizace zapisují do `.work/immich-alba.json` stavy:
`nacitani` („Immich načítá fotky“), `rozpoznavani` („Rozpoznávání
obličejů probíhá“), `rozpoznano` („Obličeje rozpoznány (datum)“)
a `nenalezeno` („Immich fotky akce zatím nenašel“ — hlídač vypršel
a Immich žádné soubory akce nezná). Zobrazení se Immiche neptá:
výpis akcí čte stav ze souboru a plocha jej během načítání
a rozpoznávání obnovuje přes `GET /api/akce/<název>/immich` (ten čte
taky jen soubor; není pod `/api/immich`, který je jen pro admina).
Rozpoznání se pozná jen nepřímo: Immich nemá příznak „obličeje
zpracovány“ — hotovo je, když mají všechny fotky alba zmenšeninu
(`thumbhash`; videa se nepočítají) a fronty `faceDetection`
i `facialRecognition` nemají aktivní ani čekající úlohy. Chyba spojení
nebo chybějící oprávnění stav nemění: zapíše se do `chyba` a vypíše
na stránce Nastavení (jen admin).

**Synchronizace obličejů** běží v serveru po startu, pak každých
15 minut a na tlačítko Načíst osoby:

- Z Immiche se načtou pojmenované osoby (i skryté), jejich assety
  a obličeje na nich; nepojmenované obličeje se ignorují.
- Asset se páruje se souborem podle posledních dvou částí cesty
  (složka akce, soubor), kořen archivu v Immichi se nenastavuje.
  Zpracují se jen akce, které už mají `_metadata.json`. Nedokončenou
  akci Immich nevidí (přípona `.ignored`), obličeje k ní přibudou až
  po dokončení.
- `oblast` se počítá z obdélníku a rozměru, ke kterému ho Immich
  vztahuje (zmenšenina už otočené fotky), takže na měřítku nezáleží.
- `_metadata.json` se přepíše, jen když se obličeje některého souboru
  změnily; soubor bez pojmenovaného obličeje `obliceje` ztratí.
  Synchronizace při zápisu drží zámek akce („Immich (synchronizace)“);
  akci otevřenou uživatelem se zámkem přeskočí a zkusí příště.
- Selže-li kterýkoli dotaz, běh nic nezapíše (neúplná data by obličeje
  mazala). Nastavení ukazuje poslední běh (změněné a přeskočené akce,
  chybu) a čas posledního úspěšného.
- Odpovídal-li záznam o exportu verzi před zápisem, posune se na novou:
  obličeje běžné sidecary nemění.

Ve formuláři souboru jsou osoby jen pro čtení (zašedlá jména
„z Immiche“, u výběru všech souborů); skupina ani akce pole osob nemají.
Bez nastavení pole uvádí „Immich není napojen“. Klient obličeje při
ukládání neposílá, server je převezme z uložené verze.

Přejmenování nebo přesun souboru je v Immichi nový asset bez obličejů;
záloha v `_metadata.json` jde s přejmenováním a obnoví se exportem pro
obnovu.
