[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WeiDUExecutable,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$workspaceRoot = $PSScriptRoot
while ($workspaceRoot -and -not (Test-Path -LiteralPath (Join-Path $workspaceRoot 'config\workspace-paths.json') -PathType Leaf)) {
    $workspaceRoot = Split-Path -Parent $workspaceRoot
}
if ([string]::IsNullOrWhiteSpace($workspaceRoot)) { throw 'Racine du workspace BG2 Upscale introuvable.' }
. (Join-Path $workspaceRoot 'pipeline\scripts\WorkspacePaths.ps1')
if ((Get-Variable -Name GameRoot -ErrorAction SilentlyContinue) -and [string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
}

$ErrorActionPreference = 'Stop'
function Require([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Copy-Required([string]$From, [string]$To) { New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force | Out-Null; Copy-Item -LiteralPath $From -Destination $To }

$source = (Resolve-Path -LiteralPath $GameRoot).Path
$runtime = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/runtime-compatibility.json') -Raw -Encoding utf8 | ConvertFrom-Json
$officialSource = $null
foreach ($name in @('Baldur.exe','BaldurReal.exe')) { $candidate=Join-Path $source $name; if((Test-Path -LiteralPath $candidate) -and (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash -eq $runtime.target_game.sha256){$officialSource=$candidate;break} }
Require ($null -ne $officialSource) 'Executable officiel absent de la fixture.'
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd';if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}
$weidu = (Resolve-Path -LiteralPath $WeiDUExecutable).Path
$temp = Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-phase3-weidu-' + [Guid]::NewGuid().ToString('N'))
$fakeGame = Join-Path $temp 'game'

try {
    New-Item -ItemType Directory -Path $fakeGame -Force | Out-Null
    foreach ($relative in @('chitin.key','InfinityLoader.exe','EEex.dll','steam_appid.txt','InfinityEngine-Enhancer.ini','lang/en_US/dialog.tlk')) {
        Copy-Required (Join-Path $source $relative) (Join-Path $fakeGame $relative)
    }
    [IO.File]::WriteAllText((Join-Path $fakeGame 'WeiDU.log'), "~EEEX/EEEX.TP2~ #0 #0`r`n~EEEX/EEEX.TP2~ #0 #1`r`n", [Text.UTF8Encoding]::new($false))
    Copy-Required $officialSource (Join-Path $fakeGame 'Baldur.exe')
    Copy-Required $loaderIniSource (Join-Path $fakeGame 'InfinityLoader.ini')
    # WeiDU asks for the game language before processing components.  Preserve
    # the source's selected language and its dialog.tlk in the isolated copy.
    $weiduConfig = Join-Path $source 'weidu.conf'
    if (Test-Path -LiteralPath $weiduConfig) {
        Copy-Required $weiduConfig (Join-Path $fakeGame 'weidu.conf')
        $selectedLanguage = (Get-Content -LiteralPath $weiduConfig -Raw | Select-String -Pattern '(?im)^\s*lang_dir\s*=\s*([^\s;#]+)').Matches.Groups[1].Value
        if ($selectedLanguage) { Copy-Required (Join-Path $source "lang/$selectedLanguage/dialog.tlk") (Join-Path $fakeGame "lang/$selectedLanguage/dialog.tlk") }
    }
    Copy-Item -LiteralPath (Join-Path $ReleaseRoot 'bg2hd') -Destination (Join-Path $fakeGame 'bg2hd') -Recurse
    $steamSource=Join-Path $temp 'steam-source';New-Item -ItemType Directory -Path $steamSource -Force|Out-Null;Copy-Required $officialSource (Join-Path $steamSource 'Baldur.exe');Copy-Required (Join-Path $source 'chitin.key') (Join-Path $steamSource 'chitin.key')
    $layoutPath=Join-Path $fakeGame 'bg2hd/state/install-layout.json';New-Item -ItemType Directory -Path (Split-Path -Parent $layoutPath) -Force|Out-Null
    [IO.File]::WriteAllText($layoutPath,([ordered]@{schema_version=1;source_game_root=$steamSource;hd_game_root=$fakeGame;source_baldur_sha256=$runtime.target_game.sha256;launch_mode='dedicated-shortcut-only';steam_source_untouched=$true;created_at=(Get-Date).ToUniversalTime().ToString('o');package_version='test'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    $setup = Join-Path $fakeGame 'setup-bg2hd.exe'
    Copy-Item -LiteralPath $weidu -Destination $setup
    Push-Location -LiteralPath $fakeGame
    try {
        $installOutput = & $setup '--noautoupdate' '--force-install-list' '0' '--language' '0' '--no-exit-pause' 2>&1 | Out-String
        Require ($LASTEXITCODE -eq 0) "Installation WeiDU Core echouee : $installOutput"
        Require ((Get-Content -LiteralPath (Join-Path $fakeGame 'WeiDU.log') -Raw) -match '(?i)BG2HD/BG2HD\.TP2~ #0 #0') 'WeiDU.log ne contient pas le Core BG2 HD.'
        Require (((Get-FileHash -LiteralPath (Join-Path $fakeGame 'Baldur.exe') -Algorithm SHA256).Hash -eq $runtime.target_game.sha256)) 'Le Core WeiDU a modifie Baldur.exe.'
        Require (-not(Test-Path -LiteralPath (Join-Path $fakeGame 'BaldurReal.exe'))) 'Le Core WeiDU a cree un ancien shim.'
        $uninstallOutput = & $setup '--noautoupdate' '--uninstall' '0' '--language' '0' '--no-exit-pause' 2>&1 | Out-String
        Require ($LASTEXITCODE -eq 0) "Desinstallation WeiDU Core echouee : $uninstallOutput"
        Require (((Get-FileHash -LiteralPath (Join-Path $fakeGame 'Baldur.exe') -Algorithm SHA256).Hash -eq $runtime.target_game.sha256)) 'La desinstallation WeiDU a modifie Baldur.exe.'
        Require (((Get-FileHash -LiteralPath (Join-Path $steamSource 'Baldur.exe') -Algorithm SHA256).Hash -eq $runtime.target_game.sha256)) 'Le cycle WeiDU a modifie la source Steam.'
        $launcherState=Get-Content -LiteralPath (Join-Path $fakeGame 'bg2hd/state/launcher.json') -Raw|ConvertFrom-Json
        Require ($launcherState.phase -eq 'bg2hd-removed') 'Etat autonome retire absent apres WeiDU.'
    }
    finally { Pop-Location }
    Write-Output 'PHASE3_WEIDU_CORE=PASSED'
}
finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
