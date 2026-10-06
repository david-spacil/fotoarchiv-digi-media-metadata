// Skládání data pořízení ze dne a času (scénáře ze specifikace
// metadata-workspace, „Kalendář u data pořízení“).
import { test } from "node:test";
import assert from "node:assert/strict";

import { parts, withDay, withTime } from "../../fotoarchiv/static/datetime.js";

test("změna dne se zachováním času", () => {
  assert.equal(withDay("2026-04-28T09:44:36", "2026-04-29"),
    "2026-04-29T09:44:36");
});

test("datum bez času", () => {
  assert.equal(withDay("2026-04-28", "2026-04-30"), "2026-04-30");
});

test("prázdné datum", () => {
  assert.equal(withDay(undefined, "2026-04-28"), "2026-04-28");
});

test("doplnění času", () => {
  assert.equal(withTime("2026-04-28", "14:05:10"), "2026-04-28T14:05:10");
});

test("smazání času", () => {
  assert.equal(withTime("2026-04-28T09:44:36", ""), "2026-04-28");
});

test("smazání dne", () => {
  assert.equal(withDay("2026-04-28T09:44:36", ""), "");
});

test("čas bez dne", () => {
  assert.equal(withTime(undefined, "12:00:00"), "");
});

test("rozdílné časy ve výběru", () => {
  assert.deepEqual(parts(["2026-04-28T09:44:36", "2026-04-28T10:02:11"]),
    { day: "2026-04-28", time: "", mixed: true });
});

test("stejné hodnoty a prázdno", () => {
  assert.deepEqual(parts(["2026-04-28", "2026-04-28"]),
    { day: "2026-04-28", time: "", mixed: false });
  assert.deepEqual(parts([undefined]), { day: "", time: "", mixed: false });
});

test("nový čas ve výběru", () => {
  const vals = ["2026-04-28T09:44:36", "2026-04-29T10:02:11"];
  assert.deepEqual(vals.map((v) => withTime(v, "12:00:00")),
    ["2026-04-28T12:00:00", "2026-04-29T12:00:00"]);
});

test("nový den ve výběru", () => {
  const vals = ["2026-04-28T09:44:36", "2026-04-28"];
  assert.deepEqual(vals.map((v) => withDay(v, "2026-05-01")),
    ["2026-05-01T09:44:36", "2026-05-01"]);
});
