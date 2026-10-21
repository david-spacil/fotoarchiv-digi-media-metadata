## 1. Server: vrácení kroku

- [x] 1.1 `immich.py`: metoda klienta `person(id)` (`GET
  /api/people/{id}`); `FakeImmich` v `tests/test_immich.py` ji obslouží
  ze `self.people`. Ověření: test v `tests/test_immich.py` vrátí jméno
  a `isHidden` osoby.
- [x] 1.2 `naming.py`: `Odlozene.zrusit(login, akce, person_id)` odebere
  jedno id (atomický zápis, chybějící id nic nedělá). Ověření: testy
  v `tests/test_naming.py` (odebrání, jiný uživatel nedotčen,
  chybějící id).
- [x] 1.3 `app.py`: `POST /api/akce/<nazev>/osoby/<person_id>/zpet`
  podle design.md (rozhodnutí 1): oprávnění a osoba v albu jako
  `osoby_jednat`, kontrola stavu, 409 `zmeneno`, 502 při chybě
  Immiche, `jmena_zmeny` a `jmena_precti` po zápisu. Ověření: testy
  v `tests/test_app.py` proti `FakeImmich`: vrácení pojmenování
  (`name: ""` v `writes`), skrytí (`isHidden: false`), odložení (osoba
  zpět v `GET /osoby`), cizí přejmenování → 409 a žádný zápis, chyba
  Immiche → 502, bez role → 403, osoba mimo album → 404, `hotovo` po
  vrácení spustí synchronizaci.
- [x] 1.4 Testy Pythonu projdou: `.venv/bin/python -m pytest -q`.

## 2. Klient: krok zpět v nástroji

- [x] 2.1 `naming.js`: čistá funkce `vratit(fronta, os)` (osoba na
  začátek fronty, bez duplicity) a `zkratka` vrací `"zpet"` pro
  Alt+Backspace (bez Ctrl/Meta/Shift, bez `repeat`). Ověření: testy
  v `tests/js/naming.test.mjs`.
- [x] 2.2 `naming.js`: stav `s.posledni`, nastavení a mazání podle
  design.md (rozhodnutí 2), volání endpointu `zpet`, obsluha 409
  `zmeneno` (hláška, Zpět zmizí) a chyby Immiche (hláška, Zpět
  zůstane), předvyplnění jména, úprava počítadla a počtu odložených.
- [x] 2.3 `naming.js`: tlačítko „Zpět (Alt+⌫)“ v řadě voleb
  i na obrazovce konce kola, neaktivní bez kroku; zkratka v listeneru
  dialogu s `preventDefault`; text nabídky sloučení s větou
  o nevratnosti.
- [x] 2.4 `docs/navod/pojmenovani-osob.md`: krok zpět (co vrátí, jen
  poslední krok, ne sloučení, zkratka) a nevratnost sloučení.
- [x] 2.5 Testy JS projdou: `node --test tests/js/*.test.mjs`
  (zkontrolovat počet testů ve výstupu).

## 3. Klient: návrhy jmen přes okraj

- [x] 3.1 Nový modul `fotoarchiv/static/naseptavani.js` s čistou
  funkcí `umisteni` a `pripojNaseptavani(input, list)` podle design.md
  (rozhodnutí 5). Ověření: `tests/js/naseptavani.test.mjs`: dost
  místa dole → dolů; málo dole a víc nahoře → nahoru; klávesnice
  (`visualViewport` nižší než okno) → nahoru; málo místa obojí →
  větší strana s `maxHeight`; šířka a levý okraj podle pole.
- [x] 3.2 `style.css`: `.suggest` jako `position: fixed` v horní vrstvě
  (zrušit výchozí `inset`/`margin` popoveru), `overflow: auto` pro
  `maxHeight`; vzhled položek beze změny.
- [x] 3.3 Napojit modul v `naming.js` (místo `suggest.hidden`) a zrušit
  `slice(0, 8)`; napojit v `namesField` (`app.js`). Ovládání šipkami,
  Enterem, Esc a myší beze změny.
- [x] 3.4 Testy JS projdou: `node --test tests/js/*.test.mjs`.

## 4. Ověření v prohlížeči (dummy data)

- [x] 4.1 Dummy archiv ve scratch s akcí, albem a ≥ 12 jmény
  v `_metadata.json` jiných akcí; server proti podvrženému Immichi
  (vzor z `tests/test_immich.py`), žádná skutečná data.
- [x] 4.2 Headless prohlížeč, desktop: v nástroji pojmenování
  10 návrhů celých pod dolním okrajem okna (screenshot); pole
  v panelu u dolního okraje → návrhy nad polem nebo přes okraj,
  panel neposunutý; posun panelu seznam zavře.
- [x] 4.3 Headless prohlížeč, telefon (šířka 412 px, zmenšený
  `visualViewport`): seznam nad polem.
- [x] 4.4 Headless prohlížeč: pojmenovat → Zpět (tlačítko i
  Alt+Backspace) → osoba znovu s předvyplněným jménem; skrýt → Zpět;
  odložit → Zpět; po sloučení Zpět neaktivní; konec kola → Zpět.

## 5. Ruční zkouška se skutečným Immichem (uživatel)

- [ ] 5.1 Uživatel na své instanci: pojmenovat osobu, Zpět → v Immichi
  je osoba bez jména a nástroj ji znovu nabídne; skrýt, Zpět → osoba
  v Immichi viditelná. Potvrzuje, že Immich bere `name: ""` jako „bez
  jména“ (design.md, Risks).
- [ ] 5.2 Uživatel na telefonu: návrhy v nástroji i v panelu nejsou
  oříznuté ani schované pod klávesnicí.
