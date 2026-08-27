[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$GameRoot,
    [Parameter(Mandatory)] [string]$WeiDUExecutable
)

$ErrorActionPreference = 'Stop'
$releaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$fixtureSource = Join-Path $releaseRoot 'tests/phase2-fixture'
$fixtureDestination = Join-Path $gameRootPath 'bg2hd-phase2-fixture'
$setupDestination = Join-Path $gameRootPath 'setup-bg2hd-phase2-fixture.exe'

if (Test-Path -LiteralPath $fixtureDestination) { throw "Fixture deja presente : $fixtureDestination" }
if (Test-Path -LiteralPath $setupDestination) { throw "Executable de test deja present : $setupDestination" }
if (-not (Test-Path -LiteralPath $WeiDUExecutable -PathType Leaf)) { throw "WeiDU introuvable : $WeiDUExecutable" }

$locationPushed = $false
try {
    Copy-Item -LiteralPath $fixtureSource -Destination $fixtureDestination -Recurse
    Copy-Item -LiteralPath $WeiDUExecutable -Destination $setupDestination
    Push-Location -LiteralPath $gameRootPath
    $locationPushed = $true
    & $setupDestination '--nogame' '--noautoupdate' '--force-install-list' '9000' '--language' '0' '--no-exit-pause'
    if ($LASTEXITCODE -ne 0) { throw "Installation fixture WeiDU echouee : code $LASTEXITCODE" }
    $marker = Join-Path $fixtureDestination 'installed-marker.txt'
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) { throw 'Le marqueur fixture est absent apres installation.' }
    & $setupDestination '--nogame' '--noautoupdate' '--uninstall' '9000' '--language' '0' '--no-exit-pause'
    if ($LASTEXITCODE -ne 0) { throw "Desinstallation fixture WeiDU echouee : code $LASTEXITCODE" }
    if (Test-Path -LiteralPath $marker) { throw 'Le marqueur fixture subsiste apres desinstallation.' }
} finally {
    if ($locationPushed) { Pop-Location }
    if (Test-Path -LiteralPath $setupDestination) { Remove-Item -LiteralPath $setupDestination }
    if (Test-Path -LiteralPath $fixtureDestination) { Remove-Item -LiteralPath $fixtureDestination -Recurse }
}

Write-Output 'WeiDU fixture install/uninstall passed. Only the isolated fixture directory and WeiDU.log were changed transiently.'
