[CmdletBinding()]
param([ValidateSet('Install', 'Verify', 'Restore')][string]$Mode = 'Install')

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$game = Resolve-WorkspaceInput 'config://bg2ee_game_root' -RequireExisting
$run = Resolve-WorkspaceInput 'icons/batches/item-description-x4-runtime-20261122-v1' -RequireExisting
$receipt = Join-Path $run 'installation.json'
$manifestPath = Join-Path $run 'runtime.json'
$dllName = 'InfinityEngine-Enhancer.dll'
$iniName = 'InfinityEngine-Enhancer.ini'
$packName = 'iee-assets/icons/ItemDescriptions-X4.registry'
$ini = Resolve-ChildPath $game $iniName -RequireExisting
$setting = 'EnableItemDescriptionX4'
$schema = 'bg2-item-description-x4-install-v1'

function Assert-Installed($State) {
    if ($State.schema -ne $schema -or $State.status -notin @('installed-pending-qa', 'validated-installed') -or
        $State.game_root -ne $game) {
        throw 'Ce test ne figure pas comme installé dans ce dossier.'
    }
    foreach ($entry in $State.targets) {
        $target = Resolve-ChildPath $game $entry.relative_path -RequireExisting
        if ((Get-FileSha256 $target) -ne $entry.installed_sha256) {
            throw "Fichier de test modifié : $($entry.relative_path)"
        }
    }
    if ((Get-IniValue ([IO.File]::ReadAllText($ini)) 'Shaders' $setting) -ne 'true') {
        throw 'Les illustrations ×4 sont désactivées dans le fichier INI.'
    }
}

function Restore-Targets($State) {
    foreach ($entry in $State.targets) {
        if ($entry.backup) {
            $backup = Resolve-ChildPath $run $entry.backup -RequireExisting
            if ((Get-FileSha256 $backup) -ne $entry.original_sha256) {
                throw "Sauvegarde altérée : $($entry.relative_path)"
            }
        }
    }
    foreach ($entry in $State.targets) {
        $target = Resolve-ChildPath $game $entry.relative_path
        if ($entry.backup) {
            Copy-FileAtomic (Resolve-ChildPath $run $entry.backup) $target
            if ((Get-FileSha256 $target) -ne $entry.original_sha256) {
                throw "Restauration incomplète : $($entry.relative_path)"
            }
        } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            Remove-Item -LiteralPath $target
        }
    }
}

if ($Mode -eq 'Verify') {
    $state = Read-JsonFile $receipt
    Assert-Installed $state
    $state | Select-Object status, asset_count, frame_count, game_root
    return
}

Assert-GameClosed
$mutexKey = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
    [Text.Encoding]::UTF8.GetBytes($game.ToUpperInvariant().TrimEnd('\'))))
$mutex = [Threading.Mutex]::new($false, "Global\BG2UpscaleGameMutation_$mutexKey")
$owned = $false
try {
    try { $owned = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $owned = $true }
    if (-not $owned) { throw 'Une autre installation modifie ce dossier de jeu.' }
    Assert-GameClosed
    if ($Mode -eq 'Restore') {
        $state = Read-JsonFile $receipt
        Assert-Installed $state
        Restore-Targets $state
        $state.status = 'restored'
        Write-JsonAtomic $receipt $state
        $state | Select-Object status, asset_count, game_root
        return
    }
    if (Test-Path -LiteralPath $receipt) {
        $state = Read-JsonFile $receipt
        if ($state.status -ne 'restored') {
            Assert-Installed $state
            $state | Select-Object status, asset_count, frame_count, game_root
            return
        }
    }

    $manifest = Read-JsonFile $manifestPath
    if ($manifest.schema -ne 'bg2-item-description-x4-runtime-v1' -or
        $manifest.asset_count -ne 976 -or $manifest.frame_count -ne 979) {
        throw 'Registre des illustrations ×4 incomplet.'
    }
    $dll = Resolve-ChildPath $run $manifest.dll -RequireExisting
    $pack = Resolve-ChildPath $run $manifest.registry -RequireExisting
    $exe = Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting
    if ((Get-FileSha256 $dll) -ne $manifest.dll_sha256 -or
        (Get-FileSha256 $pack) -ne $manifest.registry_sha256 -or
        (Get-FileSha256 $exe) -ne $manifest.baldur_real_sha256 -or
        (Get-FileSha256 (Resolve-WorkspaceInput $manifest.production -RequireExisting)) -ne $manifest.production_sha256) {
        throw 'Empreinte incompatible pour la DLL, le registre, le lot ou BaldurReal.exe.'
    }
    $newIni = Set-IniValue ([IO.File]::ReadAllText($ini)) 'Shaders' $setting 'true'
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
    $entries = foreach ($name in @($dllName, $packName, $iniName)) {
        $target = Resolve-ChildPath $game $name
        $backupRelative = $null
        $originalHash = $null
        if (Test-Path -LiteralPath $target -PathType Leaf) {
            $backupRelative = "backups/$stamp/$name"
            $backup = Resolve-ChildPath $run $backupRelative
            $originalHash = Get-FileSha256 $target
            Copy-FileAtomic $target $backup
            if ((Get-FileSha256 $backup) -ne $originalHash) { throw "Échec de sauvegarde : $name" }
        }
        [ordered]@{
            relative_path = $name
            backup = $backupRelative
            original_sha256 = $originalHash
            installed_sha256 = $null
        }
    }
    $state = [ordered]@{
        schema = $schema
        status = 'installing'
        installed_at_utc = [DateTime]::UtcNow.ToString('o')
        game_root = $game
        asset_count = $manifest.asset_count
        frame_count = $manifest.frame_count
        manifest_sha256 = Get-FileSha256 $manifestPath
        targets = @($entries)
    }
    Write-JsonAtomic $receipt $state
    try {
        Copy-FileAtomic $pack (Resolve-ChildPath $game $packName)
        Copy-FileAtomic $dll (Resolve-ChildPath $game $dllName)
        Write-TextAtomic $ini $newIni
        foreach ($entry in $state.targets) {
            $entry.installed_sha256 = Get-FileSha256 (Resolve-ChildPath $game $entry.relative_path)
        }
        if ($state.targets[0].installed_sha256 -ne $manifest.dll_sha256 -or
            $state.targets[1].installed_sha256 -ne $manifest.registry_sha256) {
            throw 'Empreintes installées incohérentes.'
        }
        $state.status = 'installed-pending-qa'
        Assert-Installed $state
        Write-JsonAtomic $receipt $state
        [pscustomobject]$state | Select-Object status, asset_count, frame_count, game_root
    } catch {
        Restore-Targets $state
        $state.status = 'restored'
        Write-JsonAtomic $receipt $state
        throw
    }
} finally {
    if ($owned) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
