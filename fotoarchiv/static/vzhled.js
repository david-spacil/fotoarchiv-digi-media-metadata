// Světlý/tmavý režim (výchozí tmavý). Klasický skript v <head> před
// style.css, aby stránka neproblikla v jiném režimu. Volba je
// v localStorage (`rezim`); vypnuté úložiště = tmavý režim.
(function () {
  var r = null;
  try { r = localStorage.getItem("rezim"); } catch (e) { /* bez úložiště */ }
  if (r === "svetly") document.documentElement.setAttribute("data-rezim", r);
})();
