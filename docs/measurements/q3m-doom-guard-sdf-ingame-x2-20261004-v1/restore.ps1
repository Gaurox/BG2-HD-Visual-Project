$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
Assert-GameClosed
foreach($entry in @(@{target=$baseline.catalog_relative;backup='CreatureSprites-XN.catalog';current=$generation.catalog.sha256;parent=$baseline.parent_catalog_sha256},@{target='InfinityEngine-Enhancer.dll';backup='InfinityEngine-Enhancer.dll';current=$generation.dll.sha256;parent=$baseline.dll_sha256})){
    $target=Resolve-ChildPath $game $entry.target -RequireExisting
    $backup=Join-Path $PSScriptRoot ('work/before/'+$entry.backup)
    if((Get-FileSha256 $target) -ne $entry.current.ToUpperInvariant() -or (Get-FileSha256 $backup) -ne $entry.parent.ToUpperInvariant()){throw 'Restore identity mismatch.'}
}
Copy-FileAtomic (Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll') (Join-Path $game 'InfinityEngine-Enhancer.dll')
Copy-FileAtomic (Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog') (Resolve-ChildPath $game $baseline.catalog_relative)
Write-JsonAtomic (Join-Path $PSScriptRoot 'restoration-verification.json') ([ordered]@{catalog_sha256=Get-FileSha256 (Resolve-ChildPath $game $baseline.catalog_relative);dll_sha256=Get-FileSha256 (Join-Path $game 'InfinityEngine-Enhancer.dll');restored_at_utc=[DateTime]::UtcNow.ToString('o')})
