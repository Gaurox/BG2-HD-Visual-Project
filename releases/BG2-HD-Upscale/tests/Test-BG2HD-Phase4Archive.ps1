[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$ArchivePath,
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
function Get-RendererSnapshot([string]$Game,[object[]]$Files){$snapshot=@{};foreach($file in $Files){$path=Join-Path $Game ($file.path.Replace('/','\\'));$snapshot[$file.path]=if(Test-Path -LiteralPath $path -PathType Leaf){Get-Hash $path}else{$null}};return $snapshot}
function Require-RendererSnapshot([string]$Game,[hashtable]$Expected,[object[]]$Files){foreach($file in $Files){$path=Join-Path $Game ($file.path.Replace('/','\\'));$actual=if(Test-Path -LiteralPath $path -PathType Leaf){Get-Hash $path}else{$null};Require ($actual -eq $Expected[$file.path]) "Le fichier renderer n a pas ete restaure : $($file.path)"}}

$archive=(Resolve-Path -LiteralPath $ArchivePath).Path;$source=(Resolve-Path -LiteralPath $GameRoot).Path;$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
$rendererManifest=Get-Content -LiteralPath (Join-Path $release 'manifests/renderer-bundle.json') -Raw -Encoding utf8|ConvertFrom-Json
$runtime=Get-Content -LiteralPath (Join-Path $release 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$officialSource=$null;foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $source $name;if((Test-Path -LiteralPath $candidate)-and(Get-Hash $candidate)-eq$runtime.target_game.sha256){$officialSource=$candidate;break}};Require ($null-ne$officialSource) 'Executable officiel absent de la fixture.'
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd';if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}
$rendererRuntimeFiles=@($rendererManifest.files|Where-Object{$_.role -ne 'config-template'})
$temp=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-phase4-archive-'+[Guid]::NewGuid().ToString('N'));$steamSource=Join-Path $temp 'steam-source';$game=Join-Path $temp 'game';$desktop=Join-Path $temp 'desktop';$previousDesktop=$env:BG2HD_DESKTOP_PATH
try {
    New-Item -ItemType Directory -Path $steamSource,$game,$desktop -Force|Out-Null;Copy-Required $officialSource (Join-Path $steamSource 'Baldur.exe')
    foreach($relative in @('chitin.key','InfinityLoader.exe','EEex.dll','steam_appid.txt','InfinityEngine-Enhancer.ini','lang/en_US/dialog.tlk')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    [IO.File]::WriteAllText((Join-Path $game 'WeiDU.log'),"~EEEX/EEEX.TP2~ #0 #0`r`n~EEEX/EEEX.TP2~ #0 #1`r`n",[Text.UTF8Encoding]::new($false))
    Copy-Required $officialSource (Join-Path $game 'Baldur.exe');Copy-Required $loaderIniSource (Join-Path $game 'InfinityLoader.ini')
    $weiduConf=Join-Path $source 'weidu.conf';if(Test-Path -LiteralPath $weiduConf){Copy-Required $weiduConf (Join-Path $game 'weidu.conf');$lang=(Get-Content -LiteralPath $weiduConf -Raw|Select-String -Pattern '(?im)^\s*lang_dir\s*=\s*([^\s;#]+)').Matches.Groups[1].Value;if($lang){Copy-Required (Join-Path $source "lang/$lang/dialog.tlk") (Join-Path $game "lang/$lang/dialog.tlk")}}else{[IO.File]::WriteAllText((Join-Path $game 'weidu.conf'),"lang_dir = en_US`r`n",[Text.UTF8Encoding]::new($false))}
    $originalBaldur=Get-Hash (Join-Path $game 'Baldur.exe');$originalLoaderIni=Get-Hash (Join-Path $game 'InfinityLoader.ini');$originalRendererIni=Get-Hash (Join-Path $game 'InfinityEngine-Enhancer.ini')
    $originalRendererFiles=Get-RendererSnapshot $game $rendererRuntimeFiles
    $fixture=Join-Path $game 'override/AR0300.TIS';New-Item -ItemType Directory -Path (Split-Path -Parent $fixture) -Force|Out-Null;[IO.File]::WriteAllBytes($fixture,[byte[]](7,4,2,1));$fixtureHash=Get-Hash $fixture
    $uiFixture=Join-Path $game 'iee-assets/BIGLOGO-MOS0017-x4.dxt5';New-Item -ItemType Directory -Path (Split-Path -Parent $uiFixture) -Force|Out-Null;[IO.File]::WriteAllBytes($uiFixture,[byte[]](8,6,4,2));$uiFixtureHash=Get-Hash $uiFixture
    Expand-Archive -LiteralPath $archive -DestinationPath $game
    $layoutPath=Join-Path $game 'bg2hd/state/install-layout.json';New-Item -ItemType Directory -Path (Split-Path -Parent $layoutPath) -Force|Out-Null;[IO.File]::WriteAllText($layoutPath,([ordered]@{schema_version=1;source_game_root=$steamSource;hd_game_root=$game;source_baldur_sha256=$runtime.target_game.sha256;launch_mode='dedicated-shortcut-only';steam_source_untouched=$true;created_at=(Get-Date).ToUniversalTime().ToString('o');package_version='test'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    $env:BG2HD_DESKTOP_PATH=$desktop
    Push-Location $game
    try {
        foreach($id in @(0,100,110,1000,1010,1020,1030,1040,1050,1060)){$output=& .\setup-bg2hd.exe '--noautoupdate' '--force-install-list' "$id" '--language' '0' '--no-exit-pause' 2>&1|Out-String;$code=$LASTEXITCODE;Require ($code -eq 0) "Installation WeiDU echouee : composant $id ($code) $output"}
        $content=Get-Content -LiteralPath (Join-Path $release 'manifests/content.json') -Raw -Encoding utf8|ConvertFrom-Json
        $byDestination=@{};foreach($entry in $content.entries){if(-not $byDestination.ContainsKey($entry.destination) -or [int]$entry.install_order -ge [int]$byDestination[$entry.destination].install_order){$byDestination[$entry.destination]=$entry}}
        foreach($destination in $byDestination.Keys){$entry=$byDestination[$destination];$file=Join-Path $game ($destination.Replace('/','\'));Require (Test-Path -LiteralPath $file -PathType Leaf) "Fichier installe absent : $destination";Require ((Get-Hash $file) -eq $entry.sha256) "Hash installe incorrect : $destination"}
        $installedIni=Get-Content -LiteralPath (Join-Path $game 'InfinityEngine-Enhancer.ini') -Raw
        foreach($setting in @('EnableBigLogoX4Test\s*=\s*true','EnableMainMenuX4Test\s*=\s*true','EnableMenuX2Test\s*=\s*false')){Require ($installedIni -match "(?im)^\s*$setting\s*$") "Configuration UI x4 absente : $setting"}
        foreach($id in @(1060,1050,1040,1030,1020,1010,1000,110,100,0)){$output=& .\setup-bg2hd.exe '--noautoupdate' '--uninstall' "$id" '--language' '0' '--no-exit-pause' 2>&1|Out-String;$code=$LASTEXITCODE;Require ($code -eq 0) "Desinstallation WeiDU echouee : composant $id ($code) $output"}
    } finally {Pop-Location}
    Require ((Get-Hash (Join-Path $game 'Baldur.exe')) -eq $originalBaldur) 'Baldur.exe a ete modifie pendant le cycle archive.'
    Require (-not(Test-Path -LiteralPath (Join-Path $game 'BaldurReal.exe'))) 'BaldurReal.exe a ete cree pendant le cycle archive.'
    Require ((Get-Hash (Join-Path $game 'InfinityLoader.ini')) -eq $originalLoaderIni) 'InfinityLoader.ini a ete modifie pendant le cycle archive.'
    Require ((Get-Hash (Join-Path $steamSource 'Baldur.exe')) -eq $originalBaldur) 'La source Steam a ete modifiee pendant le cycle archive.'
    Require ((Get-Hash (Join-Path $game 'InfinityEngine-Enhancer.ini')) -eq $originalRendererIni) 'INI renderer non restaure apres archive.'
    Require-RendererSnapshot $game $originalRendererFiles $rendererRuntimeFiles
    Require ((Get-Hash $fixture) -eq $fixtureHash) 'Le fichier override precedent n a pas ete restaure.'
    Require ((Get-Hash $uiFixture) -eq $uiFixtureHash) 'L atlas UI precedent n a pas ete restaure.'
    Require ((Get-ChildItem -LiteralPath $desktop -File -ErrorAction SilentlyContinue).Count -eq 0) 'Le raccourci de test subsiste.'
    Write-Output 'PHASE4_ARCHIVE_INSTALL_UNINSTALL=PASSED'
}
finally {
    if($null -eq $previousDesktop){Remove-Item Env:BG2HD_DESKTOP_PATH -ErrorAction SilentlyContinue}else{$env:BG2HD_DESKTOP_PATH=$previousDesktop}
    if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}
}
