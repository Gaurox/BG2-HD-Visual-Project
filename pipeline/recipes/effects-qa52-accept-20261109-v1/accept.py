"""Seal exact tested installed bindings, then accept 52 images; never promote PRO QA."""
import copy, csv, json, os, shutil, struct, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import effect_workflow as w
import effect_authority as authority
from compose_effect_runtime_packs import REGISTRY_HEADER, REGISTRY_MAGIC, validate_pack
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource

OUT = ROOT/'effects/batches/qa52-accepted-20261109-v1'
LAUNCH = ROOT/'effects/installations/qa52-launchers-20261109-v1'
PROOF = ROOT/'projectiles/analysis/components-qa52-20261109-v1'
DECISION = "oui c'est ok. tu peux valider tout le lot. travaille proprement pour les valider au bon endroit entre effets, projectiles, ou les 2"
DATE = '2026-11-09'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
rel = lambda p: p.relative_to(ROOT).as_posix()
ev = lambda p: w.file_evidence(ROOT, p)

def save(p, value):
    assert not p.exists(), p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(w.json_bytes(value))

def records(raw):
    """Extract exact v3 records, retaining padded clocks and alternate profiles."""
    magic, version, scale, count, reserved = REGISTRY_HEADER.unpack_from(raw)
    assert (magic, version, scale, reserved) == (REGISTRY_MAGIC, 3, 4, 0)
    result = {}; off = REGISTRY_HEADER.size
    for _ in range(count):
        start = off; name = raw[off:off+8].rstrip(b'\0').decode(); off += 8
        frames, cycles = struct.unpack_from('<II', raw, off); off += 8+8*frames
        for _ in range(cycles):
            n, = struct.unpack_from('<I', raw, off); off += 4+4*n
        phases, = struct.unpack_from('<I', raw, off+16); off += 20+4*cycles*phases
        alternates, = struct.unpack_from('<I', raw, off); off += 4
        for _ in range(alternates):
            _, n = struct.unpack_from('<II', raw, off); off += 8+4*n
        result[name] = raw[start:off]
    assert off == len(raw)
    return result

def descriptor(n, stage, run, recipe, inputs, output, parent=None):
    return {'$schema':'docs/workspace-run.schema.json','schema_version':1,
        'run_id':run,'domain':'effects','asset_ids':[f'effects:bam:{n}'],
        'pipeline':{'id':w.STAGES[stage], 'version':'exact-installed-reuse.v1',
                    'recipe_path':rel(recipe),'recipe_sha256':w.sha256_file(recipe)},
        'inputs':inputs, 'outputs':[dict(ev(output),role='spatial-manifest' if stage=='spatial' else 'reused-runtime-binding')],
        'provenance':{'created_at_utc':w.utc_now(),'generator':rel(Path(__file__)), 'parents':[parent] if parent else []},
        'result':{'status':'completed','sealed':True,'completed_at_utc':w.utc_now(),
                  'notes':'Exact installed output reused; no inference, resampling or new interpolation.'}}

def main():
    resume='--resume' in sys.argv
    assert not (OUT/'acceptance.json').exists(), 'Acceptance is immutable'
    assert resume or not OUT.exists()
    OUT.mkdir(parents=True,exist_ok=resume)
    proc = ROOT/'effects/index/processing.csv'
    if not resume: (OUT/'processing-before.csv').write_bytes(proc.read_bytes())
    before = {r['asset_key']:r for r in w.read_csv(OUT/'processing-before.csv',w.PROCESSING_FIELDS)}
    pp = ROOT/'projectiles/index/work-tracking.json'; pb = load(pp)
    if not resume: save(OUT/'projectile-tracking-before.json',pb)
    else: assert pb==load(OUT/'projectile-tracking-before.json')
    game = get_path('bg2ee_game_root'); mp = game/'iee-assets/effects/manifest.json'
    installed = load(mp); installed_sha = w.sha256_file(mp)
    registry_path = game/'iee-assets/effects/EffectAnimations-X4.registry'
    registry = registry_path.read_bytes(); assert w.sha256_file(registry_path)==installed['registry_sha256']
    recs = records(registry); resources = {r['resref']:r for r in installed['resources']}
    frames = defaultdict(list)
    for f in installed['frames']: frames[f['resref']].append(f)
    tests = load(LAUNCH/'launchers.json'); assert len(tests)==52
    bifs, entries = load_key(); snapshots = []; packs = {}
    # Prepare every exact artifact before changing any QA authority.
    for test in tests:
        n = test['resref']; old = before['effects:bam:'+n]
        assert old['qa_state']=='not-assessed',n
        if resume:
            snapshot=load(OUT/'bindings'/f'{n}.json')
            assert snapshot['installed_manifest_sha256']==installed_sha
            pack=ROOT/f'effects/ressources/{n}/packs/{n.lower()}-installed-accepted-20261109-v1'
            validate_pack(pack);w.pack_binding(ROOT,n,w.load_asset(ROOT,n)[1],pack/'manifest.json')
            packs[n]=(pack,n.lower()+'-installed-reuse-spatial-20261109-v1',n.lower()+'-installed-reuse30-20261109-v1')
            snapshots.append(snapshot)
            continue
        vvc = game/'override'/(test['vvc']+'.vvc')
        raw = vvc.read_bytes() if vvc.exists() else resolve_resource(bifs,next(l for a,t,l in entries if a.upper()==test['vvc'] and t==0x3fb))[0]
        ref = raw[8:16].rstrip(b'\0').decode(); resource = copy.deepcopy(resources[ref])
        assert len(frames[ref])==resource['frame_count']
        vpath = OUT/'controllers'/(test['vvc']+'.vvc'); vpath.parent.mkdir(exist_ok=True);vpath.write_bytes(raw)
        snapshot = dict(resref=n,test=test,runtime_ref=ref,controller=ev(vpath),resource=resource,
                        frames=frames[ref],installed_manifest_sha256=installed_sha,
                        prior_production={k:old[k] for k in ['spatial_run','interpolation_run','installation_receipt']},
                        visual_scope='Primary VVC tested; all palette/owner/profile variants not inferred')
        if n in ('SANCTRY','SPSHIELD'):
            snapshot['real_spell_qa']={'spell':'SPPR109' if n=='SANCTRY' else 'SPWI311',
                'result':'Protection/character transparency accepted by user after real spell test'}
        bind = OUT/'bindings'/f'{n}.json'; save(bind,snapshot); snapshots.append(snapshot)
        spatial = n.lower()+'-installed-reuse-spatial-20261109-v1'
        temporal = n.lower()+'-installed-reuse30-20261109-v1'
        sr = ROOT/f'effects/ressources/{n}/runs/{spatial}'; tr = sr.parent/temporal
        recipe = {'schema':'bg2-effects-installed-reuse-v1','new_inference':0,'new_interpolation':0,
                  'installed_binding':ev(bind),'primary_test':test,'prior_production':snapshot['prior_production']}
        for runpath in (sr,tr): save(runpath/'recipe.json',recipe)
        source = ROOT/f'effects/ressources/{n}/source.bam'
        save(sr/'run.json',descriptor(n,'spatial',spatial,sr/'recipe.json',
            [dict(ev(source),role='source-bam')],bind))
        save(tr/'run.json',descriptor(n,'interpolation',temporal,tr/'recipe.json',
            [dict(ev(bind),role='parent-spatial-output')],bind,spatial))
        pack = ROOT/f'effects/ressources/{n}/packs/{n.lower()}-installed-accepted-20261109-v1'; pack.mkdir(parents=True)
        ff = []
        for f in sorted(frames[ref],key=lambda x:x['resource_frame']):
            src = ROOT/f['source'] if f.get('source') else game/'iee-assets/effects'/f['asset']
            if not src.exists(): src=game/'iee-assets/effects'/f['asset']
            assert w.sha256_file(src)==f['sha256'],src
            # Verify actual installed backing as well as the retained production source.
            assert w.sha256_file(game/'iee-assets/effects'/f['asset'])==f['sha256']
            dest=pack/f'EFX4-{n}-frame{f["resource_frame"]:03d}.rgba'
            try: os.link(src,dest)
            except OSError: shutil.copy2(src,dest)
            frame=copy.deepcopy(f);frame.update(frame=len(ff),asset=dest.name,resref=n);ff.append(frame)
        record=n.encode().ljust(8,b'\0')+recs[ref][8:]
        reg=REGISTRY_HEADER.pack(REGISTRY_MAGIC,3,4,1,0)+record
        (pack/'EffectAnimations-X4.registry').write_bytes(reg)
        resource['resref']=n
        resource['source']={'source_bam_sha256':w.sha256_file(source),'spatial_run':spatial,
            'spatial_run_descriptor_sha256':w.sha256_file(sr/'run.json'),'spatial_manifest_sha256':w.sha256_file(bind),
            'interpolation_run':temporal,'interpolation_run_descriptor_sha256':w.sha256_file(tr/'run.json'),
            'installed_binding':ev(bind),'original_runtime_ref':ref,'no_new_inference':True}
        save(pack/'manifest.json',{'schema':'bg2-upscale-effect-animation-runtime-pack-v1','status':'completed',
            'scale':4,'registry':'EffectAnimations-X4.registry','registry_magic':'IEEEFX4','registry_version':3,
            'registry_bytes':len(reg),'registry_sha256':w.sha256_file(pack/'EffectAnimations-X4.registry'),
            'resource_count':1,'resources':[resource],'frame_count':len(ff),'frames':ff})
        validate_pack(pack); w.pack_binding(ROOT,n,w.load_asset(ROOT,n)[1],pack/'manifest.json')
        packs[n]=(pack,spatial,temporal)
        print('sealed',n,ref,flush=True)
    accepted=[]
    for n,(pack,spatial,temporal) in packs.items():
        w.register_run(ROOT,n,'spatial',spatial,write=True)
        w.register_run(ROOT,n,'interpolation',temporal,write=True)
        why=DECISION+' Validation des 52 visuels installés via les CLUA listées ; transparence des vrais sorts SPPR109/SPWI311 confirmée pour SANCTRY/SPSHIELD. Aucun test de tous les owners/palettes/profils ni du déplacement des PRO déduit.'
        w.accept_asset(ROOT,n,pack_path=rel(pack),decision=why,decision_date=DATE,write=True)
        sel=ROOT/f'effects/index/selections/{n}.json'; s=load(sel)
        accepted.append({'resref':n,'selection':ev(sel),'qa':ev(ROOT/s['qa_evidence']['path'])})
    links=defaultdict(list)
    for c in csv.DictReader((ROOT/'effects/index/consumers.csv').open(encoding='utf-8-sig')):
        n=c['asset_key'].rsplit(':',1)[-1]
        if n in packs and c['consumer_key'].startswith('projectile:'):
            links[c['consumer_key'].split(':',1)[1]].append({'resref':n,'relation':c['relation'],'via':c['via'],
                'visual_qa':next(a['qa'] for a in accepted if a['resref']==n),
                'coverage':'asset-primary-VVC; native PRO owner/palette/motion not exercised'})
    save(PROOF/'components.json',{'decision_date':DATE,'effects_acceptance':rel(OUT/'acceptance.json'),
        'projectiles':dict(links),'projectile_qa_states_changed':False})
    current=copy.deepcopy(pb)
    for pro,components in links.items():
        node=current['projectiles'].setdefault(pro,{})
        node.setdefault('component_visual_qa',{})['qa52-20261109-v1']={
            'state':'accepted-assets-only','evidence':[rel(PROOF/'components.json')],
            'assets':sorted({c['resref'] for c in components}),'reviewed_on':DATE,
            'limits':'QA des images via VVC ; QA native du PRO et déplacement inchangés.'}
    pp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    after={r['asset_key']:r for r in w.read_csv(proc,w.PROCESSING_FIELDS)}
    for key,old in before.items():
        new=after[key];n=key.rsplit(':',1)[-1]
        if n not in packs: assert new==old
        else:
            assert new['qa_state']=='passed' and new['selected_run']==packs[n][2]
            for k in ['installation_state','installation_receipt','release_state','release_candidate']: assert new[k]==old[k]
    stripped=copy.deepcopy(current)
    for pro in links:
        node=stripped['projectiles'][pro]; del node['component_visual_qa']['qa52-20261109-v1']
        if not node['component_visual_qa']: del node['component_visual_qa']
        if pro not in pb['projectiles']: del stripped['projectiles'][pro]
    assert stripped==pb
    assert w.sha256_file(mp)==installed_sha and w.sha256_file(registry_path)==installed['registry_sha256']
    linked_assets=sorted({c['resref'] for cs in links.values() for c in cs})
    save(OUT/'acceptance.json',{'schema':'bg2-effects-batch-user-acceptance-v1','status':'accepted',
        'decision_date':DATE,'user_decision':DECISION,'accepted_count':52,'accepted':accepted,
        'tests':ev(LAUNCH/'launchers.json'),'installed_manifest_sha256':installed_sha,
        'installed_registry_sha256':installed['registry_sha256'],'projectile_component_assets':linked_assets,
        'projectile_consumer_count':len(links),'projectile_evidence':ev(PROOF/'components.json'),
        'real_spell_tests':{'SANCTRY':'SPPR109','SPSHIELD':'SPWI311'},
        'limits':['Primary visual tests only; no all-owner/palette/profile coverage inferred.',
                  'PRO QA/integration/installation/release unchanged; motion remains distinct.'],
        'game_files_changed':False,'release_changed':False,'gpu_used':False})
    save(OUT/'verification.json',{'passed':True,'accepted_count':52,'exact_installed_bindings':52,
        'other_effect_rows_preserved':True,'projectile_qa_and_other_fields_preserved':True,
        'installation_release_preserved':True,'projectile_consumer_count':len(links),
        'projectile_component_asset_count':len(linked_assets)})
    note=f'52 images acceptées le {DATE} : 31 anciens effets, 18 réemplois, 3 effets 1WDC. {len(linked_assets)} images liées à {len(links)} PRO ; validation des composants seule. SANCTRY/SPPR109 et SPSHIELD/SPWI311 : transparence confirmée avec les vrais sorts. Packs mono-BAM figés sur les versions installées testées ; 0 inférence/interpolation nouvelle. Autres QA, installation et release préservées ; GPU en pause.'
    (OUT/'README.md').write_text('# QA des 52 anciens effets — acceptée\n\n- '+note+'\n- Autorités : `acceptance.json`, `verification.json`, `bindings/`, `effects/index/{qa-decisions,selections}/`. Les productions historiques restent intactes ; nouveaux runs de réemploi exact, pas de retour aux premiers packs du lot31.\n- Portée : tests VVC principaux ; aucune couverture individuelle des autres palettes/profils/owners PRO déduite.\n',encoding='utf-8')
    (PROOF/'README.md').write_text('# Composants effets des projectiles — QA52\n\n- '+note+'\n- `components.json` : liens directs depuis `effects/index/consumers.csv`. `index/work-tracking.json:component_visual_qa` relaie la QA image ; les états `.qa` des PRO restent inchangés. Ne pas confondre BURNHAND.BAM et BURNHAND.PRO.\n',encoding='utf-8')
    for p,link in [(ROOT/'effects/README.md','batches/qa52-accepted-20261109-v1/README.md'),
                   (ROOT/'effects/REPRISE.md','batches/qa52-accepted-20261109-v1/README.md'),
                   (ROOT/'projectiles/README.md','analysis/components-qa52-20261109-v1/README.md'),
                   (ROOT/'projectiles/SUIVI_MANUEL.md','analysis/components-qa52-20261109-v1/README.md')]:
        text=p.read_text(encoding='utf-8-sig');i=text.index('\n')+1
        p.write_text(text[:i]+f'\n**QA52 acceptée — {DATE}** : [décision et périmètre]({link}). '+note+'\n'+text[i:],encoding='utf-8')
    print('ACCEPTED52',len(linked_assets),'shared images;',len(links),'PRO links; PRO QA preserved.',flush=True)

if __name__=='__main__': main()
