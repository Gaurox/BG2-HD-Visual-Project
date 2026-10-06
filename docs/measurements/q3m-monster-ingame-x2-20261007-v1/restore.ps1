$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json';$receipt=Read-JsonFile $receiptPath
if($receipt.status -ne 'installed-pending-ingame-qa'){throw 'Installation is not active.'}
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
Assert-GameClosed
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
$catalog=Resolve-ChildPath $game $receipt.catalog_relative -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
Check $catalog $receipt.catalog_sha256;Check $backup $receipt.parent_catalog_sha256
foreach($r in $receipt.preserved_files){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
foreach($f in $receipt.created_files){Check (Resolve-ChildPath $game $f.relative_path -RequireExisting) $f.sha256}
Copy-FileAtomic $backup $catalog;Check $catalog $receipt.parent_catalog_sha256
foreach($f in $receipt.created_files){Remove-Item -LiteralPath (Resolve-ChildPath $game $f.relative_path -RequireExisting)}
$receipt.status='restored-parent';$receipt.restored_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $receiptPath $receipt
Write-Output 'Icewind accepted parent restored; only newly created Monster leaves/QMON fixtures removed. Installation tracking must be reconciled.'
