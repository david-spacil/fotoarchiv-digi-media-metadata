[← Dokumentace](../README.md)

# Nastavení Immiche

Stránka **Nastavení** (odkaz v hlavičce) drží adresu serveru Immich,
API klíč a výběr knihovny archivu. Klíč potřebuje čtení osob, assetů
a obličejů (`person.read`, `asset.read`, `face.read`, `asset.view`);
pro alba akcí, sken knihovny, stav rozpoznávání a nástroj pojmenování
osob i práva k zápisu a čtení front (`person.update`, `person.merge`,
`album.read`, `album.create`, `album.delete` — jen smazání alba akce
vysypané z koše —, `albumAsset.create`, `albumAsset.delete`,
`library.read`, `library.update`, `queue.read`) — klíč s `all` kryje
vše. Sken knihovny a fronty jsou v Immichi jen pro admina, klíč musí
patřit uživateli s rolí admin. Nastavení se ukládá do
`.work/immich.json` (práva 0600), nikdy do archivu; klíč se do
prohlížeče nevrací (jen „klíč nastaven (…W4No)“) a změna adresy
vyžaduje zadat ho znovu; výběr knihovny se uloží i bez nového klíče
(`knihovna` v `immich.json`, nabídne ho `GET /api/immich/knihovny`).
Otestovat ověří verzi, osoby a čtení obličejů a navíc porovná
oprávnění klíče: chybějící oprávnění, klíč uživatele bez role admin
(odpověď `GET /api/libraries` je 403) a nevybranou knihovnu vypíše
jako varování — čtení obličejů funguje i bez nich, alba akcí, sken
a nástroj pojmenování ne. Nastavení (i synchronizaci na požádání)
smí jen admin.
