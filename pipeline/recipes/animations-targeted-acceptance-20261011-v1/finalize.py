"""Seal explicit QA; keep FIRE_3's previous version/reserve outside AR0202."""
from pathlib import Path
import copy, csv, io, json, struct, sys, subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import animation_workflow as w
import run_animation_upscale_30fps_v2 as v
import split_animation_pack_by_area as split
import area_pack_state as state

TAG = 'animations-targeted-accepted-20261011-v1'
REPORT = HERE / 'acceptance.json'
DATE = '2026-10-11'

def rel(path):
    return path.resolve().relative_to(ROOT).as_posix()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
        out.write('\n')

def verify_live(ref, area, leaf):
    manifest, resources = v.validate_v2_pack(leaf)
    selected = [r for r in resources if r['resref'] == ref]
    assert selected, (ref, area)
    live = state.game_areas_dir() / area
    registry = (live / v.REGISTRY_NAME).read_bytes()
    version = struct.unpack_from('<I', registry, len(v.REGISTRY_MAGIC))[0]
    for resource in selected:
        assert v.resource_binary_v2(resource, version) in registry, (ref, area, 'runtime contract differs')
        for asset in resource['assets']:
            assert v.sha256_file(live / asset['name']) == asset['sha256'].lower(), (ref, area, asset['name'])
    installed = state.zone_signatures(live)
    assert installed == state.load_lock()['areas'][area]['resources'], area
    return dict(resref=ref, area=area, source_leaf=rel(leaf),
                installed_assets_and_runtime_match=True,
                registry_sha256=v.sha256_file(live / v.REGISTRY_NAME),
                resource_entries=len(selected), frame_counts=[r['frame_count'] for r in selected])

def snapshot(ref, sources):
    """Asset-only QA snapshot, never installed as a whole-area pack."""
    root = ROOT / 'animations/packs-par-zone' / (ref.lower() + '-' + TAG)
    assert not root.exists(), root
    entries = []
    for area, source in sorted(sources.items()):
        manifest, resources = v.validate_v2_pack(source)
        selected = copy.deepcopy([r for r in resources if r['resref'] == ref])
        assets = {a['name']:source / a['name'] for r in selected for a in r['assets']}
        leaf = root / area
        result = split.write_area_pack(leaf, source, manifest, selected, assets, area)
        entries.append(dict(area_id=area, directory=area, resrefs=[ref], resource_count=len(selected),
            frame_count=result['frame_count'], raw_bytes=result['raw_bytes'],
            registry_sha256=result['registry_sha256'], manifest_sha256=v.sha256_file(leaf/'manifest.json'),
            over_runtime_budget=False))
    write(root/'manifest.json', dict(schema=split.INDEX_SCHEMA, status='completed', created_utc=v.utc_now(),
        purpose='QA asset snapshot; not a complete-area installation pack',
        runtime_budget_bytes=v.MAX_RAW_BYTES, area_count=len(entries), areas=entries,
        largest_area_raw_bytes=max(e['raw_bytes'] for e in entries),
        total_raw_bytes=sum(e['raw_bytes'] for e in entries), areas_over_budget=[], resrefs_without_area=[]))
    return root

def final_run(ref, pack, source_pack, **extra):
    run = ROOT / 'animations/ressources' / ref / 'runs' / (ref.lower() + '-' + TAG)
    write(run/'manifest.json', dict(schema='bg2-upscale-animation-final-selection-v1', status='completed',
        created_utc=v.utc_now(), resrefs=[ref], source_pack=rel(source_pack),
        source_pack_manifest_sha256=v.sha256_file(source_pack/'manifest.json'),
        output_split_root=rel(pack), output_manifest_sha256=v.sha256_file(pack/'manifest.json'),
        release_status='not-selected', **extra))
    return run

def main():
    assert not REPORT.exists(), 'Acceptance is immutable'
    old_fire = v.load_json(ROOT/'animations/index/selections/FIRE_3.json')
    old_fpit = v.load_json(ROOT/'animations/index/selections/FPIT1S.json')
    preserved = {ROOT/x['qa_decision']['path']:v.sha256_file(ROOT/x['qa_decision']['path'])
                 for x in [old_fire, old_fpit]}
    preserved[ROOT/'animations/index/selections/FPIT1S.json'] = v.sha256_file(ROOT/'animations/index/selections/FPIT1S.json')
    night, _ = w._registry_row(ROOT, 'AM1400N')
    lock_hash = v.sha256_file(state.LOCK_PATH)
    fire_new = ROOT/'animations/packs-par-zone/fire3-aura-fade4-30fps-20261011-v1/AR0202'
    fire_run = ROOT/'animations/ressources/FIRE_3/runs/fire3-aura-fade4-30fps-20261011-v1'
    checks = [verify_live('FIRE_3', 'AR0202', fire_new)]
    fountain = ROOT/'animations/packs-par-zone/trees-seedvr-static-x4-20261011-v1-ar1400/AR1400'
    checks.append(verify_live('AM1400A', 'AR1400', fountain))
    for area in ['AR0509','AR0522','AR0601','AR5202']:
        source = next(a for a in old_fpit['source_pack']['areas'] if a['area']==area)
        checks.append(verify_live('FPIT1S', area, ROOT/source['path']))
    fingerprints = {c['area']:state.zone_fingerprint(state.game_areas_dir()/c['area']) for c in checks}

    sources = {a['area']:ROOT/a['path'] for a in old_fire['source_pack']['areas']}
    sources['AR0202'] = fire_new
    other_fire = sorted(set(sources)-{'AR0202'})
    fire_pack = snapshot('FIRE_3', sources)
    # Explicitly retain previous bytes/QA and its temporal reserve on the other nine maps.
    for area in other_fire:
        assert w._resource_group(v.validate_v2_pack(fire_pack/area)[1], 'FIRE_3') == w._resource_group(v.validate_v2_pack(sources[area])[1], 'FIRE_3')
    fire_final = final_run('FIRE_3', fire_pack, ROOT/old_fire['source_pack']['path'],
        source_run=rel(fire_run), source_run_manifest_sha256=v.sha256_file(fire_run/'manifest.json'),
        qa_status='accepted-composite; AR0202 new QA; other areas previous QA/reserve retained',
        new_ingame_tested_areas=['AR0202'], inherited_qa=old_fire['qa_decision'],
        inherited_qa_areas=other_fire, temporal_reserve_areas=other_fire,
        installation_receipt='pipeline/recipes/fire3-aura-fade4-30fps-20261011-v1/installation.json',
        recipe_by_area={'AR0202':'Apollo8 30FPS, 28 distinct phases, fade4 x4, sigma0',
                        'other_areas':'previous 14-frame Native version unchanged'})
    fire_text = ('Utilisateur : validé ! FIRE_3 accepté ingame sur les quatre flammes AR0202 : Apollo8 30 FPS, '
        '28 phases distinctes, durée 14/15 s, fondu seul 4 px x4, sans flou. Réserve AR0202 clôturée. '
        'Sélection composite : les neuf autres zones conservent strictement les octets et la QA du 2026-09-16, '
        'y compris leur réserve sur le cycle natif ; aucune nouvelle visite ni validation du traitement 30 FPS sur ces zones.')
    fire_notes = ('QA utilisateur 2026-10-11 : quatre occurrences FIRE_3 AR0202 acceptées, Apollo8 30 FPS/28 phases '
        'distinctes/0,933333 s, aura fondu seul4 px x4, sigma0, cœur et géométrie préservés. Réserve AR0202 clôturée. '
        'Autres zones : ancienne sélection 14frames Native/QA 2026-09-16 conservée avec réserve temporelle ; '
        'nouvelle recette non propagée. Détails : '+rel(REPORT)+'. Release non sélectionnée.')
    fountain_pack = snapshot('AM1400A', {'AR1400':fountain})
    fountain_final = final_run('AM1400A', fountain_pack, fountain,
        qa_status='accepted-ingame', tested_areas=['AR1400'],
        selection_reason='Utilisateur : AM1400A validé ; confirmation finale de la liste.',
        recipe='SeedVR2 7B LAB x4 / Apollo8 30 FPS, 14 phases, contour actuel accepté')
    fountain_row, _ = w._registry_row(ROOT, 'AM1400A')
    fountain_notes = fountain_row['notes'].split('Contour alpha 1 bit en escaliers')[0].rstrip() + (
        ' QA reconfirmée explicitement le 2026-10-11 sur AM1400A/AR1400, fichiers et contrat installés identiques. '
        'Contour actuel accepté en l’état : intervention spline/fondu précédemment envisagée non requise. '
        'AM1400N non nouvellement validé. Détails : '+rel(REPORT)+'.')
    jobs = [dict(raw_resref='FIRE_3', final_run=fire_final, qa_pack=fire_pack, areas=sorted(sources),
        decision_text=fire_text, decision_id='2026-10-11-accepted-fire3-ar0202-fade4-composite-v1',
        recipe_id=TAG, correction_id='fire3-mixed-ar0202-fade4-other-native-20261011-v1', notes=fire_notes),
        dict(raw_resref='AM1400A', final_run=fountain_final, qa_pack=fountain_pack, areas=['AR1400'],
        decision_text='Utilisateur : AM1400A validé. Fontaine de jour AR1400 acceptée en l’état, x4/30 FPS/14 phases ; contour actuel accepté. Confirmation de la liste le 2026-10-11. Aucune nouvelle QA AM1400N.',
        decision_id='2026-10-11-accepted-am1400a-current-contour-v1', recipe_id=TAG, notes=fountain_notes)]
    # Verify both final authority transactions before applying either.
    for job in jobs:
        w.finalize(ROOT, decision_status='accepted', decision_date=DATE, **job)
    for job in jobs:
        w.finalize(ROOT, decision_status='accepted', decision_date=DATE, apply=True, **job)

    # Separate exact area decision for the new FIRE_3 treatment; no global fresh-QA inference.
    artifact, manifest, manifest_path = w._artifact(ROOT, fire_run)
    area_decision = dict(**{'$schema':w.DECISION_SCHEMA_REF}, schema_version=1,
        decision_id='2026-10-11-accepted-fire3-ar0202-fade4-30fps-v1', asset_id='animations:bam:FIRE_3',
        resref='FIRE_3', status='accepted', result_kind='x4', decision_origin='explicit-user-ingame-qa',
        decision_date=DATE, recorded_at_utc=v.utc_now(), decision=fire_text.split('Sélection composite')[0].strip(),
        tested_areas=['AR0202'], final_run=artifact,
        source_pack=w._source_pack(ROOT, fire_new.parent, 'FIRE_3', ['AR0202']),
        lineage=w._collect_lineage(ROOT, manifest, manifest_path),
        recipe_id='fire3-aura-fade4-30fps-20261011-v1', correction_id='fire3-aura-fade4-30fps-20261011-v1')
    area_path = ROOT/'animations/index/area-qa-decisions/FIRE_3'/(area_decision['decision_id']+'.json')
    write(area_path, area_decision)
    errors=[]
    w._validate_decision_record(ROOT, area_path, 'FIRE_3', errors, validate_registry=False)
    assert not errors, errors

    # FPIT1S's acquired global QA stays immutable. Record confirmation in current tracking.
    with w._animation_authority_lock(ROOT):
        row, rows = w._registry_row(ROOT, 'FPIT1S')
        old = ('Points ouverts mineurs: les masques d\'AR0509 (deux occurrences) et d\'AR0522-droite ne retirent aucun texel a l\'animation, et AR0522-gauche, AR0601 et AR5202 n\'ont pas de masque; a confirmer comme sans occlusion ou a peindre.')
        row['notes'] = row['notes'].replace(old,
            'QA reconfirmée par l’utilisateur le 2026-10-11 : rendu et masques actuels acceptés en l’état ; '
            'aucune retouche supplémentaire demandée. Cette confirmation ne prétend pas mesurer l’occlusion ni refaire une visite exhaustive des 15 zones.')
        row['notes'] += ' Confirmation et identité des fichiers des cartes proposées : '+rel(REPORT)+'.'
        w._write_transaction(ROOT, {ROOT/w.REGISTRY_REL:w._render_registry([
            row if r['resref']=='FPIT1S' else r for r in rows])})
    finish(preserved, night, lock_hash, fingerprints, checks, other_fire, old_fpit, fire_run, area_path)

def finish(preserved, night, lock_hash, fingerprints, checks, other_fire, old_fpit, fire_run, area_path):
    alpha_path = ROOT/'animations/index/animation_alpha_corrections.csv'
    with alpha_path.open(encoding='utf-8', newline='') as stream:
        reader=csv.DictReader(stream); fields=reader.fieldnames; alpha=list(reader)
    alpha.append(dict(resref='FIRE_3', areas='AR0202', element='quatre flammes',
        correction_id='fire3-aura-fade4-30fps-20261011-v1', alpha_operations='aura-only-inner-fade;loop-wide-core-protection',
        inner_radius_x4='4', canvas_radius_x4='0', canvas_edges='none',
        rgb_policy='existing-premultiplied-RGBA-times-fade-once', status='validated-installed', validated_date=DATE,
        prototype=rel(fire_run), notes='Fondu seul4 px x4, sigma0 ; cœur lumineux/géométrie natifs préservés. Apollo8 30 FPS, 28 phases distinctes, 14/15 s. QA quatre FIRE_3 AR0202 acceptée. Autres neuf zones non propagées ; réserve temporelle conservée. '+rel(area_path)))
    out=io.StringIO(newline=''); writer=csv.DictWriter(out, fieldnames=fields, lineterminator='\n');writer.writerow(alpha[-1])
    original_bytes=alpha_path.read_bytes()
    with w._animation_authority_lock(ROOT):
        # This recipe catalogue is outside workflow's selection/QA transaction allowlist.
        temporary = HERE/'alpha-catalogue.partial'
        temporary.write_bytes(original_bytes + (b'' if original_bytes.endswith(b'\n') else b'\n') + out.getvalue().encode('utf-8'))
        temporary.replace(alpha_path)

    for path, digest in preserved.items():
        assert v.sha256_file(path)==digest, path
    assert w._registry_row(ROOT,'AM1400N')[0]==night, 'Night fountain changed'
    assert v.sha256_file(state.LOCK_PATH)==lock_hash, 'Installation lock changed'
    for area, fingerprint in fingerprints.items():
        assert state.zone_fingerprint(state.game_areas_dir()/area)==fingerprint, area
    authority={ref:w.check_workspace(ROOT,ref) for ref in ['FIRE_3','AM1400A','FPIT1S','AM1400N']}
    assert all(c['ok'] for c in authority.values()), authority
    write(REPORT, dict(schema='bg2-upscale-animation-targeted-acceptance-v1', status='accepted-ingame',
        decision_date=DATE, decision_origin='explicit-user-ingame-qa', user_statement='validé ! du coup on peut valider toute cette liste d’assets proprement ?',
        resources=[dict(resref='FIRE_3', new_qa_areas=['AR0202'], occurrences=4, fps=30, distinct_phases=28,
                        inner_fade_x4=4, sigma_x4=0, area_qa_decision=rel(area_path),
                        selection='animations/index/selections/FIRE_3.json', historical_qa_retained_areas=other_fire),
                   dict(resref='AM1400A', new_qa_areas=['AR1400'], fps=30, phases=14,
                        selection='animations/index/selections/AM1400A.json', current_contour_accepted=True),
                   dict(resref='FPIT1S', confirmation='asset accepted as currently observed',
                        acquired_global_qa=old_fpit['qa_decision'], immutable_selection_preserved=True,
                        no_exhaustive_new_visits_inferred=True),
                   dict(resref='AM1400N', status='historical validation retained; no new user confirmation')],
        installed_checks=checks, authority_checks=authority, prior_qa_hashes_preserved={rel(p):h for p,h in preserved.items()},
        remaining_actions=[dict(resref='FIRE_3', areas=other_fire,
            action='If global 30FPS treatment is requested: prepare/install/verify on these maps; prior native temporal reserve remains.')],
        game_payload_changed=False, installation_lock_changed=False, release_status='not-selected'))
    print('ACCEPTED: FIRE_3 AR0202 fade4/30FPS; AM1400A current; FPIT1S reconfirmed. AM1400N unchanged. Historical QA preserved; nine FIRE_3 maps retain native reserve.')

def finish_remaining():
    """Resume catalogue/report only after authority writes succeeded; never replay QA writes."""
    assert not REPORT.exists()
    old_fpit = v.load_json(ROOT/'animations/index/selections/FPIT1S.json')
    preserved = {}
    for name in ['animations/index/qa-decisions/FIRE_3/2026-09-16-accepted-fire3-x4-reserve-animation.json',
                 old_fpit['qa_decision']['path'], 'animations/index/selections/FPIT1S.json']:
        original = subprocess.check_output(['git','show','HEAD:'+name], cwd=ROOT)
        import hashlib
        preserved[ROOT/name] = hashlib.sha256(original).hexdigest()
    original_registry = subprocess.check_output(['git','show','HEAD:animations/index/animation_upscale_registry.csv'], cwd=ROOT).decode('utf-8')
    night = next(row for row in csv.DictReader(io.StringIO(original_registry)) if row['resref']=='AM1400N')
    checks = [verify_live('FIRE_3','AR0202',ROOT/'animations/packs-par-zone/fire3-aura-fade4-30fps-20261011-v1/AR0202'),
              verify_live('AM1400A','AR1400',ROOT/'animations/packs-par-zone/trees-seedvr-static-x4-20261011-v1-ar1400/AR1400')]
    for area in ['AR0509','AR0522','AR0601','AR5202']:
        source = next(a for a in old_fpit['source_pack']['areas'] if a['area']==area)
        checks.append(verify_live('FPIT1S',area,ROOT/source['path']))
    fingerprints = {c['area']:state.zone_fingerprint(state.game_areas_dir()/c['area']) for c in checks}
    final = v.load_json(ROOT/'animations/ressources/FIRE_3/runs'/('fire_3-'+TAG)/'manifest.json')
    area_path = ROOT/'animations/index/area-qa-decisions/FIRE_3/2026-10-11-accepted-fire3-ar0202-fade4-30fps-v1.json'
    errors=[]
    w._validate_decision_record(ROOT,area_path,'FIRE_3',errors,validate_registry=False)
    assert not errors, errors
    finish(preserved,night,v.sha256_file(state.LOCK_PATH),fingerprints,checks,final['temporal_reserve_areas'],old_fpit,
           ROOT/'animations/ressources/FIRE_3/runs/fire3-aura-fade4-30fps-20261011-v1',area_path)

if __name__ == '__main__':
    finish_remaining() if '--finish' in sys.argv else main()
