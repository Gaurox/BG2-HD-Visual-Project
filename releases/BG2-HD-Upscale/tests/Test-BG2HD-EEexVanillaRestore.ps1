[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$GameRoot,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference='Stop'
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Get-Hash([string]$Path){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()}}
function Copy-Required([string]$From,[string]$To){New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force|Out-Null;Copy-Item -LiteralPath $From -Destination $To -Recurse}
function Invoke-Core([string]$Action,[string]$Game,[string]$Desktop){
    $output=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $release 'bg2hd/tools/bg2hd-steam.ps1') -Action $Action -GameRoot $Game -DesktopPath $Desktop -SkipProcessCheck 2>&1|Out-String
    Require ($LASTEXITCODE -eq 0) "$Action echoue : $output"
}
function Test-EEexInstalled([string]$Game,[int]$Id){
    (Get-Content -LiteralPath (Join-Path $Game 'WeiDU.log') -Raw) -match ('(?im)^~EEEX/EEEX\.TP2~\s*#0\s*#'+$Id+'(?:\s|$)')
}

$source=(Resolve-Path -LiteralPath $GameRoot).Path;$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
$runtime=Get-Content -LiteralPath (Join-Path $release 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$official=$runtime.target_game.sha256;$officialSource=$null;foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $source $name;if((Test-Path -LiteralPath $candidate)-and(Get-Hash $candidate)-eq$official){$officialSource=$candidate;break}};Require ($null-ne$officialSource) 'Executable officiel absent de la fixture.'
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd';if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-eeex-vanilla-'+[Guid]::NewGuid().ToString('N'));$game=Join-Path $temp 'game';$desktop=Join-Path $temp 'desktop';$previousDesktop=$env:BG2HD_DESKTOP_PATH
try {
    New-Item -ItemType Directory -Path $game,$desktop -Force|Out-Null
    $eeexRuntimeFiles=@('InfinityLoader.db','EEex.dll','EEex.ini','InfinityLoader.exe','InfinityLoaderCommon.dll','InfinityLoaderDLL.dll','InfinityLoaderUtil.dll','LuaBindings.dll','LuaBindingsCore.dll','LuaProvider.dll')
    foreach($relative in @('chitin.key','steam_appid.txt')+$eeexRuntimeFiles+@('weidu.conf','setup-EEex.exe','lang/en_US/dialog.tlk')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    [IO.File]::WriteAllText((Join-Path $game 'WeiDU.log'),"~EEEX/EEEX.TP2~ #0 #0 // Quick Menu Core: v1.2.0`r`n~EEEX/EEEX.TP2~ #0 #1 // EEex: v1.2.0`r`n",[Text.UTF8Encoding]::new($false))
    Copy-Required $officialSource (Join-Path $game 'Baldur.exe');Copy-Required $loaderIniSource (Join-Path $game 'InfinityLoader.ini')
    $eeexSnapshot=Join-Path $temp 'eeex-reinstall-snapshot';New-Item -ItemType Directory -Path $eeexSnapshot -Force|Out-Null
    foreach($relative in $eeexRuntimeFiles+@('InfinityLoader.ini')){Copy-Required (Join-Path $game $relative) (Join-Path $eeexSnapshot $relative)}
    foreach($relative in @('EEex','EEex_scripts','override','weidu_external')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    foreach($relative in @('override/M_IEEE.lua','override/fpSEAM.glsl')){$path=Join-Path $game $relative;if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path -Force}}
    Copy-Required (Join-Path $release 'bg2hd/renderer/InfinityEngine-Enhancer.sample.ini') (Join-Path $game 'InfinityEngine-Enhancer.ini')
    $originalBaldur=Get-Hash (Join-Path $game 'Baldur.exe')
    Require ($originalBaldur -eq $official) 'La fixture ne contient pas Baldur.exe officiel.'
    Require (Test-EEexInstalled $game 0) 'EEex composant 0 absent de la fixture.';Require (Test-EEexInstalled $game 1) 'EEex composant 1 absent de la fixture.'
    $env:BG2HD_DESKTOP_PATH=$desktop
    Invoke-Core Install $game $desktop
    $firstTransaction=(Get-Content -LiteralPath (Join-Path $game 'bg2hd/state/steam-launcher.json') -Raw|ConvertFrom-Json).transaction_id
    Invoke-Core Uninstall $game $desktop
    Require ((Get-Hash (Join-Path $game 'Baldur.exe')) -eq @($runtime.eeex.files|Where-Object{$_.path-eq'InfinityLoader.exe'})[0].sha256) 'Le retrait standard n a pas conserve le shim EEex.'
    Require ((Get-Hash (Join-Path $game 'BaldurReal.exe')) -eq $official) 'Le retrait standard n a pas conserve l executable officiel.'
    Invoke-Core RestoreVanilla $game $desktop
    Require ((Get-Hash (Join-Path $game 'Baldur.exe')) -eq $official) 'Le retour vanilla n a pas restaure Baldur.exe.'
    Require (-not(Test-Path -LiteralPath (Join-Path $game 'BaldurReal.exe'))) 'BaldurReal.exe subsiste apres retrait EEex.'
    Require (-not(Test-EEexInstalled $game 0)) 'Le composant EEex 0 subsiste apres retour vanilla.';Require (-not(Test-EEexInstalled $game 1)) 'Le composant EEex 1 subsiste apres retour vanilla.'
    Require (-not(Test-Path -LiteralPath (Join-Path $game 'override/M___EEex.lua'))) 'Le garde EEex subsiste apres retour vanilla.'
    Require (-not(Test-Path -LiteralPath (Join-Path $game 'override/M_IEEE.lua'))) 'Le garde BG2HD subsiste apres retour vanilla.'
    $state=Get-Content -LiteralPath (Join-Path $game 'bg2hd/state/steam-launcher.json') -Raw -Encoding utf8|ConvertFrom-Json
    Require ($state.phase -eq 'vanilla-restored') 'Etat final vanilla restaure absent.'

    # Simulate the files and active WeiDU lines republished by the official EEex
    # installer, then exercise the exact Core reinstall that failed in Test3.
    foreach($relative in $eeexRuntimeFiles+@('InfinityLoader.ini')){Copy-Required (Join-Path $eeexSnapshot $relative) (Join-Path $game $relative)}
    [IO.File]::WriteAllText((Join-Path $game 'WeiDU.log'),"~EEEX/EEEX.TP2~ #0 #0 // Quick Menu Core: v1.2.0`r`n~EEEX/EEEX.TP2~ #0 #1 // EEex: v1.2.0`r`n",[Text.UTF8Encoding]::new($false))
    Invoke-Core Install $game $desktop
    $reinstalledState=Get-Content -LiteralPath (Join-Path $game 'bg2hd/state/steam-launcher.json') -Raw -Encoding utf8|ConvertFrom-Json
    Require ($reinstalledState.phase -eq 'installed' -and $reinstalledState.transaction_id -ne $firstTransaction) 'La reinstallation apres retour vanilla n a pas ouvert une transaction propre.'
    Require (Test-Path -LiteralPath (Join-Path $game 'InfinityEngine-Enhancer.ini') -PathType Leaf) 'La reinstallation n a pas recree InfinityEngine-Enhancer.ini.'
    Require (Test-Path -LiteralPath (Join-Path $game 'override/M_IEEE.lua') -PathType Leaf) 'La reinstallation n a pas republie le garde renderer.'
    Invoke-Core Uninstall $game $desktop
    Write-Output 'EEEX_IN_PLACE_VANILLA_RESTORE=PASSED'
}
finally {
    if($null -eq $previousDesktop){Remove-Item Env:BG2HD_DESKTOP_PATH -ErrorAction SilentlyContinue}else{$env:BG2HD_DESKTOP_PATH=$previousDesktop}
    if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}
}
