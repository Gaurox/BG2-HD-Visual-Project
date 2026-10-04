/* Numeric consistency of the interactive model against the rendered boards.
   Node only; this is not a browser layout check or an in-game test. */
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const directory = __dirname, context = {window: {}, atob: v => Buffer.from(v, 'base64').toString('binary'), Uint8Array, Uint8ClampedArray, Float64Array, Math};
vm.createContext(context);
for (const f of ['data.js', 'simulation.js']) vm.runInContext(fs.readFileSync(path.join(directory, f), 'utf8'), context, {filename: f});
const D = context.window.VISUAL_DATA, S = context.window.SIM, palette = S.bytes(D.palettes[0].rgba);
const layers = D.poses[0].layers.map(layer => S.decode(layer, 4, palette));
const reference = JSON.parse(fs.readFileSync(path.join(directory, 'filter-reference.json'), 'utf8'));
const output = {schema: 'bg2-offline-visual-js-consistency-v1', browser_layout_tested: false, results: {}};
for (const method of ['Nearest', 'BOX', 'Mipmaps', 'Catmull-Rom']) {
  const actual = S.filtered(layers, 4, 1.35, method), expected = Buffer.from(reference.methods[method], 'base64');
  if (actual.w !== reference.w || actual.h !== reference.h || actual.data.length !== expected.length) throw new Error(method + ': dimensions differ');
  let max = 0, changed = 0;
  for (let i = 0; i < expected.length; i++) {const delta = Math.abs(actual.data[i] - expected[i]); max = Math.max(max, delta); if (delta) changed++;}
  if (max > 1) throw new Error(method + ': static/interactive byte difference ' + max);
  output.results[method] = {maximum_RGBA8_difference: max, rounding_differences: changed};
}
const prepared = S.prepare(layers[0], 'BOX');
for (const zoom of [.8, .25]) {
  if (JSON.stringify(S.sample(prepared, 12.25, 23.75, zoom, 'BOX')) !== JSON.stringify(S.sample(prepared, 12.25, 23.75, zoom, 'Nearest'))) throw new Error('BOX magnification fallback differs');
}
output.BOX_magnification_fallback_matches_Nearest = true;
fs.writeFileSync(path.join(directory, 'simulation-checks.json'), JSON.stringify(output, null, 2) + '\n');
process.stdout.write(JSON.stringify(output) + '\n');
