"""Complete native Icewind production; immutable history, isolated output."""
import collections,csv,hashlib,json,os,shutil,sqlite3,struct,sys,time,zlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive,save,native_representatives
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from q3m_multipart_seams import context_plan
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def guide_locations(raw,expected):
    magic,version,scale,count,aid=struct.unpack_from('<8sIIII',raw)
    assert magic==b'IEECSXN\0' and(version,scale)==(3,2)
    off=24;locations={}
    for _ in range(count):
        ref=raw[off:off+8].split(b'\0')[0].decode('ascii');sha=raw[off+8:off+40].hex()
        nf,nc=struct.unpack_from('<II',raw,off+40);e=expected[ref]
        assert sha==e['source_sha256'].lower() and(nf,nc)==(e['frame_count'],e['cycle_count'])
        off+=48
        for fi in range(nf):
            w,h,cx,cy,tr,stored=struct.unpack_from('<HHhhB3xI',raw,off)
            assert raw[off+9]==0 and stored==w*h*4;off+=528
            assert off+stored<=len(raw);locations[(ref,fi)]=(off,stored,(w,h,cx,cy,tr));off+=stored
        for _ in range(nc):n=struct.unpack_from('<I',raw,off)[0];off+=4+n*4
    assert off==len(raw)
    return locations

def adopt_guides(works,cache):
    ns=hashlib.sha256((file_sha(get_path('mmpx_scalepix',required=True))+
        file_sha(ROOT/'pipeline/scripts/xbr2x_batch.js')+file_sha(ROOT/'pipeline/scripts/run_creature_sprite_x2.py')).encode()).hexdigest()
    destination=cache/'guides'/ns;wanted={w['source_key']:w for w in works.values()}
    pointer=load(ROOT/'sprite/index/q3m-source-work-plan.json')
    db=sqlite3.connect((ROOT/pointer['path']).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    refs={w['frame'].resref for w in works.values()};visited=set();added=equal=0;evidence=[]
    try:
        for bp in sorted((ROOT/'sprite/families/monster-icewind').glob('*/*/runs/*/build/build-manifest.json')):
            m=load(bp)
            if m.get('registry_version')!=3 or m.get('registry_layout') not in ('monolith','set'):continue
            src=ROOT/m['source_manifest'];source=load(src);expected={b['name']:b for b in source['bams']}
            if not set(expected)&refs:continue
            assert m['method']==dict(algorithm='XBR/xbr2X',scale=2,passes=1,antialias=False,xbr_blend=False)
            assert file_sha(src)==m['source_manifest_sha256'].lower()
            assert file_sha(ROOT/'pipeline/scripts/xbr2x_batch.js')==m['xbr_adapter_sha256'].lower()
            assert file_sha(get_path('mmpx_scalepix',required=True))==m['scalepix_sha256'].lower()
            if m['registry_layout']=='monolith':shards=[dict(registry=m['registry'],sha256=m['registry_sha256'],registry_bytes=m['registry_bytes'])]
            else:
                assert file_sha(bp.parent/m['registry_set'])==m['registry_set_sha256'].lower();shards=m['shards']
            record=dict(manifest=bp.relative_to(ROOT).as_posix(),layout=m['registry_layout'],adopted=0,existing_equal=0)
            for shard in shards:
                raw=(bp.parent/shard['registry']).read_bytes()
                assert len(raw)==shard['registry_bytes'] and hashlib.sha256(raw).hexdigest()==shard['sha256'].lower()
                if 'crc32' in shard:assert zlib.crc32(raw)==shard['crc32']
                locations=guide_locations(raw,expected)
                for ref in sorted({ref for ref,_ in locations}&refs):
                    nr=db.execute('SELECT * FROM resources WHERE resref=?',(ref,)).fetchone()
                    assert nr['canonical_sha256'].lower()==expected[ref]['canonical_bam_sha256'].lower()
                    for f in db.execute('SELECT f.*,lower(hex(w.work_key)) AS source_key,i.width,i.height FROM frames f JOIN source_work w USING(work_id) JOIN inputs i USING(input_id) WHERE resource_id=? ORDER BY frame_index',(nr['resource_id'],)):
                        key=f['source_key']
                        if key not in wanted or key in visited:continue
                        off,count,geometry=locations[(ref,f['frame_index'])]
                        assert geometry==(f['width'],f['height'],f['center_x'],f['center_y'],0)
                        frame=wanted[key]['frame'];guide=np.frombuffer(raw,np.uint8,count=count,offset=off).reshape(f['height']*2,f['width']*2)
                        assert np.isin(guide,np.unique(frame.indices)).all()
                        path=destination/(key+'.npz')
                        if path.exists():
                            with np.load(path,allow_pickle=False) as d:assert np.array_equal(d['guide'],guide)
                            equal+=1;record['existing_equal']+=1
                        else:save(path,guide=guide);added+=1;record['adopted']+=1
                        visited.add(key)
            evidence.append(record)
            print(json.dumps(dict(stage='guide-adoption',animation=m['animation_id'],adopted=added,existing_equal=equal)),flush=True)
    finally:db.close()
    assert len(visited)==67143
    return dict(compatible_source_work=len(visited),adopted=added,existing_equal=equal,new_xBR_work=0,evidence=evidence)

def main():
    started=time.time();cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';output=WORK/'isolated'
    assert not (HERE/'production.json').exists() and not output.exists()
    resources,works,plan=source_plan(HERE/'selection.json','monster_icewind')
    assert len(resources)==1140 and plan['physical_frames']==76955 and len(works)==70871
    assert plan['unique_original_BAM_source_work']==67143 and len(plan['replacement_palettes'])==3
    assert not any(context_plan(resources,load(HERE/'selection.json')))
    for w in works.values():native_representatives(w['frame'].indices)
    if(HERE/'plan.json').exists():assert load(HERE/'plan.json')==plan
    else:write_json(HERE/'plan.json',plan)
    print(json.dumps(dict(stage='plan',resources=len(resources),frames=76955,encoded=len(works))),flush=True)
    snapshots=[]
    for name in ('q3m_family_witnesses.py','palette_q3m_partners.py','palette_partner_registry.py','q3m_guarded_gpu_encode.py'):
        src=ROOT/'pipeline/scripts'/name;dest=WORK/'provenance'/file_sha(src)/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copyfile(src,dest)
        assert file_sha(src)==file_sha(dest);snapshots.append(dict(path=src.relative_to(ROOT).as_posix(),sha256=file_sha(src),snapshot=dest.relative_to(ROOT).as_posix()))
    recipe=dict(method='Q3m-K6-four-partners-eight-levels',scale=2,registry_version=7,SDF=False,sources=snapshots,
        selection_sha256=file_sha(HERE/'selection.json'),native_naming='body constructor 0x30EA60; weapons 0x3253E0; eastern attack3 body uses A2E',
        palette_overrides=plan['replacement_palettes'],spatial_contexts=0,acceleration=os.environ.get('Q3M_PALETTE_ENCODER','cpu'))
    if(HERE/'recipe.json').exists():assert load(HERE/'recipe.json')==recipe
    else:write_json(HERE/'recipe.json',recipe)
    with exclusive(cache):
        adoption=load(HERE/'guide-adoption.json') if(HERE/'guide-adoption.json').exists() else adopt_guides(works,cache)
        if not(HERE/'guide-adoption.json').exists():write_json(HERE/'guide-adoption.json',adoption)
        ns=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py');directory=cache/'encoded'/ns
        initial=HERE/'cache-selection.json'
        if initial.exists():old=load(initial)['acquired_hashes']
        else:
            old={key:file_sha(directory/(key+'.npz')) for key in works if(directory/(key+'.npz')).exists()}
            assert len(old)==2632;write_json(initial,dict(total=len(works),encoded_hits=len(old),new_encoded=len(works)-len(old),acquired_hashes=old))
        stats,directory=produce(resources,works,cache)
        assert all(file_sha(directory/(key+'.npz'))==sha for key,sha in old.items())
        write_json(HERE/'base-production.json',dict(plan=plan,stats=stats,encoder_namespace=ns,encoded_directory=directory.relative_to(ROOT).as_posix(),acquired_encoded_sha256_unchanged=len(old)))
        print(json.dumps(dict(stage='packing',bindings=len(resources))),flush=True)
        packed=pack(resources,works,output)
    from q3m_guarded_gpu_encode import statistics
    assert(packed['resources'],packed['frames'],packed['logical_resource_bindings'])==(1115,75176,1140)
    write_json(HERE/'production.json',dict(plan=plan,stats=stats,pack=packed,pack_directory=output.relative_to(ROOT).as_posix(),
        encoded_directory=directory.relative_to(ROOT).as_posix(),encoder_namespace=ns,guide_adoption=adoption,
        acquired_encoded_sha256_unchanged=len(old),palette_acceleration=statistics(),spatial_contexts=0,seconds=time.time()-started,SDF=False,installation=False,ingame_QA=False,release=False))
    write_json(HERE/'current-generation.json',dict(schema='bg2-icewind-Q3m-V7-current-v1',role='production-not-QA-installation-or-release',family='monster_icewind',
        models=36,animation_ids=[w['animation_id'] for w in plan['witnesses']],source_absent_animation_ids=plan['source_absent_animation_ids'],
        native_source_absent_animation_ids=plan['native_source_absent_animation_ids'],unique_native_BAM=1051,original_native_frames=71072,
        resources=1115,frames=75176,logical_resource_bindings=1140,bound_frames=76955,scale=2,registry_version=7,colour='K6-four-partners-eight-levels',SDF=False,
        generation_dir=output.relative_to(ROOT).as_posix(),catalog=dict(path=(output/'CreatureSprites-XN.catalog').relative_to(ROOT).as_posix(),sha256=packed['catalog_sha256']),
        production=dict(path=(HERE/'production.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'production.json')),
        recipe=dict(path=(HERE/'recipe.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'recipe.json')),installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='complete',resources=1115,frames=75176,stats=stats)),flush=True)

if __name__=='__main__':main()
