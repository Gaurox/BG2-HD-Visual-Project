param()

$ErrorActionPreference = 'Stop'
$topaz = 'C:\Program Files\Topaz Labs LLC\Topaz Gigapixel AI\gigapixel.exe'
$input = Join-Path $PSScriptRoot 'topaz-input-x1'
$output = Join-Path $PSScriptRoot 'upscale-topaz-recovery-v2-d50'
if (!(Test-Path -LiteralPath $topaz)) { throw "Topaz Gigapixel introuvable : $topaz" }
$sources = @(Get-ChildItem -LiteralPath $input -File -Filter '*.png')
if ($sources.Count -ne 17) { throw "17 sources du sélecteur attendues, $($sources.Count) trouvées." }

New-Item -ItemType Directory -Path $output -Force | Out-Null
& $topaz -i $input -o $output -m recovery --mv 2 --detail 50 --scale 4 -f png --cs preserve --pc 4 --suffix '-x4' --se --verbose
if ($LASTEXITCODE -ne 0) { throw "Topaz a retourné le code $LASTEXITCODE." }

$exports = @(Get-ChildItem -LiteralPath $output -File -Filter '*-x4.png')
if ($exports.Count -ne 17) { throw "17 exports x4 attendus, $($exports.Count) produits." }
Write-Host "Exports x4 Topaz Recover v2 Detail 50 terminés : $output"
