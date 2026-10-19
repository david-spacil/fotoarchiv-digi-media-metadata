[← Dokumentace](../README.md)

# Průvodce akcí

**Při prvním otevření akce bez `_metadata.json` průvodce:** úklid
(podsložky, RAW; potvrzení načte soubory kořene) → údaje akce
(předvyplněné z názvu složky a dat fotek) → skupiny a autoři.
Průvodce provede vším povinným; údaje jednotlivých souborů se
doplňují na ploše. Krok skupiny a autoři ukáže mřížku náhledů po
skupinách s úpravou skupin (přejmenovat, sloučit, nová skupina
z výběru, přesun) a u každé skupiny pole autorů; nad skupinami
jdou zadat i autoři celé akce: skupiny bez vlastních autorů je
zdědí (fotila-li celou akci stejná parta, stačí je zadat jednou).
Mřížku kroku ovládá klávesnice jako na ploše a Esc v ní zruší
výběr souborů i skupiny; Delete, Enter a P tam nic nedělají —
krok nemá lupu ani označování k vyřazení.
Existuje-li k akci návrh skupin z importu, krok použije jeho
skupiny (i s autory) a přiřazení pro soubory v kořeni, které návrh
uvádí, a autory celé akce z návrhu; ostatní soubory dostanou
automatický návrh. Prvním uložením `_metadata.json` se návrh smaže.
Akce založená importem `_metadata.json` má, průvodce ji přeskočí.
