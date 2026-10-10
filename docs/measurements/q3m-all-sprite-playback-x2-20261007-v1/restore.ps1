[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$b=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$g=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$game=Resolve-WorkspaceInput $b.game_root -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
Assert-GameClosed
if((Get-FileSha256 $target) -ne $g.dll.sha256.ToUpperInvariant() -or
   (Get-FileSha256 $backup) -ne $b.parent_dll_sha256.ToUpperInvariant()){throw 'Runtime/backup identity differs.'}
if($DryRun){Write-Output 'Ready to restore parent DLL only.';return}
Copy-FileAtomic $backup $target
if((Get-FileSha256 $target) -ne $b.parent_dll_sha256.ToUpperInvariant()){throw 'Restoration verification failed.'}
Write-JsonAtomic (Join-Path $PSScriptRoot 'ingame-installation/active-test.json') ([ordered]@{
    status='restored-parent';parent_dll_sha256=$b.parent_dll_sha256;restored_at_utc=[DateTime]::UtcNow.ToString('o');release=$false})
Write-Output 'Parent DLL restored;catalogue and sprites untouched. Update current runtime pointer accordingly.'
