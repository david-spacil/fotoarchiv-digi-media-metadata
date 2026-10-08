# Design

## Context

Verze v kódu zatím není; vydání se značí tagy `vX.Y.Z`. Aplikace se
spouští dvojím způsobem:

| Způsob | `.git` dostupný | Zdroj verze |
|---|---|---|
| lokálně z pracovní kopie (`python -m fotoarchiv`) | ano | `git describe` |
| Docker (`docker compose up -d --build`) | ne, image má jen `fotoarchiv/` | soubor z buildu |

## Goals / Non-Goals

**Goals:** verze běžícího kódu viditelná v rozhraní bez ruční údržby
čísla verze.

**Non-Goals:** verze v CLI (`--version`), na přihlašovací stránce
nebo v exportovaných XMP.

## Decisions

### Verze z `git describe`, ne ručně udržované číslo

`git describe --tags --always --dirty` dá tag vydání, počet commitů po
něm a hash, u neuložených změn `-dirty`. Rozliší i nasazení z agentní
větve. Ručně udržované `__version__` by se mezi vydáními neměnilo
a snadno by se zapomnělo zvýšit.

### Zjistit jednou při startu

Verze se zjistí při vytvoření aplikace a drží se v paměti. Kdyby se
volal git při každém požadavku, ukázal by po `git pull` novou verzi,
přestože server běží se starým kódem.

### Docker: build stage s gitem

Samostatná stage (`alpine/git`) dostane `.git`, spustí `git describe
--tags --always` a zapíše výsledek do souboru; výsledný image zkopíruje
jen ten soubor do `fotoarchiv/VERZE`. Bez `--dirty`: stage nemá pracovní
soubory (vylučuje je `.dockerignore`), takže by verze byla vždy
`-dirty`. Když git selže (např. `.git` je soubor odkazující mimo
kontext u `git worktree`), zapíše se prázdný soubor a verze je neznámá
— build kvůli tomu neselže.

Alternativa: build argument `VERZE` předávaný z `compose.yaml`
(`VERZE=$(git describe) docker compose up`). Zamítnuto: compose
neumí příkaz spustit sám a zapomenutá proměnná dá tiše neznámou verzi
při každém nasazení.

Pořadí zdrojů: git pracovní kopie, pak soubor `VERZE`. Soubor je
v `.gitignore`, v pracovní kopii běžně neexistuje.

## Risks / Trade-offs

- [Image postavený z pracovní kopie s neuloženými změnami ukáže verzi
  bez `-dirty`] → přijatelné; na serveru se nasazuje z čisté pracovní
  kopie.
- [`.git` se posílá do build kontextu] → jen několik MB; do výsledného
  image se nekopíruje.
- [Build potřebuje navíc image `alpine/git`] → stáhne se jednou, pak je
  v cache.
