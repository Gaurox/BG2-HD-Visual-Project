$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$receipt=Read-JsonFile $receiptPath
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
Assert-GameClosed
if((Get-FileSha256 $target) -ne $generation.dll.sha256.ToUpperInvariant() -or (Get-FileSha256 $backup) -ne $baseline.parent_dll_sha256.ToUpperInvariant()){throw 'DLL identity differs; no overwrite.'}
foreach($r in $baseline.preserved){if((Get-FileSha256 (Resolve-ChildPath $game $r.relative_path -RequireExisting)) -ne $r.sha256.ToUpperInvariant()){throw "Preserved file differs: $($r.relative_path)"}}
Copy-FileAtomic $backup $target
if((Get-FileSha256 $target) -ne $baseline.parent_dll_sha256.ToUpperInvariant()){throw 'Restoration failed.'}
$receipt.status='restored-parent-runtime';$receipt.restored_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $receiptPath $receipt
Write-Output 'Parent DLL restored; assets unchanged. Update current installation tracking before any new candidate.'
