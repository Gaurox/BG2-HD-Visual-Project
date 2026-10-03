"""Verify fresh alpha output and reuse unchanged V8 runtime compatibility proofs."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
work=ROOT/'sprite/.work/q3m-ankheg-alpha-light-x2-20261004-v1'
old=ROOT/'docs/measurements/q3m-ankheg-spline-fit1-x2-20261003-v1'
assert not (HERE/'verification.json').exists()
old_generation=load(old/'current-generation.json');proof=load(old/'verification.json')
assert file_sha(old/'verification.json')==old_generation['host_verification']['sha256']
for item in (proof['dll'],proof['source'],proof['leaf_writer']):
    assert file_sha(ROOT/item['path'])==item['sha256'],'runtime proof no longer reusable'
native_log=work/'native-alpha.log'
source_log=ROOT/'sprite/.work/q3m-alpha-light-native-20261004-v1.log'
native_log.write_bytes(source_log.read_bytes())
native=next(json.loads(s) for s in reversed(native_log.read_text().splitlines()) if s.startswith('{'))
assert native['passed'] and native['frames']==516 and native['resources']==12 and native['native_cycle_slots']==1485
test=subprocess.run([sys.executable,'-m','unittest','discover','-s','pipeline/tests','-p','test_sprite_alpha_coverage.py'],
    cwd=ROOT,capture_output=True,text=True)
(work/'alpha-tests.log').write_text(test.stdout+test.stderr,encoding='utf-8')
assert test.returncode==0 and 'Ran 6 tests' in test.stderr
p=load(HERE/'production.json')
assert p['positive_alpha_support_byte_identical_K6'] and p['Q3m_colour_planes_byte_identical']
assert p['stats']['physical_pixels_cleared']==0 and p['stats']['physical_frames']==516
assert all(f['source_support_preserved'] and f['minimum_coverage']>=176 for r in p['details'] for f in r['frame_masks'])
write_json(HERE/'verification.json',dict(schema='bg2-ankheg-alpha-host-verification-v1',V8_alpha=native,
    V7_original_unchanged=proof['V7_original_unchanged'],V7_flying_unchanged=proof['V7_flying_unchanged'],
    core_native_suite_passed=proof['core_native_suite_passed'],native_malformed_catalogs=proof['native_malformed_catalogs'],
    unchanged_runtime_compatibility_proof=identity(old/'verification.json'),
    python_alpha_tests=6,source_support_preserved=True,source_holes_and_connected_components_preserved=True,
    visible_RGB_preserved_K6=True,physical_pixels_cleared=0,
    application='strictly positive edge coverage multiplied at frame_pixel; original silhouette support unchanged',
    dll=proof['dll'],source=proof['source'],leaf_writer=proof['leaf_writer'],
    mask_processor=identity(ROOT/'pipeline/scripts/sprite_alpha_coverage.py'),
    native_log=identity(native_log),python_log=identity(work/'alpha-tests.log'),ingame_QA=False))
print(json.dumps(dict(native_passed=True,physical_frames=516,source_support_preserved=True,python_alpha_tests=6)))
