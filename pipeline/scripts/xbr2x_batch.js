#!/usr/bin/env node

// Binary batch adapter around the exact xBR2X/xBR4X implementations embedded in
// the local MMPX/scalepix page. The page is initialized once per sprite batch.

const fs = require('fs');
const vm = require('vm');

const scalepixPath = process.argv[2];
const requestedMode = process.argv[3] || 'legacy-xbr2x';
const xbrBlend = process.argv[4] === 'true';
if (!scalepixPath) {
  throw new Error('Usage: node xbr2x_batch.js <scalepix.html> [xbr2x|xbr4x] [true|false]');
}
if (!['legacy-xbr2x', 'xbr2x', 'xbr4x'].includes(requestedMode)) {
  throw new Error(`unsupported xBR mode: ${requestedMode}`);
}

const INPUT_MAGIC = Buffer.from('XBR2BAT\0', 'ascii');
const OUTPUT_MAGIC = Buffer.from('XBR2OUT\0', 'ascii');
const XN_INPUT_MAGIC = Buffer.from('XBRNBAT\0', 'ascii');
const XN_OUTPUT_MAGIC = Buffer.from('XBRNOUT\0', 'ascii');

function makeRuntime() {
  const checks = {xbr_blend: {checked: xbrBlend}, bilinear_unbiased: {checked: false}};
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
  vm.runInContext(`globalThis.__creatureSpriteXbr = {
    classifyBuffer,
    invertBufferInPlace,
    setClassification: value => { classification = value; },
    runXBR2X,
    runXBR4X(srcBuffer, srcWidth, srcHeight, dstBuffer) {
      const out = xbr4x(srcBuffer, srcWidth, srcHeight, {
        blendColors: document.getElementById('xbr_blend').checked,
        scaleAlpha: true
      });
      dstBuffer.set(out);
    }
  };`, sandbox, {filename: scalepixPath});
  return sandbox.__creatureSpriteXbr;
}

function u32(buffer, offset) {
  if (offset < 0 || offset + 4 > buffer.length) throw new Error('truncated batch input');
  return buffer.readUInt32LE(offset);
}

const input = fs.readFileSync(0);
const legacyProtocol = requestedMode === 'legacy-xbr2x';
const expectedScale = requestedMode === 'xbr4x' ? 4 : 2;
const expectedInputMagic = legacyProtocol ? INPUT_MAGIC : XN_INPUT_MAGIC;
const headerBytes = legacyProtocol ? 12 : 16;
if (input.length < headerBytes || !input.subarray(0, 8).equals(expectedInputMagic)) {
  throw new Error('invalid xBR batch input');
}
const scale = legacyProtocol ? 2 : u32(input, 8);
const count = u32(input, legacyProtocol ? 8 : 12);
if (scale !== expectedScale) {
  throw new Error(`xBR protocol scale ${scale} differs from mode ${requestedMode}`);
}
if (count === 0 || count > 100000) throw new Error(`invalid frame count: ${count}`);

const algorithm = makeRuntime();
const outputs = [];
let offset = headerBytes;
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
  const destination = new Uint32Array(width * height * scale * scale);
  const run = scale === 4 ? algorithm.runXBR4X : algorithm.runXBR2X;
  run(source, width, height, destination);
  if (classification === 'font') algorithm.invertBufferInPlace(destination);
  outputs.push({
    width: width * scale,
    height: height * scale,
    rgba: Buffer.from(destination.buffer, destination.byteOffset, destination.byteLength),
  });
}
if (offset !== input.length) throw new Error('trailing bytes in xBR batch input');

const chunks = legacyProtocol
  ? [OUTPUT_MAGIC, Buffer.allocUnsafe(4)]
  : [XN_OUTPUT_MAGIC, Buffer.allocUnsafe(8)];
if (legacyProtocol) {
  chunks[1].writeUInt32LE(outputs.length, 0);
} else {
  chunks[1].writeUInt32LE(scale, 0);
  chunks[1].writeUInt32LE(outputs.length, 4);
}
for (const output of outputs) {
  const header = Buffer.allocUnsafe(12);
  header.writeUInt32LE(output.width, 0);
  header.writeUInt32LE(output.height, 4);
  header.writeUInt32LE(output.rgba.length, 8);
  chunks.push(header, output.rgba);
}
process.stdout.write(Buffer.concat(chunks));
