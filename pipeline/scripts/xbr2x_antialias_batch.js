#!/usr/bin/env node

// Binary batch adapter for the exact Scalepix xBR2X implementation with its
// Antialias checkbox enabled. This adapter is intentionally separate from
// xbr2x_batch.js so legacy and V3 xN production keep their existing protocol
// and hashes.

const fs = require('fs');
const vm = require('vm');

const scalepixPath = process.argv[2];
if (!scalepixPath) {
  throw new Error('Usage: node xbr2x_antialias_batch.js <scalepix.html>');
}

const INPUT_MAGIC = Buffer.from('XBRA2BT\0', 'ascii');
const OUTPUT_MAGIC = Buffer.from('XBRA2OT\0', 'ascii');

function makeRuntime() {
  const checks = {xbr_blend: {checked: true}, bilinear_unbiased: {checked: false}};
  const context2d = {
    createImageData(width, height) {
      return {width, height, data: new Uint8ClampedArray(width * height * 4)};
    },
  };
  const sandbox = {
    Uint8ClampedArray,
    Uint32Array,
    Math,
    console: {log() {}, warn() {}, error() {}},
    performance: {now: () => 0},
    Image: class {},
    document: {
      createElement: () => ({getContext: () => context2d}),
      getElementById: (id) => checks[id] || {checked: false},
    },
  };
  vm.createContext(sandbox);
  const page = fs.readFileSync(scalepixPath, 'utf8');
  const scripts = [...page.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
    .map((match) => match[1]);
  for (const script of scripts) vm.runInContext(script, sandbox, {filename: scalepixPath});
  vm.runInContext(`globalThis.__creatureSpriteXbrAa = {
    classifyBuffer,
    invertBufferInPlace,
    setClassification: value => { classification = value; },
    runXBR2X
  };`, sandbox, {filename: scalepixPath});
  return sandbox.__creatureSpriteXbrAa;
}

function u32(buffer, offset) {
  if (offset < 0 || offset + 4 > buffer.length) throw new Error('truncated batch input');
  return buffer.readUInt32LE(offset);
}

const input = fs.readFileSync(0);
if (input.length < 12 || !input.subarray(0, 8).equals(INPUT_MAGIC)) {
  throw new Error('invalid xBR2X Antialias batch input');
}
const count = u32(input, 8);
if (count === 0 || count > 100000) throw new Error(`invalid frame count: ${count}`);

const algorithm = makeRuntime();
const outputs = [];
let offset = 12;
for (let frameIndex = 0; frameIndex < count; ++frameIndex) {
  const width = u32(input, offset);
  const height = u32(input, offset + 4);
  const byteCount = u32(input, offset + 8);
  offset += 12;
  if (width === 0 || height === 0 || width > 4096 || height > 4096 ||
      byteCount !== width * height * 4 || offset + byteCount > input.length) {
    throw new Error(`invalid frame ${frameIndex}`);
  }
  const rgba = Buffer.from(input.subarray(offset, offset + byteCount));
  offset += byteCount;
  const source = new Uint32Array(rgba.buffer, rgba.byteOffset, rgba.byteLength / 4);
  const classification = algorithm.classifyBuffer(source);
  algorithm.setClassification(classification);
  if (classification === 'font') algorithm.invertBufferInPlace(source);
  const destination = new Uint32Array(width * height * 4);
  algorithm.runXBR2X(source, width, height, destination);
  if (classification === 'font') algorithm.invertBufferInPlace(destination);
  outputs.push({
    width: width * 2,
    height: height * 2,
    rgba: Buffer.from(destination.buffer, destination.byteOffset, destination.byteLength),
  });
}
if (offset !== input.length) throw new Error('trailing bytes in xBR batch input');

const chunks = [OUTPUT_MAGIC, Buffer.allocUnsafe(4)];
chunks[1].writeUInt32LE(outputs.length, 0);
for (const output of outputs) {
  const header = Buffer.allocUnsafe(12);
  header.writeUInt32LE(output.width, 0);
  header.writeUInt32LE(output.height, 4);
  header.writeUInt32LE(output.rgba.length, 8);
  chunks.push(header, output.rgba);
}
process.stdout.write(Buffer.concat(chunks));
