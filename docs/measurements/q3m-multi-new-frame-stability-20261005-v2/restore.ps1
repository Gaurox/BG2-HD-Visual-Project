$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$receipt=Read-JsonFile (Join-Path $PSScriptRoot 'ingame-installation/active-test.json')
$game=Resolve-WorkspaceInput $receipt.game_root -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
Assert-GameClosed
if((Get-FileSha256 $target) -ne $receipt.dll_sha256.ToUpperInvariant()){throw 'Active DLL has changed; refusing to overwrite.'}
if((Get-FileSha256 $backup) -ne $receipt.parent_dll_sha256.ToUpperInvariant()){throw 'Parent backup differs.'}
Copy-FileAtomic $backup $target
if((Get-FileSha256 $target) -ne $receipt.parent_dll_sha256.ToUpperInvariant()){throw 'Restore verification failed.'}
$receipt.status='restored-parent-runtime';Write-JsonAtomic (Join-Path $PSScriptRoot 'ingame-installation/active-test.json') $receipt
Write-Output 'Parent runtime restored; sprite assets unchanged. Run finish.py to reconcile tracking.'
