// Umístění seznamu návrhů jmen mimo ořezující okna (nástroj pojmenování,
// panel editoru). Seznam se otevírá v horní vrstvě přes Popover API, takže
// ho neořízne `overflow: auto` dialogu ani panelu a leží i nad modálním
// dialogem. Bez Popover API zůstává dnešní chování (přepínání `hidden`);
// poloha se počítá vždy, fallback jen postrádá horní vrstvu.
//
// Souřadnice jsou vůči layout viewportu (`getBoundingClientRect`);
// viditelná část okna se bere z `visualViewport` (offsetTop, height),
// tedy bez klávesnice telefonu.

// Čistá funkce bez DOM: kam položit seznam výšky `vyska` vzhledem k poli
// `pole` = { left, top, bottom, width } a viditelné části okna
// `okno` = { top, height }. Vrací vždy { left, width, top, maxHeight,
// smer: "dolu" | "nahoru" }; `top` je px od horní hrany layout viewportu.
// Dolů, když se seznam vejde; jinak nahoru, je-li nahoře víc místa;
// jinak na větší stranu s `maxHeight` a posuvníkem uvnitř seznamu.
export function umisteni({ pole, okno, vyska }) {
  const dole = (okno.top + okno.height) - pole.bottom;
  const nahore = pole.top - okno.top;
  const vysledky = {
    dolu: { left: pole.left, width: pole.width, top: pole.bottom },
    nahoru: {
      left: pole.left, width: pole.width,
      top: pole.top - Math.min(vyska, Math.max(nahore, 0)),
    },
  };
  let smer;
  let misto;
  if (vyska <= dole) {
    smer = "dolu";
    misto = dole;
  } else if (nahore > dole) {
    smer = "nahoru";
    misto = nahore;
  } else {
    smer = "dolu";
    misto = dole;
  }
  return { ...vysledky[smer], maxHeight: Math.max(0, misto), smer };
}

// Napojení na DOM: `input` je pole jmen, `list` seznam návrhů (`ul.suggest`).
// Vrací { ukaz(), skryj() }. `ukaz()` se smí volat opakovaně (po naplnění
// nebo změně položek) — pokaždé přepočítá polohu. Rozepsaný text v poli
// se nikdy nemaže.
export function pripojNaseptavani(input, list) {
  const popover = typeof list.showPopover === "function";
  if (popover) list.popover = "manual";
  let pripojeno = false;

  function viditelneOkno() {
    const vv = window.visualViewport;
    return vv ? { top: vv.offsetTop, height: vv.height }
      : { top: 0, height: window.innerHeight };
  }

  // Změří přirozenou výšku seznamu (se zrušeným maxHeight) a položí ho.
  function umisti() {
    const predchozi = list.style.maxHeight;
    list.style.maxHeight = "none";
    const vyska = list.offsetHeight || list.scrollHeight;
    list.style.maxHeight = predchozi;
    const v = umisteni({ pole: input.getBoundingClientRect(),
      okno: viditelneOkno(), vyska });
    list.style.left = `${v.left}px`;
    list.style.top = `${v.top}px`;
    list.style.width = `${v.width}px`;
    list.style.maxHeight = `${v.maxHeight}px`;
  }

  // Posun uvnitř seznamu ho nechává otevřený; cokoliv jiného ho zavře.
  function naScroll(e) {
    const cyl = e.target;
    const uvnitr = cyl === list
      || (cyl instanceof Node && list.contains(cyl));
    if (!uvnitr) skryj();
  }

  function pripojPoslouchace() {
    if (pripojeno) return;
    pripojeno = true;
    document.addEventListener("scroll", naScroll, true);
    window.addEventListener("resize", umisti);
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", umisti);
      window.visualViewport.addEventListener("scroll", umisti);
    }
  }

  function odpojPoslouchace() {
    if (!pripojeno) return;
    pripojeno = false;
    document.removeEventListener("scroll", naScroll, true);
    window.removeEventListener("resize", umisti);
    if (window.visualViewport) {
      window.visualViewport.removeEventListener("resize", umisti);
      window.visualViewport.removeEventListener("scroll", umisti);
    }
  }

  function otevreny() {
    return list.matches(":popover-open");
  }

  function ukaz() {
    list.hidden = false;
    if (popover && !otevreny()) list.showPopover();
    umisti();
    pripojPoslouchace();
  }

  function skryj() {
    odpojPoslouchace();
    if (popover && otevreny()) list.hidePopover();
    list.hidden = true;
  }

  return { ukaz, skryj };
}
