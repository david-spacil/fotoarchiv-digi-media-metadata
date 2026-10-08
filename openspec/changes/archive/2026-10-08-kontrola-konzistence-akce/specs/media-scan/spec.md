## MODIFIED Requirements

### Requirement: Zpracovávané soubory
Sken SHALL zahrnout fotky a videa v kořeni akce (JPG, JPEG, PNG, MP4,
MOV bez ohledu na velikost písmen). `Thumbs.db`, RAWy, archivy a další
soubory MUST být vynechány; RAWy a další soubory (kromě `Thumbs.db`)
SHALL aplikace uvést mezi nálezy kontroly akce (viz
`event-consistency`).

#### Scenario: Zip v kořeni
- **WHEN** kořen akce obsahuje `prezentace.zip`
- **THEN** soubor není v mřížce a kontrola akce ho uvede jako
  nepodporovaný
