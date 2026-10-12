"""Pin the exact already accepted final oil stack, replacing the August-only contract."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'releases/BG2-HD-Upscale'
qa=json.loads((ROOT/'pipeline/water/manifests/ar0413-final-user-qa-20260928-v1.json').read_text())
p=R/'tools/Test-BG2HD-AR0413Contract.ps1';s=p.read_text(encoding='utf-8-sig')
start=s.index('$expectedSourceRun =');end=s.index('$release =',start)
block="$expectedSourceRun = 'maps/AR0413/runs/release-maps-20261012-v1/AR0413/05_build'\n# QA acquise 2026-09-28: ar0413-final-user-qa-20260928-v1.json; no new QA inferred.\n$expected = [ordered]@{\n"
for name,f in qa['live_files'].items():block+=f"    '{name}' = @{{ bytes = {f['bytes']}; sha256 = '{f['sha256']}' }}\n"
block+='}\n\n';s=s[:start]+block+s[end:]
s=s.replace("Write-Output 'AR0413_CANONICAL_CONTRACT=PASSED'", "Require ($rendererText.IndexOf('YFGPKI', [StringComparison]::Ordinal) -ge 0) 'La DLL ne porte pas le contrat huile final YFGPKI.'\nWrite-Output 'AR0413_CANONICAL_CONTRACT=PASSED (final 2026-09-28 oil stack, 22 files)'" )
p.write_text(s,encoding='utf-8',newline='\n')
print('AR0413 FINAL CONTRACT: 22 FILES')
