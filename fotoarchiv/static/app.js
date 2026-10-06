// Klient prototypu: seznam akcí, průvodce prvním otevřením a pracovní
// plocha. Stav (dokument `_metadata.json`) drží klient a ukládá ho celý.

import { missing, resolve, resolveGroup } from "./inherit.js";

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

// POST se streamem NDJSON (průběh dlouhých operací): `onEvent` pro každý
// řádek, vrátí poslední událost. Odmítnutí před startem je JSON s chybou.
async function apiStream(url, body, onEvent) {
  const r = await fetch(url, { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) });
  if (!r.ok) {
    const err = new Error(`HTTP ${r.status}`);
    err.status = r.status;
    err.data = await r.json().catch(() => null);
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
};

// --- stav ----------------------------------------------------------------

const state = {
  info: null,
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

function userName() {
  return localStorage.getItem("jmeno");
}

const NAME_RE = /^[^,]+, [^,]+$/;

// Do zavedení přihlašování jméno zadané v prohlížeči (jen se zobrazuje).
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
    // Zámek je pryč (restart serveru nebo opuštění); volný se získá znovu.
    state.locked = null;
    clearInterval(heartbeatTimer);
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

function lockNotice() {
  const r = state.readonly;
  // Prázdný řetězec, ne null: jde přímo do replaceChildren, který by
  // null vypsal jako text.
  if (!r) return "";
  return h("p", { class: "notice readonly" },
    `${holderText(r)} Jen ke čtení – změny se neukládají.`,
    " ", h("button", { class: "link", onclick: () => route() },
      "Zkusit znovu"));
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
  if (im) {
    await openImport(im[1] ? decodeURIComponent(im[1]) : null,
      new URLSearchParams(im[2] || ""));
  } else if (name) await openEvent(name);
  else await showList();
}

function header(...right) {
  const info = state.info || {};
  return h("header", {},
    h("a", { href: "#/", class: "brand" }, "Fotoarchiv – metadata"),
    info.zapis
      ? h("span", { class: "paths" }, `archiv: ${info.archiv || "…"} · `,
        h("strong", {}, "metadata a úklid se zapisují do archivu"))
      : h("span", { class: "paths" },
        `archiv (jen čtení): ${info.archiv || "…"} · `,
        h("strong", {}, `ukládá se do: ${info.work || "…"}`)),
    ...right,
    userName() ? h("button", { class: "link user", title: "Změnit jméno",
      onclick: async () => { await askName(); route(); } }, userName())
      : null);
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
      h("td", {}, h("span", { class: "badge" }, STAV[e.stav]),
        e.zmeneno_po_exportu
          ? h("span", { class: "warn" }, " změněno po exportu") : null)));
  app.replaceChildren(header(), h("main", { class: "list" },
    h("div", { class: "row" }, h("h1", {}, "Akce"),
      h("button", { onclick: () => { location.hash = "#/import"; } },
        "Importovat fotky a videa…")),
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
    if (!(await confirmDialog("Zahodit import?", [
      `Nahrané soubory (${it.souboru}) se smažou z pracovního adresáře ` +
      "serveru. Archiv zůstane beze změny."], "Zahodit"))) return;
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
          h("td", {}, fmtTime(it.zalozeno)),
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

// --- otevření akce --------------------------------------------------------

async function openEvent(name) {
  Object.assign(state, {
    name, detail: null, doc: null, version: null, mode: null,
    sel: new Set(), group: null, anchor: null, dirty: false,
    conflict: false, view: "grid", current: null, readonly: null,
    placeOpen: null, exporting: false, exportVersion: null, exportNote: "",
  });
  // Stav akce se mohl změnit u jiného uživatele.
  const events = state.events = await api("/api/akce");
  const entry = events.find((e) => e.nazev === name);
  if (!entry) {
    app.replaceChildren(header(), h("main", {}, "Akce nenalezena."));
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
      body: { metadata: state.doc, version: state.version, relace: session() },
    });
    if (name === state.name) {
      state.version = r.version;
      if (r.version !== state.exportVersion) {
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

function collectNames(doc) {
  const out = new Set();
  const records = [doc.akce || {}, ...Object.values(doc.skupiny || {}),
    ...Object.values(doc.soubory || {})];
  for (const r of records) {
    for (const k of ["osoby", "autori", "ucastnici"]) {
      for (const n of r[k] || []) out.add(n);
    }
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

function sections() {
  const byGroup = new Map(groupIds().map((g) => [g, []]));
  const none = [];
  for (const [f, r] of Object.entries(state.doc.soubory)) {
    if (r.skupina && byGroup.has(r.skupina)) byGroup.get(r.skupina).push(f);
    else none.push(f);
  }
  const result = [...byGroup].map(([gid, files]) =>
    ({ gid, title: groupName(gid), files: sortedFiles(files) }));
  if (none.length) {
    result.push({ gid: null, title: "Bez skupiny", files: sortedFiles(none) });
  }
  return result;
}

function tile(f) {
  const info = state.scan[f] || {};
  const present = state.present.has(f);
  const datum = resolve(state.doc, f).datum?.hodnota;
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
      `${state.sel.has(f) ? " selected" : ""}`,
    dataset: { file: f },
    title: f,
  }, thumb,
  h("div", { class: "cap" }, h("span", { class: "fn" }, f),
    h("span", { class: "dt" }, datum ? datum.replace("T", " ") : "bez data")));
}

function renderGrid() {
  const grid = document.getElementById("grid");
  if (!grid) return;
  const secs = sections();
  state.order = secs.flatMap((s) => s.files);
  const nodes = secs.map((s) => h("section", {},
    h("h3", {
      class: `ghead${s.gid && state.group === s.gid ? " selected" : ""}`,
      dataset: { group: s.gid || "" },
    }, s.title, h("span", { class: "count" }, ` ${s.files.length}`)),
    h("div", { class: "tiles" }, s.files.map(tile))));
  const other = state.detail?.nezpracovane || [];
  if (other.length) {
    nodes.push(h("details", { class: "other" },
      h("summary", {}, `Nezpracované soubory v kořeni: ${other.length}`),
      h("p", {}, other.join(", "))));
  }
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

function clickGroupHead(gid) {
  if (gid) select(new Set(), gid);
  // „Bez skupiny“ nemá skupinu; vybere její soubory.
  else select(new Set(sections().find((s) => !s.gid)?.files || []), null);
}

function setupGrid(grid) {
  grid.addEventListener("click", (e) => {
    if (grid.dataset.dragged) {
      delete grid.dataset.dragged;
      return;
    }
    const head = e.target.closest(".ghead");
    if (head) return clickGroupHead(head.dataset.group);
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
  for (const b of document.querySelectorAll(".views button")) {
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

function filmTile(f) {
  const info = state.scan[f] || {};
  const present = state.present.has(f);
  return h("div", {
    class: `ftile${present ? "" : " missing"}` +
      `${state.sel.has(f) ? " selected" : ""}` +
      `${f === state.current ? " current" : ""}`,
    dataset: { file: f }, title: f,
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
  film.replaceChildren(...(secs || sections()).map((s) =>
    h("div", { class: "fsec" },
      h("div", {
        class: `fhead${s.gid && state.group === s.gid ? " selected" : ""}`,
        dataset: { group: s.gid || "" }, title: s.title,
      }, s.title),
      s.files.map(filmTile))));
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
    if (head) return clickGroupHead(head.dataset.group);
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
  osoby: { label: "Osoby na fotce", type: "names" },
  ucastnici: { label: "Účastníci akce (nedědí se na fotky)", type: "names" },
  autori: { label: "Autoři (fotil někdo z nich)", type: "names" },
  pristroj: { label: "Přístroj", type: "text" },
  gps: { label: "GPS (šířka, délka)", type: "gps" },
};

const FIELDS = {
  akce: ["nazev", "datum_od", "datum_do", "popis", "mista", "ucastnici",
    "autori"],
  skupina: ["autori", "pristroj", "popis", "misto", "osoby", "datum_od",
    "datum_do"],
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
  return ids.map((f) => ({ obj: state.doc.soubory[f], level,
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

function fieldRow(targets, key, onChange) {
  const def = F[key];
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
  const input = editor(def.type, inherited ? undefined : shown, placeholder,
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
  if (type === "datetime") {
    return h("input", { value: value || "", placeholder:
      placeholder || "RRRR-MM-DD nebo RRRR-MM-DDTHH:MM:SS",
      oninput: (e) => {
        const v = e.target.value.trim();
        const ok = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$/.test(v);
        e.target.classList.toggle("invalid", !!v && !ok);
        if (!v || ok) update(v);
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
        ? "Geokódování je na serveru vypnuté (chybí --kontakt)."
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

// --- export a dokončení -----------------------------------------------------

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

function renderExportStatus(errors = []) {
  const el = document.getElementById("export-status");
  if (!el) return;
  const done = state.doc?.dokonceno;
  el.textContent = state.exporting ? "Exportuji…"
    : [done ? `Dokončeno ${done}` : "", state.exportNote]
      .filter(Boolean).join(" · ");
  el.className = errors.length ? "error"
    : /neaktuál|neexport|selhal/.test(state.exportNote) ? "pending" : "";
  el.title = errors.map((e) => `${e.soubor}: ${e.chyba}`).join("\n");
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

async function runExport(finish) {
  if (state.exporting || state.readonly) return;
  if (!(await flushSave())) return;
  if (finish) {
    const lines = missingItems().map((i) => i.text);
    if (lines.length && !(await confirmDialog(
      "Akci něco chybí", lines, "Přesto dokončit"))) return;
  }
  const name = state.name;
  state.exporting = true;
  renderExportStatus();
  let errors = [];
  try {
    const r = await api(eventUrl(name, finish ? "/dokoncit" : "/export"), {
      method: "POST", body: { relace: session(), version: state.version },
    });
    if (name !== state.name) return;
    errors = r.chyby;
    if (finish) {
      state.version = r.version;
      state.doc.dokonceno = r.dokonceno;
    }
    state.exportVersion = r.export_version;
    state.exportNote = (finish && !r.dokonceno
      ? "Export selhal, akce není dokončená: " : "Exportováno: ") +
      exportResult(r);
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
    state.exportNote = `Export selhal: ${err.message}`;
  } finally {
    state.exporting = false;
  }
  renderExportStatus(errors);
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
      h("button", { disabled: !!state.readonly,
        title: "Nahrát do akce další fotky a videa", onclick: () => {
          location.hash = `#/import?cil=${encodeURIComponent(state.name)}`;
        } }, "Importovat…"),
      h("span", { class: "export" },
        h("span", { id: "export-status" }),
        h("button", { disabled: !!state.readonly, title: exportTarget(),
          onclick: () => runExport(false) }, "Exportovat"),
        h("button", { class: "primary", disabled: !!state.readonly,
          onclick: () => runExport(true) }, "Dokončit akci"))),
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
  return items;
}

function renderBar() {
  const bar = document.getElementById("bar");
  if (!bar || !state.doc) return;
  const items = missingItems().map(({ text, onclick }) =>
    h("button", { class: "miss", onclick }, text));
  const chyb = state.detail?.chybejici || [];
  if (chyb.length) {
    items.push(h("span", { class: "info" },
      `${plural(chyb.length, "soubor chybí", "soubory chybí",
        "souborů chybí")} v kořeni`));
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
    changed({ grid: key === "datum" });
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

const wizard = { step: 0, plan: null, volby: {}, rawRoot: true };
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

async function executeCleanup() {
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    "Provádím úklid…"), []));
  let result;
  try {
    result = await api(eventUrl(state.name, "/uklid/provest"), {
      method: "POST", body: { volby: wizard.volby,
        raw_v_koreni: wizard.rawRoot, relace: session() },
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
  const rows = result.operace.map((o) => h("tr", {
    class: o.stav === "hotovo" ? "" : o.stav === "chyba" ? "failed" : "blocked",
  },
  h("td", {}, OPS[o.typ]), h("td", {}, h("code", {}, o.z)),
  h("td", {}, o.do ? h("code", {}, `→ ${o.do}`) : ""),
  h("td", {}, OP_STAV[o.stav], o.stav === "hotovo" ? ""
    : `: ${o.chyba || o.duvod}`)));
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

async function renderCleanup() {
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    "Počítám plán úklidu…"), []));
  const plan = await api(eventUrl(state.name, "/uklid"), {
    method: "POST", body: { volby: wizard.volby, raw_v_koreni: wizard.rawRoot },
  });
  wizard.plan = plan;
  const replan = () => renderCleanup();
  const folders = plan.podslozky.map((f) => {
    const name = `volba-${f.nazev}`;
    const radio = (value, label) => h("label", {},
      h("input", { type: "radio", name, value, checked: f.volba === value,
        onchange: () => { wizard.volby[f.nazev] = value; replan(); } }),
      " ", label);
    return h("div", { class: `folder${f.volba ? "" : " undecided"}` },
      h("p", {}, `Složka `, h("code", {}, f.nazev), ` obsahuje `,
        plural(f.souboru, "soubor", "soubory", "souborů"),
        f.rawu ? ` (RAW: ${f.rawu})` : "",
        f.podslozek ? `, podsložek: ${f.podslozek}` : "", "."),
      h("div", { class: "row" },
        radio("presunout", "přesunout mezi soubory akce"),
        radio("ponechat", h("span", {}, "ponechat stranou → ",
          h("code", {}, f.cil)))),
      f.volba ? null : h("p", { class: "warn" }, "Zatím bez rozhodnutí."));
  });
  const rawRoot = plan.raw_v_koreni ? h("label", { class: "folder" },
    h("input", { type: "checkbox", checked: wizard.rawRoot,
      onchange: (e) => { wizard.rawRoot = e.target.checked; replan(); } }),
    ` Přesunout ${plural(plan.raw_v_koreni, "RAW", "RAWy", "RAWů")} ` +
    "z kořene do ", h("code", {}, "RAW.ignored")) : null;
  const ops = plan.operace.length
    ? h("table", { class: "ops" }, plan.operace.map((o) => h("tr", {
      class: o.blocked ? "blocked" : "" },
    h("td", {}, OPS[o.typ]), h("td", {}, h("code", {}, o.z)),
    h("td", {}, o.do ? h("code", {}, `→ ${o.do}`) : ""),
    h("td", {}, o.blocked ? `blokováno: ${o.duvod}` : ""))))
    : h("p", {}, "Žádné operace.");
  const empty = !plan.podslozky.length && !plan.raw_v_koreni;
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
    empty ? h("p", {}, "Kořen akce nemá podsložky ani RAWy, " +
      "není co uklízet.") : null,
    folders, rawRoot,
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
      fieldRow(targetsFor("skupina", [gid]), "autori", () => {}));
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
    rows, warn), nav));
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
  hotovo: "hotovo", chyba: "chyba" };
const IMPORT_CHYBA = {
  probiha: "import se právě provádí (jiná záložka)",
  neuplny: "přenos se přerušil",
  prilis_velky: "soubor je příliš velký",
  malo_mista: "na serveru není dost místa",
  neplatne_jmeno: "neplatné jméno souboru",
};

const imp = {
  id: null, step: 0, cil: null, picked: [], failed: [], uploading: false,
  overview: null, target: null, targetError: null, plan: null,
  result: null, lockHolder: null, error: null, busy: null,
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
    if (imp.overview.soubory.length) imp.step = 1;
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
    `Nahrané soubory (${n}) se smažou z pracovního adresáře serveru. ` +
    "Archiv zůstane beze změny."], "Zahodit"))) return;
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

function renderOverview() {
  const o = imp.overview;
  const c = o.pocty;
  const media = (c.foto || 0) + (c.video || 0) + (c.raw || 0);
  const parts = ["foto", "video", "raw"].filter((t) => c[t])
    .map((t) => plural(c[t], ...TYP[t]));
  const dates = !o.od ? "z EXIF nezjištěno"
    : o.od === o.do ? fmtDate(o.od) : `${fmtDate(o.od)} – ${fmtDate(o.do)}`;
  const rows = o.soubory.map((f) => h("tr", {
    class: f.typ === "nepodporovany" ? "failed" : "" },
  h("td", {}, h("code", {}, f.cesta)),
  h("td", {}, TYP[f.typ][0]),
  h("td", {}, f.datum ? fmtDate(f.datum) + f.datum.slice(10)
    .replace("T", " ") : ""),
  h("td", {}, f.pristroj || ""),
  h("td", { class: "num" }, fmtSize(f.velikost))));
  const body = h("main", { class: "wizard" },
    imp.error ? h("p", { class: "notice error" }, imp.error) : null,
    h("p", {}, `Nahráno ${plural(o.soubory.length, "soubor", "soubory",
      "souborů")}: ${parts.join(", ") || "žádná média"}.`),
    h("p", {}, "Datum: ", h("strong", {}, dates)),
    h("p", {}, "Přístroje: ", o.pristroje.join(", ") || "nezjištěny"),
    o.nepodporovane.length ? h("div", { class: "notice error" },
      "Nepodporované soubory se do archivu nepřenesou: ",
      o.nepodporovane.flatMap((n, i) => [i ? ", " : "", h("code", {}, n)]))
      : null,
    h("details", {}, h("summary", {}, "Seznam souborů"),
      h("table", { class: "ops" }, rows)));
  app.replaceChildren(...importFrame(body, [
    h("span", { class: "row" },
      h("button", { onclick: () => goStep(0) }, "← Přidat soubory"),
      h("button", { onclick: discardImport }, "Zahodit import")),
    h("button", { class: "primary", disabled: !media,
      onclick: () => goStep(2) }, "Pokračovat"),
  ]));
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
          nazev: "" };
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
      events.map((e) => h("option", { value: e.nazev,
        selected: e.nazev === t.cil },
      e.nazev + (e.stav === "hotovo" ? " (hotovo)" : "")))),
    event?.stav === "hotovo" ? h("p", { class: "warn" }, "Akce je " +
      "dokončená. Nové soubory v ní budou bez metadat, dokud je " +
      "nedoplníte a akci znovu nedokončíte.") : null) : null;
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
      imp.targetError = { text: "Doplňte datum i název nové akce." };
      return renderTarget();
    } else body.nova = folder();
    imp.busy = "plan";
    imp.targetError = null;
    renderTarget();
    let total = null;
    try {
      const last = await apiStream(importUrl("/plan"), body, (ev) => {
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

function importOps(ops) {
  return h("table", { class: "ops" }, ops.map((o) => h("tr", {
    class: o.stav === "hotovo" || o.stav === "ok" ? ""
      : o.stav === "chyba" ? "failed" : o.stav === "duplicita" ? "dup"
        : "blocked" },
  h("td", {}, h("code", {}, o.z)), h("td", {}, h("code", {}, `→ ${o.do}`)),
  h("td", { class: "num" }, fmtSize(o.velikost)),
  h("td", {}, IMPORT_STAV[o.stav], o.stav === "hotovo" || o.stav === "ok"
    ? "" : `: ${o.chyba || o.duvod}`))));
}

function countBy(ops) {
  const c = {};
  for (const o of ops) c[o.stav] = (c[o.stav] || 0) + 1;
  return (st) => c[st] || 0;
}

function renderImportPlan() {
  const p = imp.plan;
  const n = countBy(p.operace);
  const zapis = state.info.zapis;
  const holder = imp.lockHolder;
  const body = h("main", { class: "wizard" },
    zapis
      ? h("p", { class: "notice" }, "Po potvrzení se soubory zkopírují do " +
        "archivu, média do kořene akce, RAWy do RAW.ignored. Nic se " +
        "nepřepíše; blokované a duplicitní soubory zůstanou v pracovním " +
        "adresáři.")
      : h("p", { class: "notice" }, "Vývojový režim: plán se jen ukazuje, " +
        "do archivu se nic nezapíše."),
    h("p", {}, p.nova ? "Vznikne nová akce " : "Cíl: ",
      h("code", {}, p.cil), "."),
    h("p", {}, `Přenese se ${n("ok")}, blokováno ${n("blokovano")}, ` +
      `duplicit ${n("duplicita")}.`),
    holder ? h("p", { class: "notice readonly" },
      `${holderText(holder)} Import teď nejde provést; nahrané ` +
      "soubory zůstávají v pracovním adresáři.") : null,
    p.nepodporovane.length ? h("p", { class: "meta" },
      `Nepodporované (nepřenesou se): ${p.nepodporovane.join(", ")}`) : null,
    importOps(p.operace));
  const go = h("button", { class: "primary", onclick: () => {
    if (!go.dataset.confirm) {
      go.dataset.confirm = "1";
      go.textContent = "Opravdu zkopírovat do archivu?";
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
  if (!p.nova && !(await acquireLock(p.cil))) {
    imp.busy = null;
    imp.lockHolder = state.readonly;
    state.readonly = null;
    return renderImport();
  }
  app.replaceChildren(...importFrame(h("main", { class: "wizard" },
    h("p", {}, "Kopíruji do archivu. Zavření stránky kopírování zastaví: " +
      "přenesené soubory zůstanou v archivu, ostatní v pracovním " +
      "adresáři."), progressBox("Připravuji…")), []));
  let start = null;
  let total = null;
  let copied = 0;
  let files = 0;
  try {
    const last = await apiStream(importUrl("/provest"), {
      jmeno: userName(), relace: session(),
      [p.nova ? "nova" : "cil"]: p.cil,
    }, (ev) => {
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
          `Zkopírováno ${files} z ${start.souboru} · ` +
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
    if (err.status === 409 && err.data?.chyba === "probiha") {
      imp.targetError = { text: "Import se právě provádí v jiné záložce." };
      return goStep(2);
    }
    if (err.status) throw err;
    // Spojení se přerušilo uprostřed: přenesené jsou v archivu.
    imp.targetError = { text: `Kopírování se přerušilo (${err.message}). ` +
      "Přenesené soubory jsou v archivu, ostatní zůstaly v pracovním " +
      "adresáři; sestavte plán znovu." };
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
  const body = h("main", { class: "wizard" },
    h("p", { class: n("chyba") ? "notice error" : "notice" },
      `Přeneseno ${n("hotovo")}, blokováno ${n("blokovano")}, duplicit ` +
      `${n("duplicita")}, chyba ${n("chyba")}.` + (r.zahozeno ? ""
        : " Nepřenesené soubory zůstaly v pracovním adresáři, dokud " +
          "import nezahodíte.")),
    r.nepodporovane.length ? h("p", { class: "meta" },
      `Nepodporované (nepřeneseno): ${r.nepodporovane.join(", ")}`) : null,
    r.smazano?.length ? h("p", { class: "meta" }, "Smazány zbytky " +
      `přerušeného importu (starší než hodina): ${r.smazano.join(", ")}`)
      : null,
    importOps(r.operace));
  app.replaceChildren(...importFrame(body, [
    r.zahozeno ? h("span") : h("button", { onclick: discardImport },
      "Zahodit nepřenesené"),
    h("button", { class: "primary", onclick: () => {
      location.hash = `#/akce/${encodeURIComponent(r.cil)}`;
    } }, "Otevřít akci"),
  ]));
}

// --- start ------------------------------------------------------------------

state.info = await api("/api/info");
route();
