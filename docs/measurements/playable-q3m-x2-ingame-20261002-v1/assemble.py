"""CPU-only parallel fan-out of the existing shared Q3m x2 results.

Resumes unsealed work output; sealed packs and source/cache bytes are immutable.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from palette_work_plan import WorkPlan, ResultCache, write_json
import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_p3_catalog import source_contract

PLAN = CACHE = OUTPUT = None


def init(output):
    global PLAN, CACHE, OUTPUT
    PLAN = WorkPlan()
    CACHE = ResultCache(PLAN, 2)
    OUTPUT = Path(output)


def check_source(info, resource):
    assert info['version'] == 6 and info['scale'] == 2
    assert info['resources'] == [resource['resref']]
    assert info['frame_count'] == resource['frame_count']
    header, geometries, cycles = source_contract(info['resource_records'][0])
    assert header[8:40].hex() == resource['canonical_sha256'].lower()
    expected = [tuple(row) for row in PLAN.db.execute(
        'SELECT i.width,i.height,f.center_x,f.center_y,i.transparent_index FROM frames f '
        'JOIN work_items w USING(work_id) JOIN inputs i USING(input_id) '
        'WHERE f.resource_id=? ORDER BY f.frame_index', (resource['resource_id'],))]
    assert geometries == expected, resource['resref']
    expected_cycles = bytearray()
    for row in PLAN.db.execute('SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index',
                              (resource['resource_id'],)):
        values = struct.unpack(f"<{row['slot_count']}H", row['frame_indices_le_u16'])
        expected_cycles.extend(struct.pack('<I', len(values)))
        expected_cycles.extend(struct.pack(f'<{len(values)}I', *values))
    assert cycles == expected_cycles, resource['resref']


def resource_pack(item):
    resource, existing = item
    if existing:
        leaf = Path(existing)
    else:
        temporary = OUTPUT / f"parallel-{resource['resource_id']:05d}.registry"
        info = v6.write(temporary, 2, [PLAN.materialize(resource, CACHE)])
        leaf = OUTPUT / registry.catalog_shard_filename(info['sha256'])
        assert not leaf.exists()
        temporary.rename(leaf)
    info = v6.inspect(leaf, include_resource_records=True)
    assert leaf.name == registry.catalog_shard_filename(info['sha256'])
    check_source(info, resource)
    logical = registry.catalog_source_component_sha256(2, info.pop('resource_records'))
    return resource['resource_id'], info, logical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT)
    assert not (output / 'pack.json').exists() and not (output / registry.XN_REGISTRY_CATALOG_FILENAME).exists()
    output.mkdir(parents=True, exist_ok=True)
    plan = WorkPlan().validate_sources()
    cache = ResultCache(plan, 2)
    resources = [dict(r) for r in plan.resources()]
    # Completed leaves from the interrupted sequential run have one resource.
    existing = {}
    for leaf in output.glob('CreatureSprites-XN-*.registry'):
        with leaf.open('rb') as stream:
            header = stream.read(80)
        assert struct.unpack_from('<I', header, 16)[0] == 1
        ref = header[32:40].split(b'\0', 1)[0].decode('ascii')
        assert ref not in existing
        existing[ref] = str(leaf)
    assert set(existing) <= {r['resref'] for r in resources}
    print(f"resume={len(existing)} total={len(resources)} workers={args.workers}", flush=True)
    completed = {}
    with cache.exclusive(), ProcessPoolExecutor(max_workers=args.workers, initializer=init,
                                               initargs=(str(output),)) as pool:
        futures = [pool.submit(resource_pack, (r, existing.get(r['resref']))) for r in resources]
        for future in as_completed(futures):
            rid, info, logical = future.result()
            completed[rid] = (info, logical)
            if len(completed) % 50 == 0 or len(completed) == len(resources):
                print(f"assembled {len(completed)}/{len(resources)}", flush=True)
    infos, components, logical, directory, mapping = [], [], [], [], {}
    storage = dict(shard_registry_version=6, stored_index_bytes=0, stored_fraction_bytes=0,
                   fraction_bytes=0, compressed_frame_count=0, raw_frame_count=0,
                   compressed_fraction_count=0, fractional_frame_count=0)
    for n, resource in enumerate(resources):
        info, digest = completed[resource['resource_id']]
        infos.append(info)
        leaf = output / registry.catalog_shard_filename(info['sha256'])
        components.append(dict(index=n, digest=registry.catalog_component_digest(2,
            [registry.catalog_shard_entry_bytes(info, leaf)]), shard_start=n, shard_count=1,
            **{key: info[key] for key in ('resource_count', 'frame_count', 'index_bytes', 'registry_bytes')}))
        logical.append(digest)
        mapping[resource['resource_id']] = n
        for key in storage:
            if key != 'shard_registry_version':
                storage[key] += info[key]
    animations = []
    chosen, _ = plan.selection()
    for animation in chosen:
        membership = []
        for resource in plan.resources([animation]):
            n = mapping[resource['resource_id']]
            membership.append(n)
            directory.append(dict(animation_id=animation, resref=resource['resref'],
                                  component_index=n, shard_index=n, resource_ordinal=0))
        animations.append(dict(animation_id=animation, owner=1, component_indices=membership))
    result = registry.write_registry_catalog_index(output / registry.XN_REGISTRY_CATALOG_FILENAME,
        2, animations, components, infos, directory, logical, storage)
    sealed = registry.read_sealed_catalog_index(output / registry.XN_REGISTRY_CATALOG_FILENAME, result['sha256'])
    assert sealed['directory'] == sorted(directory, key=lambda r: (r['animation_id'], r['resref']))
    write_json(output / 'pack.json', dict(schema='bg2-playable-q3m-experimental-pack-v1',
        status='native-source-contract-verified-not-ingame-qa', source_plan_sha256=plan.descriptor['sha256'],
        result_namespace=cache.namespace, scale=2, animations=chosen, resources=len(infos), catalog=result,
        verification=dict(missing_animation_ids=[], missing_resources=[], frame_geometry_source_cycles_identical=True,
                          frames=sealed['total_frames'], gpu_inference=False)))
    plan.close()
    print(json.dumps(dict(status='complete', animations=len(chosen), resources=len(infos),
                         frames=sealed['total_frames'], registry_bytes=sealed['total_registry_bytes'])), flush=True)


if __name__ == '__main__':
    main()
