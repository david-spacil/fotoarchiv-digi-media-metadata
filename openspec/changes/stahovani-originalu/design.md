## Context

Motivace viz proposal.md, požadavky viz `specs/event-download`.
Originál jednoho média už vydává `GET /api/akce/<nazev>/soubor/<soubor>`
(`send_file` s Range pro lupu); `root_file` pustí jen soubor z kořene
složky akce (`Workspace.event_dir`, i s příponou `.ignored`). Sidecar
souboru umí `xmp.sidecar(doc, akce, soubor)` vrátit jako text bez
zápisu. Server je jeden proces cheroot s 32 vlákny; přihlášení hlídá
`before_request`. Akce mívají stovky fotek a gigabajty videa.

## Goals / Non-Goals

**Goals:**
- ZIP libovolné velikosti bez dočasného souboru a bez načtení celého
  obsahu do paměti serveru i prohlížeče.
- Metadata v ZIPu vždy konzistentní s přibaleným `_metadata.json`.

**Non-Goals:**
- Průběh v procentech (`Content-Length` ZIPu).
- RAWy a jiné podsložky, ZIP víc akcí najednou.
- Mobilní ovládání (změna `mobilni-verze`).
- Oblasti obličejů v sidecarech (jen pro obnovu Immiche, příkaz
  `exportovat --obliceje`).

## Decisions

### Streamovaný ZIP bez komprese
`zipfile.ZipFile` zapisuje do proudu, který nejde převíjet (velikosti
v datových deskriptorech, zip64 pro soubory a archivy nad 4 GiB).
Odpověď je generátor: soubor po souboru se čte po blocích a odesílá.
Komprese `ZIP_STORED` — JPEG, PNG i MP4 jsou už komprimované, deflate
by jen zatížil CPU. Velikost ZIPu předem není známá, takže chybí
`Content-Length`.
*Alternativa:* sestavit ZIP do `.work` a poslat `send_file` — dvojnásobné
čtení, místo na disku a úklid. *Alternativa:* spočítat přesnou délku
ZIP_STORED předem — jde, ale vlastní zápis hlaviček ZIPu za procenta
v prohlížeči nestojí.

### Sidecary generované v paměti
Sidecar se pro každé médium se záznamem v `_metadata.json` vytvoří
`xmp.sidecar()` z dokumentu načteného jednou na začátku požadavku;
do ZIPu jde i přesně tato verze JSONu. Sidecary na disku (vedle
originálu nebo ve `.work/xmp/`) se nečtou: mohou chybět nebo být
zastaralé a ve vývojovém režimu leží jinde. Invariant „sidecary jsou
jen generovaný výstup JSONu“ tím platí i pro ZIP.
*Alternativa:* přibalit sidecary z disku — u rozpracované akce nejsou
a po změně neodpovídají JSONu.

### Ploché uspořádání ZIPu
Média, `<soubor>.xmp` a `_metadata.json` v kořeni ZIPu, tedy stejně
jako ve složce akce v archivu. Rozbalení do složky podle názvu ZIPu
dělají běžné nástroje samy.

### Výběr přes POST formuláře, celá akce přes GET
`GET /api/akce/<nazev>/zip` — celá akce, jde jako obyčejný odkaz
s atributem `download` na kartě. `POST /api/akce/<nazev>/zip` se seznamem
`soubory` z neviditelného `<form>`: stahování řídí prohlížeč (ne `fetch`,
který by ZIP držel v paměti), seznam stovek názvů se nevejde do URL.
Jeden vybraný soubor jde přes stávající endpoint originálu
s `?stahnout=1` (`Content-Disposition: attachment`); bez parametru
zůstává inline pro lupu.

### Kontrola výběru před prvním bajtem
Všechny názvy výběru se ověří (`root_file`, médium) předem; chyba →
404 a žádný ZIP. Po odeslání hlaviček už stav vrátit nejde, proto
soubor, který mezitím zmizel (souběžný úklid jinou relací), se jen
přeskočí. U celé akce se seznam médií bere z výpisu kořene (stejně
jako `scan`), označení k vyřazení z načteného `_metadata.json`; názvy
na disku a v JSONu se párují po NFC jako v `xmp.targets`.

### Název souboru
`Content-Disposition: attachment` s `filename*=UTF-8''…` (a ASCII
`filename` jako záloha), název akce bez přípony `.ignored`. Výběr:
`<akce> (N souborů).zip` se skloňováním jako jinde v aplikaci.

### Klient
Ikona `stahnout` v `icons.js` (obrys mráčku a šipka dolů v mřížce
24 × 24). Na kartě akce odkaz s ikonou, `aria-label` a `title`;
klik nesmí otevřít plochu. Na ploše tlačítko „Stáhnout (N)“ mezi
nástroji výběru, dostupné i v režimu jen pro čtení.

## Risks / Trade-offs

- [Dlouhé stahování drží vlákno cheroot] → 32 vláken stačí na několik
  souběžných stažení; při potížích zvýšit `--vlakna`. Přerušené
  spojení generátor ukončí (`call_on_close`).
- [Bez `Content-Length` prohlížeč neukáže procenta] → přijato; ukazuje
  stažené MB.
- [Soubor zmizí uprostřed ZIPu] → přeskočí se; ZIP zůstane platný,
  jen bez něj.
- [Čtení originálu ze SMB je pomalé] → stejné jako u náhledů; ZIP
  nečte nic navíc kromě médií a JSONu.
- [POST z cizího webu přes formulář] → cookie relace má
  `SameSite=Lax`, takže ji cizí POST nepošle a `before_request`
  požadavek odmítne; endpoint navíc nic nezapisuje.
