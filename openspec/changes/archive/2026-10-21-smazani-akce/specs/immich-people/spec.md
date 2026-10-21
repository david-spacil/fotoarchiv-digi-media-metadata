## MODIFIED Requirements

### Requirement: Album akce
Dokončení akce SHALL po zveřejnění složky spustit na pozadí sken
knihovny vybrané v nastavení a hned odpovědět. Na Immich MUST NOT
čekat a chyba Immiche MUST NOT dokončení zabránit. Jakmile Immich zná
soubory akce, SHALL aplikace v Immichi založit album pojmenované jako
akce. Pravidelná synchronizace SHALL album každé dokončené akce, jejíž
fotky Immich zná, udržovat: chybějící assety doplnit a assety, které
už k akci nepatří, odebrat. Album SHALL obsahovat assety spárované se
soubory v kořeni akce (viz Párování souborů) kromě označených
k vyřazení. Assety MUST NOT mazat. Album samotné MUST NOT mazat,
s jedinou výjimkou: při trvalém smazání akce z koše (viz `event-trash`)
SHALL aplikace album akce v Immichi smazat; assety ani tehdy nemaže. Vazba akce na
album SHALL být v pracovním adresáři. Nedokončená akce album MUST NOT
dostat. Ve vývojovém režimu SHALL dokončení sken vynechat a album
založit jen tehdy, když Immich fotky akce už zná.

#### Scenario: Dokončení akce
- **WHEN** archivář dokončí akci `2026-09-08 Konference Příkladné metody` a
  Immich její složku po spuštěném skenu načte
- **THEN** Immich má album `2026-09-08 Konference Příkladné metody`
  se všemi jejími fotkami, aniž by se čekalo na pravidelnou
  synchronizaci

#### Scenario: Dokončení nečeká na Immich
- **WHEN** archivář dokončí akci a Immich je nedostupný
- **THEN** dokončení proběhne jako dosud a album založí pozdější
  synchronizace

#### Scenario: Immich fotky ještě nezná
- **WHEN** akce je dokončená, ale Immich ještě žádný její asset nemá
- **THEN** album se nezaloží a synchronizace to zkusí při dalším běhu

#### Scenario: Restart serveru během čekání
- **WHEN** server se po dokončení akce restartuje dřív, než Immich
  fotky načte
- **THEN** album založí nejbližší pravidelná synchronizace, která fotky
  najde

#### Scenario: Album smazané v Immichi
- **WHEN** uložené album v Immichi už neexistuje
- **THEN** synchronizace založí nové a uloží jeho vazbu

#### Scenario: Klíč bez oprávnění k albům
- **WHEN** klíč nemá oprávnění zakládat alba
- **THEN** synchronizace obličeje zapíše jako dosud a stránka nastavení
  ukáže, že alba nejde vést

#### Scenario: Vývojový režim
- **WHEN** akce se dokončí ve vývojovém režimu
- **THEN** sken se nespustí, a pokud Immich fotky akce zná, album se
  založí

#### Scenario: Akce vysypaná z koše
- **WHEN** vysypání koše trvale smaže akci
  `2026-09-08 Konference Příkladné metody`, která má v Immichi album
- **THEN** album v Immichi neexistuje a vazba akce na album
  v pracovním adresáři je odstraněná

#### Scenario: Akce v koši
- **WHEN** dokončená akce leží v koši a proběhne synchronizace
- **THEN** synchronizace její album nemění ani nemaže
