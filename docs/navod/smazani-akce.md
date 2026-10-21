[← Dokumentace](../README.md)

# Smazání akce

Akci, která do archivu nepatří (omyl při importu, duplicita, soukromé
fotky), může smazat jen **admin**. Smazání nic hned nemaže: akce leží
7 dní v koši, odkud ji admin může obnovit; teprve potom ji server
smaže natrvalo (návrh viz [Archiv](../navrh/archiv.md)).

- **Smazat:** na ploše akce i v průvodci prvním otevřením tlačítko
  **Smazat akci…** v liště. Dialog chce opsat název akce (přesně,
  včetně data) a uvést důvod; tlačítko „Smazat do koše“ je aktivní,
  až obojí sedí. Neuložené změny se před smazáním uloží. Má-li akci
  otevřenou jiný uživatel, tlačítko je vypnuté (server smazání stejně
  odmítne). Po smazání se vrátíte na seznam akcí; akce v něm, v indexu
  ani v návrzích jmen už není a Immich ji nevidí. U dokončené akce
  server hned spustí sken knihovny v Immichi, takže fotky tam zmizí
  (Immich je označí jako offline a přesune do svého koše).
- **Koš:** odkaz **Koš** na seznamu akcí (jen admin). Tabulka ukazuje
  smazané akce od nejnovějších: kdo a kdy je smazal, důvod, počet
  souborů a kdy se smažou natrvalo. Složka v koši bez záznamu
  o smazání je uvedena jako neznámá — aplikace ji nikdy nesmaže ani
  neobnoví, řeší ji správce archivu ručně.
- **Obnovit:** tlačítko u akce v koši vrátí složku pod původní název
  (nedokončená zůstane skrytá před Immichem) i se stavem akce: vazbou
  na album, stavem v Immichi a záznamem exportu. U dokončené akce
  server spustí sken knihovny, Immich fotky vrátí z offline a album se
  dorovná jako po dokončení. Vznikla-li mezitím
  akce stejného názvu, obnovení se odmítne.
- **Trvalé smazání:** server při startu a pak jednou denně smaže akce
  starší 7 dní i s jejich albem v Immichi (fotky z Immiche zmizely už
  skenem po smazání a natrvalo je odstraní koš Immiche). Okamžité trvalé smazání aplikace nenabízí; ručně
  jde koš vysypat příkazem `vysypat`
  (viz [Příkazy](../provoz/prikazy.md)).

Ve vývojovém režimu dialog jen ukáže, kam by se složka přesunula
a kdy by se smazala natrvalo; archiv se nemění a koš je prázdný.
