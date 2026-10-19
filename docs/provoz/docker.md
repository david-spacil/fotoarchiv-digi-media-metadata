[← Dokumentace](../README.md)

# Docker

Pro server s Dockerem (např. tam, kde běží Immich) je v repozitáři
`Dockerfile`, `compose.yaml` a `.env.example`. Kontejner běží
v produkčním režimu (`--zapis-do-archivu`) na serveru cheroot v jediném
procesu bez varování vývojového serveru, archiv se připojuje z hostitele
(typicky SMB/CIFS mount) a pracovní adresář je bind mount `./work`;
správce v něm ručně edituje `uzivatele.json`. Před nasazením verze
s rolemi přepsat `"admin": true` na `"role": "admin"` (a doplnit
`"role": "archivar"`), jinak se kontejner restartuje dokola a důvod je
v `docker compose logs`.

```sh
cp .env.example .env          # a vyplnit FOTOARCHIV_ARCHIV, UID, GID
mkdir work                    # pracovní adresář vedle repozitáře
docker compose up -d --build  # http://127.0.0.1:5000
```

Archiv musí být připojený **před** startem kontejneru: jinak Docker
připojí prázdnou složku a po připojení SMB je potřeba kontejner
restartovat (`docker compose restart fotoarchiv`).

Kontejner běží pod UID/GID z `.env` (`user:` v compose). U archivu na
CIFS musí odpovídat vlastníkovi, kterého určují volby mountu (soubor
s přihlašovacími údaji číst netřeba):

```sh
A=/mnt/x/fotoarchiv/FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB
stat -c '%u:%g' "$A"
findmnt -no OPTIONS -T "$A"   # volby uid=, gid=, file_mode=, dir_mode=
```

Stejné UID musí mít i `./work` (`chown UID:GID work`), jinak aplikace
nezapíše cache ani hesla. Zápis do archivu ověřit před ostrým startem
přímo z kontejneru:

```sh
docker compose run --rm --entrypoint sh fotoarchiv \
  -c 'touch /archiv/.zapis-test && rm /archiv/.zapis-test'
```

Účty a příkazy v kontejneru:

```sh
# účty edituje správce na hostiteli: work/uzivatele.json
# (viz Přihlášení a role), pak jednorázové heslo:
docker compose exec fotoarchiv python -m fotoarchiv heslo LOGIN --work /work
# dávkový export XMP všech akcí:
docker compose exec fotoarchiv python -m fotoarchiv exportovat \
  --archiv /archiv --work /work --zapis-do-archivu
# kontrola poškozených souborů všech akcí (archiv jen čte):
docker compose exec fotoarchiv python -m fotoarchiv zkontrolovat \
  --archiv /archiv --work /work
# jednorázové skrytí nedokončených akcí před Immichem (při zastaveném
# serveru; bez --zapis-do-archivu jen výpis):
docker compose stop fotoarchiv
docker compose run --rm fotoarchiv skryt \
  --archiv /archiv --work /work --zapis-do-archivu
docker compose start fotoarchiv
```

Aktualizace: `git pull && docker compose up -d --build`.

Verzi v hlavičce zapíše build image z `.git` (`git describe --tags
--always`, bez příznaku neuložených změn); `.git` se do image
nekopíruje. Image postavený mimo pracovní kopii gitu ukáže „verze
neznámá“.

Poznámky:

- Vývojový režim v kontejneru: v `compose.yaml` odebrat
  `--zapis-do-archivu` z `command` (metadata pak jdou do `/work`).
- Až poběží reverzní proxy s HTTPS, přidat do `command` přepínač
  `--https` (cookie relace jen přes HTTPS).
- Server smí běžet jen v jedné instanci (zámky akcí v paměti).
- Immich se nastavuje v aplikaci adresou dosažitelnou z kontejneru,
  např. adresou hostitele; případně lze připojit kontejner do sítě
  Immiche jako external network v compose.
