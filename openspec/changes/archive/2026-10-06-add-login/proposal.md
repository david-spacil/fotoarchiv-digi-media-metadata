## Why

Sdílený server je dostupný z celé interní sítě a zapisuje do archivu
(`write-to-archive`). Bez přihlášení může archiv měnit kdokoli v síti
a jméno u zámku si každý zadá sám. Stejně tak kdokoli může přepsat
připojení k Immichi a kontakt pro Nominatim se zadává jen přepínačem
při spuštění serveru.

## What Changes

- Přístup k aplikaci (stránky i API) jen po přihlášení lokálním účtem.
- Hesla jen jako hash; heslo si uživatel mění sám v aplikaci. Úvodní
  nebo zapomenuté heslo vydá správce příkazem na serveru, aplikace
  vynutí jeho změnu po prvním přihlášení.
- Uživatelé v souboru na serveru: login → kanonické jméno
  `Příjmení, Jméno` a příznak admina. Správa uživatelů v aplikaci není.
- Role admin: jen admin smí měnit nastavení (Immich, kontakt pro
  Nominatim) a vynuceně uvolnit zámek akce.
- Kontakt pro Nominatim se přesouvá z přepínače `--kontakt` do
  nastavení aplikace (jeden globální, ne po uživatelích).
- Identita přihlášeného uživatele nahradí jméno zadané v prohlížeči
  u zámku akce.
- Ve vývojovém režimu jde přihlášení vypnout; pak je každý admin.

## Capabilities

### New Capabilities
- `user-login`: povinné přihlášení, účty, hesla, role admin, odhlášení.

### Modified Capabilities
- `event-lock`: jméno držitele z přihlášení, vynucené uvolnění adminem.
- `immich-people`: nastavení připojení jen pro admina.
- `place-geocoding`: kontakt pro Nominatim z nastavení aplikace.

## Impact

- `fotoarchiv/app.py` (ochrana všech cest, role), nový modul
  přihlašování, `geocode.py` (kontakt za běhu), `__main__.py`
  (odstranění `--kontakt`, příkaz pro vydání hesla), klient
  (přihlášení, změna hesla, odhlášení, nastavení jen pro admina).
- Nové soubory v pracovním adresáři: `uzivatele.json`, `hesla.json`,
  `nominatim.json`, tajný klíč relací.
- Bez nové závislosti: hashe z `werkzeug.security` (součást Flasku).
- Nasazení: zatím HTTP ve interní síti (přijaté riziko), HTTPS přes
  reverzní proxy výhledově.
