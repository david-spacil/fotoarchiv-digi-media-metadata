// Klient: seznam akcí, průvodce prvním otevřením a pracovní
// plocha. Stav (dokument `_metadata.json`) drží klient a ukládá ho celý.

import { parts, withDay, withTime } from "./datetime.js";
import { missing, resolve, resolveGroup } from "./inherit.js";
import {
  effectiveDoc, freshDescription, groupsWithoutAuthors, reconcile, targetKey,
} from "./importdesc.js";
import {
  STAV_KONTROLY, applyDecisionChanges, checkCounts, cleanupDecisions,
  damagedFiles, damagedMap, damagedText, decisionChanges,
  odebranaPolohaFiles, toggleAllowed, unchecked,
} from "./integrity.js";
import {
  FILTRY, POLE, RAZENI, filterCounts, lastEdit, listHash, parseListHash,
  ratio, visibleEvents,
} from "./fronta.js";
import { icon } from "./icons.js";
import { immichStav } from "./immichstav.js";
import { showNaming } from "./naming.js";
import { osmUrl } from "./osm.js";
import { klavesa, naPas, oddil, radek, stranka } from "./pohyb.js";
import {
  applyToggle, excludedCounts, importCount, planToggle, withExcluded,
} from "./vylouceni.js";
import {
  byDay, dayLabel, personIndex, sectionInfo, stripeSegments, stripeStops,
} from "./sections.js";

// --- pomocné -------------------------------------------------------------

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
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

const app = document.getElementById("app");

function eventUrl(name, rest = "") {
  return `/api/akce/${encodeURIComponent(name)}${rest}`;
}

const LARGE = 1600;

// Náhled souboru akce; v kroku skupiny a autoři importu soubor importu
// podle cesty ve výběru (`state.scan[f].cesta`).
function thumbUrl(f, size) {
  if (state.mode === "import") {
    const q = new URLSearchParams({ jmeno: userName() });
    if (size) q.set("velikost", size);
    return importUrl(`/nahled/${state.scan[f]?.cesta.split("/")
      .map(encodeURIComponent).join("/")}?${q}`);
  }
  return eventUrl(state.name, `/nahled/${encodeURIComponent(f)}` +
    (size ? `?velikost=${size}` : ""));
}

// Relace skončila (401) nebo čeká povinná změna hesla: pryč z aplikace.
// Vrátí true, když se přesměrovává.
function authRedirect(status, data) {
  const to = status === 401 ? "/prihlaseni"
    : status === 403 && data?.chyba === "zmenit_heslo" ? "/heslo" : null;
  if (!to) return false;
  state.dirty = false; // neuložené změny server stejně odmítne
  location.href = to;
  return true;
}

async function api(url, opts = {}) {
  const r = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    authRedirect(r.status, data);
    const err = new Error(`HTTP ${r.status}`);
    err.status = r.status;
    err.data = data;
    throw err;
  }
  return data;
}

// POST se streamem NDJSON (průběh dlouhých operací): `onEvent` pro každý
// řádek, vrátí poslední událost. Odmítnutí před startem je JSON s chybou.
// `body` null = GET.
async function apiStream(url, body, onEvent) {
  const r = await fetch(url, body === null ? {} : { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) });
  if (!r.ok) {
    const err = new Error(`HTTP ${r.status}`);
    err.status = r.status;
    err.data = await r.json().catch(() => null);
    authRedirect(r.status, err.data);
    throw err;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let last = null;
  const take = (line) => {
    if (!line.trim()) return;
    last = JSON.parse(line);
    onEvent(last);
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      take(buf.slice(0, i));
      buf = buf.slice(i + 1);
    }
  }
  take(buf);
  return last;
}

function plural(n, one, few, many) {
  return `${n} ${n === 1 ? one : n >= 2 && n <= 4 ? few : many}`;
}

function isEmpty(v) {
  return v === undefined || v === null || v === "" ||
    (Array.isArray(v) && v.length === 0);
}

function slug(text) {
  return text.normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") ||
    "skupina";
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

const STAV = {
  nezpracovano: "nezpracováno",
  rozpracovano: "rozpracováno",
  hotovo: "hotovo",
  kolize: "kolize složek",
};

// Složka akce je v archivu s příponou `.ignored` i bez ní (issue #13).
const KOLIZE = "Akce má v archivu dvě složky, s příponou .ignored i bez " +
  "ní. Aplikace s ní nepracuje, dokud jednu z nich správce archivu " +
  "neodstraní nebo nesloučí.";

// Pole, která chybí dokončené akci (`chybi` v seznamu akcí).
const CHYBI = { autori: "autoři", datum: "data", misto: "místa",
  osoby: "nepojmenované osoby" };

// Nálezy kontroly akce (issue #11): tvary podle počtu a dovětek.
const NALEZY = {
  nepodporovany: [["nepodporovaný soubor", "nepodporované soubory",
    "nepodporovaných souborů"], " v kořeni"],
  sirotek_xmp: [["osiřelý sidecar", "osiřelé sidecary",
    "osiřelých sidecarů"], " (.xmp bez souboru)"],
  raw: [["RAW", "RAWy", "RAWů"], " v kořeni"],
  podslozka: [["podsložka", "podsložky", "podsložek"], " k rozhodnutí"],
  chybejici: [["soubor chybí", "soubory chybí", "souborů chybí"],
    " v kořeni"],
};
// Nálezy, které úklid napraví (záznam bez souboru jen hlásí).
const NALEZY_UKLID = ["nepodporovany", "sirotek_xmp", "raw", "podslozka"];

function nalez(druh, n) {
  const [forms, tail] = NALEZY[druh];
  return plural(n, ...forms) + tail;
}

function nalezyText(counts) {
  return Object.keys(NALEZY).filter((d) => counts[d])
    .map((d) => nalez(d, counts[d])).join(", ");
}

// --- stav ----------------------------------------------------------------

const state = {
  info: null,
  me: null,          // /api/ja: přihlášený uživatel (bez přihlášení admin)
  events: null,
  name: null,        // otevřená akce
  detail: null,      // odpověď /api/akce/<n> bez metadat
  doc: null,
  version: null,
  present: new Set(), // soubory, které v kořeni skutečně jsou
  scan: {},          // název → technické údaje ze skenu
  mode: null,        // "wizard" | "workspace"
  sel: new Set(),    // vybrané soubory
  group: null,       // vybraná skupina (řádek navigátoru)
  anchor: null,
  order: [],         // pořadí souborů v mřížce (pro Shift)
  secOf: new Map(),  // soubor → klíč oddílu
  navSecs: [],       // oddíly v navigátoru (s chybějícími údaji)
  navMissing: null,  // výsledek missing() pro řádek Akce
  visible: new Set(), // klíče oddílů, které jsou v mřížce vidět
  view: "grid",      // "grid" | "loupe"
  // "skupiny" | "datum": oddíly plochy; volba prohlížeče, ne akce.
  layout: localStorage.getItem("zobrazeni") === "datum" ? "datum" : "skupiny",
  current: null,     // aktuální soubor (lupa)
  preload: [],
  listHash: null,    // adresa seznamu akcí s filtrem (návrat z plochy)
  sessionNames: new Set(),
  keptEmpty: new Set(), // prázdné skupiny, které uživatel chtěl ponechat
  dirty: false,
  saving: false,
  conflict: false,
  locked: null,      // akce, jejíž zámek tahle relace drží
  readonly: null,    // držitel cizího zámku otevřené akce, {bezPrava}, nebo null
  placeOpen: null,   // místo, jehož volba souřadnic je otevřená
  geo: {},           // název místa → odpověď /api/geokodovani
  exporting: false,  // běží export nebo dokončení
  exportVersion: null, // verze `_metadata.json` posledního exportu
  exportNote: "",    // stav exportu u tlačítka
  exportStale: true, // sidecary nejsou ověřeně aktuální
  exportErrors: [],  // chyby posledního exportu po souborech
  finishResult: null, // odpověď dokončení pro kontrolní stránku
  finishError: null, // chyba požadavku dokončení
  pendingFix: null,  // náprava z kontrolní stránky, provede se na ploše
};

// --- uživatel a zámek akce ---------------------------------------------------

// Relace = záložka prohlížeče. Náhodný token přes getRandomValues:
// crypto.randomUUID je jen v zabezpečeném kontextu (https, localhost).
function session() {
  let id = sessionStorage.getItem("relace");
  if (!id) {
    id = [...crypto.getRandomValues(new Uint8Array(16))]
      .map((b) => b.toString(16).padStart(2, "0")).join("");
    sessionStorage.setItem("relace", id);
  }
  return id;
}

// Přihlášený: kanonické jméno z účtu; bez přihlášení (vývojový režim)
// jméno zadané v prohlížeči.
function userName() {
  if (state.me?.prihlaseni) return state.me.jmeno;
  return localStorage.getItem("jmeno");
}

const NAME_RE = /^[^,]+, [^,]+$/;

// Jen bez přihlášení: jméno zadané v prohlížeči (jen se zobrazuje).
function askName() {
  return new Promise((done) => {
    const input = h("input", { value: userName() || "", list: "jmena-uziv",
      placeholder: "Příjmení, Jméno", autocomplete: "off" });
    const options = h("datalist", { id: "jmena-uziv" });
    const warn = h("p", { class: "warn", hidden: true },
      "Zadejte ve tvaru „Příjmení, Jméno“.");
    const submit = (e) => {
      e.preventDefault();
      const name = input.value.trim().replace(/\s+/g, " ")
        .replace(/\s*,\s*/, ", ");
      if (!NAME_RE.test(name)) {
        warn.hidden = false;
        return;
      }
      localStorage.setItem("jmeno", name);
      dialog.close();
      dialog.remove();
      done(name);
    };
    const dialog = h("dialog", { class: "conflict" },
      h("form", { onsubmit: submit },
        h("h2", {}, "Kdo jste?"),
        h("p", {}, "Jméno uvidí ostatní u akce, kterou upravujete."),
        input, options, warn,
        h("div", { class: "buttons" },
          h("button", { class: "primary" }, "Pokračovat"))));
    dialog.addEventListener("cancel", (e) => e.preventDefault());
    document.body.append(dialog);
    dialog.showModal();
    api("/api/jmena").then((r) => options.replaceChildren(
      ...r.navrhy.map((n) => h("option", { value: n })))).catch(() => {});
  });
}

const HEARTBEAT_MS = 60_000;
let heartbeatTimer = null;

// Jen ke čtení bez oprávnění k úpravě akce (role, `upravili`).
const NO_RIGHTS = { bezPrava: true };

// Získá zámek akce; při cizím zámku nastaví `state.readonly` (držitel),
// bez oprávnění `NO_RIGHTS`.
async function acquireLock(name) {
  try {
    await api(eventUrl(name, "/zamek"), {
      method: "POST", body: { relace: session(), jmeno: userName() },
    });
  } catch (err) {
    if (err.status === 403 && err.data?.chyba === "jen_cteni") {
      state.readonly = NO_RIGHTS;
      return false;
    }
    if (err.status !== 409) throw err;
    state.readonly = err.data.drzitel;
    return false;
  }
  state.locked = name;
  state.readonly = null;
  clearInterval(heartbeatTimer);
  heartbeatTimer = setInterval(heartbeat, HEARTBEAT_MS);
  return true;
}

async function heartbeat() {
  const name = state.locked;
  if (!name) return;
  try {
    await api(eventUrl(name, "/zamek"), {
      method: "PUT", body: { relace: session() },
    });
  } catch (err) {
    if (err.status !== 409 || name !== state.locked) return;
    state.locked = null;
    clearInterval(heartbeatTimer);
    if (err.data?.uvolnil) {
      // Zámek uvolnil admin/archivář: znovu nezískávat, rozdělané změny propadly.
      state.readonly = err.data.drzitel || { jmeno: err.data.uvolnil };
      state.readonly.uvolnil = err.data.uvolnil;
      lostLock();
      return;
    }
    // Zámek je pryč (restart serveru nebo opuštění); volný se získá znovu.
    if (!await acquireLock(name).catch(() => false)) lostLock();
  }
}

function releaseLock() {
  const name = state.locked;
  state.locked = null;
  clearInterval(heartbeatTimer);
  if (!name) return;
  api(eventUrl(name, "/zamek"), {
    method: "DELETE", body: { relace: session() },
  }).catch(() => {});
}

// Odmítnutá změna pod zámkem: držitel (423), `NO_RIGHTS` (403, oprávnění
// zmizelo během práce), jinak undefined.
function deniedLock(err) {
  if (err.status === 423) return err.data?.drzitel || { jmeno: "jiný uživatel" };
  if (err.status === 403 && err.data?.chyba === "jen_cteni") return NO_RIGHTS;
  return undefined;
}

// Klíč jména jako `names.normalize` na serveru: bez diakritiky, velikosti
// písmen a pořadí slov.
function nameKey(name) {
  return (name || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().match(/[\p{L}\p{N}_]+/gu)?.sort().join(" ") || "";
}

// Kdo drží zámek; vlastní jméno = jiná záložka téhož uživatele.
function holderText(holder) {
  return nameKey(holder.jmeno) === nameKey(userName())
    ? "Akci máte otevřenou v jiné záložce. Pokud chcete pokračovat " +
      "v práci zde, zavřete původní záložku."
    : `Akci upravuje ${holder.jmeno}.`;
}

// Admin nebo archivář uvolní cizí zámek (opuštěná rozdělaná práce) a akci otevře.
async function forceRelease() {
  const holder = state.readonly?.jmeno || "jiný uživatel";
  if (!await confirmDialog("Uvolnit zámek akce?", [
    `Zámek drží ${holder}.`,
    "Jeho neuložené změny se ztratí, akci bude mít jen ke čtení.",
  ], "Uvolnit")) return;
  await api(eventUrl(state.name, "/zamek/vynutit"), { method: "POST" });
  route();
}

function lockNotice() {
  const r = state.readonly;
  // Prázdný řetězec, ne null: jde přímo do replaceChildren, který by
  // null vypsal jako text.
  if (!r) return "";
  if (r.bezPrava) {
    return h("p", { class: "notice readonly" }, "Jen ke čtení – akci " +
      "upravují jen ti, kdo ji importovali nebo upravovali, archivář " +
      "a admin.");
  }
  if (r.uvolnil) {
    return h("p", { class: "notice readonly" },
      `Zámek akce uvolnil ${r.uvolnil}. Jen ke čtení – ` +
      "neuložené změny se neuloží.",
      " ", h("button", { class: "link", onclick: () => route() },
        "Zkusit znovu"));
  }
  const own = nameKey(r.jmeno) === nameKey(userName());
  return h("p", { class: "notice readonly" },
    `${holderText(r)} Jen ke čtení – změny se neukládají.`,
    " ", h("button", { class: "link", onclick: () => route() },
      "Zkusit znovu"),
    state.me?.archivar && state.me.prihlaseni && !own
      ? [" · ", h("button", { class: "link", onclick: forceRelease },
        "Uvolnit zámek")] : null);
}

// Zámek získal někdo jiný: zahodit plánované uložení a přepnout jen
// ke čtení.
function lostLock() {
  if (!state.readonly) state.readonly = { jmeno: "jiný uživatel" };
  state.dirty = false;
  if (state.mode === "workspace") renderWorkspace();
  else if (state.mode === "finish") renderFinish();
  else if (state.mode === "wizard") renderReadonlyWizard();
}

// --- směrování -----------------------------------------------------------

window.addEventListener("hashchange", route);
window.addEventListener("pagehide", () => {
  if (!state.locked) return;
  navigator.sendBeacon(eventUrl(state.locked, "/zamek/uvolnit"),
    JSON.stringify({ relace: session() }));
  state.locked = null;
  clearInterval(heartbeatTimer);
});
window.addEventListener("pageshow", (e) => {
  if (e.persisted) route(); // návrat z bfcache: zámek získat znovu
});
window.addEventListener("beforeunload", (e) => {
  if (state.dirty || state.saving || imp.uploading || descTimer ||
      exclDirty) {
    e.preventDefault();
  }
});
document.addEventListener("keydown", (e) => {
  const ws = state.mode === "workspace";
  // Skupinový krok (průvodce, import): klávesy jen když stránka má mřížku.
  const krok = (state.mode === "wizard" || state.mode === "import") &&
    !!document.getElementById("grid");
  if (!ws && !krok) return;
  if (e.target.closest("input, textarea, select") ||
      document.querySelector("dialog[open]")) return;
  const loupe = ws && state.view === "loupe";
  const k = klavesa(e);
  if (k) {
    e.preventDefault(); // ať šipky neposouvají stránku a Ctrl+A text
    if (k.druh === "vse") select(new Set(state.order), null);
    else moveTo(cilPohybu(k, loupe), k.rozsir);
    return;
  }
  if (e.key === "Escape") {
    if (loupe) setView("grid");
    else select(new Set(), null);
  } else if (!ws) {
    // Enter a P ve skupinovém kroku nic nedělají, Delete jen v importu
    // (vyloučení z importu).
    if (e.key === "Delete" && state.mode === "import") {
      e.preventDefault();
      toggleExcluded();
    }
  } else if (e.key === "Delete") {
    e.preventDefault();
    toggleDiscard();
  } else if ((e.key === "p" || e.key === "P") &&
             !e.altKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    togglePanel();
  } else if (e.key === "Enter" && !loupe && !e.target.closest("button, a")) {
    e.preventDefault();
    setView("loupe");
  }
});

async function route() {
  if (state.dirty && state.mode === "workspace") await save();
  const m = location.hash.match(
    /^#\/akce\/([^/#]+)(\/dokonceni)?(#osoby)?$/);
  const im = location.hash.match(/^#\/import(?:\/([^?]*))?(?:\?(.*))?$/);
  const name = m ? decodeURIComponent(m[1]) : null;
  if (state.locked && state.locked !== name) releaseLock();
  if (location.hash === "#/nastaveni") {
    await showSettings();
  } else if (location.hash === "#/pretridit") {
    await showUnsorted();
  } else if (im) {
    await openImport(im[1] ? decodeURIComponent(im[1]) : null,
      new URLSearchParams(im[2] || ""));
  } else if (name) {
    await openEvent(name, !!m[2]);
    // Odkaz ze seznamu s `#osoby`: otevře plochu akce rovnou s nástrojem.
    if (m[3] && state.mode === "workspace" && state.me?.archivar
        && canOpenNaming()) openNaming();
  } else await showList();
}

function header(...right) {
  const info = state.info || {};
  const paths = info.zapis
    ? h("span", { class: "paths" }, `archiv: ${info.archiv || "…"} · `,
      h("strong", {}, "metadata a úklid se zapisují do archivu"))
    : h("span", { class: "paths" },
      `archiv (jen čtení): ${info.archiv || "…"} · `,
      h("strong", {}, `ukládá se do: ${info.work || "…"}`));
  // Na úzkém okně se cesta ořízne; celá je v title.
  paths.title = paths.textContent;
  return h("header", {},
    h("a", { href: "#/", class: "brand" }, "Fotoarchiv – metadata"),
    state.info ? h("span", { class: "version", title: "verze aplikace" },
      info.verze || "verze neznámá") : null,
    paths,
    ...right,
    modeToggle(),
    state.me?.admin
      ? h("a", { href: "#/nastaveni", class: "settings-link" }, "Nastavení")
      : null,
    state.me?.prihlaseni ? [
      h("a", { href: "/heslo", class: "settings-link",
        title: "Změnit heslo" }, userName()),
      h("button", { class: "link user", onclick: logout }, "Odhlásit"),
    ] : userName() ? h("button", { class: "link user",
      title: "Změnit jméno",
      onclick: async () => { await askName(); route(); } }, userName())
      : null);
}

// Světlý/tmavý režim (viz vzhled.js); volba prohlížeče.
function modeToggle() {
  const root = document.documentElement;
  const label = () => root.dataset.rezim === "svetly"
    ? ["☾ Tmavý", "Přepnout do tmavého režimu"]
    : ["☀ Světlý", "Přepnout do světlého režimu"];
  const [icon, title] = label();
  const b = h("button", { class: "rezim", title, onclick: () => {
    const light = root.dataset.rezim !== "svetly";
    if (light) root.dataset.rezim = "svetly";
    else delete root.dataset.rezim;
    try {
      if (light) localStorage.setItem("rezim", "svetly");
      else localStorage.removeItem("rezim");
    } catch { /* bez úložiště jen do obnovení stránky */ }
    [b.textContent, b.title] = label();
  } }, icon);
  return b;
}

async function logout() {
  if (state.dirty) await save();
  // Server uvolní zámky tohoto přihlášení.
  state.locked = null;
  clearInterval(heartbeatTimer);
  await api("/api/odhlaseni", { method: "POST" }).catch(() => {});
  location.href = "/prihlaseni";
}

// --- seznam akcí ----------------------------------------------------------

async function showList() {
  state.mode = null;
  state.name = null;
  app.replaceChildren(header(), h("main", { class: "list" }, "Načítám…"));
  const [events, pending] = await Promise.all([
    api(`/api/akce?relace=${session()}`),
    userName() ? api(`/api/import?jmeno=${encodeURIComponent(userName())}`)
      .then((r) => r.importy).catch(() => []) : []]);
  state.events = events;
  // Filtr, hledání a řazení v adrese seznamu (přežijí návrat z plochy).
  const view = parseListHash(location.hash);
  const filters = h("div", { class: "seg", role: "group",
    "aria-label": "Filtr" });
  const search = h("input", { type: "search", value: view.hledat,
    placeholder: "Hledat v názvu…", "aria-label": "Hledat v názvu",
    oninput: () => { view.hledat = search.value; update(); } });
  const sort = h("select", { "aria-label": "Řazení",
    onchange: () => { view.razeni = sort.value; update(); } },
  RAZENI.map(([id, label]) => h("option", { value: id,
    selected: id === view.razeni }, label)));
  const layouts = h("div", { class: "seg", role: "group",
    "aria-label": "Podoba karet" });
  const list = h("div");
  const update = () => {
    state.listHash = listHash(view);
    history.replaceState(null, "", state.listHash);
    const me = userName();
    const counts = filterCounts(events, view, me);
    filters.replaceChildren(...FILTRY.map(([id, label]) =>
      h("button", { "aria-pressed": String(view.filtr === id),
        onclick: () => { view.filtr = id; update(); } },
      label, h("span", { class: "n" }, counts[id]))));
    const layout = cardLayout();
    layouts.replaceChildren(...[["dlazdice", "mrizka", "Dlaždice"],
      ["radky", "radky", "Řádky"]].map(([id, ic, label]) =>
      h("button", { "aria-pressed": String(layout === id), title: label,
        onclick: () => { localStorage.setItem("karty", id); update(); } },
      icon(ic), label)));
    const shown = visibleEvents(events, view, me);
    list.className = `karty ${layout}`;
    list.replaceChildren(...(shown.length
      ? shown.map(layout === "radky" ? eventRow : eventTile)
      : [h("p", { class: "meta" }, "Žádná akce neodpovídá filtru.")]));
  };
  update();
  app.replaceChildren(header(), h("main", { class: "list" },
    h("div", { class: "row" }, h("h1", {}, "Akce"),
      h("button", { onclick: () => { location.hash = "#/import"; } },
        "Importovat fotky a videa…"),
      state.me?.archivar ? h("a", { href: "#/pretridit" }, "Přetřídit")
        : null),
    pendingImports(pending),
    h("div", { class: "fronta-lista" }, filters, search, sort, layouts),
    list));
}

// Podoba karet seznamu akcí: "dlazdice" (výchozí) | "radky"; volba
// prohlížeče.
function cardLayout() {
  return localStorage.getItem("karty") === "radky" ? "radky" : "dlazdice";
}

// Odkaz zpět na seznam se zvoleným filtrem, hledáním a řazením.
function listLink() {
  return state.listHash || "#/";
}

function eventLink(e) {
  return h("a", { href: `#/akce/${encodeURIComponent(e.nazev)}`,
    class: "nazev" }, e.nazev.slice(11));
}

function eventMeta(e) {
  return h("span", { class: "meta" },
    `${e.datum} · ${plural(e.souboru, "soubor", "soubory", "souborů")}`);
}

// Až 4 ukázky rovnoměrně z celé akce; načtou se až u viditelné karty.
function eventThumbs(e) {
  if (!e.ukazky?.length) return null;
  const ph = (f) => h("span", { class: "ph", title: f }, "bez náhledu");
  return h("div", { class: `nahledy n${e.ukazky.length}` },
    e.ukazky.map((f) => h("img", { alt: "", title: f, loading: "lazy",
      src: eventUrl(e.nazev, `/nahled/${encodeURIComponent(f)}`),
      onerror: (ev) => ev.target.replaceWith(ph(f)) })));
}

function eventBadges(e) {
  return [
    h("span", { class: "badge stav",
      title: e.stav === "kolize" ? KOLIZE : null }, STAV[e.stav]),
    e.zmeneno_po_exportu
      ? h("span", { class: "badge zmeneno" }, "změněno po exportu") : null,
    e.chybi.length ? h("span", { class: "badge nekompletni",
      title: "Chybí: " + e.chybi.map((k) => CHYBI[k]).join(", ") },
    "nekompletní") : null,
    Object.keys(e.kontrola || {}).length
      ? h("span", { class: "badge vyresit", title: nalezyText(e.kontrola) },
        "k vyřešení") : null,
    e.poskozene
      ? h("span", { class: "badge poskozene",
        title: "Poškozené soubory z kontroly integrity" },
      plural(e.poskozene, "poškozený", "poškozené", "poškozených"))
      : null,
    e.upravit === false ? h("span", { class: "badge jen-cteni",
      title: "Akci upravují jen ti, kdo ji importovali nebo upravovali, " +
        "archivář a admin." }, "jen ke čtení") : null,
    // Stav v Immichi jen u dokončené akce se záznamem; bez nastaveného
    // Immichu výpis pole `immich` nevrací.
    e.stav === "hotovo" && e.immich?.stav
      ? h("span", { class: "badge immich" }, immichStav(e.immich)) : null,
  ];
}

// Kdo akci drží (zámek) a kdo ji naposledy upravoval.
function eventPeople(e) {
  const holder = !e.drzitel ? null : e.drzitel.vase
    ? h("span", { class: "drzitel vase" }, "otevřeno u vás")
    : h("span", { class: "drzitel" }, `upravuje ${e.drzitel.jmeno}`);
  const last = lastEdit(e);
  const edited = last ? h("span", { class: "meta" }, "upraveno ",
    new Date(last).toLocaleString("cs", { day: "numeric",
      month: "numeric", hour: "2-digit", minute: "2-digit" }), " · ",
    Object.entries(e.upravili).sort((a, b) => (a[1] < b[1] ? 1 : -1))
      .map(([jmeno]) => jmeno.split(",")[0]).join(", ")) : null;
  return holder || edited
    ? h("div", { class: "lide" }, holder, edited) : null;
}

const POLE_POPISKY = { autori: "autoři", datum: "datum", misto: "místo" };

function progress(vyplneno, celkem) {
  const part = vyplneno < celkem;
  return h("span", { class: `pruh${part ? " castecne" : ""}` },
    h("i", { style: `width: ${celkem ? 100 * vyplneno / celkem : 100}%` }));
}

// Osoby akce v hotovosti: pojmenované z neskrytých (jen při albu se
// stavem *obličeje rozpoznány*); u nepojmenovaných nabídne archiváři
// a adminovi nástroj (URL plochy s `#osoby`).
function eventOsoby(e) {
  const o = e.hotovost?.osoby;
  if (!o) return null;
  const link = o[0] < o[1] && state.me?.archivar
    ? h("a", { class: "pojmenovani",
      href: `#/akce/${encodeURIComponent(e.nazev)}#osoby`,
      title: "Otevřít nástroj pojmenování osob" }, "Pojmenovat osoby…")
    : null;
  return { text: `osoby ${o.join("/")}`, zlomek: o.join("/"), link,
    frac: progress(o[0], o[1]), necela: o[0] < o[1] };
}

// Akce bez metadat hotovost nemá; nabídne zahájení zpracování.
function startLink(e) {
  return e.stav === "nezpracovano" ? h("a", { class: "zahajit",
    href: `#/akce/${encodeURIComponent(e.nazev)}` },
  "Zahájit zpracování…") : null;
}

// Dlaždice: náhledy 2 × 2, souhrnný pruh hotovosti a zlomky polí.
function eventTile(e) {
  let done = startLink(e);
  if (e.hotovost) {
    const r = ratio(e);
    const os = eventOsoby(e);
    done = h("div", { class: "hotovost" },
      progress(Math.round(r * 1000), 1000),
      h("span", { class: "meta" }, POLE.map((k) =>
        `${POLE_POPISKY[k]} ${e.hotovost[k].join("/")}`).join(" · ")
        + (os ? ` · ${os.text}` : "")),
      os?.link);
  }
  return h("article", { class: `karta stav-${e.stav}` },
    eventThumbs(e) || h("div", { class: "nahledy prazdne" }),
    h("div", { class: "telo" }, eventMeta(e), eventLink(e),
      h("div", { class: "stitky" }, eventBadges(e)), done, eventPeople(e)));
}

// Řádek: pruh náhledů, název a štítky, pruh hotovosti pro každé pole.
function eventRow(e) {
  const done = e.hotovost
    ? h("div", { class: "hotovost pole" }, POLE.map((k) => {
      const [vyplneno, celkem] = e.hotovost[k];
      return h("div", { class: vyplneno < celkem ? "castecne" : null },
        h("span", {}, POLE_POPISKY[k]), progress(vyplneno, celkem),
        h("span", { class: "zlomek" }, `${vyplneno}/${celkem}`));
    }), (() => {
      const os = eventOsoby(e);
      return os
        ? [h("div", { class: os.necela ? "castecne" : null },
          h("span", {}, "osoby"), os.frac,
          h("span", { class: "zlomek" }, os.zlomek)),
        os.link] : null;
    })())
    : h("div", { class: "hotovost" }, startLink(e));
  return h("article", { class: `karta stav-${e.stav}` },
    eventThumbs(e) || h("div", { class: "nahledy prazdne" }),
    h("div", { class: "telo" }, eventLink(e),
      h("div", { class: "stitky" }, eventMeta(e), eventBadges(e)),
      eventPeople(e)),
    done);
}

function fmtTime(seconds) {
  return new Date(seconds * 1000).toLocaleString("cs",
    { dateStyle: "short", timeStyle: "short" });
}

// Rozpracované importy uživatele (patří jménu, ne záložce).
function pendingImports(items) {
  if (!items.length) return null;
  const discard = async (it, button) => {
    if (!(await confirmDialog("Zahodit import?", [discardText(it.zdroj,
      it.souboru)], "Zahodit"))) return;
    button.disabled = true;
    button.textContent = "Zahazuji…";
    try {
      await api(`/api/import/${encodeURIComponent(it.id)}`,
        { method: "DELETE", body: { jmeno: userName() } });
    } catch (err) {
      button.textContent = err.data?.chyba === "probiha"
        ? "Nejde: import se provádí" : `Nejde: ${err.message}`;
      return;
    }
    showList();
  };
  return h("section", { class: "pending" },
    h("h2", {}, "Moje rozpracované importy"),
    h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Založeno"),
        h("th", {}, "Souborů"), h("th", {}, "Velikost"), h("th", {}, "Cíl"),
        h("th", {}, "Poslední aktivita"), h("th"))),
      h("tbody", {}, items.map((it) => {
        const button = h("button", { disabled: it.probiha,
          onclick: () => discard(it, button) }, "Zahodit");
        return h("tr", {},
          h("td", {}, fmtTime(it.zalozeno), it.zdroj ? h("span",
            { class: "meta" }, ` ze složky ${UNSORTED}/${it.zdroj}`) : null),
          h("td", { class: "num" }, it.souboru),
          h("td", { class: "num" }, fmtSize(it.velikost)),
          h("td", {}, !it.cil ? h("span", { class: "meta" }, "nezvolen")
            : it.nova ? `nová: ${it.cil}` : it.cil),
          h("td", {}, fmtTime(it.aktivita),
            it.probiha ? h("span", { class: "warn" }, " provádí se")
              : it.nahrava ? h("span", { class: "warn" }, " nahrává se")
                : null),
          h("td", {}, h("span", { class: "row" },
            h("a", { href: `#/import/${encodeURIComponent(it.id)}` },
              "Pokračovat"), button)));
      }))));
}

function discardText(zdroj, n) {
  return zdroj ? `Import se zahodí; složka ${UNSORTED}/${zdroj} zůstane ` +
    "beze změny."
    : `Nahrané soubory (${n}) se smažou z pracovního adresáře serveru. ` +
      "Archiv zůstane beze změny.";
}

// --- přetřídit -------------------------------------------------------------

// Složky první úrovně `přetřídit` jako kandidáti na import ze zdroje:
// výpis hned, údaje z EXIF se doplňují po složkách (stream).

const UNSORTED = "přetřídit";
let unsortedRun = 0;

function countsText(c) {
  return ["foto", "video", "raw", "nepodporovany"].filter((t) => c[t])
    .map((t) => plural(c[t], ...TYP[t])).join(", ") || "prázdná";
}

// Založí (nebo vrátí rozpracovaný) import ze složky a otevře přehled.
async function importFromSource(zdroj, navrh, button) {
  if (button) setBusy(button, "Zakládám…");
  const body = { jmeno: userName(), zdroj };
  if (navrh) Object.assign(body, { cil: navrh, nova: true });
  try {
    const r = await api("/api/import", { method: "POST", body });
    imp.id = null; // přehled se načte znovu
    location.hash = `#/import/${encodeURIComponent(r.id)}` +
      (imp.cil && !navrh ? `?cil=${encodeURIComponent(imp.cil)}` : "");
  } catch (err) {
    if (button) button.textContent = `Nejde: ${err.data?.chyba ||
      err.message}`;
  }
}

async function showUnsorted() {
  state.mode = "pretridit";
  state.name = null;
  const run = ++unsortedRun;
  if (!state.me?.archivar) {
    app.replaceChildren(header(), h("main", { class: "list" },
      h("h1", {}, "Přetřídit"),
      h("p", {}, "Složku přetřídit spravuje jen archivář a admin.")));
    return;
  }
  app.replaceChildren(header(), h("main", { class: "list" }, "Načítám…"));
  if (!userName()) await askName();
  const own = new Map((await api(
    `/api/import?jmeno=${encodeURIComponent(userName())}`)
    .then((r) => r.importy).catch(() => []))
    .filter((it) => it.zdroj).map((it) => [it.zdroj, it]));
  const status = h("p", { class: "meta" }, "Načítám složky…");
  const tbody = h("tbody");
  const rows = new Map();
  app.replaceChildren(header(), h("main", { class: "list" },
    h("div", { class: "row" }, h("a", { href: listLink() }, "← Akce"),
      h("h1", {}, "Přetřídit")),
    h("p", { class: "notice" }, `Složky první úrovně ${UNSORTED} v kořeni ` +
      "archivu. Import složky soubory do akce přesune; duplicity, " +
      "blokované a nepodporované zůstanou ve složce. Podsložky s příponou " +
      ".ignored se přeskočí."),
    status,
    h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Složka"),
        h("th", {}, "Souborů"), h("th", {}, "Podsložky"),
        h("th", {}, "Data z EXIF"), h("th", {}, "Z názvu"),
        h("th", {}, "Navržená akce"), h("th"))),
      tbody)));
  const fill = (row, it) => {
    row.dates.textContent = it.od ? (it.od === it.do ? fmtDate(it.od)
      : `${fmtDate(it.od)} – ${fmtDate(it.do)}`) : "nezjištěno";
    row.navrh = it.navrh.akce;
    row.proposal.replaceChildren(it.navrh.akce ? h("code", {}, it.navrh.akce)
      : h("span", { class: "meta" }, "bez data – doplníte v průvodci"));
  };
  const addRows = (items) => {
    for (const it of items) {
      const mine = own.get(it.nazev);
      const z = it.z_nazvu;
      const row = { dates: h("td", { class: "meta" }, "…"),
        proposal: h("td", { class: "meta" }, "…"),
        navrh: z.datum ? `${z.datum} ${it.nazev}` : null };
      const button = h("button", { onclick: () =>
        importFromSource(it.nazev, row.navrh, button) },
      mine ? "Pokračovat v importu" : "Importovat");
      rows.set(it.nazev, row);
      tbody.append(h("tr", { class: mine ? "mine" : "" },
        h("td", {}, it.nazev, mine ? h("span", { class: "badge" },
          " rozpracovaný import") : null),
        h("td", {}, countsText(it.pocty),
          h("span", { class: "meta" }, ` · ${fmtSize(it.velikost)}`)),
        h("td", {}, it.podslozky.length ? it.podslozky.join(", ")
          : h("span", { class: "meta" }, "—")),
        row.dates,
        h("td", {}, z.datum ? fmtDate(z.datum) : z.rok ? `rok ${z.rok}`
          : h("span", { class: "meta" }, "—")),
        row.proposal,
        h("td", {}, button)));
    }
  };
  try {
    await apiStream("/api/pretridit", null, (ev) => {
      if (run !== unsortedRun || state.mode !== "pretridit") return;
      if (ev.typ === "vypis") {
        addRows(ev.slozky);
        status.textContent = ev.slozky.length
          ? `${plural(ev.slozky.length, "složka", "složky", "složek")}; ` +
            "čtu data z EXIF…"
          : `Složka ${UNSORTED} je prázdná nebo v archivu není.`;
      } else if (ev.typ === "slozka") {
        const row = rows.get(ev.nazev);
        if (row) fill(row, ev);
        status.textContent = ev.hotovo === ev.celkem
          ? plural(ev.celkem, "složka", "složky", "složek")
          : `Čtu data z EXIF: ${ev.hotovo} z ${ev.celkem}`;
      }
    });
  } catch (err) {
    if (run === unsortedRun) {
      status.textContent = `Přehled nejde načíst: ${err.message}`;
    }
  }
}

// --- otevření akce --------------------------------------------------------

// `finish`: kontrolní stránka dokončení (`#/akce/<název>/dokonceni`).
async function openEvent(name, finish = false) {
  // Plocha ↔ kontrolní stránka: stav akce, zámek i heartbeat zůstávají.
  if (name === state.name && state.doc && !state.detail?.novy &&
      (state.mode === "workspace" || state.mode === "finish")) {
    if (finish) renderFinish();
    else showWorkspace();
    return;
  }
  Object.assign(state, {
    name, detail: null, doc: null, version: null, mode: null,
    sel: new Set(), group: null, anchor: null, dirty: false,
    conflict: false, view: "grid", current: null, readonly: null,
    placeOpen: null, exporting: false, exportVersion: null, exportNote: "",
    exportStale: true, exportErrors: [], finishResult: null,
    immich: null,
  });
  // Stav akce se mohl změnit u jiného uživatele.
  const events = state.events = await api("/api/akce");
  const entry = events.find((e) => e.nazev === name);
  if (!entry) {
    app.replaceChildren(header(), h("main", {}, "Akce nenalezena."));
    return;
  }
  // Stav v Immichi z výpisu akcí (ze `.work/`, bez dotazu na Immich);
  // při záznamu doplníme i počty osob (`/immich` čte jen `.work/`).
  state.immich = entry.immich || null;
  if (entry.immich) await loadImmichStav(name);
  if (entry.stav === "kolize") {
    app.replaceChildren(header(), h("main", {}, KOLIZE));
    return;
  }
  if (!userName()) await askName();
  if (name !== state.name) return; // mezitím jinam
  if (entry.upravit === false) state.readonly = NO_RIGHTS;
  else await acquireLock(name);
  if (state.readonly) {
    await loadDetail();
    state.dirty = false;
    if (state.detail.novy) {
      toWorkspaceUrl(finish);
      state.mode = "wizard";
      renderReadonlyWizard();
    } else if (finish) {
      renderFinish();
    } else {
      showWorkspace();
    }
    return;
  }
  if (entry.stav === "nezpracovano") {
    toWorkspaceUrl(finish);
    state.mode = "wizard";
    wizard.step = 0;
    wizard.volby = {};
    wizard.rawRoot = true;
    wizard.other = true;
    renderWizard();
  } else {
    await loadDetail();
    if (state.doc && state.detail.novy) {
      toWorkspaceUrl(finish);
      state.mode = "wizard";
      wizard.step = 1;
      renderWizard();
    } else if (finish) {
      renderFinish();
    } else {
      showWorkspace();
    }
  }
}

// Kontrolní stránka nezpracované akce = plocha s průvodcem (bez
// záznamu v historii, zpět vede tam, odkud uživatel přišel).
function toWorkspaceUrl(finish) {
  if (finish) history.replaceState(null, "", eventHash(state.name));
}

function eventHash(name, finish = false) {
  return `#/akce/${encodeURIComponent(name)}${finish ? "/dokonceni" : ""}`;
}

// Plocha akce; provede nápravu vybranou na kontrolní stránce.
function showWorkspace() {
  state.mode = "workspace";
  renderWorkspace();
  const fix = state.pendingFix;
  state.pendingFix = null;
  if (fix) fix();
}

async function loadDetail() {
  app.replaceChildren(header(), h("main", { class: "loading" },
    "Načítám soubory a metadata (exiftool, první načtení může trvat)…"));
  const d = await api(eventUrl(state.name));
  state.detail = d;
  state.doc = d.metadata;
  state.version = d.version;
  state.present = new Set(d.soubory.map((f) => f.nazev));
  state.scan = Object.fromEntries(d.soubory.map((f) => [f.nazev, f]));
  state.exportVersion = d.export.version;
  state.exportNote = checkNote(d.export.kontrola);
  // Chybějící kontrola (nová akce, selhání) = neověřeno.
  const k = d.export.kontrola;
  state.exportStale = !k || k.zapsano + k.chyby.length > 0 ||
    (d.export.version !== null && d.export.version !== d.version);
  if (!d.novy && d.nove.length) state.dirty = true;
}

// --- ukládání ------------------------------------------------------------

const scheduleSave = debounce(() => save(), 1500);

function changed(opts = {}) {
  state.dirty = true;
  if (state.mode === "workspace") {
    setStatus();
    scheduleSave();
    renderBar();
    if (opts.grid) renderGrid();
    else renderNav();
  }
}

function setStatus(text) {
  const el = document.getElementById("save-status");
  if (!el) return;
  if (text) el.textContent = text;
  else if (state.readonly) el.textContent = "Jen ke čtení";
  else if (state.conflict) el.textContent = "Neuloženo – konflikt";
  else if (state.saving) el.textContent = "Ukládám…";
  else if (state.dirty) el.textContent = "Neuloženo";
  else el.textContent = "Uloženo";
  el.className = state.conflict ? "status error" :
    state.dirty || state.saving ? "status pending" : "status";
  renderExportStatus();
}

async function save() {
  if (state.conflict || !state.doc || state.readonly) return;
  // Export mění verzi na serveru; uloží se až po něm.
  if (state.saving || state.exporting) {
    state.dirty = true;
    return;
  }
  state.saving = true;
  state.dirty = false;
  setStatus();
  const name = state.name;
  try {
    const r = await api(eventUrl(name, "/metadata"), {
      method: "PUT",
      body: { metadata: savedDoc(state.doc), version: state.version,
        relace: session() },
    });
    if (name === state.name) {
      state.version = r.version;
      if (r.version !== state.exportVersion) {
        state.exportStale = true;
        state.exportNote = "neexportované změny";
        renderExportStatus();
      }
    }
    for (const n of collectNames(state.doc)) state.sessionNames.add(n);
  } catch (err) {
    state.dirty = true;
    if (err.status === 409) {
      state.conflict = true;
      conflictDialog();
    } else if (deniedLock(err) && name === state.name) {
      state.readonly = deniedLock(err);
      state.locked = null;
      clearInterval(heartbeatTimer);
      lostLock();
    } else {
      setStatus(`Chyba ukládání: ${err.message}`);
    }
  } finally {
    state.saving = false;
  }
  setStatus();
  if (state.dirty && !state.conflict) scheduleSave();
}

function conflictDialog() {
  const dialog = h("dialog", { class: "conflict" },
    h("h2", {}, "Soubor se změnil jinde"),
    h("p", {}, "_metadata.json této akce mezitím změnil jiný program nebo " +
      "uživatel. Uložení bylo odmítnuto, nic se nepřepsalo."),
    h("p", {}, "Znovunačtení zahodí změny provedené tady od posledního " +
      "uložení."),
    h("div", { class: "buttons" },
      h("button", {
        class: "primary",
        onclick: async () => {
          dialog.close();
          dialog.remove();
          state.dirty = false;
          state.conflict = false;
          await loadDetail();
          state.mode = "workspace";
          renderWorkspace();
        },
      }, "Znovu načíst"),
      h("button", {
        onclick: () => { dialog.close(); dialog.remove(); },
      }, "Zavřít (zatím neukládat)")));
  document.body.append(dialog);
  dialog.showModal();
}

// Dokument k uložení: bez `obliceje` (zapisuje je jen synchronizace
// z Immiche, server je vezme z uložené verze) a bez starších `osoby`.
function savedDoc(doc) {
  const copy = structuredClone(doc);
  const records = [copy.akce || {}, ...Object.values(copy.skupiny || {}),
    ...Object.values(copy.soubory || {})];
  for (const r of records) {
    delete r.obliceje;
    delete r.osoby;
  }
  return copy;
}

function collectNames(doc) {
  const out = new Set();
  const records = [doc.akce || {}, ...Object.values(doc.skupiny || {}),
    ...Object.values(doc.soubory || {})];
  for (const r of records) {
    for (const k of ["autori", "ucastnici"]) {
      for (const n of r[k] || []) out.add(n);
    }
    for (const f of r.obliceje || []) if (f.jmeno) out.add(f.jmeno);
  }
  return out;
}

// --- operace se skupinami --------------------------------------------------

function groupIds() {
  return Object.keys(state.doc.skupiny || {});
}

function groupName(gid) {
  return state.doc.skupiny[gid]?.nazev || gid;
}

// Existující skupina cíle v popisu importu: jen ke čtení (údaje se
// nemění), soubory do ní jde jen zařadit.
function fixedGroup(gid) {
  return state.mode === "import" && !!imp.defaults?.existujici?.[gid];
}

function moveFiles(files, gid) {
  for (const f of files) {
    if (gid) state.doc.soubory[f].skupina = gid;
    else delete state.doc.soubory[f].skupina;
  }
}

function newGroup(name, files) {
  const base = slug(name);
  let gid = base;
  for (let n = 2; state.doc.skupiny[gid]; n++) gid = `${base}-${n}`;
  state.doc.skupiny[gid] = { nazev: name };
  moveFiles(files, gid);
  return gid;
}

// Skupina, která po přesunu zůstala prázdná: bez vlastních údajů se smaže
// hned, s údaji (autoři apod.) se uživatel zeptá.
function dropEmptyGroups(done) {
  const used = new Set(Object.values(state.doc.soubory).map((r) => r.skupina));
  const ask = [];
  for (const gid of groupIds()) {
    if (used.has(gid) || state.keptEmpty.has(gid) || fixedGroup(gid)) {
      continue;
    }
    const own = Object.keys(state.doc.skupiny[gid])
      .filter((k) => k !== "nazev" && k !== "pristroj");
    if (own.length) ask.push(gid);
    else delete state.doc.skupiny[gid];
  }
  done();
  if (!ask.length) return;
  const close = (drop) => {
    for (const gid of ask) {
      if (drop) delete state.doc.skupiny[gid];
      else state.keptEmpty.add(gid);
    }
    dialog.close();
    dialog.remove();
    done();
  };
  const dialog = h("dialog", { class: "conflict" },
    h("h2", {}, "Prázdná skupina"),
    h("p", {}, ask.length === 1 ? "Skupina " : "Skupiny ",
      ask.map((g) => `„${groupName(g)}“`).join(", "),
      " už nemá žádné soubory, ale má zadané údaje (např. autory)."),
    h("div", { class: "buttons" },
      h("button", { class: "primary", onclick: () => close(true) },
        "Smazat"),
      h("button", { onclick: () => close(false) }, "Ponechat")));
  document.body.append(dialog);
  dialog.showModal();
}

function mergeGroup(src, dst) {
  for (const record of Object.values(state.doc.soubory)) {
    if (record.skupina === src) record.skupina = dst;
  }
  delete state.doc.skupiny[src];
}

function groupTools(afterChange) {
  // Nástroje pro výběr souborů: přesun do skupiny a nová skupina.
  const files = [...state.sel];
  if (!files.length) return null;
  const target = h("select", {},
    h("option", { value: "" }, "— bez skupiny —"),
    groupIds().map((g) => h("option", { value: g }, groupName(g))));
  const nameInput = h("input", { placeholder: "název nové skupiny" });
  const back = state.mode === "import" && files.every(excludedFile);
  return h("fieldset", { class: "tools" },
    h("legend", {}, `Skupina (${plural(files.length, "soubor", "soubory",
      "souborů")})`),
    state.mode === "import" ? h("div", { class: "row" }, h("button", {
      title: "Del", onclick: toggleExcluded,
    }, back ? "Vrátit do importu" : "Vyloučit z importu")) : null,
    h("div", { class: "row" }, target,
      h("button", {
        onclick: () => {
          moveFiles(files, target.value);
          dropEmptyGroups(afterChange);
        },
      }, "Přesunout")),
    h("div", { class: "row" }, nameInput,
      h("button", {
        onclick: () => {
          const name = nameInput.value.trim();
          if (!name) return nameInput.focus();
          newGroup(name, files);
          dropEmptyGroups(afterChange);
        },
      }, "Nová skupina z výběru")));
}

function mergeTools(gid, afterChange) {
  const others = groupIds().filter((g) => g !== gid && !fixedGroup(g));
  if (!others.length) return null;
  const target = h("select", {},
    others.map((g) => h("option", { value: g }, groupName(g))));
  return h("div", { class: "row" }, "Sloučit do ", target,
    h("button", {
      onclick: () => {
        mergeGroup(gid, target.value);
        state.group = target.value;
        afterChange();
      },
    }, "Sloučit"));
}

// --- mřížka a výběr --------------------------------------------------------

// Datum souboru; popis importu technické údaje nenese, bere se ze skenu.
function fileDate(f) {
  return resolve(state.doc, f).datum?.hodnota ||
    (state.mode === "import" ? state.scan[f]?.datum : null);
}

function sortedFiles(names) {
  return names.sort((a, b) => {
    const da = fileDate(a) || "";
    const db = fileDate(b) || "";
    return da < db ? -1 : da > db ? 1 : a.localeCompare(b);
  });
}

// Zobrazení podle data jen na pracovní ploše; průvodce vždy po skupinách.
function dateLayout() {
  return state.mode === "workspace" && state.layout === "datum";
}

// --- značky dlaždic ----------------------------------------------------------
//
// Pruh z barev výsledných autorů souboru (v obou zobrazeních). Barvy
// jsou z palety `--p0…--p7` v CSS podle pořadí osoby v akci. Značka =
// `{ stops, title, label }`; `stops` jsou zarážky gradientu pruhu,
// `null` = bez autorů (šrafování).

const PALETTE = 8;
const color = (i) => `var(--p${i % PALETTE})`;

function surname(name) {
  return name.split(",")[0].trim();
}

function dot(c) {
  return h("i", { class: "dot", style: `--c: ${c}` });
}

// Výsledná jména autorů souboru.
function authorsOf(f) {
  return (resolve(state.doc, f).autori?.hodnota || [])
    .filter((n) => typeof n === "string" && n.trim());
}

// Barva osoby podle klíče jména (stejná pro všechny soubory akce).
function personColors() {
  const people = personIndex(
    Object.keys(state.doc.soubory).flatMap(authorsOf), nameKey);
  return (key) => color(people.get(key));
}

// Funkce soubor → značka (nebo null) pro aktuální zobrazení.
function markFn() {
  if (state.mode !== "workspace") return () => null;
  const colorOf = personColors();
  return (f) => {
    if (discarded(f)) return null;
    const names = authorsOf(f);
    if (!names.length) {
      return { stops: null, title: "bez autorů", label: ["bez autorů"] };
    }
    const colors = names.map((n) => colorOf(nameKey(n)));
    // Jména se zalamují jen mezi sebou, ne uvnitř.
    const label = names.slice(0, 3).flatMap((n, i) =>
      [i ? " " : "", h("span", { class: "an" }, dot(colors[i]), surname(n))]);
    if (names.length > 3) label.push(` +${names.length - 3}`);
    return { stops: stripeStops(colors), title: names.join("; "), label };
  };
}

// Třídy a atributy dlaždice se značkou.
function markAttrs(mark, f) {
  if (!mark) return { cls: "", title: f, style: null };
  return {
    cls: mark.stops ? " mark" : " mark noauth",
    title: `${f} · ${mark.title}`,
    style: mark.stops ? `--stops: ${mark.stops}` : null,
  };
}

// Oddíl: `key` jednoznačně v rámci zobrazení, `gid` jen u skupiny. Na
// pracovní ploše navíc `info` (chybějící údaje a autoři, sectionInfo)
// a `stripe` (úseky pruhu autorů) pro navigátor.
function sections() {
  const secs = baseSections();
  if (state.mode !== "workspace") return secs;
  const m = missing(state.doc, state.present);
  const colorOf = personColors();
  const opts = { authorsOf, keyOf: nameKey,
    counted: (f) => state.present.has(f) && !discarded(f) };
  for (const s of secs) {
    s.info = sectionInfo(s, m, opts);
    s.stripe = stripeSegments(s.info.autori, s.info.bezAutoru.length,
      colorOf);
  }
  return secs;
}

function baseSections() {
  if (dateLayout()) {
    const dateOf = (f) => resolve(state.doc, f).datum?.hodnota;
    return byDay(Object.keys(state.doc.soubory), dateOf).map((s) => ({
      gid: null, key: `d:${s.day || ""}`,
      title: s.day ? dayLabel(s.day) : "Bez data", files: s.files,
    }));
  }
  const byGroup = new Map(groupIds().map((g) => [g, []]));
  const none = [];
  for (const [f, r] of Object.entries(state.doc.soubory)) {
    if (r.skupina && byGroup.has(r.skupina)) byGroup.get(r.skupina).push(f);
    else none.push(f);
  }
  const result = [...byGroup]
    .filter(([gid, files]) => files.length || !fixedGroup(gid))
    .map(([gid, files]) => ({ gid, key: `g:${gid}`, title: groupName(gid),
      files: sortedFiles(files) }));
  if (none.length) {
    result.push({ gid: null, key: "g:", title: "Bez skupiny",
      files: sortedFiles(none) });
  }
  return result;
}

function tile(f, markOf) {
  const info = state.scan[f] || {};
  const present = state.present.has(f);
  const datum = fileDate(f);
  const mark = markOf(f);
  const m = markAttrs(mark, f);
  const d = damagedAttrs(f);
  const thumb = present
    ? h("img", {
      src: thumbUrl(f), loading: "lazy", alt: "", draggable: false,
      onerror: (e) => e.target.replaceWith(
        h("div", { class: "ph" }, info.video ? "▶ video" : "bez náhledu")),
    })
    : h("div", { class: "ph" }, "chybí v kořeni");
  const ws = state.mode === "workspace";
  // Dlaždice jsou na tabulátor i ve skupinovém kroku (pohyb klávesnicí).
  const tabulator = ws || state.mode === "wizard" || state.mode === "import";
  const text = [h("span", { class: "fn" }, f),
    h("span", { class: "dt" }, datum ? datum.replace("T", " ") : "bez data"),
    mark && h("span", { class: "gn" }, mark.label)];
  return h("div", {
    class: `tile${present ? "" : " missing"}${info.video ? " video" : ""}` +
      `${state.sel.has(f) ? " selected" : ""}` +
      `${f === state.current ? " current" : ""}` +
      `${discarded(f) ? " discard" : ""}` +
      `${excludedFile(f) ? " excluded" : ""}` +
      d.cls + m.cls,
    dataset: { file: f }, title: d.title || m.title, style: m.style,
    tabindex: tabulator ? 0 : null,
    draggable: ws && !state.readonly ? "true" : null,
  }, thumb,
  // Plocha: bez popisku, ikony v rohu a překryv při najetí či fokusu.
  ws ? [tileFlags(f, datum), h("div", { class: "ov" }, text)]
    : [excludedFile(f) ? h("span", { class: "flags" },
      h("span", { title: "vyloučeno z importu" }, icon("vyloucit"))) : null,
    h("div", { class: "cap" }, text)]);
}

// Ikony v rohu dlaždice plochy: k vyřazení, jinak bez data a bez místa
// (jen když má akce víc míst).
function tileFlags(f, datum) {
  const flag = (name, title) => h("span", { title }, icon(name));
  let flags;
  if (discarded(f)) flags = [flag("vyradit", "k vyřazení")];
  else {
    const viceMist = (state.doc.akce?.mista || []).length > 1;
    flags = [!datum && flag("datum", "bez data"),
      viceMist && isEmpty(resolve(state.doc, f).misto?.hodnota) &&
        flag("misto", "bez místa")].filter(Boolean);
  }
  return flags.length ? h("span", { class: "flags" }, flags) : null;
}

function renderGrid() {
  const grid = document.getElementById("grid");
  if (!grid) return;
  const secs = sections();
  const markOf = markFn();
  state.order = secs.flatMap((s) => s.files);
  state.secOf = new Map(secs.flatMap((s) => s.files.map((f) => [f, s.key])));
  const ws = state.mode === "workspace";
  const tiles = (s) => h("div", { class: "tiles" },
    s.files.map((f) => tile(f, markOf)));
  // Plocha: oddíly jen s předělem, název a výběr oddílu nese navigátor;
  // průvodce si hlavičky nechává.
  const nodes = ws
    ? secs.filter((s) => s.files.length).map((s) =>
      h("section", { class: "section", dataset: { key: s.key } }, tiles(s)))
    : secs.map((s) => h("section", {},
      h("h3", {
        class: `ghead${s.gid && state.group === s.gid ? " selected" : ""}`,
        dataset: { group: s.gid || "", key: s.key },
      }, s.title, h("span", { class: "count" }, ` ${s.files.length}`)),
      tiles(s)));
  const scroll = grid.scrollTop;
  grid.replaceChildren(...nodes, h("div", { id: "band", hidden: true }));
  grid.scrollTop = scroll;
  renderFilm(secs);
  if (ws) {
    observeSections(grid);
    renderNav(secs);
  }
}

// Oddíly, které jsou v mřížce aspoň zčásti vidět (okraj v navigátoru).
let sectionObserver = null;

function observeSections(grid) {
  sectionObserver?.disconnect();
  state.visible = new Set();
  sectionObserver = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) state.visible.add(e.target.dataset.key);
      else state.visible.delete(e.target.dataset.key);
    }
    markVisible();
  }, { root: grid });
  for (const el of grid.querySelectorAll(".section")) {
    sectionObserver.observe(el);
  }
}

function scrollToSection(key) {
  document.querySelector(`#grid .section[data-key="${CSS.escape(key)}"]`)
    ?.scrollIntoView({ block: "start" });
}

// Vybere soubory (první aktuální) a v mřížce na ně posune.
function selectFiles(list) {
  state.anchor = list[0];
  state.current = list[0];
  select(new Set(list), null);
  if (state.view === "grid") {
    document.querySelector(`#grid .tile[data-file="${CSS.escape(list[0])}"]`)
      ?.scrollIntoView({ block: "center" });
  }
}

// Lupa: soubor aktuálním a jediným vybraným (pás ho ukáže).
function jumpTo(f) {
  if (!f) return;
  state.current = f;
  state.anchor = f;
  select(new Set([f]), null);
}

function select(files, group, opts = {}) {
  state.sel = files;
  state.group = group;
  for (const el of document.querySelectorAll("#grid .tile, #film .ftile")) {
    el.classList.toggle("selected", files.has(el.dataset.file));
  }
  markCurrent();
  for (const el of document.querySelectorAll("#grid .ghead, #film .fhead")) {
    el.classList.toggle("selected", !!group && el.dataset.group === group);
  }
  markNav();
  if (state.view === "loupe") renderBig();
  if (!opts.keepPanel) {
    state.placeOpen = opts.place ?? null;
    renderPanel();
  }
}

// Přepne třídu `current` na dlaždicích mřížky i pásu podle
// `state.current` (bez překreslení panelu).
function markCurrent() {
  for (const el of document.querySelectorAll("#grid .tile, #film .ftile")) {
    el.classList.toggle("current", el.dataset.file === state.current);
  }
}

function range(a, b) {
  const i = state.order.indexOf(a);
  const j = state.order.indexOf(b);
  return state.order.slice(Math.min(i, j), Math.max(i, j) + 1);
}

// Klik na soubor v mřížce i v pásu: klik, Ctrl, Shift; nastaví aktuální.
function clickFile(f, e) {
  const add = e.ctrlKey || e.metaKey;
  state.current = f;
  if (e.shiftKey && state.anchor && state.order.includes(state.anchor)) {
    select(new Set([...(add ? state.sel : []), ...range(state.anchor, f)]),
      null);
    return;
  }
  const next = new Set(add ? state.sel : []);
  if (add && next.has(f)) next.delete(f);
  else next.add(f);
  state.anchor = f;
  select(next, null);
}

function clickGroupHead(head) {
  const gid = head.dataset.group;
  if (gid) select(new Set(), gid);
  // Den a „Bez skupiny“/„Bez data“ nemají skupinu; vyberou soubory oddílu.
  else {
    const key = head.dataset.key;
    select(new Set(sections().find((s) => s.key === key)?.files || []), null);
  }
}

function setupGrid(grid) {
  grid.addEventListener("click", (e) => {
    if (grid.dataset.dragged) {
      delete grid.dataset.dragged;
      return;
    }
    const head = e.target.closest(".ghead");
    if (head) return clickGroupHead(head);
    const t = e.target.closest(".tile");
    if (t) clickFile(t.dataset.file, e);
    else if (!e.target.closest("details")) select(new Set(), null);
  });

  // Klávesnice: fokus dlaždice ji udělá aktuální bez změny výběru
  // ani kotvy; při kliknutí přijde focusin před click a clickFile
  // nastaví totéž.
  grid.addEventListener("focusin", (e) => {
    const t = e.target.closest(".tile");
    if (!t || !state.order.includes(t.dataset.file)) return;
    state.current = t.dataset.file;
    markCurrent();
  });

  // Přesun do skupiny: tažení dlaždice na řádek skupiny v navigátoru.
  grid.addEventListener("dragstart", (e) => {
    const t = e.target.closest?.(".tile");
    if (!t || state.mode !== "workspace" || state.readonly) {
      e.preventDefault();
      return;
    }
    const f = t.dataset.file;
    dragFiles = state.sel.has(f) ? [...state.sel] : [f];
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", dragFiles.join("\n"));
    document.getElementById("nav")?.classList.add("dragging");
  });
  grid.addEventListener("dragend", endDrag);

  grid.addEventListener("dblclick", (e) => {
    const t = e.target.closest(".tile");
    if (!t || state.mode !== "workspace") return;
    state.current = t.dataset.file;
    setView("loupe");
  });

  // Výběr tažením: začíná mimo dlaždici i hlavičku.
  grid.addEventListener("mousedown", (e) => {
    if (e.button !== 0 || e.target.closest(".tile, .ghead, details")) return;
    const band = document.getElementById("band");
    const origin = grid.getBoundingClientRect();
    const x0 = e.clientX, y0 = e.clientY;
    const base = e.ctrlKey || e.metaKey ? new Set(state.sel) : new Set();
    let active = false;
    const move = (ev) => {
      const x1 = ev.clientX, y1 = ev.clientY;
      if (!active && Math.abs(x1 - x0) + Math.abs(y1 - y0) < 6) return;
      active = true;
      const r = {
        left: Math.min(x0, x1), right: Math.max(x0, x1),
        top: Math.min(y0, y1), bottom: Math.max(y0, y1),
      };
      Object.assign(band.style, {
        left: `${r.left - origin.left + grid.scrollLeft}px`,
        top: `${r.top - origin.top + grid.scrollTop}px`,
        width: `${r.right - r.left}px`, height: `${r.bottom - r.top}px`,
      });
      band.hidden = false;
      const next = new Set(base);
      for (const el of grid.querySelectorAll(".tile")) {
        const b = el.getBoundingClientRect();
        if (b.left < r.right && b.right > r.left && b.top < r.bottom &&
            b.bottom > r.top) next.add(el.dataset.file);
      }
      select(next, null, { keepPanel: true });
    };
    const up = () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
      band.hidden = true;
      if (active) {
        grid.dataset.dragged = "1";
        renderPanel();
      }
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    e.preventDefault();
  });
}

// --- navigátor akce ---------------------------------------------------------
//
// Řádek Akce a řádek pro každý oddíl mřížky (`sections()`): název,
// počet, pruh autorů a chybějící údaje. Kreslí se z dat oddílů, takže
// funguje i v lupě, kde je mřížka skrytá.

const AKCE_POLE = { nazev: "název", datum_od: "datum od",
  datum_do: "datum do" };
// Chybějící údaje oddílu: klíč v `info` (sectionInfo), ikona, popis.
const NAV_MISS = [
  ["bezAutoru", "osoba", "bez autorů"],
  ["bezData", "datum", "bez data"],
  ["bezMista", "misto", "bez místa"],
  ["bezSkupiny", "skupina", "bez skupiny"],
];

let dragFiles = null; // soubory tažené z mřížky

function endDrag() {
  dragFiles = null;
  const nav = document.getElementById("nav");
  nav?.classList.remove("dragging");
  for (const r of nav?.querySelectorAll(".drop") || []) {
    r.classList.remove("drop");
  }
}

const nFiles = (n) => plural(n, "soubor", "soubory", "souborů");

function renderNav(secs) {
  const nav = document.getElementById("nav");
  if (!nav || state.mode !== "workspace") return;
  state.navSecs = secs ?? sections();
  const m = state.navMissing = missing(state.doc, state.present);
  const places = Object.keys(m.mistaBezSouradnic)
    .sort((a, b) => a.localeCompare(b, "cs"));
  const nepoj = state.immich?.album && Array.isArray(state.immich.osoby)
    ? state.immich.osoby[1] - state.immich.osoby[0] : 0;
  const akceMiss = [
    m.akce.length ? h("span", { class: "nm strong" },
      `chybí ${m.akce.map((k) => AKCE_POLE[k]).join(", ")}`) : null,
    nepoj > 0 ? h("button", { class: "nm", dataset: { osoby: "1" },
      title: plural(nepoj, "nepojmenovaná osoba", "nepojmenované osoby",
        "nepojmenovaných osob"),
      "aria-label": plural(nepoj, "nepojmenovaná osoba",
        "nepojmenované osoby", "nepojmenovaných osob") },
    icon("osoba"), String(nepoj)) : null,
    ...places.map((misto) => h("button", { class: "nm",
      dataset: { place: misto },
      title: `${misto}: ${nFiles(m.mistaBezSouradnic[misto].length)} bez ` +
        "GPS, souřadnice místa nejsou rozhodnuté",
    }, icon("souradnice"), misto)),
  ].filter(Boolean);
  const scroll = nav.scrollTop;
  nav.replaceChildren(
    h("div", { class: "nrow akce" },
      h("button", { class: "nmain", title: "Upravit akci (zrušit výběr)" },
        h("span", { class: "nt" }, "Akce")),
      akceMiss.length ? h("div", { class: "nmiss" }, akceMiss) : null),
    ...state.navSecs.map(navRow));
  nav.scrollTop = scroll;
  markNav();
}

function navRow(s) {
  const i = s.info;
  const miss = [];
  if (i.skupinaBezAutoru) {
    miss.push(h("button", { class: "nm strong", dataset: { miss: "skupina" },
      title: "Skupina nemá autory" }, icon("osoba"), "bez autorů"));
  }
  for (const [k, name, label] of NAV_MISS) {
    const n = i[k].length;
    if (!n || (k === "bezAutoru" && i.skupinaBezAutoru)) continue;
    const text = `${nFiles(n)} ${label}`;
    miss.push(h("button", { class: "nm", dataset: { miss: k }, title: text,
      "aria-label": text }, icon(name), String(n)));
  }
  const who = [...i.autori.map((p) => `${p.name} ${p.count}`),
    i.bezAutoru.length ? `bez autorů ${i.bezAutoru.length}` : null]
    .filter(Boolean).join("; ");
  return h("div", { class: "nrow sec",
    dataset: s.gid ? { key: s.key, gid: s.gid } : { key: s.key } },
  h("button", { class: "nmain", title: s.title },
    h("span", { class: "nt" }, s.title),
    h("span", { class: "nc" }, String(s.files.length)),
    s.stripe.length ? h("span", { class: "nstripe", title: who },
      s.stripe.map((x) => h("i", { class: x.color ? null : "noauth",
        style: `flex-grow: ${x.count}` +
          (x.color ? `; background: ${x.color}` : "") }))) : null),
  miss.length ? h("div", { class: "nmiss" }, miss) : null);
}

// Vybraný oddíl: skupina podle `state.group`, den a „Bez …“ podle toho,
// že výběr jsou právě soubory oddílu.
function navSelected(s) {
  if (s.gid) return state.group === s.gid;
  return state.sel.size > 0 && s.files.length === state.sel.size &&
    s.files.every((f) => state.sel.has(f));
}

function markNav() {
  const nav = document.getElementById("nav");
  if (!nav) return;
  const secs = new Map(state.navSecs.map((s) => [s.key, s]));
  nav.querySelector(".nrow.akce")?.classList.toggle("selected",
    !state.sel.size && !state.group);
  for (const row of nav.querySelectorAll(".nrow.sec")) {
    const s = secs.get(row.dataset.key);
    row.classList.toggle("selected", !!s && navSelected(s));
  }
  markVisible();
}

// Okraj u oddílů, které jsou v mřížce vidět; v lupě u oddílu aktuálního
// souboru.
function markVisible() {
  const keys = state.view === "loupe"
    ? new Set([state.secOf.get(state.current)]) : state.visible;
  for (const row of document.querySelectorAll("#nav .nrow.sec")) {
    row.classList.toggle("visible", keys.has(row.dataset.key));
  }
}

function navSection(row) {
  return state.navSecs.find((s) => s.key === row.dataset.key);
}

// Klik na řádek: Akce zruší výběr; v mřížce skupina vybere skupinu,
// ostatní oddíly své soubory a mřížka na oddíl skočí; v lupě první
// soubor oddílu aktuálním a jediným vybraným.
function clickNavRow(row) {
  const s = navSection(row);
  if (!s) return select(new Set(), null);
  if (state.view === "loupe") return jumpTo(s.files[0]);
  if (s.gid) select(new Set(), s.gid);
  else select(new Set(s.files), null);
  scrollToSection(s.key);
}

// Klik na chybějící údaj: dotčené soubory; skupina bez autorů vybere
// skupinu (v lupě jen skok na její první soubor).
function clickMissing(row, kind) {
  const s = navSection(row);
  if (!s) return;
  if (kind !== "skupina") return selectFiles(s.info[kind]);
  if (state.view === "loupe") return jumpTo(s.files[0]);
  select(new Set(), s.gid);
  scrollToSection(s.key);
}

function setupNav(nav) {
  nav.addEventListener("click", (e) => {
    const row = e.target.closest(".nrow");
    if (!row) return;
    const place = e.target.closest("[data-place]")?.dataset.place;
    const miss = e.target.closest("[data-miss]")?.dataset.miss;
    const nepojmene = e.target.closest("[data-osoby]");
    if (place) openPlace(place, state.navMissing.mistaBezSouradnic[place]);
    else if (miss) clickMissing(row, miss);
    // Nepojmenované osoby: klik otevře nástroj (archivář/admin),
    // ostatním údaj jen ukazuje (bez zámku, `_metadata.json` nemění).
    else if (nepojmene) {
      if (state.me?.archivar) openNaming();
    } else clickNavRow(row);
  });
  // Tažení přijme jen řádek skutečné skupiny.
  const target = (e) => {
    const row = e.target.closest(".nrow");
    return dragFiles && !state.readonly && row?.dataset.gid ? row : null;
  };
  nav.addEventListener("dragover", (e) => {
    const row = target(e);
    for (const r of nav.querySelectorAll(".drop")) {
      if (r !== row) r.classList.remove("drop");
    }
    if (!row) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    row.classList.add("drop");
  });
  nav.addEventListener("drop", (e) => {
    const row = target(e);
    const moved = dragFiles;
    endDrag();
    if (!row) return;
    e.preventDefault();
    const gid = row.dataset.gid;
    if (moved.every((f) => state.doc.soubory[f].skupina === gid)) return;
    moveFiles(moved, gid);
    dropEmptyGroups(() => {
      changed({ grid: true });
      renderPanel();
    });
  });
}

// --- vyřazení --------------------------------------------------------------

function discarded(f) {
  return !!state.doc.soubory[f]?.vyradit;
}

// Poškozené soubory pro zobrazení: souhrn z detailu omezený na
// aktuální dokument (přepínače `overeno`/`vyradit` svítí hned).
function damagedOf(f) {
  return damagedMap(state.detail?.poskozene || {},
                    state.doc?.soubory || {})[f] || null;
}

// Poškozený soubor bez rozhodnutí (ani potvrzený, ani označený
// k vyřazení) — kvůli takovým se v liště nabízí Uklidit….
function damagedRepairable(f) {
  const info = (state.detail?.poskozene || {})[f];
  if (!info || !state.present.has(f)) return null;
  const record = state.doc?.soubory?.[f] || {};
  if (info.overeno || info.vyradit || record.overeno || record.vyradit) {
    return null;
  }
  return info;
}

// Dlaždice poškozeného souboru: odlišení + důvod v tooltipu.
function damagedAttrs(f) {
  const info = damagedOf(f);
  return info ? { cls: " damaged", title: damagedText(info) }
              : { cls: "", title: null };
}

// „Považovat za v pořádku“ / zrušení potvrzení (falešná pozitivita
// dekodéru); uloží se běžným autosave jako ostatní ruční údaje.
function toggleVerified() {
  const files = [...state.sel].filter((f) => state.doc.soubory[f]
    && (damagedOf(f) || state.doc.soubory[f].overeno));
  if (state.readonly || !files.length) return;
  const unmark = files.every((f) => state.doc.soubory[f].overeno);
  for (const f of files) {
    if (unmark) delete state.doc.soubory[f].overeno;
    else state.doc.soubory[f].overeno = true;
  }
  changed({ grid: true });
  renderPanel();
}

// Del a tlačítko: označí vybrané soubory k vyřazení; jsou-li už všechny
// označené, označení zruší.
function toggleDiscard() {
  const files = [...state.sel].filter((f) => state.doc.soubory[f]);
  if (state.readonly || !files.length) return;
  const unmark = files.every(discarded);
  for (const f of files) {
    if (unmark) delete state.doc.soubory[f].vyradit;
    else state.doc.soubory[f].vyradit = true;
  }
  changed({ grid: true });
  renderPanel();
}

// Úklid z pracovní plochy: označené soubory do `k_odstraneni.ignored`,
// ostatní soubory do `ostatni.ignored`, RAWy z kořene do `RAW.ignored`
// a podsložky podle volby v dialogu (bez volby zůstanou). Plán i provedení
// čtou označení z uloženého `_metadata.json`, proto se nejdřív uloží.
async function workspaceCleanup() {
  if (state.readonly || !(await flushSave())) return;
  const name = state.name;
  const volby = {};
  // Rozhodnutí u poškozených souborů (výlučné sloupce Vyřadit /
  // V pořádku). Žije jen v dialogu, zapíše se až při spuštění — Zrušit
  // nic nezmění. Výchozí je uložený stav; nerozhodnuté zůstanou, jak jsou.
  const damaged = Object.keys(state.detail?.poskozene || {})
    .filter((f) => state.present.has(f)).sort();
  const decisions = cleanupDecisions(damaged, state.detail?.poskozene,
    state.doc.soubory);
  // Označený k vyřazení už je v plánu serveru; zrušit jde jen z dlaždice.
  const lockedRows = new Set(damaged.filter(
    (f) => decisions[f] === "vyradit"));
  const body = () => ({ z_plochy: true, volby, relace: session() });
  const zapis = state.info.zapis;
  const main = h("div");
  const buttons = h("div", { class: "buttons" });
  const dialog = h("dialog", { class: "cleanup" },
    h("h2", {}, "Úklid kořene akce"), main, buttons);
  let done = false;
  const close = async () => {
    dialog.close();
    dialog.remove();
    if (!done || name !== state.name) return;
    // Server odstranil záznamy přesunutých souborů: načíst znovu.
    state.sel = new Set();
    state.group = null;
    await loadDetail();
    renderWorkspace();
  };
  dialog.addEventListener("cancel", (e) => {
    e.preventDefault();
    if (!dialog.dataset.busy) close();
  });
  const opsTable = (ops) => ops.length
    ? h("table", { class: "ops" }, ops.map(opRow))
    : h("p", {}, "Není co přesouvat.");
  const cancel = h("button", { onclick: close }, "Zavřít");
  const run = h("button", { class: "primary" });
  let todo = 0;
  // Tlačítko podle toho, co se stane: přesuny (jen produkční režim)
  // a změny potvrzení „v pořádku“; bez přesunů jen „Uložit“.
  const updateRun = () => {
    const ch = decisionChanges(decisions, state.doc.soubory);
    const moves = zapis ? todo + ch.vyradit.length : 0;
    const parts = [];
    if (moves) parts.push(plural(moves, "přesun", "přesuny", "přesunů"));
    if (ch.overeno.length) parts.push(`${ch.overeno.length}× v pořádku`);
    if (ch.zrusit.length) {
      parts.push(`${ch.zrusit.length}× zrušit potvrzení`);
    }
    run.textContent = `${moves ? "Provést úklid" : "Uložit"} ` +
      `(${parts.join(", ")})`;
    const work = parts.length > 0;
    cancel.textContent = work ? "Zrušit" : "Zavřít";
    buttons.replaceChildren(...(work ? [run] : []), cancel);
  };

  // Tabulka poškozených: náhled, soubor s důvodem, dva výlučné sloupce.
  // Vstupy se při změně jen přenastaví (náhledy se nenačítají znovu).
  const damagedTable = () => {
    if (!damaged.length) return null;
    const editable = (col) => damaged.filter((f) => !lockedRows.has(f)
      && !(col === "vyradit" && !zapis));
    const inputs = {};
    const head = {};
    const sync = () => {
      for (const f of damaged) {
        inputs[f].vyradit.checked = decisions[f] === "vyradit";
        inputs[f].overeno.checked = decisions[f] === "overeno";
      }
      for (const col of ["vyradit", "overeno"]) {
        const rows = editable(col);
        head[col].checked = rows.length > 0
          && rows.every((f) => decisions[f] === col);
        head[col].disabled = !rows.length;
      }
      updateRun();
    };
    const choose = (f, col, on) => {
      decisions[f] = on ? col : null;
      sync();
    };
    const box = (f, col) => h("input", {
      type: "checkbox",
      disabled: lockedRows.has(f) || (col === "vyradit" && !zapis),
      onchange: (e) => choose(f, col, e.target.checked),
    });
    const headBox = (col, label, title) => {
      head[col] = h("input", {
        type: "checkbox",
        onchange: (e) => {
          for (const f of editable(col)) {
            if (e.target.checked) decisions[f] = col;
            else if (decisions[f] === col) decisions[f] = null;
          }
          sync();
        },
      });
      return h("th", { class: "choice", title },
        h("label", {}, head[col], " ", label));
    };
    const rows = damaged.map((f) => {
      const info = state.detail.poskozene[f];
      inputs[f] = { vyradit: box(f, "vyradit"), overeno: box(f, "overeno") };
      const ph = () => h("span", { class: "ph" },
        state.scan[f]?.video ? "▶ video" : "bez náhledu");
      return h("tr", { class: lockedRows.has(f) ? "locked" : "" },
        h("td", { class: "thumb" }, h("img", {
          src: thumbUrl(f), loading: "lazy", alt: "",
          onerror: (e) => e.target.replaceWith(ph()),
        })),
        h("td", {}, h("div", { class: "fn" }, f),
          h("div", { class: "meta" }, damagedText(info)),
          lockedRows.has(f) ? h("div", { class: "meta" },
            "už označeno k vyřazení — zrušit jde v panelu dlaždice") : ""),
        h("td", { class: "choice" }, inputs[f].vyradit),
        h("td", { class: "choice" }, inputs[f].overeno));
    });
    const table = h("table", { class: "damaged" },
      h("thead", {}, h("tr", {}, h("th", {}), h("th", {}, "Soubor"),
        headBox("vyradit", "Vyřadit", zapis
          ? "Přesunout do k_odstraneni.ignored"
          : "Jen v produkčním režimu"),
        headBox("overeno", "V pořádku",
          "Soubor je v pořádku, kontrola se mýlí"))),
      h("tbody", {}, rows));
    sync();
    return [h("h3", {}, "Poškozené soubory"),
      h("p", { class: "notice" }, "U každého souboru vyberte nejvýš " +
        "jedno: Vyřadit (přesune se do k_odstraneni.ignored spolu " +
        "s ostatními, údaje zůstanou v sidecaru), nebo V pořádku " +
        "(kontrola se mýlí, soubor přestane být hlášený). Soubor bez " +
        "volby zůstane, jak je. Zapíše se až tlačítkem dole."),
      table];
  };

  const showPlan = async () => {
    let plan;
    try {
      plan = await api(eventUrl(name, "/uklid"),
        { method: "POST", body: body() });
    } catch (err) {
      main.replaceChildren(h("p", { class: "notice error" },
        `Plán úklidu nejde sestavit: ${err.message}`));
      buttons.replaceChildren(cancel);
      return;
    }
    if (name !== state.name) return;
    todo = plan.operace.filter((o) => !o.blocked).length;
    const damagedBlock = damagedTable();
    main.replaceChildren(
      h("p", { class: "notice" }, zapis
        ? "Označené soubory se přesunou do k_odstraneni.ignored a jejich " +
          "záznamy se odstraní z _metadata.json (údaje zůstanou " +
          "v sidecaru vedle souboru). Nepodporované soubory a osiřelé " +
          "sidecary jdou do ostatni.ignored, RAWy do RAW.ignored. " +
          "Podsložky jen podle volby níže. Nic se nepřepíše, " +
          "blokované přesuny se přeskočí."
        : "Nasucho: vývojový režim plán jen ukazuje, v archivu nic " +
          "nepřesune."),
      ...plan.podslozky.map((f) => folderChoice(f, (value) => {
        volby[f.nazev] = value;
        showPlan();
      })),
      plan.podslozky.length ? h("h3", {}, "Plán") : "",
      // Prázdný plán: „Není co přesouvat“ jen bez poškozených (ty se
      // přesunou až po označení při spuštění); pod nadpisem Plán
      // (akce s podsložkou) aspoň věta, ať nadpis nevisí.
      plan.operace.length || !damagedBlock ? opsTable(plan.operace)
        : plan.podslozky.length ? h("p", {}, "Zatím žádné přesuny; " +
          "poškozené soubory označené níže k vyřazení se přidají při " +
          "spuštění.") : "",
      ...(damagedBlock || []));
    updateRun();
  };

  run.onclick = async () => {
    dialog.dataset.busy = "1";
    run.disabled = cancel.disabled = true;
    main.querySelectorAll("input").forEach((i) => { i.disabled = true; });
    // Rozhodnutí u poškozených zapsat a hned uložit — provedení čte
    // `vyradit` z metadat. Ne přes changed(): jeho odložené uložení by
    // přišlo až po úklidu se starou verzí (409, konflikt na ploše).
    const ch = decisionChanges(decisions, state.doc.soubory);
    if (ch.vyradit.length || ch.overeno.length || ch.zrusit.length) {
      run.textContent = "Ukládám…";
      const revert = applyDecisionChanges(state.doc.soubory, ch);
      state.dirty = true;
      if (!(await flushSave()) || name !== state.name) {
        // Neuloženo: vrátit, ať dokument odpovídá serveru.
        revert();
        delete dialog.dataset.busy;
        cancel.disabled = false;
        run.remove();
        main.append(h("p", { class: "notice error" },
          "Volby u poškozených se nepodařilo uložit, nic se neprovedlo."));
        return;
      }
    }
    if (!(zapis && todo + ch.vyradit.length)) {
      // Jen potvrzení „v pořádku“ (nebo vývojový režim): hotovo.
      delete dialog.dataset.busy;
      done = true;
      return close();
    }
    run.textContent = "Přesouvám…";
    let result;
    try {
      result = await api(eventUrl(name, "/uklid/provest"),
        { method: "POST", body: body() });
    } catch (err) {
      delete dialog.dataset.busy;
      if (deniedLock(err)) {
        dialog.close();
        dialog.remove();
        state.readonly = deniedLock(err);
        state.locked = null;
        clearInterval(heartbeatTimer);
        return lostLock();
      }
      run.remove();
      cancel.disabled = false;
      main.append(h("p", { class: "notice error" },
        `Úklid selhal: ${err.message}`));
      return;
    }
    delete dialog.dataset.busy;
    done = true;
    const count = (st) => result.operace.filter((o) => o.stav === st).length;
    main.replaceChildren(
      h("p", { class: count("chyba") ? "notice error" : "notice" },
        `Hotovo ${count("hotovo")}, blokováno ${count("blokovano")}, ` +
        `chyba ${count("chyba")}. Neprovedené operace zůstaly beze změny ` +
        "(označené soubory i s označením)."),
      opsTable(result.operace));
    cancel.textContent = "Zavřít";
    cancel.disabled = false;
    run.remove();
  };
  main.append("Počítám plán úklidu…");
  buttons.append(cancel);
  document.body.append(dialog);
  dialog.showModal();
  await showPlan();
}

// --- lupa a filmový pás ----------------------------------------------------

function setView(view) {
  state.view = view;
  const loupe = view === "loupe";
  if (loupe && !state.order.includes(state.current)) {
    state.current = state.order.find((f) => state.sel.has(f)) ??
      state.order[0] ?? null;
  }
  if (!loupe) document.querySelector("#big video")?.pause();
  document.getElementById("grid").hidden = loupe;
  document.getElementById("loupe").hidden = !loupe;
  for (const b of document.querySelectorAll(".views button[data-view]")) {
    b.classList.toggle("active", b.dataset.view === view);
  }
  markVisible();
  if (loupe) {
    renderFilm();
    renderBig();
  } else if (state.current) {
    document.querySelector(
      `#grid .tile[data-file="${CSS.escape(state.current)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }
}

// Po skupinách / podle data. Výběr souborů a aktuální soubor zůstanou;
// vybraná hlavička skupiny v zobrazení podle data není, formulář přejde
// na akci.
function setLayout(layout) {
  state.layout = layout;
  localStorage.setItem("zobrazeni", layout);
  for (const b of document.querySelectorAll(".views button[data-layout]")) {
    b.classList.toggle("active", b.dataset.layout === layout);
  }
  if (layout === "datum" && state.group) {
    state.group = null;
    renderPanel();
  }
  renderGrid();
  if (state.view === "loupe") {
    // Pořadí se změnilo: popisek „i / n“ u velké fotky přepočítat.
    const big = document.getElementById("big");
    if (big) big.dataset.file = "";
    renderBig();
  } else if (state.current) {
    document.querySelector(
      `#grid .tile[data-file="${CSS.escape(state.current)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }
}

// Pohyb na soubor: bez Shiftu jediný vybraný s kotvou na něm, se
// Shiftem rozsah od kotvy (bez platné kotvy se jí stane výchozí
// soubor). V mřížce přesune fokus na dlaždici a posune ji; v lupě
// pás posune `revealCurrent` přes `select` → `renderBig`.
function moveTo(f, extend) {
  if (!f) return;
  const vychozi = state.current;
  state.current = f;
  if (extend) {
    if (!state.order.includes(state.anchor)) {
      state.anchor = state.order.includes(vychozi) ? vychozi : f;
    }
    select(new Set(range(state.anchor, f)), null);
  } else {
    state.anchor = f;
    select(new Set([f]), null);
  }
  if (state.view === "grid") {
    const el = document.querySelector(
      `#grid .tile[data-file="${CSS.escape(f)}"]`);
    el?.focus({ preventScroll: true });
    el?.scrollIntoView({ block: "nearest" });
  }
}

// Obdélníky dlaždic mřížky v pořadí `state.order`; DOM pořadí mu
// odpovídá (renderGrid), kdyby ne, mapujeme přes `data-file`.
function tileRects() {
  const els = [...document.querySelectorAll("#grid .tile")];
  const inOrder = els.length === state.order.length &&
    els.every((el, i) => el.dataset.file === state.order[i]);
  const ordered = inOrder
    ? els
    : state.order.map((f) => els.find((el) => el.dataset.file === f))
        .filter(Boolean);
  return ordered.map((el) => el.getBoundingClientRect());
}

// Kolik souborů se vejde na šířku pásu lupy (PageUp/PageDown). Krok
// dlaždice je rozestup dvou sousedních (šířka i s mezerou).
function krokPasu() {
  const film = document.getElementById("film");
  const [a, b] = document.querySelectorAll("#film .fsec .ftile");
  if (!film || !a) return 1;
  const ra = a.getBoundingClientRect();
  const rb = b?.getBoundingClientRect();
  const krok = rb && rb.left > ra.left ? rb.left - ra.left : ra.width;
  return naPas(film.clientWidth, krok);
}

// Cílový soubor klávesového pohybu; null když se má zůstat (prázdná
// mřížka, vodorovný pohyb mimo rozsah). Bez aktuálního souboru
// končí pohyb na prvním, End na posledním.
function cilPohybu(k, loupe) {
  const n = state.order.length;
  if (!n) return null;
  const i = state.order.indexOf(state.current);
  let j;
  if (i < 0) {
    j = k.druh === "kraj" && k.smer > 0 ? n - 1 : 0;
  } else if (k.druh === "vodorovne") {
    j = i + k.smer;
    if (j < 0 || j >= n) return null;
  } else if (k.druh === "kraj") {
    j = k.smer > 0 ? n - 1 : 0;
  } else if (loupe) {
    if (k.druh === "svisle") j = oddil(state.order, state.secOf, i, k.smer);
    else j = Math.min(n - 1, Math.max(0, i + k.smer * krokPasu()));
  } else if (k.druh === "svisle") {
    j = radek(tileRects(), i, k.smer);
  } else {
    j = stranka(tileRects(), i, k.smer,
      document.getElementById("grid").clientHeight);
  }
  return state.order[j];
}

function filmTile(f, markOf) {
  const info = state.scan[f] || {};
  const present = state.present.has(f);
  const m = markAttrs(markOf(f), f);
  const d = damagedAttrs(f);
  return h("div", {
    class: `ftile${present ? "" : " missing"}` +
      `${state.sel.has(f) ? " selected" : ""}` +
      `${discarded(f) ? " discard" : ""}` +
      `${f === state.current ? " current" : ""}` + d.cls + m.cls,
    dataset: { file: f }, title: d.title || m.title, style: m.style,
  }, present
    ? h("img", { src: thumbUrl(f), loading: "lazy", alt: "", draggable: false,
      onerror: (e) => e.target.replaceWith(
        h("span", { class: "ph" }, info.video ? "▶ video" : f)) })
    : h("span", { class: "ph" }, "chybí"));
}

function renderFilm(secs) {
  const film = document.getElementById("film");
  if (!film || state.view !== "loupe") return;
  const scroll = film.scrollLeft;
  const markOf = markFn();
  film.replaceChildren(...(secs || sections()).map((s) =>
    h("div", { class: "fsec" },
      h("div", {
        class: `fhead${s.gid && state.group === s.gid ? " selected" : ""}`,
        dataset: { group: s.gid || "", key: s.key }, title: s.title,
      }, s.title),
      s.files.map((f) => filmTile(f, markOf)))));
  film.scrollLeft = scroll;
  revealCurrent();
}

function revealCurrent() {
  if (!state.current) return;
  document.querySelector(
    `#film .ftile[data-file="${CSS.escape(state.current)}"]`)
    ?.scrollIntoView({ inline: "nearest", block: "nearest" });
}

function setupFilm(film) {
  film.addEventListener("click", (e) => {
    const head = e.target.closest(".fhead");
    if (head) return clickGroupHead(head);
    const t = e.target.closest(".ftile");
    if (t) clickFile(t.dataset.file, e);
  });
}

// Velká fotka: hned roztažený náhled 320 px, po načtení 1600 px.
function renderBig() {
  const big = document.getElementById("big");
  if (!big) return;
  revealCurrent();
  const f = state.current;
  if (big.dataset.file === (f || "")) return;
  big.dataset.file = f || "";
  if (!f) {
    big.replaceChildren(h("div", { class: "media" },
      h("span", { class: "ph" }, "Akce nemá soubory.")));
    return;
  }
  const info = state.scan[f] || {};
  const media = h("div", { class: "media" });
  const placeholder = (text) => h("span", { class: "ph" }, text);
  if (!state.present.has(f)) {
    media.append(placeholder("Soubor chybí v kořeni akce."));
  } else if (info.video) {
    const fallback = () => media.replaceChildren(
      h("img", { src: thumbUrl(f, LARGE), alt: "",
        onerror: (e) => e.target.replaceWith(placeholder("bez náhledu")) }),
      h("p", { class: "vmsg" },
        "Video nejde v prohlížeči přehrát (nepodporovaný formát)."));
    media.append(h("video", {
      src: eventUrl(state.name, `/soubor/${encodeURIComponent(f)}`),
      poster: thumbUrl(f, LARGE), controls: true, preload: "metadata",
      onerror: fallback,
      onloadedmetadata: (e) => { if (!e.target.videoWidth) fallback(); },
    }));
  } else {
    const img = h("img", { src: thumbUrl(f), alt: "", draggable: false,
      onerror: () => img.replaceWith(placeholder("bez náhledu")) });
    const large = new Image();
    large.onload = () => { if (big.dataset.file === f) img.src = large.src; };
    large.src = thumbUrl(f, LARGE);
    media.append(img);
  }
  const datum = resolve(state.doc, f).datum?.hodnota;
  const i = state.order.indexOf(f);
  big.replaceChildren(media, h("div", { class: "caption" },
    `${f} · ${datum ? datum.replace("T", " ") : "bez data"} · ` +
    `${i + 1} / ${state.order.length}`));
  // Sousedé dopředu, ať šipka nečeká na SMB.
  state.preload = [i + 1, i + 2, i - 1].map((n) => state.order[n])
    .filter((g) => g && state.present.has(g)).map((g) => {
      const im = new Image();
      im.src = thumbUrl(g, LARGE);
      return im;
    });
}

// --- formulář ----------------------------------------------------------------

const F = {
  nazev: { label: "Název", type: "text" },
  popis: { label: "Popis", type: "textarea" },
  datum_od: { label: "Datum od", type: "date" },
  datum_do: { label: "Datum do", type: "date" },
  datum: { label: "Datum pořízení", type: "datetime" },
  misto: { label: "Místo", type: "place" },
  mista: { label: "Místa akce (jediné místo se dědí na fotky)",
    type: "tags" },
  osoby: { label: "Osoby na fotce", type: "faces" },
  ucastnici: { label: "Účastníci akce (nedědí se na fotky)", type: "names" },
  autori: { label: "Autoři (fotil někdo z nich)", type: "names" },
  pristroj: { label: "Přístroj", type: "text" },
  gps: { label: "GPS (šířka, délka)", type: "gps" },
};

const FIELDS = {
  akce: ["nazev", "datum_od", "datum_do", "popis", "mista", "ucastnici"],
  skupina: ["autori", "pristroj", "popis", "misto"],
  soubor: ["datum", "autori", "popis", "osoby", "misto", "pristroj", "gps"],
};

// Štítek zdroje zděděné hodnoty podle úrovně, ze které pochází.
const SOURCE = { akce: "z akce", skupina: "ze skupiny", soubor: "ze souboru",
  misto: "z místa" };

// Cíl formuláře: objekt k úpravě a výpočet výsledné hodnoty.
function targetsFor(level, ids) {
  if (level === "akce") {
    return [{ obj: state.doc.akce, level, eff: (k) =>
      k in state.doc.akce ? { hodnota: state.doc.akce[k], uroven: "akce" }
        : undefined }];
  }
  if (level === "skupina") {
    return ids.map((g) => ({ obj: state.doc.skupiny[g], level,
      eff: (k) => resolveGroup(state.doc, g)[k] }));
  }
  return ids.map((f) => ({ obj: state.doc.soubory[f], level, file: f,
    eff: (k) => resolve(state.doc, f)[k] }));
}

function fieldState(targets, key) {
  const effs = targets.map((t) => t.eff(key));
  const vals = new Set(effs.map((e) => JSON.stringify(e?.hodnota ?? null)));
  const own = targets.map((t) => Object.hasOwn(t.obj, key));
  return {
    mixed: vals.size > 1,
    value: effs[0]?.hodnota,
    anyOwn: own.some(Boolean),
    allOwn: own.every(Boolean),
    from: effs.find((e) => e && e.uroven !== targets[0].level)?.uroven,
  };
}

function setField(targets, key, value) {
  for (const t of targets) {
    // Prázdná hodnota = nezadáno (u skupiny a souboru se znovu dědí).
    if (isEmpty(value)) delete t.obj[key];
    else t.obj[key] = structuredClone(value);
  }
}

// Osoby na fotce: jména z `obliceje` (z Immiche), jen pro čtení.
function facesRow(files) {
  const note = h("span", { class: "note", title: "Synchronizace z Immiche, " +
    "jen pro čtení" }, "z Immiche");
  let text;
  if (!state.info?.immich) {
    text = "Immich není napojen";
  } else {
    const names = new Set();
    for (const f of files) {
      for (const face of state.doc.soubory[f]?.obliceje || []) {
        names.add(face.jmeno);
      }
    }
    text = [...names].sort((a, b) => a.localeCompare(b, "cs")).join("; ") ||
      "nikdo pojmenovaný";
  }
  return h("div", { class: "field readonly from-immich" },
    h("label", {}, F.osoby.label, note),
    h("div", { class: "readonly-value" }, text));
}

function fieldRow(targets, key, onChange) {
  const def = F[key];
  if (def.type === "faces") return facesRow(targets.map((t) => t.file));
  const st = fieldState(targets, key);
  const inherited = !st.anyOwn && !isEmpty(st.value);
  const row = h("div", { class: "field" });
  const note = h("span", { class: "note" });
  // Vlastní hodnota skupiny nebo souborů jde vrátit na zděděnou (týž
  // zápis jako vyprázdnění pole). Akce nic nedědí.
  const revert = targets[0].level === "akce" ? null
    : h("button", {
      class: "revert", title: "Smazat zadanou hodnotu a dědit",
      onclick: () => {
        setField(targets, key, null);
        onChange(key);
        row.replaceWith(fieldRow(targets, key, onChange));
      },
    }, "↺ vrátit na zděděné");
  // Proužek, štítek a tlačítko podle stavu. Během psaní (`editing`) se
  // zděděná hodnota neukazuje (pole nemá zástupný text), takže ani její
  // štítek.
  const refresh = (editing) => {
    const s = fieldState(targets, key);
    const inh = !editing && !s.anyOwn && !isEmpty(s.value);
    row.classList.toggle("mixed", s.mixed);
    row.classList.toggle("own", s.anyOwn && !s.mixed);
    row.classList.toggle("inherited", inh && !s.mixed);
    row.classList.toggle("from-place", inh && !s.mixed && s.from === "misto");
    note.textContent = s.mixed ? "rozdílné"
      : inh ? SOURCE[s.from] || "zděděno"
      : s.anyOwn && !s.allOwn ? "zadáno u části"
      : s.anyOwn ? "zadáno" : "";
    note.title = s.mixed ? (s.allOwn ? "Rozdílné zadané hodnoty"
      : "Rozdílné hodnoty, část zděděná") : "";
    if (revert) revert.hidden = !s.anyOwn;
  };
  refresh(false);
  const update = (value) => {
    setField(targets, key, value);
    refresh(true);
    onChange(key);
  };
  const shown = st.mixed ? undefined : st.value;
  const placeholder = st.mixed ? "rozdílné hodnoty – zápisem přepíšete vše"
    : inherited ? format(def.type, st.value) : "";
  const input = def.type === "datetime"
    ? dateTimeEditor(targets, key, () => {
      refresh(true);
      onChange(key);
    })
    : editor(def.type, inherited ? undefined : shown, placeholder,
      update, inherited ? st.value : undefined);
  // Tlačítko mimo <label>: jinak by klik na popisek spustil vrácení.
  row.append(h("div", { class: "lrow" }, h("label", {}, def.label, note),
    revert), input);
  return row;
}

function format(type, v) {
  if (isEmpty(v)) return "";
  if (type === "tags" || type === "names") return v.join("; ");
  if (type === "gps") return v.join(", ");
  return String(v);
}

// Datum pořízení: den a čas zvlášť, každý zapisuje každému cíli jen
// svou část (druhá zůstane). Rozepsaný vstup hlásí prázdno
// (`badInput`) — to není smazání; rok nad 9999 se nezapíše. Stav se
// obnoví na místě, aby psaní neztratilo fokus.
function dateTimeEditor(targets, key, changed) {
  const cur = (t) => String(t.obj[key] ?? t.eff(key)?.hodnota ?? "");
  const write = (fn, input) => {
    if (!input.validity.valid) return;
    const part = input.value;
    for (const t of targets) {
      const v = fn(cur(t), part);
      if (v) t.obj[key] = v;
      else delete t.obj[key];
    }
    refresh();
    changed();
  };
  const day = h("input", { type: "date", max: "9999-12-31",
    onchange: (e) => write(withDay, e.target) });
  const time = h("input", { type: "time", step: "1",
    onchange: (e) => write(withTime, e.target) });
  const mixed = h("span", { class: "ph-text" },
    "rozdílné hodnoty – zápisem přepíšete vše");
  const refresh = () => {
    const values = targets.map(cur);
    const p = parts(values);
    if (document.activeElement !== day) day.value = p.day;
    if (document.activeElement !== time) time.value = p.time;
    time.disabled = values.every((v) => !v);
    mixed.hidden = !p.mixed;
  };
  refresh();
  return h("div", { class: "row datetime" }, day, time, mixed);
}

function editor(type, value, placeholder, update, inheritedValue) {
  if (type === "names" || type === "tags") {
    return namesField(value || [], update, inheritedValue, placeholder,
      type === "names");
  }
  if (type === "textarea") {
    return h("textarea", { rows: 3, placeholder, value: value || "",
      oninput: (e) => update(e.target.value) });
  }
  if (type === "date") {
    const el = h("input", { type: "date", value: value || "",
      oninput: (e) => update(e.target.value) });
    if (placeholder) el.title = placeholder;
    return h("div", { class: "row" }, el,
      placeholder ? h("span", { class: "ph-text" }, placeholder) : null);
  }
  if (type === "gps") {
    return h("input", { value: format("gps", value), placeholder,
      oninput: (e) => {
        const v = e.target.value.trim();
        const m = v.match(/^(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)$/);
        e.target.classList.toggle("invalid", !!v && !m);
        if (!v) update(null);
        else if (m) update([Number(m[1]), Number(m[2])]);
      } });
  }
  if (type === "place") {
    // Jedno místo; návrhy z míst akce.
    const id = `mista-${Math.random().toString(36).slice(2)}`;
    return h("div", {},
      h("input", { value: value || "", placeholder, list: id,
        oninput: (e) => update(e.target.value.trim()) }),
      h("datalist", { id },
        (state.doc.akce.mista || []).map((m) => h("option", { value: m }))));
  }
  return h("input", { value: value || "", placeholder,
    oninput: (e) => update(e.target.value) });
}

// --- souřadnice míst -----------------------------------------------------

// Rozhodnutí o souřadnicích místa platí pro celou akce (`souradnice_mist`):
// {gps, popis[, osm]}, nebo null = bez souřadnic. Na Nominatim se ptá
// server (sdílená cache), a to až po otevření volby, ne při psaní.

const OSM = "© OpenStreetMap contributors";

// Odkaz na objekt OSM, ze kterého jsou souřadnice; neplatné `osm` → null.
// Nová karta, aby neuložené úpravy plochy zůstaly.
function osmLink(osm) {
  const href = osmUrl(osm);
  return href && h("a", { href, target: "_blank",
    rel: "noopener noreferrer", class: "osm",
    title: `Objekt na OpenStreetMap (${osm})` }, "OSM");
}

// Soubor nemá vlastní ani zděděné GPS (GPS z místa se nepočítá).
function withoutGps(f) {
  const gps = resolve(state.doc, f).gps;
  return !gps || gps.uroven === "misto";
}

// Výsledná místa vybraných souborů bez GPS.
function placesOf(files) {
  const result = new Set();
  for (const f of files) {
    const misto = resolve(state.doc, f).misto?.hodnota;
    if (!isEmpty(misto) && withoutGps(f)) result.add(misto);
  }
  return [...result].sort((a, b) => a.localeCompare(b, "cs"));
}

// Z lišty: vybrat soubory místa a rovnou otevřít volbu souřadnic.
function openPlace(misto, files) {
  state.anchor = files[0];
  state.current = files[0];
  select(new Set(files), null, { place: misto });
  document.querySelector(`#grid .tile[data-file="${CSS.escape(files[0])}"]`)
    ?.scrollIntoView({ block: "center" });
}

function renderPlaces(box) {
  const places = placesOf(state.sel);
  box.replaceChildren(...places.map((m) => placeBlock(m, box)));
}

function placeBlock(misto, box) {
  const decision = (state.doc.souradnice_mist || {})[misto];
  const decided = Object.hasOwn(state.doc.souradnice_mist || {}, misto);
  const body = h("div");
  const fs = h("fieldset", { class: "tools place" },
    h("legend", {}, `Souřadnice místa „${misto}“`), body);
  const rerender = () => renderPlaces(box);
  if (state.placeOpen === misto) {
    body.append(placeChooser(misto, rerender));
    return fs;
  }
  const open = h("button", { onclick: () => {
    state.placeOpen = misto;
    rerender();
  } }, decided ? "Změnit" : "Vybrat souřadnice");
  if (!decided) {
    body.append(h("p", { class: "warn" }, "Nerozhodnuto – fotky bez GPS " +
      "nebudou mít v Immichi místo."), open);
  } else if (decision === null) {
    body.append(h("p", { class: "meta" }, "Bez souřadnic."), open);
  } else {
    const link = osmLink(decision.osm);
    body.append(h("p", { class: "meta" },
      `${decision.gps.join(", ")}`,
      decision.popis ? h("br") : null, decision.popis || null,
      link ? " " : null, link), open);
  }
  return fs;
}

function decide(misto, value) {
  state.doc.souradnice_mist ||= {};
  state.doc.souradnice_mist[misto] = value;
  state.placeOpen = null;
  changed();
  renderPanel();
}

// Těžiště GPS souborů akce, které GPS mají (EXIF nebo ručně).
function eventCentroid() {
  const pts = Object.keys(state.doc.soubory || {})
    .filter((f) => state.present.has(f))
    .map((f) => resolve(state.doc, f).gps)
    .filter((g) => g && g.uroven !== "misto" && !isEmpty(g.hodnota))
    .map((g) => g.hodnota);
  if (!pts.length) return null;
  return [0, 1].map((i) => pts.reduce((a, p) => a + p[i], 0) / pts.length);
}

function haversine([lat1, lon1], [lat2, lon2]) {
  const r = (x) => x * Math.PI / 180;
  const a = Math.sin(r(lat2 - lat1) / 2) ** 2 + Math.cos(r(lat1)) *
    Math.cos(r(lat2)) * Math.sin(r(lon2 - lon1) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
}

// Index předvybraného kandidáta: nejbližší těžišti GPS akce, jinak první.
function preselect(candidates) {
  if (!candidates.length) return null;
  const c = eventCentroid();
  if (!c) return 0;
  let best = 0;
  candidates.forEach((k, i) => {
    if (haversine(c, k.gps) < haversine(c, candidates[best].gps)) best = i;
  });
  return best;
}

function parseGps(text) {
  const m = text.trim()
    .match(/^(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const gps = [Number(m[1]), Number(m[2])];
  return Math.abs(gps[0]) <= 90 && Math.abs(gps[1]) <= 180 ? gps : null;
}

function placeChooser(misto, rerender) {
  const name = `place-${Math.random().toString(36).slice(2)}`;
  const list = h("div", { class: "candidates" });
  const manual = h("input", {
    placeholder: "šířka, délka (49.4063, 16.7777)",
    oninput: () => {
      manual.classList.toggle("invalid",
        !!manual.value.trim() && !parseGps(manual.value));
      manualRadio.checked = true;
    } });
  const manualRadio = h("input", { type: "radio", name, value: "rucne" });
  const noneRadio = h("input", { type: "radio", name, value: "bez" });
  const err = h("p", { class: "warn" });
  let candidates = [];
  const confirm = h("button", { onclick: () => {
    const v = list.closest("fieldset")
      .querySelector(`input[name="${name}"]:checked`)?.value;
    if (v === undefined) {
      err.textContent = "Vyberte jednu z možností.";
    } else if (v === "bez") {
      decide(misto, null);
    } else if (v === "rucne") {
      const gps = parseGps(manual.value);
      if (!gps) err.textContent = "Souřadnice ve tvaru šířka, délka.";
      else decide(misto, { gps, popis: "zadáno ručně" });
    } else {
      const k = candidates[Number(v)];
      decide(misto, { gps: k.gps, popis: k.popis, osm: k.osm });
    }
  } }, "Potvrdit");
  const cancel = h("button", { class: "link", onclick: () => {
    state.placeOpen = null;
    rerender();
  } }, "zrušit");

  const showCandidates = (found) => {
    candidates = found;
    const pre = preselect(found);
    list.replaceChildren(...[
      found.length ? null : h("p", { class: "meta" },
        "Služba místo nenašla – zadejte souřadnice ručně."),
      ...found.map((k, i) => {
        const link = osmLink(k.osm);
        return h("label", { class: "candidate" },
          h("input", { type: "radio", name, value: String(i),
            checked: i === pre }),
          h("span", {}, h("b", {}, k.nazev), " ", k.popis,
            h("span", { class: "meta" }, ` (${k.gps.join(", ")})`),
            link ? " " : null, link));
      }),
      found.length ? h("p", { class: "meta attribution" }, OSM) : null,
    ].filter(Boolean));
    if (!found.length) manual.focus();
  };
  const search = async () => {
    err.textContent = "";
    if (state.geo[misto]) return showCandidates(state.geo[misto]);
    list.replaceChildren(h("p", { class: "meta" }, "Hledám…"));
    try {
      const q = encodeURIComponent(misto);
      const r = await api(`/api/geokodovani?q=${q}`);
      state.geo[misto] = r.kandidati;
      showCandidates(r.kandidati);
    } catch (e) {
      const text = e.status === 503
        ? "Geokódování je vypnuté (kontakt nastaví admin v Nastavení)."
        : "Služba neodpověděla.";
      list.replaceChildren(h("p", { class: "warn" }, text));
      if (e.status !== 503) {
        list.append(h("button", { onclick: search }, "Zkusit znovu"));
      }
    }
  };
  if (state.info?.geokodovani) search();
  else list.replaceChildren(h("p", { class: "meta" },
    "Geokódování je vypnuté – zadejte souřadnice ručně."));

  return h("div", {},
    list,
    h("label", { class: "candidate" }, manualRadio,
      h("span", {}, "Ručně:")),
    manual,
    h("label", { class: "candidate" }, noneRadio,
      h("span", {}, "Bez souřadnic")),
    err,
    h("div", { class: "row" }, confirm, cancel));
}

// --- pole jmen ---------------------------------------------------------------

// Pole se štítky. `people` = jména osob (návrhy a kontrola tvaru);
// jinak volné štítky (místa). Položky odděluje jen Enter: čárka patří
// do jmen i adres (`Adamova 150, Adamov`).
function namesField(initial, update, inheritedValue, placeholder,
  people = true) {
  let names = [...initial];
  let inherited = inheritedValue ? [...inheritedValue] : null;
  const chips = h("div", { class: "chips" });
  const input = h("input", { placeholder: placeholder || (people
    ? "Příjmení, Jméno – Enter přidá" : "Enter přidá") });
  const list = h("ul", { class: "suggest", hidden: true });
  const hint = h("div", { class: "hint", hidden: true });
  let active = -1;

  const commit = (next) => {
    names = next;
    inherited = null;
    renderChips();
    update(names);
  };
  const renderChips = () => {
    const shown = inherited || names;
    chips.replaceChildren(...shown.map((n, i) => h("span", {
      class: `chip${inherited ? " inh" : ""}`,
    }, n, h("button", {
      class: "x", title: "Odebrat",
      onclick: () => commit(shown.filter((_, j) => j !== i)),
    }, "×"))));
  };
  const add = async (raw) => {
    const name = raw.trim().replace(/\s+/g, " ");
    if (!name) return;
    input.value = "";
    list.hidden = true;
    const base = inherited || names;
    if (!people) {
      if (!base.includes(name)) commit([...base, name]);
      return;
    }
    const known = new Set([...state.sessionNames]);
    const r = known.has(name) ? { znamo: true }
      : await api(`/api/jmena/kontrola?jmeno=${encodeURIComponent(name)}`);
    const put = (n) => {
      hint.hidden = true;
      state.sessionNames.add(n);
      if (!base.includes(n)) commit([...base, n]);
    };
    // Návrh opravy podle jmen, která zná jen tento prohlížeč.
    if (!r.znamo && !r.mysleli_jste) {
      const key = normalize(name);
      const local = [...known].find((n) => normalize(n) === key);
      if (local) r.mysleli_jste = local;
    }
    if (r.mysleli_jste || r.prevod) {
      const proposal = r.mysleli_jste || r.prevod;
      hint.replaceChildren(
        r.mysleli_jste ? "Mysleli jste " : "Uložit jako ",
        h("button", { class: "link", onclick: () => put(proposal) },
          proposal), "? ",
        h("button", { class: "link", onclick: () => put(name) },
          `ponechat „${name}“`));
      hint.hidden = false;
    } else {
      put(name);
    }
  };
  const showSuggest = debounce(async () => {
    const q = input.value.trim();
    if (!people) return;
    if (!q) {
      list.hidden = true;
      return;
    }
    const r = await api(`/api/jmena?q=${encodeURIComponent(q)}`);
    const key = normalize(q).split(" ");
    const local = [...state.sessionNames].filter((n) => {
      const toks = normalize(n).split(" ");
      return key.every((k) => toks.some((t) => t.startsWith(k)));
    });
    // Účastníci akce se nabízejí přednostně.
    const ucastnici = (state.doc?.akce?.ucastnici || []).filter((n) => {
      const toks = normalize(n).split(" ");
      return key.every((k) => toks.some((t) => t.startsWith(k)));
    });
    const all = [...new Set([...ucastnici, ...r.navrhy, ...local])]
      .filter((n) => !(inherited || names).includes(n));
    active = -1;
    list.replaceChildren(...all.map((n) => h("li", {
      onmousedown: (e) => { e.preventDefault(); add(n); },
    }, n)));
    list.hidden = !all.length;
  }, 150);
  input.addEventListener("input", showSuggest);
  input.addEventListener("keydown", (e) => {
    const items = [...list.children];
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (list.hidden || !items.length) return;
      e.preventDefault();
      active = (active + (e.key === "ArrowDown" ? 1 : -1) + items.length) %
        items.length;
      items.forEach((li, i) => li.classList.toggle("active", i === active));
    } else if (e.key === "Enter") {
      e.preventDefault();
      add(!list.hidden && active >= 0 ? items[active].textContent
        : input.value);
    } else if (e.key === "Escape") {
      list.hidden = true;
    } else if (e.key === "Backspace" && !input.value &&
               (inherited || names).length) {
      commit((inherited || names).slice(0, -1));
    }
  });
  input.addEventListener("blur", () => setTimeout(() => {
    list.hidden = true;
    if (!people && input.value.trim()) add(input.value);
  }, 100));
  renderChips();
  return h("div", { class: "names" }, chips, input, list, hint);
}

function normalize(name) {
  return name.normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().match(/[\p{L}\p{N}_]+/gu)?.sort().join(" ") || "";
}

// --- dokončení (export) ------------------------------------------------------

function exportTarget() {
  return state.info?.zapis ? "Sidecary se zapíšou vedle souborů v archivu."
    : `Vývojový režim: sidecary jdou do ${state.info?.work || "…"}/xmp, ` +
      "ne do archivu.";
}

function checkNote(kontrola) {
  if (!kontrola) return "";
  const n = kontrola.zapsano + kontrola.chyby.length;
  return n ? plural(n, "sidecar neaktuální", "sidecary neaktuální",
    "sidecarů neaktuálních") : "sidecary aktuální";
}

function exportResult(r) {
  let text = `zapsáno ${r.zapsano}, nezměněno ${r.nezmeneno}`;
  if (r.chyby.length) text += `, selhalo ${r.chyby.length}`;
  if (!state.info?.zapis) text += " (vývojový režim: do pracovního adresáře)";
  return text;
}

// Je co exportovat: neuložené či neexportované změny, neaktuální sidecary,
// selhaný export nebo chybějící kontrola.
function exportPending() {
  return state.dirty || state.saving || state.exportStale;
}

function renderExportStatus() {
  const el = document.getElementById("export-status");
  if (!el) return;
  const done = state.doc?.dokonceno;
  const errors = state.exportErrors;
  el.textContent = state.exporting ? "Exportuji…"
    : [done ? `Dokončeno ${done}` : "", state.exportNote]
      .filter(Boolean).join(" · ");
  el.className = errors.length ? "error" : exportPending() ? "pending" : "";
  el.title = errors.map((e) => `${e.soubor}: ${e.chyba}`).join("\n");
  // Dokončená akce beze změn nemá co dokončovat.
  const finish = document.getElementById("finish");
  if (finish) {
    finish.disabled = !!state.readonly || (!!done && !exportPending());
  }
}

function confirmDialog(title, lines, ok) {
  return new Promise((resolve) => {
    const close = (value) => {
      dialog.close();
      dialog.remove();
      resolve(value);
    };
    const dialog = h("dialog", { class: "conflict" },
      h("h2", {}, title),
      h("ul", {}, lines.map((l) => h("li", {}, l))),
      h("div", { class: "buttons" },
        h("button", { class: "primary", onclick: () => close(true) }, ok),
        h("button", { onclick: () => close(false) }, "Zrušit")));
    dialog.addEventListener("cancel", (e) => {
      e.preventDefault();
      close(false);
    });
    document.body.append(dialog);
    dialog.showModal();
  });
}

// Uloží neuložené změny; false, když uložit nejde (konflikt, zámek).
async function flushSave() {
  while (state.saving) await new Promise((r) => setTimeout(r, 100));
  if (state.dirty) await save();
  return !state.dirty && !state.conflict && !state.readonly;
}

// Dokončení je jediný export z plochy (#20); u dokončené akce zapíše
// změny do sidecarů a datum dokončení nechá.
async function finishEvent() {
  if (state.exporting || state.readonly) return;
  if (!(await flushSave())) return;
  const name = state.name;
  state.exporting = true;
  state.exportErrors = [];
  state.finishResult = state.finishError = null;
  refreshFinish();
  try {
    const r = await api(eventUrl(name, "/dokoncit"), {
      method: "POST", body: { relace: session(), version: state.version },
    });
    if (name !== state.name) return;
    state.finishResult = r;
    state.exportErrors = r.chyby;
    state.exportStale = r.chyby.length > 0;
    state.version = r.version;
    state.doc.dokonceno = r.dokonceno;
    state.exportVersion = r.export_version;
    const failed = r.dokonceno ? "" : ", není dokončená";
    state.exportNote = r.zverejneni
      ? "Akci nešlo zveřejnit pro Immich (přejmenovat složku)" +
        `${failed}: ${r.zverejneni === "kolize_pripony" ? KOLIZE
          : r.zverejneni}`
      : (r.chyby.length ? `Export selhal${failed}: ` : "Exportováno: ") +
        exportResult(r);
    if (r.index?.length) state.exportNote += ` · Index: ${r.index.join("; ")}`;
  } catch (err) {
    if (name !== state.name) return;
    if (err.status === 409 && err.data?.chyba === "konflikt") {
      state.conflict = true;
      conflictDialog();
    } else if (deniedLock(err)) {
      state.readonly = deniedLock(err);
      state.locked = null;
      clearInterval(heartbeatTimer);
      lostLock();
    }
    state.exportStale = true;
    state.exportNote = `Export selhal: ${err.message}`;
    state.finishError = err.message;
  } finally {
    state.exporting = false;
  }
  if (state.finishResult?.dokonceno && name === state.name) {
    // Hlídač začíná na serveru až po dokončení; načti stav hned a
    // čekej na první zápis do `.work/immich-alba.json`.
    await loadImmichStav(name);
    if (name === state.name) pollImmichStav(name, IMMICH_ZAPIS_POKUSU);
  }
  refreshFinish();
  if (state.dirty && !state.conflict) scheduleSave();
}

// Po dokončení: kontrolní stránka, nebo stav u tlačítka, pokud uživatel
// mezitím přešel na plochu.
function refreshFinish() {
  if (state.mode === "finish") renderFinish();
  else renderExportStatus();
}

// --- stav akce v Immichi ----------------------------------------------------

// Plocha obnovuje stav přes `GET /api/akce/<název>/immich` (čte jen
// `.work/immich-alba.json`), dokud je stav průběhový; po dokončení
// počká i na první zápis hlídače, který může chvíli trvat.
const IMMICH_POLL_MS = 10000;
const IMMICH_ZAPIS_POKUSU = 6;
let immichTimer = null;

function renderImmichStav() {
  const el = document.getElementById("immich-stav");
  // Jen u dokončené akce; bez záznamu nebo bez Immiche prázdné.
  if (el) el.textContent = state.doc?.dokonceno
    ? immichStav(state.immich) : "";
}

async function loadImmichStav(name) {
  try {
    const r = await api(eventUrl(name, "/immich"));
    if (name !== state.name) return;
    state.immich = r.nastaveno ? r : null;
    renderImmichStav();
  } catch { /* jen informativní údaj; zkusí se příští tik */ }
}

// `pockat` = kolik tiků zbývá, než hlídač první záznam zapíše (0 =
// obnovovat jen když už stav známe a je průběhový).
function pollImmichStav(name, pockat) {
  clearTimeout(immichTimer);
  const probiha = state.immich?.stav === "nacitani"
    || state.immich?.stav === "rozpoznavani";
  if (!probiha && pockat <= 0) return;
  immichTimer = setTimeout(async () => {
    // Úklid po navigaci: plocha už může být jiná akce nebo zavřená.
    if (name !== state.name
        || (state.mode !== "workspace" && state.mode !== "finish")) return;
    await loadImmichStav(name);
    // Se záznamem rozhoduje jen stav (průběhový = dál), bez něj
    // ubývají pokusy čekání na první zápis hlídače.
    pollImmichStav(name, state.immich ? 0 : pockat - 1);
  }, IMMICH_POLL_MS);
}

// --- nástroj pojmenování osob ----------------------------------------------

// Nástroj se nabízí jen při albu v Immichi a buď osobách k pojmenování,
// nebo alespoň rozjetém rozpoznávání obličejů (stav ≥ rozpoznavani);
// do `rozpoznano` mohou osoby ještě přibývat (upozornění v nástroji).
function canOpenNaming() {
  const im = state.immich;
  if (!im?.album) return false;
  if (im.stav === "rozpoznavani" || im.stav === "rozpoznano") return true;
  return !!(im.osoby && im.osoby[0] < im.osoby[1]);
}

// Tlačítko nástroje v liště akce (archivář a admin; s počtem
// nepojmenovaných).
function renderOsobyActs() {
  const slot = document.getElementById("osoby-acts");
  if (!slot) return;
  const o = state.immich?.osoby;
  const nepoj = Array.isArray(o) ? o[1] - o[0] : 0;
  // Bez tlačítka prázdný slot: `replaceChildren(null)` by vložil text
  // „null“.
  slot.replaceChildren(...(state.me?.archivar && canOpenNaming()
    ? [h("button", { onclick: openNaming },
      nepoj > 0 ? `Pojmenovat osoby… (${nepoj})` : "Pojmenovat osoby…")]
    : []));
}

// Překryv nástroje nad plochou; po zavření pryč `#osoby` z adresy,
// obnovit počty osob v navigátoru i liště a oznámit synchronizaci.
function openNaming() {
  if (state.mode !== "workspace") return;
  showNaming({
    nazev: state.name,
    naZavreni: async (vysledek) => {
      if (location.hash.endsWith("#osoby")) {
        history.replaceState(null, "", eventHash(state.name));
      }
      await loadImmichStav(state.name);
      if (state.mode !== "workspace") return;
      renderNav();
      renderOsobyActs();
      if (vysledek?.synchronizace) {
        const el = document.getElementById("immich-stav");
        if (el) el.textContent = "⟳ Server spouští synchronizaci — " +
          "jména se přenesou do „obliceje“ a počtů osob.";
      }
    },
  });
}

// --- kontrolní stránka dokončení -------------------------------------------

// Seznam kontrol s odkazy nápravy, tlačítko Dokončit a výsledek. Sdílí
// stav akce s plochou; bez zámku jen ke čtení.
function renderFinish() {
  state.mode = "finish";
  const name = state.name;
  const items = missingItems();
  const fix = (onclick) => {
    state.pendingFix = onclick;
    location.hash = eventHash(name);
  };
  const checks = CHECKS.map(([key, label, okText]) => {
    const own = items.filter((i) => i.skupina === key);
    return h("li", { class: own.length ? "vyresit" : "ok" },
      h("span", { class: "znacka", "aria-hidden": "true" },
        own.length ? "!" : "✓"),
      h("div", {}, h("strong", {}, label),
        own.length ? h("ul", {}, own.map((i) => h("li", {}, i.text, " ",
          h("button", { class: "link", onclick: () => fix(i.onclick) },
            "Opravit na ploše")))) : h("span", { class: "meta" },
          ` – ${okText}`)));
  });
  const exp = exportCheck();
  checks.push(h("li", { class: exp.ok ? "ok" : "info" },
    h("span", { class: "znacka", "aria-hidden": "true" },
      exp.ok ? "✓" : "↻"),
    h("div", {}, h("strong", {}, "Stav exportu"), ` – ${exp.text}`,
      h("p", { class: "meta" }, exportTarget()))));
  const done = state.doc.dokonceno;
  const button = h("button", { class: "primary",
    disabled: !!state.readonly || state.exporting ||
      (!!done && !exportPending()),
    title: exportTarget(), onclick: () => finishEvent() },
  state.exporting ? "Dokončuji…" : items.length ? "Přesto dokončit"
    : "Dokončit");
  app.replaceChildren(
    header(h("span", { id: "save-status", class: "status" })),
    h("div", { class: "eventbar" },
      h("a", { href: eventHash(name) }, "← Plocha akce"),
      h("h1", {}, name)),
    lockNotice(),
    h("main", { class: "dokonceni" },
      h("h2", {}, "Kontrola před dokončením"),
      h("ul", { class: "kontroly" }, checks),
      h("div", { class: "row" }, button,
        done ? h("span", { class: "meta" }, `Dokončeno ${done}`) : null,
        items.length ? h("span", { class: "meta" },
          "Kontroly k vyřešení dokončení nebrání.") : null),
      finishResultView()));
  setStatus();
}

// Výsledek posledního dokončení: počty sidecarů, chyby, zveřejnění.
function finishResultView() {
  const r = state.finishResult;
  if (state.finishError) {
    return h("section", { class: "vysledek" },
      h("p", { class: "error" }, `Dokončení selhalo: ${state.finishError}`));
  }
  if (!r) return null;
  const failed = r.chyby.length || r.zverejneni;
  return h("section", { class: "vysledek" },
    h("h2", {}, failed ? (r.dokonceno ? "Dokončeno s chybami"
      : "Akci nešlo dokončit") : "Akce je dokončená"),
    h("p", {}, `Sidecary: ${exportResult(r)}.`),
    r.zverejneni ? h("p", { class: "error" },
      "Akci nešlo zveřejnit pro Immich (přejmenovat složku): ",
      r.zverejneni === "kolize_pripony" ? KOLIZE : r.zverejneni) : null,
    r.chyby.length ? h("ul", { class: "error" }, r.chyby.map((e) =>
      h("li", {}, h("code", {}, e.soubor), `: ${e.chyba}`))) : null,
    r.index?.length ? h("p", { class: "meta" },
      `Index: ${r.index.join("; ")}`) : null,
    h("p", {}, h("a", { href: listLink() }, "← Seznam akcí")));
}

// Tlačítko Dokončit akci na ploše: uloží a otevře kontrolní stránku.
async function openFinish() {
  if (state.readonly || !(await flushSave())) return;
  location.hash = eventHash(state.name, true);
}

// --- pracovní plocha -------------------------------------------------------

function renderWorkspace() {
  const d = state.detail;
  const back = h("a", { href: listLink() }, "← Akce");
  app.replaceChildren(
    header(h("span", { id: "save-status", class: "status" })),
    h("div", { class: "eventbar" }, back,
      h("h1", {}, state.name),
      h("span", { class: "paths" }, d.pracovni_soubor),
      // Stav v Immichi (jen u dokončené akce se záznamem); vidí ho i
      // běžný uživatel a bez zámku. `paths` by byl skrytý, `meta` je
      // viditelný slabý text.
      h("span", { class: "meta", id: "immich-stav" }),
      h("span", { class: "views" },
        h("button", { dataset: { view: "grid" }, class: "ico",
          title: "Mřížka (Esc)", "aria-label": "Mřížka",
          onclick: () => setView("grid") }, icon("mrizka")),
        h("button", { dataset: { view: "loupe" }, class: "ico",
          title: "Lupa (Enter nebo dvojklik)", "aria-label": "Lupa",
          onclick: () => setView("loupe") }, icon("lupa"))),
      h("span", { class: "views" },
        h("button", { dataset: { layout: "skupiny" },
          class: state.layout === "skupiny" ? "active" : "",
          title: "Oddíly podle skupin",
          onclick: () => setLayout("skupiny") }, "Po skupinách"),
        h("button", { dataset: { layout: "datum" },
          class: state.layout === "datum" ? "active" : "",
          title: "Všechny soubory podle data pořízení, oddíly po dnech",
          onclick: () => setLayout("datum") }, "Podle data")),
      h("label", { class: "tilesize", title: "Velikost náhledů v mřížce" },
        "Náhledy", h("input", { type: "range", min: TILE.min,
          max: TILE.max, step: 10, value: tileSize(),
          oninput: (e) => setTileSize(e.target.value) })),
      // Nálezy a počty (renderBar): zalamují se, akce vpravo ne.
      h("div", { id: "bar", class: "bar" }),
      h("span", { class: "acts" },
        h("span", { id: "osoby-acts" }),
        h("button", { disabled: !!state.readonly,
          title: "Nahrát do akce další fotky a videa", onclick: () => {
            location.hash = `#/import?cil=${encodeURIComponent(state.name)}`;
          } }, "Importovat…"),
        h("span", { class: "export" },
          h("span", { id: "export-status" }),
          h("button", { id: "finish", class: "primary",
            disabled: !!state.readonly, title: exportTarget(),
            onclick: () => openFinish() }, "Dokončit akci")))),
    lockNotice(),
    h("div", { class: `workspace${panelCollapsed() ? " panel-sbaleny" : ""}` },
      h("nav", { id: "nav", class: "nav", "aria-label": "Navigátor akce" }),
      h("div", { id: "grid", class: "grid",
        style: `--tile: ${tileSize()}px` }),
      h("div", { id: "loupe", class: "loupe", hidden: true },
        h("div", { id: "big", class: "big" }),
        h("div", { id: "film", class: "film" })),
      h("button", { id: "panel-toggle", class: "panel-toggle",
        onclick: togglePanel }),
      h("aside", { id: "panel", class: "panel" })));
  setPanelToggle();
  setupNav(document.getElementById("nav"));
  setupGrid(document.getElementById("grid"));
  setupFilm(document.getElementById("film"));
  renderGrid();
  setView(state.view);
  renderBar();
  renderPanel();
  setStatus();
  renderExportStatus();
  renderImmichStav();
  renderOsobyActs();
  pollImmichStav(state.name, 0);   // obnovuje jen během načítání
  if (state.dirty) scheduleSave();
}

// Velikost dlaždic mřížky (`--tile`); volba prohlížeče, ne akce. Strop
// 300 px: náhled ze serveru má 320 px.
// Minimum 80 px: 8 dlaždic na řádek v okně 1280 px s navigátorem
// a panelem.
const TILE = { min: 80, max: 300, init: 150 };

function tileSize() {
  const v = Number(localStorage.getItem("dlazdice"));
  return v >= TILE.min && v <= TILE.max ? v : TILE.init;
}

function setTileSize(v) {
  localStorage.setItem("dlazdice", v);
  document.getElementById("grid")?.style.setProperty("--tile", `${v}px`);
  if (state.current && state.view === "grid") {
    document.querySelector(
      `#grid .tile[data-file="${CSS.escape(state.current)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }
}

// Sbalený panel formuláře: obsah zůstane v DOM, jen se skryje, takže
// výběr ani rozepsaná pole se neztratí.
function panelCollapsed() {
  return localStorage.getItem("panel") === "sbaleny";
}

function setPanelToggle() {
  const b = document.getElementById("panel-toggle");
  if (!b) return;
  const collapsed = panelCollapsed();
  b.replaceChildren(icon("panel"));
  b.title = `${collapsed ? "Rozbalit" : "Sbalit"} panel (P)`;
  b.setAttribute("aria-label", collapsed ? "Rozbalit panel" : "Sbalit panel");
  b.setAttribute("aria-expanded", String(!collapsed));
}

function togglePanel() {
  const ws = document.querySelector(".workspace");
  if (!ws || state.mode !== "workspace") return;
  const collapsed = !panelCollapsed();
  if (collapsed) localStorage.setItem("panel", "sbaleny");
  else localStorage.removeItem("panel");
  ws.classList.toggle("panel-sbaleny", collapsed);
  setPanelToggle();
  if (state.view === "loupe") renderBig();
}

// Kontroly dokončení po skupinách (CHECKS): [{skupina, text, n, onclick}];
// `onclick` je náprava na ploše. Stav exportu je zvlášť (exportCheck).
function missingItems() {
  const m = missing(state.doc, state.present);
  const items = [];
  const item = (skupina, text, n, onclick) =>
    items.push({ skupina, text, n, onclick });
  if (m.akce.length) {
    item("akce", `Akce: chybí ${m.akce.map((k) => AKCE_POLE[k])
      .join(", ")}`, m.akce.length, () => select(new Set(), null));
  }
  if (m.skupinyBezAutoru.length) {
    item("soubory", `${plural(m.skupinyBezAutoru.length, "skupina",
      "skupiny", "skupin")} bez autorů`, m.skupinyBezAutoru.length, () => {
      const g = m.skupinyBezAutoru[0];
      select(new Set(), g);
      scrollToSection(`g:${g}`);
    });
  }
  const counted = Object.keys(state.doc.soubory || {}).filter((f) =>
    state.present.has(f) && !discarded(f));
  const files = (list, label) => {
    if (list.length) item("soubory", `${nFiles(list.length)} ${label}`,
      list.length, () => selectFiles(list));
  };
  files(counted.filter((f) => !authorsOf(f).length), "bez autorů");
  files(m.souboryBezData, "bez data");
  files(m.souboryBezSkupiny, "bez skupiny");
  files(m.souboryBezMista, "bez místa");
  const places = Object.keys(m.mistaBezSouradnic);
  if (places.length) {
    item("soubory", `${plural(places.length, "místo", "místa", "míst")} ` +
      "bez souřadnic", places.length,
    () => openPlace(places[0], m.mistaBezSouradnic[places[0]]));
  }
  for (const f of findingItems()) {
    item("nalezy", f.text, f.n, NALEZY_UKLID.includes(f.druh)
      ? workspaceCleanup : f.onclick);
  }
  const damaged = damagedToRepair();
  if (damaged.length) {
    item("poskozene", `${plural(damaged.length, "poškozený soubor",
      "poškozené soubory", "poškozených souborů")} bez rozhodnutí`,
    damaged.length, () => selectFiles(damaged));
  }
  const vyradit = Object.keys(state.doc.soubory || {})
    .filter((f) => state.present.has(f) && discarded(f));
  if (vyradit.length) {
    item("vyradit", `${nFiles(vyradit.length)} k vyřazení ještě ` +
      "v kořeni", vyradit.length, workspaceCleanup);
  }
  return items;
}

// Skupiny kontrol kontrolní stránky: [klíč, název, text bez nálezu].
const CHECKS = [
  ["akce", "Údaje akce", "název a data akce vyplněná"],
  ["soubory", "Chybějící údaje souborů", "všem souborům nic nechybí"],
  ["nalezy", "Nálezy kontroly akce", "žádné nálezy"],
  ["poskozene", "Poškozené soubory", "žádné bez rozhodnutí"],
  ["vyradit", "Soubory k vyřazení", "žádné nezůstaly v kořeni"],
];

// Stav exportu pro kontrolní stránku: {ok, text}.
function exportCheck() {
  if (state.exportErrors.length) {
    return { ok: false, text: `poslední export selhal u ${
      nFiles(state.exportErrors.length)}` };
  }
  if (state.dirty || state.saving) {
    return { ok: false, text: "neuložené změny" };
  }
  if (state.exportStale) {
    return { ok: false, text: state.exportNote || "neexportované změny" };
  }
  return { ok: true, text: "sidecary aktuální" };
}

// Nálezy kontroly kořene akce (issue #11) pro lištu akce i dokončení:
// klik ukáže názvy.
function findingItems() {
  const nalezy = state.detail?.kontrola || [];
  return Object.keys(NALEZY).flatMap((druh) => {
    const names = nalezy.filter((n) => n.druh === druh).map((n) => n.nazev);
    if (!names.length) return [];
    const text = nalez(druh, names.length);
    return [{ text, druh, n: names.length,
      onclick: () => namesDialog(text, names, druh) }];
  });
}

// Názvy souborů a složek jednoho druhu nálezu kontroly.
function namesDialog(title, names, druh) {
  const hint = NALEZY_UKLID.includes(druh)
    ? "Napraví je Uklidit… v liště."
    : "Záznamy zůstávají v _metadata.json s ručními údaji; vrácený " +
      "soubor se k nim znovu připojí.";
  const dialog = h("dialog", { class: "conflict names",
    onclose: () => dialog.remove() },
    h("h2", {}, title),
    h("ul", {}, names.map((n) => h("li", {}, h("code", {}, n)))),
    h("p", { class: "meta" }, hint),
    h("div", { class: "buttons" },
      h("button", { onclick: () => dialog.close() }, "Zavřít")));
  document.body.append(dialog);
  dialog.showModal();
}

function cleanupNeeded() {
  const vyradit = Object.keys(state.doc.soubory || {})
    .some((f) => state.present.has(f) && discarded(f));
  return vyradit || (state.detail?.kontrola || [])
    .some((n) => NALEZY_UKLID.includes(n.druh))
    || damagedToRepair().length > 0;
}

// Poškozené bez rozhodnutí (stav podle dokumentu).
function damagedToRepair() {
  return Object.keys(state.detail?.poskozene || {})
    .filter((f) => damagedRepairable(f)).sort();
}

function renderBar() {
  const bar = document.getElementById("bar");
  if (!bar || !state.doc) return;
  const items = findingItems().map(({ text, onclick }) =>
    h("button", { class: "nalez", onclick }, text));
  const vyradit = Object.keys(state.doc.soubory || {})
    .filter((f) => state.present.has(f) && discarded(f)).length;
  if (vyradit) {
    items.push(h("span", { class: "info discard" },
      `${plural(vyradit, "soubor", "soubory", "souborů")} k vyřazení`));
  }
  const poskozene = Object.keys(damagedMap(
    state.detail?.poskozene || {}, state.doc.soubory)).length;
  if (poskozene) {
    items.push(h("span", {
      class: "info damaged",
      title: "Poškozené soubory z kontroly integrity;" +
        " v panelu souboru lze potvrdit „v pořádku“ nebo vyřadit",
    }, plural(poskozene, "poškozený soubor", "poškozené soubory",
      "poškozených souborů")));
  }
  if (cleanupNeeded()) {
    items.push(h("button", { disabled: !!state.readonly,
      onclick: workspaceCleanup }, "Uklidit…"));
  }
  const nove = state.detail?.nove || [];
  if (nove.length) {
    items.push(h("span", { class: "info" },
      `${plural(nove.length, "nový soubor", "nové soubory",
        "nových souborů")} od posledního otevření`));
  }
  bar.replaceChildren(...items);
}

function renderPanel() {
  const panel = document.getElementById("panel");
  if (!panel) return;
  if (state.mode === "wizard" || state.mode === "import") {
    return renderGroupsPanel(panel);
  }
  const placeBox = h("div");
  const onChange = (key) => {
    // Datum mění pořadí, autoři značky (a dědí se na soubory pod úrovní).
    changed({ grid: key === "datum" || key === "autori" });
    if (key === "misto" || key === "gps") renderPlaces(placeBox);
  };
  const afterGroupChange = () => {
    changed({ grid: true });
    renderPanel();
  };
  let title, level, ids, extra = [];
  if (state.sel.size) {
    ids = [...state.sel];
    level = "soubor";
    title = ids.length === 1 ? ids[0]
      : plural(ids.length, "soubor", "soubory", "souborů");
    const info = ids.length === 1 ? state.scan[ids[0]] : null;
    if (info) {
      extra.push(h("p", { class: "meta" },
        `Ze skenu: ${info.datum || "bez data"} · ${info.pristroj || "?"}` +
        `${info.gps ? ` · GPS ${info.gps.map((x) => x.toFixed(5))}` : ""}`));
    }
    const marked = ids.every(discarded);
    extra.push(h("div", { class: "row" }, h("button", {
      title: "Del", onclick: toggleDiscard,
    }, marked ? "Zrušit vyřazení" : "Vyřadit"),
    marked ? h("span", { class: "warn" }, " Označeno k vyřazení.") : null));
    const pos = ids.filter((f) => damagedOf(f)
      || state.doc.soubory[f]?.overeno);
    if (pos.length) {
      const confirmed = pos.every((f) => state.doc.soubory[f]?.overeno);
      const first = pos.map(damagedOf).find(Boolean);
      extra.push(h("div", { class: "row" }, h("button", {
        onclick: toggleVerified,
      }, confirmed ? "Zrušit potvrzení integrity"
                   : "Považovat za v pořádku"),
      confirmed ? h("span", { class: "meta" }, " Potvrzeno uživatelem.")
                : first ? h("span", { class: "warn damaged" }, " "
                    + damagedText(first)
                    + (pos.length > 1 ? ` (+${pos.length - 1})` : ""))
                        : null));
    }
    extra.push(groupTools(afterGroupChange));
  } else if (state.group && state.doc.skupiny[state.group]) {
    const gid = state.group;
    ids = [gid];
    level = "skupina";
    title = `Skupina: ${groupName(gid)}`;
    const nameInput = h("input", { value: groupName(gid),
      oninput: (e) => {
        state.doc.skupiny[gid].nazev = e.target.value;
        changed(); // překreslí i řádek skupiny v navigátoru
      } });
    extra.push(h("fieldset", { class: "tools" },
      h("legend", {}, "Skupina"),
      h("div", { class: "field" }, h("label", {}, "Název skupiny"),
        nameInput),
      mergeTools(gid, afterGroupChange)));
  } else {
    level = "akce";
    ids = [];
    title = "Akce";
  }
  const targets = targetsFor(level, ids);
  // Jen ke čtení: fieldset disabled zakáže všechna pole a tlačítka panelu.
  panel.replaceChildren(h("fieldset", { class: "panel-body",
    disabled: !!state.readonly },
  h("h2", {}, title),
  ...extra.filter(Boolean),
  h("div", { class: "form" },
    FIELDS[level].map((k) => fieldRow(targets, k, onChange))),
  level === "soubor" ? placeBox : null));
  if (level === "soubor") renderPlaces(placeBox);
}

// --- průvodce --------------------------------------------------------------

const wizard = { step: 0, plan: null, volby: {}, rawRoot: true,
  other: true };
const STEPS = ["Úklid", "Údaje akce", "Skupiny a autoři"];

function wizardFrame(body, nav) {
  return [
    header(),
    h("div", { class: "eventbar" }, h("a", { href: listLink() }, "← Akce"),
      h("h1", {}, state.name)),
    h("ol", { class: "steps" }, STEPS.map((s, i) => h("li", {
      class: i === wizard.step ? "current" : i < wizard.step ? "done" : "",
    }, s))),
    body,
    h("div", { class: "wnav" }, nav),
  ];
}

async function renderWizard() {
  const step = wizard.step;
  if (step === 0) return renderCleanup();
  if (step >= 1 && !state.doc) {
    await loadDetail();
    if (!state.detail.novy) {
      // Mezitím uloženo jinde: rovnou plocha.
      state.mode = "workspace";
      return renderWorkspace();
    }
  }
  if (step === 1) return renderEventStep();
  return renderWizardGroupsStep();
}

function navButtons({ back = true, next = "Pokračovat", onNext,
  disabled = false } = {}) {
  return [
    back && wizard.step > 0 ? h("button", {
      onclick: () => { wizard.step--; renderWizard(); },
    }, "← Zpět") : h("span"),
    h("button", { class: "primary", disabled, onclick: onNext ||
      (() => { wizard.step++; renderWizard(); }) }, next),
  ];
}

// Akci bez metadat prochází průvodcem někdo jiný.
function renderReadonlyWizard() {
  app.replaceChildren(header(),
    h("div", { class: "eventbar" }, h("a", { href: listLink() }, "← Akce"),
      h("h1", {}, state.name)),
    lockNotice(),
    h("main", { class: "wizard" }, h("p", {}, "Akce zatím nemá uložená " +
      "metadata. Až je průvodce uloží, uvidíte je tady ke čtení.")));
}

const OPS = { move: "přesun", rename: "přejmenování", delete: "smazání" };
const OP_STAV = { hotovo: "hotovo", blokovano: "blokováno", chyba: "chyba" };

// Řádek operace úklidu: plánu (`blocked`), nebo výsledku (`stav`).
function opRow(o) {
  const cls = o.stav ? (o.stav === "hotovo" ? ""
    : o.stav === "chyba" ? "failed" : "blocked") : o.blocked ? "blocked" : "";
  const note = o.stav ? OP_STAV[o.stav] +
    (o.stav === "hotovo" ? "" : `: ${o.chyba || o.duvod}`)
    : o.blocked ? `blokováno: ${o.duvod}` : "";
  return h("tr", { class: cls },
    h("td", {}, OPS[o.typ]), h("td", {}, h("code", {}, o.z)),
    h("td", {}, o.do ? h("code", {}, `→ ${o.do}`) : ""),
    h("td", {}, note));
}

async function executeCleanup() {
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    "Provádím úklid…"), []));
  let result;
  try {
    result = await api(eventUrl(state.name, "/uklid/provest"), {
      method: "POST", body: { volby: wizard.volby,
        raw_v_koreni: wizard.rawRoot, ostatni: wizard.other,
        relace: session() },
    });
  } catch (err) {
    if (deniedLock(err)) {
      state.readonly = deniedLock(err);
      state.locked = null;
      return lostLock();
    }
    throw err;
  }
  const count = (st) => result.operace.filter((o) => o.stav === st).length;
  const rows = result.operace.map(opRow);
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    h("p", { class: count("chyba") ? "notice error" : "notice" },
      `Hotovo ${count("hotovo")}, blokováno ${count("blokovano")}, ` +
      `chyba ${count("chyba")}. Neprovedené operace zůstaly beze změny; ` +
      "další krok pracuje se soubory, které jsou teď v kořeni."),
    h("table", { class: "ops" }, rows)),
  [h("span"), h("button", { class: "primary", onclick: () => {
    wizard.step = 1;
    renderWizard();
  } }, "Pokračovat a načíst soubory")]));
}

function sampleUrl(folder, f, size) {
  return eventUrl(state.name, `/uklid/nahled/${encodeURIComponent(folder)}/` +
    encodeURIComponent(f) + (size ? `?velikost=${size}` : ""));
}

// Ukázky obsahu podsložky: náhled s názvem, klik zvětší.
function folderSamples(folder, files) {
  const zoom = (f) => {
    const dialog = h("dialog", { class: "sample",
      onclick: () => dialog.close(), onclose: () => dialog.remove() },
      h("img", { src: sampleUrl(folder, f, LARGE), alt: "" }),
      h("p", {}, h("code", {}, f)));
    document.body.append(dialog);
    dialog.showModal();
  };
  return h("div", { class: "samples" }, files.map((f) => {
    const name = h("span", { title: f }, f);
    const img = h("img", { src: sampleUrl(folder, f), alt: "",
      loading: "lazy", title: "Zvětšit", onclick: () => zoom(f),
      onerror: () => img.remove() });
    return h("figure", {}, img, name);
  }));
}

// Volba u podsložky (průvodce i úklid z plochy): přesunout, nebo ponechat.
function folderChoice(f, onPick) {
  const name = `volba-${f.nazev}`;
  const radio = (value, label) => h("label", {},
    h("input", { type: "radio", name, value, checked: f.volba === value,
      onchange: () => onPick(value) }),
    " ", label);
  return h("div", { class: `folder${f.volba ? "" : " undecided"}` },
    h("p", {}, `Složka `, h("code", {}, f.nazev), ` obsahuje `,
      plural(f.souboru, "soubor", "soubory", "souborů"),
      f.rawu ? ` (RAW: ${f.rawu})` : "",
      f.podslozek ? `, podsložek: ${f.podslozek}` : "", "."),
    folderSamples(f.nazev, f.ukazky),
    h("div", { class: "row" },
      radio("presunout", "přesunout mezi soubory akce"),
      radio("ponechat", h("span", {}, "ponechat stranou → ",
        h("code", {}, f.cil)))),
    f.volba ? null : h("p", { class: "warn" }, "Zatím bez rozhodnutí."));
}

async function renderCleanup() {
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    "Počítám plán úklidu…"), []));
  const plan = await api(eventUrl(state.name, "/uklid"), {
    method: "POST", body: { volby: wizard.volby, raw_v_koreni: wizard.rawRoot,
      ostatni: wizard.other },
  });
  wizard.plan = plan;
  const replan = () => renderCleanup();
  const folders = plan.podslozky.map((f) => folderChoice(f, (value) => {
    wizard.volby[f.nazev] = value;
    replan();
  }));
  const rawRoot = plan.raw_v_koreni ? h("label", { class: "folder" },
    h("input", { type: "checkbox", checked: wizard.rawRoot,
      onchange: (e) => { wizard.rawRoot = e.target.checked; replan(); } }),
    ` Přesunout ${plural(plan.raw_v_koreni, "RAW", "RAWy", "RAWů")} ` +
    "z kořene do ", h("code", {}, "RAW.ignored")) : null;
  const other = plan.ostatni_v_koreni ? h("label", { class: "folder" },
    h("input", { type: "checkbox", checked: wizard.other,
      onchange: (e) => { wizard.other = e.target.checked; replan(); } }),
    ` Přesunout ${plural(plan.ostatni_v_koreni, "ostatní soubor",
      "ostatní soubory", "ostatních souborů")} (nepodporované, osiřelé ` +
    "sidecary) do ", h("code", {}, "ostatni.ignored")) : null;
  const ops = plan.operace.length
    ? h("table", { class: "ops" }, plan.operace.map(opRow))
    : h("p", {}, "Žádné operace.");
  const empty = !plan.podslozky.length && !plan.raw_v_koreni &&
    !plan.ostatni_v_koreni;
  const zapis = state.info.zapis;
  const todo = plan.operace.filter((o) => !o.blocked).length;
  let nav = navButtons({ next: "Potvrdit plán a načíst soubory" });
  if (zapis && todo) {
    // Dvojí potvrzení: operace v archivu nejdou vrátit tlačítkem.
    nav = navButtons({ next: `Provést úklid (${plural(todo, "operace",
      "operace", "operací")})`, onNext: () => {
      if (!nav[1].dataset.confirm) {
        nav[1].dataset.confirm = "1";
        nav[1].textContent = "Opravdu přesunout a přejmenovat v archivu?";
        return;
      }
      executeCleanup();
    } });
  }
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    zapis
      ? h("p", { class: "notice" }, "Po potvrzení se plán provede " +
        "v archivu: přesuny, přejmenování na .ignored a smazání " +
        "vyprázdněných složek. Nic se nepřepíše, blokované operace se " +
        "přeskočí. Složky bez rozhodnutí zůstanou, jak jsou.")
      : h("p", { class: "notice" }, "Nasucho: vývojový režim plán jen " +
        "ukazuje, v archivu nic nepřesune ani nepřejmenuje. Další krok " +
        "pracuje se soubory, které jsou v kořeni teď."),
    empty ? h("p", {}, "Kořen akce nemá podsložky, RAWy ani ostatní " +
      "soubory, není co uklízet.") : null,
    folders, rawRoot, other,
    plan.operace.length || !empty ? h("h3", {}, "Plán") : null,
    empty ? null : ops),
  nav));
}

function renderEventStep() {
  const a = state.doc.akce;
  const ok = () => a.nazev && a.datum_od && a.datum_do;
  const nav = navButtons({ disabled: !ok() });
  const targets = targetsFor("akce", []);
  const onChange = () => { nav[1].disabled = !ok(); };
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard form" },
    h("p", { class: "meta" }, "Předvyplněno z názvu složky a dat souborů."),
    FIELDS.akce.map((k) => fieldRow(targets, k, onChange))), nav));
}

// Poslední krok průvodce: skupiny a autoři, pak pracovní plocha. Změny
// se uloží až dokončením.
function renderWizardGroupsStep() {
  const warn = h("span", { class: "warn" });
  const [back, finishBtn] = navButtons({ next: "Dokončit průvodce",
    onNext: () => finish() });
  const reset = () => {
    delete finishBtn.dataset.confirm;
    finishBtn.textContent = "Dokončit průvodce";
    warn.textContent = "";
  };
  const finish = async () => {
    const m = missing(state.doc, state.present);
    if (m.skupinyBezAutoru.length && !finishBtn.dataset.confirm) {
      finishBtn.dataset.confirm = "1";
      finishBtn.textContent = "Přesto dokončit";
      warn.textContent = `${plural(m.skupinyBezAutoru.length, "skupina",
        "skupiny", "skupin")} bez autorů – doplníte i na ploše.`;
      return;
    }
    finishBtn.disabled = true;
    state.mode = "workspace";
    state.dirty = true;
    await save();
    if (state.conflict) return;
    if (state.events) {
      const e = state.events.find((x) => x.nazev === state.name);
      if (e) e.stav = "rozpracovano";
    }
    state.sel = new Set();
    state.group = null;
    renderWorkspace();
  };
  renderGroupsStep({
    frame: wizardFrame,
    nav: [back, h("span", { class: "row" }, warn, finishBtn)],
    onChange: reset,
  });
}

// --- krok skupiny a autoři (průvodce akce i import) ---------------------
//
// Mřížka (`renderGrid`) a panel nad `state.doc`: průvodce akce nad
// dokumentem akce, import nad popisem importu (`state.mode` "import",
// náhledy přes `thumbUrl`). Rozdíly nese kontext `groupsCtx`: `frame`
// a `nav` kroku, `onChange` po každé úpravě, `top` (volba rozdělení
// v importu) a `join` (připojení nové skupiny k existující, jen import:
// `target(gid)`, `choice(gid, after)`).

let groupsCtx = null;

function renderGroupsStep(ctx) {
  groupsCtx = ctx;
  Object.assign(state, { sel: new Set(), group: null, anchor: null,
    current: null, view: "grid", keptEmpty: new Set() });
  app.replaceChildren(...ctx.frame(h("div", { class: "workspace" },
    h("div", { id: "grid", class: "grid", style: `--tile: ${tileSize()}px` }),
    h("aside", { id: "panel", class: "panel" })), ctx.nav));
  setupGrid(document.getElementById("grid"));
  renderGrid();
  renderPanel();
}

// Autoři skupiny, kterou krok neupravuje (existující skupina cíle
// importu, nebo nová skupina k ní připojená).
function authorsReadonly(gid, note) {
  const names = resolveGroup(state.doc, gid).autori?.hodnota || [];
  return h("div", { class: "field readonly" },
    h("label", {}, F.autori.label, h("span", { class: "note" }, note)),
    h("div", { class: "readonly-value" }, names.join("; ") || "bez autorů"));
}

function renderGroupsPanel(panel) {
  const ctx = groupsCtx;
  const after = () => {
    ctx.onChange();
    renderGrid();
    renderPanel();
  };
  // Řádek autorů skupiny.
  const authorsRow = (gid) => {
    const target = ctx.join?.target(gid);
    if (target) {
      return authorsReadonly(target, `ze skupiny ${groupName(target)}`);
    }
    if (fixedGroup(gid)) return authorsReadonly(gid, "skupina v akci");
    return fieldRow(targetsFor("skupina", [gid]), "autori", ctx.onChange);
  };
  const groups = groupIds().map((gid) => {
    const fixed = fixedGroup(gid);
    const files = sortedFiles(Object.keys(state.doc.soubory).filter((f) =>
      state.doc.soubory[f].skupina === gid && state.present.has(f)));
    if (fixed && !files.length) return null;
    // Pár náhledů rovnoměrně z celé skupiny, ať se skupina pozná.
    const step = Math.max(1, Math.floor(files.length / 6));
    const sample = files.filter((_, i) => i % step === 0).slice(0, 6);
    return h("fieldset", { class: `tools${state.group === gid
      ? " current" : ""}` },
    h("legend", {}, plural(files.length, "soubor", "soubory", "souborů"),
      fixed ? " · skupina v akci" : ""),
    h("div", { class: "row" }, h("input", { value: groupName(gid),
      disabled: fixed, oninput: (e) => {
        state.doc.skupiny[gid].nazev = e.target.value;
        const head = document.querySelector(
          `#grid .ghead[data-group="${CSS.escape(gid)}"]`);
        if (head) head.firstChild.textContent = e.target.value;
        ctx.onChange();
      } })),
    h("div", { class: "strip" }, sample.map((f) => h("img", {
      src: thumbUrl(f), alt: "", title: f, loading: "lazy",
      onerror: (e) => e.target.remove(),
    }))),
    fixed ? null : ctx.join?.choice(gid, after),
    fixed || ctx.join?.target(gid) ? null : mergeTools(gid, after),
    authorsRow(gid));
  });
  panel.replaceChildren(h("h2", {}, "Skupiny a autoři"),
    ...[ctx.top?.(),
      h("label", { class: "tilesize", title: "Velikost náhledů v mřížce" },
        "Náhledy", h("input", { type: "range", min: TILE.min,
          max: TILE.max, step: 10, value: tileSize(),
          oninput: (e) => setTileSize(e.target.value) })),
      h("p", { class: "meta" }, "Soubory vyberte v mřížce (klik, Ctrl, " +
        "Shift, tažení) a přesuňte do skupiny. Autoři = fotil někdo " +
        "z uvedených; u jednotlivých fotek je jde přepsat na ploše."),
      excludedLine(), groupTools(after), ...groups].filter(Boolean));
  panel.querySelector("fieldset.current")?.scrollIntoView({ block: "nearest" });
}

// --- import ---------------------------------------------------------------

// Průvodce importem: soubory se nahrají do pracovního adresáře serveru
// (`#/import/<id>` přežije reload), do archivu jdou až po potvrzení
// v kroku skupiny a autoři. Popis importu (údaje nové akce, skupiny,
// autoři; `importdesc.js`) se průběžně ukládá k importu.

const IMPORT_STEPS = ["Soubory", "Přehled", "Cíl", "Plán",
  "Skupiny a autoři", "Výsledek"];
const PARALLEL = 3;
const TYP = {
  foto: ["fotka", "fotky", "fotek"],
  video: ["video", "videa", "videí"],
  raw: ["RAW", "RAWy", "RAWů"],
  nepodporovany: ["nepodporovaný", "nepodporované", "nepodporovaných"],
};
const IMPORT_STAV = { ok: "", blokovano: "blokováno", duplicita: "duplicita",
  hotovo: "hotovo", chyba: "chyba", poskozeny: "poškozený, nepřenese se",
  vylouceny: "vyloučeno" };
const IMPORT_CHYBA = {
  probiha: "import se právě provádí (jiná záložka)",
  neuplny: "přenos se přerušil",
  prilis_velky: "soubor je příliš velký",
  malo_mista: "na serveru není dost místa",
  neplatne_jmeno: "neplatné jméno souboru",
};

const IMPORT_SKUPINY = {
  podslozky: "podle podsložek",
  jedna: "jedna nová skupina",
  auto: "automaticky podle přístroje a vzoru názvu",
  zadne: "bez skupiny",
  existujici: "zařadit do skupiny",
};
const IMPORT_SKUPINY_CHYBA = {
  bez_nazvu_skupiny: "Doplňte název skupiny.",
  neznama_skupina: "Zvolená skupina v akci není.",
  neplatne_skupiny: "Neplatná volba skupin.",
  bez_planu: "Plán už neplatí; sestavte ho znovu.",
};

const imp = {
  id: null, step: 0, cil: null, picked: [], failed: [], uploading: false,
  overview: null, target: null, targetError: null, plan: null,
  result: null, lockHolder: null, error: null, busy: null,
  unsorted: null, sourceHolder: null, checking: false, checkError: null,
  checkedFor: null,
  popis: null,      // popis importu (importdesc.js)
  defaults: null,   // odpověď POST …/skupiny pro aktuální plán
  volba: null,      // výchozí rozdělení do skupin
  modes: null,      // dostupné volby rozdělení a předvolba (groupModes)
  excluded: new Set(), // cesty vyloučené z importu (vylouceni.js)
  paths: {},        // název média kroku skupin → cesta ve výběru
};

function importUrl(rest = "") {
  return `/api/import/${encodeURIComponent(imp.id)}${rest}`;
}

function fmtDate(d) {
  const [y, m, day] = d.slice(0, 10).split("-");
  return `${+day}. ${+m}. ${y}`;
}

function fmtSize(n) {
  const units = ["B", "kB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1000 && i < units.length - 1) { n /= 1000; i++; }
  return `${n.toLocaleString("cs", { maximumFractionDigits: i ? 1 : 0 })} ` +
    units[i];
}

async function openImport(id, params) {
  state.mode = "import";
  state.name = null;
  if (!id || id !== imp.id) {
    Object.assign(imp, {
      id, step: 0, cil: params.get("cil"), picked: [], failed: [],
      uploading: false, overview: null, target: null, targetError: null,
      plan: null, result: null, lockHolder: null, error: null, busy: null,
      unsorted: null, sourceHolder: null, checking: false, checkError: null,
      checkedFor: null, popis: null, defaults: null, volba: null,
      modes: null, excluded: new Set(), paths: {},
    });
    clearTimeout(exclTimer);
    exclTimer = null;
    exclDirty = false;
  }
  app.replaceChildren(header(), h("main", { class: "list" }, "Načítám…"));
  if (!userName()) await askName();
  state.events = await api("/api/akce");
  if (imp.id && !imp.overview) {
    try {
      await loadOverview();
    } catch (err) {
      if (err.status !== 404) throw err;
      app.replaceChildren(header(), h("main", { class: "wizard" },
        h("p", {}, "Import nenalezen: je zahozený, už proběhl, nebo patří " +
          "jinému uživateli."), h("a", { href: listLink() }, "← Akce")));
      return;
    }
    if (imp.overview.soubory.length || imp.overview.zdroj) imp.step = 1;
    imp.popis = imp.overview.popis; // návrat k rozpracovanému importu
    imp.excluded = new Set(imp.overview.vyloucene || []);
  }
  renderImport();
}

async function loadOverview() {
  imp.overview = await api(importUrl(
    `?jmeno=${encodeURIComponent(userName())}&relace=${session()}`));
}

// Import patří jménu, takže ho může mít otevřený i jiná záložka; dokud
// v ní nahrávání nebo kopírování běží, upozornit.
function otherTabNotice() {
  const j = imp.overview?.jinde;
  if (!j || (!j.probiha && !j.nahrava.length)) return null;
  const what = j.probiha ? "kopíruje do archivu" : "nahrává (" +
    j.nahrava.map((u) => `${u.cesta}, ${fmtSize(u.prijato)} z ` +
      fmtSize(u.velikost)).join("; ") + ")";
  return h("p", { class: "notice readonly" },
    `Import máte otevřený v jiné záložce, kde se právě ${what}. Pokud ` +
    "chcete pokračovat zde, počkejte na dokončení nebo zavřete původní " +
    "záložku.", " ", h("button", { class: "link", onclick: async () => {
      await loadOverview();
      renderImport();
    } }, "Zkusit znovu"));
}

// Ukazatel průběhu (nahrávání, porovnání, kopie); mění se přes `setProgress`
// bez překreslení pohledu.
function progressBox(text) {
  return h("div", { class: "upload" },
    h("progress", { id: "import-progress", max: 1, value: 0 }),
    h("span", { id: "import-progress-text" }, text));
}

function setProgress(fraction, text) {
  const bar = document.getElementById("import-progress");
  if (!bar) return;
  bar.value = fraction;
  document.getElementById("import-progress-text").textContent = text;
}

// Průběh kontroly poškozených souborů (`kontrola`, `kontrola_prubeh`) ve
// streamu kontroly, plánu i provedení; `total` drží úvodní událost.
function checkProgress(ev, total) {
  if (ev.typ === "kontrola") return ev;
  if (ev.typ === "kontrola_prubeh" && total) {
    setProgress(total.bajtu ? ev.hotovo_bajtu / total.bajtu : 1,
      `Kontroluji soubory: ${ev.hotovo_souboru} z ${total.souboru} · ` +
      `${fmtSize(ev.hotovo_bajtu)} z ${fmtSize(total.bajtu)}`);
  }
  return total;
}

// Tlačítko čekající na server: zablokovat, ukázat stav, dvojklik nic
// nespustí.
function setBusy(button, text) {
  button.disabled = true;
  button.textContent = text;
}

function importFrame(body, nav) {
  const notice = otherTabNotice();
  if (notice) body.prepend(notice);
  return [
    header(),
    h("div", { class: "eventbar" }, h("a", { href: listLink() }, "← Akce"),
      h("h1", {}, "Import fotek a videí"),
      imp.cil ? h("span", { class: "paths" }, `cíl: ${imp.cil}`) : null),
    h("ol", { class: "steps" }, IMPORT_STEPS.map((s, i) => h("li", {
      class: i === imp.step ? "current" : i < imp.step ? "done" : "",
    }, s))),
    body,
    h("div", { class: "wnav" }, nav),
  ];
}

function renderImport() {
  if (state.mode !== "import") return; // mezitím jinam
  [renderPick, renderOverview, renderTarget, renderImportPlan,
    renderImportGroups, renderImportResult][imp.step]();
}

function goStep(step) {
  imp.step = step;
  renderImport();
}

async function discardImport(e) {
  const button = e?.currentTarget;
  const n = imp.overview?.soubory.length || 0;
  if (imp.id && !(await confirmDialog("Zahodit import?", [
    discardText(imp.overview?.zdroj, n)], "Zahodit"))) return;
  if (imp.id) {
    const label = button?.textContent;
    if (button) setBusy(button, "Zahazuji…");
    try {
      await api(importUrl(), { method: "DELETE",
        body: { jmeno: userName() } });
    } catch (err) {
      if (err.status !== 404) {
        if (button) {
          button.disabled = false;
          button.textContent = label;
        }
        imp.error = err.data?.chyba === "probiha"
          ? "Import se právě provádí (jiná záložka), teď ho nejde zahodit."
          : `Import nejde zahodit: ${err.message}`;
        return renderImport();
      }
    }
  }
  imp.id = null;
  location.hash = "#/";
}

// Soubory z přetažení včetně podsložek (cesta = relativní cesta ve výběru).
async function droppedFiles(dt) {
  const entries = [...dt.items].map((i) => i.webkitGetAsEntry?.())
    .filter(Boolean);
  if (!entries.length) {
    return [...dt.files].map((file) => ({ file, cesta: file.name }));
  }
  const out = [];
  async function walk(entry) {
    if (entry.isFile) {
      const file = await new Promise((ok, fail) => entry.file(ok, fail));
      out.push({ file, cesta: entry.fullPath.replace(/^\//, "") });
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      for (;;) {
        const batch = await new Promise((ok, fail) =>
          reader.readEntries(ok, fail));
        if (!batch.length) break;
        for (const e of batch) await walk(e);
      }
    }
  }
  for (const e of entries) await walk(e);
  return out;
}

function renderPick() {
  const limit = state.info.import_limit;
  const add = (items) => {
    for (const it of items) {
      if (it.file.name.toLowerCase() === "thumbs.db") continue;
      if (!imp.picked.some((p) => p.cesta === it.cesta)) imp.picked.push(it);
    }
    imp.error = null;
    renderPick();
  };
  const fileInput = h("input", { type: "file", multiple: true, hidden: true,
    onchange: (e) => add([...e.target.files].map((file) =>
      ({ file, cesta: file.name }))) });
  const dirInput = h("input", { type: "file", multiple: true, hidden: true,
    webkitdirectory: true, onchange: (e) => add([...e.target.files].map(
      (file) => ({ file, cesta: file.webkitRelativePath || file.name }))) });
  const zone = h("div", {
    class: "dropzone",
    ondragover: (e) => { e.preventDefault(); zone.classList.add("over"); },
    ondragleave: () => zone.classList.remove("over"),
    ondrop: async (e) => {
      e.preventDefault();
      zone.classList.remove("over");
      add(await droppedFiles(e.dataTransfer));
    },
  }, "Přetáhněte sem soubory nebo složku, nebo ",
  h("button", { class: "link", disabled: imp.uploading,
    onclick: () => fileInput.click() }, "vyberte soubory"), " či ",
  h("button", { class: "link", disabled: imp.uploading,
    onclick: () => dirInput.click() }, "celou složku"),
  ". Soubory z podsložek se zpracují, jako by ležely v jedné úrovni.",
  fileInput, dirInput);

  const fromSource = state.me?.archivar && !imp.id && !imp.picked.length &&
    !imp.uploading ? unsortedChoice() : null;
  const tooBig = imp.picked.filter((p) => p.file.size > limit);
  const todo = imp.picked.filter((p) => p.file.size <= limit);
  const total = todo.reduce((s, p) => s + p.file.size, 0);
  const uploaded = imp.overview?.soubory.length || 0;
  const failed = new Map(imp.failed.map((f) => [f.cesta, f.chyba]));
  const rows = imp.picked.slice(0, 500).map((p) => h("tr", {
    class: failed.has(p.cesta) || p.file.size > limit ? "failed" : "" },
  h("td", {}, h("code", {}, p.cesta)), h("td", { class: "num" },
    fmtSize(p.file.size)),
  h("td", {}, p.file.size > limit ? "příliš velký, nenahraje se"
    : failed.get(p.cesta) || "")));
  const body = h("main", { class: "wizard" },
    h("p", { class: "notice" }, "Soubory se nejdřív nahrají do pracovního " +
      "adresáře serveru. Do archivu se nic nezapíše, dokud import " +
      "nepotvrdíte; zavření stránky archiv nezmění."),
    uploaded ? h("p", {}, `Už nahráno: ${plural(uploaded, "soubor",
      "soubory", "souborů")}.`) : null,
    imp.uploading ? null : zone,
    fromSource,
    imp.error ? h("p", { class: "notice error" }, imp.error) : null,
    imp.uploading ? progressBox("Nahrávám…") : null,
    imp.picked.length ? h("p", {}, `K nahrání: ${plural(todo.length,
      "soubor", "soubory", "souborů")}, ${fmtSize(total)}` +
      (tooBig.length ? `; příliš velkých (nad ${fmtSize(limit)}): ` +
        tooBig.length : "") + ".") : null,
    imp.picked.length ? h("table", { class: "ops" }, rows) : null,
    imp.picked.length > 500
      ? h("p", { class: "meta" }, `… a dalších ${imp.picked.length - 500}.`)
      : null);
  const nav = [
    h("button", { disabled: imp.uploading, onclick: discardImport },
      imp.id ? "Zahodit import" : "Zrušit"),
    h("span", { class: "row" },
      uploaded && !imp.uploading ? h("button", {
        onclick: async (e) => {
          setBusy(e.currentTarget, "Načítám přehled…");
          await loadOverview();
          goStep(1);
        },
      }, "Přeskočit na přehled") : null,
      h("button", { class: "primary", disabled: imp.uploading || !todo.length,
        onclick: () => startUpload(todo, total) },
      imp.failed.length ? "Nahrát znovu" : "Nahrát")),
  ];
  app.replaceChildren(...importFrame(body, nav));
}

// Krok Soubory: místo nahrání složka v `přetřídit` (výpis bez EXIF).
function unsortedChoice() {
  const box = h("fieldset", { class: "folder" },
    h("legend", {}, `Nebo ze složky ${UNSORTED} v archivu`));
  if (!imp.unsorted) {
    box.append(h("button", { class: "link", onclick: async (e) => {
      setBusy(e.currentTarget, "Načítám…");
      const last = await apiStream("/api/pretridit?exif=0", null, () => {})
        .catch(() => null);
      imp.unsorted = last?.slozky || [];
      renderPick();
    } }, "Ukázat složky…"));
    return box;
  }
  if (!imp.unsorted.length) {
    box.append(h("p", { class: "meta" }, `Složka ${UNSORTED} je prázdná ` +
      "nebo v archivu není."));
    return box;
  }
  box.append(h("p", { class: "meta" }, "Soubory se nenahrávají; import " +
    "je do akce přesune."), h("table", { class: "ops" },
    imp.unsorted.map((it) => {
      const button = h("button", { class: "link", onclick: () =>
        importFromSource(it.nazev, null, button) }, it.nazev);
      return h("tr", {}, h("td", {}, button),
        h("td", {}, countsText(it.pocty)),
        h("td", { class: "num" }, fmtSize(it.velikost)));
    })));
  return box;
}

function uploadOne(item, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const q = new URLSearchParams({ jmeno: userName(), relace: session(),
      cesta: item.cesta,
      mtime: item.file.lastModified });
    xhr.open("POST", importUrl(`/soubor?${q}`));
    xhr.upload.onprogress = (e) => onProgress(e.loaded);
    xhr.onload = () => {
      if (xhr.status === 200) return resolve();
      let code = null;
      try { code = JSON.parse(xhr.responseText).chyba; } catch { /* HTML */ }
      authRedirect(xhr.status, { chyba: code });
      reject(new Error(IMPORT_CHYBA[code] || `HTTP ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("spojení se serverem selhalo"));
    xhr.send(item.file);
  });
}

async function startUpload(todo, total) {
  if (imp.uploading) return;
  imp.uploading = true;
  imp.failed = [];
  imp.error = null;
  renderImport();
  if (!imp.id) {
    try {
      const r = await api("/api/import", { method: "POST",
        body: { jmeno: userName(), celkem: total } });
      imp.id = r.id;
      history.replaceState(null, "", `#/import/${r.id}` +
        (imp.cil ? `?cil=${encodeURIComponent(imp.cil)}` : ""));
    } catch (err) {
      imp.uploading = false;
      imp.error = err.data?.chyba === "malo_mista"
        ? "Na serveru není dost místa pro nahrání vybraných souborů."
        : `Import nejde založit: ${err.message}`;
      return renderImport();
    }
  }
  renderImport();
  const loaded = new Map();
  let done = 0;
  const update = () => {
    const sum = [...loaded.values()].reduce((s, n) => s + n, 0);
    setProgress(total ? sum / total : 1, `Nahráno ${done} z ${todo.length}` +
      ` · ${fmtSize(sum)} z ${fmtSize(total)}`);
  };
  const queue = [...todo];
  async function worker() {
    while (queue.length) {
      const item = queue.shift();
      try {
        await uploadOne(item, (n) => { loaded.set(item, n); update(); });
        loaded.set(item, item.file.size);
        done++;
        imp.picked.splice(imp.picked.indexOf(item), 1);
      } catch (err) {
        loaded.set(item, 0);
        imp.failed.push({ cesta: item.cesta, chyba: err.message });
      }
      update();
    }
  }
  await Promise.all(Array.from({ length: PARALLEL }, worker));
  imp.uploading = false;
  if (imp.failed.length) {
    imp.error = `Nepodařilo se nahrát ${plural(imp.failed.length, "soubor",
      "soubory", "souborů")}; ostatní jsou nahrané.`;
    return renderImport();
  }
  await loadOverview();
  goStep(1);
}

// Kontrola poškozených souborů po zobrazení přehledu; hotové z cache
// přijdou hned. Po doběhnutí se přehled načte znovu (výsledky u souborů).
async function runCheck() {
  if (imp.checking) return;
  imp.checking = true;
  imp.checkError = null;
  renderImport();
  let total = null;
  try {
    const last = await apiStream(importUrl("/kontrola"), { jmeno: userName() },
      (ev) => { total = checkProgress(ev, total); });
    if (last?.typ !== "kontrola_hotovo") throw new Error("nedoběhla");
    await loadOverview();
  } catch (err) {
    if (err.status === 404) {
      location.hash = "#/";
      return;
    }
    imp.checkError = `Kontrola souborů selhala (${err.message}); plán ` +
      "soubory zkontroluje znovu.";
  } finally {
    imp.checking = false;
  }
  renderImport();
}

async function setAllowed(cesta, on) {
  const o = imp.overview;
  try {
    const r = await api(importUrl("/poskozene"), { method: "POST", body: {
      jmeno: userName(),
      povolene: toggleAllowed(o.povolene_poskozene, cesta, on) } });
    o.povolene_poskozene = r.povolene;
    imp.error = null;
  } catch (err) {
    imp.error = err.data?.chyba === "probiha"
      ? IMPORT_CHYBA.probiha : `Volbu nejde uložit (${err.message}).`;
  }
  renderImport();
}

async function deleteDamaged(d, button) {
  const zdroj = imp.overview.zdroj;
  if (!(await confirmDialog("Smazat poškozený soubor?", [
    d.cesta, `${STAV_KONTROLY[d.stav]}: ${d.duvod}`,
    zdroj ? `Soubor se nevratně smaže ze složky ${UNSORTED}/${zdroj}.`
      : "Soubor se smaže z nahraných souborů importu; archiv se nezmění.",
  ], "Smazat"))) return;
  setBusy(button, "Mažu…");
  try {
    await api(importUrl("/soubor"), { method: "DELETE",
      body: { jmeno: userName(), relace: session(), cesta: d.cesta } });
    imp.error = null;
  } catch (err) {
    const c = err.data?.chyba;
    imp.error = c === "zdroj_obsazen"
      ? `Složku ${UNSORTED}/${zdroj} právě přesouvá ` +
        `${err.data.drzitel?.jmeno || "jiný uživatel"}; soubor teď nejde ` +
        "smazat."
      : c === "nezkontrolovano"
      ? "Soubor se od kontroly změnil; zkontrolujte ho znovu."
      : c === "probiha" ? IMPORT_CHYBA.probiha
      : `Soubor nejde smazat (${err.message}).`;
  }
  try {
    await loadOverview();
  } catch {
    location.hash = "#/";
    return;
  }
  renderImport();
}

// Výsledek kontroly v přehledu: souhrn, poškozené s důvodem, volba
// „přesto importovat“ u podezřelých a smazání (u zdroje jen v produkčním
// režimu).
function damagedBlock(o) {
  if (imp.checking) return progressBox("Kontroluji soubory…");
  const c = checkCounts(o.soubory);
  const list = damagedFiles(o.soubory, o.povolene_poskozene,
    o.odebrana_poloha);
  const error = imp.checkError
    ? h("p", { class: "notice error" }, imp.checkError) : null;
  if (!list.length) {
    return [error, c.ok && !c.nezkontrolovano ? h("p", {},
      "Kontrola souborů: ", h("strong", {}, "bez poškozených")) : null];
  }
  const canDelete = !o.zdroj || state.info.zapis;
  return [error, h("div", { class: "notice error damaged" },
    h("p", {}, `Poškozené soubory: ${plural(list.length, "soubor",
      "soubory", "souborů")} (nečitelných ${c.necitelny}, podezřelých ` +
      `${c.podezrely}). Nečitelné se do archivu nepřenesou, podezřelé jen ` +
      "po povolení; nepřenesené zůstanou " +
      (o.zdroj ? "ve zdroji." : "v pracovním adresáři.")),
    h("table", { class: "ops" }, list.map((d) => h("tr", {},
      h("td", {}, h("code", {}, d.cesta)),
      h("td", {}, STAV_KONTROLY[d.stav]),
      h("td", {}, d.duvod),
      h("td", {}, d.stav === "podezrely" ? h("label", {},
        h("input", { type: "checkbox", checked: d.povoleno,
          onchange: (e) => setAllowed(d.cesta, e.target.checked) }),
        " přesto importovat") : ""),
      h("td", {}, canDelete ? h("button", { class: "link",
        onclick: (e) => deleteDamaged(d, e.currentTarget) }, "Smazat…")
        : null)))))];
}

// Soubory s odebranou polohou v přehledu: samostatný blok s vysvětlením
// a seznamem, bez volby „přesto importovat“ a bez Smazat — soubor není
// poškozený, jen přišel bez polohy; originál je potřeba předat jinou
// cestou (`odebranaPolohaFiles`).
function odebranaPolohaBlock(o) {
  const list = odebranaPolohaFiles(o.soubory, o.odebrana_poloha);
  if (!list.length) return null;
  return h("div", { class: "notice error damaged" },
    h("p", {}, h("strong", {}, "Odebraná poloha: "),
      `${plural(list.length, "soubor", "soubory", "souborů")} ` +
      "(telefon odebral polohu). Android při předání fotky prohlížeči " +
      "nebo mailem vynuluje blok GPS v EXIF, takže soubor přijde o " +
      "polohu — pro archiv zásadní informaci. Do archivu se " +
      "nepřenesou a nelze ani povolit, ani smazat; originál předejte " +
      "jinou cestou: např. kabelem z telefonu nebo FileSenderem " +
      "z počítače."),
    h("table", { class: "ops" }, list.map((d) => h("tr", {},
      h("td", {}, h("code", {}, d.cesta)),
      h("td", {}, d.duvod)))));
}

// Operace plánu/výsledku s fotkou, které telefon odebral polohu
// (`iter_plan` je vede jako poškozené se stavem `bez_polohy`).
const bezPolohyOp = (o) => o.stav === "poskozeny"
  && o.poskozeni === "bez_polohy";

// Samostatná skupina nepřenesených s odebranou polohou v plánu i
// výsledku, s důvodem.
function bezPolohyGroup(ops, zdroj) {
  if (!ops.length) return null;
  return h("div", { class: "notice error damaged" },
    h("p", {}, "Odebraná poloha (nepřenesou se): ",
      h("strong", {}, `${ops.length}.`), " Telefon předal soubor bez " +
      "GPS polohy; zůstane " +
      (zdroj ? `ve zdroji ${UNSORTED}/${zdroj}`
        : "v pracovním adresáři") + " do zahodení importu. Originál " +
      "předejte jinou cestou (kabel, FileSender)."),
    h("table", { class: "ops" }, ops.map((o) => h("tr", { class: "failed" },
      h("td", {}, h("code", {}, o.z)),
      h("td", {}, o.duvod)))));
}

function renderOverview() {
  const o = imp.overview;
  // Kontrola se sama spustí jednou pro každou sadu nezkontrolovaných
  // souborů (soubor, který mezitím zmizel, ji nespouští dokola).
  const pending = unchecked(o.soubory).map((f) => f.cesta).join("\n");
  if (pending && !imp.checking && imp.checkedFor !== pending) {
    imp.checkedFor = pending;
    queueMicrotask(runCheck); // po vykreslení, překreslí s ukazatelem
  }
  const c = o.pocty;
  const media = (c.foto || 0) + (c.video || 0) + (c.raw || 0);
  const parts = ["foto", "video", "raw"].filter((t) => c[t])
    .map((t) => plural(c[t], ...TYP[t]));
  const dates = !o.od ? "z EXIF nezjištěno"
    : o.od === o.do ? fmtDate(o.od) : `${fmtDate(o.od)} – ${fmtDate(o.do)}`;
  const rows = o.soubory.map((f) => h("tr", {
    class: f.typ === "nepodporovany" || f.poloha_odebrana ||
      (f.kontrola && f.kontrola.stav !== "ok") ? "failed" : "" },
  h("td", {}, h("code", {}, f.cesta)),
  h("td", {}, TYP[f.typ][0], f.poloha_odebrana ? " (odebraná poloha)"
    : f.kontrola && f.kontrola.stav !== "ok"
      ? ` (${STAV_KONTROLY[f.kontrola.stav]})` : ""),
  h("td", {}, f.datum ? fmtDate(f.datum) + f.datum.slice(10)
    .replace("T", " ") : ""),
  h("td", {}, f.pristroj || ""),
  h("td", { class: "num" }, fmtSize(f.velikost))));
  const body = h("main", { class: "wizard" },
    imp.error ? h("p", { class: "notice error" }, imp.error) : null,
    h("p", {}, (o.zdroj ? `Ve složce ${UNSORTED}/${o.zdroj} je `
      : "Nahráno ") + `${plural(o.soubory.length, "soubor", "soubory",
      "souborů")}: ${parts.join(", ") || "žádná média"}.`),
    h("p", {}, "Datum: ", h("strong", {}, dates)),
    h("p", {}, "Přístroje: ", o.pristroje.join(", ") || "nezjištěny"),
    o.nepodporovane.length ? h("div", { class: "notice error" },
      "Nepodporované soubory se do archivu nepřenesou: ",
      o.nepodporovane.flatMap((n, i) => [i ? ", " : "", h("code", {}, n)]))
      : null,
    odebranaPolohaBlock(o),
    damagedBlock(o),
    h("details", {}, h("summary", {}, "Seznam souborů"),
      h("table", { class: "ops" }, rows)));
  app.replaceChildren(...importFrame(body, [
    h("span", { class: "row" },
      o.zdroj ? null : h("button", { onclick: () => goStep(0) },
        "← Přidat soubory"),
      h("button", { onclick: discardImport }, "Zahodit import")),
    h("button", { class: "primary", disabled: !media || imp.checking,
      onclick: () => goStep(2) },
    imp.checking ? "Kontroluji soubory…" : "Pokračovat"),
  ]));
}

// Nejdelší společná složka cest výběru (jako `importer.selection_root`).
function selectionRoot(files) {
  const dirs = files.map((f) => f.cesta.split(/[/\\]/).slice(0, -1));
  let root = dirs[0] || [];
  for (const d of dirs.slice(1)) {
    let n = 0;
    while (n < root.length && n < d.length && root[n] === d[n]) n++;
    root = root.slice(0, n);
  }
  return root;
}

// --- popis importu: průběžné ukládání ---------------------------------------

let descTimer = null;

// Po úpravě popisu: uložit s prodlevou. `edit` = ruční úprava skupin nebo
// autorů (změna výchozího rozdělení se pak ptá).
function descChanged(edit = true) {
  if (edit) imp.popis.upraveno = true;
  clearTimeout(descTimer);
  descTimer = setTimeout(saveDescription, 1000);
}

// Uloží popis k importu (ne do archivu); false při chybě.
async function saveDescription() {
  clearTimeout(descTimer);
  descTimer = null;
  if (!imp.id || !imp.popis) return true;
  try {
    await api(importUrl("/popis"), { method: "PUT",
      body: { jmeno: userName(), popis: imp.popis } });
    return true;
  } catch (err) {
    imp.error = `Popis importu nejde uložit (${err.message}).`;
    return false;
  }
}

// Seznam vyloučených se ukládá zvlášť (`POST …/vyloucene`), také
// s prodlevou; `exclDirty` drží neuloženou změnu i po chybě uložení.
let exclTimer = null;
let exclDirty = false;

function scheduleExcluded() {
  exclDirty = true;
  clearTimeout(exclTimer);
  exclTimer = setTimeout(saveExcluded, 1000);
}

// Uloží seznam vyloučených k importu (ne do archivu); false při chybě.
async function saveExcluded() {
  clearTimeout(exclTimer);
  exclTimer = null;
  if (!imp.id || !exclDirty) return true;
  try {
    await api(importUrl("/vyloucene"), { method: "POST",
      body: { jmeno: userName(), vyloucene: [...imp.excluded] } });
    exclDirty = false;
    return true;
  } catch (err) {
    imp.error = `Seznam vyloučených nejde uložit (${err.message}).`;
    return false;
  }
}

// --- cíl -------------------------------------------------------------------

// Údaje nové akce v popisu (krok cíl): odložené z dřívějška, jinak
// předvyplněné názvem složky a dny médií z přehledu.
function newEventFields(t) {
  const o = imp.overview;
  const p = imp.popis ||= { cil: null, typ: null, akce: {}, skupiny: {},
    soubory: {}, pripojit: {} };
  if (p.typ !== "nova") {
    // Prázdné hodnoty se nezapisují: pole by jinak hlásilo „zadáno“.
    p.akce = p.nova_akce || Object.fromEntries(Object.entries({
      nazev: t.nazev.trim(), datum_od: o.od || t.datum,
      datum_do: o.do || o.od || t.datum }).filter(([, v]) => v));
    p.typ = "nova";
    delete p.nova_akce;
  }
  // Popis uložený dřív mohl prázdné hodnoty mít.
  for (const k of Object.keys(p.akce)) {
    if (isEmpty(p.akce[k])) delete p.akce[k];
  }
  return p.akce;
}

function renderTarget() {
  const o = imp.overview;
  // Cílem jen akce, kterou uživatel smí upravit (server jinak odmítne).
  const events = (state.events || []).filter((e) => e.upravit !== false);
  // Předvyplnit: cíl z adresy (plocha akce), zvolený dřív (návrat
  // k rozpracovanému importu), jinak nová akce s datem z EXIF.
  imp.target ||= imp.cil
    ? { mode: "stavajici", cil: imp.cil, datum: o.od || "", nazev: "" }
    : o.cil && o.nova
      ? { mode: "nova", cil: events[0]?.nazev, datum: o.cil.slice(0, 10),
        nazev: o.cil.slice(11) }
      : o.cil && events.some((e) => e.nazev === o.cil)
        ? { mode: "stavajici", cil: o.cil, datum: o.od || "", nazev: "" }
        : { mode: "nova", cil: events[0]?.nazev, datum: o.od || "",
          nazev: o.zdroj || "" };
  const t = imp.target;
  if (t.mode === "stavajici" && !events.some((e) => e.nazev === t.cil)) {
    t.cil = events[0]?.nazev;
  }
  const radio = (mode, label) => h("label", {},
    h("input", { type: "radio", name: "cil", checked: t.mode === mode,
      onchange: () => { t.mode = mode; imp.targetError = null;
        renderTarget(); } }), " ", label);
  const event = events.find((e) => e.nazev === t.cil);
  const preview = h("code");
  const folder = () => `${t.datum} ${t.nazev.trim()}`;
  const updatePreview = () => { preview.textContent = folder(); };
  updatePreview();
  const existing = t.mode === "stavajici" ? h("div", { class: "folder" },
    h("select", { onchange: (e) => { t.cil = e.target.value; renderTarget(); } },
      events.filter((e) => e.stav !== "kolize").map((e) =>
        h("option", { value: e.nazev, selected: e.nazev === t.cil },
          e.nazev + (e.stav === "hotovo" ? " (hotovo)" : "")))),
    event?.stav === "hotovo" ? h("p", { class: "warn" }, "Akce je " +
      "dokončená. Immich nové soubory uvidí hned; skupiny a autoři " +
      "z importu se do sidecarů dostanou až novým dokončením akce.")
      : null) : null;
  let created = null;
  if (t.mode === "nova") {
    const a = newEventFields(t);
    const targets = [{ obj: a, level: "akce", eff: (k) =>
      k in a ? { hodnota: a[k], uroven: "akce" } : undefined }];
    const onChange = () => descChanged(false);
    const rows = Object.fromEntries(FIELDS.akce
      .map((k) => [k, fieldRow(targets, k, onChange)]));
    created = h("div", { class: "folder" },
      h("div", { class: "row" },
        h("input", { type: "date", value: t.datum,
          oninput: (e) => { t.datum = e.target.value; updatePreview(); } }),
        h("input", { type: "text", value: t.nazev, size: 50,
          placeholder: "název akce, např. kontrola Stezky",
          oninput: (e) => {
            // Název akce jde se složkou, dokud ho uživatel nezmění.
            const prev = t.nazev.trim();
            t.nazev = e.target.value;
            updatePreview();
            if ((a.nazev || "") === prev) {
              if (t.nazev.trim()) a.nazev = t.nazev.trim();
              else delete a.nazev;
              const row = fieldRow(targets, "nazev", onChange);
              rows.nazev.replaceWith(row);
              rows.nazev = row;
              descChanged(false);
            }
          } })),
      h("p", { class: "meta" }, "Složka: ", preview,
        o.od ? "" : " (datum z EXIF nezjištěno, doplňte ho)"),
      h("div", { class: "form" }, h("h3", {}, "Údaje akce"),
        Object.values(rows)));
  }
  const err = imp.targetError;
  const planning = imp.busy === "plan";
  const body = h("main", { class: "wizard" },
    h("div", { class: "row" }, radio("stavajici", "do stávající akce"),
      radio("nova", "do nové akce")),
    existing, created,
    planning ? progressBox("Sestavuji plán…") : null,
    err ? h("p", { class: "notice error" }, err.text,
      err.akce ? [" ", h("button", { class: "link", onclick: () => {
        Object.assign(t, { mode: "stavajici", cil: err.akce });
        imp.targetError = null;
        renderTarget();
      } }, "Zvolit ji jako stávající")] : null) : null);
  const next = async () => {
    if (imp.busy) return;
    const body = { jmeno: userName() };
    if (t.mode === "stavajici") body.cil = t.cil;
    else if (!t.datum || !t.nazev.trim()) {
      imp.targetError = { text: "Doplňte datum i název složky nové akce." };
      return renderTarget();
    } else if (!imp.popis.akce.nazev || !imp.popis.akce.datum_od) {
      imp.targetError = { text: "Doplňte název akce a datum od." };
      return renderTarget();
    } else body.nova = folder();
    imp.busy = "plan";
    imp.targetError = null;
    renderTarget();
    await saveDescription();
    await saveExcluded();
    let total = null;
    try {
      let checkTotal = null;
      const last = await apiStream(importUrl("/plan"), body, (ev) => {
        checkTotal = checkProgress(ev, checkTotal);
        if (ev.typ === "hash") total = ev;
        else if (ev.typ === "hash_prubeh") {
          setProgress(total.bajtu ? ev.hotovo_bajtu / total.bajtu : 1,
            `Porovnávám se soubory akce stejné velikosti: ` +
            `${ev.hotovo_souboru} z ${total.souboru} · ` +
            `${fmtSize(ev.hotovo_bajtu)} z ${fmtSize(total.bajtu)}`);
        }
      });
      if (last?.typ !== "plan") throw new Error("plán nedorazil celý");
      imp.plan = last;
      imp.defaults = null;
    } catch (e) {
      imp.busy = null;
      if (e.status !== 409) {
        imp.targetError = { text: `Plán nejde sestavit: ${e.message}` };
        return renderTarget();
      }
      const known = events.some((x) => x.nazev === e.data.akce);
      imp.targetError = e.data.chyba === "existuje"
        ? { text: `Složka ${e.data.akce} v archivu už je.`,
          akce: known ? e.data.akce : null }
        : { text: "Neplatný název: složka musí mít tvar „YYYY-MM-DD " +
          "název“ a nesmí obsahovat / ani \\." };
      return renderTarget();
    }
    imp.busy = null;
    imp.targetError = null;
    imp.lockHolder = null;
    goStep(3);
  };
  app.replaceChildren(...importFrame(body, [
    h("button", { disabled: planning, onclick: () => goStep(1) }, "← Zpět"),
    h("button", { class: "primary",
      disabled: planning || (t.mode === "stavajici" && !t.cil),
      onclick: next }, planning ? "Počítám plán…" : "Ukázat plán"),
  ]));
}

// --- plán ------------------------------------------------------------------

// `group(gid)` = popis cílové skupiny (bez ní sloupec chybí).
function importOps(ops, group) {
  return h("table", { class: "ops" }, ops.map((o) => h("tr", {
    class: o.stav === "hotovo" || o.stav === "ok" ? ""
      : o.stav === "chyba" || o.stav === "poskozeny" ? "failed"
        : o.stav === "duplicita" ? "dup"
          : o.stav === "vylouceny" ? "excluded" : "blocked" },
  h("td", {}, h("code", {}, o.z)), h("td", {}, h("code", {}, `→ ${o.do}`)),
  group ? h("td", {}, o.skupina ? group(o.skupina) : "") : null,
  h("td", { class: "num" }, fmtSize(o.velikost)),
  h("td", {}, o.poskozeni === "bez_polohy"
    ? "odebraná poloha, nepřenese se" : IMPORT_STAV[o.stav],
    o.stav === "hotovo" || o.stav === "ok" || o.stav === "vylouceny"
    ? "" : `: ${o.chyba || o.duvod}`))));
}

function countBy(ops) {
  const c = {};
  for (const o of ops) c[o.stav] = (c[o.stav] || 0) + 1;
  return (st) => c[st] || 0;
}

function renderImportPlan() {
  // Plán podle aktuálního vyloučení (krok skupin ho mohl od sestavení
  // změnit; server ho při provedení použije také).
  const p = { ...imp.plan, operace: withExcluded(imp.plan.operace,
    imp.excluded) };
  const n = countBy(p.operace);
  const bezPolohy = p.operace.filter(bezPolohyOp);
  const zdroj = imp.overview?.zdroj;
  const body = h("main", { class: "wizard" },
    imp.error ? h("p", { class: "notice error" }, imp.error) : null,
    h("p", { class: "notice" }, "Plán ukazuje, co se přenese. Skupiny " +
      "a autory zadáte v dalším kroku; do archivu se zatím nic nezapíše."),
    h("p", {}, p.nova ? "Vznikne nová akce " : "Cíl: ",
      h("code", {}, p.cil), "."),
    h("p", {}, `Přenese se ${n("ok")}, blokováno ${n("blokovano")}, ` +
      `duplicit ${n("duplicita")}` + (bezPolohy.length
        ? `, s odebranou polohou ${bezPolohy.length}` : "") +
      (n("poskozeny") - bezPolohy.length
        ? `, poškozených (nepřenesou se) ` +
          `${n("poskozeny") - bezPolohy.length}` : "") +
      (n("vylouceny") ? `, vyloučeno ${n("vylouceny")}.` : ".")),
    p.nepodporovane.length ? h("p", { class: "meta" },
      `Nepodporované (nepřenesou se): ${p.nepodporovane.join(", ")}`) : null,
    bezPolohyGroup(bezPolohy, zdroj),
    importOps(p.operace));
  // Vše vyloučené jde v kroku skupin zase vrátit.
  const go = h("button", { class: "primary",
    disabled: !n("ok") && !n("vylouceny"),
    onclick: () => enterImportGroups(go) },
  "Pokračovat ke skupinám a autorům");
  app.replaceChildren(...importFrame(body, [
    h("span", { class: "row" },
      h("button", { onclick: () => goStep(2) }, "← Zpět"),
      h("button", { onclick: discardImport }, "Zahodit import")),
    go,
  ]));
}

// --- skupiny a autoři --------------------------------------------------------

// Volby výchozího rozdělení a předvolba (spec photo-import, Volba
// skupin). `tg` = skupiny cíle (`GET /api/akce/<n>/skupiny`).
function groupModes(tg) {
  const files = imp.overview.soubory;
  const root = selectionRoot(files);
  const hasSub = files.some((f) =>
    f.cesta.split(/[/\\]/).length - 1 > root.length);
  const own = tg.zdroj === "metadata" ? tg.skupiny || {} : {};
  return {
    root, own,
    avail: ["podslozky", "jedna", "auto", "zadne", "existujici"]
      .filter((m) => (m !== "podslozky" || hasSub) &&
        (m !== "existujici" || Object.keys(own).length)),
    preset: hasSub ? "podslozky" : tg.zdroj === "metadata" ? "jedna" : "auto",
    nazev: root.at(-1) || `Import ${new Date().toLocaleDateString("sv")}`,
  };
}

function presetVolba(m) {
  const volba = { rezim: m.preset };
  if (m.preset === "jedna") volba.nazev = m.nazev;
  return volba;
}

// Výchozí rozdělení přenášených médií podle `volba` (server plán znovu
// nepočítá).
function loadDefaults(volba) {
  return api(importUrl("/skupiny"), { method: "POST",
    body: { jmeno: userName(), skupiny: volba } });
}

// Z plánu do kroku skupiny a autoři: volba rozdělení (uložená, jinak
// předvolba), výchozí rozdělení a popis sladěný s plánem.
async function enterImportGroups(button) {
  const label = button.textContent;
  setBusy(button, "Sestavuji skupiny…");
  try {
    const p = imp.plan;
    const tg = p.nova ? { zdroj: null }
      : await api(`/api/akce/${encodeURIComponent(p.cil)}/skupiny`);
    const m = imp.modes = groupModes(tg);
    const saved = imp.volba || imp.overview.skupiny;
    const volba = saved && m.avail.includes(saved.rezim) &&
      (saved.rezim !== "existujici" || saved.skupina in m.own)
      ? saved : presetVolba(m);
    const d = await loadDefaults(volba);
    imp.defaults = d;
    imp.volba = volba;
    imp.paths = mediaPaths(d);
    if (imp.popis?.cil === targetKey(d)) reconcile(imp.popis, d);
    else imp.popis = freshDescription(d, imp.popis);
    imp.error = (await saveDescription()) ? null : imp.error;
  } catch (err) {
    button.disabled = false;
    button.textContent = label;
    imp.error = IMPORT_SKUPINY_CHYBA[err.data?.chyba] ||
      `Skupiny nejde sestavit (${err.message}).`;
    return renderImport();
  }
  goStep(4);
}

// Změna výchozího rozdělení sestaví skupiny znovu; ruční úpravy a autoři
// skupin se zahodí jen po potvrzení. Údaje a autoři akce zůstanou.
async function changeVolba(volba) {
  if (volba.rezim === "jedna" && !volba.nazev) {
    imp.error = IMPORT_SKUPINY_CHYBA.bez_nazvu_skupiny;
    return renderImport();
  }
  if (imp.popis.upraveno && !(await confirmDialog("Rozdělit znovu?", [
    "Skupiny se sestaví znovu podle nové volby; ruční úpravy skupin " +
    "a jejich autoři se zahodí."], "Rozdělit znovu"))) {
    return renderImport();
  }
  try {
    const d = await loadDefaults(volba);
    const akce = imp.popis.akce;
    imp.defaults = d;
    imp.volba = volba;
    imp.paths = mediaPaths(d);
    imp.popis = freshDescription(d, imp.popis);
    imp.popis.akce = akce;
    imp.error = (await saveDescription()) ? null : imp.error;
  } catch (err) {
    imp.error = IMPORT_SKUPINY_CHYBA[err.data?.chyba] ||
      `Skupiny nejde sestavit (${err.message}).`;
  }
  renderImport();
}

// Volba výchozího rozdělení nahoře v panelu.
function importVolbaBlock() {
  const m = imp.modes;
  const v = imp.volba;
  const name = h("input", { type: "text", value: v.rezim === "jedna"
    ? v.nazev : m.nazev, size: 24 });
  const own = Object.keys(m.own);
  return h("fieldset", { class: "tools" }, h("legend", {}, "Výchozí rozdělení"),
    h("select", { onchange: (e) => {
      const rezim = e.target.value;
      if (rezim === "jedna") return changeVolba({ rezim, nazev: m.nazev });
      if (rezim === "existujici") {
        return changeVolba({ rezim, skupina: own[0] });
      }
      changeVolba({ rezim });
    } }, m.avail.map((r) => h("option", { value: r, selected: r === v.rezim },
      IMPORT_SKUPINY[r]))),
    v.rezim === "jedna" ? h("div", { class: "row" }, name,
      h("button", { onclick: () => changeVolba({ rezim: "jedna",
        nazev: name.value.trim() }) }, "Přejmenovat")) : null,
    v.rezim === "existujici" ? h("div", { class: "row" }, h("select", {
      onchange: (e) => changeVolba({ rezim: "existujici",
        skupina: e.target.value }) },
    own.map((id) => h("option", { value: id, selected: id === v.skupina },
      m.own[id].nazev || id)))) : null,
    v.rezim === "podslozky" ? h("p", { class: "meta" }, "Skupina = " +
      "podsložka první úrovně" + (m.root.length ? ` pod ${m.root.join("/")}`
        : "") + ". RAWy skupinu nedostanou.") : null);
}

// Nová skupina: „nová skupina“, nebo „připojit ke skupině …“ cíle (shody
// první); změna plán nepřepočítává.
function joinChoice(gid, after) {
  const ex = imp.defaults.existujici;
  if (!Object.keys(ex).length) return null;
  const shody = imp.defaults.shody?.[gid] || [];
  const order = [...shody,
    ...Object.keys(ex).filter((x) => !shody.includes(x))];
  return h("div", { class: "row" }, h("select", { onchange: (e) => {
    if (e.target.value) imp.popis.pripojit[gid] = e.target.value;
    else delete imp.popis.pripojit[gid];
    after();
  } }, h("option", { value: "" }, "nová skupina"),
  order.map((x) => h("option", { value: x,
    selected: imp.popis.pripojit[gid] === x },
  `připojit ke skupině ${ex[x].nazev || x}` +
    (shody.includes(x) ? " (shoda)" : "")))));
}

// Co se při provedení zapíše (vývojový režim i kontrola před importem).
function descriptionLines() {
  const p = imp.popis;
  const doc = effectiveDoc(p, excludedNames());
  const lines = [];
  const a = p.akce;
  if (imp.defaults.nova) {
    lines.push(`Nová akce ${imp.plan.cil}: ${a.nazev}, ${a.datum_od}` +
      (a.datum_do && a.datum_do !== a.datum_od ? ` – ${a.datum_do}` : "") +
      (a.mista?.length ? `, místa ${a.mista.join("; ")}` : "") +
      (a.ucastnici?.length ? `, účastníci ${a.ucastnici.join("; ")}` : ""));
  }
  const counts = new Map();
  for (const r of Object.values(doc.soubory)) {
    counts.set(r.skupina || "", (counts.get(r.skupina || "") || 0) + 1);
  }
  for (const [gid, n] of counts) {
    if (!gid) continue;
    const autori = resolveGroup(doc, gid).autori?.hodnota || [];
    lines.push(`${fixedGroup(gid) ? "Skupina v akci" : "Nová skupina"} ` +
      `${doc.skupiny[gid]?.nazev || gid}: ${plural(n, "soubor", "soubory",
        "souborů")}, autoři ${autori.join("; ") || "chybí"}`);
  }
  if (counts.get("")) {
    lines.push(`Bez skupiny: ${plural(counts.get(""), "soubor", "soubory",
      "souborů")}`);
  }
  const ex = excludedNames().size;
  if (ex) {
    lines.push(`Vyloučeno z importu (nezapíše se): ${plural(ex, "médium",
      "média", "médií")}`);
  }
  return lines;
}

function linesDialog(title, lines) {
  const dialog = h("dialog", { class: "conflict names",
    onclose: () => dialog.remove() },
  h("h2", {}, title),
  h("ul", {}, lines.map((l) => h("li", {}, l))),
  h("div", { class: "buttons" },
    h("button", { onclick: () => dialog.close() }, "Zavřít")));
  document.body.append(dialog);
  dialog.showModal();
}

// --- vyloučení z importu -----------------------------------------------------

// Název média kroku skupin → cesta ve výběru (vyloučení je podle cest).
function mediaPaths(d) {
  return Object.fromEntries(d.soubory.map((f) => [f.nazev, f.cesta]));
}

function excludedFile(f) {
  return state.mode === "import" && imp.excluded.has(imp.paths[f]);
}

// Názvy vyloučených médií (pro popis a upozornění na autory).
function excludedNames() {
  return new Set(Object.keys(imp.paths)
    .filter((f) => imp.excluded.has(imp.paths[f])));
}

// Řádek panelu „Vyloučeno: N médií, M RAWů“ (jen když něco vyloučeno).
function excludedLine() {
  if (state.mode !== "import") return null;
  const c = excludedCounts(imp.excluded, Object.values(imp.paths),
    imp.defaults?.raw || []);
  if (!c.media && !c.raw) return null;
  return h("p", { class: "warn" }, `Vyloučeno: ${plural(c.media, "médium",
    "média", "médií")}, ${plural(c.raw, "RAW", "RAWy", "RAWů")}`);
}

// Dotaz, zda s fotkami vyloučit i jejich RAWy: "raw", "foto", nebo null
// (Esc, celé vyloučení se zruší).
function askRaws(n) {
  return new Promise((resolve) => {
    const close = (value) => {
      dialog.close();
      dialog.remove();
      resolve(value);
    };
    const dialog = h("dialog", { class: "conflict" },
      h("h2", {}, "Vyloučit i RAWy?"),
      h("p", {}, `K vylučovaným fotkám patří ${plural(n, "RAW", "RAWy",
        "RAWů")} stejného jména.`),
      h("div", { class: "buttons" },
        h("button", { class: "primary", onclick: () => close("raw") },
          "Vyloučit i RAWy"),
        h("button", { onclick: () => close("foto") }, "Jen fotky")));
    dialog.addEventListener("cancel", (e) => {
      e.preventDefault();
      close(null);
    });
    document.body.append(dialog);
    dialog.showModal();
  });
}

// Del a tlačítko v kroku skupin importu: vybraná média vyloučí, jsou-li
// už všechna vyloučená, vrátí je (i s jejich RAWy). Výběr zůstává.
async function toggleExcluded() {
  const files = [...state.sel].map((f) => imp.paths[f]).filter(Boolean);
  if (state.mode !== "import" || !files.length) return;
  const t = planToggle(imp.excluded, files, imp.defaults?.raw || []);
  let raws = t.raws;
  if (t.exclude && raws.length) {
    const choice = await askRaws(raws.length);
    if (!choice) return;
    if (choice === "foto") raws = [];
  }
  imp.excluded = applyToggle(imp.excluded, files, t.exclude, raws);
  scheduleExcluded();
  groupsCtx?.onExclude?.();
  renderGrid();
  renderPanel();
}

function renderImportGroups() {
  const d = imp.defaults;
  const p = imp.popis;
  Object.assign(state, { doc: p, detail: null, readonly: null,
    present: new Set(Object.keys(p.soubory)),
    scan: Object.fromEntries(d.soubory.map((f) => [f.nazev, f])) });
  const zapis = state.info.zapis;
  const zdroj = imp.overview?.zdroj;
  const warn = h("span", { class: "warn" });
  // Počet bez vyloučených; vyloučí-li se vše, tlačítko je vypnuté.
  const label = () => {
    const n = importCount(imp.plan.operace, imp.excluded);
    return `Importovat (${plural(n, "soubor", "soubory", "souborů")})`;
  };
  const go = h("button", { class: "primary", onclick: () => {
    if (!go.dataset.confirm) {
      const bez = groupsWithoutAuthors(p, excludedNames());
      go.dataset.confirm = "1";
      warn.textContent = bez.length ? `${plural(bez.length, "skupina",
        "skupiny", "skupin")} bez autorů: ${bez.map(groupName)
        .join(", ")}.` : "";
      go.textContent = (bez.length ? "Přesto importovat – " : "Opravdu ") +
        (zdroj ? "přesunout do archivu?" : "zkopírovat do archivu?");
      return;
    }
    executeImport(go);
  } });
  const reset = () => {
    delete go.dataset.confirm;
    go.textContent = label();
    go.disabled = !importCount(imp.plan.operace, imp.excluded);
    warn.textContent = "";
  };
  reset();
  const holder = imp.lockHolder;
  const notices = [
    imp.error ? h("p", { class: "notice error" }, imp.error) : null,
    zapis ? null : h("p", { class: "notice" }, "Vývojový režim: import " +
      "se neprovede a popis se nezapíše; tlačítkem Co by se zapsalo " +
      "uvidíte, co by se zapsalo."),
    holder ? h("p", { class: "notice readonly" },
      `${holderText(holder)} Import teď nejde provést; ` + (zdroj
        ? "soubory zůstávají ve zdroji."
        : "nahrané soubory zůstávají v pracovním adresáři.")) : null,
    imp.sourceHolder ? h("p", { class: "notice readonly" },
      `Složku ${UNSORTED}/${zdroj} právě přesouvá ` +
      `${imp.sourceHolder.jmeno}. Import teď nejde provést.`) : null,
  ].filter(Boolean);
  renderGroupsStep({
    frame: (body, nav) => importFrame(
      h("div", { class: "import-groups" }, notices, body), nav),
    nav: [
      h("span", { class: "row" },
        h("button", { onclick: () => goStep(3) }, "← Zpět"),
        h("button", { onclick: discardImport }, "Zahodit import")),
      h("span", { class: "row" }, warn,
        h("button", { onclick: () => linesDialog("Co se zapíše",
          descriptionLines()) }, "Co by se zapsalo"),
        zapis ? go : null),
    ],
    onChange: () => {
      descChanged();
      reset();
    },
    onExclude: reset,
    top: importVolbaBlock,
    join: { target: (gid) => p.pripojit[gid], choice: joinChoice },
  });
}

async function executeImport(button) {
  if (imp.busy) return;
  imp.busy = "provest";
  setBusy(button, "Připravuji…");
  const p = imp.plan;
  const zdroj = imp.overview?.zdroj;
  imp.sourceHolder = null;
  // Provedení bere popis a vyloučené z importu: nejdřív uložit poslední
  // úpravy.
  if (!(await saveDescription()) || !(await saveExcluded())) {
    imp.busy = null;
    return renderImport();
  }
  if (!p.nova && !(await acquireLock(p.cil))) {
    imp.busy = null;
    imp.lockHolder = state.readonly;
    state.readonly = null;
    return renderImport();
  }
  app.replaceChildren(...importFrame(h("main", { class: "wizard" },
    h("p", {}, zdroj ? `Přesouvám ze složky ${UNSORTED}/${zdroj}. Zavření ` +
      "stránky přesun zastaví: přesunuté soubory zůstanou v akci, ostatní " +
      "ve zdroji."
      : "Kopíruji do archivu. Zavření stránky kopírování zastaví: " +
      "přenesené soubory zůstanou v archivu, ostatní v pracovním " +
      "adresáři."), progressBox("Připravuji…")), []));
  let start = null;
  let total = null;
  let copied = 0;
  let files = 0;
  let checkTotal = null;
  try {
    const last = await apiStream(importUrl("/provest"), {
      jmeno: userName(), relace: session(),
      [p.nova ? "nova" : "cil"]: p.cil,
    }, (ev) => {
      checkTotal = checkProgress(ev, checkTotal);
      if (ev.typ === "hash") total = ev;
      else if (ev.typ === "hash_prubeh") {
        setProgress(total.bajtu ? ev.hotovo_bajtu / total.bajtu : 1,
          `Porovnávám se soubory akce: ${ev.hotovo_souboru} z ` +
          `${total.souboru}`);
      } else if (ev.typ === "start") start = ev;
      else if (ev.typ === "prubeh" || ev.typ === "soubor") {
        const now = ev.typ === "prubeh" ? ev.bajtu : 0;
        if (ev.typ === "soubor" && ev.operace.stav === "hotovo") {
          files++;
          copied += ev.operace.velikost;
        }
        setProgress(start.bajtu ? (copied + now) / start.bajtu : 1,
          `${zdroj ? "Přesunuto" : "Zkopírováno"} ${files} z ` +
          `${start.souboru} · ` +
          `${fmtSize(copied + now)} z ${fmtSize(start.bajtu)}`);
      }
    });
    if (last?.typ !== "vysledek") throw new Error("výsledek nedorazil");
    imp.result = last;
  } catch (err) {
    imp.busy = null;
    if (err.status === 423) {
      imp.lockHolder = err.data?.drzitel || { jmeno: "jiný uživatel" };
      releaseLock();
      return renderImport();
    }
    if (err.status === 409 && err.data?.chyba === "existuje") {
      imp.targetError = { text: `Složka ${err.data.akce} mezitím vznikla.` };
      return goStep(2);
    }
    if (err.status === 409 && err.data?.chyba === "bez_planu") {
      imp.targetError = { text: "Plán už neplatí (import se mezitím " +
        "provedl jinde); sestavte ho znovu." };
      if (!p.nova) releaseLock();
      return goStep(2);
    }
    if (err.status === 409 && err.data?.chyba === "zdroj_obsazen") {
      imp.sourceHolder = err.data.drzitel || { jmeno: "jiný uživatel" };
      if (!p.nova) releaseLock();
      return renderImport();
    }
    if (err.status === 409 && err.data?.chyba === "probiha") {
      imp.targetError = { text: "Import se právě provádí v jiné záložce." };
      return goStep(2);
    }
    if (err.status) throw err;
    // Spojení se přerušilo uprostřed: přenesené jsou v archivu.
    imp.targetError = { text: `Přenos se přerušil (${err.message}). ` +
      "Přenesené soubory jsou v archivu, ostatní zůstaly " +
      (zdroj ? "ve zdroji" : "v pracovním adresáři") +
      "; sestavte plán znovu." };
    state.events = await api("/api/akce").catch(() => state.events);
    try {
      await loadOverview();
    } catch {
      location.hash = "#/";
      return;
    }
    return goStep(2);
  }
  imp.busy = null;
  // Novou akci server zamkl pro tuhle relaci; klient zámek převezme.
  if (p.nova) await acquireLock(p.cil).catch(() => false);
  state.events = await api("/api/akce");
  goStep(5);
}

function renderImportResult() {
  const r = imp.result;
  const n = countBy(r.operace);
  const bezPolohy = r.operace.filter(bezPolohyOp);
  const zdroj = imp.overview?.zdroj;
  const left = Object.values(r.zdroj_zbyva || {}).reduce((a, b) => a + b, 0);
  const body = h("main", { class: "wizard" },
    h("p", { class: n("chyba") ? "notice error" : "notice" },
      `Přeneseno ${n("hotovo")}, blokováno ${n("blokovano")}, duplicit ` +
      `${n("duplicita")}, ` + (bezPolohy.length
        ? `s odebranou polohou ${bezPolohy.length}, ` : "") +
      (n("poskozeny") - bezPolohy.length
        ? `poškozených ${n("poskozeny") - bezPolohy.length}, ` : "") +
      (n("vylouceny") ? `vyloučeno ${n("vylouceny")}, ` : "") +
      `chyba ${n("chyba")}.` + (r.zahozeno || zdroj ? ""
        : " Nepřenesené soubory zůstaly v pracovním adresáři, dokud " +
          "import nezahodíte.")),
    zdroj ? h("p", {}, r.zdroj_smazan
      ? `Složka ${UNSORTED}/${zdroj} se vyprázdnila a byla smazána.`
      : `Ve složce ${UNSORTED}/${zdroj} ` + (left ? `zůstal${left === 1
        ? "" : left < 5 ? "y" : "o"} ${plural(left, "soubor", "soubory",
        "souborů")} (${countsText(r.zdroj_zbyva)}); složka zůstala.`
        : "nezůstaly žádné soubory; složka zůstala.")) : null,
    r.po_planu?.length ? h("div", { class: "notice readonly" },
      `Po sestavení plánu přibyly do zdroje soubory (${r.po_planu.length}); ` +
      "nepřesunuly se a zůstaly ve zdroji (pro přesun sestavte nový " +
      "plán): ",
      r.po_planu.flatMap((c, i) => [i ? ", " : "", h("code", {}, c)]))
      : null,
    r.nepodporovane.length ? h("p", { class: "meta" },
      `Nepodporované (nepřeneseno): ${r.nepodporovane.join(", ")}`) : null,
    r.smazano?.length ? h("p", { class: "meta" }, "Smazány zbytky " +
      `přerušeného importu (starší než hodina): ${r.smazano.join(", ")}`)
      : null,
    r.skupiny && !r.skupiny.zapsano ? h("p", { class: "notice error" },
      `Popis se nepodařilo zapsat (${r.skupiny.chyba}); přenesené ` +
      "soubory jsou v akci bez skupiny a autorů, doplňte je na ploše " +
      "nebo v průvodci akce.") : null,
    r.index?.length ? h("p", { class: "notice error" },
      `Index archivu se nepodařilo aktualizovat: ${r.index.join("; ")}`)
      : null,
    r.skupiny?.zapsano && r.skupiny.navrh
      ? h("p", { class: "meta" }, "Akce zatím nemá _metadata.json: " +
        "skupiny a autoři se použijí jako návrh v průvodci při prvním " +
        "otevření akce.") : null,
    bezPolohyGroup(bezPolohy, zdroj),
    importOps(r.operace, r.skupiny && ((gid) =>
      r.skupiny.nazvy?.[gid] || gid)));
  app.replaceChildren(...importFrame(body, [
    r.zahozeno ? h("span") : h("button", { onclick: discardImport },
      zdroj ? "Zahodit import" : "Zahodit nepřenesené"),
    h("button", { class: "primary", onclick: () => {
      location.hash = `#/akce/${encodeURIComponent(r.cil)}`;
    } }, "Otevřít akci"),
  ]));
}

// --- nastavení (jen admin: Immich, Nominatim) -------------------------------

// Klíč se do prohlížeče nevrací; server ukáže jen jeho poslední 4 znaky.
let settingsTimer = null;

async function showSettings() {
  state.mode = "settings";
  state.name = null;
  clearTimeout(settingsTimer);
  if (!state.me?.admin) {
    app.replaceChildren(header(), h("main", { class: "list settings" },
      h("h1", {}, "Nastavení"),
      h("p", {}, "Nastavení serveru mění jen admin.")));
    return;
  }
  const [s, nominatim] = await Promise.all([api("/api/immich"),
    api("/api/nominatim")]);
  let knihovny = [];
  if (s.nastaveno) {
    // Uložená knihovna zůstane volbou i bez spojení, jinak by ji
    // uložení nastavení smazalo.
    try {
      knihovny = (await api("/api/immich/knihovny")).knihovny || [];
    } catch {
      knihovny = []; // Immich nedostupný
    }
    if (s.knihovna && !knihovny.some((k) => k.id === s.knihovna)) {
      knihovny.push({ id: s.knihovna, name: s.knihovna });
    }
  }
  const msg = h("p", { class: "status" });
  const varovani = h("div", {});
  const say = (text, error = false) => {
    msg.textContent = text;
    msg.className = error ? "status error" : "status";
  };
  const adresa = h("input", { value: s.adresa || "",
    placeholder: "http://10.10.1.51:2283" });
  const klic = h("input", { type: "password", autocomplete: "off",
    placeholder: s.nastaveno ? `klíč nastaven (${s.klic}) – vyplňte jen ` +
      "pro změnu" : "API klíč (osoby, assety, obličeje)" });
  const knihovna = h("select", {},
    h("option", { value: "" }, "— není vybrána —"),
    ...knihovny.map((k) => h("option", {
      value: k.id, selected: k.id === s.knihovna }, k.name || k.id)));
  const refresh = async () => {
    state.info = await api("/api/info");
    await showSettings();
  };
  const saveSettings = async () => {
    try {
      await api("/api/immich", { method: "PUT",
        body: { adresa: adresa.value, klic: klic.value,
          knihovna: knihovna.value } });
      await refresh();
    } catch (err) {
      say({ klic_povinny: "Při změně adresy zadejte klíč znovu.",
        spatna_adresa: "Adresa musí začínat http:// nebo https://." }[
        err.data?.chyba] || `Uložení selhalo: ${err.message}`, true);
    }
  };
  const test = async () => {
    say("Zkouším připojení…");
    varovani.replaceChildren();
    try {
      const r = await api("/api/immich/test", { method: "POST" });
      say(`Připojení funguje: Immich ${r.verze}, osob ${r.osob}.`);
      varovani.replaceChildren(...(r.varovani || []).map(
        (w) => h("p", { class: "warn" }, w)));
    } catch (err) {
      say(`Připojení nefunguje: ${err.data?.chyba || err.message}`, true);
    }
  };
  const remove = async () => {
    await api("/api/immich", { method: "DELETE" });
    await refresh();
  };
  const sync = async () => {
    await api("/api/immich/sync", { method: "POST" });
    await showSettings();
  };
  app.replaceChildren(header(), h("main", { class: "list settings" },
    h("h1", {}, "Nastavení"),
    h("h2", {}, "Immich"),
    h("p", {}, "Osoby na fotkách se přebírají z pojmenovaných obličejů " +
      "v Immichi. Klíč potřebuje čtení osob, assetů a obličejů; pro " +
      "alba akcí, sken knihovny a nástroj pojmenování i práva k zápisu " +
      "a uživatele s rolí admin. Test připojení vypíše, co chybí."),
    h("div", { class: "field" }, h("label", {}, "Adresa serveru"), adresa),
    h("div", { class: "field" }, h("label", {}, "API klíč"), klic),
    s.nastaveno ? h("div", { class: "field" },
      h("label", {}, "Knihovna archivu (sken po dokončení akce)"),
      knihovna) : null,
    h("div", { class: "row" },
      h("button", { class: "primary", onclick: saveSettings }, "Uložit"),
      s.nastaveno ? h("button", { onclick: test }, "Otestovat") : null,
      s.nastaveno ? h("button", { onclick: remove }, "Smazat") : null),
    msg,
    varovani,
    s.nastaveno ? syncBlock(s.synchronizace, sync) : null,
    // Chyby alba (spojení, oprávnění) stav akce nemění; alb se ujme
    // až další synchronizace. Ukazují se jen adminovi.
    s.nastaveno && s.alba_chyby?.length
      ? h("section", {}, h("h2", {}, "Alba akcí"),
          ...s.alba_chyby.map((a) => h("p", { class: "warn" },
            `${a.akce}: ${a.chyba}`)))
      : null,
    contactBlock(nominatim, refresh)));
  if (s.synchronizace.bezi) {
    settingsTimer = setTimeout(() => {
      if (state.mode === "settings") showSettings();
    }, 2000);
  }
}

// Kontakt provozovatele do User-Agent Nominatimu: jeden pro celý server.
function contactBlock(n, refresh) {
  const msg = h("p", { class: "status" });
  const kontakt = h("input", { value: n.kontakt || n.navrh || "",
    placeholder: "e-mail nebo URL provozovatele" });
  const saveContact = async () => {
    try {
      await api("/api/nominatim", { method: "PUT",
        body: { kontakt: kontakt.value } });
      await refresh();
    } catch (err) {
      msg.className = "status error";
      msg.textContent = err.data?.chyba === "kontakt_povinny"
        ? "Zadejte kontakt." : `Uložení selhalo: ${err.message}`;
    }
  };
  const remove = async () => {
    await api("/api/nominatim", { method: "DELETE" });
    await refresh();
  };
  return h("section", {},
    h("h2", {}, "Geokódování míst (Nominatim)"),
    h("p", {}, "Souřadnice míst se hledají ve veřejném Nominatimu " +
      "(OpenStreetMap). Jeho podmínky vyžadují kontakt na provozovatele; " +
      "je jeden pro celý server, ne po uživatelích. Bez něj jdou " +
      "souřadnice zadat jen ručně."),
    h("div", { class: "field" }, h("label", {},
      n.kontakt ? "Kontakt" : "Kontakt (zatím nenastaven)"), kontakt),
    h("div", { class: "row" },
      h("button", { class: "primary", onclick: saveContact }, "Uložit"),
      n.kontakt ? h("button", { onclick: remove }, "Smazat") : null),
    msg);
}

function syncBlock(st, sync) {
  const last = st.posledni;
  const lines = [];
  if (st.bezi) lines.push("Načítám osoby z Immiche…");
  if (last && !last.ok) {
    lines.push(`Poslední běh ${last.cas} selhal: ${last.chyba}`);
    lines.push(st.posledni_uspesny
      ? `Poslední úspěšný běh: ${st.posledni_uspesny.cas}`
      : "Zatím žádný úspěšný běh.");
  } else if (last) {
    lines.push(`Poslední běh: ${last.cas}`);
    lines.push(last.zmenene.length
      ? `Změněné akce: ${last.zmenene.join(", ")}` : "Beze změn.");
  } else if (!st.bezi) {
    lines.push("Synchronizace zatím neproběhla.");
  }
  if (last?.preskocene?.length) {
    lines.push(`Přeskočené (otevřené se zámkem): ` +
      last.preskocene.join(", "));
  }
  return h("section", {},
    h("h2", {}, "Osoby z Immiche"),
    h("p", { class: "meta" }, "Načítají se po startu serveru a pak každých " +
      "15 minut; akce otevřená se zámkem se přeskočí."),
    ...lines.map((l) => h("p", { class: last && !last.ok ? "warn" : "" }, l)),
    h("button", { onclick: sync, disabled: st.bezi }, "Načíst osoby"));
}

// --- start ------------------------------------------------------------------

[state.me, state.info] = await Promise.all([api("/api/ja"),
  api("/api/info")]);
route();
