$ErrorActionPreference = 'Stop'
$workspace=$PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) { $workspace=Split-Path -Parent $workspace }
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$proof=Join-Path $PSScriptRoot 'installer-verification.json'
if (Test-Path -LiteralPath $proof) { throw 'Proof already saved.' }
$game=Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$manifest=Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-sprite-p7-full-ui-q3m-20261002-v1.json' -RequireExisting
$runtime=Read-JsonFile $manifest
$fixtureRoot=Join-Path $PSScriptRoot ('work/fixtures/'+[guid]::NewGuid().ToString('N'))
$fixture=Join-Path $fixtureRoot 'game'
$names=@('BaldurReal.exe','InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','iee-assets/creature-sprites/CreatureSprites-XN.catalog') + @($runtime.shaders.target) + @($runtime.preserved_packs.target)
foreach ($name in $names) { Copy-FileAtomic (Resolve-ChildPath $game $name -RequireExisting) (Resolve-ChildPath $fixture $name) }
$installer=Join-Path $PSScriptRoot 'install.ps1'
$state=Join-Path $fixtureRoot 'state'
& $installer -Mode Install -GameRoot $fixture -StateRoot $state | Out-Null
& $installer -Mode Verify -GameRoot $fixture -StateRoot $state | Out-Null
$pack=$runtime.paperdoll_packs[0]
$target=Resolve-ChildPath $fixture $pack.target
[IO.File]::AppendAllText($target,'drift')
$drift=Get-FileSha256 $target
$rejected=$false
try { & $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null } catch { if ($_.Exception.Message -notmatch 'Target drift') { throw }; $rejected=$true }
if (-not $rejected -or (Get-FileSha256 $target) -ne $drift) { throw 'Pack drift not preserved.' }
Copy-FileAtomic (Resolve-WorkspaceInput $pack.path) $target
$ini=Resolve-ChildPath $fixture 'InfinityEngine-Enhancer.ini'
[IO.File]::AppendAllText($ini,"`n; user drift`n")
$drift=Get-FileSha256 $ini;$rejected=$false
try { & $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null } catch { if ($_.Exception.Message -notmatch 'Target drift: ini') { throw }; $rejected=$true }
if (-not $rejected -or (Get-FileSha256 $ini) -ne $drift) { throw 'INI drift not preserved.' }
Copy-FileAtomic (Resolve-WorkspaceInput $runtime.ini.path) $ini
$preserved=$runtime.preserved_packs[0];$preservedTarget=Resolve-ChildPath $fixture $preserved.target
[IO.File]::AppendAllText($preservedTarget,'drift');$drift=Get-FileSha256 $preservedTarget;$rejected=$false
try { & $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null } catch { if ($_.Exception.Message -notmatch 'Preserved pack differs') { throw }; $rejected=$true }
if (-not $rejected -or (Get-FileSha256 $preservedTarget) -ne $drift) { throw 'Accepted-body drift not preserved.' }
Copy-FileAtomic (Resolve-ChildPath $game $preserved.target) $preservedTarget
& $installer -Mode Restore -GameRoot $fixture -StateRoot $state | Out-Null
foreach ($name in $names) { if ((Get-FileSha256 (Resolve-ChildPath $fixture $name)) -ne (Get-FileSha256 (Resolve-ChildPath $game $name))) { throw "Baseline restore differs: $name" } }
foreach ($pack in $runtime.paperdoll_packs) { if (Test-Path -LiteralPath (Resolve-ChildPath $fixture $pack.target)) { throw 'New pack survived restore.' } }
$nextState=Join-Path $fixtureRoot 'blocked-state'
[IO.File]::AppendAllText($ini,"`n; baseline drift`n");$drift=Get-FileSha256 $ini;$rejected=$false
try { & $installer -Mode Install -GameRoot $fixture -StateRoot $nextState | Out-Null } catch { if ($_.Exception.Message -notmatch 'Target drift: ini') { throw }; $rejected=$true }
if (-not $rejected -or (Get-FileSha256 $ini) -ne $drift -or (Test-Path -LiteralPath $nextState)) { throw 'Baseline drift not protected.' }
Copy-FileAtomic (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini') $ini
[IO.File]::WriteAllText((Resolve-ChildPath $fixture 'override/WPNAXINV.BAM'),'foreign override');$rejected=$false
try { & $installer -Mode Install -GameRoot $fixture -StateRoot $nextState | Out-Null } catch { if ($_.Exception.Message -notmatch 'Native UI override differs') { throw }; $rejected=$true }
if (-not $rejected -or (Test-Path -LiteralPath $nextState)) { throw 'Equipment override not protected.' }
$result=[ordered]@{schema='bg2-p7-full-ui-installer-verification-v1';status='pass';verified_at_utc=[DateTime]::UtcNow.ToString('o');install_verify_restore=$true;new_packs=79;preserved_packs=2;exact_baseline_restored=$true;restore_rejects_pack_ini_and_preserved_drift=$true;install_rejects_baseline_and_native_override_drift=$true;real_game_modified=$false;manifest_sha256=Get-FileSha256 $manifest;installer_sha256=Get-FileSha256 $installer}
Write-JsonAtomic $proof $result
[pscustomobject]$result
