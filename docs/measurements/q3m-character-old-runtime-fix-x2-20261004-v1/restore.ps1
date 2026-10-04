$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$gen=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$target=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
Assert-GameClosed
if((Get-FileSha256 $target) -ne $gen.catalog.sha256.ToUpperInvariant()){throw 'Current catalog changed.'}
if((Get-FileSha256 $backup) -ne $baseline.parent_catalog_sha256.ToUpperInvariant()){throw 'Backup changed.'}
foreach($item in $baseline.preserved){if((Get-FileSha256 (Resolve-ChildPath $game $item.relative_path -RequireExisting)) -ne $item.sha256.ToUpperInvariant()){throw "Preserved identity changed: $($item.relative_path)"}}
Copy-FileAtomic $backup $target
if((Get-FileSha256 $target) -ne $baseline.parent_catalog_sha256.ToUpperInvariant()){throw 'Restoration identity differs.'}
Write-JsonAtomic (Join-Path $PSScriptRoot 'ingame-installation/restoration.json') ([ordered]@{status='restored-parent-catalog';restored_at_utc=[DateTime]::UtcNow.ToString('o');catalog_sha256=$baseline.parent_catalog_sha256;unused_content_addressed_leaves_retained=$true})
