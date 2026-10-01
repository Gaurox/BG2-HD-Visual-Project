$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) {
    $workspace = Split-Path -Parent $workspace
    if (-not $workspace) { throw 'Workspace introuvable.' }
}
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$manifestPath = Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-sprite-p7-chff1inv-q3m-20261002-v1.json'
if (Test-Path -LiteralPath $manifestPath) { throw 'Manifeste figé : nouveau run requis.' }
$game = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$runtime = Read-JsonFile (Join-Path $workspace 'pipeline/runtime/manifests/iee-sprite-p7-ui-probe-20261002-v2.json')
$liveDll = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$liveIni = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
if ((Get-FileSha256 $liveDll) -ne $runtime.dll.sha256 -or (Get-FileSha256 $liveIni) -ne $runtime.ini.sha256) {
    throw 'Sonde P7 v2 attendue comme baseline.'
}
$pack = Read-JsonFile (Join-Path $PSScriptRoot 'pack.json')
$candidateIni = Join-Path $PSScriptRoot 'work/InfinityEngine-Enhancer.ini'
$ini = Set-IniValue ([IO.File]::ReadAllText($liveIni)) 'Shaders' 'EnablePaperdollQ3mTest' 'true'
Write-TextAtomic $candidateIni $ini
$runtime.runtime_id = 'iee-sprite-p7-chff1inv-q3m-20261002-v1'
$dllRelative = 'build/sprite-p7-chff1inv-q3m-20261002-v1/cmake/Release/InfinityEngine-Enhancer.dll'
$dll = Resolve-WorkspaceInput $dllRelative -RequireExisting
$runtime.dll = [pscustomobject]@{path=$dllRelative;sha256=Get-FileSha256 $dll;bytes=(Get-Item -LiteralPath $dll).Length}
$runtime.ini = [pscustomobject]@{path=[IO.Path]::GetRelativePath($workspace,$candidateIni).Replace('\','/');sha256=Get-FileSha256 $candidateIni}
$runtime.baseline = [pscustomobject]@{runtime_id='iee-sprite-p7-ui-probe-20261002-v2';scale=2;filter='Box'
    dll=Get-FileSha256 $liveDll;ini=Get-FileSha256 $liveIni;pack=$null
    catalog=Get-FileSha256 (Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting)}
$runtime | Add-Member -NotePropertyName paperdoll_pack -NotePropertyValue ([pscustomobject]@{
    path=$pack.pack.path;sha256=$pack.pack.sha256;bytes=$pack.pack.bytes
    target='iee-assets/paperdolls/CHFF1INV-Q3m-X2.registry';source_bam_sha256=$pack.source_sha256})
$runtime.capabilities | Add-Member -NotePropertyName paperdoll_q3m_test -NotePropertyValue ([pscustomobject]@{
    opt_in='EnablePaperdollQ3mTest';resref='CHFF1INV';scale=2;parts=2;profile=1;decode_rule=1
    ui_sampler='Nearest';ui_shader='native Bitmap (6)';dynamic_native_palette=$true;native_geometry=$true
    queued_palette_updates='native DrawFlushGl before replacing either of two backings'
    flags='0x4005';cycle=@(0,0,1,1);world_filter='Box';controls_pc_input=$false;ingame_qa=$false})
$hashes = [ordered]@{}
foreach ($relative in @('src/iee/hooks.cpp','src/iee/paperdoll_q3m.cpp','src/iee/paperdoll_q3m.h','src/iee/core/config.cpp',
    'src/iee/core/config.h','src/iee/dll_main.cpp','src/iee/game/build_manifest.cpp','src/iee/game/game_types.h')) {
    $hashes[$relative] = Get-FileSha256 (Join-Path $workspace ('engine/InfinityEngine-Enhancer/source-patchee/'+$relative))
}
$runtime.source_provenance = [pscustomobject]$hashes
Write-JsonAtomic $manifestPath $runtime
[pscustomobject]@{Status='prepared';Manifest=$manifestPath;DLLSha256=$runtime.dll.sha256;PackSha256=$runtime.paperdoll_pack.sha256}
