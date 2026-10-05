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
  sessionNames: new Set(),
  dirty: false,
  saving: false,
  conflict: false,
};

// --- směrování -----------------------------------------------------------

window.addEventListener("hashchange", route);
window.addEventListener("beforeunload", (e) => {
  if (state.dirty || state.saving) e.preventDefault();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && state.mode === "workspace" &&
      !document.querySelector("dialog[open]")) {
    select(new Set(), null);
  }
});

async function route() {
  if (state.dirty && state.mode === "workspace") await save();
  const m = location.hash.match(/^#\/akce\/(.+)$/);
  if (m) await openEvent(decodeURIComponent(m[1]));
  else await showList();
}

function header(...right) {
  const info = state.info || {};
  return h("header", {},
    h("a", { href: "#/", class: "brand" }, "Fotoarchiv – metadata"),
    h("span", { class: "paths" },
      `archiv (jen čtení): ${info.archiv || "…"} · `,
      h("strong", {}, `ukládá se do: ${info.work || "…"}`)),
    ...right);
}

// --- seznam akcí ----------------------------------------------------------

async function showList() {
  state.mode = null;
  state.name = null;
  app.replaceChildren(header(), h("main", { class: "list" }, "Načítám…"));
  state.events = await api("/api/akce");
  const rows = state.events.map((e) =>
    h("tr", { class: `stav-${e.stav}` },
      h("td", {}, e.datum),
      h("td", {}, h("a", { href: `#/akce/${encodeURIComponent(e.nazev)}` },
        e.nazev.slice(11))),
      h("td", { class: "num" }, e.souboru),
      h("td", {}, h("span", { class: "badge" }, STAV[e.stav]))));
  app.replaceChildren(header(), h("main", { class: "list" },
    h("h1", {}, "Akce"),
    h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Datum"), h("th", {}, "Akce"),
        h("th", {}, "Souborů"), h("th", {}, "Stav"))),
      h("tbody", {}, rows))));
}

// --- otevření akce --------------------------------------------------------

async function openEvent(name) {
  Object.assign(state, {
    name, detail: null, doc: null, version: null, mode: null,
    sel: new Set(), group: null, anchor: null, dirty: false,
    conflict: false,
  });
  const events = state.events || await api("/api/akce");
  const entry = events.find((e) => e.nazev === name);
  if (!entry) {
    app.replaceChildren(header(), h("main", {}, "Akce nenalezena."));
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
  else if (state.conflict) el.textContent = "Neuloženo – konflikt";
  else if (state.saving) el.textContent = "Ukládám…";
  else if (state.dirty) el.textContent = "Neuloženo";
  else el.textContent = "Uloženo";
  el.className = state.conflict ? "status error" :
    state.dirty || state.saving ? "status pending" : "status";
}

async function save() {
  if (state.conflict || !state.doc) return;
  if (state.saving) {
    state.dirty = true;
    return;
  }
  state.saving = true;
  state.dirty = false;
  setStatus();
  const name = state.name;
  try {
    const r = await api(eventUrl(name, "/metadata"), {
      method: "PUT", body: { metadata: state.doc, version: state.version },
    });
    if (name === state.name) state.version = r.version;
    for (const n of collectNames(state.doc)) state.sessionNames.add(n);
  } catch (err) {
    state.dirty = true;
    if (err.status === 409) {
      state.conflict = true;
      conflictDialog();
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
    for (const k of ["osoby", "autori"]) {
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
        onclick: () => { moveFiles(files, target.value); afterChange(); },
      }, "Přesunout")),
    h("div", { class: "row" }, nameInput,
      h("button", {
        onclick: () => {
          const name = nameInput.value.trim();
          if (!name) return nameInput.focus();
          newGroup(name, files);
          afterChange();
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
}

function select(files, group, opts = {}) {
  state.sel = files;
  state.group = group;
  for (const el of document.querySelectorAll("#grid .tile")) {
    el.classList.toggle("selected", files.has(el.dataset.file));
  }
  for (const el of document.querySelectorAll("#grid .ghead")) {
    el.classList.toggle("selected", !!group && el.dataset.group === group);
  }
  if (!opts.keepPanel) renderPanel();
}

function setupGrid(grid) {
  grid.addEventListener("click", (e) => {
    if (grid.dataset.dragged) {
      delete grid.dataset.dragged;
      return;
    }
    const head = e.target.closest(".ghead");
    if (head) {
      if (head.dataset.group) {
        select(new Set(), head.dataset.group);
      } else {
        // „Bez skupiny“ nemá skupinu; vybere její soubory.
        const files = [...head.nextElementSibling.children]
          .map((t) => t.dataset.file);
        select(new Set(files), null);
      }
      return;
    }
    const t = e.target.closest(".tile");
    if (!t) {
      if (!e.target.closest("details")) select(new Set(), null);
      return;
    }
    const f = t.dataset.file;
    const add = e.ctrlKey || e.metaKey;
    if (e.shiftKey && state.anchor && state.order.includes(state.anchor)) {
      const a = state.order.indexOf(state.anchor);
      const b = state.order.indexOf(f);
      const range = state.order.slice(Math.min(a, b), Math.max(a, b) + 1);
      select(new Set([...(add ? state.sel : []), ...range]), null);
      return;
    }
    const next = new Set(add ? state.sel : []);
    if (add && next.has(f)) next.delete(f);
    else next.add(f);
    state.anchor = f;
    select(next, null);
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

// --- formulář ----------------------------------------------------------------

const F = {
  nazev: { label: "Název", type: "text" },
  popis: { label: "Popis", type: "textarea" },
  datum_od: { label: "Datum od", type: "date" },
  datum_do: { label: "Datum do", type: "date" },
  datum: { label: "Datum pořízení", type: "datetime" },
  misto: { label: "Místo", type: "list" },
  osoby: { label: "Osoby", type: "names" },
  autori: { label: "Autoři (fotil někdo z nich)", type: "names" },
  projekt: { label: "Projekt", type: "text" },
  pristroj: { label: "Přístroj", type: "text" },
  gps: { label: "GPS (šířka, délka)", type: "gps" },
};

const FIELDS = {
  akce: ["nazev", "datum_od", "datum_do", "popis", "misto", "osoby",
    "projekt", "autori"],
  skupina: ["autori", "pristroj", "popis", "misto", "osoby", "projekt",
    "datum_od", "datum_do"],
  soubor: ["datum", "autori", "popis", "osoby", "misto", "projekt",
    "pristroj", "gps"],
};

const LEVEL = { akce: "akce", skupina: "skupiny", soubor: "souboru" };

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
      `${inherited ? " inherited" : ""}${st.anyOwn ? " own" : ""}`,
  });
  const update = (value) => {
    setField(targets, key, value);
    row.classList.remove("mixed", "inherited");
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
  if (type === "list" || type === "names") return v.join("; ");
  if (type === "gps") return v.join(", ");
  return String(v);
}

function editor(type, value, placeholder, update, inheritedValue) {
  if (type === "names") {
    return namesField(value || [], update, inheritedValue, placeholder);
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
  if (type === "list") {
    return h("input", { value: format("list", value), placeholder,
      oninput: (e) => update(e.target.value.split(";").map((s) => s.trim())
        .filter(Boolean)) });
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
  return h("input", { value: value || "", placeholder,
    oninput: (e) => update(e.target.value) });
}

// --- pole jmen ---------------------------------------------------------------

function namesField(initial, update, inheritedValue, placeholder) {
  let names = [...initial];
  let inherited = inheritedValue ? [...inheritedValue] : null;
  const chips = h("div", { class: "chips" });
  const input = h("input", { placeholder: placeholder ||
    "Příjmení, Jméno – Enter přidá" });
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
    const all = [...new Set([...r.navrhy, ...local])]
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
  }, 100));
  renderChips();
  return h("div", { class: "names" }, chips, input, list, hint);
}

function normalize(name) {
  return name.normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().match(/[\p{L}\p{N}_]+/gu)?.sort().join(" ") || "";
}

// --- pracovní plocha ----------------------------------------------------------

function renderWorkspace() {
  const d = state.detail;
  const back = h("a", { href: "#/" }, "← Akce");
  app.replaceChildren(
    header(h("span", { id: "save-status", class: "status" })),
    h("div", { class: "eventbar" }, back,
      h("h1", {}, state.name),
      h("span", { class: "paths" }, d.pracovni_soubor)),
    h("div", { id: "bar", class: "bar" }),
    h("div", { class: "workspace" },
      h("div", { id: "grid", class: "grid" }),
      h("aside", { id: "panel", class: "panel" })));
  setupGrid(document.getElementById("grid"));
  renderGrid();
  renderBar();
  renderPanel();
  setStatus();
  if (state.dirty) scheduleSave();
}

function renderBar() {
  const bar = document.getElementById("bar");
  if (!bar || !state.doc) return;
  const m = missing(state.doc, state.present);
  const items = [];
  const item = (text, onclick) =>
    items.push(h("button", { class: "miss", onclick }, text));
  if (m.akce.length) {
    const names = { nazev: "název", datum_od: "datum od", datum_do: "datum do" };
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
        select(new Set(list), null);
        document.querySelector(
          `#grid .tile[data-file="${CSS.escape(list[0])}"]`)
          ?.scrollIntoView({ block: "center" });
      });
  };
  files(m.souboryBezData, "bez data");
  files(m.souboryBezSkupiny, "bez skupiny");
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
  const onChange = (key) => {
    changed({ grid: key === "datum" });
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
  panel.replaceChildren(
    h("h2", {}, title),
    ...extra.filter(Boolean),
    h("div", { class: "form" },
      FIELDS[level].map((k) => fieldRow(targets, k, onChange))));
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
  const OPS = { move: "přesun", rename: "přejmenování", delete: "smazání" };
  const ops = plan.operace.length
    ? h("table", { class: "ops" }, plan.operace.map((o) => h("tr", {
      class: o.blocked ? "blocked" : "" },
    h("td", {}, OPS[o.typ]), h("td", {}, h("code", {}, o.z)),
    h("td", {}, o.do ? h("code", {}, `→ ${o.do}`) : ""),
    h("td", {}, o.blocked ? `blokováno: ${o.duvod}` : ""))))
    : h("p", {}, "Žádné operace.");
  const empty = !plan.podslozky.length && !plan.raw_v_koreni;
  app.replaceChildren(...wizardFrame(h("main", { class: "wizard" },
    h("p", { class: "notice" }, "Nasucho: prototyp plán jen ukazuje, " +
      "v archivu nic nepřesune ani nepřejmenuje. Další krok pracuje se " +
      "soubory, které jsou v kořeni teď."),
    empty ? h("p", {}, "Kořen akce nemá podsložky ani RAWy, " +
      "není co uklízet.") : null,
    folders, rawRoot,
    plan.operace.length || !empty ? h("h3", {}, "Plán") : null,
    empty ? null : ops), navButtons({ next: "Potvrdit plán a načíst soubory" })));
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
    return h("fieldset", { class: "tools" },
      h("legend", {}, `${groupName(gid)} (${plural(count, "soubor",
        "soubory", "souborů")})`),
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

// --- start ------------------------------------------------------------------

state.info = await api("/api/info");
route();
