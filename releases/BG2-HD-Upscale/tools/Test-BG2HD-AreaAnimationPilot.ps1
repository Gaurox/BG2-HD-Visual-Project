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
$candidatePath = Join-Path $release 'manifests\animation-release-candidates.json'
$candidateSchema = Join-Path $release 'schemas\animation-release-candidates.schema.json'
Require (Test-Json -Path $candidatePath -SchemaFile $candidateSchema) 'Schema du registre de candidats animation invalide.'
$candidates = Get-Content -LiteralPath $candidatePath -Raw -Encoding utf8 | ConvertFrom-Json
$candidate = @($candidates.candidates | Where-Object { $_.area -eq 'AR0602' })
Require ($candidate.Count -eq 1) 'Le pilote animation AR0602 doit etre declare une seule fois.'
Require ($candidate[0].approval_status -eq 'approved-for-release') 'Le pilote AR0602 doit etre explicitement approuve avant son integration.'
Require ([int]$candidate[0].registry_version -eq 2) 'Le pilote AR0602 doit rester le temoin de compatibilite v2.'
Require ($candidate[0].renderer_contract -eq 'area-animation-per-area-registry-v2-timed-timeline') 'Contrat renderer AR0602 inattendu.'
$candidateV3 = @($candidates.candidates | Where-Object { $_.area -eq 'AR0900' })
Require ($candidateV3.Count -eq 1) 'Le pilote animation AR0900 doit etre declare une seule fois.'
Require ($candidateV3[0].approval_status -eq 'approved-for-release' -and [int]$candidateV3[0].registry_version -eq 3) 'Le pilote AR0900 v3 doit etre explicitement approuve.'
Require ($candidateV3[0].renderer_contract -eq 'area-animation-per-area-registry-v3-position-timed-timeline') 'Contrat renderer AR0900 inattendu.'

$runtime = Get-Content -LiteralPath (Join-Path $release 'manifests\runtime-compatibility.json') -Raw -Encoding utf8 | ConvertFrom-Json
Require ($runtime.renderer.area_animation_runtime.status -eq 'integrated') 'Le renderer doit etre declare integre avec le pack AR0602 approuve.'
Require ($runtime.renderer.area_animation_runtime.payload_layout -eq 'iee-assets/areas/<AREA>') 'Layout renderer animation inattendu.'
Require ([int]$runtime.renderer.area_animation_runtime.registry_version -eq 3 -and (($runtime.renderer.area_animation_runtime.supported_registry_versions -join ',') -eq '1,2,3')) 'Compatibilite renderer v1/v2/v3 absente.'
Require ($runtime.owned_ini_keys.'core-steam'.Core.EnableAreaAnimationX4 -eq 'true') 'Le Core doit posseder l activation area-animation.'
$rendererCandidatePath = Join-Path $release 'manifests\renderer-animation-pilot.json'
Require (Test-Json -Path $rendererCandidatePath -SchemaFile (Join-Path $release 'schemas\renderer-bundle.schema.json')) 'Schema du renderer candidat animation invalide.'
$rendererCandidate = Get-Content -LiteralPath $rendererCandidatePath -Raw -Encoding utf8 | ConvertFrom-Json
Require ($rendererCandidate.bundle_id -eq 'iee-0.1.0-alpha.5' -and $rendererCandidate.status -eq 'frozen-awaiting-clean-game-validation') 'Etat du renderer candidat animation inattendu.'
$rendererCandidateRoot = Join-Path $release 'release-inputs\renderer\iee-0.1.0-alpha.5'
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
    $animationEntries = @($contentObject.entries | Where-Object { $_.kind -eq 'area-animation' -and $_.area -eq 'AR0602' })
    $pack = Get-Content -LiteralPath (Join-Path $workspace ($candidate[0].source_pack.Replace('/', '\') + '\manifest.json')) -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedCount = 2 + [int]$pack.frame_count
    Require ($animationEntries.Count -eq $expectedCount) "AR0602 doit declarer $expectedCount fichiers runtime, pas $($animationEntries.Count)."
    Require ((@($animationEntries.destination | Where-Object { $_ -notmatch '^iee-assets/areas/AR0602/[A-Za-z0-9._-]+$' }).Count) -eq 0) 'Destination AR0602 hors iee-assets/areas/AR0602.'
    $animationEntriesV3 = @($contentObject.entries | Where-Object { $_.kind -eq 'area-animation' -and $_.area -eq 'AR0900' })
    $packV3 = Get-Content -LiteralPath (Join-Path $workspace ($candidateV3[0].source_pack.Replace('/', '\') + '\manifest.json')) -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedCountV3 = 2 + [int]$packV3.frame_count
    Require ($animationEntriesV3.Count -eq $expectedCountV3) "AR0900 doit declarer $expectedCountV3 fichiers runtime, pas $($animationEntriesV3.Count)."
    Require ((@($animationEntriesV3 | Where-Object { $_.model -ne 'AreaAnimationRuntimeV3' -or $_.destination -notmatch '^iee-assets/areas/AR0900/[A-Za-z0-9._-]+$' }).Count) -eq 0) 'Contenu AR0900 v3 incoherent.'

    # Stage a minimal payload independently from the 4+ GiB maps payload. This
    # proves that the approved content type preserves the same hash-verified
    # staging contract before the full release payload is rebuilt.
    $pilotContent = Join-Path $tempRoot 'content-ar0602-only.json'
    $pilotPayload = Join-Path $tempRoot 'payload-ar0602-only'
    $pilotManifest = [ordered]@{
        '$schema' = '../schemas/content.schema.json'
        schema_version = 1
        generated_by = 'tools/Test-BG2HD-AreaAnimationPilot.ps1'
        entries = @($animationEntries)
    }
    [IO.File]::WriteAllText($pilotContent, ($pilotManifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    & (Join-Path $release 'tools\Stage-BG2HDPayload.ps1') -WorkspaceRoot $workspace -ReleaseRoot $release -ContentPath $pilotContent -PayloadRoot $pilotPayload | Out-Null
    $staged = @(Get-ChildItem -LiteralPath $pilotPayload -File -Recurse)
    Require ($staged.Count -eq $expectedCount) "Staging AR0602 incomplet : $($staged.Count)/$expectedCount"

    & (Join-Path $release 'tools\New-BG2HD-ComponentManifest.ps1') -ReleaseRoot $release -ContentPath $content -OutputPath $components | Out-Null
    $component = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { $_.id -eq 3000 })
    Require ($component.Count -eq 1 -and $component[0].label -eq 'animation-ar0602' -and $component[0].depends_on -contains 0) 'Composant WeiDU AR0602 invalide.'
    $componentV3 = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { $_.id -eq 3001 })
    Require ($componentV3.Count -eq 1 -and $componentV3[0].label -eq 'animation-ar0900' -and $componentV3[0].depends_on -contains 0) 'Composant WeiDU AR0900 invalide.'

    & (Join-Path $release 'tools\Generate-BG2HD-Tp2.ps1') -ReleaseRoot $release -ContentPath $content -ComponentsPath $components -OutputPath $tp2 | Out-Null
    $tp2Raw = Get-Content -LiteralPath $tp2 -Raw -Encoding utf8
    Require ($tp2Raw -match '(?m)^BEGIN ~AR0602 area animations \(x4\)~\r?$') 'BEGIN WeiDU AR0602 absent.'
    Require ($tp2Raw -match '(?m)^  DESIGNATED 3000\r?$') 'DESIGNATED WeiDU AR0602 absent.'
    Require ($tp2Raw -match '(?m)^BEGIN ~AR0900 area animations \(x4\)~\r?$' -and $tp2Raw -match '(?m)^  DESIGNATED 3001\r?$') 'Composant WeiDU AR0900 v3 absent.'
    Require ($tp2Raw -match '(?m)^  REQUIRE_COMPONENT ~bg2hd/bg2hd\.tp2~ ~0~ @14\r?$') 'Dependance Core AR0602 absente.'
    foreach ($directory in @('iee-assets', 'iee-assets/areas', 'iee-assets/areas/AR0602')) {
        Require ($tp2Raw -match ('(?m)^  MKDIR ~' + [regex]::Escape($directory) + '~\r?$')) "MKDIR WeiDU absent : $directory"
    }
    $copies = [regex]::Matches($tp2Raw, '(?m)^  COPY_LARGE ~bg2hd/payload/animation-ar0602/[^~]+~ ~iee-assets/areas/AR0602/[^~]+~\r?$')
    Require ($copies.Count -eq $expectedCount) "COPY_LARGE WeiDU AR0602 incomplet : $($copies.Count)/$expectedCount"

    Write-Output "Area-animation compatibility pilots passed: AR0602 v2 ($expectedCount files) and AR0900 v3 ($expectedCountV3 files)."
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
