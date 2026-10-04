/* Deterministic offline model. Cached Q3m planes, no network or game access. */
(function (global) {
  'use strict';
  const bytes = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  function decode(layer, scale, palette) {
    const {I, F} = layer.planes[String(scale)];
    const ii = bytes(I), ff = bytes(F), data = new Uint8ClampedArray(ii.length * 4);
    for (let k = 0; k < ii.length; k++) {
      const i = ii[k], f = ff[k];
      const terminal = i < 4 || (i < 88 ? (i - 4) % 12 === 11 : (i - 88) % 8 === 7);
      const j = terminal ? i : i + 1;
      for (let c = 0; c < 3; c++) data[k * 4 + c] = (palette[i * 4 + c] * (8 - f) + palette[j * 4 + c] * f + 4) >> 3;
      data[k * 4 + 3] = palette[i * 4 + 3];
    }
    return {w: layer.w * scale, h: layer.h * scale, data, cx: layer.cx, cy: layer.cy};
  }
  function premultiplied(image, rounded = false) {
    const data = new Float64Array(image.data.length);
    for (let k = 0; k < data.length; k += 4) {
      const a = image.data[k + 3] / 255;
      for (let c = 0; c < 3; c++) {
        const v = image.data[k + c] * a;
        data[k + c] = (rounded ? Math.round(v + 1e-9) : v) / 255;
      }
      data[k + 3] = a;
    }
    return {w: image.w, h: image.h, data};
  }
  function tap(image, x, y) {
    if (x < 0 || y < 0 || x >= image.w || y >= image.h) return [0, 0, 0, 0];
    const k = (y * image.w + x) * 4;
    return [image.data[k], image.data[k + 1], image.data[k + 2], image.data[k + 3]];
  }
  function straight(p) {
    const a = clamp(p[3], 0, 1);
    return a <= 1e-6 ? [0, 0, 0, a] : [clamp(p[0], 0, a) / a, clamp(p[1], 0, a) / a, clamp(p[2], 0, a) / a, a];
  }
  function pyramid(image) {
    const chain = [premultiplied(image, true)];
    while (Math.max(chain.at(-1).w, chain.at(-1).h) > 1) {
      const prev = chain.at(-1), w = Math.max(1, Math.floor(prev.w / 2)), h = Math.max(1, Math.floor(prev.h / 2));
      const data = new Float64Array(w * h * 4), sx = prev.w / w, sy = prev.h / h;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const loX = x * sx, loY = y * sy, hiX = loX + sx, hiY = loY + sy, k = (y * w + x) * 4;
        for (let j = Math.floor(loY); j < Math.ceil(hiY); j++) for (let i = Math.floor(loX); i < Math.ceil(hiX); i++) {
          const weight = Math.max(0, Math.min(hiX, i + 1) - Math.max(loX, i)) * Math.max(0, Math.min(hiY, j + 1) - Math.max(loY, j)) / (sx * sy);
          const p = tap(prev, i, j);
          for (let c = 0; c < 4; c++) data[k + c] += p[c] * weight;
        }
        for (let c = 0; c < 4; c++) data[k + c] = Math.round(data[k + c] * 255 + 1e-9) / 255;
      }
      chain.push({w, h, data});
    }
    return chain;
  }
  function linear(image, x, y) {
    const bx = Math.floor(x - .5), by = Math.floor(y - .5), tx = x - .5 - bx, ty = y - .5 - by, out = [0, 0, 0, 0];
    for (let j = 0; j < 2; j++) for (let i = 0; i < 2; i++) {
      const p = tap(image, bx + i, by + j), weight = (i ? tx : 1 - tx) * (j ? ty : 1 - ty);
      for (let c = 0; c < 4; c++) out[c] += p[c] * weight;
    }
    return out;
  }
  function prepare(image, method) {
    return {...image, pm: premultiplied(image), mips: method === 'Mipmaps' ? pyramid(image) : null};
  }
  function sample(image, x, y, footprint, method) {
    if (method === 'Nearest' || ((method === 'BOX' || method === 'Mipmaps') && footprint <= 1) || (method === 'BOX' && footprint > 16)) {
      return tap(image, Math.floor(x), Math.floor(y)).map(v => v / 255);
    }
    if (method === 'BOX') {
      const loX = x - footprint / 2, loY = y - footprint / 2, bx = Math.floor(loX), by = Math.floor(loY), out = [0, 0, 0, 0];
      for (let j = 0; j < Math.ceil(footprint) + 1; j++) {
        const wy = Math.max(0, Math.min(loY + footprint, by + j + 1) - Math.max(loY, by + j));
        for (let i = 0; i < Math.ceil(footprint) + 1; i++) {
          const wx = Math.max(0, Math.min(loX + footprint, bx + i + 1) - Math.max(loX, bx + i));
          const p = tap(image.pm, bx + i, by + j), weight = wx * wy / footprint ** 2;
          for (let c = 0; c < 4; c++) out[c] += p[c] * weight;
        }
      }
      return straight(out);
    }
    if (method === 'Catmull-Rom') {
      const bx = Math.floor(x - .5), by = Math.floor(y - .5), tx = x - .5 - bx, ty = y - .5 - by, out = [0, 0, 0, 0];
      const weights = t => [-.5 * t ** 3 + t * t - .5 * t, 1.5 * t ** 3 - 2.5 * t * t + 1, -1.5 * t ** 3 + 2 * t * t + .5 * t, .5 * t ** 3 - .5 * t * t];
      const wx = weights(tx), wy = weights(ty);
      for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) {
        const p = tap(image.pm, bx + i - 1, by + j - 1), weight = wx[i] * wy[j];
        for (let c = 0; c < 4; c++) out[c] += p[c] * weight;
      }
      return straight(out);
    }
    const lod = Math.min(Math.log2(footprint), image.mips.length - 1), level = Math.floor(lod), t = lod - level;
    const a = image.mips[level], b = image.mips[Math.min(level + 1, image.mips.length - 1)];
    const aa = linear(a, x * a.w / image.w, y * a.h / image.h), bb = linear(b, x * b.w / image.w, y * b.h / image.h);
    return straight(aa.map((v, c) => v * (1 - t) + bb[c] * t));
  }
  function filtered(layers, scale, zoom, method, phase = .25) {
    // Transparent texture borders, common native-coordinate rectangle.
    const w = Math.ceil(80 * zoom), h = Math.ceil(90 * zoom), data = new Uint8ClampedArray(w * h * 4);
    const prepared = layers.map(image => prepare(image, method));
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const worldX = -40 + (x + .5 - phase) / zoom, worldY = -75 + (y + .5 - phase) / zoom;
      let pm = [0, 0, 0], a = 0;
      for (const image of prepared) {
        const s = sample(image, (worldX + image.cx) * scale, (worldY + image.cy) * scale, scale / zoom, method);
        pm = pm.map((v, c) => s[c] * s[3] + v * (1 - s[3]));
        a = s[3] + a * (1 - s[3]);
      }
      const k = (y * w + x) * 4;
      for (let c = 0; c < 3; c++) data[k + c] = a > 1e-8 ? Math.round(clamp(pm[c] / a, 0, 1) * 255) : 0;
      data[k + 3] = Math.round(a * 255);
    }
    return {w, h, data};
  }
  function background(w, h, kind) {
    const data = new Uint8ClampedArray(w * h * 4);
    const base = kind === 'parchment' ? [184, 166, 132] : kind === 'grid' ? [19, 25, 27] : [61, 64, 60];
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let n;
      if (kind === 'parchment') n = 2 * Math.sin(x * .079) * Math.cos(y * .057) + 1.2 * Math.sin(x * .021 + y * .039);
      else if (kind === 'grid') n = x % 120 === 0 || y % 120 === 0 ? 13 : x % 24 === 0 || y % 24 === 0 ? 8 : 0;
      else {
        n = 2.5 * Math.sin(x * .08 + y * .035) * Math.cos(y * .11) + 1.1 * Math.sin(x * .43 + y * .21);
        if (y % 70 < 2 || (x + (Math.floor(y / 70) % 2) * 57) % 114 < 2) n -= 16;
        if (y % 70 === 3) n += 5;
      }
      const k = (y * w + x) * 4;
      for (let c = 0; c < 3; c++) data[k + c] = Math.floor(clamp(base[c] + n, 0, 255));
      data[k + 3] = 255;
    }
    return {w, h, data};
  }
  global.SIM = {bytes, decode, premultiplied, pyramid, sample, prepare, filtered, background};
})(window);
