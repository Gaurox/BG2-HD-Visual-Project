[CmdletBinding()]
param(
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

$ErrorActionPreference='Stop'
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
function Copy-Required([string]$From,[string]$To){New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force|Out-Null;Copy-Item -LiteralPath $From -Destination $To -Force}
function Invoke-Core([string]$Action,[string]$Root,[string]$Desktop){
    $output=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $ReleaseRoot 'bg2hd/tools/bg2hd-steam.ps1') -Action $Action -GameRoot $Root -DesktopPath $Desktop -SkipProcessCheck 2>&1|Out-String
    Require ($LASTEXITCODE -eq 0) "$Action echoue : $output"
}

$source=(Resolve-Path -LiteralPath $GameRoot).Path
$runtime=Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$renderer=Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/renderer-bundle.json') -Raw -Encoding utf8|ConvertFrom-Json
$officialSource=$null
foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $source $name;if((Test-Path -LiteralPath $candidate)-and(Hash $candidate)-eq$runtime.target_game.sha256){$officialSource=$candidate;break}}
Require ($null-ne$officialSource) 'Executable officiel absent de la fixture source.'
$loaderSource=Join-Path $source 'InfinityLoader.exe';if(-not(Test-Path -LiteralPath $loaderSource)){$loaderSource=Join-Path $source 'EEex/loader/InfinityLoader.exe'}
$eeexSource=Join-Path $source 'EEex.dll';if(-not(Test-Path -LiteralPath $eeexSource)){$eeexSource=Join-Path $source 'EEex/loader/v2.7.3.0/EEex.dll'}
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';if(-not(Test-Path -LiteralPath $loaderIniSource)){$loaderIniSource=Join-Path $source 'EEex/loader/InfinityLoader.ini'};$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd'
if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}

$temp=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-phase3-'+[Guid]::NewGuid().ToString('N'));$game=Join-Path $temp 'game';$desktop=Join-Path $temp 'desktop'
try{
    New-Item -ItemType Directory -Path $game,$desktop -Force|Out-Null
    foreach($relative in @('chitin.key','steam_appid.txt','lang/en_US/dialog.tlk')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    Copy-Required $loaderSource (Join-Path $game 'InfinityLoader.exe');Copy-Required $eeexSource (Join-Path $game 'EEex.dll')
    [IO.File]::WriteAllText((Join-Path $game 'WeiDU.log'),"~EEEX/EEEX.TP2~ #0 #0 // Quick Menu Core: v1.2.0`r`n~EEEX/EEEX.TP2~ #0 #1 // EEex: v1.2.0`r`n",[Text.UTF8Encoding]::new($false))
    Copy-Required $officialSource (Join-Path $game 'Baldur.exe');Copy-Required $loaderIniSource (Join-Path $game 'InfinityLoader.ini')
    $rendererIniSource=Join-Path $source 'InfinityEngine-Enhancer.ini';if(-not(Test-Path -LiteralPath $rendererIniSource)){$rendererIniSource=Join-Path $ReleaseRoot 'bg2hd/renderer/InfinityEngine-Enhancer.sample.ini'}
    Copy-Required $rendererIniSource (Join-Path $game 'InfinityEngine-Enhancer.ini')
    $official=$runtime.target_game.sha256;$loader=@($runtime.eeex.files|Where-Object{$_.path-eq'InfinityLoader.exe'})[0].sha256
    $originalIni=Hash (Join-Path $game 'InfinityLoader.ini');$originalRenderer=Hash (Join-Path $game 'InfinityEngine-Enhancer.ini')

    Invoke-Core Test $game $desktop
    Invoke-Core Install $game $desktop
    Require ((Hash (Join-Path $game 'Baldur.exe'))-eq$loader) 'Baldur.exe n est pas le shim InfinityLoader verifie.'
    Require ((Hash (Join-Path $game 'BaldurReal.exe'))-eq$official) 'BaldurReal.exe ne preserve pas l executable officiel.'
    $loaderIni=Get-Content -LiteralPath (Join-Path $game 'InfinityLoader.ini') -Raw
    Require ($loaderIni -match '(?im)^\s*ExeNames\s*=\s*BaldurReal\.exe' -and $loaderIni -match '(?im)^\s*ExeSwitchAlias\s*=\s*BaldurReal\.exe:Baldur\.exe') 'InfinityLoader.ini ne contient pas le routage Steam attendu.'
    $guardRecord=@($renderer.files|Where-Object{$_.path-eq'override/M_IEEE.lua'})[0];$guardPath=Join-Path $game 'override/M_IEEE.lua'
    Require ((Hash $guardPath)-eq$guardRecord.sha256) 'Le garde save-neutral installe est incorrect.'
    Require ((Get-Content -LiteralPath $guardPath -Raw)-match '(?m)^EEex_Debug_DisableExtraCreatureMarshalling\s*=\s*true\s*$') 'Le garde save-neutral n est pas actif.'
    $shortcutPath=Join-Path $desktop "Baldur's Gate II Enhanced Edition - HD.lnk";Require (Test-Path -LiteralPath $shortcutPath) 'Raccourci HD absent.'
    $shell=New-Object -ComObject WScript.Shell;$shortcut=$shell.CreateShortcut($shortcutPath);Require ($shortcut.TargetPath-eq(Join-Path $game 'InfinityLoader.exe')) 'Le raccourci HD ne cible pas InfinityLoader.'
    $statePath=Join-Path $game 'bg2hd/state/steam-launcher.json';$state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
    Require ($state.phase-eq'installed' -and $state.launch_mode-eq'steam-shim-in-place') 'Etat Steam integre absent.'
    $firstTransactionId=$state.transaction_id
    Require (Test-Json -Path $statePath -SchemaFile (Join-Path $ReleaseRoot 'schemas/state.schema.json')) 'Etat Core non conforme au schema.'

    Copy-Required $officialSource (Join-Path $game 'Baldur.exe')
    Invoke-Core Repair $game $desktop
    Require ((Hash (Join-Path $game 'Baldur.exe'))-eq$loader) 'Repair n a pas republié le shim InfinityLoader.'

    Invoke-Core Uninstall $game $desktop
    Require ((Hash (Join-Path $game 'Baldur.exe'))-eq$loader -and (Hash (Join-Path $game 'BaldurReal.exe'))-eq$official) 'Le retrait standard n a pas conserve le lancement EEex.'
    Require ((Hash (Join-Path $game 'InfinityEngine-Enhancer.ini'))-eq$originalRenderer) 'La configuration renderer n a pas ete restauree.'
    Require (-not(Test-Path -LiteralPath $guardPath)) 'Le garde renderer subsiste apres retrait BG2HD.'
    Require (-not(Test-Path -LiteralPath $shortcutPath)) 'Le raccourci HD subsiste apres retrait.'
    $state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json;Require ($state.phase-eq'eeex-retained') 'Etat EEex conserve absent.'

    Invoke-Core Install $game $desktop
    $secondState=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
    Require ($secondState.transaction_id -ne $firstTransactionId) 'La reinstallation apres retrait doit ouvrir une nouvelle transaction Core.'
    Require (@($secondState.completed_steps).Count -eq @($secondState.completed_steps|Sort-Object -Unique).Count) 'La reinstallation ne doit pas reutiliser les etapes terminees du cycle precedent.'
    Require ((Test-Path -LiteralPath (Join-Path $game 'InfinityEngine-Enhancer.ini')) -and (Test-Path -LiteralPath $guardPath)) 'La reinstallation n a pas republie le renderer et sa configuration.'
    Invoke-Core Uninstall $game $desktop
    Require ((Hash (Join-Path $game 'InfinityLoader.ini'))-ne$originalIni) 'Le retrait standard doit conserver le routage EEex fonctionnel.'
    'PHASE3_IN_PLACE_CORE_LIFECYCLE=PASSED'
}finally{if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}}
