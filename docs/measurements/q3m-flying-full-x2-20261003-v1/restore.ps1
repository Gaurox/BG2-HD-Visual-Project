$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
if ($receipt.status -ne 'installed-pending-ingame-qa') { throw 'No active installation to restore.' }
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backupRoot=Resolve-WorkspaceInput $receipt.backup_root -RequireExisting
Assert-GameClosed
$catalog=Resolve-ChildPath $game $receipt.catalog_relative -RequireExisting
$backup=Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog' -RequireExisting
if ((Get-FileSha256 $catalog) -ne $receipt.catalog_sha256.ToUpperInvariant() -or
    (Get-FileSha256 $backup) -ne $receipt.parent_catalog_sha256.ToUpperInvariant()) { throw 'Catalog identity changed.' }
Copy-FileAtomic $backup $catalog
if ((Get-FileSha256 $catalog) -ne $receipt.parent_catalog_sha256.ToUpperInvariant()) { throw 'Restore identity differs.' }
$receipt.status='restored-parent'
$receipt | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
Write-JsonAtomic $receiptPath $receipt
Write-Output 'Parent Ogre catalog restored; unreferenced bird leaves retained.'
