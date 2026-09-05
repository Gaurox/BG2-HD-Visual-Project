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

$ErrorActionPreference='Stop'
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Get-Hash([string]$Path){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()}}
function Copy-Required([string]$From,[string]$To){New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force|Out-Null;Copy-Item -LiteralPath $From -Destination $To}
function Invoke-WeiDU([string]$Setup,[string[]]$Arguments){$output=& $Setup @Arguments 2>&1|Out-String;$code=$LASTEXITCODE;[pscustomobject]@{code=$code;output=$output}}

$source=(Resolve-Path -LiteralPath $GameRoot).Path;$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path;$weidu=(Resolve-Path -LiteralPath $WeiDUExecutable).Path
$runtime=Get-Content -LiteralPath (Join-Path $release 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$officialSource=$null;foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $source $name;if((Test-Path -LiteralPath $candidate)-and(Get-Hash $candidate)-eq$runtime.target_game.sha256){$officialSource=$candidate;break}};Require ($null-ne$officialSource) 'Executable officiel absent de la fixture.'
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd';if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-phase5a-update-'+[Guid]::NewGuid().ToString('N'));$steamSource=Join-Path $temp 'steam-source';$game=Join-Path $temp 'game';$desktop=Join-Path $temp 'desktop';$previousDesktop=$env:BG2HD_DESKTOP_PATH
try {
    New-Item -ItemType Directory -Path $steamSource,$game,$desktop -Force|Out-Null;Copy-Required $officialSource (Join-Path $steamSource 'Baldur.exe')
    foreach($relative in @('chitin.key','InfinityLoader.exe','EEex.dll','steam_appid.txt','InfinityEngine-Enhancer.ini','lang/en_US/dialog.tlk')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    [IO.File]::WriteAllText((Join-Path $game 'WeiDU.log'),"~EEEX/EEEX.TP2~ #0 #0`r`n~EEEX/EEEX.TP2~ #0 #1`r`n",[Text.UTF8Encoding]::new($false))
    Copy-Required $officialSource (Join-Path $game 'Baldur.exe');Copy-Required $loaderIniSource (Join-Path $game 'InfinityLoader.ini')
    $weiduConf=Join-Path $source 'weidu.conf';if(Test-Path -LiteralPath $weiduConf){Copy-Required $weiduConf (Join-Path $game 'weidu.conf');$lang=(Get-Content -LiteralPath $weiduConf -Raw|Select-String -Pattern '(?im)^\s*lang_dir\s*=\s*([^\s;#]+)').Matches.Groups[1].Value;if($lang){Copy-Required (Join-Path $source "lang/$lang/dialog.tlk") (Join-Path $game "lang/$lang/dialog.tlk")}}else{[IO.File]::WriteAllText((Join-Path $game 'weidu.conf'),"lang_dir = en_US`r`n",[Text.UTF8Encoding]::new($false))}
    $originalBaldur=Get-Hash (Join-Path $game 'Baldur.exe');$fixture=Join-Path $game 'override/AR0703.TIS';New-Item -ItemType Directory -Path (Split-Path -Parent $fixture) -Force|Out-Null;[IO.File]::WriteAllBytes($fixture,[byte[]](5,4,3,2));$fixtureHash=Get-Hash $fixture
    Copy-Item -LiteralPath (Join-Path $release 'bg2hd') -Destination (Join-Path $game 'bg2hd') -Recurse;Copy-Item -LiteralPath $weidu -Destination (Join-Path $game 'setup-bg2hd.exe')
    $layoutPath=Join-Path $game 'bg2hd/state/install-layout.json';New-Item -ItemType Directory -Path (Split-Path -Parent $layoutPath) -Force|Out-Null;[IO.File]::WriteAllText($layoutPath,([ordered]@{schema_version=1;source_game_root=$steamSource;hd_game_root=$game;source_baldur_sha256=$runtime.target_game.sha256;launch_mode='dedicated-shortcut-only';steam_source_untouched=$true;created_at=(Get-Date).ToUniversalTime().ToString('o');package_version='test'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    $env:BG2HD_DESKTOP_PATH=$desktop;Push-Location $game
    try {
        foreach($id in @(0,1060)){$result=Invoke-WeiDU '.\setup-bg2hd.exe' @('--noautoupdate','--force-install-list',"$id",'--language','0','--no-exit-pause');Require ($result.code -eq 0) "Installation initiale $id echouee : $($result.output)"}
        $tis=Join-Path $game 'override/AR0703.TIS';Require ((Get-Hash $tis) -ne $fixtureHash) 'La carte initiale n a pas remplace le fixture.'
        $tp2=Join-Path $game 'bg2hd/bg2hd.tp2';$text=Get-Content -LiteralPath $tp2 -Raw -Encoding utf8;Require ($text -match 'VERSION ~0\.1\.0-alpha\.2~') 'Version alpha.2 initiale absente.';[IO.File]::WriteAllText($tp2,$text.Replace('VERSION ~0.1.0-alpha.2~','VERSION ~0.1.0-alpha.3~'),[Text.UTF8Encoding]::new($false))
        $result=Invoke-WeiDU '.\setup-bg2hd.exe' @('--noautoupdate','--force-install-list','1060','--language','0','--no-exit-pause');Require ($result.code -eq 0) "Mise a jour alpha.3 echouee : $($result.output)";Require ((Get-Hash $tis) -eq (Get-Hash (Join-Path $game 'bg2hd/payload/map-ar0703/AR0703.TIS'))) 'La reinstallation alpha.3 n a pas republie le contenu.'
        foreach($id in @(1060,0)){$result=Invoke-WeiDU '.\setup-bg2hd.exe' @('--noautoupdate','--uninstall',"$id",'--language','0','--no-exit-pause');Require ($result.code -eq 0) "Desinstallation $id echouee : $($result.output)"}
    } finally {Pop-Location}
    Require ((Get-Hash (Join-Path $game 'Baldur.exe')) -eq $originalBaldur) 'Baldur.exe a ete modifie pendant la mise a jour.';Require (-not(Test-Path -LiteralPath (Join-Path $game 'BaldurReal.exe'))) 'BaldurReal.exe a ete cree pendant la mise a jour.';Require ((Get-Hash (Join-Path $steamSource 'Baldur.exe')) -eq $originalBaldur) 'La source Steam a ete modifiee.';Require ((Get-Hash $fixture) -eq $fixtureHash) 'Fixture AR0703 non restaure apres mise a jour.'
    Write-Output 'PHASE5A_WEIDU_UPDATE=PASSED'
}
finally {if($null -eq $previousDesktop){Remove-Item Env:BG2HD_DESKTOP_PATH -ErrorAction SilentlyContinue}else{$env:BG2HD_DESKTOP_PATH=$previousDesktop};if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}}
