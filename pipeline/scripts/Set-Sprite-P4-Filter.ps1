[CmdletBinding()]
param(
    [ValidateSet('Install', 'Verify', 'Select', 'Restore')][string]$Mode = 'Install',
    [ValidateSet('Nearest', 'Box', 'Mipmaps')][string]$Filter = 'Box',
    [string]$Run = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-filters-20261001-v1',
    [string]$Manifest = 'pipeline/runtime/manifests/iee-sprite-p4-filters-20261001-v1.json',
    [string]$CatalogReceipt = 'sprite/catalogs/palette-q3m-human-fighters-x4-20261001-v1/ingame-installation/active-test.json'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')
$runRoot = Resolve-WorkspaceInput $Run -RequireExisting
$game = Resolve-BG2WorkspacePath -Key bg2ee_game_root -RequireExisting
$manifestPath = Resolve-WorkspaceInput $Manifest -RequireExisting
$runtime = Read-JsonFile $manifestPath
$stateRoot = Join-Path $runRoot 'ingame-filter'
$statePath = Join-Path $stateRoot 'active-test.json'
$runtimeState = Join-Path $stateRoot 'runtime'
$iniPath = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
$dllPath = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$catalogPath = Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting
$receiptPath = Resolve-WorkspaceInput $CatalogReceipt -RequireExisting
$catalogHash = '637DBC809EAD7A9AD2A771BB760F5C0042109C5A4B6A19BE68A75CC41D50E0B8'
if ($runtime.runtime_id -ne 'iee-sprite-p4-filters-20261001-v1' -or
    @($runtime.shaders).Count -ne 3) { throw 'Manifeste P4 filtres incompatible.' }

function Assert-Current($State) {
    if ($State.schema -ne 'bg2-sprite-p4-filter-install-v1' -or $State.status -ne 'installed' -or
        $State.game_root -ne $game -or $State.runtime_manifest -ne $manifestPath -or
        $State.receipt_path -ne $receiptPath) { throw 'Identité de transaction P4 incohérente.' }
    $expectedTargets = @{'ini-before.bin' = $iniPath; 'receipt-before.json' = $receiptPath}
    foreach ($shader in $runtime.shaders) {
        $expectedTargets[('before-' + [IO.Path]::GetFileName($shader.target))] = Resolve-ChildPath $game $shader.target
    }
    if (@($State.backups).Count -ne $expectedTargets.Count -or
        @($State.backups.backup | Select-Object -Unique).Count -ne $expectedTargets.Count -or
        $State.catalog_sha256 -ne $catalogHash) { throw 'Contrat de sauvegarde P4 incohérent.' }
    foreach ($file in $State.backups) {
        if (-not $expectedTargets.ContainsKey([string]$file.backup) -or
            $file.target -ne $expectedTargets[[string]$file.backup]) { throw 'Cible de restauration P4 hors périmètre.' }
    }
    & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Verify -Manifest $manifestPath -StateRoot $runtimeState | Out-Null
    if ((Get-FileSha256 $iniPath) -ne $State.ini_after_sha256 -or
        (Get-FileSha256 $catalogPath) -ne $State.catalog_sha256 -or
        (Get-FileSha256 $receiptPath) -ne $State.receipt_after_sha256) { throw 'INI, catalogue ou reçu changé ; transaction refusée.' }
    foreach ($shader in $runtime.shaders) {
        $target = Resolve-ChildPath $game ([string]$shader.target) -RequireExisting
        if ((Get-FileSha256 $target) -ne $shader.sha256) { throw "Shader installé changé : $($shader.target)" }
    }
}

function Set-FilterIni([string]$Text, [string]$Value, [string]$Output) {
    $Text = Set-IniValue $Text 'Shaders' 'CreatureSpriteFilter' $Value
    $Text = Set-IniValue $Text 'Shaders' 'CreatureSpriteFilterAnimation' '0x6110'
    $Text = Set-IniValue $Text 'Shaders' 'EnableCreatureSpriteP4Probe' 'true'
    return (Set-IniValue $Text 'Shaders' 'CreatureSpriteP4Output' $Output)
}

function Set-Receipt($Receipt, [string]$Value) {
    $Receipt.runtime_id = $runtime.runtime_id
    $Receipt.runtime_manifest = $manifestPath
    $Receipt.creature_sprite_filter = $Value
    $Receipt | Add-Member -NotePropertyName creature_sprite_filter_animation -NotePropertyValue '0x6110' -Force
    return $Receipt
}

if ($Mode -ne 'Install') {
    $state = Read-JsonFile $statePath
    Assert-Current $state
    if ($Mode -eq 'Verify') {
        [pscustomobject]@{ Status = 'verified'; Filter = $state.filter; Animation = '0x6110'; Scale = 4; Captures = $state.captures }
        return
    }
    Assert-GameClosed
    if ($Mode -eq 'Select') {
        $beforeIni = [IO.File]::ReadAllBytes($iniPath)
        $beforeReceipt = [IO.File]::ReadAllBytes($receiptPath)
        $beforeState = [IO.File]::ReadAllBytes($statePath)
        $captures = Join-Path $runRoot ('captures/' + $Filter.ToLowerInvariant())
        New-Item -ItemType Directory -Path $captures -Force | Out-Null
        try {
            Write-TextAtomic $iniPath (Set-FilterIni ([IO.File]::ReadAllText($iniPath)) $Filter $captures)
            Write-JsonAtomic $receiptPath (Set-Receipt (Read-JsonFile $receiptPath) $Filter)
            $state.filter = $Filter; $state.captures = $captures
            $state.ini_after_sha256 = Get-FileSha256 $iniPath
            $state.receipt_after_sha256 = Get-FileSha256 $receiptPath
            Write-JsonAtomic $statePath $state
        } catch {
            [IO.File]::WriteAllBytes($iniPath, $beforeIni)
            [IO.File]::WriteAllBytes($receiptPath, $beforeReceipt)
            [IO.File]::WriteAllBytes($statePath, $beforeState)
            throw
        }
        & $PSCommandPath -Mode Verify -Run $Run -Manifest $Manifest -CatalogReceipt $CatalogReceipt
        return
    }
    foreach ($file in $state.backups) {
        if ((Get-FileSha256 (Resolve-ChildPath $stateRoot $file.backup -RequireExisting)) -ne $file.sha256) {
            throw "Sauvegarde P4 incohérente : $($file.backup)"
        }
    }
    if ((Get-FileSha256 (Join-Path $runtimeState 'previous-InfinityEngine-Enhancer.dll')) -ne $state.dll_before_sha256) {
        throw 'Sauvegarde DLL P4 incohérente.'
    }
    & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Restore -StateRoot $runtimeState | Out-Null
    foreach ($file in $state.backups) { Copy-FileAtomic (Join-Path $stateRoot $file.backup) $file.target }
    $state.status = 'restored'
    Write-JsonAtomic (Join-Path $stateRoot 'restoration.json') $state
    Remove-Item -LiteralPath $statePath
    [pscustomobject]@{ Status = 'restored'; CatalogChanged = $false; CapturesPreserved = $true }
    return
}

Assert-GameClosed
if (Test-Path -LiteralPath $stateRoot) { throw 'Run déjà utilisé ; Verify/Select/Restore ou nouveau run requis.' }
$previous = Read-JsonFile (Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-sprite-p4-probe-20261001-v1.json' -RequireExisting)
if ((Get-FileSha256 $dllPath) -ne $previous.dll.sha256 -or
    (Get-FileSha256 $iniPath) -ne $runtime.baseline.ini_sha256 -or
    (Get-FileSha256 $catalogPath) -ne $catalogHash) { throw 'Baseline P4 sonde/x4 différente ; aucun remplacement.' }
$receipt = Read-JsonFile $receiptPath
if ($receipt.runtime_id -ne $previous.runtime_id -or $receipt.catalog_sha256 -ne $catalogHash) { throw 'Reçu P4 baseline incohérent.' }
foreach ($shader in $runtime.shaders) {
    if ((Get-FileSha256 (Resolve-WorkspaceInput $shader.path -RequireExisting)) -ne $shader.sha256 -or
        (Get-FileSha256 (Resolve-ChildPath $game $shader.target -RequireExisting)) -ne $shader.baseline_sha256) {
        throw "Shader source ou baseline changé : $($shader.target)"
    }
}
$files = @(
    [pscustomobject]@{ target = $iniPath; backup = 'ini-before.bin' },
    [pscustomobject]@{ target = $receiptPath; backup = 'receipt-before.json' }
)
foreach ($shader in $runtime.shaders) {
    $files += [pscustomobject]@{ target = Resolve-ChildPath $game $shader.target -RequireExisting; backup = ('before-' + [IO.Path]::GetFileName($shader.target)) }
}
New-Item -ItemType Directory -Path $stateRoot | Out-Null
foreach ($file in $files) {
    $file | Add-Member -NotePropertyName sha256 -NotePropertyValue (Get-FileSha256 $file.target)
    Copy-Item -LiteralPath $file.target -Destination (Join-Path $stateRoot $file.backup)
}
$captures = Join-Path $runRoot ('captures/' + $Filter.ToLowerInvariant())
New-Item -ItemType Directory -Path $captures -Force | Out-Null
$state = [ordered]@{
    schema = 'bg2-sprite-p4-filter-install-v1'; status = 'installing'; game_root = $game
    runtime_manifest = $manifestPath; runtime_id = $runtime.runtime_id; receipt_path = $receiptPath
    catalog_sha256 = $catalogHash; dll_before_sha256 = Get-FileSha256 $dllPath
    backups = $files; filter = $Filter; captures = $captures
}
Write-JsonAtomic $statePath $state
try {
    & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Install -Manifest $manifestPath -StateRoot $runtimeState | Out-Null
    foreach ($shader in $runtime.shaders) {
        Copy-FileAtomic (Resolve-WorkspaceInput $shader.path -RequireExisting) (Resolve-ChildPath $game $shader.target)
    }
    Write-TextAtomic $iniPath (Set-FilterIni ([IO.File]::ReadAllText($iniPath)) $Filter $captures)
    Write-JsonAtomic $receiptPath (Set-Receipt $receipt $Filter)
    $state.status = 'installed'
    $state.ini_after_sha256 = Get-FileSha256 $iniPath
    $state.receipt_after_sha256 = Get-FileSha256 $receiptPath
    $state.installed_at_utc = [DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
} catch {
    $failure = $_
    if (Test-Path -LiteralPath (Join-Path $runtimeState 'active-test.json')) {
        & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Restore -StateRoot $runtimeState | Out-Null
    }
    foreach ($file in $files) { Copy-FileAtomic (Join-Path $stateRoot $file.backup) $file.target }
    $state.status = 'rolled-back'
    Write-JsonAtomic $statePath $state
    throw $failure
}
& $PSCommandPath -Mode Verify -Run $Run -Manifest $Manifest -CatalogReceipt $CatalogReceipt
