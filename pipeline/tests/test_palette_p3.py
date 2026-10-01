from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"pipeline/scripts"))
import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_p2 import component_catalog, v5_from_raw_v6
from palette_p3 import verify_capture
from palette_p3_catalog import derive, record_sha
from test_palette_registry import resource


class PaletteP3Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        r=resource(fraction=0)
        info=v6.write(self.root/"zero",2,[r],compress=False)
        raw=(self.root/"zero").read_bytes()
        # Parent has two resources in a shared V5 component.
        first=v5_from_raw_v6(raw,resref="TEST")
        second=v5_from_raw_v6(raw,resref="KEEP")
        parent=first[:24]+first[24:]+second[24:]
        parent=bytearray(parent);struct.pack_into("<I",parent,16,2)
        source=self.root/"parent-shard";source.write_bytes(parent)
        checked=registry.inspect_registry(source,include_resource_records=True)
        self.parent=self.root/"parent";self.parent.mkdir()
        leaf=self.parent/registry.catalog_shard_filename(checked["sha256"]);source.rename(leaf)
        checked=registry.inspect_registry(leaf,include_resource_records=True)
        entry=registry.catalog_shard_entry_bytes(checked,leaf)
        component=dict(index=0,digest=registry.catalog_component_digest(2,[entry]),shard_start=0,shard_count=1,
            **{k:checked[k] for k in ("resource_count","frame_count","index_bytes","registry_bytes")})
        animations=[dict(animation_id=a,owner=1,component_indices=[0]) for a in ("0x6110","0x6115")]
        rows=[dict(animation_id=a["animation_id"],resref=r,component_index=0,shard_index=0,resource_ordinal=n)
              for a in animations for n,r in enumerate(checked["resources"])]
        self.catalog=self.parent/registry.XN_REGISTRY_CATALOG_FILENAME
        out=registry.write_registry_catalog_index(self.catalog,2,animations,[component],[checked],rows,
            [registry.catalog_source_component_sha256(2,sorted(checked["resource_records"],key=lambda r:r["resref"]))],dict(shard_registry_version=5))
        self.manifest=dict(registry_catalog_sha256=out["sha256"],
            registry_catalog_logical_component_digests=out["logical_component_digests"],
            storage=dict(shard_registry_version=5,**{k:checked[k] for k in
                ("stored_index_bytes","compressed_frame_count","raw_frame_count")}))
        self.replacement=self.root/"replacement"
        v6.write(self.replacement,2,[resource()],compress=False)
        self.destination=self.root/"derived"

    def tearDown(self):
        self.temp.cleanup()

    def test_derived_catalog_preserves_other_actors_and_residual_bytes(self):
        out,proof=derive(self.catalog,self.manifest,self.replacement,self.destination)
        checked=registry.inspect_registry_catalog(self.destination/registry.XN_REGISTRY_CATALOG_FILENAME)
        self.assertEqual(checked["animation_resources"],{"0x6110":["KEEP","TEST"],"0x6115":["TEST","KEEP"]})
        self.assertEqual(checked["shard_registry_versions"],[5,6])
        self.assertEqual(proof["unchanged_animations"],1)
        self.assertEqual(proof["new_shards"],2)
        self.assertTrue(proof["unrelated_routes_identical"])
        old=registry.inspect_registry(next(self.parent.glob("*.registry")),include_resource_records=True)
        keep=next(r for r in old["resource_records"] if r["resref"]=="KEEP")
        self.assertEqual(proof["residual_records"],[dict(resref="KEEP",sha256=record_sha(keep))])
        with self.assertRaises(ValueError):derive(self.catalog,self.manifest,self.replacement,self.destination)

    def test_source_geometry_difference_rejected(self):
        r=resource();r["frames"][0]["geometry"]=(2,2,0,0,0)
        changed=self.root/"changed";v6.write(changed,2,[r],compress=False)
        with self.assertRaisesRegex(ValueError,"geometry/cycles"):
            derive(self.catalog,self.manifest,changed,self.destination)

    def test_complete_replacement_accepts_multiple_bounded_leaves(self):
        r=resource(fraction=0);r["resref"]="KEEP"
        other=self.root/"replacement-keep";v6.write(other,2,[r],compress=False)
        _,proof=derive(self.catalog,self.manifest,[self.replacement,other],self.destination)
        checked=registry.inspect_registry_catalog(self.destination/registry.XN_REGISTRY_CATALOG_FILENAME)
        self.assertEqual(checked["animation_resources"]["0x6110"],["TEST","KEEP"])
        self.assertEqual(checked["animation_resources"]["0x6115"],["TEST","KEEP"])
        self.assertEqual(proof["replaced_resrefs"],["KEEP","TEST"])
        self.assertEqual(proof["residual_records"],[])
        self.assertEqual(proof["new_shards"],2)

    def test_duplicate_replacement_leaves_rejected_before_output(self):
        with self.assertRaisesRegex(ValueError,"Duplicate replacement"):
            derive(self.catalog,self.manifest,[self.replacement,self.replacement],self.destination)
        self.assertFalse(self.destination.exists())

    def test_capture_requires_correlated_hd_substitution_and_routes_by_catalog(self):
        derive(self.catalog,self.manifest,self.replacement,self.destination)
        colors=[0]*256;colors[4]=0x4d000000;colors[5]=0xff505050
        fingerprint=1469598103934665603
        encoded=b"".join(w.to_bytes(4,"little") for w in (0x1908,0x1401,1,1))
        encoded+=b"\x04"+colors[4].to_bytes(4,"little")+b"\x05"+colors[5].to_bytes(4,"little")
        for byte in encoded:fingerprint=((fingerprint^byte)*1099511628211)&((1<<64)-1)
        crc=zlib.crc32(struct.pack("<16I",*([0x4d1e1e1e]*16)))
        line=(f"Q3M_P3_PALETTE animation=6110 generation=9 cell=123 layer=0 resref=TEST "
              f"sequence=0 slot=0 frame=0 format=1908 type=1401 decoded=true pixels=16 "
              f"crc32={crc:08X} fingerprint={fingerprint:016X} colors="+"".join(f"{c:08X}" for c in colors)+"\n")
        log=self.root/"capture.log";report=self.root/"capture.json";log.write_text(line)
        with self.assertRaises(SystemExit):verify_capture(self.destination,log,report)
        self.assertEqual(json.loads(report.read_text())["status"],"passed-cpu-only")
        log.write_text(line+"Q3M_P3_DRAW animation=6110 generation=8 replacementBound=true layers=4 incomplete=false\n")
        with self.assertRaises(SystemExit):verify_capture(self.destination,log,self.root/"wrong-generation.json")
        log.write_text(line+"Q3M_P3_DRAW animation=6110 generation=9 replacementBound=true layers=4 incomplete=false\n")
        verify_capture(self.destination,log,self.root/"success.json")
        result=json.loads((self.root/"success.json").read_text())
        self.assertEqual(result["status"],"passed-cpu-and-hd-substitution")
        self.assertEqual(result["fractional_generations_with_hd_substitution"],1)


if __name__=="__main__":unittest.main()
