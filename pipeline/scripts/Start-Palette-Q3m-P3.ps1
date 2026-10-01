[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Run,
    [string]$GameRoot,
    [ValidateSet('Q0', 'Q3m', 'Restore')][string]$Mode = 'Q3m',
    [ValidateSet(2, 4)][int]$Scale = 2,
    [switch]$TracePalettes
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')
$runRoot = Resolve-WorkspaceInput $Run -RequireExisting
$game = if ($GameRoot) { Resolve-WorkspaceInput $GameRoot -RequireExisting } else {
    Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
}
Assert-GameClosed
$runtimeManifest = Join-Path $runRoot 'runtime.json'
$runtimeState = Join-Path $runRoot 'ingame-runtime'
$sessionPath = Join-Path $runRoot 'active-session.json'
$active = if (Test-Path -LiteralPath $sessionPath) { Read-JsonFile $sessionPath } else { $null }
if ($active -and $active.status -eq 'installed-pending-qa') {
    & (Join-Path $PSScriptRoot 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $active.job_file
    $active.status = 'restored'
    Write-JsonAtomic $sessionPath $active
}
if ($Mode -eq 'Restore') {
    if (Test-Path -LiteralPath (Join-Path $runtimeState 'active-test.json')) {
        & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Restore -GameRoot $game -StateRoot $runtimeState
    }
    return
}

$label = if ($Mode -eq 'Q0') { "x$Scale-q0" } else { "x$Scale-q3m-k6" }
$job = Join-Path $runRoot "$label.job.json"
$newRuntime = -not (Test-Path -LiteralPath (Join-Path $runtimeState 'active-test.json'))
& (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Manifest $runtimeManifest -GameRoot $game -StateRoot $runtimeState
try {
    & (Join-Path $PSScriptRoot 'Install-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $job -RuntimeManifest $runtimeManifest -CreatureSpriteFilter Nearest
    $iniPath = Join-Path $game 'InfinityEngine-Enhancer.ini'
    $ini = Get-Content -LiteralPath $iniPath -Raw
    $traceValue = if ($TracePalettes) { 'true' } else { 'false' }
    $ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpritePaletteTrace' $traceValue
    $ini = Set-IniValue $ini 'ShaderSuite.fpSprite' 'Enabled' 'false'
    $ini = Set-IniValue $ini 'ShaderSuite.fpSELECT' 'Enabled' 'false'
    Write-TextAtomic $iniPath $ini
    Write-JsonAtomic $sessionPath ([ordered]@{
        schema = 'bg2-upscale-character-palette-p3-active-v1'; status = 'installed-pending-qa'
        mode = $Mode; job_file = $job; palette_trace = [bool]$TracePalettes
        installed_at_utc = [DateTime]::UtcNow.ToString('o'); visual_qa_accepted = $false
    })
} catch {
    & (Join-Path $PSScriptRoot 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $job
    if ($newRuntime) {
        & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Restore -GameRoot $game -StateRoot $runtimeState
    }
    throw
}
