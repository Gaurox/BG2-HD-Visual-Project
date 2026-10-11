[CmdletBinding()]
param(
    [string]$GameRoot = "G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition",
    [string]$BundleRoot = "G:\AI\BG2_Upscale\engine\InfinityEngine-Enhancer\source-patchee\build-filter-diagnostic-v142\release-bundle"
)

$ErrorActionPreference = 'Stop'

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Set-IniFlag([string]$Path, [string]$Key, [string]$Value) {
    $content = Get-Content -LiteralPath $Path -Raw
    $pattern = "(?im)^\s*" + [regex]::Escape($Key) + "\s*=.*$"
    # Old local test INIs can contain several [Shaders] blocks. Remove all
    # prior copies first, then add exactly one flag to the first block.
    $content = [regex]::Replace($content, "$pattern\r?\n?", '')
    $shaderMatch = [regex]::Match($content, '(?im)^\s*\[Shaders\]\s*$')
    if ($shaderMatch.Success) {
        $lineEnd = $content.IndexOf("`n", $shaderMatch.Index + $shaderMatch.Length)
        if ($lineEnd -lt 0) {
            $content += "`r`n$Key = $Value`r`n"
        } else {
            $content = $content.Insert($lineEnd + 1, "$Key = $Value`r`n")
        }
    } else {
        $content += "`r`n[Shaders]`r`n$Key = $Value`r`n"
    }
    [System.IO.File]::WriteAllText($Path, $content, [System.Text.UTF8Encoding]::new($false))
}

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$bundleRootPath = (Resolve-Path -LiteralPath $BundleRoot).Path
$sourceDll = Join-Path $bundleRootPath 'InfinityEngine-Enhancer.dll'
$sourceAssets = Join-Path $bundleRootPath 'iee-assets\bridge-transition'
$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$targetIni = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$targetAssets = Join-Path $gameRootPath 'iee-assets\bridge-transition'

foreach ($path in @($sourceDll, $targetDll, $targetIni)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Fichier requis introuvable : $path" }
}
if (-not (Test-Path -LiteralPath $sourceAssets -PathType Container)) { throw "Assets du pont introuvables : $sourceAssets" }
if (Test-Path -LiteralPath $targetAssets) { throw "Refus d'ecraser des assets existants : $targetAssets" }
if (Get-Process -Name 'Baldur*','InfinityLoader*' -ErrorAction SilentlyContinue) {
    throw 'Fermez Baldur''s Gate II et InfinityLoader avant l''installation.'
}

$backupRoot = Join-Path (Split-Path -Parent $PSScriptRoot) ('install-backups\bridge-preview-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
Copy-Item -LiteralPath $targetDll -Destination (Join-Path $backupRoot 'InfinityEngine-Enhancer.dll')
Copy-Item -LiteralPath $targetIni -Destination (Join-Path $backupRoot 'InfinityEngine-Enhancer.ini')

$manifest = [ordered]@{
    schema = 'ar1300-bridge-transition-preview-install-v1'
    game_root = $gameRootPath
    original_dll_sha256 = Get-Sha256 $targetDll
    original_ini_sha256 = Get-Sha256 $targetIni
    target_assets_previously_present = $false
    installed_at = (Get-Date).ToUniversalTime().ToString('o')
}

try {
    New-Item -ItemType Directory -Path (Split-Path -Parent $targetAssets) -Force | Out-Null
    Copy-Item -LiteralPath $sourceDll -Destination $targetDll -Force
    Copy-Item -LiteralPath $sourceAssets -Destination $targetAssets -Recurse
    Set-IniFlag $targetIni 'EnableBridgeTransitionPreview' 'true'

    $manifest.installed_dll_sha256 = Get-Sha256 $targetDll
    $manifest.installed_ini_sha256 = Get-Sha256 $targetIni
    $manifest.assets = Get-ChildItem -LiteralPath $targetAssets -File | ForEach-Object {
        [ordered]@{ name = $_.Name; bytes = $_.Length; sha256 = Get-Sha256 $_.FullName }
    }
    $manifest.status = 'installed'
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backupRoot 'install-backup.json') -Encoding UTF8
} catch {
    Copy-Item -LiteralPath (Join-Path $backupRoot 'InfinityEngine-Enhancer.dll') -Destination $targetDll -Force
    Copy-Item -LiteralPath (Join-Path $backupRoot 'InfinityEngine-Enhancer.ini') -Destination $targetIni -Force
    if (Test-Path -LiteralPath $targetAssets) { Remove-Item -LiteralPath $targetAssets -Recurse -Force }
    throw
}

Write-Host "Preview installee. Sauvegarde reversible : $backupRoot"
Write-Host 'Dans AR1300, BRIDGE01 pilote ouverture/fermeture/inversion; F9 rejoue uniquement l''ouverture en diagnostic.'
