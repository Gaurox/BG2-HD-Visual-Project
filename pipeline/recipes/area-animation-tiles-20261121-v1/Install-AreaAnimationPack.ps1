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
$previous = Join-Path $game 'InfinityEngine-Enhancer.before-area-archive-20261121-v1.bak'
$next = Join-Path $game 'InfinityEngine-Enhancer.area-archive-20261121-v1.tmp'
$active = Join-Path $assets 'area-animation-pack'
$stage = Join-Path $assets 'area-animation-pack-stage-20261121-v1'
$run = Join-Path $PSScriptRoot 'run'
$receipt = Join-Path $run 'installation.json'

function Assert-GameClosed {
    if (Get-Process -Name Baldur,BaldurReal,BaldurII,InfinityLoader -ErrorAction SilentlyContinue) {
        throw 'Quitter BG2EE et InfinityLoader.'
    }
}

function Assert-OrdinaryItem([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Lien inattendu ($Path)."
    }
}

function File-Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }

Assert-GameClosed
Assert-OrdinaryItem $game
Assert-OrdinaryItem $assets
Assert-OrdinaryItem $dll
if ($Action -eq 'Install') {
    if (!$Candidate) { throw 'Indiquer la DLL candidate vérifiée avec -Candidate.' }
    foreach ($path in @($previous, $next, $active, $stage, $receipt)) {
        if (Test-Path -LiteralPath $path) { throw "Chemin déjà utilisé ($path)." }
    }
    $source = Join-Path $run 'verify-assets/area-animation-pack'
    $proof = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'results.json') -Raw | ConvertFrom-Json
    $oldHash = File-Hash $dll
    $newHash = File-Hash $Candidate
    New-Item -ItemType Directory -Path $stage | Out-Null
    foreach ($file in (Get-ChildItem -LiteralPath $source -File)) {
        $stagedFile = Join-Path $stage $file.Name
        Copy-Item -LiteralPath $file.FullName -Destination $stagedFile
        $hash = if ($file.Name -eq 'AreaAnimations-X4.zip') { $proof.tiled_zip_sha256 } else { File-Hash $file.FullName }
        if ((File-Hash $stagedFile) -ne $hash) { throw "Copie divergente ($stagedFile)." }
    }
    Copy-Item -LiteralPath $Candidate -Destination $next
    if ((File-Hash $next) -ne $newHash -or (File-Hash $dll) -ne $oldHash) {
        throw 'Empreinte de DLL divergente.'
    }
    Assert-GameClosed
    Move-Item -LiteralPath $stage -Destination $active
    try {
        [IO.File]::Replace($next, $dll, $previous)
        if ((File-Hash $dll) -ne $newHash -or (File-Hash $previous) -ne $oldHash) {
            throw 'Empreinte de DLL divergente après activation.'
        }
        [ordered]@{
            state = 'installed-awaiting-ingame-test'
            previous_renderer_sha256 = $oldHash
            renderer_sha256 = $newHash
            archive_sha256 = $proof.tiled_zip_sha256
            index_count = @(Get-ChildItem -LiteralPath $active -File -Filter '*.index').Count
        } | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8NoBOM
    } catch {
        if (Test-Path -LiteralPath $previous) { [IO.File]::Replace($previous, $dll, $next) }
        Move-Item -LiteralPath $active -Destination $stage
        throw
    }
    'Pack actif. Anciens fichiers RGBA et ancienne DLL disponibles.'
} else {
    $installed = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    Assert-OrdinaryItem $active
    Assert-OrdinaryItem $previous
    if ($installed.state -ne 'installed-awaiting-ingame-test' -or
        (Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $next) -or
        (File-Hash $dll) -ne $installed.renderer_sha256 -or
        (File-Hash $previous) -ne $installed.previous_renderer_sha256) {
        throw 'Etat de restauration inattendu.'
    }
    Move-Item -LiteralPath $active -Destination $stage
    try {
        [IO.File]::Replace($previous, $dll, $next)
        $installed.state = 'restored'
        $installed | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8NoBOM
    } catch {
        if (Test-Path -LiteralPath $next) { [IO.File]::Replace($next, $dll, $previous) }
        Move-Item -LiteralPath $stage -Destination $active
        throw
    }
    'Ancienne DLL et lecture des RGBA restaurées.'
}
