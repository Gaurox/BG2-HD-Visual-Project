$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
if ($receipt.status -ne 'installed-pending-ingame-qa') { throw 'No active SDF trial to restore.' }
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backupRoot=Resolve-WorkspaceInput $receipt.backup_root -RequireExisting
function Assert-Identity([string]$Path,[string]$Expected) {
    if ((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()) { throw "Identity differs: $Path" }
}
Assert-GameClosed
$catalog=Resolve-ChildPath $game $receipt.catalog_relative -RequireExisting
$dll=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
Assert-Identity $catalog $receipt.catalog_sha256
Assert-Identity $dll $receipt.dll_sha256
Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting) $receipt.ini_sha256
Assert-Identity (Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog' -RequireExisting) $receipt.parent_catalog_sha256
Assert-Identity (Resolve-ChildPath $backupRoot 'InfinityEngine-Enhancer.dll' -RequireExisting) $receipt.parent_dll_sha256
foreach ($shader in $receipt.shaders) { Assert-Identity (Resolve-ChildPath $game $shader.target -RequireExisting) $shader.sha256 }
foreach ($shader in $receipt.parent_shaders) { Assert-Identity (Resolve-ChildPath $backupRoot $shader.relative_path -RequireExisting) $shader.sha256 }
Copy-FileAtomic (Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog') $catalog
Copy-FileAtomic (Resolve-ChildPath $backupRoot 'InfinityEngine-Enhancer.dll') $dll
foreach ($shader in $receipt.parent_shaders) {
    Copy-FileAtomic (Resolve-ChildPath $backupRoot $shader.relative_path) (Resolve-ChildPath $game $shader.relative_path)
    Assert-Identity (Resolve-ChildPath $game $shader.relative_path) $shader.sha256
}
Assert-Identity $catalog $receipt.parent_catalog_sha256
Assert-Identity $dll $receipt.parent_dll_sha256
$receipt.status='restored-parent-alpha-light'
$receipt | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
Write-JsonAtomic $receiptPath $receipt
Write-Output 'Ankheg alpha-light parent restored; SDF trial disabled.'
