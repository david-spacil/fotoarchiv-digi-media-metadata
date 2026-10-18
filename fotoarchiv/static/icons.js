// Ikony plochy jako inline SVG. Tah `currentColor`, takže ikona bere
// barvu textu (tokeny ve style.css). Tlačítko jen s ikonou potřebuje
// `aria-label` a `title`; samotná ikona je pro čtečky skrytá.

const NS = "http://www.w3.org/2000/svg";

// Obrysy v mřížce 24 × 24.
const PATHS = {
  datum: ["M4 6h16v14H4z", "M4 10h16", "M8 3v5", "M16 3v5"],
  misto: ["M12 21s-6-6.2-6-11a6 6 0 0 1 12 0c0 4.8-6 11-6 11z",
    "M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"],
  osoba: ["M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    "M4 21c0-4 3.6-6 8-6s8 2 8 6"],
  skupina: ["M3 6h6l2 2h10v11H3z"],
  souradnice: ["M12 19a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M12 2v5",
    "M12 17v5", "M2 12h5", "M17 12h5"],
  vyradit: ["M4 7h16", "M9 7V4h6v3", "M6 7l1 13h10l1-13", "M10 11v6",
    "M14 11v6"],
  panel: ["M3 4h18v16H3z", "M15 4v16"],
  mrizka: ["M4 4h7v7H4z", "M13 4h7v7h-7z", "M4 13h7v7H4z",
    "M13 13h7v7h-7z"],
  radky: ["M4 6h16", "M4 12h16", "M4 18h16"],
  enter: ["M20 4v7a4 4 0 0 1-4 4H4", "M9 10l-5 5 5 5"],
  lupa: ["M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z",
    "M15.5 15.5L21 21"],
};

export function icon(name, cls = "") {
  const svg = document.createElementNS(NS, "svg");
  for (const [k, v] of Object.entries({
    viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
    "stroke-width": "2", "stroke-linecap": "round",
    "stroke-linejoin": "round", "aria-hidden": "true",
    class: `icon${cls ? ` ${cls}` : ""}`,
  })) svg.setAttribute(k, v);
  for (const d of PATHS[name]) {
    const p = document.createElementNS(NS, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}
