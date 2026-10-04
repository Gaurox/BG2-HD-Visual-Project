$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
if ($receipt.status -ne 'installed-pending-ingame-qa') { throw 'No active runtime patch to restore.' }
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backup=Resolve-WorkspaceInput ($receipt.backup_root + '/InfinityEngine-Enhancer.dll') -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
Assert-GameClosed
foreach ($item in $receipt.preserved_files) {
    if ((Get-FileSha256 (Resolve-ChildPath $game $item.relative_path -RequireExisting)) -ne $item.sha256.ToUpperInvariant()) {
        throw "Preserved file changed: $($item.relative_path)"
    }
}
if ((Get-FileSha256 $target) -ne $receipt.dll_sha256.ToUpperInvariant() -or
    (Get-FileSha256 $backup) -ne $receipt.parent_dll_sha256.ToUpperInvariant()) { throw 'DLL identity differs.' }
Copy-FileAtomic $backup $target
if ((Get-FileSha256 $target) -ne $receipt.parent_dll_sha256.ToUpperInvariant()) { throw 'Restore failed.' }
$receipt.status='restored-parent-runtime'
Write-JsonAtomic $receiptPath $receipt
Write-Output 'Previous SDF runtime restored. Sprite assets and contour remain installed.'
