$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) {
    $workspace = Split-Path -Parent $workspace
    if (-not $workspace) { throw 'Workspace introuvable.' }
}
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$manifestRelative = 'pipeline/runtime/manifests/iee-sprite-p7-ui-probe-20261002-v1.json'
$manifestPath = Resolve-WorkspaceInput $manifestRelative
if (Test-Path -LiteralPath $manifestPath) { throw 'Manifeste déjà figé : utiliser un nouveau run.' }
$game = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$baseline = Read-JsonFile (Join-Path $workspace 'pipeline/runtime/manifests/iee-sprite-p4-box-x2-20261001-v1.json')
$liveDll = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$liveIni = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
if ((Get-FileSha256 $liveDll) -ne $baseline.dll.sha256) { throw 'Runtime BOX x2 attendu avant sonde P7.' }
$work = Join-Path $PSScriptRoot 'work'
if (Test-Path -LiteralPath $work) { throw 'Préparation déjà utilisée.' }
New-Item -ItemType Directory -Path $work | Out-Null
$candidateIni = Join-Path $work 'InfinityEngine-Enhancer.ini'
$ini = [IO.File]::ReadAllText($liveIni)
$ini = Set-IniValue $ini 'Shaders' 'EnablePaperdollUIProbe' 'true'
$ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpriteP4Probe' 'false'
Write-TextAtomic $candidateIni $ini
$dllRelative = 'build/sprite-p7-ui-probe-20261002-v1/cmake/Release/InfinityEngine-Enhancer.dll'
$dll = Resolve-WorkspaceInput $dllRelative -RequireExisting
$baseline.runtime_id = 'iee-sprite-p7-ui-probe-20261002-v1'
$baseline.dll = [pscustomobject]@{path=$dllRelative; sha256=Get-FileSha256 $dll; bytes=(Get-Item -LiteralPath $dll).Length}
$baseline | Add-Member -NotePropertyName ini -NotePropertyValue ([pscustomobject]@{
    path=[IO.Path]::GetRelativePath($workspace,$candidateIni).Replace('\','/'); sha256=Get-FileSha256 $candidateIni
})
$baseline.baseline = [pscustomobject]@{
    runtime_id='iee-sprite-p4-box-x2-20261001-v1'; scale=2; filter='Box'
    dll=Get-FileSha256 $liveDll; ini=Get-FileSha256 $liveIni
    catalog=Get-FileSha256 (Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting)
}
$baseline.capabilities | Add-Member -NotePropertyName paperdoll_ui_probe -NotePropertyValue ([pscustomobject]@{
    opt_in='EnablePaperdollUIProbe'; resref='CHFF1INV'; storage='P7_UI_* records in InfinityEngine-Enhancer.log'
    palette_limit=64; draw_limit=128; controls_input=$false; writes_render_state=$false; hd_paperdoll=$false
    requires='validated creature palette hook and D7 CVidCell owner/common hooks'
    measurements=@('realized 256-entry native palette','native CVidPalette source/ranges/type','sequence/cycle-slot',
        'pixel encoding','palette/draw caller RVA','draw position','logical backing size','source/render/clip rectangles','native shader tone')
})
$hashes = [ordered]@{}
foreach ($relative in @('src/iee/hooks.cpp','src/iee/core/config.cpp','src/iee/core/config.h','src/iee/game/build_manifest.cpp','src/iee/game/runtime_types_x64.h')) {
    $hashes[$relative] = Get-FileSha256 (Join-Path $workspace ('engine/InfinityEngine-Enhancer/source-patchee/' + $relative))
}
$baseline | Add-Member -NotePropertyName source_provenance -NotePropertyValue $hashes
Write-JsonAtomic $manifestPath $baseline
[pscustomobject]@{Status='prepared'; Manifest=$manifestPath; CandidateINI=$candidateIni; DLLSha256=$baseline.dll.sha256; Baseline=$baseline.baseline}
