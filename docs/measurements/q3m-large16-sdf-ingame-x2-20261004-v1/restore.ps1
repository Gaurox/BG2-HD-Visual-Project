$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
if($receipt.status -ne 'installed-pending-ingame-qa'){throw 'No active Large16 SDF trial.'}
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backupRoot=Resolve-WorkspaceInput $receipt.backup_root -RequireExisting
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
Assert-GameClosed
$catalog=Resolve-ChildPath $game $receipt.catalog_relative -RequireExisting
$dll=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$catalogBackup=Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog' -RequireExisting
$dllBackup=Resolve-ChildPath $backupRoot 'InfinityEngine-Enhancer.dll' -RequireExisting
Assert-Identity $catalog $receipt.catalog_sha256
Assert-Identity $dll $receipt.dll_sha256
Assert-Identity $catalogBackup $receipt.parent_catalog_sha256
Assert-Identity $dllBackup $receipt.parent_dll_sha256
foreach($item in $receipt.preserved_files){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
Assert-GameClosed
Copy-FileAtomic $dllBackup $dll
Copy-FileAtomic $catalogBackup $catalog
Assert-Identity $dll $receipt.parent_dll_sha256
Assert-Identity $catalog $receipt.parent_catalog_sha256
$receipt.status='restored-parent';$receipt | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
Write-JsonAtomic $receiptPath $receipt
Write-Output 'Accepted Large16 V7 without SDF restored; white test creature, Ankheg contour and unrelated files retained.'
