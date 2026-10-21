// Nástroj pojmenování osob: překryv nad plochou akce (změna
// pojmenovani-osob). Výpočet výřezu a logika pořadí kroků kola jsou
// čisté funkce s testy v tests/js/naming.test.mjs; překryv a volání
// API žijí zde, aby `app.js` nerostl. Schválený vzhled = varianta A
// „Karta“: 3 výřezy vedle sebe nahoře, metadata pod každým, ovládání
// (pole jména, Uložit, Odložit, Skrýt, počítadlo) dole; stejné rozložení
// i na mobilu. Výřez se kreslí z proxované zmenšeniny na canvas.

import { icon } from "./icons.js";
import { pripojNaseptavani } from "./naseptavani.js";

// --- čisté funkce ----------------------------------------------------------

// Okraj čtvercového výřezu kolem obličeje (násobek větší strany
// obdélníku). `obdelnik` je {x1, y1, x2, y2} z Immiche — platí k
// zmenšenině `sirka` × `vyska` ze stejného údaje.
export const OKRAJ = 1.45;

// Obdélník obličeje + rozměr zmenšeniny → parametry vykreslení
// výřezu `{sx, sy, sw, sh, dw, dh}` pro `drawImage` (čtverec s
// okrajem, ořezaný do okrajů zmenšeniny). Neplatné, obrácené ani
// nulové obdélníky a rozměry oznámí null.
export function vyrez(obdelnik, sirka, vyska, cilova = 256) {
  if (!(sirka > 0) || !(vyska > 0) || !(cilova > 0)) return null;
  const o = obdelnik || {};
  if (![o.x1, o.y1, o.x2, o.y2].every((v) => Number.isFinite(v))) return null;
  const clam = (v, max) => Math.min(Math.max(v, 0), max);
  const x1 = clam(o.x1, sirka), x2 = clam(o.x2, sirka);
  const y1 = clam(o.y1, vyska), y2 = clam(o.y2, vyska);
  const w = x2 - x1, h = y2 - y1;
  if (w <= 0 || h <= 0) return null;
  const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
  const side = Math.min(Math.max(w, h) * OKRAJ, sirka, vyska);
  return {
    sx: Math.min(Math.max(cx - side / 2, 0), sirka - side),
    sy: Math.min(Math.max(cy - side / 2, 0), vyska - side),
    sw: side, sh: side, dw: cilova, dh: cilova,
  };
}

// Pořadí osob: podle počtu obličejů sestupně, při shodě podle id
// (stejné deterministické pravidlo jako server `naming.py`).
export function poradiOsob(osoby) {
  return [...(osoby || [])].sort((a, b) => (b.pocet || 0) - (a.pocet || 0)
    || String(a.id).localeCompare(String(b.id)));
}

// Další krok kola: `fronta` jsou dosud nenabídnuté osoby (bez
// odložených — ty vyřadí server i klient), `odlozene` je počet
// odložených v aktuálním kole. Neprázdná fronta →Offer další osoba;
// prázdná → konec kola, s odloženými nabídne „projít znovu“.
export function prechod(fronta, odlozene) {
  if (fronta && fronta.length) return { krok: "osoba", osoba: fronta[0] };
  const o = odlozene || 0;
  return { krok: "konec", odlozene: o, nabizi: o > 0 };
}

// Vyřízení osoby (po pojmenovat / sloučit / skryt / nevim) → nová
// fronta bez ní. Žádná akce sama o sobě frontu neposouvá víc.
export function vyrid(fronta, id) {
  return fronta.filter((o) => o.id !== id);
}

// Vrácení posledního kroku (Zpět) → nová fronta s osobou zpět na
// začátku, na jak ji uživatel viděl naposledy. Bez duplicity: je-li
// osoba ve fronty už (jmenem i objektem pracuje jako `vyrid`), patří
// jen na začátek. Původní frontu nemění.
export function vratit(fronta, os) {
  return [os, ...fronta.filter((o) => o.id !== os.id)];
}

// Klávesová zkratka volby z události `keydown` → "odlozit" | "skryt" |
// "zpet" | null. Platí i s kurzorem v poli jména, proto jen klávesy bez
// významu pro editaci jednořádkového pole ani pro prohlížeč: PageDown
// (bez modifikátorů) a Alt+Delete (Ctrl+Delete maže slovo, Shift+Delete
// na Windows vyjímá). Alt+Backspace vrátí poslední krok — v poli by na
// Windows jinak vrátil psaní, listener proto volá `preventDefault`
// vždy, i když žádný krok vrátit nejde. Podržená klávesa (`repeat`)
// se nepočítá.
export function zkratka(e) {
  if (e.repeat) return null;
  const mod = e.ctrlKey || e.metaKey || e.shiftKey;
  if (e.key === "PageDown" && !mod && !e.altKey) return "odlozit";
  if (e.key === "Delete" && e.altKey && !mod) return "skryt";
  if (e.key === "Backspace" && e.altKey && !mod) return "zpet";
  return null;
}

// Posun zvýraznění v našeptávání šipkou: z žádného výběru (-1) šipka
// dolů vybere první a nahoru poslední položku, na konci se přetáčí.
export function posunVyberu(aktivni, pocet, dolu) {
  if (!(aktivni >= 0 && aktivni < pocet)) return dolu ? 0 : pocet - 1;
  return (aktivni + (dolu ? 1 : -1) + pocet) % pocet;
}

// Co v poli jména udělá Enter: vybraný návrh z našeptávání se převezme
// a uloží („navrh“), jinak nabídnuté sloučení se potvrdí („sloucit“),
// jinak se jméno uloží („ulozit“).
export function volbaEnteru({ vybranyNavrh = false, slouceni = null } = {}) {
  if (vybranyNavrh) return "navrh";
  return slouceni ? "sloucit" : "ulozit";
}

// Počítadlo „Osoba N z M“: `vyslo` = kolik osob uživatel v tomhle
// sezení už vyřídil, `zbava` = kolik jich zbývá ve frontě.
export function pocetadlo(vyslo, zbava) {
  return `Osoba ${vyslo + 1} z ${vyslo + zbava}`;
}

// --- překryv ---------------------------------------------------------------

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null) continue;
    if (k === "dataset") { Object.assign(el.dataset, v); continue; }
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k in el && (typeof v !== "string" || k === "value")) el[k] = v;
    else if (v === false) continue;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

function plural(n, one, few, many) {
  return `${n} ${n === 1 ? one : n >= 2 && n <= 4 ? few : many}`;
}

function prid(el, ...children) {
  // `el.append(null)` by vložil text „null“ – filtrujeme podmíněné dílky
  el.append(...children.flat().filter((c) => c !== null
    && c !== undefined && c !== false));
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function api(url, opts = {}) {
  const r = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    const err = new Error(`HTTP ${r.status}`);
    err.status = r.status;
    err.data = data;
    throw err;
  }
  return data;
}

function textChyby(err) {
  const c = err?.data?.chyba;
  if (c === "jen_archivar") return "Na nástroj nemáte oprávnění.";
  if (c === "immich_nenastaven") return "Immich není nastaven.";
  if (c === "bez_alba") return "Akce nemá v Immichi album.";
  if (typeof c === "string" && c) return c;
  return err?.message || "Neznámá chyba.";
}

// Uložit-li klient nekanonický tvar, server vrátí 400 `kanonicky_tvar`
// s `navrh`; ten klient pošle potvrzený.
function jeKanon(name) {
  return name.includes(",");
}

/**
 * Otevře překryv nástroje nad aktuální plochou akce.
 *
 * `deps.nazev` je název akce, `deps.naZavreni(vysledek)` se volá po
 * zavření (POST `hotovo`); `vysledek.synchronizace` značí, že server
 * po změně spustil synchronizaci. Zavření kolo neukončí — odložené
 * osoby zůstávají na serveru.
 */
export function showNaming(deps) {
  const { nazev, naZavreni } = deps;
  const url = (rest) => `/api/akce/${encodeURIComponent(nazev)}${rest}`;

  const s = {
    stav: null, uplne: true,
    fronta: [],           // dosud nenabídnuté osoby této chvíle
    odlozene: 0,          // odložené v kole (ze serveru + „odložit“ navíc)
    zapisuje: false,      // běží zápis volby (další se neodešle)
    vyslo: 0,             // vyřízeno v tomhle sezení (pro počítadlo)
    os: null,             // aktuální osoba
    prevedeno: false,     // návrh kanonického tvaru už byl nabídnut
    navrh: "",            // kanonický tvar, který uživatel potvrdí
    chyba: "",            // chyba Immiche (osoba zůstává s jménem)
    zprava: "",           // měkké hlášení pod polem
    slouceni: null,       // {id, jmeno} po 409 (nabídka sloučení)
    posledni: null,       // {typ, os, jmeno} poslední vratitelný krok (Zpět)
    osoby: null,           // poslední [pojmenované, celkem] z odpovědi
    zmena: false,         // zapisovalo se (poznámka ke synchronizaci)
    nacitani: true,
    chybaNacteni: "",
  };

  const nahledAsset = (v) =>
    url(`/osoby/nahled/${encodeURIComponent(v.asset)}`);
  const OBR = new Map();  // URL zmenšeniny → napoprvé napočatý Image

  function imgAsset(src) {
    if (!OBR.has(src)) {
      OBR.set(src, new Promise((res, rej) => {
        const i = new Image();
        i.onload = () => res(i);
        i.onerror = () => rej(new Error("Zmenšeninu nešlo načíst."));
        i.src = src;
      }));
      OBR.get(src).catch(() => {});
    }
    return OBR.get(src);
  }

  // --- vykreslení výřezů --------------------------------------------------

  function cropBox(v) {
    const cv = h("canvas", { class: "vyrez-cv", role: "img",
      "aria-label": `Výřez obličeje z ${v.immich?.soubor || "fotky"}` });
    cv.dataset.v = JSON.stringify(v);
    return h("div", { class: "vyrez-box" }, cv);
  }

  function rozmerVyreze(root) {
    for (const cv of root.querySelectorAll("canvas.vyrez-cv")) {
      const v = JSON.parse(cv.dataset.v);
      const css = cv.clientWidth || 120;
      const dpst = Math.min(2, window.devicePixelRatio || 1);
      const px = Math.max(16, Math.round(css * dpst));
      const q = vyrez(v, v.sirka, v.vyska, px);
      if (cv.width !== px) { cv.width = px; cv.height = px; }
      const ctx = cv.getContext("2d");
      ctx.clearRect(0, 0, px, px);
      if (!q) continue;
      imgAsset(nahledAsset(v)).then((img) => {
        // obdélník platí ke zmenšenině `sirka`×`vyska`; škálujeme,
        // kdyby prohlížeč dostal jiné rozlišení
        const k = Math.min(img.naturalWidth / v.sirka,
          img.naturalHeight / v.vyska) || 1;
        ctx.drawImage(img, q.sx * k, q.sy * k, q.sw * k, q.sh * k,
          0, 0, px, px);
      }).catch(() => {});
    }
  }

  // --- dílky ---------------------------------------------------------------

  // Immich vrací čas v UTC (`…Z`) → místní čas; datum z archivu je
  // místní, jen bez `T` a sekund.
  function datumText(value) {
    if (!value) return value;
    const s = String(value);
    if (/Z$|[+-]\d\d:\d\d$/.test(s)) {
      const d = new Date(s);
      if (!isNaN(d)) {
        return d.toLocaleString("cs-CZ", { dateStyle: "short",
          timeStyle: "short" });
      }
    }
    return s.replace("T", " ").replace(/:\d\d(\.\d+)?$/, "");
  }

  function metaList(v) {
    const ul = h("ul");
    const li = (ikona, label, hodnota, trida) => {
      if (hodnota === null || hodnota === undefined || hodnota === "") return;
      ul.append(h("li", { class: trida }, icon(ikona),
        h("b", {}, label), h("span", {}, String(hodnota))));
    };
    // Název souboru je v popisku výřezu; tady datum pořízení z Immiche
    // a údaje z archivu po zdědění.
    li("datum", "pořízeno", datumText(v.immich?.datum), "imm");
    if (v.archiv) {
      li("skupina", "skupina", v.archiv.skupina, "in");
      li("datum", "datum", datumText(v.archiv.datum), "in");
      li("misto", "místo", v.archiv.misto, "in");
      li("osoba", "autoři", v.archiv.autori, "in");
    }
    return ul;
  }

  function figureFor(v) {
    const fig = h("figure", { class: "vyrez" }, cropBox(v),
      h("figcaption", {}, h("span", { class: "soub" }, v.immich?.soubor || ""),
        v.archiv ? null
          : h("span", { class: "bez-archivu" },
            "bez archivního páru — jen Immich")),
      h("div", { class: "mdet" }, metaList(v)));
    return fig;
  }

  function badge(text, cls) {
    return h("span", { class: `badge${cls ? ` ${cls}` : ""}` }, text);
  }

  // --- jméno: našeptávání a uložení ---------------------------------------

  let input, suggest, nasept, zpetna, panelSlouceni, dialog, tlUlozit,
    tlSloucit, tlZpet;

  function jmenovePole() {
    input = h("input", { type: "text", id: "pojm-jmeno",
      autocomplete: "off", placeholder: "Příjmení, Jméno",
      "aria-label": "Jméno osoby",
      oninput: () => {
        s.prevedeno = false;
        s.navrh = "";
        s.zprava = "";
        if (s.chyba) s.chyba = "";
        skrytNavesty();
        zrusSlouceni();
        naseptavani(input.value);
      },
      onkeydown: (e) => {
        const items = [...suggest.children];
        if ((e.key === "ArrowDown" || e.key === "ArrowUp")
            && !suggest.hidden && items.length) {
          e.preventDefault();
          const act = posunVyberu(Number(suggest.dataset.active ?? -1),
            items.length, e.key === "ArrowDown");
          suggest.dataset.active = String(act);
          items.forEach((li, i) => li.classList.toggle("active", i === act));
          return;
        }
        if (e.key === "Enter") {
          e.preventDefault();
          const vybrany = !suggest.hidden
            && items[Number(suggest.dataset.active)];
          const volba = volbaEnteru({ vybranyNavrh: !!vybrany,
            slouceni: s.slouceni });
          if (volba === "navrh") {
            input.value = vybrany.textContent;
            skrytNavesty();
            zrusSlouceni();
          }
          if (volba === "sloucit") sloucit();
          else pokusUlozit();
        }
      } });
    if (s.os && s.priorJmeno) input.value = s.priorJmeno;
    suggest = h("ul", { class: "suggest", hidden: true });
    // Nová osoba = nové pole i seznam: odpošlouchá starý seznam a ten
    // svůj napojí na modul strkající návrhy do horní vrstvy.
    nasept?.skryj();
    nasept = pripojNaseptavani(input, suggest);
    zpetna = h("div", { class: "zpetna-vazba" });
    panelSlouceni = h("div", { class: "panel-slouceni" });
    return h("div", { class: "field" },
      h("label", { for: "pojm-jmeno" }, "Jméno osoby"),
      h("div", { class: "names" }, input, suggest),
      zpetna,
      h("div", { class: "hint" }, "Jméno dostane tato osoba na všech " +
        "fotkách v Immichi, nejen na fotkách této akce."),
      panelSlouceni);
  }

  function skrytNavesty() {
    if (!suggest) return;
    nasept.skryj();
    suggest.replaceChildren();
    delete suggest.dataset.active;
  }

  // Návrh sloučení ruší jen úprava jména — pozdní odpověď
  // našeptávání nesmí panel smazat (až by dorazil po 409).
  function zrusSlouceni() {
    if (panelSlouceni) panelSlouceni.replaceChildren();
    s.slouceni = null;
    tlSloucit = null;
    oznacEnter();
  }

  function sloucit() {
    if (s.slouceni) zapis({ akce: "sloucit", cil: s.slouceni.id });
  }

  // Ikonka Enteru u tlačítka, které Enter v poli jména stiskne:
  // „Sloučit“, je-li sloučení nabídnuté, jinak „Uložit“.
  function oznacEnter() {
    const cil = volbaEnteru({ slouceni: s.slouceni }) === "sloucit"
      ? tlSloucit : tlUlozit;
    for (const b of [tlUlozit, tlSloucit]) {
      if (!b) continue;
      b.querySelector(".icon.enter")?.remove();
      b.removeAttribute("aria-keyshortcuts");
    }
    if (!cil) return;
    cil.append(icon("enter", "enter"));
    cil.setAttribute("aria-keyshortcuts", "Enter");
  }

  const naseptavani = debounce(async () => {
    const q = input.value.trim();
    skrytNavesty();
    if (!q) return;
    let navrhy = [];
    try {
      navrhy = (await api(`/api/jmena?q=${encodeURIComponent(q)}`)).navrhy;
    } catch { /* našeptávání je jen pohodlnost */ }
    if (!navrhy.length || input.value.trim() !== q) return;
    suggest.replaceChildren(...navrhy.map((n) => h("li", {
      onmousedown: (e) => {
        e.preventDefault();
        input.value = n;
        skrytNavesty();
        pokusUlozit();
      },
    }, n)));
    suggest.dataset.active = "-1";
    if (suggest.children.length) nasept.ukaz();
    else nasept.skryj();
  }, 150);

  function vykresZpetnou() {
    if (!zpetna) return;
    zpetna.replaceChildren();
    if (s.chyba) {
      zpetna.append(h("div", { class: "notice error" }, s.chyba));
      input?.classList.add("invalid");
    } else {
      input?.classList.remove("invalid");
      if (s.zprava) zpetna.append(h("div", { class: "hint" }, s.zprava));
    }
  }

  async function pokusUlozit() {
    if (!s.os) return;
    // Jméno odchází (Enter i tlačítko): návrhy pryč, jinak by seznam
    // v horní vrstvě zůstal na místě, když se okno přeskládá (sloučení).
    skrytNavesty();
    const jmeno = input.value.trim().replace(/\s+/g, " ")
      .replace(/\s*,\s*/, ", ");
    s.zprava = "";
    s.chyba = "";
    if (!jmeno) {
      s.zprava = "Jméno musí být vyplněno.";
      vykresZpetnou();
      return;
    }
    let kanonicke = jmeno;
    if (!jeKanon(jmeno)) {
      // tvar ze seznamu / návrh převodu — jako ostatní pole jmen
      if (!(s.prevedeno && s.navrh)) {
        let r = null;
        try {
          r = await api(
            `/api/jmena/kontrola?jmeno=${encodeURIComponent(jmeno)}`);
        } catch { /* bez kontroly zkusíme zapsat přímo */ }
        if (r?.znamo) kanonicke = jmeno;
        else if (r?.mysleli_jste) kanonicke = r.mysleli_jste;
        else if (r?.prevod) {
          s.prevedeno = true;
          s.navrh = r.prevod;
          s.zprava = `Nové jméno — nabízím převod na kanonický tvar ` +
            `„${r.prevod}“. Potvrďte Enterem nebo „Uložit“.`;
          vykresZpetnou();
          return;
        }
      } else {
        kanonicke = s.navrh;
      }
    }
    await zapis({ akce: "pojmenovat", jmeno: kanonicke });
  }

  async function zapis(body) {
    // Jedna volba naráz: druhá (dvojklik, zkratka) by po odpovědi
    // vyřídila už další, nezobrazenou osobu.
    if (!s.os || s.zapisuje) return;
    const os = s.os;
    if (body.akce === "pojmenovat") s.posledniJmeno = body.jmeno;
    s.zapisuje = true;
    try {
      const r = await api(url(`/osoby/${encodeURIComponent(os.id)}`),
        { method: "POST", body });
      uspesne(body.akce, r, os);
    } catch (err) {
      if (err.status === 409 && err.data?.shoda) {
        s.slouceni = err.data.shoda;
        vykresSlouceni(err.data.shoda);
        return;
      }
      if (err.status === 400 && err.data?.chyba === "kanonicky_tvar") {
        s.prevedeno = true;
        s.navrh = err.data.navrh || "";
        s.zprava = `Uložit jako „${err.data.navrh}“? Potvrďte ` +
          "Enterem nebo „Uložit“.";
        vykresZpetnou();
        return;
      }
      if (err.status === 400 && err.data?.chyba === "jmeno_povinne") {
        s.zprava = "Jméno musí být vyplněno.";
        vykresZpetnou();
        return;
      }
      // chyba Immiche: osoba zůstává aktuální s vyplněným jménem
      s.chyba = `Chyba Immiche — ${textChyby(err)} ` +
        "Osoba zůstává nabídnutá s vyplněným jménem.";
      s.priorJmeno = input?.value || "";
      vykresZpetnou();
    } finally {
      s.zapisuje = false;
    }
  }

  function vykresSlouceni(shoda) {
    if (!panelSlouceni) return;
    const nahled = h("img", { class: "nahled", alt: "",
      src: url(`/osoby/osoba/${encodeURIComponent(shoda.id)}/nahled`) });
    nahled.addEventListener("error", () => nahled.remove());
    panelSlouceni.replaceChildren(h("div", { class: "slouceni" }, nahled,
      h("div", {}, `V Immichi už existuje osoba „${shoda.jmeno}“ — ` +
        "shoda bez diakritiky, velikosti písmen a pořadí slov. Sloučit " +
        "tuto osobu do ní (obličeje se spojí)? Sloučení nejde v nástroji " +
        "vrátit."),
      h("div", { class: "tl" },
        tlSloucit = h("button", { class: "primary",
          title: "Sloučit (Enter)", onclick: sloucit }, "Sloučit"),
        h("button", {
          onclick: () => zapis({ akce: "pojmenovat",
            jmeno: s.posledniJmeno || input.value.trim(),
            samostatne: true }) },
        "Ponechat samostatně"))));
    oznacEnter();
  }

  function uspesne(typ, r, os) {
    s.fronta = vyrid(s.fronta, os.id);
    if (typ === "nevim") s.odlozene += 1;
    else s.zmena = true;
    if (Array.isArray(r?.osoby)) s.osoby = r.osoby;
    // Zpět vrátí jen poslední krok; sloučení se vracet nedá. „Ponechat
    // samostatně“ posílá pojmenovat, jméno kroku drží s.posledniJmeno.
    s.posledni = typ === "sloucit" ? null
      : {
        typ, os,
        jmeno: typ === "pojmenovat" ? (s.posledniJmeno || "") : "",
      };
    s.vyslo += 1;
    dalsi();
  }

  // Vrácení posledního kroku (tlačítko i Alt+Backspace): endpoint
  // `zpet` ověří, že osobu nikdo mezitím nezměnil. Při úspěchu osobu
  // vrátí na začátek fronty a nabídne ji znovu (po pojmenování
  // s předvyplněným jménem); 409 krok odepíše, chyba Immiche ho nechá
  // na výběr. Hlídá tentýž zámek `s.zapisuje` jako ostatní volby.
  async function vratitKrok() {
    const p = s.posledni;
    if (!p || s.zapisuje) return;
    s.zapisuje = true;
    const body = p.typ === "pojmenovat"
      ? { krok: p.typ, jmeno: p.jmeno } : { krok: p.typ };
    try {
      const r = await api(url(`/osoby/${encodeURIComponent(p.os.id)}/zpet`),
        { method: "POST", body });
      s.posledni = null;
      s.fronta = vratit(s.fronta, p.os);
      s.vyslo -= 1;
      if (p.typ === "nevim") s.odlozene -= 1;
      else {
        s.zmena = true;
        if (Array.isArray(r?.osoby)) s.osoby = r.osoby;
      }
      dalsi(p.typ === "pojmenovat" ? p.jmeno : "");
    } catch (err) {
      if (err.status === 409 && err.data?.chyba === "zmeneno") {
        // někdo jiný už osobu pozměnil — krok už není co vrátit
        s.posledni = null;
        if (tlZpet) tlZpet.disabled = true;
        s.zprava = "Osobu mezitím změnil někdo jiný, krok nejde vrátit.";
        if (s.os) vykresZpetnou();
        else kresleni();
      } else {
        // zápis do Immiche selhal — krok zůstává, Zpět je pořád dostupné
        s.chyba = `Chyba Immiche — ${textChyby(err)} ` +
          "Osoba se nezměnila, vrácení lze zkusit znovu.";
        if (s.os) vykresZpetnou();
        else kresleni();
      }
    } finally {
      s.zapisuje = false;
    }
  }

  function nevime() {
    if (!s.os) return;
    zapis({ akce: "nevim" });
  }

  function skryt() {
    if (!s.os) return;
    zapis({ akce: "skryt" });
  }

  // --- průchod a kreslení ---------------------------------------------------

  function dalsi(priorJmeno = "") {
    const krok = prechod(s.fronta, s.odlozene);
    s.os = krok.krok === "osoba" ? krok.osoba : null;
    s.prevedeno = false;
    s.navrh = "";
    s.chyba = "";
    s.zprava = "";
    s.priorJmeno = priorJmeno;   // jen po vrácení pojmenování
    s.slouceni = null;
    kresleni();
    if (s.os) dialog.querySelector("#pojm-jmeno")?.focus();
  }

  function konecKola() {
    const obs = h("div", { class: "konec" });
    // Hláška z vrácení, které selhalo už na obrazovce konce kola.
    if (s.chyba) obs.append(h("div", { class: "notice error" }, s.chyba));
    else if (s.zprava) obs.append(h("div", { class: "notice" }, s.zprava));
    if (s.odlozene > 0) {
      obs.append(h("div", { class: "notice warn" },
        h("strong", {}, "Konec kola. "),
        `Neodložené osoby nezbyly — zbývají jen odložené (${plural(
          s.odlozene, "osoba", "osoby", "osob")}). Můžete je projít ` +
        "znovu (odložení se vymaže), nebo nástroj zavřít a vrátit se " +
        "později."),
      h("div", { class: "radek" },
        h("button", { class: "primary", onclick: noveKolo },
          `Projít odložené znovu (${s.odlozene})`),
        tlacitkoZpet(),
        h("button", { onclick: () => zavrit() }, "Zavřít")));
    } else {
      obs.append(h("div", { class: "notice" },
        h("strong", {}, "Hotovo. "),
        "Všechny osoby z alba této akce jsou pojmenované nebo skryté."),
      h("div", { class: "radek" },
        tlacitkoZpet(),
        h("button", { class: "primary", onclick: () => zavrit() },
          "Zavřít")));
    }
    return obs;
  }

  // Tlačítko Zpět: vrácení naposledy vyřízené osoby, ne volba nad tou
  // aktuální — proto vlevo od „Uložit“. Neaktivní, dokud nic není.
  function tlacitkoZpet() {
    return tlZpet = h("button", { class: "zpet", disabled: !s.posledni,
      title: "Vrátit poslední krok (Alt+Backspace)",
      onclick: () => vratitKrok() }, "Zpět (Alt+⌫)");
  }

  async function noveKolo() {
    try {
      await api(url("/osoby/kolo"), { method: "POST" });
      s.posledni = null;        // nové kolo — krok z toho předchozího už ne
      await nacti();
      dalsi();
    } catch (err) {
      s.chybaNacteni = textChyby(err);
      kresleni();
    }
  }

  function kresleni() {
    const hlavni = dialog.querySelector(".obsah");
    hlavni.replaceChildren();
    if (s.chybaNacteni) {
      hlavni.append(h("div", { class: "notice error" },
        `Nástroj nelze načíst: ${s.chybaNacteni}`),
      h("div", { class: "radek" },
        h("button", { onclick: () => zavrit() }, "Zavřít")));
      return;
    }
    if (s.nacitani) {
      hlavni.append(h("p", { class: "meta" }, "Načítám osoby z alba…"));
      return;
    }
    const stavka = h("div", { class: "stavka" });
    if (!s.uplne) {
      stavka.append(h("div", { class: "notice warn" },
        "Rozpoznávání obličejů v Immichi ještě probíhá — další osoby " +
        "mohou přibýt."));
    }
    if (s.os) {
      prid(stavka,
        badge(pocetadlo(s.vyslo, s.fronta.length), "pocetadlo"),
        badge(plural(s.os.pocet, "obličej", "obličeje", "obličejů")
          + " v akci"),
        s.odlozene ? badge(`odloženo: ${s.odlozene}`, "odlozeno") : null,
        h("span", { class: "vyrovn" },
          badge(`zbývá pojmenovat: ${s.fronta.length}`)));
    }
    hlavni.append(stavka);
    if (!s.os) {
      hlavni.append(konecKola());
      return;
    }
    const kont = h("div", { class: "va" },
      h("div", { class: "vl" }, ...s.os.vyrezy.map(figureFor)),
      h("div", { class: "ovladani" },
        h("div", { class: "poloz" }, jmenovePole()),
        h("div", { class: "tl" },
          tlacitkoZpet(),
          tlUlozit = h("button", { class: "primary", title: "Uložit (Enter)",
            onclick: () => pokusUlozit() }, "Uložit"),
          h("button", { title: "Osoba se v tomto kole už nenabídne",
            onclick: nevime }, "Odložit (PgDn)"),
          h("button", { title: "Skrýt osobu v Immichi (obličeje zůstanou)",
            onclick: skryt }, "Skrýt (Alt+Del)"))));
    if (!s.os.vyrezy.length) {
      kont.prepend(h("p", { class: "meta" },
        "Osoba nemá v albu žádný zobrazitelný výřez."));
    }
    hlavni.append(kont);
    tlSloucit = null;
    oznacEnter();
    vykresZpetnou();
    rozmerVyreze(hlavni);
  }

  // --- načtení, zavření -----------------------------------------------------

  async function nacti() {
    s.nacitani = true;
    s.chybaNacteni = "";
    kresleni();
    try {
      const r = await api(url("/osoby"));
      s.stav = r.stav;
      s.uplne = !!r.uplne;
      s.odlozene = r.odlozene || 0;
      s.fronta = poradiOsob(r.osoby || []);
      s.nacitani = false;
    } catch (err) {
      s.nacitani = false;
      s.chybaNacteni = textChyby(err);
    }
  }

  let zavirajici = false;

  async function zavrit() {
    if (zavirajici) return;
    zavirajici = true;
    let vysledek = {};
    try {
      vysledek = await api(url("/osoby/hotovo"), { method: "POST" }) || {};
    } catch { /* zavření se provede i bez potvrzení ze serveru */ }
    nasept?.skryj();        // otevřený seznam návrhů nesmí přežít dialog
    dialog.close();
    dialog.remove();
    window.removeEventListener("resize", onResize);
    naZavreni?.({ ...vysledek, zmena: s.zmena, osoby: s.osoby });
  }

  const onResize = () => {
    if (dialog.open) rozmerVyreze(dialog.querySelector(".obsah"));
  };

  dialog = h("dialog", { class: "nastroj-osoby",
    "aria-label": "Nástroj pojmenování osob" },
  h("div", { class: "hl" },
    h("div", {},
      h("h2", {}, "Nástroj pojmenování osob"),
      h("div", { class: "meta" }, `${nazev} · nepojmenované osoby ` +
        "z alba v Immichi")),
    h("button", { class: "zavrit", title: "Zavřít",
      "aria-label": "Zavřít", onclick: () => zavrit() }, "✕")),
  h("div", { class: "obsah" }));
  // Zkratky voleb platí v celém překryvu, i v poli jména (Enter řeší
  // pole samo, Esc událost `cancel`).
  dialog.addEventListener("keydown", (e) => {
    const volba = zkratka(e);
    if (!volba) return;
    e.preventDefault();     // Alt+Backspace v poli nesmí smazat text
    if (volba === "odlozit") nevime();
    else if (volba === "skryt") skryt();
    else vratitKrok();      // bez kroku nic nedělá
  });
  dialog.addEventListener("cancel", (e) => {
    e.preventDefault();      // Esc → stejné zavření jako křížek
    zavrit();
  });
  document.body.append(dialog);
  window.addEventListener("resize", onResize);
  dialog.showModal();
  nacti().then(() => {
    dalsi();
  });
  return dialog;
}
