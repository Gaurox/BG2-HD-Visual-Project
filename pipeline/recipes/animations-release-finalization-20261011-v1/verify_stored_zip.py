"""Verify actual ZIP methods, not just the requested compression option."""
import json, sys, zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[1]) as z:
    entries=z.infolist()
    assert entries and all(e.compress_type==zipfile.ZIP_STORED for e in entries)
    manifest=json.loads(z.read('BUILD-MANIFEST.json'))
    assert manifest['zip_compression_level']=='NoCompression'
receipt=Path(__file__).with_name('zip-storage-verification.json')
assert not receipt.exists()
receipt.write_text(json.dumps(dict(entries=len(entries),method='ZIP_STORED',compression='NoCompression'),indent=2)+'\n',encoding='utf-8')
print('ZIP_STORED=PASSED',len(entries))
