[CmdletBinding()]
param([ValidateSet('Install', 'Restore')] [string]$Action = 'Install')

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$game = (& python -B -c "import sys; sys.path.insert(0,sys.argv[1]); from workspace_paths import get_path; print(get_path('bg2ee_game_root'))" (Join-Path $workspace 'pipeline/scripts'))
if ($LASTEXITCODE -ne 0) { throw 'Chemin BG2EE indisponible.' }
$game = (Resolve-Path -LiteralPath $game).Path
$assetParent = (Resolve-Path -LiteralPath (Join-Path $game 'iee-assets')).Path
if ((Split-Path -Parent $assetParent) -ne $game) { throw 'Dossier iee-assets inattendu.' }
$active = Join-Path $assetParent 'effects'
$backup = Join-Path $assetParent 'effects-before-crop-20261121-v1'
$staged = Join-Path $assetParent 'effects-crop-stage-20261121-v1'
$retired = Join-Path $assetParent 'effects-crop-retired-20261121-v1'
$dll = Join-Path $game 'InfinityEngine-Enhancer.dll'
$backupDll = Join-Path $game 'InfinityEngine-Enhancer.before-effects-crop-20261121-v1.dll'
$stagedDll = Join-Path $game 'InfinityEngine-Enhancer.crop-stage-20261121-v1.dll'
$receipt = Join-Path $PSScriptRoot 'packs/installed.json'

function Assert-GameClosed {
    if (Get-Process -Name Baldur,BaldurReal,BaldurII,InfinityLoader -ErrorAction SilentlyContinue) {
        throw 'Quitter BG2EE et InfinityLoader.'
    }
}
function Assert-Directory([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    if (!$item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        $item.FullName -ne $Path -or (Split-Path -Parent $item.FullName) -ne $assetParent) {
        throw "Dossier effets inattendu ($Path)"
    }
}
function File-Hash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Assert-Registry($Metadata, $Directory) {
    foreach ($name in @('EffectAnimations-X4.registry', 'manifest.json')) {
        if ((File-Hash (Join-Path $Directory $name)) -ne $Metadata.files.$name.sha256) {
            throw "Le pack actif a changé ($name)"
        }
    }
}

Assert-GameClosed
Assert-Directory $active
$result = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'results-live.json') -Raw | ConvertFrom-Json
if ($Action -eq 'Install') {
    foreach ($path in @($backup, $staged, $backupDll, $stagedDll, $receipt)) {
        if (Test-Path -LiteralPath $path) { throw "Chemin déjà utilisé ($path)" }
    }
    Assert-Registry $result $active
    if (Test-Path -LiteralPath (Join-Path $active 'EffectStorage-X4.index')) {
        throw 'Le pack actif utilise un nouvel index de partage.'
    }
    $renderer = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'renderer.json') -Raw | ConvertFrom-Json
    $rendererInput = Join-Path $PSScriptRoot 'packs/renderer/InfinityEngine-Enhancer.dll'
    if ((File-Hash $rendererInput) -ne $renderer.sha256) { throw 'DLL candidat modifié.' }
    $beforeDll = File-Hash $dll
    New-Item -ItemType Directory -Path $staged | Out-Null
    Assert-Directory $staged
    foreach ($file in $result.files.PSObject.Properties) {
        $target = Join-Path $staged $file.Name
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot "packs/live/$($file.Name)") -Destination $target
        if ((File-Hash $target) -ne $file.Value.sha256) { throw "Copie invalide ($target)" }
    }
    Copy-Item -LiteralPath $rendererInput -Destination $stagedDll
    if ((File-Hash $stagedDll) -ne $renderer.sha256) { throw 'Copie du renderer invalide.' }
    Assert-GameClosed
    Assert-Registry $result $active
    if ((File-Hash $dll) -ne $beforeDll) { throw 'Le renderer actif a changé pendant la préparation.' }
    Move-Item -LiteralPath $active -Destination $backup
    try {
        Move-Item -LiteralPath $staged -Destination $active
        [IO.File]::Replace($stagedDll, $dll, $backupDll)
        [ordered]@{
            state = 'installed-awaiting-ingame-test'
            previous_renderer_sha256 = $beforeDll
            renderer_sha256 = $renderer.sha256
            original_pack = 'config://bg2ee_game_root/iee-assets/effects-before-crop-20261121-v1'
            original_renderer = 'config://bg2ee_game_root/InfinityEngine-Enhancer.before-effects-crop-20261121-v1.dll'
            registry_sha256 = $result.files.'EffectAnimations-X4.registry'.sha256
        } | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8NoBOM
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
    'Cropped effects active; original pack and DLL retained.'
} else {
    $state = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    if ($state.state -ne 'installed-awaiting-ingame-test' -or
        (Test-Path -LiteralPath $retired) -or (Test-Path -LiteralPath $stagedDll)) {
        throw 'Etat de restauration inattendu.'
    }
    Assert-Directory $backup
    Assert-Registry $result $backup
    foreach ($file in $result.files.PSObject.Properties) {
        if ((File-Hash (Join-Path $active $file.Name)) -ne $file.Value.sha256) {
            throw "Pack modifié ($($file.Name))"
        }
    }
    if ((File-Hash $dll) -ne $state.renderer_sha256 -or
        (File-Hash $backupDll) -ne $state.previous_renderer_sha256) {
        throw 'Le renderer actif ou sa sauvegarde a changé.'
    }
    Assert-GameClosed
    Move-Item -LiteralPath $active -Destination $retired
    try {
        Move-Item -LiteralPath $backup -Destination $active
        [IO.File]::Replace($backupDll, $dll, $stagedDll)
    } catch {
        if (Test-Path -LiteralPath $active) {
            Assert-Directory $active
            Move-Item -LiteralPath $active -Destination $backup
        }
        Assert-Directory $retired
        Move-Item -LiteralPath $retired -Destination $active
        throw
    }
    $state.state = 'restored'
    $state | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8NoBOM
    'Original effects pack and DLL restored.'
}
