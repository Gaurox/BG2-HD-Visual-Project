"""A newer DLL needs both an explicit binding and the exact acquired water fingerprint."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.scripts.verify_map_release_candidates import verify_renderer_continuity


class MapRendererSuccessorTests(unittest.TestCase):
    def test_successor_requires_explicit_binding_and_exact_water_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);registry=root/'registry.json';dll=root/'renderer.dll'
            raw=b'{"version":3,"entries":[]}\r\n';registry.write_bytes(raw)
            old='A'*64
            normalized=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest().upper()
            contract=f'IEE_WATER_ROUTE2_V1:{normalized}:3:188'
            dll.write_bytes(b'MZfixture'+contract.encode()+b'\0')
            runtime=dict(dll_sha256=old,registry_sha256=hashlib.sha256(raw).hexdigest().upper(),entries=188)
            successor=dict(inherited_from_dll_sha256=old,dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest().upper(),registry_sha256=runtime['registry_sha256'],build_contract=contract)
            with self.assertRaisesRegex(ValueError,'explicit compatible successor'):
                verify_renderer_continuity(dll,runtime,registry,{})
            verify_renderer_continuity(dll,runtime,registry,dict(renderer=dict(map_water_runtime=successor)))
            dll.write_bytes(b'MZfixtureIEE_WATER_ROUTE2_V1:'+b'0'*64+b':3:188\0')
            successor['dll_sha256']=hashlib.sha256(dll.read_bytes()).hexdigest().upper()
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                verify_renderer_continuity(dll,runtime,registry,dict(renderer=dict(map_water_runtime=successor)))


if __name__=='__main__':unittest.main()
