[CmdletBinding()]
param(
    [ValidateSet('Install', 'Restore')] [string]$Action = 'Install',
    [string]$Candidate
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$gamePath = & python -B -c "import sys; sys.path.insert(0,sys.argv[1]); from workspace_paths import get_path; print(get_path('bg2ee_game_root'))" (Join-Path $workspace 'pipeline/scripts')
if ($LASTEXITCODE -ne 0) { throw 'Chemin BG2EE indisponible.' }
$game = (Resolve-Path -LiteralPath $gamePath).Path
$assets = Join-Path $game 'iee-assets'
$dll = Join-Path $game 'InfinityEngine-Enhancer.dll'
$previous = Join-Path $game 'InfinityEngine-Enhancer.before-shared-effect-tiles-20261121-v1.bak'
$next = Join-Path $game 'InfinityEngine-Enhancer.shared-effect-tiles-20261121-v1.tmp'
$active = Join-Path $assets 'effects'
$backup = Join-Path $assets 'effects-before-tile-sharing-20261121-v1'
$stage = Join-Path $assets 'effects-tile-sharing-stage-20261121-v1'
$local = Join-Path $PSScriptRoot 'runtime'
$receipt = Join-Path $local 'installation.json'
$proof = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'results-live.json') -Raw | ConvertFrom-Json
$tiled = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../rgba-tiles-20261121-v1/results-live.json') -Raw | ConvertFrom-Json

function Assert-GameClosed {
    if (Get-Process -Name Baldur,BaldurReal,BaldurII,InfinityLoader -ErrorAction SilentlyContinue) {
        throw 'Quitter BG2EE et InfinityLoader.'
    }
}

function Ordinary-Item([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Lien inattendu ($Path)." }
    return $item
}

function File-Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Assert-Pack($Proof, [string]$Path) {
    if (!(Ordinary-Item $Path).PSIsContainer) { throw "Dossier attendu ($Path)." }
    $expected = $Proof.files.PSObject.Properties
    if (Compare-Object @($expected.Name) @(Get-ChildItem -LiteralPath $Path -Force | ForEach-Object Name)) {
        throw "Inventaire divergent ($Path)."
    }
    foreach ($file in $expected) {
        $candidate = Join-Path $Path $file.Name
        $item = Ordinary-Item $candidate
        if ($item.Length -ne $file.Value.bytes -or (File-Hash $candidate) -ne $file.Value.sha256) {
            throw "Empreinte divergente ($candidate)."
        }
    }
}

Assert-GameClosed
foreach ($path in @($game, $assets, $dll)) { $null = Ordinary-Item $path }
if ($Action -eq 'Install') {
    if (!$Candidate) { throw 'Indiquer la DLL candidate vérifiée avec -Candidate.' }
    foreach ($path in @($previous, $next, $backup, $stage, $receipt)) {
        if (Test-Path -LiteralPath $path) { throw "Chemin déjà utilisé ($path)." }
    }
    $source = Join-Path $PSScriptRoot 'pack-live'
    $oldHash = File-Hash $dll
    $newHash = File-Hash $Candidate
    Assert-Pack $tiled $active
    $null = New-Item -ItemType Directory -Path $local -Force
    $null = New-Item -ItemType Directory -Path $stage
    foreach ($name in $proof.files.PSObject.Properties.Name) {
        Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $stage $name)
    }
    Assert-Pack $proof $stage
    Copy-Item -LiteralPath $Candidate -Destination $next
    if ((File-Hash $next) -ne $newHash -or (File-Hash $dll) -ne $oldHash) {
        throw 'Empreinte de DLL divergente.'
    }
    Assert-GameClosed
    Move-Item -LiteralPath $active -Destination $backup
    try {
        Move-Item -LiteralPath $stage -Destination $active
        [IO.File]::Replace($next, $dll, $previous)
        if ((File-Hash $dll) -ne $newHash -or (File-Hash $previous) -ne $oldHash) {
            throw 'Vérification de la DLL installée échouée.'
        }
        [ordered]@{
            state = 'installed-awaiting-ingame-test'
            previous_renderer_sha256 = $oldHash
            renderer_sha256 = $newHash
            shared_index_sha256 = $proof.files.'EffectSharedTiles-X4.index'.sha256
        } | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8NoBOM
    } catch {
        if (Test-Path -LiteralPath $previous) { [IO.File]::Replace($previous, $dll, $next) }
        if (Test-Path -LiteralPath $active) { Move-Item -LiteralPath $active -Destination $stage }
        Move-Item -LiteralPath $backup -Destination $active
        throw
    }
    'Effets mutualisés actifs. Pack tuilé et ancienne DLL sauvegardés.'
} else {
    $installed = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    $null = Ordinary-Item $previous
    if ($installed.state -ne 'installed-awaiting-ingame-test' -or
        (Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $next) -or
        (File-Hash $dll) -ne $installed.renderer_sha256 -or
        (File-Hash $previous) -ne $installed.previous_renderer_sha256) {
        throw 'État de restauration inattendu.'
    }
    Assert-Pack $proof $active
    Assert-Pack $tiled $backup
    Assert-GameClosed
    Move-Item -LiteralPath $active -Destination $stage
    try {
        Move-Item -LiteralPath $backup -Destination $active
        [IO.File]::Replace($previous, $dll, $next)
        $installed.state = 'restored'
        $installed | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8NoBOM
    } catch {
        if (Test-Path -LiteralPath $next) { [IO.File]::Replace($next, $dll, $previous) }
        if (Test-Path -LiteralPath $active) { Move-Item -LiteralPath $active -Destination $backup }
        Move-Item -LiteralPath $stage -Destination $active
        throw
    }
    'Pack tuilé et ancienne DLL restaurés.'
}
