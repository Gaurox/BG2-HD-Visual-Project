$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$r=Read-JsonFile $receiptPath
if ($r.status -ne 'installed-pending-ingame-qa') { throw 'No active spline test to restore.' }
$game=Resolve-WorkspaceInput $r.game_root -RequireExisting
$backup=Resolve-WorkspaceInput $r.backup_root -RequireExisting
Assert-GameClosed
$catalog=Resolve-ChildPath $game $r.catalog_relative -RequireExisting
$dll=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$catalogBackup=Resolve-ChildPath $backup 'CreatureSprites-XN.catalog' -RequireExisting
$dllBackup=Resolve-ChildPath $backup 'InfinityEngine-Enhancer.dll' -RequireExisting
foreach ($pair in @(@($catalog,$r.catalog_sha256),@($dll,$r.dll_sha256),@($catalogBackup,$r.parent_catalog_sha256),@($dllBackup,$r.parent_dll_sha256))) {
    if ((Get-FileSha256 $pair[0]) -ne $pair[1].ToUpperInvariant()) { throw 'Installation identity changed; inspect before restoring.' }
}
Copy-FileAtomic $catalogBackup $catalog
Copy-FileAtomic $dllBackup $dll
if ((Get-FileSha256 $catalog) -ne $r.parent_catalog_sha256.ToUpperInvariant() -or
    (Get-FileSha256 $dll) -ne $r.parent_dll_sha256.ToUpperInvariant()) { throw 'Restore verification failed.' }
$r.status='restored-parent'
$r | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
Write-JsonAtomic $receiptPath $r
Write-Output 'Ankheg original Q3m sans spline restauré ; CatmullRom conservé.'
