[CmdletBinding()]
param(
    [ValidateSet('Install', 'Verify', 'Restore')][string]$Mode = 'Install',
    [string]$Run = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-probe-20261001-v1',
    [string]$Manifest = 'pipeline/runtime/manifests/iee-sprite-p4-probe-20261001-v1.json',
    [string]$CatalogReceipt = 'sprite/catalogs/palette-q3m-human-fighters-x4-20261001-v1/ingame-installation/active-test.json'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$runRoot = Resolve-WorkspaceInput $Run -RequireExisting
$gameRoot = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$runtimePath = Resolve-WorkspaceInput $Manifest -RequireExisting
$runtime = Read-JsonFile $runtimePath
$stateRoot = Join-Path $runRoot 'ingame-probe'
$statePath = Join-Path $stateRoot 'active-test.json'
$runtimeState = Join-Path $stateRoot 'runtime'
$iniPath = Resolve-ChildPath $gameRoot 'InfinityEngine-Enhancer.ini' -RequireExisting
$dllPath = Resolve-ChildPath $gameRoot 'InfinityEngine-Enhancer.dll' -RequireExisting
$catalogPath = Resolve-ChildPath $gameRoot 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting
$receiptPath = Resolve-WorkspaceInput $CatalogReceipt -RequireExisting
$captures = Join-Path $runRoot 'captures'

if ($Mode -ne 'Install') {
    $state = Read-JsonFile $statePath
    if ($state.schema -ne 'bg2-sprite-p4-probe-install-v1' -or $state.status -ne 'installed' -or
        $state.game_root -ne $gameRoot -or $state.runtime_manifest -ne $runtimePath -or
        $state.receipt_path -ne $receiptPath) { throw 'Identité de transaction P4 incohérente.' }
}

if ($Mode -eq 'Verify') {
    $state = Read-JsonFile $statePath
    & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Verify -Manifest $runtimePath -StateRoot $runtimeState
    if ((Get-FileSha256 $iniPath) -ne $state.ini_after_sha256 -or
        (Get-FileSha256 $catalogPath) -ne $state.catalog_sha256 -or
        (Get-FileSha256 $receiptPath) -ne $state.receipt_after_sha256) {
        throw 'INI, catalogue ou reçu diffère de la transaction P4.'
    }
    [pscustomobject]@{ Status = 'verified-probe-ready'; Captures = $captures; CatalogChanged = $false; Filter = 'Nearest'; Scale = 4 }
    return
}

Assert-GameClosed
if ($Mode -eq 'Restore') {
    $state = Read-JsonFile $statePath
    if ((Get-FileSha256 $dllPath) -ne $runtime.dll.sha256 -or
        (Get-FileSha256 $iniPath) -ne $state.ini_after_sha256 -or
        (Get-FileSha256 $catalogPath) -ne $state.catalog_sha256 -or
        (Get-FileSha256 $receiptPath) -ne $state.receipt_after_sha256) {
        throw 'Installation changée depuis P4 ; restauration automatique refusée pour préserver ces changements.'
    }
    if ((Get-FileSha256 (Join-Path $stateRoot 'ini-before.bin')) -ne $state.ini_before_sha256 -or
        (Get-FileSha256 (Join-Path $stateRoot 'receipt-before.json')) -ne $state.receipt_before_sha256) {
        throw 'Sauvegarde P4 incohérente.'
    }
    & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Restore -StateRoot $runtimeState
    Copy-FileAtomic (Join-Path $stateRoot 'ini-before.bin') $iniPath
    Copy-FileAtomic (Join-Path $stateRoot 'receipt-before.json') $receiptPath
    $state.status = 'restored'
    Write-JsonAtomic (Join-Path $stateRoot 'restoration.json') $state
    Remove-Item -LiteralPath $statePath
    [pscustomobject]@{ Status = 'restored'; CatalogChanged = $false; CapturesPreserved = $true }
    return
}

if (Test-Path -LiteralPath $stateRoot) { throw 'Transaction P4 déjà présente ; utiliser Verify ou un nouveau run.' }
$previous = Read-JsonFile (Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-character-cold-resolve-20261001-v1.json' -RequireExisting)
if ((Get-FileSha256 $dllPath) -ne $previous.dll.sha256 -or
    (Get-FileSha256 $catalogPath) -ne '637DBC809EAD7A9AD2A771BB760F5C0042109C5A4B6A19BE68A75CC41D50E0B8') {
    throw 'Baseline x4 / runtime corrigé différente ; aucun remplacement.'
}
$ini = [IO.File]::ReadAllText($iniPath)
if ((Get-IniValue $ini 'Shaders' 'CreatureSpriteFilter') -ne 'Nearest') { throw 'Filtre baseline inattendu.' }
$receipt = Read-JsonFile $receiptPath
if ($receipt.runtime_id -ne $previous.runtime_id -or
    $receipt.catalog_sha256 -ne (Get-FileSha256 $catalogPath)) { throw 'Reçu baseline incohérent.' }
New-Item -ItemType Directory -Path $stateRoot | Out-Null
New-Item -ItemType Directory -Path $captures -Force | Out-Null
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $stateRoot 'ini-before.bin')
Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $stateRoot 'receipt-before.json')
$state = [ordered]@{
    schema = 'bg2-sprite-p4-probe-install-v1'; status = 'installing'; game_root = $gameRoot
    runtime_manifest = $runtimePath; runtime_id = $runtime.runtime_id
    receipt_path = $receiptPath
    ini_before_sha256 = Get-FileSha256 $iniPath; receipt_before_sha256 = Get-FileSha256 $receiptPath
    catalog_sha256 = Get-FileSha256 $catalogPath
}
Write-JsonAtomic $statePath $state
try {
    & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Install -Manifest $runtimePath -StateRoot $runtimeState
    $ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpriteP4Probe' 'true'
    $ini = Set-IniValue $ini 'Shaders' 'CreatureSpriteP4Output' $captures
    Write-TextAtomic $iniPath $ini
    $receipt.runtime_id = $runtime.runtime_id
    $receipt.runtime_manifest = $runtimePath
    Write-JsonAtomic $receiptPath $receipt
    $state.status = 'installed'
    $state.ini_after_sha256 = Get-FileSha256 $iniPath
    $state.receipt_after_sha256 = Get-FileSha256 $receiptPath
    $state.installed_at_utc = [DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
} catch {
    $failure = $_
    if (Test-Path -LiteralPath (Join-Path $runtimeState 'active-test.json')) {
        & (Join-Path $PSScriptRoot 'Install-IEE-Runtime-Test.ps1') -Mode Restore -StateRoot $runtimeState
    }
    Copy-FileAtomic (Join-Path $stateRoot 'ini-before.bin') $iniPath
    Copy-FileAtomic (Join-Path $stateRoot 'receipt-before.json') $receiptPath
    $state.status = 'rolled-back'
    Write-JsonAtomic $statePath $state
    throw $failure
}
& $PSCommandPath -Mode Verify -Run $Run -Manifest $Manifest -CatalogReceipt $CatalogReceipt
