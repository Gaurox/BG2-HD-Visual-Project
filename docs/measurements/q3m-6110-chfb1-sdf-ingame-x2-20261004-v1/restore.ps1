$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
if($receipt.status -ne 'installed-pending-ingame-qa') { throw 'No active Character SDF trial.' }
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$backup=Resolve-WorkspaceInput $receipt.backup_root -RequireExisting
Assert-GameClosed
$expected=@([pscustomobject]@{relative_path='InfinityEngine-Enhancer.dll';sha256=$receipt.dll_sha256},
            [pscustomobject]@{relative_path='iee-assets/creature-sprites/CreatureSprites-XN.catalog';sha256=$receipt.catalog_sha256})+
          @($receipt.shaders | ForEach-Object { [pscustomobject]@{relative_path=$_.target;sha256=$_.sha256} })+
          @($receipt.preserved_files)
foreach($item in $expected) {
    if((Get-FileSha256 (Resolve-ChildPath $game $item.relative_path -RequireExisting)) -ne $item.sha256.ToUpperInvariant()) { throw "Current file changed: $($item.relative_path)" }
}
foreach($item in $receipt.parent_files) {
    if((Get-FileSha256 (Resolve-ChildPath $backup $item.relative_path -RequireExisting)) -ne $item.sha256.ToUpperInvariant()) { throw 'Backup differs.' }
}
foreach($item in $receipt.parent_files) { Copy-FileAtomic (Resolve-ChildPath $backup $item.relative_path) (Resolve-ChildPath $game $item.relative_path) }
$receipt.status='restored-parent'
Write-JsonAtomic $receiptPath $receipt
Write-Output 'Character SDF trial removed; previous stable Ankheg runtime restored.'
