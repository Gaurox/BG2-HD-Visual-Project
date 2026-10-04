$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
$target=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
Assert-GameClosed
Assert-Identity $target $generation.catalog.sha256
Assert-Identity $backup $baseline.parent_catalog_sha256
foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
foreach($item in $receipt.fixtures){Assert-Identity (Resolve-ChildPath $game $item.target -RequireExisting) $item.sha256}
Copy-FileAtomic $backup $target
Assert-Identity $target $baseline.parent_catalog_sha256
foreach($item in $receipt.fixtures){Remove-Item -LiteralPath (Resolve-ChildPath $game $item.target -RequireExisting)}
$receipt.status='restored-parent';Write-JsonAtomic $receiptPath $receipt
Write-Output 'Parent catalogue restored; seven generated test CRE removed; unreferenced leaves preserved.'
