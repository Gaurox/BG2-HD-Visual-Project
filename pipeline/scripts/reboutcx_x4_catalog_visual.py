"""Repackage verified 0x6110 x4 pixels for nonblocking catalog startup."""
import json
from pathlib import Path
import reboutcx_x4_visual_test as source
import run_creature_sprite_x2 as xn


def main():
    output = source.OUTPUT.with_name('reboutcx-x4-visual-catalog-v2')
    if (output / 'manifest.json').exists():
        raise RuntimeError('Catalog already exists; preserve the previous generation')
    manifest = source.read_json(source.OUTPUT / 'manifest.json')
    pack = output / 'build/iee-assets/creature-sprites'
    records = []
    for shard in manifest['shards']:
        path = source.OUTPUT / 'build' / shard['path']
        info = xn.inspect_registry(path, include_resource_records=True)
        if info['sha256'] != shard['sha256'] or info['scale'] != 4:
            raise RuntimeError('Source x4 shard changed')
        records.extend(info['resource_records'])
    partitions = xn.partition_registry_resources(
        records, maximum_resources=16, maximum_bytes=512 * 1024**2,
        maximum_shards=64)
    pack.mkdir(parents=True, exist_ok=True)
    shards, components, directory, logical = [], [], [], []
    for index, group in enumerate(partitions):
        scratch = pack / f'part-{index:04d}.tmp'
        info = xn.write_compressed_catalog_registry_records(scratch, 4, group)
        final = pack / xn.catalog_shard_filename(info['sha256'])
        if final.exists():
            if xn.sha256_file(final) != info['sha256']:
                raise RuntimeError('Existing shard differs')
            scratch.unlink()
        else:
            scratch.rename(final)
        digest = xn.catalog_component_digest(4, [xn.catalog_shard_entry_bytes(info, final)])
        components.append(dict(index=index, digest=digest, shard_start=index,
                               shard_count=1, **{key: info[key] for key in
                               ('resource_count', 'frame_count', 'index_bytes', 'registry_bytes')}))
        shards.append(info)
        logical.append(xn.catalog_source_component_sha256(4, sorted(group, key=lambda r: r['resref'])))
        for ordinal, record in enumerate(group):
            directory.append(dict(animation_id='0x6110', resref=record['resref'],
                                  component_index=index, shard_index=index,
                                  resource_ordinal=ordinal))
        source.emit('catalog-shard', completed=index+1, total=len(partitions), bytes=info['registry_bytes'])
    catalog = pack / xn.XN_REGISTRY_CATALOG_FILENAME
    info = xn.write_registry_catalog_index(
        catalog, 4,
        [dict(animation_id='0x6110', owner=xn.CATALOG_OWNER_CHARACTER,
              component_indices=list(range(len(components))))],
        components, shards, directory, logical,
        dict(frame_storage='XPRESS_HUFF-or-raw-per-frame-v1'))
    verified = xn.inspect_registry_catalog(catalog)
    if verified['scale'] != 4 or verified['total_frames'] != manifest['coverage']['frames']:
        raise RuntimeError('Catalog coverage differs')
    result = dict(schema='bg2-upscale-reboutcx-x4-visual-catalog-v2',
                  status='built-pending-ingame-qa', target_scale=4,
                  animation_id='0x6110', registry_layout='catalog',
                  source_manifest=source.relative(source.OUTPUT / 'manifest.json'),
                  source_manifest_sha256=source.sha256_file(source.OUTPUT / 'manifest.json'),
                  method=manifest['method'], coverage=manifest['coverage'],
                  registry_catalog='iee-assets/creature-sprites/'+catalog.name,
                  registry_catalog_sha256=info['sha256'],
                  shards=[dict(path=s['registry'], sha256=s['sha256']) for s in info['shards']],
                  totals=dict(registry_bytes=info['total_registry_bytes']),
                  catalog=info)
    xn.write_json(output / 'manifest.json', result)
    source.emit('catalog-verified', scale=4, frames=info['total_frames'],
                shards=info['shard_count'], bytes=info['total_registry_bytes'])


if __name__ == '__main__':
    main()
