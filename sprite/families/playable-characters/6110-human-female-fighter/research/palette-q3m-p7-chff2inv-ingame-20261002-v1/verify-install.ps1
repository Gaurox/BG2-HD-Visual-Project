$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) { $workspace=Split-Path -Parent $workspace }
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$proof = Join-Path $PSScriptRoot 'verification.json'
if (Test-Path -LiteralPath $proof) { throw 'Preuve finale déjà figée.' }
$game = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$manifest = Join-Path $workspace 'pipeline/runtime/manifests/iee-sprite-p7-chff2inv-q3m-20261002-v1.json'
$runtime = Read-JsonFile $manifest
$fixtureRoot = Join-Path $PSScriptRoot ('work/fixtures/' + [guid]::NewGuid().ToString('N'))
$fixture = Join-Path $fixtureRoot 'game'
New-Item -ItemType Directory -Path $fixture | Out-Null
foreach ($name in @('BaldurReal.exe','InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','iee-assets/creature-sprites/CreatureSprites-XN.catalog',
    'iee-assets/paperdolls/CHFF1INV-Q3m-X2.registry','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl')) {
    Copy-FileAtomic (Resolve-ChildPath $game $name -RequireExisting) (Resolve-ChildPath $fixture $name)
}
$state = Join-Path $fixtureRoot 'state'
$installer = Join-Path $PSScriptRoot 'install.ps1'
& $installer -Mode Install -GameRoot $fixture -StateRoot $state | Out-Null
& $installer -Mode Verify -GameRoot $fixture -StateRoot $state | Out-Null
$packTarget = Resolve-ChildPath $fixture $runtime.paperdoll_pack.target -RequireExisting
[IO.File]::AppendAllText($packTarget,'drift')
$drift = Get-FileSha256 $packTarget
$rejected = $false
try { & $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null } catch {
    if ($_.Exception.Message -notmatch 'Dérive pack') { throw };$rejected=$true
}
if (-not $rejected -or (Get-FileSha256 $packTarget) -ne $drift) { throw 'Dérive pack non préservée.' }
Copy-FileAtomic (Resolve-WorkspaceInput $runtime.paperdoll_pack.path -RequireExisting) $packTarget
$iniTarget = Resolve-ChildPath $fixture 'InfinityEngine-Enhancer.ini' -RequireExisting
[IO.File]::AppendAllText($iniTarget,"`n; user drift`n")
$drift = Get-FileSha256 $iniTarget
$rejected = $false
try { & $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null } catch {
    if ($_.Exception.Message -notmatch 'Dérive ini') { throw };$rejected=$true
}
if (-not $rejected -or (Get-FileSha256 $iniTarget) -ne $drift) { throw 'Dérive INI non préservée.' }
Copy-FileAtomic (Resolve-WorkspaceInput $runtime.ini.path -RequireExisting) $iniTarget
& $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null
foreach ($key in @('dll','ini')) {
    if ((Get-FileSha256 (Resolve-ChildPath $fixture ('InfinityEngine-Enhancer.'+$key) -RequireExisting)) -ne $runtime.baseline.$key) { throw 'Restauration non exacte.' }
}
if (Test-Path -LiteralPath $packTarget) { throw 'Paquet UI non retiré après restauration.' }
if ((Get-FileSha256 (Resolve-ChildPath $fixture $runtime.preserved_packs[0].target -RequireExisting)) -ne $runtime.preserved_packs[0].sha256) { throw 'Pack CHFF1INV altéré.' }
$newState = Join-Path $fixtureRoot 'state-drift'
[IO.File]::AppendAllText($iniTarget,"`n; baseline drift`n")
$before = Get-FileSha256 $iniTarget
$rejected = $false
try { & $installer -Mode Install -GameRoot $fixture -StateRoot $newState | Out-Null } catch {
    if ($_.Exception.Message -notmatch 'Dérive ini') { throw };$rejected=$true
}
if (-not $rejected -or (Get-FileSha256 $iniTarget) -ne $before -or (Test-Path -LiteralPath $newState)) { throw 'Baseline divergente non protégée.' }
Copy-FileAtomic (Join-Path $state 'previous-InfinityEngine-Enhancer.ini') $iniTarget
# Existing body override must block installation before any mutation.
$bodyOverride = Resolve-ChildPath $fixture 'override/CHFF2INV.BAM'
[IO.File]::WriteAllText($bodyOverride,'fixture foreign override')
$rejected = $false
try { & $installer -Mode Install -GameRoot $fixture -StateRoot $newState | Out-Null } catch {
    if ($_.Exception.Message -notmatch 'CHFF2INV ou UI.MENU override') { throw };$rejected=$true
}
if (-not $rejected -or (Test-Path -LiteralPath $newState)) { throw 'Override natif non protégé.' }
$result = [ordered]@{
    schema='bg2-p7-paperdoll-installer-verification-v1';status='pass';fixture_game=$fixture
    verified_at_utc=[DateTime]::UtcNow.ToString('o');install_verify_restore=$true;exact_baseline_restored=$true
    restore_rejects_pack_and_ini_drift=$true;install_rejects_baseline_drift=$true;install_rejects_body_override=$true
    preserved_chff1inv_pack_exact=$true;real_game_modified=$false;manifest_sha256=Get-FileSha256 $manifest;installer_sha256=Get-FileSha256 $installer
}
Write-JsonAtomic $proof $result
[pscustomobject]$result
