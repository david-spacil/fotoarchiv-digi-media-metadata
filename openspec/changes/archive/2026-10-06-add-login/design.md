## Context

Server po `write-to-archive`: jeden proces na Debianu ve firemní síti,
zámek v paměti, jméno uživatele z prohlížeče. Nastavení Immiche smí
měnit kdokoli, kontakt pro Nominatim je přepínač `--kontakt`.

## Goals / Non-Goals

**Goals:**
- Aplikace se o přihlášení stará co nejméně (jedna vstupní kontrola).
- Uživatel si heslo spravuje sám; správce hesla nevidí ani nezadává
  v aplikaci.
- Odlišit admina od běžného uživatele u nastavení serveru.

**Non-Goals:**
- Role a oprávnění po akcích (všichni přihlášení smějí s akcemi totéž).
- Správa uživatelů v aplikaci (přidání, role) — jen soubor na serveru.
- Přístup mimo firemní síť, obnova hesla e-mailem.

## Decisions

**Lokální účty (dříve varianta C).** Uživatel si má měnit heslo sám
v aplikaci, což u SSO proxy (A) ani LDAP (B) nedává smysl — heslo patří
adresáři. Mapa uživatelů je na způsobu ověření nezávislá, pozdější
přechod na A/B vymění jen ověření hesla.

**Dva soubory v pracovním adresáři, oba s právy jen pro vlastníka:**
- `uzivatele.json` píše ručně správce, aplikace ho jen čte:
  ```json
  {"spacil": {"jmeno": "Spáčil, David", "admin": true}}
  ```
- `hesla.json` píše jen aplikace: login → hash, příznak „změnit při
  přihlášení“. Oddělené, aby aplikace nepřepisovala ručně editovaný
  soubor a hash se nedostal do souboru, který se kopíruje a upravuje.

Alternativa jeden soubor: zápis aplikace by kolidoval s ruční editací.

**Hash** `werkzeug.security.generate_password_hash` (výchozí scrypt
se solí), ověření `check_password_hash`. Bez nové závislosti.

**Úvodní a zapomenuté heslo** vydá správce na serveru:
`python -m fotoarchiv heslo LOGIN --work .work` vygeneruje náhodné
jednorázové heslo, vypíše ho a uloží jeho hash s příznakem změny. Po
přihlášení jednorázovým heslem aplikace pustí jen na změnu hesla.
Správce tak heslo předává, ale nezná výsledné heslo uživatele a webová
administrace hesel nevzniká.

**Relace** podepsanou cookie Flasku; tajný klíč se vygeneruje při
prvním spuštění do pracovního adresáře (přežije restart). Relace nese
login a otisk hashe hesla: změna hesla nebo nové heslo od správce
zneplatní ostatní relace uživatele. Odebrání uživatele
z `uzivatele.json` zneplatní jeho relace při dalším požadavku (soubor
se čte při změně mtime).

**Admin** podle `uzivatele.json`. Jen admin: stránka nastavení (Immich
včetně synchronizace na požádání, kontakt pro Nominatim) a vynucené
uvolnění zámku. Kontrolu dělá server; klient admin prvky jen skryje.

**Kontakt pro Nominatim** v `nominatim.json`, nastavuje admin na
stránce nastavení; prázdný formulář předvyplní e-mail přihlášeného
admina (je-li v `uzivatele.json` pole `email`), uloží se ale jako jeden
globální kontakt provozovatele. Geocoder čte kontakt za běhu, změna platí bez restartu.
`--kontakt` se odstraní; při prvním spuštění s ním server hodnotu
převezme do `nominatim.json` a upozorní, že přepínač je zastaralý.

**Vývojový režim:** přepínač `--bez-prihlaseni` jen bez
`--zapis-do-archivu`; pak jméno u zámku z prohlížeče jako dnes a každý
je admin. Produkční režim bez přihlášení server nespustí.

**Pokusy o přihlášení:** po 5 chybných pokusech na login prodleva
roste (v paměti, jeden proces). Odpověď neprozradí, zda login existuje.

## Risks / Trade-offs

- [Zatím bez HTTPS: hesla a cookie relace jdou firemní sítí v otevřené
  podobě] → přijaté riziko do domluvy reverzní proxy s IT; přihlášení
  chrání proti omylu a neoprávněné změně kolegou, ne proti odposlechu
  v síti. Aplikace na HTTP při přihlášení upozorní; cookie je
  `HttpOnly` a `SameSite=Lax`, `Secure` se zapne přepínačem `--https`, až bude
  HTTPS. Uživatelé nemají používat heslo z jiných systémů.
- [Jednorázové heslo předávané mimo aplikaci] → platí jen do první
  změny; správce ho může kdykoli znovu vydat.
- [Ztráta `hesla.json`] → všichni dostanou nové jednorázové heslo;
  archivu se to netýká.

## Open Questions

- Reverzní proxy s HTTPS od IT (výhledově); pak zapnout `Secure` cookie
  a server pustit jen na localhost.
