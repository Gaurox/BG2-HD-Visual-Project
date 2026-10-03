from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=(HERE.parent/'q3m-ankheg-alpha-light-x2-20261004-v1/produce.py').read_text()
def sub(a,b):
    global s
    if s.count(a)!=1:raise ValueError(a[:100])
    s=s.replace(a,b)
sub('from sprite_alpha_coverage import coverage,apply', '''from sprite_sdf_registry import planes
import importlib.util
offline=ROOT/'docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1'
spec=importlib.util.spec_from_file_location('sdf_reference',offline/'sdf_trial.py');reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)''')
sub("previous=load(parent_run/'current-generation.json');production=load(parent_run/'production.json')", "original_run=parent_run\nparent_run=ROOT/'docs/measurements/q3m-ankheg-alpha-light-x2-20261004-v1'\nprevious=load(parent_run/'current-generation.json');production=load(original_run/'production.json')")
sub("work=ROOT/'sprite/.work/q3m-ankheg-alpha-light-x2-20261004-v1'", "work=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1'")
start=s.index('recipe=dict(');end=s.index('# K6 palettes',start)
s=s[:start]+'''recipe=dict(reference.RECIPE,installation='V9-adaptive-runtime',distance_quantization_x2=1/16,sdf_pad_x2=6)
recipe_bytes=json.dumps(reference.RECIPE,sort_keys=True).encode()+bytes.fromhex(file_sha(offline/'sdf_trial.py'))
'''+s[end:]
start=s.index('resources={};infos=[]');end=s.index('details=[]',start)
s=s[:start]+'''resources={};infos=[];mask_cache={};stats=dict(physical_frames=0,unique_masks=0,mask_cache_hits=0,
    acquired_offline_masks_reused=0,new_neural_targets=0,new_Q3m_encodings=0)
'''+s[end:]
start=s.index('        if key in mask_cache:');end=s.index('    materials=',start)
s=s[:start]+'''        if key in mask_cache:distance,report=mask_cache[key];stats['mask_cache_hits']+=1
        else:
            acquired=ROOT/'sprite/.work/q3m-ankheg-sdf-offline-x2-20261004-v1'/ (key+'.npz')
            if acquired.exists():
                distance=np.load(acquired)['SDF'];stats['acquired_offline_masks_reused']+=1
                report=dict(reused_offline_field=True)
            elif np.any(frame['I']>=2):distance,report=reference.reconstruct(frame['I'])
            else:distance=np.full((binary.shape[0]+12,binary.shape[1]+12),-4,np.float32);report=dict(empty_foreground=True)
            np.savez_compressed(cache/(key+'.npz'),SDF=distance)
            mask_cache[key]=(distance,report);stats['unique_masks']+=1
        frame['S'],frame['M']=planes(frame['I'],distance)
        frame['guide']=frame['I'].copy();frame['dep']=np.frombuffer(frame['dep'],np.uint8).copy()
        rows.append(dict(frame=ordinal,mask_key=key,**report))
        stats['physical_frames']+=1
'''+s[end:]
sub('profile,version=8)','profile,version=9)')
sub("np.array_equal(a['A'],b['A'])", "np.array_equal(a['S'],b['S']) and np.array_equal(a['M'],b['M'])")
sub("frames_changed=int(changed),", "sdf_bytes=int(new['sdf_bytes']),")
sub("V8_sha256=new['sha256']", "V9_sha256=new['sha256']")
sub("changed=changed,unique_masks", "unique_masks")
sub("stats['physical_frames']==516 and stats['frames_changed']>0", "stats['physical_frames']==516 and stats['acquired_offline_masks_reused']==12")
start=s.index('oracle=bytearray(old_oracle[:12])');end=s.index('components=[]',start)
s=s[:start]+'''(isolated/'witnesses.oracle').write_bytes(old_oracle)
# Independent Python oracle for the encoded upload plane and native bordered compositor.
sdf_oracle=bytearray(b'IEESDF1\\0')
for ref,prefix,geometry in chunks:
    resource=resources[ref]
    for frame in resource['frames']:
        for k,palette in enumerate(palette_map[ref]):
            rgba=resource['profile'].decode(frame['I'],frame['F'],palette)
            require(np.all(rgba[frame['I']>=2,3]==255),'foreground alpha contract')
            shadow=rgba[frame['I']==1]
            require(np.all(shadow[:,:3]==0) and np.all(shadow[:,3]==127),'shadow contract differs')
            m=frame['M'];valid=m!=0xffffffff
            encoded=np.zeros((*m.shape,4),np.uint8)
            encoded[valid,:3]=rgba.reshape(-1,4)[m[valid],:3]
            encoded[...,3]=frame['S']
            encoded[6:-6,6:-6,3]|=(frame['I']==1).astype(np.uint8)*128
            sdf_oracle.extend(hashlib.sha256(encoded.tobytes()).digest())
            if k==0:composite_sha=hashlib.sha256(encoded[4:-4,4:-4].tobytes()).digest()
        sdf_oracle.extend(composite_sha)
(isolated/'sdf.oracle').write_bytes(sdf_oracle)
'''+s[end:]
sub('dict(shard_registry_versions=[8])','dict(shard_registry_versions=[9])')
sub('dict(shard_registry_versions=[6,7,8])','dict(shard_registry_versions=[6,7,9])')
sub("path=game/entry['target'];baseline['unchanged_assets'].append", "path=game/entry['target']\n    if path.name in ('fpDraw.glsl','fpSprite.glsl','fpSELECT.glsl'):continue\n    baseline['unchanged_assets'].append")
sub("write_json(HERE/'baseline.json',baseline)", "baseline['replaced_shaders']=[dict(relative_path='override/'+n,sha256=file_sha(game/'override'/n)) for n in ('fpDraw.glsl','fpSprite.glsl','fpSELECT.glsl')]\nwrite_json(HERE/'baseline.json',baseline)")
sub('positive_alpha_support_byte_identical_K6=True,','reference_offline_masks_reused=12,')
sub("original_generation=identity(parent_run/'current-generation.json'),original_production=identity(parent_run/'production.json')", "original_generation=identity(original_run/'current-generation.json'),original_production=identity(original_run/'production.json')")
sub('registry_version=8','registry_version=9')
s=s[:s.index('# Four body poses')]+"print(json.dumps(dict(stats=stats,catalog=catalog['sha256'],complete=True)),flush=True)\n"
(HERE/'produce.py').write_text(s,encoding='utf-8',newline='\n')
