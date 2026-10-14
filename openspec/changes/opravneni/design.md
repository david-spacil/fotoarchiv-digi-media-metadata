## Context

Motivace viz proposal.md. Dnes `auth.Users.get` vrací `{jmeno, email,
admin}` a soubor načítá znovu při změně mtime; rozepsaný (nečitelný)
soubor znamená „nikdo“. Vstupní kontrola v `app.py` (`check_login`)
hlídá jen prefixy `/api/immich` a `/api/nominatim`, vynucené uvolnění
zámku kontroluje endpoint sám. Každá změna akce (uložení, dokončení,
úklid, import do stávající akce) už vyžaduje zámek (`require_lock`),
zámek se získává v `zamek_ziskat`. `/api/akce` vrací u akce `upravili`
(výpis v `archive.list_events`). Import do nové akce zakládá
`_metadata.json` ve `write_description` bez `upravili`. Endpointy
importů berou vlastníka z `jmeno` v těle nebo v `?jmeno=` (asi 12 míst,
`check_import` a `imports.*`); `Imports._owner` ho normalizuje přes
`names.normalize`.

## Goals / Non-Goals

**Goals:**
- Jedno místo rozhodnutí „smí upravit“, sdílené zámkem, `require_lock`
  i výpisem akcí.
- Uživatel, který akci naimportoval, ji hned smí upravit.
- Identita u importů z relace stejně jako u zámku.

**Non-Goals:**
- Správa rolí v aplikaci (dál jen ruční `uzivatele.json`).
- Oprávnění na úrovni skupin nebo souborů.
- Omezení čtení (náhledy, originály, `/api/jmena`) — vidí všichni.
- Úprava klienta u importů: dál posílá `jmeno`, server ho s přihlášením
  ignoruje (bez přihlášení ho potřebuje).

## Decisions

**Pole `role` (`"admin"` | `"archivar"`), bez role běžný uživatel.**
Jedna hodnota místo dvou příznaků vylučuje nesmyslné kombinace
a přidání další role nemění schéma. `Users.get` vrací `role` (None pro
běžného uživatele); odvozené `admin` a `archivar` (admin ⊃ archivář pro
správu archivu) počítá jedna pomocná funkce, aby se pravidla nerozlévala
po `app.py`.

**Kontrola souboru: `Users.problems()`** vrátí seznam (login, důvod)
pro záznamy s klíčem `admin` nebo s neznámou `role`.
- Start serveru (`__main__`) a příkaz `heslo`: neprázdný seznam →
  `sys.exit` s výpisem loginů a návodem `"admin": true` →
  `"role": "admin"`. Odmítnout, ne ignorovat: tiché ignorování by
  z admina po nasazení udělalo běžného uživatele.
- Za běhu (načtení po změně mtime): chybný záznam se do `_users` nedá
  (login → 401, stejně jako rozepsaný soubor), ostatní fungují dál;
  chyba jednou do logu (`logging.warning`) při každém novém načtení.
  Pád serveru by kvůli překlepu shodil všechny.

**Rozhodnutí o úpravě v jedné funkci** `model.can_edit(user, doc)`:
admin/archivář → True; jinak `names.normalize(jmeno)` ∈
`{names.normalize(k) for k in upravili}`. Porovnání přes `normalize`
kvůli invariantu o jménech (diakritika, pořadí slov).

**Vynucení na zámku a v `require_lock`.** `zamek_ziskat` vrátí 403
`{"chyba": "jen_cteni"}`; `require_lock` po kontrole zámku znovu ověří
oprávnění (role mohla zmizet během držení zámku). Tím jsou kryté
uložení, dokončení, úklid i import do stávající akce bez úprav
jednotlivých endpointů. Alternativa — kontrola v každém zapisujícím
endpointu — je víc míst k zapomenutí. `require_lock` načte uložený
dokument jen pro uživatele bez role; admin/archivář I/O nemá.

**Výpis akcí nese `upravit: bool`** spočtené serverem; klient
oprávnění nepočítá. `/api/ja` vrací `role` a odvozené `admin`
a `archivar` (klient rozhoduje podle nich, ne podle řetězce role).

**Správa archivu (admin i archivář)**: `/api/pretridit`
a `zamek_vynutit` kontrolují `archivar`; `import_create` se `zdroj`
a `import_execute` u importu se zdrojem vrátí 403. `ADMIN_PREFIXES`
zůstává jen pro Nastavení. Mazání poškozeného souboru zdroje je pod
importem se zdrojem, takže ho kryje vlastnictví importu.

**Vlastník importu z relace**: pomocná `owner()` v `app.py` vrátí
`g.user["jmeno"]`, bez přihlášení `jmeno` z těla / `?jmeno=`; nahradí
všechna čtení `jmeno` u importů. Stávající rozpracované importy mají
v záznamu kanonické jméno z doby, kdy ho klient bral z `/api/ja`,
takže dál patří svému autorovi.

**Klient**: při `upravit === false` plocha nezískává zámek a jede
stávající cestou jen ke čtení (`state.readonly`) s vlastním textem
„Akci upravují jen ti, kdo ji importovali nebo upravovali, archivář
a admin.“ — bez „Zkusit znovu“. Karta v seznamu dostane drobný štítek
„jen ke čtení“. Cíl importu filtruje `state.events` na `upravit`.
Odkaz Přetřídit, volba zdroje v kroku Soubory a „Uvolnit zámek“ podle
`me.archivar`; Nastavení podle `me.admin`.

**`upravili` při importu**: `write_description` zavolá `model.touch`
jménem z `owner()` u nové akce i akce s `_metadata.json`. U akce bez
`_metadata.json` se nic nezapisuje (jen návrh); takovou akci jako cíl
stejně smí jen admin/archivář. Mění se invariant v AGENTS.md
(`upravili` píše `akce_save`, `akce_finish` a zápis po importu).

## Risks / Trade-offs

- [Server po nasazení nenastartuje kvůli starému `uzivatele.json`] →
  záměr; chyba vypíše přesně, co přepsat. Docker: kontejner se
  restartuje dokola, chyba je v `docker compose logs`.
- [Starší akce bez `upravili` zamrznou pro běžné uživatele] → záměr
  issue; archivář/admin je upraví, odemkne je tím jen pro sebe.
- [Uživatel, který jednou uložil cizí akci (dnes ještě volně), ji smí
  upravovat i nadále] → přijaté; `upravili` se nečistí.
- [Klient spoléhá na `upravit` z výpisu, který může zastarat] → server
  rozhoduje při zámku; zastaralý výpis skončí 403 a plochou jen ke
  čtení.

## Migration Plan

Před nasazením správce přepíše v `uzivatele.json` `"admin": true` na
`"role": "admin"` a lidem, kteří mají upravovat všechno, doplní
`"role": "archivar"`. Bez toho server nenastartuje a řekne proč. Návrat
na předchozí verzi vyžaduje vrátit `"admin": true` (stará verze `role`
nezná a admin by v ní byl běžný uživatel); `upravili` zapsané importem
je platné i pro ni.
