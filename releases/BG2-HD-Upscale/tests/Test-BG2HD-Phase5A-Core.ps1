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
function Get-Hash([string]$Path){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()}}
function Copy-Required([string]$From,[string]$To){New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force|Out-Null;Copy-Item -LiteralPath $From -Destination $To}
function Renderer-Snapshot([string]$Game){$snapshot=[ordered]@{};foreach($file in $rendererRuntimeFiles){$path=Join-Path $Game $file.path.Replace('/','\');$snapshot[$file.path]=if(Test-Path -LiteralPath $path -PathType Leaf){Get-Hash $path}else{$null}};$snapshot}
function Invoke-Helper([string]$Action,[string]$Root,[string]$Desktop,[string]$Fault=''){$args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $ReleaseRoot 'bg2hd/tools/bg2hd-steam.ps1'),'-Action',$Action,'-GameRoot',$Root,'-DesktopPath',$Desktop,'-SkipProcessCheck');if($Fault){$args+=@('-FaultAfterStep',$Fault)};& powershell.exe @args *> $null;$LASTEXITCODE}

$source=(Resolve-Path -LiteralPath $GameRoot).Path
$runtime=Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$officialSource=$null;foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $source $name;if((Test-Path -LiteralPath $candidate)-and(Get-Hash $candidate)-eq$runtime.target_game.sha256){$officialSource=$candidate;break}};Require ($null-ne$officialSource) 'Executable officiel absent de la fixture.'
$loaderIniSource=Join-Path $source 'InfinityLoader.ini';$backupIni=Join-Path $source 'bg2hd/state/backups/InfinityLoader.ini.before-bg2hd';if((Test-Path -LiteralPath $backupIni)-and((Get-Content -LiteralPath $backupIni -Raw)-match '(?im)^\s*ExeNames\s*=.*\bBaldur\.exe\b')){$loaderIniSource=$backupIni}
$rendererRuntimeFiles=@((Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/renderer-bundle.json') -Raw -Encoding utf8|ConvertFrom-Json).files|Where-Object{$_.path-ne'InfinityEngine-Enhancer.sample.ini'})
$temp=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-phase5a-core-'+[Guid]::NewGuid().ToString('N'))

function New-FakeGame([string]$Name,[string]$RendererIni=''){
    $game=Join-Path $temp $Name;$steam=Join-Path $temp "steam-$Name";New-Item -ItemType Directory -Path $game,$steam -Force|Out-Null
    Copy-Required $officialSource (Join-Path $steam 'Baldur.exe');Copy-Required $officialSource (Join-Path $game 'Baldur.exe');Copy-Required $loaderIniSource (Join-Path $game 'InfinityLoader.ini')
    foreach($relative in @('chitin.key','InfinityLoader.exe','EEex.dll','steam_appid.txt','InfinityEngine-Enhancer.ini','WeiDU.log','lang/en_US/dialog.tlk')){Copy-Required (Join-Path $source $relative) (Join-Path $game $relative)}
    if($RendererIni){[IO.File]::WriteAllText((Join-Path $game 'InfinityEngine-Enhancer.ini'),$RendererIni,[Text.UnicodeEncoding]::new($false,$true))}
    $layout=Join-Path $game 'bg2hd/state/install-layout.json';New-Item -ItemType Directory -Path (Split-Path -Parent $layout) -Force|Out-Null;[IO.File]::WriteAllText($layout,([ordered]@{schema_version=1;source_game_root=$steam;hd_game_root=$game;source_baldur_sha256=$runtime.target_game.sha256;launch_mode='dedicated-shortcut-only';steam_source_untouched=$true;created_at=(Get-Date).ToUniversalTime().ToString('o');package_version='test'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false));$game
}
function Snapshot([string]$Game){$layout=Get-Content -LiteralPath (Join-Path $Game 'bg2hd/state/install-layout.json') -Raw|ConvertFrom-Json;[ordered]@{baldur=Get-Hash (Join-Path $Game 'Baldur.exe');source_baldur=Get-Hash (Join-Path $layout.source_game_root 'Baldur.exe');loader_ini=Get-Hash (Join-Path $Game 'InfinityLoader.ini');renderer_ini=Get-Hash (Join-Path $Game 'InfinityEngine-Enhancer.ini');renderer_files=Renderer-Snapshot $Game}}
function Assert-Baseline([string]$Game,[object]$Before,[string]$Desktop,[string]$Label){
    $layout=Get-Content -LiteralPath (Join-Path $Game 'bg2hd/state/install-layout.json') -Raw|ConvertFrom-Json
    Require ((Get-Hash (Join-Path $Game 'Baldur.exe'))-eq$Before.baldur) "$Label : Baldur.exe modifie"
    Require (-not(Test-Path -LiteralPath (Join-Path $Game 'BaldurReal.exe'))) "$Label : BaldurReal.exe cree"
    Require ((Get-Hash (Join-Path $layout.source_game_root 'Baldur.exe'))-eq$Before.source_baldur) "$Label : source Steam modifiee"
    Require ((Get-Hash (Join-Path $Game 'InfinityLoader.ini'))-eq$Before.loader_ini) "$Label : InfinityLoader.ini modifie"
    Require ((Get-Hash (Join-Path $Game 'InfinityEngine-Enhancer.ini'))-eq$Before.renderer_ini) "$Label : INI renderer non restaure"
    foreach($file in $rendererRuntimeFiles){$path=Join-Path $Game $file.path.Replace('/','\');$actual=if(Test-Path -LiteralPath $path -PathType Leaf){Get-Hash $path}else{$null};Require ($actual-eq$Before.renderer_files.($file.path)) "$Label : renderer non restaure : $($file.path)"}
    Require ((Get-ChildItem -LiteralPath $Desktop -File -ErrorAction SilentlyContinue).Count-eq0) "$Label : raccourci BG2HD subsiste"
}
function Assert-Removed([string]$Game,[object]$Before,[string]$Desktop,[string]$Label){Assert-Baseline $Game $Before $Desktop $Label;$state=Get-Content -LiteralPath (Join-Path $Game 'bg2hd/state/launcher.json') -Raw|ConvertFrom-Json;Require ($state.phase-eq'bg2hd-removed') "$Label : phase retiree absente"}

try{
    New-Item -ItemType Directory -Path $temp -Force|Out-Null
    $missingLayout=New-FakeGame 'missing-layout';Remove-Item -LiteralPath (Join-Path $missingLayout 'bg2hd/state/install-layout.json');Require ((Invoke-Helper Test $missingLayout (Join-Path $temp 'desk-layout'))-ne0) 'Un dossier sans marqueur HD aurait du etre refuse.'
    $missingDll=New-FakeGame 'missing-eeex';$before=Snapshot $missingDll;Remove-Item -LiteralPath (Join-Path $missingDll 'EEex.dll');Require ((Invoke-Helper Test $missingDll (Join-Path $temp 'desk-missing'))-ne0) 'EEex absent aurait du etre refuse.';Require ((Get-Hash (Join-Path $missingDll 'Baldur.exe'))-eq$before.baldur) 'Refus EEex a modifie Baldur.exe.'
    $badExe=New-FakeGame 'unknown-exe';[IO.File]::WriteAllBytes((Join-Path $badExe 'Baldur.exe'),[byte[]](1,2,3,4));Require ((Invoke-Helper Test $badExe (Join-Path $temp 'desk-unknown'))-ne0) 'Executable inconnu aurait du etre refuse.';Require (-not(Test-Path -LiteralPath (Join-Path $badExe 'BaldurReal.exe'))) 'Refus executable a cree BaldurReal.exe.'
    $missingComponent=New-FakeGame 'missing-component';$log=Join-Path $missingComponent 'WeiDU.log';[IO.File]::WriteAllText($log,(Get-Content -LiteralPath $log -Raw).Replace('~EEEX/EEEX.TP2~ #0 #1','~EEEX/EEEX.TP2~ #0 #9'),[Text.UTF8Encoding]::new($false));Require ((Invoke-Helper Test $missingComponent (Join-Path $temp 'desk-component'))-ne0) 'Composant EEex manquant aurait du etre refuse.'

    foreach($fault in @('renderer-files-installed','renderer-config-merged','shortcut-created')){$game=New-FakeGame "fault-$fault";$desktop=Join-Path $temp "desk-$fault";New-Item -ItemType Directory -Path $desktop -Force|Out-Null;$before=Snapshot $game;Require ((Invoke-Helper Install $game $desktop $fault)-ne0) "La panne $fault aurait du interrompre l installation.";Assert-Baseline $game $before $desktop "Rollback $fault";Require ((Invoke-Helper Test $game $desktop)-eq0) "Rollback $fault non reinstallable."}

    $removed=New-FakeGame 'removed';$desktop=Join-Path $temp 'desk-removed';New-Item -ItemType Directory -Path $desktop -Force|Out-Null;$before=Snapshot $removed
    Require ((Invoke-Helper Install $removed $desktop)-eq0) 'Installation autonome echouee.';Require ((Invoke-Helper Uninstall $removed $desktop)-eq0) 'Desinstallation autonome echouee.';Assert-Removed $removed $before $desktop 'Desinstallation standard'
    Require ((Invoke-Helper Install $removed $desktop)-eq0) 'Reinstallation autonome echouee.';Require ((Invoke-Helper Uninstall $removed $desktop)-eq0) 'Seconde desinstallation autonome echouee.';Assert-Removed $removed $before $desktop 'Seconde desinstallation'

    $repair=New-FakeGame 'repair';$desktop=Join-Path $temp 'desk-repair';New-Item -ItemType Directory -Path $desktop -Force|Out-Null;$before=Snapshot $repair;Require ((Invoke-Helper Install $repair $desktop)-eq0) 'Installation de reparation echouee.';$shortcut=Join-Path $desktop "Baldur's Gate II Enhanced Edition - HD.lnk";Remove-Item -LiteralPath $shortcut;Require ((Invoke-Helper Repair $repair $desktop)-eq0) 'Repair du raccourci echoue.';Require (Test-Path -LiteralPath $shortcut) 'Repair n a pas recree le raccourci.';[IO.File]::WriteAllBytes((Join-Path $repair 'Baldur.exe'),[byte[]](9,8,7,6));Require ((Invoke-Helper Repair $repair $desktop)-ne0) 'Repair a accepte un executable inconnu.';Require ((Invoke-Helper Uninstall $repair $desktop)-ne0) 'Uninstall a accepte un executable inconnu.';Require (-not(Test-Path -LiteralPath (Join-Path $repair 'BaldurReal.exe'))) 'Layout legacy cree apres refus.'

    $customIni="; comment preserved`r`n[Core]`r`nVerboseLogs = true ; old`r`nPerformanceLogs = true`r`nUserValue = original`r`n`r`n[Shaders]`r`nEnableWaterEffect = false # old`r`nForeignShader = keep`r`n"
    $custom=New-FakeGame 'custom-ini' $customIni;$desktop=Join-Path $temp 'desk-custom';New-Item -ItemType Directory -Path $desktop -Force|Out-Null;$customBefore=Snapshot $custom;$userShortcut=Join-Path $desktop "Baldur's Gate II Enhanced Edition - HD.lnk";$shell=New-Object -ComObject WScript.Shell;$user=$shell.CreateShortcut($userShortcut);$user.TargetPath=Join-Path $env:WINDIR 'System32\notepad.exe';$user.WorkingDirectory=$env:WINDIR;$user.Save()
    Require ((Invoke-Helper Install $custom $desktop)-eq0) 'Installation avec collision raccourci echouee.';$ownedShortcut=Join-Path $desktop "Baldur's Gate II Enhanced Edition - HD (BG2HD).lnk";Require (Test-Path -LiteralPath $ownedShortcut) 'Raccourci alternatif absent.';Require (Test-Path -LiteralPath $userShortcut) 'Raccourci utilisateur ecrase.'
    $iniPath=Join-Path $custom 'InfinityEngine-Enhancer.ini';$iniText=[Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes($iniPath));[IO.File]::WriteAllText($iniPath,$iniText.Replace('UserValue = original','UserValue = user-change'),[Text.UnicodeEncoding]::new($false,$true))
    Require ((Invoke-Helper Uninstall $custom $desktop)-eq0) 'Uninstall avec INI externe modifie echoue.';Require ((Get-Hash (Join-Path $custom 'Baldur.exe'))-eq$customBefore.baldur) 'Uninstall a modifie Baldur.exe.';$restored=[Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes($iniPath));Require ($restored-match'UserValue = user-change') 'Modification INI externe perdue.';Require ($restored-match'VerboseLogs = true ; old') 'Cle possedee non restauree.';Require (Test-Path -LiteralPath $userShortcut) 'Raccourci utilisateur retire.';Require (-not(Test-Path -LiteralPath $ownedShortcut)) 'Raccourci BG2HD subsiste.'
    'PHASE5A_DEDICATED_CORE_MATRIX=PASSED'
}finally{if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}}
