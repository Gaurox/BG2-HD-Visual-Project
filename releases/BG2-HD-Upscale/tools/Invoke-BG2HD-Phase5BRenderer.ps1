[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateSet('Audit','Stage','Restore')]
    [string]$Action,
    [Parameter(Mandatory)] [string]$GameRoot,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$SessionRoot,
    [switch]$KeepStagedRenderer
)

# This tool is deliberately separate from the WeiDU package.  The renderer is
# an external prerequisite until its real-game gates have passed.  Stage can
# only publish the already frozen, manifest-verified candidate; Restore refuses
# to overwrite a renderer changed outside this controlled session.
$ErrorActionPreference = 'Stop'

function Resolve-Directory([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "$Label introuvable : $Path" }
    return (Resolve-Path -LiteralPath $Path).Path
}
function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-', '') }
    finally { $sha.Dispose() }
}
function Read-Json([string]$Path) { return Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json }
function Write-JsonAtomic([string]$Path, [object]$Value) {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $temporary = Join-Path $parent ('.' + [IO.Path]::GetFileName($Path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 16), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}
function Relative-WindowsPath([string]$Path) { return $Path.Replace('/', '\') }
function Get-ExpectedFiles([object]$Manifest) {
    $files = @($Manifest.files)
    if ($files.Count -ne 8) { throw 'Inventaire renderer inattendu : huit fichiers sont requis.' }
    $paths = @($files | ForEach-Object { [string]$_.path })
    $expected = @(
        'InfinityEngine-Enhancer.dll',
        'InfinityEngine-Enhancer.sample.ini',
        'iee-textures/iee_water_dudv.rgba',
        'iee-textures/iee_water_foam.rgba',
        'iee-textures/iee_water_normal.rgba',
        'iee-textures/README.md',
        'override/fpSEAM.glsl',
        'override/M_IEEE.lua'
    )
    if (Compare-Object ($expected | Sort-Object) ($paths | Sort-Object)) { throw 'Inventaire renderer non approuve.' }
    return $files
}

$game = Resolve-Directory $GameRoot 'Dossier du jeu'
$release = Resolve-Directory $ReleaseRoot 'Racine de release'
$manifestPath = Join-Path $release 'manifests\renderer-bundle.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Manifeste renderer absent : $manifestPath" }
$manifest = Read-Json $manifestPath
if ($manifest.status -ne 'frozen-awaiting-clean-game-validation') { throw "Statut renderer non eligible : $($manifest.status)" }
$bundle = Join-Path $release ('release-inputs\renderer\' + $manifest.bundle_id)
$expectedFiles = Get-ExpectedFiles $manifest

function Assert-Candidate() {
    if (-not (Test-Path -LiteralPath $bundle -PathType Container)) { throw "Bundle renderer absent : $bundle" }
    foreach ($file in $expectedFiles) {
        $source = Join-Path $bundle (Relative-WindowsPath $file.path)
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Fichier candidat absent : $($file.path)" }
        if ((Get-Item -LiteralPath $source).Length -ne [int64]$file.bytes -or (Get-Sha256 $source) -ne $file.sha256) {
            throw "Fichier candidat invalide : $($file.path)"
        }
    }
}
function New-DefaultSessionRoot() {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    return Join-Path $release ("validation\phase5b-$stamp")
}
function Get-SessionRootForStage() {
    if ($SessionRoot) { return [IO.Path]::GetFullPath($SessionRoot) }
    return New-DefaultSessionRoot
}
function Get-SessionRootForRead() {
    if (-not $SessionRoot) { throw 'SessionRoot est obligatoire pour Restore.' }
    return Resolve-Directory $SessionRoot 'Session Phase 5B'
}
function Get-SessionState([string]$Root) {
    $statePath = Join-Path $Root 'renderer-session.json'
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { throw "Etat de session absent : $statePath" }
    return Read-Json $statePath
}

function Invoke-Audit() {
    Assert-Candidate
    $comparison = foreach ($file in $expectedFiles) {
        if ($file.path -eq 'InfinityEngine-Enhancer.sample.ini') { continue }
        $destination = Join-Path $game (Relative-WindowsPath $file.path)
        $exists = Test-Path -LiteralPath $destination -PathType Leaf
        [ordered]@{
            path = $file.path
            candidate_sha256 = $file.sha256
            destination_exists = $exists
            destination_sha256 = if ($exists) { Get-Sha256 $destination } else { $null }
            matches_candidate = if ($exists) { (Get-Sha256 $destination) -eq $file.sha256 } else { $false }
        }
    }
    [ordered]@{
        candidate_bundle_id = $manifest.bundle_id
        candidate_status = $manifest.status
        game_root = $game
        files = @($comparison)
    } | ConvertTo-Json -Depth 8
}
function Invoke-Stage() {
    Assert-Candidate
    $root = Get-SessionRootForStage
    if (Test-Path -LiteralPath $root) { throw "Session deja existante : $root" }
    New-Item -ItemType Directory -Path $root | Out-Null
    $backupRoot = Join-Path $root 'original'
    $records = @()
    try {
        foreach ($file in $expectedFiles) {
            if ($file.path -eq 'InfinityEngine-Enhancer.sample.ini') { continue }
            $relative = Relative-WindowsPath $file.path
            $destination = Join-Path $game $relative
            $wasPresent = Test-Path -LiteralPath $destination -PathType Leaf
            $backup = Join-Path $backupRoot $relative
            $beforeHash = $null
            if ($wasPresent) {
                $beforeHash = Get-Sha256 $destination
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
                Copy-Item -LiteralPath $destination -Destination $backup -ErrorAction Stop
                if ((Get-Sha256 $backup) -ne $beforeHash) { throw "Sauvegarde invalide : $relative" }
            }
            $records += [ordered]@{ path=$file.path; existed_before=$wasPresent; before_sha256=$beforeHash; staged_sha256=$file.sha256 }
        }
        $state = [ordered]@{
            schema_version = 1
            phase = 'backed-up'
            created_at = (Get-Date).ToUniversalTime().ToString('o')
            game_root = $game
            bundle_id = $manifest.bundle_id
            candidate_manifest_sha256 = Get-Sha256 $manifestPath
            files = @($records)
        }
        Write-JsonAtomic (Join-Path $root 'renderer-session.json') $state
        foreach ($record in $records) {
            $source = Join-Path $bundle (Relative-WindowsPath $record.path)
            $destination = Join-Path $game (Relative-WindowsPath $record.path)
            if ($record.staged_sha256 -eq $record.before_sha256) { continue }
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
            Copy-Item -LiteralPath $source -Destination $destination -Force -ErrorAction Stop
            if ((Get-Sha256 $destination) -ne $record.staged_sha256) { throw "Publication invalide : $($record.path)" }
        }
        $state.phase = 'staged'
        $state | Add-Member -Force -NotePropertyName staged_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'))
        Write-JsonAtomic (Join-Path $root 'renderer-session.json') $state
        [ordered]@{ session_root=$root; phase='staged'; renderer_sha256=(Get-Sha256 (Join-Path $game 'InfinityEngine-Enhancer.dll')) } | ConvertTo-Json
    } catch {
        # A partial Stage is restored from its own byte-verified snapshot.
        if (Test-Path -LiteralPath (Join-Path $root 'renderer-session.json')) {
            try { Invoke-Restore -Root $root -AllowBackedUp } catch {}
        }
        throw
    }
}
function Invoke-Restore([string]$Root, [switch]$AllowBackedUp) {
    $state = Get-SessionState $Root
    if ($state.schema_version -ne 1 -or $state.game_root -ne $game) { throw 'Session renderer non associee a ce jeu.' }
    if ($state.phase -notin @('staged','backed-up')) { throw "Session non restaurable dans son etat actuel : $($state.phase)" }
    if ($state.phase -eq 'backed-up' -and -not $AllowBackedUp) { throw 'La publication renderer n a pas ete confirmee ; intervention manuelle requise.' }
    foreach ($record in @($state.files)) {
        $destination = Join-Path $game (Relative-WindowsPath $record.path)
        if (-not (Test-Path -LiteralPath $destination -PathType Leaf) -or (Get-Sha256 $destination) -ne $record.staged_sha256) {
            throw "Refus de restaurer : fichier modifie hors session : $($record.path)"
        }
    }
    foreach ($record in @($state.files)) {
        $destination = Join-Path $game (Relative-WindowsPath $record.path)
        if ($record.existed_before) {
            $backup = Join-Path $Root ('original\' + (Relative-WindowsPath $record.path))
            if (-not (Test-Path -LiteralPath $backup -PathType Leaf) -or (Get-Sha256 $backup) -ne $record.before_sha256) { throw "Sauvegarde invalide : $($record.path)" }
            Copy-Item -LiteralPath $backup -Destination $destination -Force -ErrorAction Stop
            if ((Get-Sha256 $destination) -ne $record.before_sha256) { throw "Restauration invalide : $($record.path)" }
        } else {
            Remove-Item -LiteralPath $destination -ErrorAction Stop
        }
    }
    $state.phase = if ($KeepStagedRenderer) { 'staged' } else { 'restored' }
    $state | Add-Member -Force -NotePropertyName restored_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'))
    Write-JsonAtomic (Join-Path $Root 'renderer-session.json') $state
    [ordered]@{ session_root=$Root; phase=$state.phase; renderer_sha256=(Get-Sha256 (Join-Path $game 'InfinityEngine-Enhancer.dll')) } | ConvertTo-Json
}

switch ($Action) {
    'Audit' { Invoke-Audit; exit 0 }
    'Stage' { Invoke-Stage; exit 0 }
    'Restore' { Invoke-Restore -Root (Get-SessionRootForRead); exit 0 }
}
