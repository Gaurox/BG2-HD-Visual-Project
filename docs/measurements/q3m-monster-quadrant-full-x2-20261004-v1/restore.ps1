$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receipt=Read-JsonFile (Join-Path $PSScriptRoot 'ingame-installation/active-test.json')
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
Assert-GameClosed
function Check([string]$p,[string]$sha){if((Get-FileSha256 $p) -ne $sha.ToUpperInvariant()){throw "Identity differs: $p"}}
$catalog=Resolve-ChildPath $game $receipt.catalog_relative -RequireExisting
$dll=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
Check $catalog $receipt.catalog_sha256;Check $dll $receipt.dll_sha256
$beforeCatalog=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
$beforeDll=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
Check $beforeCatalog $receipt.parent_catalog_sha256;Check $beforeDll $receipt.parent_dll_sha256
foreach($f in $receipt.preserved_files){Check (Resolve-ChildPath $game $f.relative_path -RequireExisting) $f.sha256}
Copy-FileAtomic $beforeDll $dll;Copy-FileAtomic $beforeCatalog $catalog
foreach($f in $receipt.fixtures){$p=Resolve-ChildPath $game $f.target -RequireExisting;Check $p $f.sha256;Remove-Item -LiteralPath $p}
Check $catalog $receipt.parent_catalog_sha256;Check $dll $receipt.parent_dll_sha256
Write-JsonAtomic (Join-Path $PSScriptRoot 'restoration-verification.json') ([ordered]@{status='restored-parent';catalog_sha256=$receipt.parent_catalog_sha256;dll_sha256=$receipt.parent_dll_sha256;restored_at_utc=[DateTime]::UtcNow.ToString('o');ingame_QA=$false})
