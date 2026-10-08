// Klient: seznam akcí, průvodce prvním otevřením a pracovní
// plocha. Stav (dokument `_metadata.json`) drží klient a ukládá ho celý.

import { parts, withDay, withTime } from "./datetime.js";
import { missing, resolve, resolveGroup } from "./inherit.js";
import {
  STAV_KONTROLY, applyDecisionChanges, checkCounts, cleanupDecisions,
  damagedFiles, damagedMap, damagedText, decisionChanges, toggleAllowed,
  unchecked,
} from "./integrity.js";
import { byDay, dayLabel, personIndex, stripeStops } from "./sections.js";

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

function thumbUrl(f, size) {
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
const CHYBI = { autori: "autoři", datum: "data", misto: "místa" };

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
  group: null,       // vybraná hlavička skupiny
  anchor: null,
  order: [],         // pořadí souborů v mřížce (pro Shift)
  view: "grid",      // "grid" | "loupe"
  // "skupiny" | "datum": oddíly plochy; volba prohlížeče, ne akce.
  layout: localStorage.getItem("zobrazeni") === "datum" ? "datum" : "skupiny",
  current: null,     // aktuální soubor (lupa)
  preload: [],
  sessionNames: new Set(),
  keptEmpty: new Set(), // prázdné skupiny, které uživatel chtěl ponechat
  dirty: false,
  saving: false,
  conflict: false,
  locked: null,      // akce, jejíž zámek tahle relace drží
  readonly: null,    // držitel cizího zámku otevřené akce, nebo null
  placeOpen: null,   // místo, jehož volba souřadnic je otevřená
  geo: {},           // název místa → odpověď /api/geokodovani
  exporting: false,  // běží export nebo dokončení
  exportVersion: null, // verze `_metadata.json` posledního exportu
  exportNote: "",    // stav exportu u tlačítka
  exportStale: true, // sidecary nejsou ověřeně aktuální
  exportErrors: [],  // chyby posledního exportu po souborech
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

// Získá zámek akce; při cizím zámku nastaví `state.readonly` (držitel).
async function acquireLock(name) {
  try {
    await api(eventUrl(name, "/zamek"), {
      method: "POST", body: { relace: session(), jmeno: userName() },
    });
  } catch (err) {
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
      // Zámek uvolnil admin: znovu nezískávat, rozdělané změny propadly.
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

// Admin uvolní cizí zámek (opuštěná rozdělaná práce) a akci otevře.
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
  if (r.uvolnil) {
    return h("p", { class: "notice readonly" },
      `Zámek akce uvolnil admin ${r.uvolnil}. Jen ke čtení – ` +
      "neuložené změny se neuloží.",
      " ", h("button", { class: "link", onclick: () => route() },
        "Zkusit znovu"));
  }
  const own = nameKey(r.jmeno) === nameKey(userName());
  return h("p", { class: "notice readonly" },
    `${holderText(r)} Jen ke čtení – změny se neukládají.`,
    " ", h("button", { class: "link", onclick: () => route() },
      "Zkusit znovu"),
    state.me?.admin && state.me.prihlaseni && !own
      ? [" · ", h("button", { class: "link", onclick: forceRelease },
        "Uvolnit zámek")] : null);
}

// Zámek získal někdo jiný: zahodit plánované uložení a přepnout jen
// ke čtení.
function lostLock() {
  if (!state.readonly) state.readonly = { jmeno: "jiný uživatel" };
  state.dirty = false;
  if (state.mode === "workspace") renderWorkspace();
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
  if (state.dirty || state.saving || imp.uploading) e.preventDefault();
});
document.addEventListener("keydown", (e) => {
  if (state.mode !== "workspace" ||
      e.target.closest("input, textarea, select") ||
      document.querySelector("dialog[open]")) return;
  const loupe = state.view === "loupe";
  if (e.key === "Escape") {
    if (loupe) setView("grid");
    else select(new Set(), null);
  } else if (e.key === "Delete") {
    e.preventDefault();
    toggleDiscard();
  } else if (e.key === "Enter" && !loupe && !e.target.closest("button, a")) {
    e.preventDefault();
    setView("loupe");
  } else if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && loupe &&
             !e.altKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    step(e.key === "ArrowRight" ? 1 : -1, e.shiftKey);
  }
});

async function route() {
  if (state.dirty && state.mode === "workspace") await save();
  const m = location.hash.match(/^#\/akce\/(.+)$/);
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
  } else if (name) await openEvent(name);
  else await showList();
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
  const [events, pending] = await Promise.all([api("/api/akce"),
    userName() ? api(`/api/import?jmeno=${encodeURIComponent(userName())}`)
      .then((r) => r.importy).catch(() => []) : []]);
  state.events = events;
  const rows = state.events.map((e) =>
    h("tr", { class: `stav-${e.stav}` },
      h("td", {}, e.datum),
      h("td", {}, h("a", { href: `#/akce/${encodeURIComponent(e.nazev)}` },
        e.nazev.slice(11))),
      h("td", { class: "num" }, e.souboru),
      h("td", {}, h("span", { class: "badge",
        title: e.stav === "kolize" ? KOLIZE : null }, STAV[e.stav]),
        e.chybi.length ? h("span", { class: "badge nekompletni",
          title: "Chybí: " + e.chybi.map((k) => CHYBI[k]).join(", ") },
          "nekompletní") : null,
        Object.keys(e.kontrola || {}).length
          ? [h("span", { class: "badge vyresit" }, "k vyřešení"),
            h("span", { class: "vyresit-detail" },
              ` ${nalezyText(e.kontrola)}`)] : null,
        e.poskozene
          ? h("span", { class: "badge poskozene",
            title: "Poškozené soubory z kontroly integrity" },
            plural(e.poskozene, "poškozený", "poškozené", "poškozených"))
          : null,
        e.zmeneno_po_exportu
          ? h("span", { class: "warn" }, " změněno po exportu") : null)));
  app.replaceChildren(header(), h("main", { class: "list" },
    h("div", { class: "row" }, h("h1", {}, "Akce"),
      h("button", { onclick: () => { location.hash = "#/import"; } },
        "Importovat fotky a videa…"),
      h("a", { href: "#/pretridit" }, "Přetřídit")),
    pendingImports(pending),
    h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Datum"), h("th", {}, "Akce"),
        h("th", {}, "Souborů"), h("th", {}, "Stav"))),
      h("tbody", {}, rows))));
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
    h("div", { class: "row" }, h("a", { href: "#/" }, "← Akce"),
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

async function openEvent(name) {
  Object.assign(state, {
    name, detail: null, doc: null, version: null, mode: null,
    sel: new Set(), group: null, anchor: null, dirty: false,
    conflict: false, view: "grid", current: null, readonly: null,
    placeOpen: null, exporting: false, exportVersion: null, exportNote: "",
    exportStale: true, exportErrors: [],
  });
  // Stav akce se mohl změnit u jiného uživatele.
  const events = state.events = await api("/api/akce");
  const entry = events.find((e) => e.nazev === name);
  if (!entry) {
    app.replaceChildren(header(), h("main", {}, "Akce nenalezena."));
    return;
  }
  if (entry.stav === "kolize") {
    app.replaceChildren(header(), h("main", {}, KOLIZE));
    return;
  }
  if (!userName()) await askName();
  if (name !== state.name) return; // mezitím jinam
  await acquireLock(name);
  if (state.readonly) {
    await loadDetail();
    state.dirty = false;
    if (state.detail.novy) {
      state.mode = "wizard";
      renderReadonlyWizard();
    } else {
      state.mode = "workspace";
      renderWorkspace();
    }
    return;
  }
  if (entry.stav === "nezpracovano") {
    state.mode = "wizard";
    wizard.step = 0;
    wizard.volby = {};
    wizard.rawRoot = true;
    wizard.other = true;
    renderWizard();
  } else {
    await loadDetail();
    if (state.doc && state.detail.novy) {
      state.mode = "wizard";
      wizard.step = 1;
      renderWizard();
    } else {
      state.mode = "workspace";
      renderWorkspace();
    }
  }
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
    } else if (err.status === 423 && name === state.name) {
      state.readonly = err.data?.drzitel;
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
    if (used.has(gid) || state.keptEmpty.has(gid)) continue;
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
  return h("fieldset", { class: "tools" },
    h("legend", {}, `Skupina (${plural(files.length, "soubor", "soubory",
      "souborů")})`),
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
  const others = groupIds().filter((g) => g !== gid);
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

function sortedFiles(names) {
  return names.sort((a, b) => {
    const da = resolve(state.doc, a).datum?.hodnota || "";
    const db = resolve(state.doc, b).datum?.hodnota || "";
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

// Funkce soubor → značka (nebo null) pro aktuální zobrazení.
function markFn() {
  if (state.mode !== "workspace") return () => null;
  const authors = (f) => (resolve(state.doc, f).autori?.hodnota || [])
    .filter((n) => typeof n === "string" && n.trim());
  const files = Object.keys(state.doc.soubory);
  const people = personIndex(files.flatMap(authors), nameKey);
  return (f) => {
    if (discarded(f)) return null;
    const names = authors(f);
    if (!names.length) {
      return { stops: null, title: "bez autorů", label: ["bez autorů"] };
    }
    const colors = names.map((n) => color(people.get(nameKey(n))));
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

// Oddíl: `key` jednoznačně v rámci zobrazení, `gid` jen u skupiny.
function sections() {
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
  const result = [...byGroup].map(([gid, files]) =>
    ({ gid, key: `g:${gid}`, title: groupName(gid),
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
  const datum = resolve(state.doc, f).datum?.hodnota;
  const mark = markOf(f);
  const m = markAttrs(mark, f);
  const d = damagedAttrs(f);
  const thumb = present
    ? h("img", {
      src: eventUrl(state.name, `/nahled/${encodeURIComponent(f)}`),
      loading: "lazy", alt: "", draggable: false,
      onerror: (e) => e.target.replaceWith(
        h("div", { class: "ph" }, info.video ? "▶ video" : "bez náhledu")),
    })
    : h("div", { class: "ph" }, "chybí v kořeni");
  return h("div", {
    class: `tile${present ? "" : " missing"}${info.video ? " video" : ""}` +
      `${state.sel.has(f) ? " selected" : ""}${discarded(f) ? " discard" : ""}` +
      d.cls + m.cls,
    dataset: { file: f }, title: d.title || m.title, style: m.style,
  }, thumb,
  h("div", { class: "cap" }, h("span", { class: "fn" }, f),
    h("span", { class: "dt" }, datum ? datum.replace("T", " ") : "bez data"),
    mark && h("span", { class: "gn" }, mark.label)));
}

function renderGrid() {
  const grid = document.getElementById("grid");
  if (!grid) return;
  const secs = sections();
  const markOf = markFn();
  state.order = secs.flatMap((s) => s.files);
  const nodes = secs.map((s) => h("section", {},
    h("h3", {
      class: `ghead${s.gid && state.group === s.gid ? " selected" : ""}`,
      dataset: { group: s.gid || "", key: s.key },
    }, s.title, h("span", { class: "count" }, ` ${s.files.length}`)),
    h("div", { class: "tiles" }, s.files.map((f) => tile(f, markOf)))));
  const scroll = grid.scrollTop;
  grid.replaceChildren(...nodes, h("div", { id: "band", hidden: true }));
  grid.scrollTop = scroll;
  renderFilm(secs);
}

function select(files, group, opts = {}) {
  state.sel = files;
  state.group = group;
  for (const el of document.querySelectorAll("#grid .tile, #film .ftile")) {
    el.classList.toggle("selected", files.has(el.dataset.file));
  }
  for (const el of document.querySelectorAll("#film .ftile")) {
    el.classList.toggle("current", el.dataset.file === state.current);
  }
  for (const el of document.querySelectorAll("#grid .ghead, #film .fhead")) {
    el.classList.toggle("selected", !!group && el.dataset.group === group);
  }
  if (state.view === "loupe") renderBig();
  if (!opts.keepPanel) {
    state.placeOpen = opts.place ?? null;
    renderPanel();
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
      if (err.status === 423) {
        dialog.close();
        dialog.remove();
        state.readonly = err.data?.drzitel;
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

// Šipky v lupě: další/předchozí soubor; se Shiftem rozšíří výběr od kotvy.
function step(dir, extend) {
  const i = state.order.indexOf(state.current);
  const f = state.order[i < 0 ? 0 : i + dir];
  if (!f) return;
  state.current = f;
  if (extend) {
    if (!state.order.includes(state.anchor)) {
      state.anchor = state.order[Math.max(i, 0)];
    }
    select(new Set(range(state.anchor, f)), null);
  } else {
    state.anchor = f;
    select(new Set([f]), null);
  }
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
  akce: ["nazev", "datum_od", "datum_do", "popis", "mista", "ucastnici",
    "autori"],
  skupina: ["autori", "pristroj", "popis", "misto", "datum_od", "datum_do"],
  soubor: ["datum", "autori", "popis", "osoby", "misto", "pristroj", "gps"],
};

const LEVEL = { akce: "akce", skupina: "skupiny", soubor: "souboru",
  misto: "souřadnic místa" };

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
  const note = h("span", { class: "note" }, "z Immiche");
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
  return h("div", { class: "field readonly" },
    h("label", {}, F.osoby.label, " ", note),
    h("div", { class: "readonly-value" }, text));
}

function fieldRow(targets, key, onChange) {
  const def = F[key];
  if (def.type === "faces") return facesRow(targets.map((t) => t.file));
  const st = fieldState(targets, key);
  const inherited = !st.anyOwn && !isEmpty(st.value);
  const row = h("div", {
    class: `field${st.mixed ? " mixed" : ""}` +
      `${inherited ? " inherited" : ""}${st.anyOwn ? " own" : ""}` +
      `${inherited && st.from === "misto" ? " from-place" : ""}`,
  });
  const update = (value) => {
    setField(targets, key, value);
    row.classList.remove("mixed", "inherited", "from-place");
    row.classList.toggle("own", !isEmpty(value));
    note.textContent = noteText();
    onChange(key);
  };
  const noteText = () => {
    const s = fieldState(targets, key);
    if (s.mixed && !s.allOwn) return "rozdílné hodnoty";
    if (s.mixed) return "rozdílné hodnoty (zadané)";
    if (!s.anyOwn && !isEmpty(s.value)) return `zděděno z ${LEVEL[s.from]}`;
    if (s.anyOwn && !s.allOwn) return "zadáno jen u části výběru";
    return "";
  };
  const note = h("span", { class: "note" }, noteText());
  const revert = targets[0].level !== "akce" && st.anyOwn
    ? h("button", {
      class: "link", title: "Smazat zadanou hodnotu a dědit",
      onclick: () => {
        for (const t of targets) delete t.obj[key];
        onChange(key);
        row.replaceWith(fieldRow(targets, key, onChange));
      },
    }, "vrátit na zděděné")
    : null;
  const shown = st.mixed ? undefined : st.value;
  const placeholder = st.mixed ? "rozdílné hodnoty – zápisem přepíšete vše"
    : inherited ? format(def.type, st.value) : "";
  const input = def.type === "datetime"
    ? dateTimeEditor(targets, key, () => {
      row.classList.remove("inherited", "from-place");
      const s = fieldState(targets, key);
      row.classList.toggle("mixed", s.mixed);
      row.classList.toggle("own", s.anyOwn);
      note.textContent = noteText();
      onChange(key);
    })
    : editor(def.type, inherited ? undefined : shown, placeholder,
      update, inherited ? st.value : undefined);
  row.append(h("label", {}, def.label, " ", note, revert), input);
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
    body.append(h("p", { class: "meta" },
      `${decision.gps.join(", ")}`,
      decision.popis ? h("br") : null, decision.popis || null), open);
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
      ...found.map((k, i) => h("label", { class: "candidate" },
        h("input", { type: "radio", name, value: String(i),
          checked: i === pre }),
        h("span", {}, h("b", {}, k.nazev), " ", k.popis,
          h("span", { class: "meta" }, ` (${k.gps.join(", ")})`)))),
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
  const lines = missingItems().map((i) => i.text);
  if (lines.length && !(await confirmDialog("Akci něco chybí nebo je " +
    "k vyřešení", lines, "Přesto dokončit"))) return;
  const name = state.name;
  state.exporting = true;
  state.exportErrors = [];
  renderExportStatus();
  try {
    const r = await api(eventUrl(name, "/dokoncit"), {
      method: "POST", body: { relace: session(), version: state.version },
    });
    if (name !== state.name) return;
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
    } else if (err.status === 423) {
      state.readonly = err.data?.drzitel;
      state.locked = null;
      clearInterval(heartbeatTimer);
      lostLock();
    }
    state.exportStale = true;
    state.exportNote = `Export selhal: ${err.message}`;
  } finally {
    state.exporting = false;
  }
  renderExportStatus();
  if (state.dirty && !state.conflict) scheduleSave();
}

// --- pracovní plocha -------------------------------------------------------

function renderWorkspace() {
  const d = state.detail;
  const back = h("a", { href: "#/" }, "← Akce");
  app.replaceChildren(
    header(h("span", { id: "save-status", class: "status" })),
    h("div", { class: "eventbar" }, back,
      h("h1", {}, state.name),
      h("span", { class: "paths" }, d.pracovni_soubor),
      h("span", { class: "views" },
        h("button", { dataset: { view: "grid" }, title: "Esc",
          onclick: () => setView("grid") }, "Mřížka"),
        h("button", { dataset: { view: "loupe" },
          title: "Enter nebo dvojklik", onclick: () => setView("loupe") },
        "Lupa")),
      h("span", { class: "views" },
        h("button", { dataset: { layout: "skupiny" },
          class: state.layout === "skupiny" ? "active" : "",
          title: "Oddíly podle skupin",
          onclick: () => setLayout("skupiny") }, "Po skupinách"),
        h("button", { dataset: { layout: "datum" },
          class: state.layout === "datum" ? "active" : "",
          title: "Všechny soubory podle data pořízení, oddíly po dnech",
          onclick: () => setLayout("datum") }, "Podle data")),
      h("button", { disabled: !!state.readonly,
        title: "Nahrát do akce další fotky a videa", onclick: () => {
          location.hash = `#/import?cil=${encodeURIComponent(state.name)}`;
        } }, "Importovat…"),
      h("span", { class: "export" },
        h("span", { id: "export-status" }),
        h("button", { id: "finish", class: "primary",
          disabled: !!state.readonly, title: exportTarget(),
          onclick: () => finishEvent() }, "Dokončit akci"))),
    lockNotice(),
    h("div", { id: "bar", class: "bar" }),
    h("div", { class: "workspace" },
      h("div", { id: "grid", class: "grid" }),
      h("div", { id: "loupe", class: "loupe", hidden: true },
        h("div", { id: "big", class: "big" }),
        h("div", { id: "film", class: "film" })),
      h("aside", { id: "panel", class: "panel" })));
  setupGrid(document.getElementById("grid"));
  setupFilm(document.getElementById("film"));
  renderGrid();
  setView(state.view);
  renderBar();
  renderPanel();
  setStatus();
  renderExportStatus();
  if (state.dirty) scheduleSave();
}

// Chybějící údaje jako [{text, onclick}] pro lištu i dokončení akce.
function missingItems() {
  const m = missing(state.doc, state.present);
  const items = [];
  const item = (text, onclick) => items.push({ text, onclick });
  if (m.akce.length) {
    const names = {
      nazev: "název", datum_od: "datum od", datum_do: "datum do",
    };
    item(`Akce: chybí ${m.akce.map((k) => names[k]).join(", ")}`,
      () => select(new Set(), null));
  }
  if (m.skupinyBezAutoru.length) {
    item(`${plural(m.skupinyBezAutoru.length, "skupina", "skupiny",
      "skupin")} bez autorů`, () => {
      const g = m.skupinyBezAutoru[0];
      select(new Set(), g);
      document.querySelector(`#grid .ghead[data-group="${CSS.escape(g)}"]`)
        ?.scrollIntoView({ block: "start" });
    });
  }
  const files = (list, label) => {
    if (!list.length) return;
    item(`${plural(list.length, "soubor", "soubory", "souborů")} ${label}`,
      () => {
        state.anchor = list[0];
        state.current = list[0];
        select(new Set(list), null);
        document.querySelector(
          `#grid .tile[data-file="${CSS.escape(list[0])}"]`)
          ?.scrollIntoView({ block: "center" });
      });
  };
  files(m.souboryBezData, "bez data");
  files(m.souboryBezSkupiny, "bez skupiny");
  files(m.souboryBezMista, "bez místa");
  const places = Object.keys(m.mistaBezSouradnic);
  if (places.length) {
    item(`${plural(places.length, "místo", "místa", "míst")} bez souřadnic`,
      () => openPlace(places[0], m.mistaBezSouradnic[places[0]]));
  }
  // Nálezy kontroly kořene akce (issue #11): klik ukáže názvy.
  const nalezy = state.detail?.kontrola || [];
  for (const druh of Object.keys(NALEZY)) {
    const names = nalezy.filter((n) => n.druh === druh).map((n) => n.nazev);
    if (names.length) {
      const text = nalez(druh, names.length);
      item(text, () => namesDialog(text, names, druh));
    }
  }
  return items;
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
  const items = missingItems().map(({ text, onclick }) =>
    h("button", { class: "miss", onclick }, text));
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
  bar.replaceChildren(...(items.length ? items
    : [h("span", { class: "ok" }, "Nic nechybí.")]));
}

function renderPanel() {
  const panel = document.getElementById("panel");
  if (!panel) return;
  if (state.mode === "wizard") return renderWizardPanel(panel);
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
        changed();
        const head = document.querySelector(
          `#grid .ghead[data-group="${CSS.escape(gid)}"]`);
        if (head) head.firstChild.textContent = e.target.value;
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
const STEPS = ["Úklid", "Načtení a skupiny", "Údaje akce", "Autoři skupin"];

function wizardFrame(body, nav) {
  return [
    header(),
    h("div", { class: "eventbar" }, h("a", { href: "#/" }, "← Akce"),
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
  if (step === 1) return renderGroupsStep();
  if (step === 2) return renderEventStep();
  return renderAuthorsStep();
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
    h("div", { class: "eventbar" }, h("a", { href: "#/" }, "← Akce"),
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
    if (err.status === 423) {
      state.readonly = err.data?.drzitel;
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

function renderGroupsStep() {
  app.replaceChildren(...wizardFrame(h("div", { class: "workspace" },
    h("div", { id: "grid", class: "grid" }),
    h("aside", { id: "panel", class: "panel" })), navButtons()));
  setupGrid(document.getElementById("grid"));
  renderGrid();
  renderPanel();
}

function renderWizardPanel(panel) {
  // Krok skupiny: přejmenovat, sloučit, nová skupina, přesun souborů.
  const after = () => {
    renderGrid();
    renderPanel();
  };
  const groups = groupIds().map((gid) => {
    const count = Object.values(state.doc.soubory)
      .filter((r) => r.skupina === gid).length;
    return h("fieldset", {
      class: `tools${state.group === gid ? " current" : ""}` },
    h("legend", {}, plural(count, "soubor", "soubory", "souborů")),
    h("div", { class: "row" }, h("input", { value: groupName(gid),
      oninput: (e) => {
        state.doc.skupiny[gid].nazev = e.target.value;
        const head = document.querySelector(
          `#grid .ghead[data-group="${CSS.escape(gid)}"]`);
        if (head) head.firstChild.textContent = e.target.value;
      } })),
    mergeTools(gid, after));
  });
  panel.replaceChildren(
    h("h2", {}, "Skupiny"),
    h("p", { class: "meta" }, "Navrženo podle přístroje a vzoru názvu. " +
      "Soubory vyberte v mřížce (klik, Ctrl, Shift, tažení) a přesuňte."),
    ...[groupTools(after), ...groups].filter(Boolean));
}

function renderEventStep() {
  const a = state.doc.akce;
  const ok = () => a.nazev && a.datum_od && a.datum_do;
  const nav = navButtons({ disabled: !ok() });
  const targets = targetsFor("akce", []);
  const onChange = () => { nav[1].disabled = !ok(); };
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard form" },
    h("p", { class: "meta" }, "Předvyplněno z názvu složky a dat souborů."),
    FIELDS.akce.filter((k) => k !== "autori")
      .map((k) => fieldRow(targets, k, onChange))), nav));
}

function renderAuthorsStep() {
  // Řádek autorů skupiny se vykreslí jednou; po změně autorů akce se
  // nahradí novým, ať ukazuje aktuální zděděnou hodnotu.
  const groupRows = {};
  const groupRow = (gid) =>
    fieldRow(targetsFor("skupina", [gid]), "autori", () => {});
  const onEventChange = () => {
    for (const gid of Object.keys(groupRows)) {
      const row = groupRow(gid);
      groupRows[gid].replaceWith(row);
      groupRows[gid] = row;
    }
    delete finishBtn.dataset.confirm;
    finishBtn.textContent = "Dokončit průvodce";
    warn.textContent = "";
  };
  const eventBox = h("fieldset", { class: "tools" },
    h("legend", {}, "Celá akce"),
    h("p", { class: "meta" },
      "Skupiny bez vlastních autorů zdědí autory akce."),
    fieldRow(targetsFor("akce", []), "autori", onEventChange));
  const rows = groupIds().map((gid) => {
    const count = Object.values(state.doc.soubory)
      .filter((r) => r.skupina === gid).length;
    // Pár náhledů rovnoměrně z celé skupiny, ať se skupina pozná.
    const files = sortedFiles(Object.keys(state.doc.soubory)
      .filter((f) => state.doc.soubory[f].skupina === gid &&
        state.present.has(f)));
    const step = Math.max(1, Math.floor(files.length / 8));
    const sample = files.filter((_, i) => i % step === 0).slice(0, 8);
    return h("fieldset", { class: "tools" },
      h("legend", {}, `${groupName(gid)} (${plural(count, "soubor",
        "soubory", "souborů")})`),
      h("div", { class: "strip" }, sample.map((f) => h("img", {
        src: eventUrl(state.name, `/nahled/${encodeURIComponent(f)}`),
        alt: "", title: f, loading: "lazy",
        onerror: (e) => e.target.remove(),
      }))),
      groupRows[gid] = groupRow(gid));
  });
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
  const warn = h("p", { class: "warn" });
  const nav = navButtons({ next: "Dokončit průvodce", onNext: finish });
  const finishBtn = nav[1];
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    h("p", { class: "meta" }, "Autoři = fotil někdo z uvedených. " +
      "U jednotlivých fotek jde autory přepsat na ploše."),
    eventBox, rows, warn), nav));
}

// --- import ---------------------------------------------------------------

// Průvodce importem: soubory se nahrají do pracovního adresáře serveru
// (`#/import/<id>` přežije reload), do archivu jdou až po potvrzení plánu.

const IMPORT_STEPS = ["Soubory", "Přehled", "Cíl", "Plán", "Výsledek"];
const PARALLEL = 3;
const TYP = {
  foto: ["fotka", "fotky", "fotek"],
  video: ["video", "videa", "videí"],
  raw: ["RAW", "RAWy", "RAWů"],
  nepodporovany: ["nepodporovaný", "nepodporované", "nepodporovaných"],
};
const IMPORT_STAV = { ok: "", blokovano: "blokováno", duplicita: "duplicita",
  hotovo: "hotovo", chyba: "chyba", poskozeny: "poškozený, nepřenese se" };
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
};

const imp = {
  id: null, step: 0, cil: null, picked: [], failed: [], uploading: false,
  overview: null, target: null, targetError: null, plan: null,
  result: null, lockHolder: null, error: null, busy: null,
  groups: null, targetGroups: null, pripojit: {}, unsorted: null,
  sourceHolder: null, checking: false, checkError: null, checkedFor: null,
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
      groups: null, targetGroups: null, pripojit: {}, unsorted: null,
      sourceHolder: null, checking: false, checkError: null,
      checkedFor: null,
    });
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
          "jinému uživateli."), h("a", { href: "#/" }, "← Akce")));
      return;
    }
    if (imp.overview.soubory.length || imp.overview.zdroj) imp.step = 1;
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
    h("div", { class: "eventbar" }, h("a", { href: "#/" }, "← Akce"),
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
    renderImportResult][imp.step]();
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

  const fromSource = !imp.id && !imp.picked.length && !imp.uploading
    ? unsortedChoice() : null;
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
  const list = damagedFiles(o.soubory, o.povolene_poskozene);
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
    class: f.typ === "nepodporovany" ||
      (f.kontrola && f.kontrola.stav !== "ok") ? "failed" : "" },
  h("td", {}, h("code", {}, f.cesta)),
  h("td", {}, TYP[f.typ][0], f.kontrola && f.kontrola.stav !== "ok"
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

// Skupiny cílové akce bez skenu (`_metadata.json`, jinak návrh z importu);
// načtou se na pozadí a krok cíle se pak překreslí.
function targetGroups(cil) {
  if (imp.targetGroups?.cil === cil) return imp.targetGroups;
  imp.targetGroups = { cil, loading: true };
  api(`/api/akce/${encodeURIComponent(cil)}/skupiny`)
    .then((r) => { imp.targetGroups = { cil, ...r }; })
    .catch(() => { imp.targetGroups = { cil, skupiny: null, zdroj: null }; })
    .then(() => { if (imp.step === 2) renderTarget(); });
  return imp.targetGroups;
}

function importGroupsBlock(t) {
  const o = imp.overview;
  const tg = t.mode === "stavajici" ? targetGroups(t.cil)
    : { skupiny: null, zdroj: null };
  const root = selectionRoot(o.soubory);
  const hasSub = o.soubory.some((f) =>
    f.cesta.split(/[/\\]/).length - 1 > root.length);
  const own = tg.zdroj === "metadata" ? tg.skupiny || {} : {};
  const ownIds = Object.keys(own);
  const avail = ["podslozky", "jedna", "auto", "zadne", "existujici"]
    .filter((m) => (m !== "podslozky" || hasSub) &&
      (m !== "existujici" || ownIds.length));
  const preset = hasSub ? "podslozky"
    : tg.zdroj === "metadata" ? "jedna" : "auto";
  // Uložená volba (návrat k importu) platí, dokud je dostupná; jinak
  // předvolba podle cíle.
  imp.groups ||= o.skupiny ? { ...o.skupiny, chosen: true }
    : { chosen: false };
  const g = imp.groups;
  if (!tg.loading && (!g.chosen || !avail.includes(g.rezim))) {
    g.rezim = preset;
  }
  g.nazev ??= root.at(-1) ||
    `Import ${new Date().toLocaleDateString("sv")}`;
  if (!(g.skupina in own)) g.skupina = ownIds[0];
  const set = (changes) => {
    Object.assign(g, changes, { chosen: true });
    imp.targetError = null;
    renderTarget();
  };
  const radio = (mode) => h("label", {},
    h("input", { type: "radio", name: "skupiny", checked: g.rezim === mode,
      onchange: () => set({ rezim: mode }) }), " ", IMPORT_SKUPINY[mode]);
  return h("fieldset", { class: "folder" }, h("legend", {}, "Skupiny"),
    tg.loading ? h("p", { class: "meta" }, "Načítám skupiny akce…") : [
      ...avail.map((m) => h("div", {}, radio(m),
        m === "jedna" && g.rezim === "jedna" ? [" ", h("input", {
          type: "text", value: g.nazev, size: 40,
          oninput: (e) => { g.nazev = e.target.value; g.chosen = true; },
        })] : null,
        m === "existujici" && g.rezim === "existujici" ? [" ", h("select", {
          onchange: (e) => set({ skupina: e.target.value }) },
        ownIds.map((id) => h("option", { value: id,
          selected: id === g.skupina }, own[id].nazev || id)))] : null)),
      g.rezim === "podslozky" ? h("p", { class: "meta" }, "Skupina = " +
        "podsložka první úrovně" + (root.length ? ` pod ${root.join("/")}`
          : "") + ". RAWy skupinu nedostanou.") : null,
    ]);
}

function importGroupsChoice() {
  const g = imp.groups;
  if (!g || imp.targetGroups?.loading && imp.target.mode === "stavajici") {
    return null;
  }
  const volba = { rezim: g.rezim };
  if (g.rezim === "jedna") volba.nazev = g.nazev.trim();
  if (g.rezim === "existujici") volba.skupina = g.skupina;
  return volba;
}

function renderTarget() {
  const o = imp.overview;
  const events = state.events || [];
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
      "dokončená. Nové soubory v ní budou bez metadat, dokud je " +
      "nedoplníte a akci znovu nedokončíte, a Immich je uvidí hned.")
      : null) : null;
  const created = t.mode === "nova" ? h("div", { class: "folder" },
    h("div", { class: "row" },
      h("input", { type: "date", value: t.datum,
        oninput: (e) => { t.datum = e.target.value; updatePreview(); } }),
      h("input", { type: "text", value: t.nazev, size: 50,
        placeholder: "název akce, např. kontrola Stezky",
        oninput: (e) => { t.nazev = e.target.value; updatePreview(); } })),
    h("p", { class: "meta" }, "Složka: ", preview,
      o.od ? "" : " (datum z EXIF nezjištěno, doplňte ho)")) : null;
  const err = imp.targetError;
  const planning = imp.busy === "plan";
  const groups = importGroupsBlock(t);
  const body = h("main", { class: "wizard" },
    h("div", { class: "row" }, radio("stavajici", "do stávající akce"),
      radio("nova", "do nové akce")),
    existing, created, groups,
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
      imp.targetError = { text: "Doplňte datum i název nové akce." };
      return renderTarget();
    } else body.nova = folder();
    body.skupiny = importGroupsChoice();
    if (!body.skupiny) return;
    if (body.skupiny.rezim === "jedna" && !body.skupiny.nazev) {
      imp.targetError = { text: IMPORT_SKUPINY_CHYBA.bez_nazvu_skupiny };
      return renderTarget();
    }
    imp.busy = "plan";
    imp.targetError = null;
    renderTarget();
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
      imp.plan = { ...last, volba: body.skupiny };
      imp.pripojit = {};
    } catch (e) {
      imp.busy = null;
      if (e.status !== 409) {
        imp.targetError = { text: `Plán nejde sestavit: ${e.message}` };
        return renderTarget();
      }
      const known = events.some((x) => x.nazev === e.data.akce);
      imp.targetError = IMPORT_SKUPINY_CHYBA[e.data.chyba]
        ? { text: IMPORT_SKUPINY_CHYBA[e.data.chyba] }
        : e.data.chyba === "existuje"
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
      disabled: planning || (t.mode === "stavajici" && !t.cil) ||
        !importGroupsChoice(),
      onclick: next }, planning ? "Počítám plán…" : "Ukázat plán"),
  ]));
}

// `group(gid)` = popis cílové skupiny (bez ní sloupec chybí).
function importOps(ops, group) {
  return h("table", { class: "ops" }, ops.map((o) => h("tr", {
    class: o.stav === "hotovo" || o.stav === "ok" ? ""
      : o.stav === "chyba" || o.stav === "poskozeny" ? "failed"
        : o.stav === "duplicita" ? "dup" : "blocked" },
  h("td", {}, h("code", {}, o.z)), h("td", {}, h("code", {}, `→ ${o.do}`)),
  group ? h("td", {}, o.skupina ? group(o.skupina) : "") : null,
  h("td", { class: "num" }, fmtSize(o.velikost)),
  h("td", {}, IMPORT_STAV[o.stav], o.stav === "hotovo" || o.stav === "ok"
    ? "" : `: ${o.chyba || o.duvod}`))));
}

function countBy(ops) {
  const c = {};
  for (const o of ops) c[o.stav] = (c[o.stav] || 0) + 1;
  return (st) => c[st] || 0;
}

// Nové skupiny plánu s volbou „nová / připojit ke skupině …“; změna
// plán nepřepočítává, `pripojit` jde až s provedením.
function importPlanGroups(p) {
  const nove = Object.entries(p.skupiny.nove);
  if (!nove.length) return null;
  const ex = p.skupiny.existujici;
  const count = (gid) => p.operace.filter((o) => o.skupina === gid).length;
  return h("table", { class: "ops" },
    h("tr", {}, h("th", {}, "Nová skupina"), h("th", {}, "Souborů"),
      Object.keys(ex).length ? h("th", {}, "Zařazení") : null),
    nove.map(([gid, g]) => h("tr", {},
      h("td", {}, g.nazev, g.pristroj ? h("span", { class: "meta" },
        ` (${g.pristroj})`) : null),
      h("td", { class: "num" }, String(count(gid))),
      Object.keys(ex).length ? h("td", {}, h("select", {
        onchange: (e) => {
          if (e.target.value) imp.pripojit[gid] = e.target.value;
          else delete imp.pripojit[gid];
          renderImportPlan();
        } },
      h("option", { value: "" }, "nová skupina"),
      [...g.shody, ...Object.keys(ex).filter((x) => !g.shody.includes(x))]
        .map((x) => h("option", { value: x,
          selected: imp.pripojit[gid] === x },
        `připojit ke skupině ${ex[x].nazev || x}` +
          (g.shody.includes(x) ? " (shoda)" : ""))))) : null)));
}

function renderImportPlan() {
  const p = imp.plan;
  const n = countBy(p.operace);
  const zapis = state.info.zapis;
  const holder = imp.lockHolder;
  const zdroj = imp.overview?.zdroj;
  const body = h("main", { class: "wizard" },
    zapis && zdroj
      ? h("p", { class: "notice" }, "Po potvrzení se soubory přesunou ze " +
        `složky ${UNSORTED}/${zdroj}, média do kořene akce, RAWy do ` +
        "RAW.ignored. Nic se nepřepíše; blokované, duplicitní, poškozené " +
        "a nepodporované soubory zůstanou ve zdroji. Prázdné složky zdroje " +
        "se smažou.")
      : zapis
      ? h("p", { class: "notice" }, "Po potvrzení se soubory zkopírují do " +
        "archivu, média do kořene akce, RAWy do RAW.ignored. Nic se " +
        "nepřepíše; blokované, duplicitní a poškozené soubory zůstanou " +
        "v pracovním adresáři.")
      : h("p", { class: "notice" }, "Vývojový režim: plán se jen ukazuje, " +
        "do archivu se nic nezapíše."),
    h("p", {}, p.nova ? "Vznikne nová akce " : "Cíl: ",
      h("code", {}, p.cil), "."),
    h("p", {}, `Přenese se ${n("ok")}, blokováno ${n("blokovano")}, ` +
      `duplicit ${n("duplicita")}` + (n("poskozeny")
        ? `, poškozených (nepřenesou se) ${n("poskozeny")}.` : ".")),
    holder ? h("p", { class: "notice readonly" },
      `${holderText(holder)} Import teď nejde provést; ` + (zdroj
        ? "soubory zůstávají ve zdroji."
        : "nahrané soubory zůstávají v pracovním adresáři.")) : null,
    imp.sourceHolder ? h("p", { class: "notice readonly" },
      `Složku ${UNSORTED}/${zdroj} právě přesouvá ` +
      `${imp.sourceHolder.jmeno}. Import teď nejde provést.`) : null,
    p.nepodporovane.length ? h("p", { class: "meta" },
      `Nepodporované (nepřenesou se): ${p.nepodporovane.join(", ")}`) : null,
    importPlanGroups(p),
    importOps(p.operace, (gid) => {
      const join = imp.pripojit[gid];
      if (join) return p.skupiny.existujici[join].nazev || join;
      const nova = p.skupiny.nove[gid];
      return nova ? `${nova.nazev} (nová)`
        : p.skupiny.existujici[gid]?.nazev || gid;
    }));
  const go = h("button", { class: "primary", onclick: () => {
    if (!go.dataset.confirm) {
      go.dataset.confirm = "1";
      go.textContent = zdroj ? "Opravdu přesunout do archivu?"
        : "Opravdu zkopírovat do archivu?";
      return;
    }
    executeImport(go);
  } }, `Importovat (${plural(n("ok"), "soubor", "soubory", "souborů")})`);
  app.replaceChildren(...importFrame(body, [
    h("span", { class: "row" },
      h("button", { onclick: () => goStep(2) }, "← Zpět"),
      h("button", { onclick: discardImport }, "Zahodit import")),
    zapis && n("ok") ? go : h("span"),
  ]));
}

async function executeImport(button) {
  if (imp.busy) return;
  imp.busy = "provest";
  setBusy(button, "Připravuji…");
  const p = imp.plan;
  const zdroj = imp.overview?.zdroj;
  imp.sourceHolder = null;
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
      skupiny: p.volba, pripojit: imp.pripojit,
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
  goStep(4);
}

function renderImportResult() {
  const r = imp.result;
  const n = countBy(r.operace);
  const zdroj = imp.overview?.zdroj;
  const left = Object.values(r.zdroj_zbyva || {}).reduce((a, b) => a + b, 0);
  const body = h("main", { class: "wizard" },
    h("p", { class: n("chyba") ? "notice error" : "notice" },
      `Přeneseno ${n("hotovo")}, blokováno ${n("blokovano")}, duplicit ` +
      `${n("duplicita")}, ` + (n("poskozeny")
        ? `poškozených ${n("poskozeny")}, ` : "") +
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
      `Skupiny se nepodařilo zapsat (${r.skupiny.chyba}); přenesené ` +
      "soubory jsou v akci bez skupiny, rozdělte je na ploše.") : null,
    r.index?.length ? h("p", { class: "notice error" },
      `Index archivu se nepodařilo aktualizovat: ${r.index.join("; ")}`)
      : null,
    r.skupiny?.zapsano && r.skupiny.navrh &&
      Object.keys(r.skupiny.prirazeni).length
      ? h("p", { class: "meta" }, "Skupiny se použijí jako návrh při " +
        "prvním otevření akce.") : null,
    importOps(r.operace, r.skupiny && ((gid) =>
      r.skupiny.skupiny[gid]?.nazev || gid)));
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
  const msg = h("p", { class: "status" });
  const say = (text, error = false) => {
    msg.textContent = text;
    msg.className = error ? "status error" : "status";
  };
  const adresa = h("input", { value: s.adresa || "",
    placeholder: "http://10.10.1.51:2283" });
  const klic = h("input", { type: "password", autocomplete: "off",
    placeholder: s.nastaveno ? `klíč nastaven (${s.klic}) – vyplňte jen ` +
      "pro změnu" : "API klíč (jen pro čtení)" });
  const refresh = async () => {
    state.info = await api("/api/info");
    await showSettings();
  };
  const saveSettings = async () => {
    try {
      await api("/api/immich", { method: "PUT",
        body: { adresa: adresa.value, klic: klic.value } });
      await refresh();
    } catch (err) {
      say({ klic_povinny: "Při změně adresy zadejte klíč znovu.",
        spatna_adresa: "Adresa musí začínat http:// nebo https://." }[
        err.data?.chyba] || `Uložení selhalo: ${err.message}`, true);
    }
  };
  const test = async () => {
    say("Zkouším připojení…");
    try {
      const r = await api("/api/immich/test", { method: "POST" });
      say(`Připojení funguje: Immich ${r.verze}, osob ${r.osob}.`);
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
      "v Immichi. Stačí klíč jen pro čtení (osoby, assety, obličeje)."),
    h("div", { class: "field" }, h("label", {}, "Adresa serveru"), adresa),
    h("div", { class: "field" }, h("label", {}, "API klíč"), klic),
    h("div", { class: "row" },
      h("button", { class: "primary", onclick: saveSettings }, "Uložit"),
      s.nastaveno ? h("button", { onclick: test }, "Otestovat") : null,
      s.nastaveno ? h("button", { onclick: remove }, "Smazat") : null),
    msg,
    s.nastaveno ? syncBlock(s.synchronizace, sync) : null,
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
