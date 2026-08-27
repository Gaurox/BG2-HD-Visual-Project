[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateSet('Test','Install','Restore')] [string]$Action,
    [Parameter(Mandatory)] [string]$GameRoot,
    [string]$RendererManifestPath,
    [string]$PayloadRoot,
    [string]$StatePath
)

$ErrorActionPreference = 'Stop'
if (-not $RendererManifestPath) { $RendererManifestPath = Join-Path $PSScriptRoot '..\manifests\renderer-bundle.json' }
if (-not $PayloadRoot) { $PayloadRoot = Join-Path $PSScriptRoot '..\renderer' }
function Resolve-Absolute([string]$Path) { (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path }
function Read-Json([string]$Path) { Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json }
function Get-Hash([string]$Path) { $sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()} }
function Same([string]$Path,[string]$Hash) { (Test-Path -LiteralPath $Path -PathType Leaf) -and (Get-Hash $Path) -eq $Hash }
function Write-AtomicJson([string]$Path,[object]$Value) { $directory=Split-Path -Parent $Path;New-Item -ItemType Directory -Path $directory -Force|Out-Null;$temporary=Join-Path $directory ('.'+[IO.Path]::GetFileName($Path)+'.'+[guid]::NewGuid().ToString('N')+'.tmp');[IO.File]::WriteAllText($temporary,($Value|ConvertTo-Json -Depth 32),[Text.UTF8Encoding]::new($false));Move-Item -LiteralPath $temporary -Destination $Path -Force }
function Relative([string]$Path) { $Path.Replace('/','\') }
function Require([bool]$Condition,[string]$Message) { if(-not $Condition){throw $Message} }

$game=Resolve-Absolute $GameRoot
$manifestPath=Resolve-Absolute $RendererManifestPath
$payload=Resolve-Absolute $PayloadRoot
$manifest=Read-Json $manifestPath
if(-not $StatePath){$StatePath=Join-Path $game 'bg2hd\state\renderer-files.json'}
$expectedPaths=@('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.sample.ini','iee-textures/iee_water_dudv.rgba','iee-textures/iee_water_foam.rgba','iee-textures/iee_water_normal.rgba','iee-textures/README.md','override/fpSEAM.glsl','override/M_IEEE.lua')
Require ($manifest.status -in @('integrated-awaiting-clean-lifecycle-test','integrated-in-place-awaiting-user-lifecycle-test')) "Bundle renderer non eligible : $($manifest.status)"
$manifestPaths=@($manifest.files|ForEach-Object{[string]$_.path})
Require (-not (Compare-Object ($expectedPaths|Sort-Object) ($manifestPaths|Sort-Object))) 'Inventaire renderer inattendu.'
foreach($file in @($manifest.files)){
    $source=Join-Path $payload (Relative $file.path)
    Require (Test-Path -LiteralPath $source -PathType Leaf) "Payload renderer absent : $($file.path)"
    Require ((Get-Item -LiteralPath $source).Length -eq [int64]$file.bytes -and (Get-Hash $source) -eq $file.sha256) "Payload renderer invalide : $($file.path)"
}
$runtimeFiles=@($manifest.files|Where-Object{$_.path -ne 'InfinityEngine-Enhancer.sample.ini'})
function Read-State(){if(Test-Path -LiteralPath $StatePath){Read-Json $StatePath}else{$null}}
function Assert-OwnState([object]$State){
    Require ($State.schema_version -eq 1 -and $State.game_root -eq $game) 'Etat renderer associe a un autre jeu.'
    foreach($record in @($State.files)){
        $target=Join-Path $game (Relative $record.path)
        Require (Same $target $record.installed_sha256) "Renderer modifie hors BG2HD : $($record.path)"
    }
}
function New-Records(){
    $records=@()
    foreach($file in $runtimeFiles){
        $target=Join-Path $game (Relative $file.path);$present=Test-Path -LiteralPath $target -PathType Leaf;$before=$null;$backup=$null
        if($present){$before=Get-Hash $target;$backup=Join-Path (Split-Path -Parent $StatePath) ('renderer-backups\'+(Relative $file.path));New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force|Out-Null;Copy-Item -LiteralPath $target -Destination $backup;if(-not(Same $backup $before)){throw "Sauvegarde renderer invalide : $($file.path)"}}
        $records += [ordered]@{path=$file.path;existed_before=$present;before_sha256=$before;backup_path=$backup;installed_sha256=$file.sha256}
    }
    return @($records)
}
function Restore-Records([object[]]$Records,[switch]$OnlyPublished){
    foreach($record in $Records){
        $target=Join-Path $game (Relative $record.path)
        if(-not(Same $target $record.installed_sha256)){if($OnlyPublished){continue};throw "Refus de restaurer un renderer modifie : $($record.path)"}
        if($record.existed_before){Require (Same $record.backup_path $record.before_sha256) "Sauvegarde renderer invalide : $($record.path)";Copy-Item -LiteralPath $record.backup_path -Destination $target -Force;Require (Same $target $record.before_sha256) "Restauration renderer invalide : $($record.path)"}
        else{Remove-Item -LiteralPath $target -ErrorAction Stop}
    }
}
function Install-Renderer(){
    $state=Read-State
    if($state -and $state.phase -eq 'installed'){
        Assert-OwnState $state
        $sameBundle=($state.bundle_id -eq $manifest.bundle_id -and $state.manifest_sha256 -eq (Get-Hash $manifestPath))
        if($sameBundle){return}
        foreach($record in @($state.files)){
            $next=@($runtimeFiles|Where-Object{$_.path -eq $record.path})
            Require ($next.Count -eq 1) "Chemin renderer absent du nouveau bundle : $($record.path)"
            $record.installed_sha256=$next[0].sha256
        }
        $state.phase='prepared-update'
        Write-AtomicJson $StatePath $state
    } elseif($state -and $state.phase -notin @('uninstalled')){throw "Etat renderer non installable : $($state.phase)"}
    if(-not $state -or $state.phase -eq 'uninstalled'){
        $state=[ordered]@{schema_version=1;phase='prepared';game_root=$game;bundle_id=$manifest.bundle_id;manifest_sha256=(Get-Hash $manifestPath);files=(New-Records);created_at=(Get-Date).ToUniversalTime().ToString('o')}
        Write-AtomicJson $StatePath $state
    }
    try{
        foreach($record in @($state.files)){
            $source=Join-Path $payload (Relative $record.path);$target=Join-Path $game (Relative $record.path)
            if(Same $target $record.installed_sha256){continue}
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null
            Copy-Item -LiteralPath $source -Destination $target -Force
            Require (Same $target $record.installed_sha256) "Publication renderer invalide : $($record.path)"
        }
        $state.phase='installed';$state.bundle_id=$manifest.bundle_id;$state.manifest_sha256=Get-Hash $manifestPath;$state|Add-Member -Force -NotePropertyName installed_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'));Write-AtomicJson $StatePath $state
    }catch{
        try{Restore-Records @($state.files) -OnlyPublished}catch{}
        $state.phase='uninstalled';$state|Add-Member -Force -NotePropertyName rollback_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'));Write-AtomicJson $StatePath $state
        throw
    }
}
function Restore-Renderer(){
    $state=Read-State
    if(-not $state -or $state.phase -eq 'uninstalled'){return}
    Require ($state.phase -eq 'installed') "Etat renderer non restaurable : $($state.phase)"
    Assert-OwnState $state
    Restore-Records @($state.files)
    $state.phase='uninstalled';$state|Add-Member -Force -NotePropertyName uninstalled_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'));Write-AtomicJson $StatePath $state
}

switch($Action){
    'Test' {$state=Read-State;if($state -and $state.phase -eq 'installed'){Assert-OwnState $state};[ordered]@{bundle_id=$manifest.bundle_id;state=if($state){$state.phase}else{'ready'};payload_root=$payload}|ConvertTo-Json;exit 0}
    'Install' {Install-Renderer;exit 0}
    'Restore' {Restore-Renderer;exit 0}
}
