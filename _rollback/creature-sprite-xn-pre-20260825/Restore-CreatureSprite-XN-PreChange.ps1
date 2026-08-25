[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$resolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $resolvedProject 'AGENTS.md') -PathType Leaf)) {
    throw "ProjectRoot ne désigne pas BG2_Upscale : $resolvedProject"
}

$relativeFiles = @(
    'pipeline\scripts\run_creature_sprite_x2.py',
    'pipeline\scripts\xbr2x_batch.js',
    'pipeline\scripts\Install-CreatureSprite-X2-Test.ps1',
    'pipeline\scripts\Restore-CreatureSprite-X2-Test.ps1',
    'pipeline\tests\test_creature_sprite_x2_pipeline.py',
    'sprite\README.md',
    'sprite\SPRITE_UPSCALE_PIPELINE.md',
    'engine\InfinityEngine-Enhancer\source-patchee\src\iee\creature_sprite_x2.h',
    'engine\InfinityEngine-Enhancer\source-patchee\src\iee\creature_sprite_x2.cpp',
    'engine\InfinityEngine-Enhancer\source-patchee\src\iee\hooks.cpp',
    'engine\InfinityEngine-Enhancer\source-patchee\src\iee\dll_main.cpp',
    'engine\InfinityEngine-Enhancer\source-patchee\src\iee\core\config.h',
    'engine\InfinityEngine-Enhancer\source-patchee\src\iee\core\config.cpp',
    'engine\InfinityEngine-Enhancer\source-patchee\tests\iee_tests.cpp'
)

foreach ($relative in $relativeFiles) {
    $backup = Join-Path $PSScriptRoot $relative
    $target = Join-Path $resolvedProject $relative
    if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
        throw "Sauvegarde manquante : $backup"
    }
    $targetFull = [IO.Path]::GetFullPath($target)
    if (-not $targetFull.StartsWith($resolvedProject + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors workspace : $targetFull"
    }
    if ($PSCmdlet.ShouldProcess($targetFull, 'Restaurer la version pré-xN')) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $targetFull) -Force | Out-Null
        Copy-Item -LiteralPath $backup -Destination $targetFull -Force
    }
}
