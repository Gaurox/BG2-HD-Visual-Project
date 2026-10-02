$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) { $workspace = Split-Path -Parent $workspace }
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$game = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$manifest = Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-sprite-p7-full-ui-q3m-20261002-v1.json'
if (Test-Path -LiteralPath $manifest) { throw 'Manifest already prepared; use a fresh run.' }
$baseline = Read-JsonFile (Join-Path $workspace 'pipeline/runtime/manifests/iee-sprite-p7-chff2inv-q3m-20261002-v1.json')
$production = Read-JsonFile (Join-Path $PSScriptRoot 'production.json')
$preserved = @($baseline.preserved_packs) + @($baseline.paperdoll_pack)
foreach ($name in @('dll','ini')) {
    if ((Get-FileSha256 (Resolve-ChildPath $game ('InfinityEngine-Enhancer.'+$name) -RequireExisting)) -ne $baseline.$name.sha256) { throw "Baseline $name differs." }
}
foreach ($pack in $preserved) {
    if ((Get-FileSha256 (Resolve-ChildPath $game $pack.target -RequireExisting)) -ne $pack.sha256) { throw 'Validated body pack differs.' }
}
$candidateIni = Join-Path $PSScriptRoot 'work/InfinityEngine-Enhancer.ini'
Copy-FileAtomic (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini') $candidateIni
$dllRelative = 'build/sprite-p7-full-ui-q3m-20261002-v1/cmake/Release/InfinityEngine-Enhancer.dll'
$dll = Resolve-WorkspaceInput $dllRelative -RequireExisting
$packs = @()
foreach ($resource in $production.resources) {
    $target = 'iee-assets/paperdolls/'+$resource.resref+'-Q3m-X2.registry'
    $existing = @($preserved | Where-Object target -eq $target)
    if ($existing.Count) {
        if ($resource.pack.sha256 -ne $existing[0].sha256) { throw 'Accepted body bytes changed.' }
    } else {
        $packs += [pscustomobject]@{path=$resource.pack.path;sha256=$resource.pack.sha256;bytes=$resource.pack.bytes;target=$target;resref=$resource.resref;source_bam_sha256=$resource.source_sha256}
    }
}
if ($packs.Count -ne 79) { throw 'Expected 79 new appearances.' }
$runtime = $baseline
$runtime.runtime_id = 'iee-sprite-p7-full-ui-q3m-20261002-v1'
$runtime.dll = [pscustomobject]@{path=$dllRelative;sha256=Get-FileSha256 $dll;bytes=(Get-Item -LiteralPath $dll).Length}
$runtime.ini = [pscustomobject]@{path=[IO.Path]::GetRelativePath($workspace,$candidateIni).Replace('\','/');sha256=Get-FileSha256 $candidateIni}
$runtime.baseline = [pscustomobject]@{runtime_id='iee-sprite-p7-chff2inv-q3m-20261002-v1';scale=2;filter='Box';dll=Get-FileSha256 (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll');ini=Get-FileSha256 $candidateIni;catalog=Get-FileSha256 (Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog')}
$runtime.PSObject.Properties.Remove('paperdoll_pack')
$runtime.preserved_packs = $preserved
$runtime | Add-Member -NotePropertyName paperdoll_packs -NotePropertyValue $packs
$runtime.capabilities.paperdoll_q3m_test = [pscustomobject]@{opt_in='EnablePaperdollQ3mTest';resrefs=@($production.resources.resref);scale=2;native_frames=163;profile=1;decode_rule=1;ui_sampler='Nearest';ui_shader='native Bitmap (6)';texture_pool=32;queued_updates='native DrawFlushGl before upload or pool eviction';dynamic_native_palette=$true;native_geometry=$true;controls_pc_input=$false;ingame_qa=$false}
$hashes = [ordered]@{}
foreach ($relative in @('src/iee/hooks.cpp','src/iee/paperdoll_q3m.cpp','src/iee/paperdoll_q3m.h','src/iee/paperdoll_q3m_scope.h','src/iee/core/config.cpp','src/iee/core/config.h','src/iee/dll_main.cpp','src/iee/game/build_manifest.cpp','src/iee/game/game_types.h')) {
    $hashes[$relative] = Get-FileSha256 (Join-Path $workspace ('engine/InfinityEngine-Enhancer/source-patchee/'+$relative))
}
$runtime.source_provenance = [pscustomobject]$hashes
Write-JsonAtomic $manifest $runtime
[pscustomobject]@{Status='prepared';Manifest=$manifest;NewPacks=$packs.Count;PreservedPacks=$preserved.Count;DLLSha256=$runtime.dll.sha256}
