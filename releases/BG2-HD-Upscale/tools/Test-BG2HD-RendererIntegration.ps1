[CmdletBinding()]
param([string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)

$ErrorActionPreference='Stop'
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Hash([string]$Path){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()}}
$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
$helper=Join-Path $release 'bg2hd\tools\bg2hd-renderer.ps1'
$config=Join-Path $release 'bg2hd\tools\bg2hd-config.ps1'
$manifestRoot=if(Test-Path -LiteralPath (Join-Path $release 'manifests') -PathType Container){Join-Path $release 'manifests'}else{Join-Path $release 'bg2hd\manifests'}
$rendererManifestPath=Join-Path $manifestRoot 'renderer-bundle.json'
$manifest=Get-Content -LiteralPath $rendererManifestPath -Raw -Encoding utf8|ConvertFrom-Json
$compat=Join-Path $manifestRoot 'runtime-compatibility.json'
$payload=Join-Path $release 'bg2hd\renderer'
$testRoot=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-renderer-'+[guid]::NewGuid().ToString('N'))
try{
    New-Item -ItemType Directory -Path $testRoot|Out-Null
    $expected=@($manifest.files|Where-Object{$_.path -ne 'InfinityEngine-Enhancer.sample.ini'})
    $before=@{}
    foreach($file in $expected){
        $target=Join-Path $testRoot $file.path.Replace('/','\');New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null
        [IO.File]::WriteAllText($target,"before-$($file.path)",[Text.UTF8Encoding]::new($false));$before[$file.path]=Hash $target
    }
    $state=Join-Path $testRoot 'bg2hd\state\renderer-files.json'
    & $helper -Action Test -GameRoot $testRoot -RendererManifestPath $rendererManifestPath -PayloadRoot $payload -StatePath $state|Out-Null
    Require ($LASTEXITCODE -eq 0) 'Preflight renderer fixture echoue.'
    & $helper -Action Install -GameRoot $testRoot -RendererManifestPath $rendererManifestPath -PayloadRoot $payload -StatePath $state
    Require ($LASTEXITCODE -eq 0) 'Installation renderer fixture echoue.'
    & $helper -Action Install -GameRoot $testRoot -RendererManifestPath $rendererManifestPath -PayloadRoot $payload -StatePath $state
    Require ($LASTEXITCODE -eq 0) 'Installation renderer idempotente echoue.'
    foreach($file in $expected){Require ((Hash (Join-Path $testRoot $file.path.Replace('/','\'))) -eq $file.sha256) "Fichier renderer non publie : $($file.path)"}
    $configState=Join-Path $testRoot 'bg2hd\state\renderer-config.json'
    & $config -Action Apply -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $configState -TemplatePath (Join-Path $payload 'InfinityEngine-Enhancer.sample.ini') -Owner core-steam
    Require ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path $testRoot 'InfinityEngine-Enhancer.ini'))) 'Configuration renderer creee echouee.'
    & $config -Action Restore -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $configState
    Require ($LASTEXITCODE -eq 0 -and -not(Test-Path -LiteralPath (Join-Path $testRoot 'InfinityEngine-Enhancer.ini'))) 'Configuration renderer creee doit etre retiree.'

    # A full vanilla cycle leaves the state journals but removes the generated
    # INI. The next Core/UI cycle must recreate it, and a repeated rollback
    # against a now-missing INI must remain a harmless no-op.
    & $config -Action Apply -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $configState -TemplatePath (Join-Path $payload 'InfinityEngine-Enhancer.sample.ini') -Owner core-steam
    Require ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path $testRoot 'InfinityEngine-Enhancer.ini'))) 'Reinstallation de la configuration Core apres retour vanilla echouee.'
    $uiConfigState=Join-Path $testRoot 'bg2hd\state\renderer-config-ui-mainmenu.json'
    & $config -Action Apply -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $uiConfigState -Owner ui-mainmenu-x4
    Require ($LASTEXITCODE -eq 0) 'Reinstallation de la configuration UI apres retour vanilla echouee.'
    & $config -Action Restore -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $uiConfigState -Owner ui-mainmenu-x4
    Require ($LASTEXITCODE -eq 0) 'Restauration de la configuration UI du second cycle echouee.'
    & $config -Action Restore -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $configState
    Require ($LASTEXITCODE -eq 0 -and -not(Test-Path -LiteralPath (Join-Path $testRoot 'InfinityEngine-Enhancer.ini'))) 'Restauration Core du second cycle echouee.'
    & $config -Action Restore -GameRoot $testRoot -CompatibilityManifestPath $compat -StatePath $uiConfigState -Owner ui-mainmenu-x4
    Require ($LASTEXITCODE -eq 0) 'Un rollback UI repete avec INI absent doit etre idempotent.'

    & $helper -Action Restore -GameRoot $testRoot -RendererManifestPath $rendererManifestPath -PayloadRoot $payload -StatePath $state
    Require ($LASTEXITCODE -eq 0) 'Restauration renderer fixture echoue.'
    foreach($file in $expected){Require ((Hash (Join-Path $testRoot $file.path.Replace('/','\'))) -eq $before[$file.path]) "Fichier renderer non restaure : $($file.path)"}

    & $helper -Action Install -GameRoot $testRoot -RendererManifestPath $rendererManifestPath -PayloadRoot $payload -StatePath $state
    $changed=Join-Path $testRoot 'override\M_IEEE.lua';[IO.File]::WriteAllText($changed,'external change',[Text.UTF8Encoding]::new($false))
    $restoreFailed=$false
    try{& $helper -Action Restore -GameRoot $testRoot -RendererManifestPath $rendererManifestPath -PayloadRoot $payload -StatePath $state}catch{$restoreFailed=$true}
    Require $restoreFailed 'La restauration doit refuser un renderer modifie.'
    Require ((Get-Content -LiteralPath $changed -Raw) -eq 'external change') 'Un fichier renderer externe a ete ecrase.'
    Write-Output 'BG2HD renderer integration validation passed.'
}finally{if(Test-Path -LiteralPath $testRoot){Remove-Item -LiteralPath $testRoot -Recurse -Force}}
