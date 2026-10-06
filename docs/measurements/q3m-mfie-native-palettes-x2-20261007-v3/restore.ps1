[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
Assert-GameClosed
if($receipt.status -ne 'installed-MFIE-native-palettes-pending-ingame-qa'){throw 'Unexpected active installation.'}
$dll=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$catalog=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$backupDll=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
$backupCatalog=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
Check $dll $receipt.dll_sha256;Check $catalog $receipt.catalog_sha256
Check $backupDll $baseline.parent_dll_sha256;Check $backupCatalog $baseline.parent_catalog_sha256
foreach($r in $receipt.created_leaves){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
if($DryRun){Write-Output 'Ready to restore parent DLL/catalog and remove only six identified v3 leaves.';return}
Assert-GameClosed;Copy-FileAtomic $backupDll $dll;Copy-FileAtomic $backupCatalog $catalog
Check $dll $baseline.parent_dll_sha256;Check $catalog $baseline.parent_catalog_sha256
foreach($r in $receipt.created_leaves){$p=Resolve-ChildPath $game $r.relative_path -RequireExisting;Check $p $r.sha256;Remove-Item -LiteralPath $p -Force}
$receipt.status='restored-parent';$receipt.restored_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $receiptPath $receipt
Write-Output 'Parent restored; historical installation proof retained; reconcile active tracking if this restore is used.'
