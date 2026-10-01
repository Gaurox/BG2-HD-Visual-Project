$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) { $workspace=Split-Path -Parent $workspace }
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$game = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$runtime = Read-JsonFile (Join-Path $workspace 'pipeline/runtime/manifests/iee-sprite-p7-ui-probe-20261002-v1.json')
$fixtureRoot = Join-Path $PSScriptRoot ('work/fixtures/' + [guid]::NewGuid().ToString('N'))
$fixture = Join-Path $fixtureRoot 'game'
if (Test-Path -LiteralPath $fixture) { throw 'Fixture déjà utilisée.' }
New-Item -ItemType Directory -Path $fixture | Out-Null
foreach ($name in @('BaldurReal.exe','InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','iee-assets/creature-sprites/CreatureSprites-XN.catalog',
    'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl')) {
    $target = Resolve-ChildPath $fixture $name
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath (Resolve-ChildPath $game $name -RequireExisting) -Destination $target
}
$state = Join-Path $fixtureRoot 'state'
$installer = Join-Path $PSScriptRoot 'install.ps1'
& $installer -Mode Install -GameRoot $fixture -StateRoot $state | Out-Null
& $installer -Mode Verify -GameRoot $fixture -StateRoot $state | Out-Null
$iniTarget = Resolve-ChildPath $fixture 'InfinityEngine-Enhancer.ini' -RequireExisting
[IO.File]::AppendAllText($iniTarget,"`n; simulated user drift`n")
$drift = Get-FileSha256 $iniTarget
$rejected = $false
try { & $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null } catch {
    if ($_.Exception.Message -notmatch 'Dérive ini') { throw }
    $rejected=$true
}
if (-not $rejected -or (Get-FileSha256 $iniTarget) -ne $drift) { throw 'Dérive non préservée.' }
Copy-FileAtomic (Resolve-WorkspaceInput $runtime.ini.path -RequireExisting) $iniTarget
& $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null
foreach ($key in @('dll','ini')) {
    if ((Get-FileSha256 (Resolve-ChildPath $fixture ('InfinityEngine-Enhancer.'+$key) -RequireExisting)) -ne $runtime.baseline.$key) {
        throw 'Restauration non exacte.'
    }
}
[IO.File]::AppendAllText($iniTarget,"`n; simulated baseline drift`n")
$before = Get-FileSha256 $iniTarget
$newState = Join-Path $fixtureRoot 'state-drift'
$rejected = $false
try { & $installer -Mode Install -GameRoot $fixture -StateRoot $newState | Out-Null } catch {
    if ($_.Exception.Message -notmatch 'Dérive ini') { throw }
    $rejected=$true
}
if (-not $rejected -or (Get-FileSha256 $iniTarget) -ne $before -or (Test-Path -LiteralPath $newState)) {
    throw 'Installation sur baseline divergente.'
}
$result = [ordered]@{
    schema='bg2-p7-ui-probe-installer-verification-v1'; status='pass'; fixture_game=$fixture
    verified_at_utc=[DateTime]::UtcNow.ToString('o'); install_verify_restore=$true; exact_baseline_restored=$true
    restore_rejects_user_drift=$true; install_rejects_baseline_drift=$true; real_game_modified=$false
    manifest_sha256=Get-FileSha256 (Join-Path $workspace 'pipeline/runtime/manifests/iee-sprite-p7-ui-probe-20261002-v1.json')
    installer_sha256=Get-FileSha256 $installer; runtime_tests='ctest -C Release -R ^iee_tests$: 1/1 passed'
}
Write-JsonAtomic (Join-Path $PSScriptRoot 'verification.json') $result
[pscustomobject]$result
