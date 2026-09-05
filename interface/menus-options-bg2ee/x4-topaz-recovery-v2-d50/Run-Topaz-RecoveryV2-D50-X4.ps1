param()

$workspaceRoot = $PSScriptRoot
while ($workspaceRoot -and -not (Test-Path -LiteralPath (Join-Path $workspaceRoot 'config\workspace-paths.json') -PathType Leaf)) {
    $workspaceRoot = Split-Path -Parent $workspaceRoot
}
if ([string]::IsNullOrWhiteSpace($workspaceRoot)) { throw 'Racine du workspace BG2 Upscale introuvable.' }
. (Join-Path $workspaceRoot 'pipeline\scripts\WorkspacePaths.ps1')
if ((Get-Variable -Name GameRoot -ErrorAction SilentlyContinue) -and [string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
}

$ErrorActionPreference = 'Stop'
$topaz = Resolve-BG2WorkspacePath -Key 'topaz_gigapixel_exe' -RequireExisting
$input = Join-Path $PSScriptRoot 'topaz-input-x1'
$output = Join-Path $PSScriptRoot 'upscale-topaz-recovery-v2-d50'
if (!(Test-Path -LiteralPath $topaz)) { throw "Topaz Gigapixel introuvable : $topaz" }
$sources = @(Get-ChildItem -LiteralPath $input -File -Filter '*.png')
if ($sources.Count -ne 34) { throw "34 éléments UI attendus, $($sources.Count) trouvés." }

New-Item -ItemType Directory -Path $output -Force | Out-Null
& $topaz -i $input -o $output -m recovery --mv 2 --detail 50 --scale 4 -f png --cs preserve --pc 4 --suffix '-x4' --se --verbose
if ($LASTEXITCODE -ne 0) { throw "Topaz a retourné le code $LASTEXITCODE." }

$exports = @(Get-ChildItem -LiteralPath $output -File -Filter '*-x4.png')
if ($exports.Count -ne 34) { throw "34 exports x4 attendus, $($exports.Count) produits." }
Write-Host "Exports Topaz Recover v2 Detail 50 x4 terminés : $output"
