[CmdletBinding()]
param(
    [ValidateSet('Install', 'Inspect', 'Uninstall')]
    [string]$Action = 'Install',
    [string]$GameRoot,
    [string]$EEexInstallerPath,
    [switch]$DownloadEEex,
    [switch]$NonInteractive,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WeiDUArguments
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Resolve-Absolute([string]$Path) {
    return (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
}

function Get-Hash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '')
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}

function Read-Json([string]$Path) {
    return Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
}

function Get-DependencyStatePath([string]$Root) {
    return Join-Path $Root 'bg2hd\state\dependency-bootstrap.json'
}

function Get-EEexOrigin([string]$Root) {
    $path = Get-DependencyStatePath $Root
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return 'unknown' }
    try {
        $state = Read-Json $path
        if ($state.eeex_origin -in @('bg2hd-bootstrap', 'pre-existing', 'unknown')) { return [string]$state.eeex_origin }
    } catch { }
    return 'unknown'
}

function Set-EEexOrigin([string]$Root, [ValidateSet('bg2hd-bootstrap', 'pre-existing', 'unknown')][string]$Origin) {
    $path = Get-DependencyStatePath $Root
    $directory = Split-Path -Parent $path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $temporary = Join-Path $directory ('.dependency-bootstrap.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $state = [ordered]@{
        schema_version = 1
        eeex_origin = $Origin
        recorded_at = (Get-Date).ToUniversalTime().ToString('o')
    }
    try {
        [IO.File]::WriteAllText($temporary, ($state | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $path -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Test-SameFile([string]$Path, [object]$Expected) {
    return (Test-Path -LiteralPath $Path -PathType Leaf) -and (Get-Item -LiteralPath $Path).Length -eq $Expected.bytes -and (Get-Hash $Path) -eq $Expected.sha256
}

function Assert-ClosedProcesses([string]$Root) {
    $normalizedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\\') + '\\'
    foreach ($name in @('Baldur', 'InfinityLoader')) {
        foreach ($process in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) {
            try {
                if ($process.Path -and [IO.Path]::GetFullPath($process.Path).StartsWith($normalizedRoot, [StringComparison]::OrdinalIgnoreCase)) {
                    throw "Processus ouvert dans le dossier de jeu : $name ($($process.Id))."
                }
            } catch {
                if ($_.Exception.Message -like 'Processus ouvert*') { throw }
            }
        }
    }
}

function Get-VisualCxxState() {
    $runtime = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
    return [bool]($runtime -and $runtime.Installed -eq 1)
}

function Get-GameState([string]$Root) {
    $baldur = Join-Path $Root 'Baldur.exe'
    $real = Join-Path $Root 'BaldurReal.exe'
    $loader = Join-Path $Root 'InfinityLoader.exe'
    Require (Test-Path -LiteralPath (Join-Path $Root 'chitin.key') -PathType Leaf) 'chitin.key absent : ce dossier n est pas une installation BG2EE.'
    Require (Test-Path -LiteralPath $baldur -PathType Leaf) 'Baldur.exe absent.'
    $official = $runtime.target_game
    $loaderExpected = @($runtime.eeex.files | Where-Object { $_.path -eq 'InfinityLoader.exe' })
    Require ($loaderExpected.Count -eq 1) 'Contrat InfinityLoader absent du runtime.'
    $launcherState = Join-Path $Root 'bg2hd\state\steam-launcher.json'
    if ((Test-SameFile $real $official) -and (Test-SameFile $baldur $loaderExpected[0]) -and (Test-SameFile $loader $loaderExpected[0])) { return 'bg2hd-steam-shim-installed' }
    if ((Test-SameFile $real $official) -and (Test-SameFile $baldur $official) -and (Test-Path -LiteralPath $launcherState -PathType Leaf)) { return 'steam-repaired-bg2hd' }
    if ((Test-SameFile $baldur $official) -and -not (Test-Path -LiteralPath $real)) { return 'clean-steam' }
    throw 'Executables BG2EE non supportes : aucune ecriture autorisee.'
}

function Assert-FutureSaveCompatibility([string]$Root, [switch]$Installed) {
    $saveContract = $runtime.save_compatibility_contract
    Require ($saveContract.scope -eq 'future-save-chains-from-vanilla-compatible-state') 'Contrat de compatibilite des futures sauvegardes absent.'
    Require ($saveContract.eeex_extra_creature_marshalling -eq 'disabled') 'La neutralite des sauvegardes EEex n est pas activee dans le contrat.'
    Require ($saveContract.forbidden_signature -eq 'X-BIV1.0') 'Signature de sauvegarde interdite inattendue.'

    $rendererManifest = Read-Json (Join-Path $packageRoot 'manifests\renderer-bundle.json')
    $guardRecord = @($rendererManifest.files | Where-Object { $_.path -eq 'override/M_IEEE.lua' })
    Require ($guardRecord.Count -eq 1) 'M_IEEE.lua absent du manifeste renderer.'
    $guardPath = if ($Installed) { Join-Path $Root 'override\M_IEEE.lua' } else { Join-Path $packageRoot 'renderer\override\M_IEEE.lua' }
    Require (Test-SameFile $guardPath $guardRecord[0]) "Garde de compatibilite des sauvegardes absent ou modifie : $guardPath"
    $guardText = Get-Content -LiteralPath $guardPath -Raw -Encoding utf8
    Require ($guardText -match '(?m)^\s*EEex_Debug_DisableExtraCreatureMarshalling\s*=\s*true\s*$') 'Le garde-fou EEex des sauvegardes n est pas active.'
}

function Get-WeiDUComponentCount([string]$Root) {
    $log = Join-Path $Root $contract.eeex.detection.weidu_log
    if (-not (Test-Path -LiteralPath $log -PathType Leaf)) { return 0 }
    $text = Get-Content -LiteralPath $log -Raw -Encoding utf8
    $count = 0
    foreach ($component in $contract.eeex.installation.required_weidu_components) {
        # Only an active WeiDU line starts with ~TP2~. Commented
        # "Recently Uninstalled" history must not count as installed.
        $needle = '(?im)^~' + [regex]::Escape($component.tp2) + '~\s*#0\s*#' + $component.id + '(?:\s|$)'
        if ($text -match $needle) { $count++ }
    }
    return $count
}

function Get-EEexState([string]$Root) {
    $requiredComponentCount = @($contract.eeex.installation.required_weidu_components).Count
    $componentCount = Get-WeiDUComponentCount $Root
    $inactiveResidueCount = @($contract.eeex.detection.inactive_residue_paths | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_) }).Count
    $runtimePaths = @($contract.eeex.detection.exact_files | ForEach-Object { [string]$_.path }) + @($contract.eeex.detection.mutable_runtime_files) + @('InfinityLoader.ini')
    $runtimePresent = @($runtimePaths | Select-Object -Unique | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_) }).Count
    $knownSignalCount = $componentCount + $inactiveResidueCount + $runtimePresent
    if ($knownSignalCount -eq 0) { return 'absent' }

    # A normal WeiDU uninstall removes every active component and runtime file,
    # but deliberately leaves the mod sources and setup-EEex.exe in the game
    # directory. This is a safe reinstallable state, not a damaged install.
    if ($componentCount -eq 0 -and $runtimePresent -eq 0 -and $inactiveResidueCount -eq $contract.eeex.detection.inactive_residue_paths.Count) {
        return 'inactive'
    }

    $pathsPresent = @($contract.eeex.detection.required_paths | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_) }).Count
    $filesPresent = @($contract.eeex.detection.exact_files | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_.path) }).Count
    if ($pathsPresent -ne $contract.eeex.detection.required_paths.Count -or $filesPresent -ne $contract.eeex.detection.exact_files.Count -or $componentCount -ne $requiredComponentCount) {
        return 'partial'
    }
    foreach ($file in $contract.eeex.detection.exact_files) {
        if (-not (Test-SameFile (Join-Path $Root $file.path) $file)) { return 'unknown_or_changed' }
    }
    return 'compatible'
}

function Assert-Archive([string]$Path) {
    $archive = Resolve-Absolute $Path
    $expected = $contract.eeex.official_release
    Require ((Split-Path -Leaf $archive) -eq $expected.filename) 'Nom d archive EEex non accepte.'
    Require ((Get-Item -LiteralPath $archive).Length -eq $expected.bytes) 'Taille d archive EEex non acceptee.'
    Require ((Get-Hash $archive) -eq $expected.sha256) 'SHA-256 d archive EEex non accepte.'
    return $archive
}

function Confirm([string]$Prompt) {
    if ($NonInteractive) { throw 'Consentement interactif requis.' }
    $answer = Read-Host "$Prompt [O/N]"
    return $answer -match '^(?i:o|oui|y|yes)$'
}

function Get-OfficialEEexArchive() {
    if ($EEexInstallerPath) {
        if (-not $NonInteractive -and -not (Confirm "Executer l installeur EEex officiel fourni")) { throw 'Installation EEex annulee par l utilisateur.' }
        return [pscustomobject]@{ path = (Assert-Archive $EEexInstallerPath); temporary = $false }
    }
    if (-not $DownloadEEex) {
        if ($NonInteractive) { throw 'EEex doit etre installe ou reactive : fournir -EEexInstallerPath ou -DownloadEEex.' }
        $choice = Read-Host 'EEex est absent ou desinstalle. [T]elecharger, [L]ocaliser une archive officielle ou [A]nnuler'
        if ($choice -match '^(?i:l|local)') {
            $localPath = Read-Host 'Chemin complet de EEex-v1.2.0.exe'
            $script:EEexInstallerPath = $localPath
            return Get-OfficialEEexArchive
        }
        if ($choice -notmatch '^(?i:t|telecharger|download|d)$') { throw 'Installation EEex annulee par l utilisateur.' }
    }
    if (-not $NonInteractive -and -not (Confirm "Telecharger et executer EEex v$($contract.eeex.required_version) depuis sa release officielle")) { throw 'Installation EEex annulee par l utilisateur.' }
    $temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ('BG2HD-EEex-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null
    $archive = Join-Path $temporaryRoot $contract.eeex.official_release.filename
    try {
        Invoke-WebRequest -Uri $contract.eeex.official_release.asset_url -OutFile $archive -UseBasicParsing
        return [pscustomobject]@{ path = (Assert-Archive $archive); temporary = $true; directory = $temporaryRoot }
    } catch {
        if (Test-Path -LiteralPath $temporaryRoot) { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force }
        throw
    }
}

function Install-EEex([object]$Archive) {
    Write-Host 'Lancement de l installeur officiel EEex. Selectionnez ce dossier BG2EE dans son interface, puis terminez son installation.'
    $process = Start-Process -FilePath $Archive.path -WorkingDirectory (Split-Path -Parent $Archive.path) -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installeur EEex termine avec le code $($process.ExitCode)." }
    $after = Get-EEexState $game
    if ($after -ne 'compatible') { throw "EEex n est pas compatible apres son installeur : $after." }
}

function Start-BG2HDWeiDU() {
    $gamePackageRoot = Resolve-Absolute (Join-Path $PSScriptRoot '..\..')
    Require ([IO.Path]::GetFullPath($gamePackageRoot).TrimEnd('\\') -eq [IO.Path]::GetFullPath($game).TrimEnd('\\')) 'Le paquet BG2HD doit etre extrait a la racine du jeu avant l installation.'
    $setup = Join-Path $game 'setup-bg2hd.exe'
    Require (Test-Path -LiteralPath $setup -PathType Leaf) 'setup-bg2hd.exe absent de la racine du jeu.'
    Push-Location -LiteralPath $game
    try {
        & $setup @WeiDUArguments
        if ($LASTEXITCODE -ne 0) { throw "WeiDU BG2HD termine avec le code $LASTEXITCODE." }
    } finally {
        Pop-Location
    }
}

function Get-BG2HDLauncherStatus() {
    $stateTool = Join-Path $PSScriptRoot 'bg2hd-steam.ps1'
    $status = & powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $stateTool -Action Status -GameRoot $game 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Controle de l etat BG2HD echoue : $status" }
    return ($status | ConvertFrom-Json)
}

function Invoke-BG2HDUninstall() {
    $before = Get-BG2HDLauncherStatus
    if ($before.state.phase -eq 'eeex-retained') {
        Write-Host 'BG2HD est deja retire ; EEex et le lancement Steam sont conserves.'
        return
    }
    Require ($before.state.phase -in @('installed', 'failed')) 'Etat BG2HD installe absent : rien a retirer avant le choix EEex.'
    $setup = Join-Path $game 'setup-bg2hd.exe'
    Require (Test-Path -LiteralPath $setup -PathType Leaf) 'setup-bg2hd.exe absent de la racine du jeu.'
    Push-Location -LiteralPath $game
    try {
        & $setup '--noautoupdate' '--uninstall' '0' '--no-exit-pause'
        if ($LASTEXITCODE -ne 0) { throw "WeiDU BG2HD termine avec le code $LASTEXITCODE." }
    } finally {
        Pop-Location
    }
    $statusObject = Get-BG2HDLauncherStatus
    Require ($statusObject.state.phase -eq 'eeex-retained') 'BG2HD n a pas laisse le shim EEex attendu.'
}

function Invoke-CompleteVanillaRestore() {
    $stateTool = Join-Path $PSScriptRoot 'bg2hd-steam.ps1'
    & powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $stateTool -Action RestoreVanilla -GameRoot $game
    if ($LASTEXITCODE -ne 0) { throw "Retour vanilla complet echoue : $LASTEXITCODE" }
}

function Select-UninstallMode() {
    if ($NonInteractive) { throw 'Le choix du mode de desinstallation exige une confirmation interactive.' }
    Write-Host ''
    Write-Host 'Choisissez le mode de desinstallation :'
    Write-Host '  1 - Retirer BG2HD et conserver EEex (Steam continue via InfinityLoader).'
    Write-Host '  2 - Retour vanilla complet (retire aussi EEex et peut affecter d autres mods).'
    Write-Host '  A - Annuler'
    $choice = Read-Host 'Votre choix'
    switch -Regex ($choice) {
        '^(1|garder|keep)$' { return 'keep-eeex' }
        '^(2|vanilla|complet)$' {
            if ($script:eeexOrigin -ne 'bg2hd-bootstrap') {
                $originMessage = if ($script:eeexOrigin -eq 'pre-existing') { 'EEex etait deja installe avant BG2HD.' } else { 'L origine de cette installation EEex est inconnue (ancien paquet ou installation externe possible).' }
                Write-Host "ATTENTION : $originMessage"
                if (-not (Confirm 'Retirer quand meme EEex, ce qui peut affecter d autres mods')) { throw 'Retour vanilla annule par l utilisateur.' }
            }
            if (-not (Confirm 'Confirmer le retrait de BG2HD et EEex pour revenir au vanilla complet')) { throw 'Retour vanilla annule par l utilisateur.' }
            return 'full-vanilla'
        }
        default { throw 'Desinstallation annulee par l utilisateur.' }
    }
}

$packageRoot = Resolve-Absolute (Join-Path $PSScriptRoot '..')
$contract = Read-Json (Join-Path $packageRoot 'manifests\dependency-bootstrap.json')
$runtime = Read-Json (Join-Path $packageRoot 'manifests\runtime-compatibility.json')
if ($Action -ne 'Uninstall') { Assert-FutureSaveCompatibility $packageRoot }
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Join-Path $PSScriptRoot '..\..'
}
$game = Resolve-Absolute $GameRoot
Require ([Environment]::Is64BitOperatingSystem) 'Windows x64 requis.'
$gameState = Get-GameState $game
$visualCxxAvailable = Get-VisualCxxState
$eeexState = Get-EEexState $game
$eeexOrigin = Get-EEexOrigin $game
$result = [ordered]@{ game_root = $game; game_state = $gameState; visual_cxx_available = $visualCxxAvailable; eeex_state = $eeexState; action = $Action }

if ($Action -eq 'Inspect') {
    $result | ConvertTo-Json
    exit 0
}

Assert-ClosedProcesses $game
if ($Action -eq 'Uninstall') {
    Require ($eeexState -eq 'compatible') "EEex doit etre dans son etat compatible pour une desinstallation sure : $eeexState. Reparez EEex 1.2.0 avant de relancer."
    $mode = Select-UninstallMode
    Invoke-BG2HDUninstall
    if ($mode -eq 'full-vanilla') { Invoke-CompleteVanillaRestore }
    exit 0
}
if (-not $visualCxxAvailable) {
    Write-Host 'Microsoft Visual C++ x64 est requis par EEex.'
    if (-not $NonInteractive -and (Confirm 'Ouvrir le telechargement officiel Microsoft')) { Start-Process $contract.visual_cxx.official_url }
    throw 'Installez Visual C++ x64, puis relancez Install-BG2HD.exe.'
}
$eeexNeedsInstall = $false
switch ($eeexState) {
    'compatible' {
        # A first BG2HD installation must remember whether EEex was already
        # present.  Do not guess for installations made by an older package:
        # the full-vanilla path will warn in that deliberately conservative case.
        if ($Action -eq 'Install' -and $eeexOrigin -eq 'unknown') {
            $launcherState = Join-Path $game 'bg2hd\state\steam-launcher.json'
            if (-not (Test-Path -LiteralPath $launcherState -PathType Leaf)) {
                Set-EEexOrigin $game 'pre-existing'
                $eeexOrigin = 'pre-existing'
            }
        }
    }
    'absent' { $eeexNeedsInstall = $true }
    'inactive' { $eeexNeedsInstall = $true }
    'partial' { throw 'EEex est partiellement installe. Reparez-le avec son installeur officiel, puis relancez BG2HD.' }
    'unknown_or_changed' { throw 'EEex ou InfinityLoader n est pas une version admise. Aucune ecriture BG2HD ne sera effectuee.' }
    default { throw "Etat EEex inattendu : $eeexState." }
}
if ($eeexNeedsInstall) {
    $archive = $null
    try {
        $archive = Get-OfficialEEexArchive
        Install-EEex $archive
        Set-EEexOrigin $game 'bg2hd-bootstrap'
        $eeexOrigin = 'bg2hd-bootstrap'
    } finally {
        if ($archive -and $archive.temporary -and (Test-Path -LiteralPath $archive.directory)) { Remove-Item -LiteralPath $archive.directory -Recurse -Force }
    }
}
Start-BG2HDWeiDU
$installedStatus = Get-BG2HDLauncherStatus
Require ($installedStatus.state.phase -eq 'installed') 'BG2HD n a pas atteint l etat integre attendu.'
Assert-FutureSaveCompatibility $game -Installed
Write-Host 'BG2HD est installe dans le jeu Steam. Les futures sauvegardes restent neutres pour le moteur vanilla.'
