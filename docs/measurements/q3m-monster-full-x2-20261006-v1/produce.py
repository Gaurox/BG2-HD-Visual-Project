"""Complete approved Monster production; shared immutable hits, no installation."""
import json
import os
import shutil
import sys
import time
import hashlib
import runpy
import sqlite3
import struct
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = ROOT / 'sprite/.work' / HERE.name
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from q3m_family_witnesses import source_plan, produce, pack, exclusive, native_representatives, save
from q3m_multipart_seams import apply_context
from palette_work_plan import file_sha, write_json
from workspace_paths import get_path

def adopt_historical_guides(works, cache):
    from palette_monster_work_plan import WorkPlan
    from analyze_playable_frame_dedup import identities
    by_source = {w['source_key']: w for w in works.values()}
    namespace = hashlib.sha256((file_sha(get_path('mmpx_scalepix',required=True)) +
                file_sha(ROOT/'pipeline/scripts/xbr2x_batch.js') +
                file_sha(ROOT/'pipeline/scripts/run_creature_sprite_x2.py')).encode()).hexdigest()
    directory = cache / 'guides' / namespace
    plan = WorkPlan()
    added, existing, visited = 0, 0, set()
    try:
        for row in plan.work_rows(plan.resources()):
            old = plan.work(row)
            source = identities(old.frame.indices, old.frame.palette, 0)[1].hex()
            if source not in by_source or source in visited:
                continue
            visited.add(source)
            frame = by_source[source]['frame']
            assert np.array_equal(frame.indices,old.frame.indices)
            assert np.array_equal(frame.palette[frame.indices],old.frame.palette[old.frame.indices])
            guide = plan.guide(old)
            path = directory / (source + '.npz')
            if path.exists():
                with np.load(path,allow_pickle=False) as data:
                    assert np.array_equal(data['guide'],guide), 'historical/current xBR guide differs'
                existing += 1
            else:
                save(path,guide=guide)
                added += 1
    finally:
        plan.close()
    report = dict(compatible_source_work=len(visited), acquired_guides_adopted=added,
                  existing_guide_bytes_equal=existing, new_xBR_work=0, source_plan_sha256=plan.descriptor['sha256'])
    write_json(HERE/'guide-adoption.json',report)
    print(json.dumps(dict(stage='historical-guide-adoption',**report)),flush=True)
    return report

def adopt_all_stock_guides(works,cache):
    """Exact V3 source/kernel/geometry proof; historical registries stay read-only."""
    by_source={w['source_key']:w for w in works.values()}
    namespace=hashlib.sha256((file_sha(get_path('mmpx_scalepix',required=True))+
              file_sha(ROOT/'pipeline/scripts/xbr2x_batch.js')+
              file_sha(ROOT/'pipeline/scripts/run_creature_sprite_x2.py')).encode()).hexdigest()
    directory=cache/'guides'/namespace
    ns=runpy.run_path(str(HERE.parent/'q3m-monster-work-plan-x2-20261003-v1/analyze.py'))
    descriptor=json.loads((ROOT/'sprite/index/q3m-source-work-plan.json').read_text())
    db=sqlite3.connect((ROOT/descriptor['path']).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    kernel={'xbr2x_batch.js':file_sha(ROOT/'pipeline/scripts/xbr2x_batch.js'),
            'config://mmpx_scalepix':file_sha(get_path('mmpx_scalepix',required=True))}
    visited=set();evidence=[];added=existing=unsupported=0
    try:
        for build in sorted((ROOT/'sprite/families/monsters').glob('*/*/runs/*/build/build-manifest.json')):
            m=json.loads(build.read_text(encoding='utf-8-sig'))
            if m.get('registry_version')!=3 or m.get('registry_layout')!='monolith':
                unsupported+=1;continue
            mp=ROOT/m['source_manifest'];source=json.loads(mp.read_text(encoding='utf-8-sig'))
            expected={b['name']:b for b in source['bams']}
            _,registry,raw,locations=ns['old_guide_locations'](build,expected,kernel,{m['source_manifest']:file_sha(mp)})
            record=dict(manifest=build.relative_to(ROOT).as_posix(),registry_sha256=m['registry_sha256'],adopted=0,existing_equal=0)
            for ref in expected:
                native=db.execute('SELECT * FROM resources WHERE resref=?',(ref,)).fetchone()
                if native is None:continue
                assert native['canonical_sha256'].lower()==expected[ref]['canonical_bam_sha256'].lower()
                for f in db.execute('SELECT f.*,lower(hex(w.work_key)) AS source_key,i.width,i.height FROM frames f JOIN source_work w USING(work_id) JOIN inputs i USING(input_id) WHERE f.resource_id=? ORDER BY frame_index',(native['resource_id'],)):
                    key=f['source_key']
                    if key not in by_source or key in visited:continue
                    visited.add(key);work=by_source[key];frame=work['frame']
                    offset,count,geometry=locations[(ref,f['frame_index'])]
                    assert geometry==(f['width'],f['height'],f['center_x'],f['center_y'],0)
                    guide=np.frombuffer(raw,np.uint8,count,offset).reshape(frame.height*2,frame.width*2).copy()
                    assert np.isin(guide,np.unique(frame.indices)).all()
                    path=directory/(key+'.npz')
                    if path.exists():
                        with np.load(path,allow_pickle=False) as data:assert np.array_equal(data['guide'],guide),'historical/current guide mismatch'
                        existing+=1;record['existing_equal']+=1
                    else:
                        save(path,guide=guide);added+=1;record['adopted']+=1
            evidence.append(record)
            print(json.dumps(dict(stage='stock-guide-adoption',animation_id=m['animation_id'],adopted=added,existing_equal=existing)),flush=True)
    finally:db.close()
    report=dict(compatible_source_work=len(visited),acquired_guides_adopted=added,existing_guide_bytes_equal=existing,
                skipped_unsupported_registries=unsupported,new_xBR_work=0,evidence=evidence)
    write_json(HERE/'stock-guide-adoption.json',report)
    return report

def main():
    started = time.time()
    cache = ROOT / 'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
    resume_base = json.loads((HERE/'base-production.json').read_text()) if (HERE/'base-production.json').exists() else None
    output = WORK / ('isolated-v2' if resume_base else 'isolated')
    recipe_path = HERE / ('recipe-packing-v2.json' if resume_base else 'recipe.json')
    assert not output.exists() and not (HERE / 'production.json').exists()
    resources, works, plan = source_plan(HERE / 'selection.json', 'monster')
    if resume_base: assert plan == resume_base['plan'], 'resume source plan differs'
    assert len(plan['witnesses']) == 77 and len({r['resref'] for r in resources}) == 850
    assert plan['unique_original_BAM_source_work'] == 86963 and len(plan['replacement_palettes']) == 15
    for work in works.values():
        native_representatives(work['frame'].indices)
    write_json(HERE / 'plan.json', plan)
    print(json.dumps(dict(stage='plan', **{k: plan[k] for k in ('resources','physical_frames','unique_source_work','unique_encoded_work')})), flush=True)
    provenance = WORK / 'provenance'
    provenance.mkdir(parents=True, exist_ok=True)
    kernels = ['q3m_family_witnesses.py','palette_q3m_partners.py','palette_partner_registry.py','q3m_guarded_gpu_encode.py']
    sources = []
    for name in kernels:
        source = ROOT / 'pipeline/scripts' / name
        target = provenance / file_sha(source) / name
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            shutil.copyfile(source, target)
        assert file_sha(target) == file_sha(source)
        sources.append(dict(path=source.relative_to(ROOT).as_posix(), sha256=file_sha(source), bytes=source.stat().st_size,
                            snapshot=target.relative_to(ROOT).as_posix()))
    write_json(recipe_path, dict(method='Q3m-K6-four-partners-eight-levels', scale=2,
               SDF=False, sources=sources, source_scope='source-scope.json', selection_sha256=file_sha(HERE / 'selection.json'),
               short_palette='MFIEG3B: 252 native entries; zero native source tail retained; no bitmap pixel bytes interpreted as colours',
               large_frame='native dimensions preserved; u16 first representatives checked before conversion',
               acceleration=os.environ.get('Q3M_PALETTE_ENCODER','cpu'),
               encoding_recipe=dict(path=(HERE/'recipe.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'recipe.json')) if resume_base else None))
    with exclusive(cache):
        guide_adoption = json.loads((HERE/'guide-adoption.json').read_text()) if resume_base else adopt_historical_guides(works,cache)
        stock_guide_adoption = json.loads((HERE/'stock-guide-adoption.json').read_text()) if resume_base else adopt_all_stock_guides(works,cache)
        namespace = file_sha(ROOT / 'pipeline/scripts/palette_q3m_partners.py')
        old = {p: file_sha(p) for key in works if (p := cache / 'encoded' / namespace / (key + '.npz')).exists()}
        retained = dict(stage='cache-selection', compatible_encoded_present=len(old), total=len(works),
                        missing_encoded=len(works)-len(old), keys_sha256=__import__('hashlib').sha256(''.join(sorted(works)).encode()).hexdigest())
        write_json(HERE / ('cache-selection-resume.json' if resume_base else 'cache-selection.json'), retained)
        print(json.dumps(retained), flush=True)
        stats, directory = produce(resources, works, cache)
        assert all(file_sha(p) == digest for p, digest in old.items()), 'acquired hit modified'
        resume_stats = stats if resume_base else None
        if resume_base:
            assert stats == dict(encoded_cache_hits=len(works)), 'packing resume attempted recomputation'
            write_json(HERE/'packing-resume.json',dict(stats=stats,acquired_encoded_sha256_unchanged=len(old),new_inference=0,new_encoding=0))
            stats = resume_base['stats']
        else:
            write_json(HERE / 'base-production.json', dict(plan=plan, stats=stats, encoder_namespace=directory.name,
                       acquired_encoded_sha256_unchanged=len(old), encoded_directory=directory.relative_to(ROOT).as_posix()))
        contextual = apply_context(resources, works, HERE / 'selection.json', cache, 'run')
        assert contextual['contexts'] == 0, 'Monster is not a native multipart family'
        print(json.dumps(dict(stage='packing', resource_bindings=len(resources), bound_frames=plan['physical_frames'])), flush=True)
        packed = pack(resources, works, output)
        partial_equal = []
        if resume_base:
            for path in sorted((WORK/'isolated').glob('*.registry')):
                replacement = output/path.name
                assert replacement.exists() and file_sha(path)==file_sha(replacement),'partial pack bytes differ'
                partial_equal.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path)))
    from q3m_guarded_gpu_encode import statistics
    write_json(HERE / 'production.json', dict(plan=plan, stats=stats, acquired_encoded_sha256_unchanged=resume_base['acquired_encoded_sha256_unchanged'] if resume_base else len(old),
               historical_guide_adoption=guide_adoption,
               stock_guide_adoption=stock_guide_adoption,
               encoder_namespace=directory.name, encoded_directory=directory.relative_to(ROOT).as_posix(),
               pack=packed, pack_directory=output.relative_to(ROOT).as_posix(), multipart_context=contextual,
               palette_acceleration=dict(mode=os.environ.get('Q3M_PALETTE_ENCODER','cpu'), stats=None if resume_base else statistics(),
                     note='encoding completed before pack-only restart; detailed in-memory acceleration counters unavailable' if resume_base else None),
               packing_resume=resume_stats,partial_pack_bytes_equal=partial_equal,
               seconds=time.time()-started, SDF=False, installation=False, ingame_QA=False, release=False))
    write_json(HERE / 'current-generation.json', dict(schema='bg2-monster-Q3m-V7-current-v1',
               role='production-not-QA-installation-or-release', family='monster', models=62,
               animation_ids=[w['animation_id'] for w in plan['witnesses']], source_absent_animation_ids=plan['source_absent_animation_ids'],
               unique_native_BAM=850, original_native_frames=409599, resources=packed['resources'], frames=packed['frames'],
               logical_resource_bindings=packed['logical_resource_bindings'], scale=2, registry_version=7,
               colour='K6-four-partners-eight-levels', SDF=False, generation_dir=output.relative_to(ROOT).as_posix(),
               catalog=dict(path=(output/'CreatureSprites-XN.catalog').relative_to(ROOT).as_posix(),sha256=packed['catalog_sha256']),
               production=dict(path=(HERE/'production.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'production.json')),
               recipe=dict(path=recipe_path.relative_to(ROOT).as_posix(),sha256=file_sha(recipe_path)),
               installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='complete',resources=packed['resources'],frames=packed['frames'],stats=stats)),flush=True)

if __name__ == '__main__':
    main()
