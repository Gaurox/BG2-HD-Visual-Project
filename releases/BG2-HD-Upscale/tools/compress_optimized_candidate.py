"""Build and validate a standard ZIP/Deflate variant of the exact alpha.12 payload."""
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import zipfile
import zlib

from build_optimized_candidate import DIST, OUT

LEVEL = 4
CHUNK = 4 << 20
WORKERS = 12
ORIGINAL = OUT
SOURCE = OUT.with_suffix('')
STAGE = OUT.with_name(OUT.stem + '-deflate-zlib.partial.zip')
FINAL = OUT.with_name(OUT.stem + '-deflate.zip')


def deflate(data, tail, flush):
    compressor = (zlib.compressobj(LEVEL, wbits=-15, zdict=tail) if tail
                  else zlib.compressobj(LEVEL, wbits=-15))
    return compressor.compress(data) + compressor.flush(flush)


class ParallelDeflate:
    """Emit ordered byte-aligned nonfinal blocks followed by one final block."""

    def __init__(self, executor):
        self.executor = executor
        self.queue = deque()
        self.pending = b''
        self.tail = b''

    def compress(self, block):
        if not block:
            return b''
        # Keep the last input block for Z_FINISH. Each preceding block is
        # byte aligned and receives the preceding bytes as its DEFLATE window.
        if self.pending:
            self.queue.append(self.executor.submit(deflate, self.pending, self.tail, zlib.Z_SYNC_FLUSH))
            self.tail = (self.tail + self.pending[-32768:])[-32768:]
        self.pending = block
        if len(self.queue) >= WORKERS + 2:
            return self.queue.popleft().result()
        return b''

    def flush(self):
        if not self.queue:
            return deflate(self.pending, self.tail, zlib.Z_FINISH)
        last = self.executor.submit(deflate, self.pending, self.tail, zlib.Z_FINISH)
        return b''.join([*(chunk.result() for chunk in self.queue), last.result()])


def write_zip(entries):
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        # ZipFile still owns the ZIP64 structure, sizes and CRCs.
        factory = zipfile._get_compressor
        def select(method, level=None):
            return ParallelDeflate(executor) if method == zipfile.ZIP_DEFLATED else factory(method, level)

        sample = (b'anchor:ABCD' * CHUNK) + b'end'
        test = ParallelDeflate(executor)
        pieces = [test.compress(sample[i:i+CHUNK]) for i in range(0, len(sample), CHUNK)]
        assert zlib.decompress(b''.join(pieces) + test.flush(), wbits=-15) == sample
        zipfile._get_compressor = select
        try:
            with zipfile.ZipFile(STAGE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=LEVEL) as output:
                total = 0
                next_update = 2 << 30
                for item in entries.values():
                    info = zipfile.ZipInfo(item.filename, item.date_time)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.file_size = item.file_size
                    with (SOURCE/item.filename).open('rb') as src, output.open(info, 'w', force_zip64=item.file_size >= 2**31) as out:
                        for block in iter(lambda: src.read(CHUNK), b''):
                            out.write(block)
                            total += len(block)
                            if total >= next_update:
                                print(f'{total/1e9:.2f} Go lus pour la compression', flush=True)
                                next_update += 2 << 30
                    if info.file_size != item.file_size or info.CRC != item.CRC:
                        raise ValueError(f'Input differs from original ZIP: {item.filename}')
        finally:
            zipfile._get_compressor = factory


def verify(original, entries):
    manifest = original.read('checksums.sha256')
    hashes = {n:s.upper() for s,n in (ln.split('  ',1) for ln in manifest.decode().splitlines())}
    hashes['checksums.sha256'] = hashlib.sha256(manifest).hexdigest().upper()
    if hashes.keys() != entries.keys():
        raise ValueError('Original checksum inventory differs')
    gains = Counter()
    with zipfile.ZipFile(STAGE) as output:
        compressed = output.infolist()
        if len(compressed) != len(entries) or {i.filename for i in compressed} != entries.keys():
            raise ValueError('Compressed inventory differs')
        for index, info in enumerate(compressed, 1):
            old = entries[info.filename]
            if (info.file_size, info.CRC, info.compress_type) != (old.file_size, old.CRC, zipfile.ZIP_DEFLATED):
                raise ValueError(f'Invalid ZIP record: {info.filename}')
            with output.open(info) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest().upper()
            if digest != hashes[info.filename]:
                raise ValueError(f'Archive bytes differ: {info.filename}')
            parts = info.filename.split('/')
            group = parts[2] if len(parts) > 3 and parts[:2] == ['bg2hd','payload'] else ''
            names = (('effects-','effects'),('animation-','area_animations'),('map-','maps'),('sprites-','sprites'))
            kind = next((name for prefix,name in names if group.startswith(prefix)), 'other')
            gains[kind] += old.compress_size - info.compress_size
            if index%5000 == 0:
                print(f'{index}/{len(compressed)} fichiers vérifiés par SHA-256', flush=True)
    return dict(gains)


def main():
    if FINAL.exists() or STAGE.exists():
        raise FileExistsError('Archive de test déjà présente')
    with zipfile.ZipFile(ORIGINAL) as archive:
        entries = {item.filename:item for item in archive.infolist() if not item.is_dir()}
        if len(entries) != len(archive.infolist()):
            raise ValueError('Unexpected duplicate or directory in reference ZIP')
        write_zip(entries)
        print('Compression terminée, vérification du ZIP', flush=True)
        gains = verify(archive, entries)
    base, size = ORIGINAL.stat().st_size, STAGE.stat().st_size
    with STAGE.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest().upper()
    result = dict(deflate_level=LEVEL, baseline_zip_bytes=base, deflate_zip_bytes=size,
                  savings_bytes=base-size, savings_pct=round(100*(base-size)/base, 4),
                  verified_files=len(entries), payload_savings_by_kind=gains, sha256=digest)
    STAGE.rename(FINAL)
    FINAL.with_suffix('.zip.sha256').write_text(f'{digest}  {FINAL.name}\n', encoding='ascii')
    (DIST/'deflate-results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2), end='')


if __name__ == '__main__':
    main()
