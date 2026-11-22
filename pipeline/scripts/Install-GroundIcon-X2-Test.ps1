[CmdletBinding()]
param([ValidateSet('Install', 'Verify', 'Restore')][string]$Mode = 'Install')

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$game = Resolve-WorkspaceInput 'config://bg2ee_game_root' -RequireExisting
$run = Resolve-WorkspaceInput 'icons/batches/item-ground-x2-runtime-20261122-v1' -RequireExisting
$receipt = Join-Path $run 'installation.json'
$iniName = 'InfinityEngine-Enhancer.ini'
$dllName = 'InfinityEngine-Enhancer.dll'
$packName = 'iee-assets/icons/GroundItems-X2.registry'

function Assert-Installed($State) {
    if ($State.status -notin @('installed-pending-qa', 'validated-installed')) {
        throw 'Le test ne figure pas comme installé.'
    }
    foreach ($entry in $State.targets) {
        $target = Resolve-ChildPath $game $entry.relative_path -RequireExisting
        if ((Get-FileSha256 $target) -ne $entry.installed_sha256) {
            throw "Fichier de test modifié : $($entry.relative_path)"
        }
    }
}

function Restore-Targets($State) {
    foreach ($entry in $State.targets) {
        $target = Resolve-ChildPath $game $entry.relative_path
        if ($entry.backup) {
            $backup = Resolve-ChildPath $run $entry.backup -RequireExisting
            if ((Get-FileSha256 $backup) -ne $entry.original_sha256) {
                throw "Sauvegarde altérée : $($entry.relative_path)"
            }
            Copy-FileAtomic $backup $target
        } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            Remove-Item -LiteralPath $target
        }
    }
}

function Set-GroundIconIni([string]$Text) {
    $section = [regex]::new('(?im)^\[Shaders\][^\S\r\n]*\r?$[\s\S]*?(?=^\[|\z)')
    $match = $section.Match($Text)
    if (-not $match.Success) { throw 'Section Shaders absente du fichier INI.' }
    $key = [regex]::new('(?im)^\s*EnableGroundItemIconX2\s*=[^\r\n]*')
    $content = $match.Value
    if ($key.IsMatch($content)) {
        $content = $key.Replace($content, 'EnableGroundItemIconX2 = true')
    } else {
        $newline = if ($content.Contains("`r`n")) { "`r`n" } else { "`n" }
        $headingEnd = $content.IndexOf("`n")
        if ($headingEnd -lt 0) { throw 'Section Shaders vide.' }
        $content = $content.Insert($headingEnd + 1, "EnableGroundItemIconX2 = true$newline")
    }
    return $Text.Substring(0, $match.Index) + $content + $Text.Substring($match.Index + $match.Length)
}

if ($Mode -eq 'Verify') {
    $state = Read-JsonFile $receipt
    Assert-Installed $state
    $state | Select-Object status, asset_count, installed_at_utc, game_root
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
        $existing = Read-JsonFile $receipt
        if ($existing.status -ne 'restored') {
            Assert-Installed $existing
            $existing | Select-Object status, asset_count, game_root
            return
        }
    }
    $manifestPath = Join-Path $run 'runtime.json'
    $manifest = Read-JsonFile $manifestPath
    if ($manifest.schema -ne 'bg2-ground-items-x2-runtime-v1' -or
        $manifest.sampler -ne 'nearest' -or @($manifest.asset_ids).Count -ne 67) {
        throw 'Registre objets au sol incomplet.'
    }
    $dll = Resolve-WorkspaceInput $manifest.dll -RequireExisting
    $pack = Resolve-WorkspaceInput $manifest.registry -RequireExisting
    $exe = Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting
    if ((Get-FileSha256 $dll) -ne $manifest.dll_sha256 -or
        (Get-FileSha256 $pack) -ne $manifest.registry_sha256 -or
        (Get-FileSha256 $exe) -ne $manifest.baldur_real_sha256) {
        throw 'Empreinte de la DLL, du registre ou de BaldurReal.exe incompatible.'
    }
    $ini = Resolve-ChildPath $game $iniName -RequireExisting
    $iniText = [IO.File]::ReadAllText($ini)
    foreach ($key in @('EnableEffectAnimationX4', 'EnableNativeOcclusionBridge')) {
        if ((Get-IniValue $iniText 'Shaders' $key) -ne 'true') {
            throw "$key est nécessaire au chemin FX de cette installation de test."
        }
    }
    $newIni = Set-GroundIconIni $iniText

    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
    $entries = foreach ($name in @($dllName, $iniName, $packName)) {
        $target = Resolve-ChildPath $game $name
        $backupRelative = $null
        $originalHash = $null
        if (Test-Path -LiteralPath $target -PathType Leaf) {
            $backupRelative = "backups/$stamp/$name"
            $backup = Resolve-ChildPath $run $backupRelative
            Copy-FileAtomic $target $backup
            $originalHash = Get-FileSha256 $target
            if ((Get-FileSha256 $backup) -ne $originalHash) { throw "Échec de sauvegarde : $name" }
        }
        [ordered]@{ relative_path = $name; backup = $backupRelative; original_sha256 = $originalHash; installed_sha256 = $null }
    }
    $state = [ordered]@{
        schema = 'bg2-ground-items-x2-install-v1'
        status = 'installing'
        installed_at_utc = [DateTime]::UtcNow.ToString('o')
        game_root = $game
        asset_count = @($manifest.asset_ids).Count
        manifest_sha256 = Get-FileSha256 $manifestPath
        targets = @($entries)
    }
    Write-JsonAtomic $receipt $state
    try {
        Copy-FileAtomic $dll (Resolve-ChildPath $game $dllName)
        Copy-FileAtomic $pack (Resolve-ChildPath $game $packName)
        Write-TextAtomic $ini $newIni
        foreach ($entry in $state.targets) {
            $entry.installed_sha256 = Get-FileSha256 (Resolve-ChildPath $game $entry.relative_path)
        }
        if ($state.targets[0].installed_sha256 -ne $manifest.dll_sha256 -or
            $state.targets[2].installed_sha256 -ne $manifest.registry_sha256 -or
            (Get-IniValue ([IO.File]::ReadAllText($ini)) 'Shaders' 'EnableGroundItemIconX2') -ne 'true') {
            throw 'Échec de vérification des fichiers installés.'
        }
        $state.status = 'installed-pending-qa'
        Write-JsonAtomic $receipt $state
        [pscustomobject]$state | Select-Object status, asset_count, installed_at_utc, game_root
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
