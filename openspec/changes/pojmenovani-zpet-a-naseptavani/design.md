## Context

Motivace viz proposal.md. Stav na `main` (f5bdd85):

- Nástroj pojmenování (`fotoarchiv/static/naming.js`) drží frontu osob
  v uzávěru `showNaming`; vyřízená osoba se z fronty vyřadí
  (`vyrid`, `naming.js:59`) a nikde se neuchová. Server pojmenované
  a skryté osoby nenabízí (`naming.py:128`).
- Kroky zapisuje `POST /api/akce/<nazev>/osoby/<person_id>`
  (`app.py:456`): `pojmenovat` a `skryt` přes `PUT /api/people`,
  `sloucit` přes `POST /api/people/merge`, `nevim` jen do
  `.work/pojmenovani.json` (třída `Odlozene`). Po zápisu do Immiche se
  přepočtou počty osob (`jmena_precti`) a poznamená změna
  (`jmena_zmeny`) pro synchronizaci při `hotovo`.
- Nabízené osoby nemají jméno a nejsou skryté, takže stav „před
  krokem“ je vždy známý: bez jména, neskrytá, neodložená.
- Našeptávání je `ul.suggest` s `position: absolute` v obalu
  `.names` (`style.css:764`, `:772`). V nástroji ho ořízne
  `dialog.nastroj-osoby { max-height: 94vh; overflow: auto }`
  (`style.css:416`), v panelu editoru `#panel { overflow: auto }`
  (`style.css:503`). Nástroj má vlastní kopii logiky (`naming.js:338`,
  `:385–404`, 8 návrhů), panel svou v `namesField` (`app.js:3129`).
- Okno nástroje je modální `<dialog>` v horní vrstvě (top layer)
  prohlížeče; prvek mimo horní vrstvu se nad něj nedostane žádným
  `z-index`.

## Goals / Non-Goals

**Goals:**
- Vrácení posledního kroku bez nového stavu na serveru a bez nových
  oprávnění klíče Immiche.
- Jeden mechanismus zobrazení návrhů pro nástroj i panel.

**Non-Goals:**
- Vrácení sloučení, historie víc kroků, Zpět po zavření nástroje.
- Změna obsahu, pořadí a filtrování návrhů a ovládání seznamu
  (šipky, Enter, výběr myší zůstávají, jak jsou).
- macOS (Alt+Backspace tam v poli maže slovo; aplikace se tam
  nepoužívá).

## Decisions

### 1. Zpět jako nový endpoint bez stavu na serveru

`POST /api/akce/<nazev>/osoby/<person_id>/zpet` s tělem
`{"krok": "pojmenovat" | "skryt" | "nevim", "jmeno": "…"}`. Server
ověří oprávnění a osobu v albu stejně jako `osoby_jednat`, pak:

| krok | kontrola stavu v Immichi | zápis |
|---|---|---|
| pojmenovat | osoba má přesně `jmeno` | `PUT /api/people` `name: ""` |
| skryt | osoba má `isHidden: true` | `PUT /api/people` `isHidden: false` |
| nevim | — | `Odlozene.zrusit(login, akce, id)` |

Nesouhlasí-li stav, vrátí 409 `{"chyba": "zmeneno"}` a nic nezapíše.
Chyba Immiche = 502 jako u kroku. Po zápisu do Immiche přidá
`(login, akce)` do `jmena_zmeny` a vrátí přepočtené počty
(`jmena_precti`), takže `hotovo` spustí synchronizaci. Stav osoby se
čte novou metodou klienta `person(id)` (`GET /api/people/{id}`,
oprávnění `person.read`, které klíč už má).

Co a kdy jde vrátit, ví jen klient (poslední krok v uzávěru nástroje).
Zavřením nástroje tak Zpět zanikne samo, bez úklidu na serveru.

*Alternativa:* server si pamatuje poslední krok na `(login, akce)`.
Zamítnuto: stav by musel zaniknout při zavření nástroje a restartu
serveru a nepřinese žádnou ochranu navíc. Archivář smí touž osobu
přejmenovat nebo skrýt i běžným krokem, takže endpoint, který věří
klientovi, co vrátit, oprávnění nerozšiřuje.

*Alternativa:* vracet přes existující endpoint akcí `odjmenovat`
a `odkryt`. Zamítnuto: `pojmenovat` odmítá prázdné jméno (spec
Pojmenování osoby) a míchání by rozbilo jeho kontroly (kanonický tvar,
nabídka sloučení).

Prázdné jméno po vrácení není v rozporu s pravidlem „Prázdné jméno
MUST NOT jít uložit“: vrácení neukládá jméno, obnovuje stav, který
osoba měla.

### 2. Stav kroku v klientovi

`s.posledni = { typ, os, jmeno }` se nastaví v `uspesne` po
`pojmenovat` (i „Ponechat samostatně“), `skryt` a `nevim`; po `sloucit`
se vymaže. Vymaže se i po vrácení, po novém kole a při 409 `zmeneno`.
Vrácení vrátí osobu na začátek fronty (čistá funkce `vratit(fronta,
os)` vedle `vyrid`), sníží `s.vyslo`, u odložení i `s.odlozene`,
a u pojmenování předvyplní `s.priorJmeno`. Pak `dalsi()`, takže
vrácená osoba je aktuální.

Tlačítko „Zpět (Alt+⌫)“ stojí v řadě voleb vlevo od „Uložit“ (vrácení
předchozí volby, ne volba nad aktuální osobou), neaktivní bez kroku.
Na obrazovce konce kola je vedle „Zavřít“. Zápis hlídá tentýž zámek
`s.zapisuje` jako ostatní volby.

### 3. Zkratka Alt+Backspace

`zkratka(e)` vrátí `"zpet"` pro `Backspace` s Alt bez dalších
modifikátorů a bez `repeat`; listener na dialogu volá
`preventDefault`, takže v poli nic nesmaže (na Windows Alt+Backspace
v poli jinak vrací psaní). Ctrl+Z zamítnuto: v poli vrací psaní.

### 4. Upozornění u sloučení

Text nabídky sloučení (`vykresSlouceni`) dostane větu „Sloučení nejde
v nástroji vrátit.“ Jiný mechanismus (potvrzovací dialog) se
nepřidává: sloučení už samo je potvrzení nabídky.

### 5. Návrhy v horní vrstvě (Popover API)

Nový modul `fotoarchiv/static/naseptavani.js`:

- čistá funkce `umisteni({ pole, okno, vyska })` → `{ left, width,
  top, maxHeight, smer }` (`top` vždy od horní hrany okna, `smer`
  = `"dolu"` | `"nahoru"`): `pole` = obdélník pole
  (`getBoundingClientRect`), `okno` = viditelná část okna
  (`visualViewport`: výška a posun, tedy bez klávesnice telefonu),
  `vyska` = přirozená výška seznamu. Dolů, když se vejde; jinak
  nahoru, když je nahoře víc místa; jinak tam, kde je místa víc,
  s `maxHeight` a posuvníkem uvnitř seznamu;
- `pripojNaseptavani(input, list)` dá seznamu `popover="manual"`,
  při otevření `showPopover()` a umístění přes `position: fixed`.
  Zavře se (`hidePopover`) při posunu kteréhokoli předka
  (posluchač `scroll` v capture fázi na `document`, kromě posunu
  uvnitř seznamu), přepočítá se při `resize` okna
  a `visualViewport`.

Seznam v horní vrstvě leží i nad modálním dialogem, protože se do ní
dostane později než dialog. Ovládání zůstává v obou polích beze
změny; obě místa jen nahradí `list.hidden = …` voláním modulu.
`namesField` slouží i místům (`people = false`); mechanismus tak
dostanou i ta, bez změny chování.

*Alternativa:* jen otevírat seznam nahoru uvnitř okna. Zamítnuto
rozhodnutím v issue #55 (seznam má přetéct okno).
*Alternativa:* seznam přesunout do `document.body` se `z-index`.
Zamítnuto: nad modální `<dialog>` v horní vrstvě se nedostane.
*Alternativa:* zrušit `overflow: auto` u dialogu a panelu. Zamítnuto:
na malém displeji se obsah okna musí posouvat.

### 6. Počet návrhů

Nástroj přestane ořezávat na 8 (`slice(0, 8)`); server jich vrací
nejvýš 10 (`names.suggest`, `limit=10`). Panel beze změny.

## Risks / Trade-offs

- [Immich nemusí `name: ""` brát jako „bez jména“.] → V OpenAPI je
  `name` volitelný řetězec bez minimální délky. Chování nasazené
  verze ověří ruční zkouška (nástroj osobu po vrácení znovu nabídne
  a v Immichi je bez jména); agent na skutečný Immich nesahá.
- [Jiný archivář dá osobě mezi krokem a vrácením totéž jméno.] →
  Kontrola stavu projde a vrácení jeho jméno smaže; okno je krátké
  a následek se opraví novým pojmenováním. Přijato.
- [Popover API: Chrome 114+, Firefox 125+, Safari 17+.] → Cílové
  prohlížeče (desktop Chrome/Firefox, Android Chrome) ho mají; jinak
  se seznam ukáže na místě jako dnes (`showPopover` chybí → zůstane
  dnešní `hidden`).
- [Souběh se změnou `mobilni-verze`, která mění `app.js`
  a `style.css`.] → Změny se dotýkají jiných míst; panel jako spodní
  list bude návrhy kreslit stejným modulem. Případný konflikt
  vyřeší rebase té změny.
- [DOM a CSS nástroje se netestují automaticky.] → Čisté funkce
  (`umisteni`, `zkratka`, `vratit`) mají testy v `tests/js/`;
  zobrazení ověří skriptovaná kontrola v prohlížeči.
