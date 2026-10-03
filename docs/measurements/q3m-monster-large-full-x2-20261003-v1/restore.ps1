$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receipt = Read-JsonFile (Join-Path $PSScriptRoot 'ingame-installation/active-test.json')
if ($receipt.status -ne 'installed-pending-ingame-qa') { throw 'No active installation to restore.' }
$game = Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backupRoot = Resolve-WorkspaceInput $receipt.backup_root -RequireExisting
Assert-GameClosed
foreach ($item in @(
    @{ path = $receipt.catalog_relative; sha = $receipt.catalog_sha256 },
    @{ path = 'InfinityEngine-Enhancer.dll'; sha = $receipt.dll_sha256 },
    @{ path = 'InfinityEngine-Enhancer.ini'; sha = $receipt.ini_sha256 }
)) {
    if ((Get-FileSha256 (Resolve-ChildPath $game $item.path -RequireExisting)) -ne $item.sha.ToUpperInvariant()) {
        throw "Active installation changed: $($item.path)"
    }
}
foreach ($item in $receipt.backups) {
    if ((Get-FileSha256 (Resolve-ChildPath $backupRoot $item.file -RequireExisting)) -ne $item.sha256.ToUpperInvariant()) {
        throw 'Backup identity differs.'
    }
}
foreach ($item in $receipt.backups) {
    Copy-FileAtomic (Resolve-ChildPath $backupRoot $item.file -RequireExisting) (Resolve-ChildPath $game $item.relative_path)
    if ((Get-FileSha256 (Resolve-ChildPath $game $item.relative_path)) -ne $item.sha256.ToUpperInvariant()) {
        throw 'Restore identity differs.'
    }
}
$receipt.status = 'restored-parent'
$receipt | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
Write-JsonAtomic (Join-Path $PSScriptRoot 'ingame-installation/active-test.json') $receipt
Write-Output 'Parent DLL/catalog/INI restored; unreferenced content-addressed Ogre leaves retained.'
