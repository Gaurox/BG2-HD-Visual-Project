"""Record only completed release work; preserve previous QA and reports."""
from pathlib import Path
import datetime,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
R=ROOT/'releases/BG2-HD-Upscale'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest().upper()
def rel(p):return p.resolve().relative_to(ROOT).as_posix()
def write_new(p,data):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
package=load(HERE/'package-finalization.json')
assert package['zip_storage_verified'] and package['zip_compression']=='NoCompression' and package['public_status']=='blocked'
archive=Path(package['archive']);assert sha(archive)==package['archive_sha256']
required_logs={'compile-batch':'Wrote 28630 entries','phase2':'Phase 2 static validation passed','staging':'"sha256_verified": true','phase4':'Phase 4 payload validation passed','phase6b-uncompressed':'PHASE6B_PACKAGE=PASSED','phase5a-uncompressed':'PHASE5A_SUITE=PASSED','unit-tests':'Ran 64 tests','config-encodings':'CONFIG_ENCODINGS=PASSED'}
proof_logs={}
for name,marker in required_logs.items():
    source=HERE/(name+'.log');assert marker in source.read_text(encoding='utf-8-sig'),name
    target=HERE/'verification'/(name+'.txt');assert not target.exists();target.parent.mkdir(exist_ok=True);target.write_bytes(source.read_bytes());proof_logs[name]=dict(path=rel(target),sha256=sha(target))
for name in ['build-uncompressed']:
    source=HERE/(name+'.log');target=HERE/'verification'/(name+'.txt');assert not target.exists();target.write_bytes(source.read_bytes());proof_logs[name]=dict(path=rel(target),sha256=sha(target))
release=load(R/'manifests/release.json');candidates=load(R/'manifests/animation-release-candidates.json')['candidates'];content=load(R/'manifests/content.json')['entries'];components=load(R/'manifests/components.json')['components']
assert len(candidates)==234 and all(c['approval_status']=='approved-for-release' for c in candidates)
assert len(content)==28630 and len(components)==616
refs={ref for c in candidates for ref in c['required_resrefs']}
selections=[load(p) for p in (ROOT/'animations/index/selections').glob('*.json')]
assert len(selections)==len(refs)==246
assert {s.get('runtime_resref') or s['resref'] for s in selections}==refs
before=load(HERE/'qa-authorities-before.json');changed=[p for p,h in before.items() if sha(ROOT/p)!=h.upper()]
assert set(changed)=={'animations/index/selections/AM0309A.json','animations/index/selections/OHHPORT.json'},changed
receipt=load(HERE/'promotion-receipt.json')
assert all(sha(ROOT/p)==h.upper() for p,h in receipt['preserved_qa_sha256'].items())
assert sha(R/'manifests/animation-release-candidates.json')==receipt['candidates_sha256'].upper()
area_packs=[load(ROOT/c['source_pack']/'manifest.json') for c in candidates]
max_raw=max(p['raw_bytes'] for p in area_packs);assert max_raw<=512*1024*1024
stats={}
for e in content:
    s=stats.setdefault(e['kind'],dict(files=0,bytes=0,areas=set()));s['files']+=1;s['bytes']+=e['bytes'];s['areas'].add(e['area'])
for s in stats.values():s['areas']=len(s['areas'])
manifest_files=['release.json','content.json','components.json','animation-release-candidates.json','renderer-bundle.json','runtime-compatibility.json']
for name in manifest_files:assert (R/'manifests'/name).read_bytes()==(R/'bg2hd/manifests'/name).read_bytes(),name
with zipfile.ZipFile(archive) as z:
    for name in manifest_files:assert z.read('bg2hd/manifests/'+name)==(R/'manifests'/name).read_bytes(),name
    assert z.read('bg2hd/bg2hd.tp2')==(R/'bg2hd/bg2hd.tp2').read_bytes()
report=dict(schema='bg2-animation-release-status-v1',generated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),request_date='2026-10-11',status='animation-release-integrated-local-alpha',version=release['version'],
    qa=dict(accepted_assets=246,new_ingame_validation=False,previous_decisions_unchanged=True,preserved_authority_hashes=len(receipt['preserved_qa_sha256']),mutable_selections_rebound=changed,bindings=['ar0309-occurrence-binding.json','ohhport-canonical-binding.json'],previous_tracking='docs/validation/animations-cleanup-status-20261011-v4.json'),
    production=dict(frozen_pack_root='animations/packs-par-zone/animations-release-20261011-v1',complete_areas=234,max_area_raw_bytes=max_raw,budget_bytes=512*1024*1024),
    installation=dict(game_mutation=False,acquired_installed_payloads_preserved=True,ini_activation='owned_ini_keys.core-steam.Shaders.EnableAreaAnimationX4=true'),
    release=dict(approved_animation_areas=234,pending_animation_areas=0,components=len(components),files=len(content),bytes=sum(e['bytes'] for e in content),by_kind=stats,manifest_sha256={name:sha(R/'manifests'/name) for name in manifest_files},tp2_sha256=sha(R/'bg2hd/bg2hd.tp2')),
    renderer=dict(bundle_id='iee-0.1.0-alpha.9',accepted_dll_sha256=load(R/'manifests/renderer-bundle.json')['files'][0]['sha256'],retained_source_inventory=rel(HERE/'renderer-source-inventory.json'),source_rebuild_performed=False,continuity='accepted trees/night DLL and preserved SPHINCT source contracts; exact binary retained'),
    verification=dict(unit_tests=64,static_schema_translations_tp2='passed',all_candidates_full_proof_verification='passed',staging_sha256='passed',payload_and_renderer='passed',archive_checksums_and_fixed_timestamps='passed',installer_and_restoration_fixtures='passed',animation_install_samples=['AR0603','AR0900','AR0516'],real_clean_game_lifecycle='pending',proof_logs=proof_logs),
    package=dict(path=rel(archive),sha256=package['archive_sha256'],bytes=package['archive_bytes'],zip_compression='NoCompression',storage_methods_verified='ZIP_STORED',independent_builds_comparison_performed=False,build_receipts=[rel(HERE/'build-uncompressed.json')],superseded_trial_receipt=rel(HERE/'build-a.json'),disposable_build_scratch_removed=True),
    remaining=dict(published_asset_ambiguities=[],historical_exceptions=['superseded OHHPORT final_run layout retained immutably; current canonical binding repaired','previous 29 uncertain runs remain in corbeille/animations-20261011-v1; not promoted'],public_status=release['release_status'],public_blocking_conditions=release['blocking_conditions']))
# Select the DLL explicitly rather than relying on bundle manifest ordering.
report['renderer']['accepted_dll_sha256']=next(f['sha256'] for f in load(R/'manifests/renderer-bundle.json')['files'] if f['path']=='InfinityEngine-Enhancer.dll')
path=ROOT/'docs/validation/animations-release-status-20261012-v1.json';write_new(path,report)
p=ROOT/'animations/README.md';text=p.read_text(encoding='utf-8-sig').replace('## Suivi au 2026-10-11 — QA et nettoyage clôturés','## Suivi au 2026-10-12 — QA, nettoyage et release animations intégrés')
text=text.replace('- [Rapport courant](../docs/validation/animations-cleanup-status-20261011-v4.json) ; rapports `v1`/`v2`/`v3` historiques immuables.','- [Rapport courant](../docs/validation/animations-release-status-20261012-v1.json) ; [nettoyage v4](../docs/validation/animations-cleanup-status-20261011-v4.json) et rapports antérieurs immuables.')
text=text.replace('- Release : finalisation séparée ; aucun payload, candidat, manifeste release ou paquet modifié.','- Release alpha.6 : 234 zones approuvées, composition complète figée sous `packs-par-zone/animations-release-20261011-v1/` ; 246 BAM acceptés, aucune QA ingame nouvelle déduite. AM0309A/OHHPORT rattachés aux octets et contrats acquis ; anciennes décisions conservées.\n- Renderer alpha.9 : DLL acceptée arbres/nuit + contrats SPHINCT conservés ; activation `Shaders.EnableAreaAnimationX4=true`. WED AR0516 inchangé, preuve acquise reliée au registre courant.\n- Payload global : 28 630 fichiers / 616 composants ; schémas, neuf langues, TP2, SHA du staging, intégrité ZIP et installation/restauration sur fixtures passent. ZIP sans compression (méthode ZIP_STORED vérifiée) ; scratch de construction supprimé, anciens paquets conservés. Comparaison de deux builds non effectuée.\n- Publication `blocked` : cycle réel jeu propre/Steam/EEex, sauvegardes futures vanilla, désinstallation complète, cycle renderer combiné et contact/provenance publics. Assets retenus : aucun cas ambigu supplémentaire.')
p.write_bytes(text.encode('utf-8'))
print('FINAL_REPORT',rel(path),'ARCHIVE',rel(archive),flush=True)
