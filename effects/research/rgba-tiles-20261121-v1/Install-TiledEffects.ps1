[CmdletBinding()]
param([ValidateSet('Install', 'Restore')] [string]$Action = 'Install')

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$gamePath = & python -B -c "import sys; sys.path.insert(0,sys.argv[1]); from workspace_paths import get_path; print(get_path('bg2ee_game_root'))" (Join-Path $workspace 'pipeline/scripts')
if ($LASTEXITCODE -ne 0) { throw 'Chemin BG2EE indisponible.' }
$game = (Resolve-Path -LiteralPath $gamePath).Path
$parent = (Resolve-Path -LiteralPath (Join-Path $game 'iee-assets')).Path
if ((Split-Path -Parent $parent) -ne $game -or ((Get-Item -LiteralPath $parent).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Dossier iee-assets inattendu.'
}
$active = Join-Path $parent 'effects'
$backup = Join-Path $parent 'effects-before-tiles-20261121-v1'
$staged = Join-Path $parent 'effects-tiles-stage-20261121-v1'
$dll = Join-Path $game 'InfinityEngine-Enhancer.dll'
$backupDll = Join-Path $game 'InfinityEngine-Enhancer.before-effects-tiles-20261121-v1.dll'
$stagedDll = Join-Path $game 'InfinityEngine-Enhancer.effects-tiles-stage-20261121-v1.dll'
$local = Join-Path $PSScriptRoot 'installation'
$receiptPath = Join-Path $local 'installed.json'
$tiled = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'results-live.json') -Raw | ConvertFrom-Json
$cropped = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../rgba-crop-full-20261121-v1/results-live.json') -Raw | ConvertFrom-Json

function Assert-GameClosed {
    if (Get-Process -Name Baldur,BaldurReal,BaldurII,InfinityLoader -ErrorAction SilentlyContinue) {
        throw 'Quitter BG2EE et InfinityLoader.'
    }
}
function Assert-Directory([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    if (!$item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        $item.FullName -ne $Path -or (Split-Path -Parent $item.FullName) -ne $parent) {
        throw "Dossier effets inattendu ($Path)"
    }
}
function File-Hash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Assert-Pack($Metadata, [string]$Path) {
    Assert-Directory $Path
    $expected = $Metadata.files.PSObject.Properties
    $actual = Get-ChildItem -LiteralPath $Path -Force
    if (Compare-Object @($expected.Name) @($actual.Name)) { throw "Inventaire modifié ($Path)" }
    foreach ($file in $expected) {
        $source = Join-Path $Path $file.Name
        if ((Get-Item -LiteralPath $source).Length -ne $file.Value.bytes -or (File-Hash $source) -ne $file.Value.sha256) {
            throw "Pack modifié ($source)"
        }
    }
}

Assert-GameClosed
Assert-Directory $active
if ($Action -eq 'Install') {
    foreach ($path in @($backup, $staged, $backupDll, $stagedDll, $receiptPath)) {
        if (Test-Path -LiteralPath $path) { throw "Chemin déjà utilisé ($path)" }
    }
    $renderer = Get-Content -LiteralPath (Join-Path $local 'renderer.json') -Raw | ConvertFrom-Json
    $rendererInput = Join-Path $local 'InfinityEngine-Enhancer.dll'
    if ((File-Hash $rendererInput) -ne $renderer.sha256 -or (File-Hash $dll) -ne $renderer.previous_sha256) {
        throw 'Empreinte du renderer candidat ou actif différente.'
    }
    Assert-Pack $cropped $active
    New-Item -ItemType Directory -Path $staged | Out-Null
    Assert-Directory $staged
    foreach ($file in $tiled.files.PSObject.Properties) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot "pack-live/$($file.Name)") -Destination (Join-Path $staged $file.Name)
    }
    Assert-Pack $tiled $staged
    Copy-Item -LiteralPath $rendererInput -Destination $stagedDll
    if ((File-Hash $stagedDll) -ne $renderer.sha256 -or (File-Hash $dll) -ne $renderer.previous_sha256 -or
        (File-Hash (Join-Path $active 'manifest.json')) -ne $cropped.files.'manifest.json'.sha256) {
        throw 'Le pack actif ou le renderer a changé pendant la préparation.'
    }
    Assert-GameClosed
    Assert-Directory $active
    Move-Item -LiteralPath $active -Destination $backup
    try {
        Move-Item -LiteralPath $staged -Destination $active
        [IO.File]::Replace($stagedDll, $dll, $backupDll)
        [ordered]@{
            state = 'installed-awaiting-ingame-test'
            renderer_sha256 = $renderer.sha256
            previous_renderer_sha256 = $renderer.previous_sha256
            original_pack = 'config://bg2ee_game_root/iee-assets/effects-before-tiles-20261121-v1'
            original_renderer = 'config://bg2ee_game_root/InfinityEngine-Enhancer.before-effects-tiles-20261121-v1.dll'
            tile_index_sha256 = $tiled.files.'EffectTiles-X4.index'.sha256
        } | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding utf8NoBOM
    } catch {
        if (Test-Path -LiteralPath $backupDll) { [IO.File]::Replace($backupDll, $dll, $stagedDll) }
        if (Test-Path -LiteralPath $active) {
            Assert-Directory $active
            Move-Item -LiteralPath $active -Destination $staged
        }
        Assert-Directory $backup
        Move-Item -LiteralPath $backup -Destination $active
        throw
    }
    'Tiled effects active; cropped pack and previous DLL retained.'
} else {
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.state -ne 'installed-awaiting-ingame-test' -or (Test-Path -LiteralPath $staged) -or
        (Test-Path -LiteralPath $stagedDll)) { throw 'Etat de restauration inattendu.' }
    Assert-Pack $tiled $active
    Assert-Pack $cropped $backup
    if ((File-Hash $dll) -ne $receipt.renderer_sha256 -or (File-Hash $backupDll) -ne $receipt.previous_renderer_sha256) {
        throw 'Le renderer actif ou sa sauvegarde a changé.'
    }
    Assert-GameClosed
    Assert-Directory $active
    Assert-Directory $backup
    Move-Item -LiteralPath $active -Destination $staged
    try {
        Move-Item -LiteralPath $backup -Destination $active
        [IO.File]::Replace($backupDll, $dll, $stagedDll)
    } catch {
        if (Test-Path -LiteralPath $active) {
            Assert-Directory $active
            Move-Item -LiteralPath $active -Destination $backup
        }
        Assert-Directory $staged
        Move-Item -LiteralPath $staged -Destination $active
        throw
    }
    $receipt.state = 'restored'
    $receipt | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding utf8NoBOM
    'Cropped effects pack and previous DLL restored.'
}
