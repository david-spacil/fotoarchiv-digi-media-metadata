# AGENTS.md

Pokyny pro AI agenty (Claude Code, Codex aj.) pracující v tomto repozitáři.

## Stav

Repo je ve fázi návrhu: jen `README.md`, žádný kód, build, testy ani
závislosti. Jazyk a stack aplikace nejsou zvolené — nepředjímat, volba jde
přes varianty k odsouhlasení. Až kód vznikne, doplnit sem příkazy (spuštění,
testy, jeden test).

`README.md` je specifikace (archiv, datový model, jména osob, výstupy,
aplikace). Při změně návrhu ho aktualizovat; tady ho neopakovat.

## Invarianty návrhu

Pravidla, která se táhnou přes víc částí README a snadno se poruší:

- **Zdroj pravdy je `_metadata.json` ve složce akce.** XMP sidecary a CSV
  index jsou čistě generované výstupy — nikdy z nich nečíst zpět a nikdy je
  needitovat ručně.
- **Originály fotek a videí se nemění** (žádný zápis EXIF/XMP do souboru).
- **Dědění akce → skupina → soubor**, nižší úroveň přepisuje vyšší. Sidecar
  obsahuje hodnoty už rozepsané (zděděné), JSON jen to, co je na dané úrovni
  zadané.
- `autori` = „fotil někdo z uvedených“, ne přiřazení konkrétní osoby.
- Jména v kanonickém tvaru `Příjmení, Jméno`; seznam návrhů se skládá ze
  všech `_metadata.json` v archivu, žádný pevný číselník. Porovnání ignoruje
  diakritiku, velikost písmen a pořadí slov.
- Zpracovávají se jen složky akcí na první úrovni (`YYYY-MM-DD název`);
  `přetřídit`, `přednášky SKLEP TIC` a `Thumbs.db` se přeskakují.
- Datum u WhatsApp fotek (`IMG-YYYYMMDD-WA*`) jen z názvu souboru, EXIF
  nemají.

## Otevřené otázky

- Jak Immich načítá osoby ze sidecaru (`Iptc4xmpExt:PersonInImage` vs.
  oblasti obličejů vs. tagy) — ověřit dřív, než se zafixuje formát XMP.
- Zdroj souborů `IMG_####.jpg` a jejich EXIF.

## Prostředí

Primárně Fedora. Windows u kolegů žádoucí, ale jen pokud to nestojí dny
práce — neobětovat kvůli tomu jednoduchost na Linuxu.
