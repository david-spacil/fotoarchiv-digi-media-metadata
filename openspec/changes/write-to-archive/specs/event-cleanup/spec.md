## ADDED Requirements

### Requirement: Provedení úklidu
V produkčním režimu SHALL průvodce po potvrzení plán úklidu provést.
Server MUST plán sestavit znovu z voleb uživatele těsně před provedením
a provést jen neblokované operace; blokované přeskočí. Přesun ani
přejmenování MUST NOT přepsat existující soubor nebo složku. Smazat se
smí jen podsložka, ve které po přesunech zbyl nejvýš `Thumbs.db`.
Ve vývojovém režimu SHALL průvodce plán jen zobrazit.

#### Scenario: Přesun podsložky do kořene
- **WHEN** uživatel zvolí přesunout podsložku `Video` s 22 soubory bez
  kolizí a plán potvrdí
- **THEN** 22 souborů je v kořeni akce a složka `Video` je smazaná

#### Scenario: Ponechání podsložky
- **WHEN** uživatel ponechá podsložku `RAWy` a plán potvrdí
- **THEN** složka se jmenuje `RAW.ignored`

#### Scenario: Kolize při provedení
- **WHEN** mezi zobrazením a potvrzením plánu vznikne v kořeni soubor
  stejného jména jako přesouvaný
- **THEN** přesun se neprovede, soubor zůstane v podsložce a podsložka
  se nesmaže

### Requirement: Výsledek úklidu
Po provedení SHALL průvodce ukázat, které operace proběhly, které byly
blokované a které selhaly (s chybou). Selhání jedné operace MUST NOT
zastavit ostatní nezávislé operace. Další krok průvodce SHALL pracovat
se soubory, které jsou v kořeni po úklidu.

#### Scenario: Chyba oprávnění
- **WHEN** přesun jednoho souboru selže na oprávnění
- **THEN** výsledek ho ukáže jako selhaný s chybou, ostatní přesuny
  proběhnou a podsložka se nesmaže

## REMOVED Requirements

### Requirement: Úklid nasucho
**Reason**: Úklid se v produkčním režimu provádí.
**Migration**: Zobrazení bez provedení zůstává ve vývojovém režimu, viz
„Provedení úklidu“.
