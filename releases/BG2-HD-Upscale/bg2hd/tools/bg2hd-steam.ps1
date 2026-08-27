[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateSet('Test','Status','Install','Repair','Uninstall','RestoreVanilla')] [string]$Action,
    [string]$GameRoot = (Get-Location).Path,
    [string]$CompatibilityManifestPath,
    [string]$ReleaseManifestPath,
    [string]$RendererManifestPath,
    [string]$RendererPayloadRoot,
    [string]$DesktopPath,
    [switch]$SkipProcessCheck,
    [string]$FaultAfterStep
)

$ErrorActionPreference='Stop'
if (-not $CompatibilityManifestPath) { $CompatibilityManifestPath = Join-Path $PSScriptRoot '..\manifests\runtime-compatibility.json' }
if (-not $ReleaseManifestPath) { $ReleaseManifestPath = Join-Path $PSScriptRoot '..\manifests\release.json' }
if (-not $RendererManifestPath) { $RendererManifestPath = Join-Path $PSScriptRoot '..\manifests\renderer-bundle.json' }
if (-not $RendererPayloadRoot) { $RendererPayloadRoot = Join-Path $PSScriptRoot '..\renderer' }
if (-not $DesktopPath) { $DesktopPath = if ($env:BG2HD_DESKTOP_PATH) { $env:BG2HD_DESKTOP_PATH } else { [Environment]::GetFolderPath('Desktop') } }
function Absolute([string]$p){(Resolve-Path -LiteralPath $p -ErrorAction Stop).Path}
function Hash([string]$p){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($p)))).Replace('-','')}finally{$sha.Dispose()}}
function Json([string]$p){Get-Content -LiteralPath $p -Raw -Encoding utf8|ConvertFrom-Json}
function Write-AtomicJson([string]$p,[object]$o){$d=Split-Path -Parent $p;New-Item -ItemType Directory -Path $d -Force|Out-Null;$t=Join-Path $d ('.'+[IO.Path]::GetFileName($p)+'.'+[guid]::NewGuid().ToString('N')+'.tmp');[IO.File]::WriteAllText($t,($o|ConvertTo-Json -Depth 32),[Text.UTF8Encoding]::new($false));Move-Item -LiteralPath $t -Destination $p -Force}
function Same([string]$p,[string]$h){(Test-Path -LiteralPath $p -PathType Leaf) -and (Hash $p) -eq $h}
function TempNear([string]$p,[string]$tag){Join-Path (Split-Path -Parent $p) ('.'+[IO.Path]::GetFileName($p)+'.bg2hd-'+$tag+'-'+[guid]::NewGuid().ToString('N')+'.tmp')}
function Copy-Verified([string]$from,[string]$to,[string]$expected){Copy-Item -LiteralPath $from -Destination $to -ErrorAction Stop;if((Hash $to)-ne$expected){throw "Empreinte incorrecte apres copie : $to"}}
function Fail-IfRequested([string]$step){if($FaultAfterStep -eq $step){throw "Panne simulee apres $step"}}

$game=Absolute $GameRoot;$compat=Json (Absolute $CompatibilityManifestPath);$release=Json (Absolute $ReleaseManifestPath)
$baldur=Join-Path $game 'Baldur.exe';$real=Join-Path $game 'BaldurReal.exe';$loader=Join-Path $game 'InfinityLoader.exe';$loaderIni=Join-Path $game 'InfinityLoader.ini';$eeex=Join-Path $game 'EEex.dll';$statePath=Join-Path $game 'bg2hd/state/steam-launcher.json';$backupDir=Join-Path $game 'bg2hd/state/backups';$rendererTool=Join-Path $PSScriptRoot 'bg2hd-renderer.ps1';$rendererStatePath=Join-Path $game 'bg2hd/state/renderer-files.json';$rendererTemplate=Join-Path $RendererPayloadRoot 'InfinityEngine-Enhancer.sample.ini'
function State(){if(Test-Path -LiteralPath $statePath){Json $statePath}else{$null}}
function New-TransactionState(){[ordered]@{schema_version=2;transaction_id=[guid]::NewGuid().ToString();mod_version=$release.version;phase='prepared';game_root=$game;launch_mode='steam-shim-in-place';completed_steps=@();files=@();shortcut=$null}}
function Invoke-Renderer([string]$RendererAction){& $rendererTool -Action $RendererAction -GameRoot $game -RendererManifestPath $RendererManifestPath -PayloadRoot $RendererPayloadRoot -StatePath $rendererStatePath|Out-Null;if($LASTEXITCODE -ne 0){throw "Action renderer echouee : $RendererAction"}}
function Ensure-Renderer([object]$state){
    if(-not $state.renderer_files_state){$state|Add-Member -Force -NotePropertyName renderer_files_state -NotePropertyValue $rendererStatePath;Write-AtomicJson $statePath $state}
    Invoke-Renderer 'Install'
    $configTool=Join-Path $PSScriptRoot 'bg2hd-config.ps1';$configState=Join-Path $game 'bg2hd/state/renderer-config.json'
    # The state journal can legitimately survive a full vanilla restore while
    # the INI it described has been removed. Apply is idempotent and must
    # revalidate/recreate the real file on every installation cycle.
    & $configTool -Action Apply -GameRoot $game -CompatibilityManifestPath $CompatibilityManifestPath -StatePath $configState -TemplatePath $rendererTemplate -Owner 'core-steam'
    if($LASTEXITCODE -ne 0){throw 'Fusion renderer echouee.'}
    $state|Add-Member -Force -NotePropertyName renderer_config_state -NotePropertyValue $configState;Write-AtomicJson $statePath $state
}
function Assert-Processes(){if($SkipProcessCheck){return};foreach($name in @('Baldur','InfinityLoader')){foreach($p in @(Get-Process -Name $name -ErrorAction SilentlyContinue)){try{if($p.Path -and ([IO.Path]::GetFullPath($p.Path)).StartsWith($game,[StringComparison]::OrdinalIgnoreCase)){throw "Processus ouvert : $name ($($p.Id))"}}catch{if($_.Exception.Message -like 'Processus ouvert*'){throw}}}}}
function Assert-Base(){
    if(-not [Environment]::Is64BitOperatingSystem){throw 'Windows x64 requis.'}
    foreach($p in @((Join-Path $game 'chitin.key'),$baldur,$loader,$eeex,(Join-Path $game 'steam_appid.txt'),$loaderIni)){if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "Fichier requis absent : $p"}}
    if(-not((Test-Path -LiteralPath (Join-Path $game 'dialog.tlk')) -or (Test-Path -LiteralPath (Join-Path $game 'lang/en_US/dialog.tlk')))){throw 'dialog.tlk absent.'}
    if((Get-Content -LiteralPath (Join-Path $game 'steam_appid.txt') -Raw).Trim() -ne [string]$compat.target_game.steam_app_id){throw 'Steam App ID non supporte.'}
    if(-not(Same $loader $compat.eeex.files[1].sha256) -or -not(Same $eeex $compat.eeex.files[0].sha256)){throw 'EEex ou InfinityLoader non supporte.'}
    $log=Join-Path $game 'WeiDU.log';if(-not(Test-Path -LiteralPath $log)){throw 'WeiDU.log absent.'};$logText=Get-Content -LiteralPath $log -Raw;if($logText -notmatch '(?i)EEEX/EEEX\.TP2~ #0 #0' -or $logText -notmatch '(?i)EEEX/EEEX\.TP2~ #0 #1'){throw 'Composants EEex 0/1 absents de WeiDU.log.'}
    Invoke-Renderer 'Test'
    Assert-Processes
}
function Get-Mode(){
    $state=State;$official=$compat.target_game.sha256;$loaderHash=$compat.eeex.files[1].sha256
    if($state -and $state.phase -eq 'installed' -and (Same $real $official) -and (Same $baldur $loaderHash)){return 'installed'}
    if($state -and $state.phase -eq 'eeex-retained' -and (Same $real $official) -and (Same $baldur $loaderHash)){return 'eeex-steam'}
    if($state -and $state.phase -eq 'installed' -and (Same $real $official) -and (Same $baldur $official)){return 'steam-repaired'}
    if(-not $state -and (Same $baldur $official) -and -not(Test-Path -LiteralPath $real)){return 'clean'}
    if($state -and $state.phase -in @('uninstalled','vanilla-restored') -and (Same $baldur $official) -and -not(Test-Path -LiteralPath $real)){return 'clean'}
    # A failed transaction which has already restored the official executable is
    # safe to retry.  Its state file remains as an audit record only.
    if($state -and $state.phase -eq 'failed' -and (Same $baldur $official) -and -not(Test-Path -LiteralPath $real)){return 'clean'}
    return 'foreign'
}
function Set-LoaderIni(){
    $lines=[Collections.Generic.List[string]]::new();Get-Content -LiteralPath $loaderIni|ForEach-Object{$lines.Add($_)};$inGeneral=$false;$nameIndex=-1;$aliasIndex=-1
    for($i=0;$i-lt$lines.Count;$i++){if($lines[$i]-match '^\s*\[(.+?)\]'){$inGeneral=$Matches[1]-ieq'General';continue};if($inGeneral -and $lines[$i]-match '^\s*ExeNames\s*='){$nameIndex=$i};if($inGeneral -and $lines[$i]-match '^\s*ExeSwitchAlias\s*='){$aliasIndex=$i}}
    if($nameIndex-lt 0 -or $aliasIndex-lt 0){throw 'InfinityLoader.ini ne contient pas les cles General attendues.'}
    $names=(($lines[$nameIndex]-split '=',2)[1]-split ','|ForEach-Object{$_.Trim()}|Where-Object{$_ -and $_ -ine 'Baldur.exe' -and $_ -ine 'BaldurReal.exe'});$aliases=(($lines[$aliasIndex]-split '=',2)[1]-split ','|ForEach-Object{$_.Trim()}|Where-Object{$_ -and $_ -notmatch '^(?i)BaldurReal\.exe:'})
    $lines[$nameIndex]='ExeNames='+(@('BaldurReal.exe')+$names -join ',');$lines[$aliasIndex]='ExeSwitchAlias='+(@('BaldurReal.exe:Baldur.exe')+$aliases -join ',')
    $temp=TempNear $loaderIni 'ini';[IO.File]::WriteAllLines($temp,$lines,[Text.UTF8Encoding]::new($false));Move-Item -LiteralPath $temp -Destination $loaderIni -Force
}
function New-Shortcut([object]$state){New-Item -ItemType Directory -Path $DesktopPath -Force|Out-Null;$desired=Join-Path $DesktopPath "Baldur's Gate II Enhanced Edition - HD.lnk";$path=$desired;if(Test-Path -LiteralPath $desired){$shell=New-Object -ComObject WScript.Shell;$s=$shell.CreateShortcut($desired);if($s.TargetPath -ne $loader){$path=Join-Path $DesktopPath "Baldur's Gate II Enhanced Edition - HD (BG2HD).lnk"}};$shell=New-Object -ComObject WScript.Shell;$s=$shell.CreateShortcut($path);$s.TargetPath=$loader;$s.WorkingDirectory=$game;$s.IconLocation="$real,0";$s.Arguments='';$s.Save();[ordered]@{path=$path;target=$loader;working_directory=$game;icon_location="$real,0";arguments=''}}
function Remove-Shortcut([object]$shortcut){if(-not $shortcut -or -not(Test-Path -LiteralPath $shortcut.path)){return};$shell=New-Object -ComObject WScript.Shell;$s=$shell.CreateShortcut($shortcut.path);if($s.TargetPath -eq $shortcut.target -and $s.WorkingDirectory -eq $shortcut.working_directory){Remove-Item -LiteralPath $shortcut.path}}
function Preflight(){Assert-Base;$mode=Get-Mode;if($mode-eq'foreign'){throw 'Etat executable etranger : aucune ecriture autorisee.'};[ordered]@{game_root=$game;mode=$mode;official_sha256=$compat.target_game.sha256;loader_sha256=$compat.eeex.files[1].sha256}}
function Install-Or-Repair([bool]$repair){$pre=Preflight;if($repair -and $pre.mode -ne 'steam-repaired'){throw 'Repair exige un shim installe puis remplace exactement par Steam.'};if(-not $repair -and $pre.mode -notin @('clean','steam-repaired','installed','eeex-steam')){throw 'Installation non autorisee dans cet etat.'}
    $oldState=State
    $newCycle=(-not $oldState) -or $oldState.phase -in @('eeex-retained','vanilla-restored') -or ($oldState.phase -eq 'failed' -and $pre.mode -eq 'clean')
    $state=if($newCycle){New-TransactionState}else{$oldState}
    $state|Add-Member -Force -NotePropertyName schema_version -NotePropertyValue 2
    $state|Add-Member -Force -NotePropertyName launch_mode -NotePropertyValue 'steam-shim-in-place'
    if($pre.mode -eq 'installed'){Ensure-Renderer $state;$state.phase='installed';Write-AtomicJson $statePath $state;return}
    New-Item -ItemType Directory -Path $backupDir -Force|Out-Null;if(-not $state.ini_backup){$iniBackup=Join-Path $backupDir 'InfinityLoader.ini.before-bg2hd';Copy-Item -LiteralPath $loaderIni -Destination $iniBackup -Force;$state|Add-Member -NotePropertyName ini_backup -NotePropertyValue ([ordered]@{path=$iniBackup;sha256=(Hash $iniBackup)})}
    $state.phase='prepared';Write-AtomicJson $statePath $state
    $originalTemp=$null;try{
        Ensure-Renderer $state;$state.completed_steps+='renderer-files-installed';Fail-IfRequested 'renderer-files-installed'
        if($pre.mode -eq 'clean'){$realTemp=TempNear $real 'real';Copy-Verified $baldur $realTemp $pre.official_sha256;Move-Item -LiteralPath $realTemp -Destination $real;$state.completed_steps+= 'baldur-real-created';Fail-IfRequested 'baldur-real-created'}
        $loaderTemp=TempNear $baldur 'loader';Copy-Verified $loader $loaderTemp $pre.loader_sha256;$originalTemp=TempNear $baldur 'previous';Move-Item -LiteralPath $baldur -Destination $originalTemp;Move-Item -LiteralPath $loaderTemp -Destination $baldur;$state.completed_steps+='steam-shim-published';Fail-IfRequested 'steam-shim-published'
        Set-LoaderIni;$state.completed_steps+='loader-ini-merged';Fail-IfRequested 'loader-ini-merged'
        $state.completed_steps+='renderer-config-merged';Fail-IfRequested 'renderer-config-merged'
        $state.shortcut=New-Shortcut $state;$state.completed_steps+='shortcut-created';Fail-IfRequested 'shortcut-created'
        if(-not(Same $baldur $pre.loader_sha256) -or -not(Same $real $pre.official_sha256)){throw 'Verification finale du shim echouee.'};if(Test-Path -LiteralPath $originalTemp){Remove-Item -LiteralPath $originalTemp};$state.phase='installed';Write-AtomicJson $statePath $state
    }catch{try{if($state.renderer_config_state -and(Test-Path -LiteralPath $state.renderer_config_state)){& (Join-Path $PSScriptRoot 'bg2hd-config.ps1') -Action Restore -GameRoot $game -CompatibilityManifestPath $CompatibilityManifestPath -StatePath $state.renderer_config_state};if($state.renderer_files_state){Invoke-Renderer 'Restore'};if($originalTemp -and(Test-Path -LiteralPath $originalTemp)){if(Test-Path -LiteralPath $baldur){Remove-Item -LiteralPath $baldur};Move-Item -LiteralPath $originalTemp -Destination $baldur};if((Test-Path -LiteralPath $real) -and(Same $real $pre.official_sha256) -and $pre.mode -eq 'clean'){Remove-Item -LiteralPath $real};if($state.ini_backup -and(Same $state.ini_backup.path $state.ini_backup.sha256)){Copy-Item -LiteralPath $state.ini_backup.path -Destination $loaderIni -Force};Remove-Shortcut $state.shortcut}catch{};$state.phase='failed';Write-AtomicJson $statePath $state;throw}
}
function Uninstall(){Assert-Base;$state=State;if(-not $state -or $state.phase -notin @('installed','failed')){throw 'Etat BG2 HD installe absent.'};if($state.game_root -ne $game){throw 'Etat associe a un autre dossier de jeu.'};$official=$compat.target_game.sha256;$loaderHash=$compat.eeex.files[1].sha256;if(-not(Same $real $official)){throw 'BaldurReal.exe est inconnu : refus de suppression.'};if(-not((Same $baldur $loaderHash) -or (Same $baldur $official))){throw 'Baldur.exe est inconnu : refus de desinstallation.'}
    if($state.renderer_config_state -and(Test-Path -LiteralPath $state.renderer_config_state)){& (Join-Path $PSScriptRoot 'bg2hd-config.ps1') -Action Restore -GameRoot $game -CompatibilityManifestPath $CompatibilityManifestPath -StatePath $state.renderer_config_state;if($LASTEXITCODE -ne 0){throw 'Restauration renderer echouee.'}}
    if($state.renderer_files_state){Invoke-Renderer 'Restore'}
    # EEex leaves an override guard which requires InfinityLoader. Keep the
    # verified Steam shim and its BaldurReal target when BG2HD alone is removed;
    # this preserves normal Steam launches without touching the shared EEex install.
    if(-not(Same $baldur $loaderHash)){throw 'Shim Steam EEex absent : utilisez le retour vanilla complet.'}
    Set-LoaderIni
    Remove-Shortcut $state.shortcut;$state.phase='eeex-retained';$state|Add-Member -Force -NotePropertyName eeex_retained_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'));Write-AtomicJson $statePath $state
}
function Test-EEexComponentInstalled([int]$Id){
    $log=Join-Path $game 'WeiDU.log'
    if(-not(Test-Path -LiteralPath $log -PathType Leaf)){return $false}
    return (Get-Content -LiteralPath $log -Raw) -match ('(?im)^~EEEX/EEEX\.TP2~\s*#0\s*#'+$Id+'(?:\s|$)')
}
function Invoke-EEexComponentRemoval([string]$Setup){
    # EEex v1.2.0 only supplies English, Chinese and Spanish WeiDU translations.
    # A French BG2EE installation can therefore have "lang_dir = fr_fr" in
    # weidu.conf, which makes its command-line uninstaller abort before acting.
    # Temporarily select the guaranteed English game TLK, then restore the user's
    # exact WeiDU configuration whether removal succeeds or not.
    $weiduConf=Join-Path $game 'weidu.conf';$hadWeiduConf=Test-Path -LiteralPath $weiduConf -PathType Leaf;$previous=$null
    if($hadWeiduConf){$previous=[IO.File]::ReadAllBytes($weiduConf)}
    try{
        [IO.File]::WriteAllText($weiduConf,"lang_dir = en_US`r`n",[Text.UTF8Encoding]::new($false))
        Push-Location $game
        try{
            foreach($id in @(1,0)){
                if(Test-EEexComponentInstalled $id){& $Setup '--noautoupdate' '--uninstall' "$id" '--no-exit-pause'|Out-Null;if($LASTEXITCODE -ne 0){throw "Desinstallation EEex du composant $id echouee : $LASTEXITCODE"}}
            }
        }finally{Pop-Location}
    }finally{
        if($hadWeiduConf){[IO.File]::WriteAllBytes($weiduConf,$previous)}elseif(Test-Path -LiteralPath $weiduConf){Remove-Item -LiteralPath $weiduConf -Force}
    }
}
function Restore-Vanilla(){
    Assert-Base;$state=State;if(-not $state -or $state.phase -ne 'eeex-retained'){throw 'Le retour vanilla complet exige un retrait BG2HD avec conservation EEex prealable.'};if($state.game_root -ne $game){throw 'Etat associe a un autre dossier de jeu.'}
    $official=$compat.target_game.sha256;$loaderHash=$compat.eeex.files[1].sha256
    if(-not(Same $real $official) -or -not(Same $baldur $loaderHash)){throw 'Shim Steam EEex invalide : retour vanilla refuse.'}
    $setup=Join-Path $game 'setup-EEex.exe';if(-not(Test-Path -LiteralPath $setup -PathType Leaf)){throw 'setup-EEex.exe absent : retour vanilla automatique impossible.'}
    try{
        Invoke-EEexComponentRemoval $setup
        foreach($id in @(1,0)){if(Test-EEexComponentInstalled $id){throw "Composant EEex $id encore installe apres retrait."}}
        $temp=TempNear $baldur 'vanilla';Copy-Verified $real $temp $official;$old=TempNear $baldur 'eeex-loader';Move-Item -LiteralPath $baldur -Destination $old;Move-Item -LiteralPath $temp -Destination $baldur;Remove-Item -LiteralPath $old
        if(-not(Same $baldur $official)){throw 'Restauration Baldur.exe vanilla echouee.'};Remove-Item -LiteralPath $real
        $dependencyState=Join-Path $game 'bg2hd/state/dependency-bootstrap.json';if(Test-Path -LiteralPath $dependencyState){Remove-Item -LiteralPath $dependencyState -Force}
        $state.phase='vanilla-restored';$state|Add-Member -Force -NotePropertyName vanilla_restored_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'));Write-AtomicJson $statePath $state
    }catch{
        $state.phase='vanilla-removal-incomplete';$state|Add-Member -Force -NotePropertyName vanilla_removal_failed_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'));Write-AtomicJson $statePath $state;throw
    }
}
switch($Action){'Test'{Preflight|ConvertTo-Json -Depth 8;exit 0}'Status'{[ordered]@{mode=Get-Mode;state=State}|ConvertTo-Json -Depth 16;exit 0}'Install'{Install-Or-Repair $false;exit 0}'Repair'{Install-Or-Repair $true;exit 0}'Uninstall'{Uninstall;exit 0}'RestoreVanilla'{Restore-Vanilla;exit 0}}
