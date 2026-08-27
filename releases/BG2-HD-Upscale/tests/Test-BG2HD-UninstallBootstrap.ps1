[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WeiDUExecutable,
    [Parameter(Mandatory)] [string]$GameRoot,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference='Stop'
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Copy-Required([string]$From,[string]$To){New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force|Out-Null;Copy-Item -LiteralPath $From -Destination $To -Recurse}
function Invoke-Bootstrap([string[]]$Arguments,[string]$Root){$output=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $Root 'bg2hd/tools/Install-BG2HD.ps1') @Arguments 2>&1|Out-String;[pscustomobject]@{code=$LASTEXITCODE;output=$output}}
function Invoke-BootstrapInteractive([string[]]$Arguments,[string]$Root,[string]$AnswerText){$output=$AnswerText|& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'bg2hd/tools/Install-BG2HD.ps1') @Arguments 2>&1|Out-String;[pscustomobject]@{code=$LASTEXITCODE;output=$output}}

$source=(Resolve-Path -LiteralPath $GameRoot).Path;$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path;$weidu=(Resolve-Path -LiteralPath $WeiDUExecutable).Path
$runtime=Get-Content -LiteralPath (Join-Path $release 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$officialSource=$null;foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $source $name;if((Test-Path -LiteralPath $candidate)-and(Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash-eq$runtime.target_game.sha256){$officialSource=$candidate;break}};Require ($null-ne$officialSource) 'Executable officiel absent de la fixture.'
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd';if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-uninstall-bootstrap-'+[Guid]::NewGuid().ToString('N'));$steam=Join-Path $temp 'steam-source';$game=Join-Path $temp 'game';$desktop=Join-Path $temp 'desktop';$previousDesktop=$env:BG2HD_DESKTOP_PATH
try {
    New-Item -ItemType Directory -Path $steam,$game,$desktop -Force|Out-Null;Copy-Required (Join-Path $source 'chitin.key') (Join-Path $steam 'chitin.key');Copy-Required $officialSource (Join-Path $steam 'Baldur.exe')
    foreach($relative in @('chitin.key','steam_appid.txt','InfinityLoader.db','EEex.dll','EEex.ini','InfinityLoader.exe','InfinityLoaderCommon.dll','InfinityLoaderDLL.dll','InfinityLoaderUtil.dll','LuaBindings.dll','LuaBindingsCore.dll','LuaProvider.dll','lang/en_US/dialog.tlk')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    [IO.File]::WriteAllText((Join-Path $game 'WeiDU.log'),"~EEEX/EEEX.TP2~ #0 #0`r`n~EEEX/EEEX.TP2~ #0 #1`r`n",[Text.UTF8Encoding]::new($false))
    Copy-Required $officialSource (Join-Path $game 'Baldur.exe');Copy-Required $loaderIniSource (Join-Path $game 'InfinityLoader.ini')
    foreach($relative in @('EEex','EEex_scripts','override')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    Copy-Required (Join-Path $release 'bg2hd') (Join-Path $game 'bg2hd');Copy-Required $weidu (Join-Path $game 'setup-bg2hd.exe');Copy-Required (Join-Path $release 'bg2hd/renderer/InfinityEngine-Enhancer.sample.ini') (Join-Path $game 'InfinityEngine-Enhancer.ini')
    $layoutPath=Join-Path $game 'bg2hd/state/install-layout.json';New-Item -ItemType Directory -Path (Split-Path -Parent $layoutPath) -Force|Out-Null;[IO.File]::WriteAllText($layoutPath,([ordered]@{schema_version=1;source_game_root=$steam;hd_game_root=$game;source_baldur_sha256=$runtime.target_game.sha256;launch_mode='dedicated-shortcut-only';steam_source_untouched=$true;created_at=(Get-Date).ToUniversalTime().ToString('o');package_version='test'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $game 'weidu.conf'),"lang_dir = en_US`r`n",[Text.UTF8Encoding]::new($false))
    $env:BG2HD_DESKTOP_PATH=$desktop
    $install=Invoke-Bootstrap @('-Action','Install','-GameRoot',$game,'-SourceGameRoot',$steam,'--noautoupdate','--force-install-list','0','--language','0','--no-exit-pause') $game
    Require ($install.code -eq 0) "Installation bootstrap echouee : $($install.output)"
    $dependency=Get-Content -LiteralPath (Join-Path $game 'bg2hd/state/dependency-bootstrap.json') -Raw -Encoding utf8|ConvertFrom-Json
    Require ($dependency.eeex_origin -eq 'pre-existing') 'EEex pre-existant n a pas ete enregistre avant l installation BG2HD.'
    $nonInteractive=Invoke-Bootstrap @('-Action','Uninstall','-GameRoot',$game,'-SourceGameRoot',$steam,'-NonInteractive') $game
    Require ($nonInteractive.code -ne 0) 'Le choix de desinstallation a accepte un appel non interactif.'
    Require ($nonInteractive.output -match 'choix du mode de desinstallation exige une confirmation interactive') 'Le refus du choix non interactif est ambigu.'
    $core=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $game 'bg2hd/tools/bg2hd-steam.ps1') -Action Uninstall -GameRoot $game -DesktopPath $desktop -SkipProcessCheck 2>&1|Out-String
    Require ($LASTEXITCODE -eq 0) "Retrait Core de nettoyage echoue : $core"
    $resume=Invoke-BootstrapInteractive @('-Action','Uninstall','-GameRoot',$game,'-SourceGameRoot',$steam) $game "1`r`n"
    Require ($resume.code -eq 0) "Le desinstalleur ne reprend pas un Core deja retire : $($resume.output)"
    Require ($resume.output -match 'BG2HD est deja retire') 'La reprise de desinstallation deja retiree n a pas ete confirmee.'
    Write-Output 'UNINSTALL_BOOTSTRAP_GUARDS=PASSED'
}
finally {
    if($null -eq $previousDesktop){Remove-Item Env:BG2HD_DESKTOP_PATH -ErrorAction SilentlyContinue}else{$env:BG2HD_DESKTOP_PATH=$previousDesktop}
    if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}
}
