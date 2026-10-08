## ADDED Requirements

### Requirement: Verze aplikace v hlavičce
Hlavička stránky SHALL ukazovat verzi běžící aplikace vedle názvu
aplikace. Verze SHALL být ta, se kterou byl server spuštěn: v pracovní
kopii gitu popis podle posledního tagu (tag, počet commitů po něm,
hash a příznak neuložených změn), v Docker image popis zapsaný při
buildu. Když verzi nejde zjistit, hlavička SHALL ukázat „verze
neznámá“. Zobrazení verze MUST NOT měnit výšku hlavičky.

#### Scenario: Pracovní kopie po vydání
- **WHEN** server běží z pracovní kopie jeden commit za tagem `v0.2.0`
- **THEN** hlavička ukazuje verzi `v0.2.0-1-g5609826`

#### Scenario: Neuložené změny
- **WHEN** pracovní kopie má neuložené změny
- **THEN** verze končí `-dirty`

#### Scenario: Docker image
- **WHEN** server běží v image postaveném z commitu s tagem `v0.3.0`
- **THEN** hlavička ukazuje verzi `v0.3.0`, přestože image neobsahuje
  `.git`

#### Scenario: Verze se po startu nemění
- **WHEN** se po startu serveru v pracovní kopii udělá `git pull`
- **THEN** hlavička dál ukazuje verzi, se kterou server startoval

#### Scenario: Neznámá verze
- **WHEN** server neběží z gitu ani nemá verzi z buildu
- **THEN** hlavička ukazuje „verze neznámá“
