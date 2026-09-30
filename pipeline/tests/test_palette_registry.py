from __future__ import annotations
import copy
import hashlib
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"pipeline/scripts"))
import palette_registry as v6
import run_creature_sprite_x2 as pipeline
from reboutcx_catalog import resource_contract_digest


def resource(*,fraction=3,index=4):
    i = np.full((4,4),index,np.uint8)
    reps = np.full(256,65535,np.uint16)
    reps[4] = 0  # Successor5 has no native representative, deliberately.
    return dict(resref="TEST",source_sha256="12"*32,cycles=[[0,0],[]],frames=[dict(
        geometry=(2,2,-3,5,0),representatives=reps,I=i,F=np.full_like(i,fraction),guide=i.copy())])


class PaletteRegistryTests(unittest.TestCase):
    def test_raw_roundtrip_profiles_geometry_cycles_absent_representative(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"test.registry"
            v6.write(p,2,[resource()],compress=False)
            d=v6.inspect(p,include_frames=True,include_resource_records=True)
            self.assertEqual((d["version"],d["class_profile_id"],d["decode_rule_id"]),(6,1,1))
            f=d["frame_data"][0]["frames"][0]
            self.assertEqual(f["geometry"],(2,2,-3,5,0))
            self.assertEqual(f["dep"],bytes([0x30])+bytes(31))
            self.assertEqual(f["F"],bytes([3])*16)
            self.assertEqual(d["frame_data"][0]["cycles"],[[0,0],[]])
            self.assertEqual(pipeline.inspect_registry(p)["sha256"],d["sha256"])

    def test_absent_and_explicit_zero_f_identity_and_dependencies(self):
        with tempfile.TemporaryDirectory() as td:
            for explicit in (False,True):
                p=Path(td)/str(explicit)
                v6.write(p,2,[resource(fraction=0)],compress=False,retain_zero_f=explicit)
                d=v6.inspect(p,include_frames=True)
                f=d["frame_data"][0]["frames"][0]
                self.assertEqual(f["F"],bytes(16) if explicit else b"")
                self.assertEqual(f["dep"],bytes([0x10])+bytes(31))

    def test_semantic_guide_and_source_offsets_checked_by_writer(self):
        for mutate in (lambda r:r["frames"][0].pop("guide"),
                       lambda r:r["frames"][0]["guide"].fill(16),
                       lambda r:r["frames"][0]["representatives"].__setitem__(4,4)):
            with tempfile.TemporaryDirectory() as td:
                r=resource(); mutate(r)
                p=Path(td)/"test"
                with self.assertRaises((RuntimeError,ValueError)):
                    v6.write(p,2,[r],compress=False)
                self.assertFalse(p.exists());self.assertFalse(p.with_name("test.part").exists())

    def test_rejects_bad_masks_fractions_flags_profiles_counts_and_sizes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"base"
            v6.write(p,2,[resource()],compress=False)
            raw=p.read_bytes(); frame=32+48; ip=frame+568; fp=ip+16
            mutations=[(24,struct.pack("<I",2)),(28,struct.pack("<I",2)),
                       (12,struct.pack("<I",3)),(20,struct.pack("<I",0x6110)),
                       (72,struct.pack("<I",4097)),(frame,b"\0\0"),
                       (frame+8,b"\1"),(frame+9,b"\2"),(frame+10,b"\2"),
                       (frame+11,b"\1"),(frame+12,struct.pack("<I",15)),
                       (frame+528,b"\x10"),(frame+528,b"\x70"),
                       (frame+560,struct.pack("<I",15)),(frame+564,b"\2"),
                       (frame+565,b"\1"),(fp,b"\x08")]
            for offset,value in mutations:
                bad=bytearray(raw);bad[offset:offset+len(value)]=value
                q=Path(td)/"bad";q.write_bytes(bad)
                with self.subTest(offset=offset,value=value),self.assertRaises(RuntimeError):
                    v6.inspect(q)
            for bad in (raw[:20],raw[:28],raw[:200],raw[:ip+3],raw[:fp+3],raw[:-1],raw+b"x"):
                q.write_bytes(bad)
                with self.assertRaises(RuntimeError):v6.inspect(q)

    def test_special_and_terminal_nonzero_f_rejected(self):
        for i in (0,1,2,3,15,27,87,95,255):
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(ValueError):
                    v6.write(Path(td)/"bad",2,[resource(index=i)],compress=False)

    @unittest.skipUnless(os.name=="nt","XPRESS_HUFF is a Windows codec")
    def test_compression_changes_storage_not_logical_identity(self):
        with tempfile.TemporaryDirectory() as td:
            r=resource(); f=r["frames"][0]
            f["geometry"]=(64,64,-3,5,0)
            for key in ("I","F","guide"):f[key]=np.full((128,128),3 if key=="F" else 4,np.uint8)
            records=[]
            for compress in (False,True):
                p=Path(td)/str(compress)
                info=v6.write(p,2,[r],compress=compress)
                records.append(info["resource_records"][0])
            a,b=records
            self.assertGreater(a["bytes"],b["bytes"])
            self.assertEqual(resource_contract_digest(a),resource_contract_digest(b))
            self.assertEqual(pipeline.catalog_source_component_sha256(2,[a]),pipeline.catalog_source_component_sha256(2,[b]))
            r["frames"][0]["F"].fill(2)
            c=v6.write(Path(td)/"different",2,[r],compress=True)["resource_records"][0]
            self.assertNotEqual(resource_contract_digest(b),resource_contract_digest(c))

    def test_catalog_scopes_shared_resref_and_preserves_complete_cycles(self):
        with tempfile.TemporaryDirectory() as td:
            a=resource();b=copy.deepcopy(a);b["frames"][0]["F"].fill(2)
            animations=[dict(animation_id="0x6110",owner=1,component_indices=[0]),
                        dict(animation_id="0x6111",owner=1,component_indices=[1])]
            d=v6.write_catalog(Path(td)/"catalog",2,[[a],[b]],animations=animations,compress=False)
            checked=pipeline.inspect_registry_catalog(Path(td)/"catalog"/pipeline.XN_REGISTRY_CATALOG_FILENAME)
            self.assertEqual(checked["shard_registry_version"],6)
            self.assertEqual(d["animation_resources"],{"0x6110":["TEST"],"0x6111":["TEST"]})
            self.assertEqual(d["total_frames"],2)

    def test_catalog_profile_rejects_other_owner_and_duplicate_scope(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                v6.write_catalog(Path(td)/"bad",2,[[resource()]],
                    animations=[dict(animation_id="0xE400",owner=2,component_indices=[0])],compress=False)
            with self.assertRaises(RuntimeError):
                v6.write_catalog(Path(td)/"duplicate",2,[[resource()],[resource(fraction=2)]],compress=False)

    def test_existing_outputs_and_legacy_producer_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"existing";p.write_bytes(b"preserve")
            with self.assertRaises(RuntimeError):v6.write(p,2,[resource()],compress=False)
            self.assertEqual(p.read_bytes(),b"preserve")
            q=Path(td)/"v6";info=v6.write(q,2,[resource()],compress=False)
            with self.assertRaises(RuntimeError):
                pipeline.write_compressed_catalog_registry_records(Path(td)/"legacy",2,info["resource_records"])
            self.assertFalse((Path(td)/"legacy").exists())
            with self.assertRaises(RuntimeError):
                pipeline.write_registry_records(Path(td)/"legacy-raw",pipeline.XN_REGISTRY_MAGIC,
                                                3,2,0x6110,info["resource_records"])
            self.assertFalse((Path(td)/"legacy-raw").exists())


if __name__=="__main__":unittest.main()
