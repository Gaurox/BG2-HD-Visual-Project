[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$GameRoot,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
function Copy-Required([string]$From,[string]$To){New-Item -ItemType Directory -Path (Split-Path -Parent $To) -Force|Out-Null;Copy-Item -LiteralPath $From -Destination $To -Force}
function Inspect([string]$Script,[string]$Root){
    if([IO.Path]::GetExtension($Script) -ieq '.exe'){$output=& $Script -Action Inspect -GameRoot $Root -NonInteractive 2>&1|Out-String}
    else{$output=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Script -Action Inspect -GameRoot $Root -NonInteractive 2>&1|Out-String}
    Require ($LASTEXITCODE -eq 0) "Inspection bootstrap echouee : $output"
    $output|ConvertFrom-Json
}

$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
$fixture=(Resolve-Path -LiteralPath $GameRoot).Path
& (Join-Path $release 'tools/Test-BG2HD-DependencyContract.ps1') -ReleaseRoot $release
$contract=Get-Content -LiteralPath (Join-Path $release 'manifests/dependency-bootstrap.json') -Raw -Encoding utf8|ConvertFrom-Json
$runtime=Get-Content -LiteralPath (Join-Path $release 'manifests/runtime-compatibility.json') -Raw -Encoding utf8|ConvertFrom-Json
$officialSource=$null
foreach($name in @('Baldur.exe','BaldurReal.exe')){$candidate=Join-Path $fixture $name;if((Test-Path -LiteralPath $candidate -PathType Leaf)-and(Hash $candidate)-eq$runtime.target_game.sha256){$officialSource=$candidate;break}}
$loaderSource=Join-Path $fixture 'InfinityLoader.exe'
if(-not(Test-Path -LiteralPath $loaderSource)){$loaderSource=Join-Path $fixture 'EEex/loader/InfinityLoader.exe'}
Require ($null-ne$officialSource) 'Executable officiel absent de la fixture bootstrap.'
Require ((Test-Path -LiteralPath $loaderSource -PathType Leaf) -and ((Hash $loaderSource) -eq @($runtime.eeex.files|Where-Object{$_.path-eq'InfinityLoader.exe'})[0].sha256)) 'InfinityLoader compatible absent de la fixture bootstrap.'

$testRoot=Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-bootstrap-'+[Guid]::NewGuid().ToString('N'))
try{
    $package=Join-Path $testRoot 'package';$script=Join-Path $package 'bg2hd/tools/Install-BG2HD.ps1'
    New-Item -ItemType Directory -Path (Split-Path -Parent $script), (Join-Path $package 'bg2hd/manifests'), (Join-Path $package 'bg2hd/renderer/override') -Force|Out-Null
    Copy-Required (Join-Path $release 'bg2hd/tools/Install-BG2HD.ps1') $script
    foreach($name in @('dependency-bootstrap.json','runtime-compatibility.json','release.json','renderer-bundle.json')){Copy-Required (Join-Path $release "manifests/$name") (Join-Path $package "bg2hd/manifests/$name")}
    Copy-Required (Join-Path $release 'bg2hd/renderer/override/M_IEEE.lua') (Join-Path $package 'bg2hd/renderer/override/M_IEEE.lua')

    function New-Game([string]$Name,[string]$Executable){
        $root=Join-Path $testRoot $Name;New-Item -ItemType Directory -Path $root -Force|Out-Null
        Copy-Required (Join-Path $fixture 'chitin.key') (Join-Path $root 'chitin.key')
        Copy-Required $Executable (Join-Path $root 'Baldur.exe')
        $root
    }

    $clean=New-Game 'clean-steam' $officialSource
    $cleanBefore=Hash (Join-Path $clean 'Baldur.exe')
    $inspection=Inspect $script $clean
    Require ($inspection.game_state -eq 'clean-steam' -and $inspection.eeex_state -eq 'absent') 'Une installation Steam vanilla propre doit etre admise.'
    $installOutput=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script -Action Install -GameRoot $clean -NonInteractive 2>&1|Out-String
    Require ($LASTEXITCODE -ne 0 -and $installOutput -match 'Visual C\+\+|EEex doit etre installe ou reactive') "Arret bootstrap inattendu : $installOutput"
    Require ((Hash (Join-Path $clean 'Baldur.exe'))-eq$cleanBefore) 'Le bootstrap incomplet a modifie Baldur.exe.'
    Require (-not(Test-Path -LiteralPath (Join-Path $clean 'BaldurReal.exe'))) 'Le bootstrap incomplet a cree BaldurReal.exe.'

    # Model the exact residue policy of the official WeiDU uninstall: sources
    # remain, while components and runtime binaries are gone.
    $inactive=New-Game 'eeex-inactive-after-vanilla-restore' $officialSource
    foreach($relative in @($contract.eeex.detection.inactive_residue_paths)){
        $target=Join-Path $inactive $relative
        if([IO.Path]::GetExtension($target)){
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null
            [IO.File]::WriteAllBytes($target,[byte[]]@())
        }else{
            New-Item -ItemType Directory -Path $target -Force|Out-Null
        }
    }
    $recentlyUninstalled=@($contract.eeex.installation.required_weidu_components|ForEach-Object{"// Recently Uninstalled: ~$($_.tp2)~ #0 #$($_.id) // $($_.name)"})-join"`r`n"
    [IO.File]::WriteAllText((Join-Path $inactive 'WeiDU.log'),$recentlyUninstalled+"`r`n",[Text.UTF8Encoding]::new($false))
    $inactiveInspection=Inspect $script $inactive
    Require ($inactiveInspection.game_state -eq 'clean-steam' -and $inactiveInspection.eeex_state -eq 'inactive') 'Les residus normaux apres retour vanilla doivent etre classes EEex inactif.'
    $inactiveBaldurBefore=Hash (Join-Path $inactive 'Baldur.exe')
    $inactiveInstallOutput=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script -Action Install -GameRoot $inactive -NonInteractive 2>&1|Out-String
    Require ($LASTEXITCODE -ne 0 -and $inactiveInstallOutput -match 'EEex doit etre installe ou reactive' -and $inactiveInstallOutput -notmatch 'partiellement installe') "Le flux EEex inactif ne repropose pas l installeur officiel : $inactiveInstallOutput"
    Require ((Hash (Join-Path $inactive 'Baldur.exe')) -eq $inactiveBaldurBefore -and -not(Test-Path -LiteralPath (Join-Path $inactive 'BaldurReal.exe'))) 'Le flux EEex inactif sans archive a modifie le jeu.'

    # Mixed states remain fail-closed: one active component or one declared
    # runtime file must never be treated as inactive.
    $firstComponent=@($contract.eeex.installation.required_weidu_components)[0]
    [IO.File]::WriteAllText((Join-Path $inactive 'WeiDU.log'),"~$($firstComponent.tp2)~ #0 #$($firstComponent.id) // $($firstComponent.name)`r`n",[Text.UTF8Encoding]::new($false))
    Require ((Inspect $script $inactive).eeex_state -eq 'partial') 'Un seul composant EEex actif doit rester classe partiel.'
    [IO.File]::WriteAllText((Join-Path $inactive 'WeiDU.log'),$recentlyUninstalled+"`r`n",[Text.UTF8Encoding]::new($false))
    Copy-Required $loaderSource (Join-Path $inactive 'InfinityLoader.exe')
    Require ((Inspect $script $inactive).eeex_state -eq 'partial') 'Un residu runtime EEex doit rester classe partiel.'

    $installed=New-Game 'installed-shim' $loaderSource
    Copy-Required $officialSource (Join-Path $installed 'BaldurReal.exe');Copy-Required $loaderSource (Join-Path $installed 'InfinityLoader.exe')
    Require ((Inspect $script $installed).game_state -eq 'bg2hd-steam-shim-installed') 'Le shim Steam BG2HD installe n est pas reconnu.'

    $repaired=New-Game 'steam-repaired' $officialSource
    Copy-Required $officialSource (Join-Path $repaired 'BaldurReal.exe')
    $state=Join-Path $repaired 'bg2hd/state/steam-launcher.json';New-Item -ItemType Directory -Path (Split-Path -Parent $state) -Force|Out-Null
    [IO.File]::WriteAllText($state,'{}',[Text.UTF8Encoding]::new($false))
    Require ((Inspect $script $repaired).game_state -eq 'steam-repaired-bg2hd') 'Le layout restaure par Steam Verify n est pas reconnu.'

    $foreign=New-Game 'foreign' (Join-Path $fixture 'chitin.key')
    $foreignOutput=& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script -Action Inspect -GameRoot $foreign -NonInteractive 2>&1|Out-String
    Require ($LASTEXITCODE -ne 0 -and $foreignOutput -match 'Executables BG2EE non supportes') 'Un executable etranger doit etre refuse sans ecriture.'

    $launcher=Join-Path $package 'Install-BG2HD.exe';$repeat=Join-Path $testRoot 'repeat/Install-BG2HD.exe'
    & (Join-Path $release 'tools/Build-BG2HDBootstrapLauncher.ps1') -ReleaseRoot $release -OutputPath $launcher|Out-Null
    & (Join-Path $release 'tools/Build-BG2HDBootstrapLauncher.ps1') -ReleaseRoot $release -OutputPath $repeat|Out-Null
    Require ((Hash $launcher)-eq(Hash $repeat)) 'Le launcher bootstrap doit etre reproductible.'
    & $launcher -Action Inspect -GameRoot $clean -NonInteractive
    Require ($LASTEXITCODE -eq 0) 'L inspection via Install-BG2HD.exe a echoue.'
    'BG2HD_IN_PLACE_BOOTSTRAP=PASSED'
}finally{if(Test-Path -LiteralPath $testRoot){Remove-Item -LiteralPath $testRoot -Recurse -Force}}
