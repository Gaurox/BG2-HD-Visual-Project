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
$input = Join-Path $PSScriptRoot 'sources\pages'
$output = Join-Path $PSScriptRoot 'upscale-topaz-recovery-v2-d50'
if (!(Test-Path -LiteralPath $topaz)) { throw "Topaz Gigapixel introuvable : $topaz" }
$sources = @(Get-ChildItem -LiteralPath $input -File -Filter '*-x1.png')
if ($sources.Count -ne 2) { throw "2 atlas source attendus, $($sources.Count) trouvés." }

New-Item -ItemType Directory -Path $output -Force | Out-Null
& $topaz -i $input -o $output -m recovery --mv 2 --detail 50 --scale 4 -f png --cs preserve --pc 4 --suffix '-x4' --se --verbose
$topazExitCode = $LASTEXITCODE

$exports = @(Get-ChildItem -LiteralPath $output -File -Filter '*-x1-x4.png')
if ($exports.Count -ne 2) { throw "2 exports x4 attendus, $($exports.Count) produits." }
if ($topazExitCode -ne 0) {
    Write-Warning "Topaz a retourné $topazExitCode après avoir écrit les deux exports ; ils sont conservés pour vérification."
}
Write-Host "Exports Topaz Recovery v2 Detail 50 x4 terminés : $output"
