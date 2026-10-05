## Why

Sdílený server je dostupný z celé firemní sítě a zapisuje do archivu
(`write-to-archive`). Bez přihlášení může archiv měnit kdokoli v síti
a jméno u zámku si každý zadá sám.

## What Changes

- Přístup k aplikaci (stránky i API) jen po přihlášení.
- Identita přihlášeného uživatele nahradí jméno zadané v prohlížeči
  u zámku akce.
- Přiřazení identity ke kanonickému jménu `Příjmení, Jméno` (kvůli
  návrhům jmen a zobrazení držitele zámku).
- Ve vývojovém režimu jde přihlášení vypnout.

Plánovací změna: způsob přihlášení se vybere v design.md, úlohy vzniknou
až po výběru.

## Capabilities

### New Capabilities
- `user-login`: povinné přihlášení, identita uživatele, odhlášení.

### Modified Capabilities
- (žádné; požadavek „Jméno uživatele“ z `event-lock` se upraví po
  archivaci `write-to-archive`)

## Impact

- `fotoarchiv/app.py` (ochrana všech cest), klient (odhlášení, zobrazení
  uživatele), nasazení serveru (podle zvolené varianty reverzní proxy
  nebo napojení na adresářovou službu).
- Závisí na `write-to-archive`.
