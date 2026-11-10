"""Verify final projection, preserved authorities and package mirrors after staging."""
import csv, hashlib, json
from common import ROOT, OUT, RELEASE, load, save, sha


def main():
    content = load(RELEASE/'manifests/content.json')['entries']
    baseline = load(ROOT/'pipeline/recipes/effects-release-finalization-20261110-v1/existing-content-summary.json')
    other = [e for e in content if e['kind'] != 'effect']
    digest = hashlib.sha256(json.dumps(other, sort_keys=True, separators=(',', ':')).encode()).hexdigest().upper()
    assert len(other) == baseline['entries'] and sum(e['bytes'] for e in other) == baseline['bytes']
    assert digest == baseline['canonical_json_sha256'], 'Unrelated content changed'
    before = load(OUT/'processing-before.json')
    with (ROOT/'effects/index/processing.csv').open(encoding='utf-8-sig', newline='') as stream:
        after = list(csv.DictReader(stream))
    changed = 0
    assert len(before) == len(after)
    for old, new in zip(before, after):
        expected = dict(old)
        if old['release_state'] == 'approved':
            expected['release_candidate'] = 'effects-accepted-shared-storage-20261110-v1'
            changed += 1
        assert new == expected, old['asset_key']
    assert changed == 424
    mirrors = []
    names = ['runtime-compatibility.json', 'dependency-bootstrap.json', 'components.json',
             'content.json', 'map-release-candidates.csv', 'map-release-assemblies.json',
             'animation-release-candidates.json', 'effect-release-candidates.json',
             'sprite-release-candidates.json', 'overlay-sources.json', 'renderer-bundle.json',
             'languages.json', 'licenses-and-exclusions.json', 'release.json']
    names += ['sprite-inventories/'+p.name for p in (RELEASE/'manifests/sprite-inventories').glob('*.json')]
    for name in names:
        source = RELEASE/'manifests'/name
        mirror = RELEASE/'bg2hd/manifests'/name
        assert mirror.exists() and sha(source) == sha(mirror), source.name
        mirrors.append(name)
    renderer = load(RELEASE/'manifests/renderer-bundle.json')
    for entry in renderer['files']:
        f = RELEASE/'bg2hd/renderer'/entry['path']
        assert f.stat().st_size == entry['bytes'] and sha(f) == entry['sha256']
    staging = load(OUT/'staging.json')
    total = sum(e['bytes'] for e in content)
    assert staging['status'] == 'passed' and staging['sha256_verified']
    assert staging['files'] == len(content) == 109512 and staging['bytes'] == total
    tp2 = (RELEASE/'bg2hd/bg2hd.tp2').read_text(encoding='utf-8-sig')
    assert 'bg2hd-effect-storage.ps1' in tp2 and 'EffectStorage-X4.index' in tp2
    release = load(RELEASE/'manifests/release.json')
    assert release['version'] == '0.1.0-alpha.9' and release['release_status'] == 'blocked'
    save(OUT/'projection-verification.json', dict(status='passed', version=release['version'],
        renderer=renderer['bundle_id'], payload_files=len(content), payload_bytes=total,
        non_effect_entries_unchanged=len(other), non_effect_canonical_sha256=digest,
        processing_rows_rebound=changed, processing_other_fields_unchanged=True,
        mirrored_manifests=mirrors, renderer_hashes_verified=True, staging=staging,
        game_modified=False, ingame_smoke='pending', public_release='blocked'))
    print(f'Projection verified: {len(content)} files / {total} bytes; {len(other)} unrelated entries unchanged.')


if __name__ == '__main__':
    main()
