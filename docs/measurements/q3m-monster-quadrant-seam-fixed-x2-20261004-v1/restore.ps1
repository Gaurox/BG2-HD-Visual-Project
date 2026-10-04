$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$r=Read-JsonFile (Join-Path $PSScriptRoot 'ingame-installation/active-test.json')
$game=Resolve-WorkspaceInput $r.game_root -RequireExisting
Assert-GameClosed
$target=Resolve-ChildPath $game $r.catalog_relative -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
if((Get-FileSha256 $target) -ne $r.catalog_sha256.ToUpperInvariant() -or (Get-FileSha256 $backup) -ne $r.parent_catalog_sha256.ToUpperInvariant()){throw 'Catalogue identity changed.'}
foreach($f in $r.preserved_files){if((Get-FileSha256 (Resolve-ChildPath $game $f.relative_path -RequireExisting)) -ne $f.sha256.ToUpperInvariant()){throw 'Preserved identity changed.'}}
Copy-FileAtomic $backup $target
Write-JsonAtomic (Join-Path $PSScriptRoot 'restoration-verification.json') ([ordered]@{status='restored-parent';catalog_sha256=$r.parent_catalog_sha256;DLL_unchanged=$true;ingame_QA=$false})
