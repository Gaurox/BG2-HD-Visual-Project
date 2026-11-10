$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$fixture = Join-Path $workspace '.tmp/shared-storage-installer-guard-default-20261110-v1'
if (Test-Path -LiteralPath $fixture) { throw 'Use a new fixture version.' }
New-Item -ItemType Directory -Path $fixture | Out-Null
$release = Join-Path $workspace 'releases/BG2-HD-Upscale'
$helper = Join-Path $release 'bg2hd/tools/bg2hd-effect-storage.ps1'
function Expect-Rejected {
    $rejected = $false
    try { & $helper -GameRoot $fixture | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'An incompatible renderer was accepted.' }
}
Expect-Rejected
$dll = Join-Path $fixture 'InfinityEngine-Enhancer.dll'
Copy-Item -LiteralPath (Join-Path $release 'release-inputs/renderer/iee-0.1.0-alpha.10/InfinityEngine-Enhancer.dll') -Destination $dll
Expect-Rejected
Copy-Item -LiteralPath (Join-Path $release 'bg2hd/renderer/InfinityEngine-Enhancer.dll') -Destination $dll -Force
& $helper -GameRoot $fixture
if (-not $?) { throw 'Current renderer rejected.' }
$resolved = [IO.Path]::GetFullPath($fixture)
if (-not $resolved.StartsWith((Join-Path $workspace '.tmp/'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe fixture cleanup.' }
Remove-Item -LiteralPath $resolved -Recurse -Force
Write-Output 'INSTALLER_STORAGE_GUARD=PASSED (missing/old rejected, bundled renderer accepted)'
