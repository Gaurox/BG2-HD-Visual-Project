"""Assemble the four optimized payloads over the verified alpha.11 ZIP."""
import hashlib
import json
from pathlib import Path
import re
from contextlib import ExitStack
from collections import defaultdict
from zipfile import ZIP_STORED, ZipFile, ZipInfo

RELEASE = Path(__file__).resolve().parents[1]
ROOT = RELEASE.parents[1]
VERSION = '0.1.0-alpha.12'
DIST = RELEASE / 'dist-local/alpha12-optimized-20261121-v1'
OUT = DIST / f'BG2HD-{VERSION}-windows-local-alpha.zip'
BASE = RELEASE / 'dist-local/alpha11-crop-20261121-v1/BG2HD-0.1.0-alpha.11-windows-local-alpha.zip'
SPRITE = ROOT / 'pipeline/recipes/sprite-compact-representatives-20261121-v1'
MAP = ROOT / 'pipeline/recipes/map-original-sharing-20261121-v1'
AREA = ROOT / 'pipeline/recipes/area-animation-tiles-20261121-v1'
EFFECT = ROOT / 'effects/research/rgba-tile-sharing-20261121-v1'
ENGINE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/build-effect-tiles-20261121-v1/Release'
HELPER = 'bg2hd/tools/Expand-BG2HDPayload.exe'
HELPER_COMMAND = HELPER.replace('/', '\\')
MOD = 'bg2hd/manifests/'
PREFIX = 'bg2hd/payload/'


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def proof(path, expected):
    if file_hash(path) != expected.upper():
        raise ValueError(f'Input checksum differs: {path}')
    return path


def read_json(path):
    return json.loads(path.read_bytes())


def relative(path):
    return path.relative_to(ROOT).as_posix()


def payload(row):
    return f"{PREFIX}{row['payload_group']}/{Path(row['source']).name}"


def physical(path):
    return path.stat().st_size, file_hash(path)


def file_asset(row, path, destination=None, group=None, component=None, label=None):
    row = dict(row)
    if destination:
        row['destination'] = destination
    if component is not None:
        row['component_id'] = row['install_order'] = component
        row['component_label'] = label
    if group:
        row['payload_group'] = group
    row.update(source=relative(path), source_run=relative(path.parent))
    row['bytes'], row['sha256'] = physical(path)
    return row


def build_tp2(text, entries, destination_paths, transports, affected_area_components):
    prologue, *blocks = re.split(r'(?m)^BEGIN ', text.replace('\r\n', '\n'))
    prologue = re.sub(r'(?m)^VERSION ~[^~]+~$', f'VERSION ~{VERSION}~', prologue)
    by_component = defaultdict(list)
    for row in entries:
        by_component[row['component_id']].append(row)
    pattern = re.compile(r'(?m)^  COPY_LARGE ~([^~]+)~ ~([^~]+)~\r?\n')
    inserted = False
    result = [prologue]
    archive = by_component[2999][0]
    for original in blocks:
        component = int(re.search(r'(?m)^  DESIGNATED (\d+)', original)[1])
        block = 'BEGIN ' + original
        if component in affected_area_components and not inserted:
            result.append(
                'BEGIN ~Shared area animation archive (x4)~\n'
                '  DESIGNATED 2999\n  LABEL ~animation-shared-archive~\n'
                '  REQUIRE_PREDICATE GAME_IS ~bg2ee~ @11\n'
                '  REQUIRE_COMPONENT ~bg2hd/bg2hd.tp2~ ~0~ @14\n'
                '  MKDIR ~iee-assets~\n  MKDIR ~iee-assets/area-animation-pack~\n'
                f"  COPY_LARGE ~{payload(archive)}~ ~{archive['destination']}~\n\n"
            )
            inserted = True
        rows = by_component.get(component, [])
        if rows:
            if component in affected_area_components:
                # REQUIRE_COMPONENT is a WeiDU component flag, before actions.
                requirements = list(re.finditer(r'(?m)^  REQUIRE_COMPONENT [^\n]+\n', block))
                if not requirements:
                    raise ValueError(f'No dependency header in component {component}')
                anchor = requirements[-1].end()
                block = (block[:anchor] +
                         '  REQUIRE_COMPONENT ~bg2hd/bg2hd.tp2~ ~2999~ ~Install the shared area animation archive first.~\n' +
                         block[anchor:])
            first = pattern.search(block)
            if not first:
                raise ValueError(f'No insertion point in component {component}')
            lines = []
            if component in affected_area_components:
                lines.append('  MKDIR ~iee-assets/area-animation-pack~')
            if component in transports:
                lines.extend([
                    f'  AT_NOW expand_payload_result ~{HELPER_COMMAND} {component}~',
                    '  ACTION_IF expand_payload_result != 0 THEN BEGIN FAIL ~Unable to restore the optimized payload.~ END',
                ])
            for row in sorted(rows, key=lambda x: (x['install_order'], x['destination'], x['source'])):
                destination = row['destination']
                path = destination_paths.get((component, destination), payload(row))
                lines.append(f'  COPY_LARGE ~{path}~ ~{destination}~')
            # Retain component preconditions, configuration and uninstall hooks.
            block = block[:first.start()] + '\n'.join(lines) + '\n' + pattern.sub('', block[first.start():])
        elif pattern.search(block):
            raise ValueError(f'Unexpected stale COPY component {component}')
        result.append(block)
    if not inserted:
        raise ValueError('Missing area archive component')
    return ''.join(result).encode()


class ArchiveBuilder:
    def __init__(self, path):
        self.archive = ZipFile(path, 'x')
        self.files = {}

    def add(self, name, source, size=None, expected=None):
        if name in self.files:
            raise ValueError(f'Duplicate archive path: {name}')
        entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        entry.compress_type = ZIP_STORED
        if isinstance(source, bytes):
            self.archive.writestr(entry, source)
            record = (len(source), sha(source))
        else:
            digest = hashlib.sha256()
            total = 0
            with source as inp, self.archive.open(entry, 'w', force_zip64=size >= 2**31) as out:
                for data in iter(lambda: inp.read(8 << 20), b''):
                    digest.update(data)
                    total += len(data)
                    out.write(data)
            record = total, digest.hexdigest().upper()
        if size is not None and record[0] != size or expected is not None and record[1] != expected.upper():
            raise ValueError(f'Packaged asset differs: {name}')
        self.files[name] = record

    def close(self):
        self.archive.close()


def assemble(base, sprite, maps):
    manifest = json.loads(base.read(MOD+'content.json'))
    components = json.loads(base.read(MOD+'components.json'))
    release = json.loads(base.read(MOD+'release.json'))
    renderer = json.loads(base.read(MOD+'renderer-bundle.json'))
    if release['version'] != '0.1.0-alpha.11':
        raise ValueError('Wrong baseline release')
    entries = manifest['entries']
    retained = []
    sources = {}
    bindings = {}
    transport = defaultdict(list)
    area_template = {}
    effect_template = None
    map_pages = []
    for row in entries:
        kind, dest = row['kind'], row['destination']
        path = payload(row)
        if kind == 'area-animation' and dest.endswith('.rgba'):
            continue
        if kind == 'effect' and dest.startswith('iee-assets/effects/'):
            effect_template = effect_template or row
            continue
        if kind == 'map' and dest.upper().endswith('.PVRZ'):
            map_pages.append(row)
            continue
        retained.append(row)
        if kind == 'area-animation' and dest.endswith('.registry'):
            area_template[row['area']] = row
        if kind == 'sprite' and dest.endswith('.registry'):
            transport[row['component_id']].append(f"S {path} {row['bytes']} {row['sha256']}")
            info = sprite.getinfo(dest)
            sources[path+'.compact'] = (sprite, dest, info.file_size, None)
        else:
            sources[path] = (base, path, row['bytes'], row['sha256'])

    sprite_proof = json.loads(sprite.read('sprite-representatives-pack.json'))
    if sprite_proof != {r['destination']: {k: r[k] for k in ('sha256', 'bytes')}
                        for r in retained if r['kind']=='sprite'}:
        raise ValueError('Sprite pack and baseline registry identities differ')
    area_proof = read_json(AREA/'results.json')
    area_archive = proof(AREA/'run/area-animations-tiled-test.zip', area_proof['tiled_zip_sha256'])
    overlays = AREA/'run/verify-assets/area-animation-pack'
    with ZipFile(area_archive) as area_zip:
        mapping = json.loads(area_zip.read('area-animation-frames.json'))
    expected_area = {r['destination']: r['sha256'].lower() for r in entries
                     if r['kind']=='area-animation' and r['destination'].endswith('.rgba')}
    if mapping['frames'] != expected_area or len(area_template) != 234:
        raise ValueError('Area archive does not cover the baseline animations')
    archive_row = file_asset(next(iter(area_template.values())), area_archive,
                             'iee-assets/area-animation-pack/AreaAnimations-X4.zip',
                             'animation-shared-archive', 2999, 'animation-shared-archive')
    archive_row.update(area='AREAS', model='AreaAnimationArchive-X4')
    retained.append(archive_row)
    sources[payload(archive_row)] = (area_archive, None, archive_row['bytes'], archive_row['sha256'])
    for area, old in sorted(area_template.items()):
        row = file_asset(old, overlays/f'{area}.index', f'iee-assets/area-animation-pack/{area}.index')
        row['model'] = 'AreaAnimationArchiveSeekIndex-X4'
        retained.append(row)
        sources[payload(row)] = (ROOT/row['source'], None, row['bytes'], row['sha256'])
    ids = {row['component_id'] for row in area_template.values()}
    for component in components['components']:
        if component['id'] in ids:
            component['depends_on'].append(2999)
    components['components'].append(dict(id=2999, label='animation-shared-archive',
        name='Shared area animation archive (x4)', status='validated', depends_on=[0],
        payload_groups=['animation-shared-archive']))
    components['components'].sort(key=lambda row: row['id'])

    for name, info in read_json(EFFECT/'results-release.json')['files'].items():
        path = EFFECT/'pack-release'/name
        row = file_asset(effect_template, path, f'iee-assets/effects/{name}')
        if (row['bytes'], row['sha256']) != (info['bytes'], info['sha256'].upper()):
            raise ValueError(f'Shared effect file differs: {name}')
        row['model'] = 'EffectAnimationRuntimeV3SharedTiles'
        retained.append(row)
        sources[payload(row)] = (path, None, row['bytes'], row['sha256'])

    map_outputs = read_json(MAP/'results.json')['files']
    recipes = json.loads(maps.read('map-sharing-index.json'))
    pages = defaultdict(list)
    for old in map_pages:
        name = Path(old['destination']).name.upper()
        row = dict(old)
        if name in map_outputs:
            info = map_outputs[name]
            if info['baseline_sha256'].upper() != old['sha256']:
                raise ValueError(f'Map baseline changed: {name}')
            row.update(bytes=info['bytes'], sha256=info['sha256'].upper())
            if row['sha256'] != old['sha256']:
                row.update(source=relative(MAP/'run/shared-original-maps-test.zip'),
                           source_run=relative(MAP), model='SharedOriginalMapDecor-X4')
        pages[row['sha256']].append((row, old, recipes.get(name)))
        retained.append(row)
    for digest, candidates in pages.items():
        choice = next((item for item in candidates if item[2] is None or 'pvrz' in item[2]), candidates[0])
        row, old, recipe = choice
        path = f'{PREFIX}map-shared-pages/{digest}.PVRZ' if len(candidates)>1 or recipe else payload(row)
        if recipe is None:
            sources[path] = (base, payload(old), row['bytes'], digest)
        elif 'pvrz' in recipe:
            sources[path] = (maps, 'objects/'+recipe['pvrz'], row['bytes'], digest)
        else:
            def plane(part):
                key = recipe[part]
                member = 'objects/'+key
                plane_path = f'{PREFIX}map-shared-planes/{key}.bin'
                sources.setdefault(plane_path, (maps, member, maps.getinfo(member).file_size, key))
                return plane_path
            action = f"P {path} {row['bytes']} {digest} {plane('rgb')} {plane('alpha')} {recipe['pvr_header']}"
            for component in {item[0]['component_id'] for item in candidates}:
                transport[component].append(action)
        for item, _, _ in candidates:
            bindings[item['component_id'], item['destination']] = path

    manifest.update(generated_by='tools/build_optimized_candidate.py', entries=retained)
    release['version'] = VERSION
    release['manifest_files'] = [*release['manifest_files'], 'manifests/payload-layout.json']
    release['blocking_conditions'].append('optimized-payload-final-ingame-qa-pending')
    release['content_scope'].update(
        maps=release['content_scope']['maps'] + ' Mutualisation PVRZ et décors x1 identiques; QA finale en attente.',
        effects='Même sélection d’effets et porteurs natifs. IEETSHR1, 65849 frames physiques, 71971 références.',
        animations='234 zones, archive tuilée partagée et index par zone. Registres natifs conservés.',
        sprites=release['content_scope']['sprites'] + ' Tables de représentants compactées à la distribution.')
    dll = ENGINE/'InfinityEngine-Enhancer.dll'
    dll_size, dll_hash = physical(dll)
    checked = read_json(EFFECT/'runtime/installation.json')['renderer_sha256']
    if dll_hash != checked.upper():
        raise ValueError('Candidate renderer differs from the verified local DLL')
    renderer['bundle_id'] = 'iee-0.1.0-alpha.14-optimized-local'
    renderer['source_tree'] = 'git:3deb837d9:engine/InfinityEngine-Enhancer/source-patchee'
    for record in renderer['files']:
        if record['path'] == dll.name:
            record.update(bytes=dll_size, sha256=dll_hash)
    output = {
        MOD+'content.json': json_bytes(manifest),
        MOD+'components.json': json_bytes(components),
        MOD+'release.json': json_bytes(release),
        MOD+'renderer-bundle.json': json_bytes(renderer),
        MOD+'payload-layout.json': json_bytes({
            'schema_version': 1,
            'map_copy_sources': {f'{r["component_id"]}/{r["destination"]}': path for r in retained
                                 if (path := bindings.get((r['component_id'], r['destination']))) and path != payload(r)},
            'restoration_lists': {str(i): f'bg2hd/transport/{i}.tsv' for i in sorted(transport)},
            'area_archive_component': 2999,
        }),
        'bg2hd/bg2hd.tp2': build_tp2(base.read('bg2hd/bg2hd.tp2').decode(), retained, bindings, transport, ids),
        'BUILD-STATUS.txt': (f'BG2 HD Visual Project {VERSION}\nLOCAL CANDIDATE. Final ingame validation pending.\n').encode(),
    }
    for component, actions in transport.items():
        output[f'bg2hd/transport/{component}.tsv'] = ('\n'.join(actions) + '\n').encode()
    return sources, output, dll, manifest


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    base_sha = BASE.with_suffix('.zip.sha256').read_text(encoding='utf-8-sig').split()[0]
    sprite_path = proof(SPRITE/'run/sprite-compact-representatives-test.zip', read_json(SPRITE/'results.json')['compact_zip_sha256'])
    map_path = proof(MAP/'run/shared-original-maps-test.zip', read_json(MAP/'results.json')['pack_sha256'])
    extractor = DIST/'extractor-build/Release/Expand-BG2HDPayload.exe'
    pending = OUT.with_suffix('.partial')
    with ExitStack() as stack:
        base, sprite, maps = [stack.enter_context(ZipFile(path)) for path in (BASE, sprite_path, map_path)]
        base_checksums = {}
        for line in base.read('checksums.sha256').decode('utf-8-sig').splitlines():
            digest, name = line.split('  ', 1)
            base_checksums[name] = digest
        for name in ('content.json', 'components.json', 'release.json', 'renderer-bundle.json'):
            if sha(base.read(MOD+name)) != base_checksums[MOD+name].upper():
                raise ValueError(f'Baseline control file differs: {name}')
        sources, generated, renderer, manifest = assemble(base, sprite, maps)
        out = ArchiveBuilder(pending)
        stack.callback(out.close)
        effect_guard = 'bg2hd/tools/bg2hd-effect-storage.ps1'
        replacements = {HELPER: extractor, 'bg2hd/renderer/'+renderer.name: renderer,
                        effect_guard: RELEASE/effect_guard}
        skipped = set(generated) | set(replacements) | {'BUILD-MANIFEST.json', 'checksums.sha256'}
        for info in base.infolist():
            name = info.filename
            if name.startswith(PREFIX) or name in skipped:
                continue
            out.add(name, base.open(name), info.file_size, base_checksums[name])
        for name, path in replacements.items():
            out.add(name, path.open('rb'), path.stat().st_size)
        for name, data in generated.items():
            out.add(name, data)
        for i, (name, (source, member, size, expected)) in enumerate(sorted(sources.items()), 1):
            stream = source.open(member) if member else source.open('rb')
            out.add(name, stream, size, expected)
            if i%5000 == 0:
                print(f'{i}/{len(sources)} fichiers du payload empaquetés', flush=True)
        build_info = dict(schema_version=1, package_kind='local-alpha-not-public', version=VERSION,
            source_archive_sha256=base_sha.upper(), content_entries=len(manifest['entries']),
            archive_payload_files=len(sources), content_manifest_sha256=out.files[MOD+'content.json'][1],
            renderer_dll_sha256=out.files['bg2hd/renderer/'+renderer.name][1],
            installer_transport=['sprite-representatives-v1', 'map-PVRZ-shared-v1'],
            validated_in_game=False)
        out.add('BUILD-MANIFEST.json', json_bytes(build_info))
        checksums = ''.join(f'{record[1]}  {name}\n' for name, record in sorted(out.files.items()))
        out.add('checksums.sha256', checksums.encode())
    with ZipFile(pending) as archive:
        if len(archive.infolist()) != len(out.files):
            raise ValueError('Incomplete optimized archive')
    pending.rename(OUT)
    digest = file_hash(OUT)
    OUT.with_suffix('.zip.sha256').write_text(f'{digest}  {OUT.name}\n', encoding='ascii')
    manifests = DIST/'manifests'
    manifests.mkdir(exist_ok=False)
    for name, data in generated.items():
        if name.startswith(MOD):
            (manifests/Path(name).name).write_bytes(data)
    print(json.dumps(dict(archive_bytes=OUT.stat().st_size, alpha11_bytes=BASE.stat().st_size,
        net_savings_bytes=BASE.stat().st_size-OUT.stat().st_size, archive_sha256=digest,
        archive_entries=len(out.files), content_entries=len(manifest['entries'])), indent=2))


if __name__ == '__main__':
    main()
