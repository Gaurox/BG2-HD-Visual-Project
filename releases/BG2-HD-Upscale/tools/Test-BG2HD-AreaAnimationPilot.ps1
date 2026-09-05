[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
$candidatePath = Join-Path $release 'manifests\animation-release-candidates.json'
$candidateSchema = Join-Path $release 'schemas\animation-release-candidates.schema.json'
Require (Test-Json -Path $candidatePath -SchemaFile $candidateSchema) 'Schema du registre de candidats animation invalide.'
$candidates = Get-Content -LiteralPath $candidatePath -Raw -Encoding utf8 | ConvertFrom-Json
$candidateV2 = @($candidates.candidates | Where-Object { $_.area -eq 'AR0603' })
Require ($candidateV2.Count -eq 1) 'Le temoin animation v2 AR0603 doit etre declare une seule fois.'
Require ($candidateV2[0].approval_status -eq 'approved-for-release' -and [int]$candidateV2[0].registry_version -eq 2) 'Le temoin de retrocompatibilite AR0603 v2 doit etre explicitement approuve.'
Require ($candidateV2[0].renderer_contract -eq 'area-animation-per-area-registry-v2-timed-timeline') 'Contrat renderer AR0603 v2 inattendu.'
$candidateV3 = @($candidates.candidates | Where-Object { $_.area -eq 'AR0602' })
Require ($candidateV3.Count -eq 1) 'Le pilote animation AR0602 v3 doit etre declare une seule fois.'
Require ($candidateV3[0].approval_status -eq 'approved-for-release' -and [int]$candidateV3[0].registry_version -eq 3) 'Le pilote AR0602 v3 doit etre explicitement approuve.'
Require ($candidateV3[0].renderer_contract -eq 'area-animation-per-area-registry-v3-position-timed-timeline') 'Contrat renderer AR0602 v3 inattendu.'
$candidatePositionV3 = @($candidates.candidates | Where-Object { $_.area -eq 'AR0900' })
Require ($candidatePositionV3.Count -eq 1) 'Le pilote animation AR0900 v3 doit etre declare une seule fois.'
Require ($candidatePositionV3[0].approval_status -eq 'approved-for-release' -and [int]$candidatePositionV3[0].registry_version -eq 3) 'Le pilote AR0900 v3 doit etre explicitement approuve.'
Require ($candidatePositionV3[0].renderer_contract -eq 'area-animation-per-area-registry-v3-position-timed-timeline') 'Contrat renderer AR0900 v3 inattendu.'
$candidateOcclusion = @($candidates.candidates | Where-Object { $_.area -eq 'AR0516' })
Require ($candidateOcclusion.Count -eq 1 -and $null -ne $candidateOcclusion[0].occlusion_contract) 'Contrat occlusion AR0516 absent.'
Require ($candidateOcclusion[0].occlusion_contract.mode -eq 'native-wed-bridge-v1' -and [int]$candidateOcclusion[0].occlusion_contract.map_component_id -eq 1580) 'Contrat WED/bridge AR0516 invalide.'

$runtime = Get-Content -LiteralPath (Join-Path $release 'manifests\runtime-compatibility.json') -Raw -Encoding utf8 | ConvertFrom-Json
Require ($runtime.renderer.area_animation_runtime.status -eq 'integrated') 'Le renderer doit etre declare integre avec le pack AR0602 approuve.'
Require ($runtime.renderer.area_animation_runtime.payload_layout -eq 'iee-assets/areas/<AREA>') 'Layout renderer animation inattendu.'
Require ([int]$runtime.renderer.area_animation_runtime.registry_version -eq 3 -and (($runtime.renderer.area_animation_runtime.supported_registry_versions -join ',') -eq '1,2,3')) 'Compatibilite renderer v1/v2/v3 absente.'
Require ($runtime.owned_ini_keys.'core-steam'.Core.EnableAreaAnimationX4 -eq 'true') 'Le Core doit posseder l activation area-animation.'
Require ($runtime.owned_ini_keys.'core-steam'.Shaders.EnableNativeOcclusionBridge -eq 'true') 'Le Core doit posseder l activation du bridge d occlusion.'
$rendererCandidatePath = Join-Path $release 'manifests\renderer-animation-pilot.json'
Require (Test-Json -Path $rendererCandidatePath -SchemaFile (Join-Path $release 'schemas\renderer-bundle.schema.json')) 'Schema du renderer candidat animation invalide.'
$rendererCandidate = Get-Content -LiteralPath $rendererCandidatePath -Raw -Encoding utf8 | ConvertFrom-Json
Require ($rendererCandidate.bundle_id -eq 'iee-0.1.0-alpha.6' -and $rendererCandidate.status -eq 'rejected') 'Le pilote alpha.6 pre-occlusion doit rester rejete.'
$rendererCandidateRoot = Join-Path $release 'release-inputs\renderer\iee-0.1.0-alpha.6'
foreach ($file in @($rendererCandidate.files)) {
    $path = Join-Path $rendererCandidateRoot $file.path.Replace('/', '\')
    Require (Test-Path -LiteralPath $path -PathType Leaf) "Fichier renderer candidat absent : $($file.path)"
    Require ((Get-Item -LiteralPath $path).Length -eq [int64]$file.bytes) "Taille renderer candidat invalide : $($file.path)"
    Require ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -eq $file.sha256) "Hash renderer candidat invalide : $($file.path)"
}

$rendererSource = Join-Path $workspace 'engine\InfinityEngine-Enhancer\source-patchee'
$registrySource = Get-Content -LiteralPath (Join-Path $rendererSource 'src\iee\area_animation_x4_registry.cpp') -Raw -Encoding utf8
$hookSource = Get-Content -LiteralPath (Join-Path $rendererSource 'src\iee\hooks.cpp') -Raw -Encoding utf8
$sampleConfig = Get-Content -LiteralPath (Join-Path $rendererSource 'tools\InfinityEngine-Enhancer.sample.ini') -Raw -Encoding utf8
Require ($registrySource -match 'assetsDirectory / "areas"' -and $registrySource -match 'prepare_for_area') 'Le source renderer ne contient pas le chargement par zone.'
Require ($hookSource -match 'prepare_for_area\(game::resref_view') 'Le hook LoadArea ne recharge pas le pack animation.'
Require ($sampleConfig -match '(?m)^EnableAreaAnimationX4 = false\r?$') 'Le renderer source ne declare pas la cle de configuration animation.'
Require ($sampleConfig -match '(?m)^EnableNativeOcclusionBridge = false\r?$') 'Le renderer source ne declare pas la cle du bridge d occlusion.'
Require ($hookSource -match 'FXRenderClippingPolys' -and $hookSource -match 'enableNativeOcclusionBridge') 'Le source renderer ne contient pas le bridge d occlusion natif.'

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-animation-pilot-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    $content = Join-Path $tempRoot 'content.json'
    $components = Join-Path $tempRoot 'components.json'
    $tp2 = Join-Path $tempRoot 'bg2hd.tp2'

    & (Join-Path $release 'tools\New-BG2HD-ContentManifest.ps1') -WorkspaceRoot $workspace -OutputPath $content | Out-Null
    Require (Test-Json -Path $content -SchemaFile (Join-Path $release 'schemas\content.schema.json')) 'Schema du contenu pilote animation invalide.'
    & python (Join-Path $release 'tools\Validate-BG2HD-Assets.py') --workspace $workspace --content $content
    if ($LASTEXITCODE -ne 0) { throw 'Validation structurelle du pilote animation echouee.' }

    $contentObject = Get-Content -LiteralPath $content -Raw -Encoding utf8 | ConvertFrom-Json
    $animationEntriesV2 = @($contentObject.entries | Where-Object { $_.kind -eq 'area-animation' -and $_.area -eq 'AR0603' })
    $packV2 = Get-Content -LiteralPath (Join-Path $workspace ($candidateV2[0].source_pack.Replace('/', '\') + '\manifest.json')) -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedCountV2 = 2 + [int]$packV2.frame_count
    Require ($animationEntriesV2.Count -eq $expectedCountV2) "AR0603 v2 doit declarer $expectedCountV2 fichiers runtime, pas $($animationEntriesV2.Count)."
    Require ((@($animationEntriesV2 | Where-Object { $_.model -ne 'AreaAnimationRuntimeV2' -or $_.destination -notmatch '^iee-assets/areas/AR0603/[A-Za-z0-9._-]+$' }).Count) -eq 0) 'Contenu AR0603 v2 incoherent.'
    $animationEntriesV3 = @($contentObject.entries | Where-Object { $_.kind -eq 'area-animation' -and $_.area -eq 'AR0602' })
    $packV3 = Get-Content -LiteralPath (Join-Path $workspace ($candidateV3[0].source_pack.Replace('/', '\') + '\manifest.json')) -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedCountV3 = 2 + [int]$packV3.frame_count
    Require ($animationEntriesV3.Count -eq $expectedCountV3) "AR0602 doit declarer $expectedCountV3 fichiers runtime, pas $($animationEntriesV3.Count)."
    Require ((@($animationEntriesV3 | Where-Object { $_.model -ne 'AreaAnimationRuntimeV3' -or $_.destination -notmatch '^iee-assets/areas/AR0602/[A-Za-z0-9._-]+$' }).Count) -eq 0) 'Contenu AR0602 v3 incoherent.'
    $animationEntriesPositionV3 = @($contentObject.entries | Where-Object { $_.kind -eq 'area-animation' -and $_.area -eq 'AR0900' })
    $packPositionV3 = Get-Content -LiteralPath (Join-Path $workspace ($candidatePositionV3[0].source_pack.Replace('/', '\') + '\manifest.json')) -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedCountPositionV3 = 2 + [int]$packPositionV3.frame_count
    Require ($animationEntriesPositionV3.Count -eq $expectedCountPositionV3) "AR0900 doit declarer $expectedCountPositionV3 fichiers runtime, pas $($animationEntriesPositionV3.Count)."
    Require ((@($animationEntriesPositionV3 | Where-Object { $_.model -ne 'AreaAnimationRuntimeV3' -or $_.destination -notmatch '^iee-assets/areas/AR0900/[A-Za-z0-9._-]+$' }).Count) -eq 0) 'Contenu AR0900 v3 incoherent.'
    $wedOcclusionEntries = @($contentObject.entries | Where-Object { $_.destination -eq 'override/AR0516.WED' })
    Require ($wedOcclusionEntries.Count -eq 1) 'Correction WED AR0516 absente ou dupliquee.'
    Require ($wedOcclusionEntries[0].sha256 -eq '8A0AA3CA4C5D7A9BD42DDD0F55F6CA5ED57241A5F4B141C3CBE7D18D9AA2DB1A' -and [int64]$wedOcclusionEntries[0].bytes -eq 41502) 'Correction WED AR0516 non epinglee.'

    # Stage a minimal payload independently from the 4+ GiB maps payload. This
    # proves that the approved content type preserves the same hash-verified
    # staging contract before the full release payload is rebuilt.
    $pilotContent = Join-Path $tempRoot 'content-ar0603-v2-only.json'
    $pilotPayload = Join-Path $tempRoot 'payload-ar0603-v2-only'
    $pilotManifest = [ordered]@{
        '$schema' = '../schemas/content.schema.json'
        schema_version = 1
        generated_by = 'tools/Test-BG2HD-AreaAnimationPilot.ps1'
        entries = @($animationEntriesV2)
    }
    [IO.File]::WriteAllText($pilotContent, ($pilotManifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    & (Join-Path $release 'tools\Stage-BG2HDPayload.ps1') -WorkspaceRoot $workspace -ReleaseRoot $release -ContentPath $pilotContent -PayloadRoot $pilotPayload | Out-Null
    $staged = @(Get-ChildItem -LiteralPath $pilotPayload -File -Recurse)
    Require ($staged.Count -eq $expectedCountV2) "Staging AR0603 v2 incomplet : $($staged.Count)/$expectedCountV2"

    & (Join-Path $release 'tools\New-BG2HD-ComponentManifest.ps1') -ReleaseRoot $release -ContentPath $content -OutputPath $components | Out-Null
    $componentV2 = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { $_.id -eq 3004 })
    Require ($componentV2.Count -eq 1 -and $componentV2[0].label -eq 'animation-ar0603' -and $componentV2[0].depends_on -contains 0) 'Composant WeiDU AR0603 v2 invalide.'
    $componentV3 = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { $_.id -eq 3000 })
    Require ($componentV3.Count -eq 1 -and $componentV3[0].label -eq 'animation-ar0602' -and $componentV3[0].depends_on -contains 0) 'Composant WeiDU AR0602 v3 invalide.'
    $componentPositionV3 = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { $_.id -eq 3001 })
    Require ($componentPositionV3.Count -eq 1 -and $componentPositionV3[0].label -eq 'animation-ar0900' -and $componentPositionV3[0].depends_on -contains 0) 'Composant WeiDU AR0900 v3 invalide.'
    $componentOcclusion = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { $_.id -eq 3002 })
    Require ($componentOcclusion.Count -eq 1 -and $componentOcclusion[0].depends_on -contains 0 -and $componentOcclusion[0].depends_on -contains 1580) 'Dependance WED AR0516 absente du composant animation.'

    & (Join-Path $release 'tools\Generate-BG2HD-Tp2.ps1') -ReleaseRoot $release -ContentPath $content -ComponentsPath $components -OutputPath $tp2 | Out-Null
    $tp2Raw = Get-Content -LiteralPath $tp2 -Raw -Encoding utf8
    Require ($tp2Raw -match '(?m)^BEGIN ~AR0603 area animations \(x4\)~\r?$' -and $tp2Raw -match '(?m)^  DESIGNATED 3004\r?$') 'Composant WeiDU AR0603 v2 absent.'
    Require ($tp2Raw -match '(?m)^BEGIN ~AR0602 area animations \(x4\)~\r?$' -and $tp2Raw -match '(?m)^  DESIGNATED 3000\r?$') 'Composant WeiDU AR0602 v3 absent.'
    Require ($tp2Raw -match '(?m)^BEGIN ~AR0900 area animations \(x4\)~\r?$' -and $tp2Raw -match '(?m)^  DESIGNATED 3001\r?$') 'Composant WeiDU AR0900 v3 absent.'
    Require ($tp2Raw -match '(?m)^  REQUIRE_COMPONENT ~bg2hd/bg2hd\.tp2~ ~0~ @14\r?$') 'Dependance Core animation absente.'
    foreach ($directory in @('iee-assets', 'iee-assets/areas', 'iee-assets/areas/AR0603')) {
        Require ($tp2Raw -match ('(?m)^  MKDIR ~' + [regex]::Escape($directory) + '~\r?$')) "MKDIR WeiDU absent : $directory"
    }
    $copies = [regex]::Matches($tp2Raw, '(?m)^  COPY_LARGE ~bg2hd/payload/animation-ar0603/[^~]+~ ~iee-assets/areas/AR0603/[^~]+~\r?$')
    Require ($copies.Count -eq $expectedCountV2) "COPY_LARGE WeiDU AR0603 v2 incomplet : $($copies.Count)/$expectedCountV2"

    Write-Output "Area-animation compatibility pilots passed: AR0603 v2 ($expectedCountV2 files), AR0602 v3 ($expectedCountV3 files), and AR0900 v3 ($expectedCountPositionV3 files)."
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
