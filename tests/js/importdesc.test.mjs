// Popis importu: sestavení, sladění s novým plánem a kontrola autorů
// (scénáře ze specifikace photo-import, „Skupiny a autoři v importu“
// a „Volba skupin“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  effectiveDoc, freshDescription, groupsWithoutAuthors, reconcile,
} from "../../fotoarchiv/static/importdesc.js";

const media = (...names) => names.map((nazev) => ({ nazev }));

const defaults = {
  cil: "2026-04-28 kontrola", nova: false,
  soubory: media("a.jpg", "b.jpg", "c.jpg"),
  skupiny: { jana: { nazev: "Jana" }, pavla: { nazev: "Pavla" } },
  prirazeni: { "a.jpg": "jana", "b.jpg": "pavla" },
  existujici: { g9: { nazev: "G9", autori: ["Příkladný, Daniel"] } },
};

test("nový popis z výchozího rozdělení", () => {
  const p = freshDescription(defaults, null);
  assert.equal(p.cil, "2026-04-28 kontrola");
  assert.deepEqual(Object.keys(p.skupiny), ["g9", "jana", "pavla"]);
  assert.deepEqual(p.soubory, { "a.jpg": { skupina: "jana" },
    "b.jpg": { skupina: "pavla" }, "c.jpg": {} });
  assert.deepEqual(p.akce, {});
  assert.equal(p.upraveno, false);
});

test("autory akce ze staršího serveru popis nepřevezme", () => {
  const p = freshDescription(
    { ...defaults, akce_autori: ["Modelová, Zuzana"] }, null);
  assert.deepEqual(p.akce, {});
});

test("údaje nové akce zůstanou, stávající cíl je odloží", () => {
  const akce = { nazev: "kontrola Stezky", datum_od: "2026-04-28" };
  const nova = freshDescription({ ...defaults, nova: true, cil: "x" },
    { typ: "nova", akce });
  assert.equal(nova.cil, "nova");
  assert.equal(nova.typ, "nova");
  assert.deepEqual(nova.akce, akce);
  const stavajici = freshDescription(defaults, nova);
  assert.deepEqual(stavajici.akce, {});
  assert.deepEqual(stavajici.nova_akce, akce);
  assert.equal(stavajici.typ, "stavajici");
  const zpet = freshDescription({ ...defaults, nova: true }, stavajici);
  assert.deepEqual(zpet.akce, akce);
});

test("sladění s novým plánem zachová ruční úpravy", () => {
  const p = freshDescription(defaults, null);
  p.skupiny.nova = { nazev: "Nová", autori: ["Pokusná, Bára"] };
  p.soubory["a.jpg"].skupina = "nova";
  p.pripojit = { pavla: "g9", jana: "zmizela" };
  const plan = { ...defaults,
    soubory: media("a.jpg", "b.jpg", "d.jpg"),
    prirazeni: { "a.jpg": "jana", "b.jpg": "pavla", "d.jpg": "dalsi" },
    skupiny: { ...defaults.skupiny, dalsi: { nazev: "Další" } } };
  reconcile(p, plan);
  // c.jpg se už nepřenese, d.jpg přibyl; ruční skupina a.jpg zůstala.
  assert.deepEqual(p.soubory, { "a.jpg": { skupina: "nova" },
    "b.jpg": { skupina: "pavla" }, "d.jpg": { skupina: "dalsi" } });
  assert.deepEqual(p.skupiny.dalsi, { nazev: "Další" });
  assert.deepEqual(p.pripojit, { pavla: "g9" });
});

test("připojená skupina dědí autory existující", () => {
  const p = freshDescription(defaults, null);
  p.pripojit = { pavla: "g9" };
  const doc = effectiveDoc(p);
  assert.equal(doc.soubory["b.jpg"].skupina, "g9");
  assert.equal(doc.skupiny.pavla, undefined);
  // jana nemá autory; pavla je připojená k g9 s autory.
  assert.deepEqual(groupsWithoutAuthors(p), ["jana"]);
  // Autoři akce (rozpracovaný import z doby před schématem /2) nepomohou.
  p.akce.autori = ["Příkladný, Daniel"];
  assert.deepEqual(groupsWithoutAuthors(p), ["jana"]);
});
