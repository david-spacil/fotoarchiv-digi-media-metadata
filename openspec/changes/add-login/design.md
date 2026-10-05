## Context

Server po `write-to-archive`: jeden proces na Debianu ve firemní síti,
zámek v paměti, jméno uživatele z prohlížeče. Firemní infrastruktura
přihlašování (AD/LDAP, SSO, reverzní proxy) zatím nezmapovaná.

## Goals / Non-Goals

**Goals:**
- Žádná správa hesel v aplikaci, pokud firma má adresářovou službu.
- Aplikace se o přihlášení stará co nejméně (jedna vstupní kontrola).

**Non-Goals:**
- Role a oprávnění po akcích (všichni přihlášení smějí totéž).
- Přístup mimo firemní síť.

## Decisions

**K rozhodnutí** — nejdřív zjistit, čím firma přihlašuje dnes:

- **A – reverzní proxy s SSO** (Authentik, Authelia, Keycloak,
  oauth2-proxy před aplikací): aplikace jen čte hlavičku
  s uživatelem od proxy a server poslouchá jen na localhostu. Nejméně
  kódu, pokud proxy/IdP už existuje; jinak nová služba k provozu.
- **B – LDAP/AD bind v aplikaci**: přihlašovací formulář, ověření
  firemním účtem, session cookie. Bez nové služby, ale hesla prochází
  aplikací (nutné HTTPS) a přibude závislost `ldap3`.
- **C – lokální účty** v souboru na serveru (hash hesel): bez závislosti
  na firemní infrastruktuře, ale další hesla ke správě. Jen pokud A ani
  B nejdou.

Ve všech variantách: převod identity na `Příjmení, Jméno` mapou
v konfiguraci serveru (login → kanonické jméno), u A/B případně
z atributů adresáře.

## Risks / Trade-offs

- [HTTP ve firemní síti] → hesla (B, C) jen přes HTTPS; certifikát
  řeší nasazení.
- [Hlavička od proxy jde podvrhnout, pokud je aplikace dostupná
  napřímo] → u A poslouchat jen na localhostu / unix socketu.

## Open Questions

- Jaký adresář nebo SSO firma používá a jestli na serveru běží reverzní
  proxy — rozhoduje mezi A, B a C; úlohy (tasks.md) se napíšou až po
  rozhodnutí.
