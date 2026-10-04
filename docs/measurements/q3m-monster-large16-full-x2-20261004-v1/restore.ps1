$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
if($receipt.status -ne 'installed-pending-ingame-qa'){throw 'No active Large16 installation.'}
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backupRoot=Resolve-WorkspaceInput $receipt.backup_root -RequireExisting
$catalog=Resolve-ChildPath $game $receipt.catalog_relative -RequireExisting
$backup=Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog' -RequireExisting
Assert-GameClosed
if((Get-FileSha256 $catalog) -ne $receipt.catalog_sha256.ToUpperInvariant() -or
   (Get-FileSha256 $backup) -ne $receipt.parent_catalog_sha256.ToUpperInvariant()){throw 'Catalog identity changed.'}
foreach($item in $receipt.preserved_files){if((Get-FileSha256 (Resolve-ChildPath $game $item.relative_path -RequireExisting)) -ne $item.sha256.ToUpperInvariant()){throw 'Preserved file changed.'}}
if($receipt.fixture.target -ne 'override/QMWYVW01.cre'){throw 'Unexpected fixture target.'}
$fixture=Resolve-ChildPath $game $receipt.fixture.target -RequireExisting
if((Get-FileSha256 $fixture) -ne $receipt.fixture.sha256.ToUpperInvariant()){throw 'Test creature changed.'}
Copy-FileAtomic $backup $catalog
if((Get-FileSha256 $catalog) -ne $receipt.parent_catalog_sha256.ToUpperInvariant()){throw 'Restore failed.'}
Remove-Item -LiteralPath $fixture
$receipt.status='restored-parent';$receipt | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
Write-JsonAtomic $receiptPath $receipt
Write-Output 'Previous stable Ankheg catalog restored; Large16 test CRE removed; unreferenced registry leaves retained.'
