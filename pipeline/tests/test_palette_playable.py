"""CPU integration: queue, durable reuse, native metadata, V6 and fail-closed cases."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zlib
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import analyze_playable_frame_dedup as analysis
import palette_playable as pipeline
import palette_frac_encode as encoder
import palette_registry as v6
from palette_work_plan import WorkPlan, ResultCache, POINTER_SCHEMA, file_sha
import run_creature_sprite_x2 as registry


class FakeProcessor:
    calls = []
    def __init__(self, plan, cache, workers):
        self.plan, self.cache, self.stats = plan, cache, Counter()
        self.pool = ThreadPoolExecutor(max_workers=1)

    def process(self, frames):
        for frame in frames:
            self.calls.append(self.plan.key(frame))
            guide = np.repeat(np.repeat(frame.indices, self.cache.scale, 0), self.cache.scale, 1)
            f = np.where(guide == 4, 3, 0).astype(np.uint8)
            self.cache.save(frame, dict(guide=guide, I=guide, F=f, dep=encoder.dependency_mask(guide, f)))


class PlayablePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.database = self.root / "plan.sqlite"
        self.pointer = self.root / "active.json"
        self.palette = np.zeros((256, 4), np.uint8)
        self.palette[:, :3] = np.arange(768, dtype=np.uint16).reshape(256, 3).astype(np.uint8)
        self.rgb = self.palette[:, [2, 1, 0]].copy()
        self.planes = [np.array([[0, 4], [5, 4]], np.uint8), np.array([[0, 4], [4, 5]], np.uint8), np.array([[2]], np.uint8)]
        self.keys = []
        db = sqlite3.connect(self.database)
        db.executescript(analysis.DDL)
        self.profile = dict(namespace_by_scale={"2": "22" * 32, "4": "44" * 32}, inference={"test": True},
                            code_sha256={"palette_frac_encode.py":file_sha(ROOT/'pipeline/scripts/palette_frac_encode.py')},
                            fitting_rgb_sha256=hashlib.sha256(np.stack([self.rgb] * 6).tobytes()).hexdigest())
        for k, v in dict(schema=analysis.SCHEMA, status="complete-source-analysis-not-generated", profile=self.profile,
                         contract={"test": "actual indexed identity"}, source_pins={}).items():
            analysis.put_meta(db, k, v)
        for mid, animation in enumerate(("0x6010", "0x6110")):
            db.execute("INSERT INTO models VALUES(?,?,?,?)", (mid, animation, "TEST", "{}"))
            db.execute("INSERT INTO families VALUES(?,?,?,?,?,?,?,?)", (f'f{mid}', mid, 'body' if mid == 0 else 'weapon', 'v', '1', 'TEST', 'available', '{}'))
        for rid in (0, 1):
            db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (rid, f'TEST{rid}', 'source', 'stock', f'{rid+1:02x}'*32, '03'*32, self.palette.tobytes(), 'p', 0, 3, 2, 3, '{}'))
            db.execute("INSERT INTO model_resources VALUES(?,?)", (rid, rid))
            db.execute("INSERT INTO family_resources VALUES(?,?)", (f'f{rid}', rid))
        for wid, plane in enumerate(self.planes):
            h, w = plane.shape
            ik, wk, raw, used, needs = analysis.identities(plane, self.rgb, 0)
            self.keys.append(wk.hex())
            db.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (wid, ik, w, h, 0, w*h, 32, 32, int(needs), 1, zlib.compress(raw)))
            db.execute("INSERT INTO work_items VALUES(?,?,?,?,?,?,?,?,?,?,?)", (wid, wk, wid, used, 0, wid, 2, 2, 2, b'\3', 1))
        for rid in (0, 1):
            for fi in range(3):
                db.execute("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?)", (rid, fi, fi, -3-rid, 5+rid, 0, 0, int(fi < 2)))
            db.execute("INSERT INTO cycles VALUES(?,?,?,?,?)", (rid, 0, 7, 3, struct.pack('<3H',1,0,1)))
            db.execute("INSERT INTO cycles VALUES(?,?,?,?,?)", (rid, 1, 10, 0, b''))
        for i in range(6):
            db.execute("INSERT INTO profile_palettes VALUES(?,?,?,?)", (i, f'P{i}', self.rgb.tobytes(), hashlib.sha256(self.rgb.tobytes()).hexdigest()))
        db.commit();db.close()
        self.pointer.write_text(json.dumps(dict(schema=POINTER_SCHEMA, path='plan.sqlite', bytes=self.database.stat().st_size, sha256=file_sha(self.database))))
        self.plan = WorkPlan(self.pointer, root=self.root)
        FakeProcessor.calls.clear()

    def tearDown(self):
        self.plan.close()
        self.tmp.cleanup()

    def produce(self, ids=None, scale=4):
        cache = ResultCache(self.plan, scale, self.root / 'cache')
        with cache.exclusive():
            result = pipeline.produce(self.plan, cache, ids, processor_factory=FakeProcessor)
        return cache, result

    def test_global_and_per_model_runs_share_a_single_durable_result(self):
        cache, first = self.produce(['0x6010'])
        self.assertEqual(first['selected_unique_work'], 3)
        self.assertEqual(first['new_unique_results'], 2)
        self.assertEqual(first['special_unique_results'], 1)
        _, second = self.produce(['0x6110'])
        self.assertEqual(second['reused_unique_results'], 3)
        self.assertEqual(len(FakeProcessor.calls), 2)
        _, third = self.produce()  # New producer call / result loads: no in-memory ticket reuse.
        self.assertEqual(third['reused_unique_results'], 3)
        self.assertEqual(len(list(cache.directory.glob('*.npz'))), 3)

    def test_warm_cache_does_not_initialize_gpu_processor(self):
        cache, _ = self.produce()
        with cache.exclusive():
            result = pipeline.produce(self.plan, cache, processor_factory=mock.Mock(side_effect=AssertionError('GPU initialized')))
        self.assertEqual(result['reused_unique_results'], 3)

    def test_scales_are_separate_and_metadata_survives_fanout(self):
        a, _ = self.produce(scale=2)
        b, _ = self.produce(scale=4)
        self.assertNotEqual(a.directory, b.directory)
        resources = self.plan.resources()
        ra, rb = [self.plan.materialize(r, b) for r in resources]
        self.assertEqual(ra['source_sha256'], '01'*32)
        self.assertEqual(rb['source_sha256'], '02'*32)
        self.assertEqual(ra['cycles'], [[1,0,1], []])
        self.assertEqual(rb['cycles'], ra['cycles'])
        self.assertEqual(ra['frames'][0]['geometry'], (2,2,-3,5,0))
        self.assertEqual(rb['frames'][0]['geometry'], (2,2,-4,6,0))
        np.testing.assert_array_equal(ra['frames'][0]['I'], rb['frames'][0]['I'])
        np.testing.assert_array_equal(ra['frames'][0]['representatives'], rb['frames'][0]['representatives'])
        self.assertEqual(ra['frames'][0]['representatives'][4], 1)

    def test_pack_uses_existing_results_and_preserves_V6_routes_source_geometry(self):
        cache, _ = self.produce()
        output = self.root / 'pack'
        with cache.exclusive(), mock.patch.object(pipeline, 'SharedPixelProcessor', side_effect=AssertionError('GPU initialized')):
            result = pipeline.pack(self.plan, cache, output)
        catalog = registry.read_sealed_catalog_index(output / registry.XN_REGISTRY_CATALOG_FILENAME, result['sha256'])
        self.assertEqual({(r['animation_id'],r['resref']) for r in catalog['directory']}, {('0x6010','TEST0'),('0x6110','TEST1')})
        self.assertEqual(len(catalog['shards']), 2)
        files = list(output.glob('*.registry'))
        native = {r['resref']:r for f in files for r in v6.inspect(f,include_frames=True)['frame_data']}
        self.assertEqual(native['TEST1']['cycles'], [[1,0,1],[]])
        self.assertEqual(native['TEST1']['frames'][0]['geometry'], (2,2,-4,6,0))
        self.assertEqual(native['TEST0']['source_sha256'],'01'*32)
        self.assertEqual(native['TEST1']['source_sha256'],'02'*32)
        self.assertEqual(native['TEST0']['frames'][0]['I'],native['TEST1']['frames'][0]['I'])
        self.assertNotEqual(native['TEST0']['frames'][0]['F'],b'')

    def test_corrupt_dependency_or_fraction_never_becomes_cache_hit(self):
        cache, _ = self.produce()
        frame = self.plan.frame(next(self.plan.work_rows()))
        original = cache.load(frame)
        for name,value in (('dep',np.zeros(32,np.uint8)),('F',np.full_like(original['F'],8))):
            arrays = {k:v.copy() for k,v in original.items()};arrays[name]=value
            with cache.path(frame).open('wb') as f:np.savez_compressed(f,**arrays)
            with self.assertRaisesRegex(ValueError,'invalid shared result'):cache.contains(frame)
        with cache.path(frame).open('wb') as f:f.write(b'PK truncated')
        with self.assertRaisesRegex(ValueError,'invalid shared result'):cache.contains(frame)

    def test_recipe_mismatch_and_concurrent_writers_are_rejected(self):
        cache, _ = self.produce()
        with cache.exclusive():
            with self.assertRaisesRegex(ValueError,'another Q3m producer'):
                with ResultCache(self.plan,4,self.root/'cache').exclusive():pass
        (cache.root/'recipe.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'profile changed'):
            with cache.exclusive():pass

    def test_unknown_source_or_RGBA_mismatch_never_uses_shared_result(self):
        frame = self.plan.frame(next(self.plan.work_rows()))
        frame.rgba = bytes(len(frame.rgba))
        with self.assertRaisesRegex(ValueError,'RGBA differs'):self.plan.key(frame)
        with self.assertRaisesRegex(ValueError,'outside'):list(self.plan.work_rows(['0x6400']))

    def test_missing_plan_or_changed_database_cannot_fall_back_to_old_runner(self):
        p = self.root/'missing.json'
        d=json.loads(self.pointer.read_text());d['path']='missing.sqlite';p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'cannot bypass'):WorkPlan(p,root=self.root)
        d['path']='plan.sqlite';d['sha256']='00'*32;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'file changed'):WorkPlan(p,root=self.root)

    def test_pack_requires_complete_results_before_creating_output(self):
        output = self.root/'no-pack'
        with self.assertRaisesRegex(ValueError,'results incomplete'):
            pipeline.pack(self.plan,ResultCache(self.plan,4,self.root/'cache'),output)
        self.assertFalse(output.exists())

    def test_same_BAM_shared_by_models_is_written_once_with_two_routes(self):
        self.plan.close()
        db=sqlite3.connect(self.database)
        db.execute('INSERT INTO model_resources VALUES(1,0)')
        db.execute("INSERT INTO family_resources VALUES('f1',0)")
        db.commit();db.close()
        descriptor=json.loads(self.pointer.read_text());descriptor.update(bytes=self.database.stat().st_size,sha256=file_sha(self.database))
        self.pointer.write_text(json.dumps(descriptor))
        self.plan=WorkPlan(self.pointer,root=self.root)
        cache,_=self.produce()
        output=self.root/'shared-BAM'
        with cache.exclusive():result=pipeline.pack(self.plan,cache,output)
        catalog=registry.read_sealed_catalog_index(output/registry.XN_REGISTRY_CATALOG_FILENAME,result['sha256'])
        routes=[r for r in catalog['directory'] if r['resref']=='TEST0']
        self.assertEqual({r['animation_id'] for r in routes},{'0x6010','0x6110'})
        self.assertEqual(len({r['component_index'] for r in routes}),1)
        self.assertEqual(len(catalog['shards']),2)
        self.assertEqual(len(FakeProcessor.calls),2)

    def test_source_pin_change_is_rejected_before_processing(self):
        source=self.root/'asset.bin';source.write_bytes(b'source')
        self.plan.meta['source_pins']={'asset.bin':file_sha(source)}
        source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'source changed'):self.plan.validate_sources()

    def test_shared_adapter_changes_identity_and_keeps_proven_pixel_process(self):
        self.assertIs(pipeline.SharedPixelProcessor.process,pipeline.PixelProcessor.process)
        self.assertIs(pipeline.SharedPixelProcessor.encode,pipeline.PixelProcessor.encode)
        adapter=pipeline.SharedPixelProcessor.__new__(pipeline.SharedPixelProcessor)
        adapter.plan=self.plan
        row=next(self.plan.work_rows());frame=self.plan.frame(row)
        self.assertEqual(adapter.key(frame),row['work_key'])

    def seed_fixture(self):
        cache,_=self.produce()
        run=self.root/'legacy';(run/'work/leaves').mkdir(parents=True);(run/'work/encoded').mkdir()
        resource=self.plan.resources(['0x6010'])[0]
        materialized=self.plan.materialize(resource,cache)
        leaf=run/'work/leaves/TEST0.registry'
        info=v6.write(leaf,4,[materialized])
        recipe=dict(animation_id='0x6010',scale=4,method='Q3m',k=6,boundary_mixing=False,dithering=False,
                    inference=self.plan.profile['inference'],palettes=json.loads(analysis.ANCHOR.read_text())['palettes'])
        context=hashlib.sha256(json.dumps(recipe['inference'],sort_keys=True).encode()+self.plan.fitting().tobytes()+b'/direct-x4').digest()
        for row in self.plan.work_rows():
            frame=self.plan.frame(row,resref='TEST0',index=row['representative_frame_index'],centre=(-3,5),palette_bgra=resource['palette_bgra'])
            key=pipeline.frame_key(frame,None,context).hex()
            with (run/'work/encoded'/f'{key}.npz').open('wb') as f:np.savez_compressed(f,**cache.load(frame))
        coverage=dict(resources=[dict(resref='TEST0',source_sha256=resource['canonical_sha256'],registry_sha256=info['sha256'])])
        for name,obj in (('recipe.json',recipe),('coverage.json',coverage)):(run/name).write_text(json.dumps(obj))
        proof=dict(status='passed-offline-ready-for-manual-game',scale=4,method='Q3m',k=6,boundary_mixing=False,dithering=False,
                   recipe_sha256=file_sha(run/'recipe.json'),coverage_sha256=file_sha(run/'coverage.json'),
                   source_sha256={'pipeline/scripts/palette_frac_encode.py':self.plan.profile['code_sha256']['palette_frac_encode.py']})
        (run/'verification.json').write_text(json.dumps(proof))
        record=dict(path='legacy',sha256={n:file_sha(run/n) for n in ('recipe.json','coverage.json','verification.json')})
        return run,record

    def test_seed_adopts_verified_V6_data_without_neural_reprocessing(self):
        run,record=self.seed_fixture();calls=len(FakeProcessor.calls)
        target=ResultCache(self.plan,4,self.root/'seed-cache')
        with target.exclusive():
            seeded=pipeline.seed_verified_run(self.plan,target,record)
            self.assertEqual(seeded['seeded_unique_results'],3)
            result=pipeline.produce(self.plan,target,processor_factory=mock.Mock(side_effect=AssertionError('GPU initialized')))
        self.assertEqual(result['reused_unique_results'],3)
        self.assertEqual(len(FakeProcessor.calls),calls)

    def test_seed_rejects_single_palette_old_method_and_unverified_loose_bytes(self):
        run,record=self.seed_fixture()
        recipe=json.loads((run/'recipe.json').read_text());recipe['method']='Q0'
        (run/'recipe.json').write_text(json.dumps(recipe));record['sha256']['recipe.json']=file_sha(run/'recipe.json')
        target=ResultCache(self.plan,4,self.root/'rejected-seed')
        with target.exclusive(),self.assertRaisesRegex(ValueError,'current Q3m'):
            pipeline.seed_verified_run(self.plan,target,record)
        run,record=self.seed_fixture_again(run)
        path=next((run/'work/encoded').glob('*.npz'))
        with np.load(path,allow_pickle=False) as z:arrays={n:z[n].copy() for n in z.files}
        arrays['F']=np.zeros_like(arrays['F']) if np.any(arrays['F']) else np.ones_like(arrays['F'])
        with path.open('wb') as f:np.savez_compressed(f,**arrays)
        with target.exclusive(),self.assertRaisesRegex(ValueError,'differs from verified leaf'):
            pipeline.seed_verified_run(self.plan,target,record)

    def seed_fixture_again(self,run):
        # Restore exactly the trusted metadata rather than recreate historical files.
        recipe=json.loads((run/'recipe.json').read_text());recipe['method']='Q3m';(run/'recipe.json').write_text(json.dumps(recipe))
        proof=json.loads((run/'verification.json').read_text());proof['recipe_sha256']=file_sha(run/'recipe.json')
        (run/'verification.json').write_text(json.dumps(proof))
        return run,dict(path='legacy',sha256={n:file_sha(run/n) for n in ('recipe.json','coverage.json','verification.json')})

    def test_corrupt_NPY_header_is_rejected_before_array_allocation(self):
        cache,_=self.produce();frame=self.plan.frame(next(self.plan.work_rows()));arrays=cache.load(frame)
        with zipfile.ZipFile(cache.path(frame),'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,array in arrays.items():
                stream=io.BytesIO()
                if name=='I':
                    np.lib.format.write_array_header_1_0(stream,dict(descr='|u1',fortran_order=False,shape=(1<<40,)))
                else:np.save(stream,array,allow_pickle=False)
                archive.writestr(name+'.npy',stream.getvalue())
        with mock.patch('palette_work_plan.np.load',side_effect=AssertionError('allocated from corrupt header')):
            with self.assertRaisesRegex(ValueError,'invalid shared result'):cache.load(frame)


if __name__ == '__main__':
    unittest.main()
