"""Pair the measured duplicate DEFLATE6 sum with new index/manifest overhead."""
import zlib
from common import ROOT, OUT, RELEASE, load, save


def compressed_bytes(path):
    compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
    result = 0
    with path.open('rb') as stream:
        while block := stream.read(1024*1024):
            result += len(compressor.compress(block))
    return result + len(compressor.flush())


def main():
    audit = load(ROOT/'effects/research/duplicate-analysis-20261110-v1/summary.json')['categories']['rgba']
    pack = load(OUT/'pack-receipt.json')
    assert audit['redundant_files'] == pack['removed_files'] and audit['saved_bytes'] == pack['saved_rgba_bytes']
    base = RELEASE/'release-inputs/effects'
    added_index = compressed_bytes(base/'accepted-shared-20261110-v1/EffectStorage-X4.index')
    manifest_growth = compressed_bytes(base/'accepted-shared-20261110-v1/manifest.json')-compressed_bytes(base/'accepted-20261110-v1/manifest.json')
    save(OUT/'archive-delta.json', dict(method='ZIP raw DEFLATE level6 file payloads; paired exact delta',
        removed_compressed_rgba_bytes=audit['deflate6_duplicate_payload_bytes'],
        added_compressed_index_bytes=added_index, compressed_manifest_growth_bytes=manifest_growth,
        net_compressed_effect_payload_saved_bytes=audit['deflate6_duplicate_payload_bytes']-added_index-manifest_growth,
        limits=['ZIP headers/path/checksum deltas and renderer/other package metadata excluded.',
                'Archive not built; applies to independent per-file DEFLATE6, not solid compression.']))
    print(load(OUT/'archive-delta.json'))


if __name__ == '__main__':
    main()
