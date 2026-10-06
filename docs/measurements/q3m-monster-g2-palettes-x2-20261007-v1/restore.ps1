[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json';$receipt=Read-JsonFile $receiptPath
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
Assert-GameClosed
if($receipt.status -ne 'installed-G2-native-palettes-pending-ingame-qa'){throw 'Unexpected active installation.'}
$catalog=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
Check $catalog $receipt.catalog_sha256;Check $backup $baseline.parent_catalog_sha256
foreach($r in $receipt.created_leaves){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
if($DryRun){Write-Output 'Ready to restore MFIE-accepted catalog and remove only14 identified new G2 leaves;DLL preserved.';return}
Assert-GameClosed;Copy-FileAtomic $backup $catalog;Check $catalog $baseline.parent_catalog_sha256
foreach($r in $receipt.created_leaves){$p=Resolve-ChildPath $game $r.relative_path -RequireExisting;Check $p $r.sha256;Remove-Item -LiteralPath $p -Force}
$receipt.status='restored-parent';$receipt.restored_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $receiptPath $receipt
Write-Output 'Parent catalog restored;historical installation proof retained;reconcile active tracking if this restore is used.'
