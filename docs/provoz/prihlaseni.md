[← Dokumentace](../README.md)

# Přihlášení a role

Účty jsou lokální. Uživatele zapisuje správce ručně do
`.work/uzivatele.json` (login → kanonické jméno, volitelně e-mail
a role); aplikace ho jen čte, změna platí bez restartu a odebraný
uživatel přijde o přístup při dalším požadavku:

```json
{"prikladny": {"jmeno": "Příkladný, Daniel", "email": "…",
               "role": "admin"},
 "novak": {"jmeno": "Novák, Petr", "role": "archivar"},
 "modelova": {"jmeno": "Modelová, Zuzana"}}
```

Role je `"admin"`, `"archivar"`, nebo chybí (běžný uživatel).
Dřívější zápis `"admin": true` a neznámá role jsou chyba: server ani
příkaz `heslo` nenastartují a vypíšou chybné loginy s návodem
(`"admin": true` → `"role": "admin"`). Objeví-li se chybný záznam za
běhu, server běží dál, chybný login nemá přístup (401) a chyba jde do
logu.

Úvodní nebo zapomenuté heslo vydá správce na serveru:

```sh
.venv/bin/python -m fotoarchiv heslo LOGIN --work .work
```

Příkaz vypíše jednorázové heslo; po přihlášení s ním aplikace pustí
jen na změnu hesla. Vydání nového hesla ukončí stávající relace
uživatele. Heslo si pak uživatel mění sám (aspoň 10 znaků, odkaz se
jménem v hlavičce); změna ukončí jeho ostatní relace.

Hesla jsou jen jako hash se solí (`werkzeug.security`, scrypt)
v `.work/hesla.json`, který píše jen aplikace; tajný klíč relací je
v `.work/relace.key`. Všechny tři soubory mají práva jen pro
vlastníka (`uzivatele.json` nastaví správce). Odpověď na chybné
přihlášení neprozradí, zda login existuje; po 5 chybných pokusech na
login server další pokusy zdržuje.

Jen **admin** smí měnit Nastavení (Immich včetně synchronizace na
požádání, kontakt pro Nominatim). **Admin a archivář** smějí stránku
Přetřídit s importem ze složky `přetřídit` a vynuceně uvolnit zámek
akce. Ostatním server vrátí 403 a klient tyto prvky nezobrazí.

**Úprava akce** (zámek, uložení, dokončení, úklid, import do ní): admin
a archivář každou akci, běžný uživatel jen akci, v jejímž `upravili`
je jeho jméno (porovnání jako u jmen) — v praxi tu, kterou sám
naimportoval nebo upravoval. Akci bez `_metadata.json` nebo bez
`upravili` upravují jen admin a archivář. Prohlížet smí každý všechno.
Bez oprávnění server zámek odmítne (403) a klient akci otevře jen ke
čtení s vysvětlením; seznam ji označí „jen ke čtení“ a průvodce
importem ji nenabídne jako cíl. Bez přihlášení smí každý všechno.

Bez `--https` jde heslo i cookie nešifrovaně; v nasazení používejte
HTTPS (reverzní proxy). Přihlašovací stránka na HTTP upozorní. Cookie
je `HttpOnly` a `SameSite=Lax`; `Secure` zapne `--https`.

Na Windows místo `.venv/bin/` použít `.venv\Scripts\`.
