"""Corrupt inputs must never enter a local sprite package."""
import copy
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verify_sprite_release_candidate as verifier


class SpriteReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        renderer = self.root / 'releases/BG2-HD-Upscale/bg2hd/renderer'
        renderer.mkdir(parents=True)
        dll = renderer / 'InfinityEngine-Enhancer.dll'
        dll.write_bytes(b'pinned-renderer')
        dll_hash = verifier.sha256(dll)
        self.write('releases/BG2-HD-Upscale/manifests/renderer-bundle.json', {'files': [{'path': dll.name, 'bytes': dll.stat().st_size, 'sha256': dll_hash}]})
        ids = [f'0x{0x1000+n:04X}' for n in range(15)]
        evidence = []
        for n, aid in enumerate(ids):
            p = self.write(f'qa/family-{n}.json', {'status': 'accepted', 'qa_state': 'passed', 'scope': {'animation_ids': [aid]}})
            evidence.append({'path': p.relative_to(self.root).as_posix(), 'sha256': verifier.sha256(p), 'kind': 'family-qa', 'animation_ids': [aid]})
        files = []
        self.index = {'animations': [{'animation_id': aid} for aid in ids], 'shards': []}
        for version in [6, 7, 9]:
            p = self.root / f'sprite/world/leaf-v{version}.registry'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(struct.pack('<8sII', b'IEECSXN\0', version, 2))
            record = {'source': p.relative_to(self.root).as_posix(), 'destination': f'iee-assets/creature-sprites/{p.name}', 'bytes': p.stat().st_size, 'sha256': verifier.sha256(p)}
            files.append(record)
            self.index['shards'].append({'registry': record['destination'], 'registry_bytes': record['bytes'], 'sha256': record['sha256']})
        p = self.root / 'sprite/world/CreatureSprites-XN.catalog'
        p.write_bytes(b'sealed-index')
        files.append({'source': p.relative_to(self.root).as_posix(), 'destination': f'iee-assets/creature-sprites/{p.name}', 'bytes': p.stat().st_size, 'sha256': verifier.sha256(p)})
        inventory = self.write('inventory/world.json', {'scale': 2, 'display_filter': 'Nearest', 'animation_ids': ids, 'files': files})
        self.register = {'candidates': [{'candidate_id': 'test', 'kind': 'sprite', 'approval_status': 'approved-for-release', 'runtime_contract': {'dll_sha256': dll_hash, 'filter': 'Nearest'}, 'source_pack': {'path': 'inventory/world.json', 'sha256': verifier.sha256(inventory)}, 'asset_scope': {'animation_ids': ids, 'file_count': len(files), 'bytes': sum(f['bytes'] for f in files)}, 'qa_approval': {'evidence': evidence}}]}
        self.catalog_patch = patch.object(verifier, 'read_sealed_catalog_index', return_value=self.index)
        self.catalog_patch.start()
        self.addCleanup(self.catalog_patch.stop)

    def write(self, relative, data):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding='utf-8')
        return p

    def test_acquired_mixed_versions_pass(self):
        self.assertEqual(verifier.verify(self.root, self.register)['sprite']['versions'], [6, 7, 9])

    def test_changed_leaf_bytes_fail_even_with_same_length(self):
        p = self.root / 'sprite/world/leaf-v6.registry'
        p.write_bytes(b'X' + p.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, 'payload differs'):
            verifier.verify(self.root, self.register)

    def test_qa_evidence_tampering_fails(self):
        (self.root / 'qa/family-0.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'evidence hash differs'):
            verifier.verify(self.root, self.register)

    def test_renderer_change_fails(self):
        (self.root / 'releases/BG2-HD-Upscale/bg2hd/renderer/InfinityEngine-Enhancer.dll').write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'Renderer payload differs'):
            verifier.verify(self.root, self.register)

    def test_declared_qa_cannot_expand_immutable_scope(self):
        register = copy.deepcopy(self.register)
        register['candidates'][0]['qa_approval']['evidence'][0]['animation_ids'].append('0x7FFF')
        with self.assertRaisesRegex(ValueError, 'Declared family IDs'):
            verifier.verify(self.root, register)

    def test_path_traversal_refused(self):
        with self.assertRaises(ValueError):
            verifier.contained(self.root, '../outside.registry')


if __name__ == '__main__':
    unittest.main()
