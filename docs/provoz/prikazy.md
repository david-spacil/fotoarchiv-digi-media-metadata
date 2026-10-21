[← Dokumentace](../README.md)

# Příkazy

Bez podpříkazu `python -m fotoarchiv` spustí server (přepínače viz
[Lokální spuštění](spusteni.md)). Příkazy berou `--archiv` a `--work`
jako server (`heslo` jen `--work`). `exportovat`, `zkontrolovat`,
`skryt`, `migrovat` a `vysypat` bez `--zapis-do-archivu` archiv jen
čtou; `prevzit` zapisuje do archivu vždy. V kontejneru se spouštějí
přes `docker compose exec fotoarchiv python -m fotoarchiv …` (viz
[Docker](docker.md)).

| příkaz | co dělá | podrobnosti |
|--------|---------|-------------|
| `heslo LOGIN` | vydá jednorázové heslo pro login z `.work/uzivatele.json` | [Přihlášení a role](prihlaseni.md) |
| `exportovat [AKCE]` | zapíše XMP sidecary jedné nebo všech akcí, jen změněné; `--obliceje` přidá oblasti obličejů pro obnovu Immiche | [Ukládání a export](../navrh/ukladani-a-export.md), [Výstupy](../navrh/vystupy.md) |
| `zkontrolovat [AKCE]` | najde poškozené soubory a nálezy konzistence akcí; `--rychle` jen konzistence, `--zapis-do-archivu` po potvrzení nápravu přesuny | [Poškozené soubory](../navrh/poskozene-soubory.md) |
| `skryt` | skryje nedokončené akce před Immichem (přípona `.ignored`); spouštět při zastaveném serveru | [Archiv](../navrh/archiv.md) |
| `migrovat` | převede `_metadata.json` ze schématu `/1` na `/2` (bez autorů celé akce, starších `osoby` a data od/do u skupiny); spouštět při zastaveném serveru | [Datový model](../../README.md#datový-model) |
| `vysypat` | vypíše akce v koši s datem trvalého smazání; s `--zapis-do-archivu` trvale smaže ty po 7denní lhůtě a jejich alba v Immichi (server to dělá sám denně) | [Archiv](../navrh/archiv.md) |
| `prevzit` | jednorázově převezme `_metadata.json` z `.work` do archivu | [Ukládání a export](../navrh/ukladani-a-export.md) |
