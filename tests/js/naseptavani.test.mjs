// Umístění seznamu návrhů jmen (scénáře ze změny
// „pojmenovani-zpet-a-naseptavani“, rozhodnutí 5: dolů, když se vejde;
// jinak nahoru, je-li nahoře víc místa; jinak větší strana s maxHeight).
import { test } from "node:test";
import assert from "node:assert/strict";

import { umisteni } from "../../fotoarchiv/static/naseptavani.js";

// Pole 10 px vysoko, vlevo na 100 px, široké 240 px.
const pole = (top, bottom = top + 24) =>
  ({ left: 100, top, bottom, width: 240 });
// Okno výšky 600 px bez posunu.
const okno = (top = 0, height = 600) => ({ top, height });
const VYSKA = 200;

test("umisteni: dost místa dole → dolů pod pole", () => {
  const v = umisteni({ pole: pole(100), okno: okno(), vyska: VYSKA });
  assert.equal(v.smer, "dolu");
  assert.equal(v.top, 124); // rovnou pod dolní hranou pole
  assert.ok(v.maxHeight >= VYSKA);
});

test("umisteni: přesně na těsno dole → stále dolů", () => {
  // pole.bottom = 400, okno končí v 600 → dole přesně 200 = vyska
  const v = umisteni({ pole: pole(376, 400), okno: okno(), vyska: 200 });
  assert.equal(v.smer, "dolu");
  assert.equal(v.top, 400);
  assert.equal(v.maxHeight, 200);
});

test("umisteni: málo dole a víc nahoře → nahoru nad pole", () => {
  // dole 50 px, nahoře 400 px
  const v = umisteni({ pole: pole(400, 424), okno: okno(), vyska: VYSKA });
  assert.equal(v.smer, "nahoru");
  assert.equal(v.top, 400 - VYSKA); // horní hrana končí nad polem
  assert.ok(v.maxHeight >= VYSKA);
});

test("umisteni: klávesnice telefonu → nahoru, pod pole nesmí", () => {
  // Layout okno 800 px, viditelná část jen 0–400 (klávesnice zabírá zbytek),
  // pole těsně nad klávesnicí.
  const v = umisteni({ pole: pole(360, 384), okno: okno(0, 400),
    vyska: VYSKA });
  assert.equal(v.smer, "nahoru");
  assert.equal(v.top, 360 - VYSKA);
  // seznam se vejde do viditelné části a sahá pod pole až pod klávesnici
  assert.ok(v.top >= 0);
  assert.ok(v.top + VYSKA <= 360);
});

test("umisteni: viditelná část posunutá (offsetTop) počítá s ní", () => {
  // Stránka odscrollovaná, visualViewport: top 150, height 400.
  // Pole na 200–224: dole = 550 − 224 = 326 → vejde se dolů.
  const v = umisteni({ pole: pole(200, 224), okno: okno(150, 400),
    vyska: VYSKA });
  assert.equal(v.smer, "dolu");
  assert.equal(v.top, 224);
});

test("umisteni: málo místa obojí → větší strana dole s maxHeight", () => {
  // viditelná část 0–264: pole 60–164 → dole 100 px, nahoře 60 px,
  // seznam 200 px → dolů na kratko s posuvníkem
  const v = umisteni({ pole: pole(60, 164), okno: okno(0, 264),
    vyska: VYSKA });
  assert.equal(v.smer, "dolu");
  assert.equal(v.top, 164);
  assert.equal(v.maxHeight, 100); // zbytek vyřeší posuvník uvnitř seznamu
});

test("umisteni: málo místa obojí → větší strana nahoře s maxHeight", () => {
  // viditelná část 0–184: pole 100–124 → nahoře 100 px, dole 60 px,
  // seznam 200 px → nahoru na kratko
  const v = umisteni({ pole: pole(100, 124), okno: okno(0, 184),
    vyska: VYSKA });
  assert.equal(v.smer, "nahoru");
  assert.equal(v.top, 0); // 100 − min(200, 100)
  assert.equal(v.maxHeight, 100);
});

test("umisteni: shoda stran bez místa → dolů", () => {
  // viditelná část 0–244: pole 80–164 → dole == nahoře == 80 px
  const v = umisteni({ pole: pole(80, 164), okno: okno(0, 244),
    vyska: VYSKA });
  assert.equal(v.smer, "dolu");
  assert.equal(v.top, 164);
  assert.equal(v.maxHeight, 80);
});

test("umisteni: left a width berou pole, top nikdy nezáporný souřadnicově", () => {
  const v = umisteni({ pole: pole(100), okno: okno(), vyska: VYSKA });
  assert.equal(v.left, 100);
  assert.equal(v.width, 240);
});

test("umisteni: maxHeight nikdy nezáporný, ani když je pole mimo okno", () => {
  // Pole zcela pod viditelnou částí (třeba pod klávesnicí): nahoru je
  // spousta místa, výsledek musí mít maxHeight >= 0.
  const v = umisteni({ pole: pole(700, 724), okno: okno(0, 400),
    vyska: VYSKA });
  assert.equal(v.smer, "nahoru");
  assert.ok(v.maxHeight >= 0);
  // Pole vyšší než malá viditelná část (překrývá ji): dole i nahoře
  // záporné → dolů s maxHeight sraženým na 0.
  const v2 = umisteni({ pole: pole(50, 200), okno: okno(100, 50),
    vyska: VYSKA });
  assert.equal(v2.smer, "dolu");
  assert.equal(v2.maxHeight, 0);
});
