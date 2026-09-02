[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$WeiDUExecutable
)

$ErrorActionPreference = 'Stop'

$workspace = (Resolve-Path -LiteralPath (Join-Path $ReleaseRoot '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Test-QAEvidenceHash([string]$Workspace, [string]$RelativePath, [string]$ExpectedHash) {
    $current = Join-Path $Workspace ($RelativePath.Replace('/', '\'))
    if ((Test-Path -LiteralPath $current -PathType Leaf) -and
        (Get-FileHash -LiteralPath $current -Algorithm SHA256).Hash -eq $ExpectedHash) {
        return $true
    }
    $adapter = Join-Path $Workspace 'pipeline\scripts\verify_historical_git_evidence.py'
    & python $adapter --path $RelativePath --sha256 $ExpectedHash --quiet
    return $LASTEXITCODE -eq 0
}

function Get-AnimationManifestResrefs([object]$Manifest) {
    $values = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($key in @('asset', 'resref', 'bam_resref')) {
        $value = [string]$Manifest.$key
        if ($value -match '^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$') { [void]$values.Add($value.ToUpperInvariant()) }
    }
    foreach ($key in @('resources', 'timed_resources', 'resrefs', 'targets', 'requested_resrefs', 'resolved_resrefs')) {
        foreach ($item in @($Manifest.$key)) {
            if ($item -is [string]) {
                if ($item -match '^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$') { [void]$values.Add($item.ToUpperInvariant()) }
                continue
            }
            foreach ($itemKey in @('asset', 'resref', 'bam_resref', 'resource_resref')) {
                $itemValue = [string]$item.$itemKey
                if ($itemValue -match '^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$') { [void]$values.Add($itemValue.ToUpperInvariant()) }
            }
        }
    }
    if ($null -ne $Manifest.request) {
        foreach ($key in @('resref', 'resrefs', 'targets', 'requested_resrefs', 'resolved_resrefs')) {
            foreach ($item in @($Manifest.request.$key)) {
                $value = if ($item -is [string]) { $item } else { [string]$item.resref }
                if ($value -match '^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$') { [void]$values.Add($value.ToUpperInvariant()) }
            }
        }
    }
    return @($values | Sort-Object)
}

$schemas = @(
    @('release.json', 'release.schema.json'),
    @('components.json', 'components.schema.json'),
    @('runtime-compatibility.json', 'runtime-compatibility.schema.json'),
    @('dependency-bootstrap.json', 'dependency-bootstrap.schema.json'),
    @('content.json', 'content.schema.json'),
    @('animation-release-candidates.json', 'animation-release-candidates.schema.json'),
    @('overlay-sources.json', 'overlay-sources.schema.json'),
    @('licenses-and-exclusions.json', 'licenses-and-exclusions.schema.json'),
    @('renderer-bundle.json', 'renderer-bundle.schema.json'),
    @('renderer-animation-pilot.json', 'renderer-bundle.schema.json')
)
foreach ($pair in $schemas) {
    $manifest = Join-Path $ReleaseRoot (Join-Path 'manifests' $pair[0])
    $schema = Join-Path $ReleaseRoot (Join-Path 'schemas' $pair[1])
    Require (Test-Json -Path $manifest -SchemaFile $schema) "Schema invalide : $($pair[0])"
}

$animationQaSchema = Join-Path $ReleaseRoot 'schemas\animation-qa-approval.schema.json'
$animationDecisionSchema = Join-Path $workspace 'animations\schemas\animation-qa-decision.schema.json'
$animationCandidatesPath = Join-Path $ReleaseRoot 'manifests\animation-release-candidates.json'
$animationCandidates = Get-Content -LiteralPath $animationCandidatesPath -Raw -Encoding utf8 | ConvertFrom-Json
$animationCandidateAreas = @($animationCandidates.candidates | ForEach-Object { [string]$_.area })
$animationComponentIds = @($animationCandidates.candidates | ForEach-Object { [int]$_.component_id })
Require ($animationCandidateAreas.Count -eq @($animationCandidateAreas | Sort-Object -Unique).Count) 'Zones dupliquees dans le registre de candidats animation.'
Require ($animationComponentIds.Count -eq @($animationComponentIds | Sort-Object -Unique).Count) 'Component_id duplique dans le registre de candidats animation.'
foreach ($candidate in @($animationCandidates.candidates)) {
    $qaPath = [IO.Path]::GetFullPath((Join-Path $workspace ([string]$candidate.qa_approval).Replace('/', '\')))
    $relativeQaPath = [IO.Path]::GetRelativePath($workspace, $qaPath).Replace('\', '/')
    Require ($relativeQaPath -ceq [string]$candidate.qa_approval) "Chemin d'approbation QA animation non canonique : $($candidate.area)"
    Require ($relativeQaPath.StartsWith("releases/BG2-HD-Upscale/manifests/animation-qa-approvals/$($candidate.area)/", [StringComparison]::Ordinal)) "Approbation QA rangee sous une autre zone : $relativeQaPath"
    Require (Test-Path -LiteralPath $qaPath -PathType Leaf) "Approbation QA animation absente : $($candidate.area)"
    Require (Test-Json -Path $qaPath -SchemaFile $animationQaSchema) "Schema approbation QA animation invalide : $($candidate.area)"
    Require ((Get-FileHash -LiteralPath $qaPath -Algorithm SHA256).Hash -eq [string]$candidate.qa_approval_sha256) "Hash approbation QA animation invalide : $($candidate.area)"
    $qaApproval = Get-Content -LiteralPath $qaPath -Raw -Encoding utf8 | ConvertFrom-Json
    Require ([string]$qaApproval.area -eq [string]$candidate.area -and [string]$qaApproval.source_pack -eq [string]$candidate.source_pack) "Zone ou pack QA animation incoherent : $($candidate.area)"
    Require ([string]$qaApproval.pack_manifest_sha256 -eq [string]$candidate.pack_manifest_sha256 -and [string]$qaApproval.registry_sha256 -eq [string]$candidate.registry_sha256) "Hashes QA animation incoherents : $($candidate.area)"
    Require ([string]$qaApproval.registry -eq [string]$candidate.registry -and [int]$qaApproval.registry_version -eq [int]$candidate.registry_version) "Registre/version QA animation incoherent : $($candidate.area)"
    Require (-not (Compare-Object @($candidate.required_resrefs | Sort-Object -Unique) @($qaApproval.required_resrefs | Sort-Object -Unique))) "Couverture QA animation incoherente : $($candidate.area)"
    $releaseVerifier = Join-Path $workspace 'pipeline\scripts\verify_animation_release_candidate.py'
    Require (Test-Path -LiteralPath $releaseVerifier -PathType Leaf) 'Validateur de release animation absent.'
    $releaseArguments = @(
            $releaseVerifier,
            '--workspace-root', $workspace,
            '--animation-candidates-path', $animationCandidatesPath,
            '--area', [string]$candidate.area
    )
    if ([string]$candidate.approval_status -eq 'validated-awaiting-manifest-approval') {
        $releaseArguments += '--allow-pending'
    }
    & python @releaseArguments
    Require ($LASTEXITCODE -eq 0) "Release animation invalide : $($candidate.area)"
    if ([int]$qaApproval.schema_version -in @(1, 3)) {
        continue
    }
    $qaDecisionRuns = @{}
    foreach ($evidence in @($qaApproval.evidence)) {
        $evidencePath = [IO.Path]::GetFullPath((Join-Path $workspace ([string]$evidence.path).Replace('/', '\')))
        $relativeEvidence = [IO.Path]::GetRelativePath($workspace, $evidencePath).Replace('\', '/')
        Require ($relativeEvidence -notmatch '(^|/)\.\.(/|$)') "Preuve QA animation hors workspace : $($evidence.path)"
        Require (Test-Path -LiteralPath $evidencePath -PathType Leaf) "Preuve QA animation absente : $relativeEvidence"
        if ([int]$qaApproval.schema_version -eq 2) {
            Require ((Get-FileHash -LiteralPath $evidencePath -Algorithm SHA256).Hash -eq [string]$evidence.sha256) "Hash courant de decision ingame invalide : $relativeEvidence"
            Require ([string]$evidence.kind -eq 'ingame-qa-decision') "Type de preuve QA v2 invalide : $relativeEvidence"
            Require (Test-Json -Path $evidencePath -SchemaFile $animationDecisionSchema) "Schema de decision ingame invalide : $relativeEvidence"
            $decision = Get-Content -LiteralPath $evidencePath -Raw -Encoding utf8 | ConvertFrom-Json
            $acceptedResrefs = @($evidence.accepted_resrefs | Sort-Object -Unique)
            Require ($acceptedResrefs.Count -eq 1 -and [string]$decision.resref -eq [string]$acceptedResrefs[0]) "Resref de decision ingame incoherent : $relativeEvidence"
            Require ([string]$decision.result_kind -eq 'x4') "Decision ingame non x4 interdite en release : $relativeEvidence"
            Require ($decision.status -eq 'accepted' -and $decision.decision_origin -eq 'explicit-user-ingame-qa') "Decision ingame non acceptee : $relativeEvidence"
            $decisionResref = ([string]$decision.resref).ToUpperInvariant()
            $expectedDecisionPath = "animations/index/qa-decisions/$decisionResref/$($decision.decision_id).json"
            Require ($relativeEvidence -ceq $expectedDecisionPath) "Decision ingame rangee sous un autre asset ou identifiant : $relativeEvidence"
            Require (@($decision.tested_areas) -contains [string]$candidate.area) "Zone absente de la decision ingame : $relativeEvidence"
            $decisionArea = @($decision.source_pack.areas | Where-Object { [string]$_.area -eq [string]$candidate.area })
            Require ($decisionArea.Count -eq 1 -and [string]$decisionArea[0].path -eq [string]$candidate.source_pack) "Pack de decision ingame incoherent : $relativeEvidence"
            Require ([string]$decisionArea[0].manifest_sha256 -eq [string]$candidate.pack_manifest_sha256 -and [string]$decisionArea[0].registry_sha256 -eq [string]$candidate.registry_sha256) "Hashes de decision ingame incoherents : $relativeEvidence"
            $decisionRunPath = [string]$decision.final_run.path
            $decisionRunDirectory = [IO.Path]::GetFullPath((Join-Path $workspace $decisionRunPath.Replace('/', '\')))
            $relativeDecisionRun = [IO.Path]::GetRelativePath($workspace, $decisionRunDirectory).Replace('\', '/')
            Require ($relativeDecisionRun -ceq $decisionRunPath) "Chemin de run final non canonique : $decisionRunPath"
            $decisionRunLayoutValid = (
                $relativeDecisionRun -match '^animations/(?:runs|batches)/[A-Za-z0-9][A-Za-z0-9._-]*$' -or
                $relativeDecisionRun -match "^animations/ressources/$([regex]::Escape($decisionResref))/runs/[A-Za-z0-9][A-Za-z0-9._-]*$"
            ) -and $relativeDecisionRun -notmatch '[.]partial$'
            Require ($decisionRunLayoutValid) "Layout de run final invalide : $relativeDecisionRun"
            Require (Test-Path -LiteralPath $decisionRunDirectory -PathType Container) "Run final absent : $relativeDecisionRun"
            $decisionRunManifest = [string]$decision.final_run.manifest_path
            $decisionRunManifestPath = [IO.Path]::GetFullPath((Join-Path $workspace $decisionRunManifest.Replace('/', '\')))
            $relativeDecisionRunManifest = [IO.Path]::GetRelativePath($workspace, $decisionRunManifestPath).Replace('\', '/')
            Require ($relativeDecisionRunManifest -ceq $decisionRunManifest) "Chemin de manifeste du run final non canonique : $decisionRunManifest"
            Require ($relativeDecisionRunManifest -ceq "$relativeDecisionRun/manifest.json") "Manifest hors run final ou non canonique : $relativeDecisionRunManifest"
            Require (Test-Path -LiteralPath $decisionRunManifestPath -PathType Leaf) "Manifest de run final absent : $decisionRunManifest"
            Require ((Get-FileHash -LiteralPath $decisionRunManifestPath -Algorithm SHA256).Hash -eq [string]$decision.final_run.manifest_sha256) "Hash du run final invalide : $decisionRunManifest"
            $decisionFinalManifest = Get-Content -LiteralPath $decisionRunManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
            Require ([string]$decisionFinalManifest.schema -eq [string]$decision.final_run.schema -and [string]$decisionFinalManifest.status -eq [string]$decision.final_run.status) "Identite du run final incoherente : $decisionRunManifest"
            Require ([string]$decisionFinalManifest.status -in @('completed', 'validated', 'validated-installed')) "Run final non termine : $decisionRunManifest"
            Require (@(Get-AnimationManifestResrefs $decisionFinalManifest) -contains [string]$decision.resref) "Run final sans resref cible : $decisionRunManifest"
            Require (-not $qaDecisionRuns.ContainsKey($decisionResref)) "Decision ingame dupliquee : $decisionResref / $($candidate.area)"
            $qaDecisionRuns[$decisionResref] = @{
                path = $relativeDecisionRun
                manifest_path = $relativeDecisionRunManifest
                manifest_sha256 = [string]$decision.final_run.manifest_sha256
            }
        } else {
            Require (Test-QAEvidenceHash $workspace $relativeEvidence ([string]$evidence.sha256)) "Hash preuve QA animation invalide : $relativeEvidence"
        }
    }
    if ([int]$qaApproval.schema_version -eq 2) {
        $requiredQaResrefs = @($candidate.required_resrefs | ForEach-Object { ([string]$_).ToUpperInvariant() } | Sort-Object -Unique)
        Require (-not (Compare-Object $requiredQaResrefs @($qaDecisionRuns.Keys | Sort-Object))) "Couverture des decisions ingame incoherente : $($candidate.area)"
        Require ($null -ne $candidate.PSObject.Properties['source_runs']) "Runs source structures absents du candidat QA v2 : $($candidate.area)"
        $candidateRuns = @{}
        $candidateRunPaths = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($sourceRun in @($candidate.source_runs)) {
            Require ([string]$sourceRun.role -eq 'final') "Role de run candidat non final : $($sourceRun.path)"
            $sourceRunPath = [string]$sourceRun.path
            $sourceRunDirectory = [IO.Path]::GetFullPath((Join-Path $workspace $sourceRunPath.Replace('/', '\')))
            $relativeSourceRun = [IO.Path]::GetRelativePath($workspace, $sourceRunDirectory).Replace('\', '/')
            Require ($relativeSourceRun -ceq $sourceRunPath) "Chemin de run candidat non canonique : $sourceRunPath"
            Require ($relativeSourceRun -notmatch '[.]partial$') "Run candidat partiel interdit : $relativeSourceRun"
            Require ($candidateRunPaths.Add($relativeSourceRun)) "Run candidat duplique : $relativeSourceRun"
            Require (Test-Path -LiteralPath $sourceRunDirectory -PathType Container) "Run candidat absent : $relativeSourceRun"
            $sourceManifestPath = [IO.Path]::GetFullPath((Join-Path $workspace ([string]$sourceRun.manifest_path).Replace('/', '\')))
            $relativeSourceManifest = [IO.Path]::GetRelativePath($workspace, $sourceManifestPath).Replace('\', '/')
            Require ($relativeSourceManifest -ceq [string]$sourceRun.manifest_path) "Chemin de manifeste du run candidat non canonique : $($sourceRun.manifest_path)"
            Require ($relativeSourceManifest -ceq "$relativeSourceRun/manifest.json") "Manifest hors run candidat ou non canonique : $relativeSourceManifest"
            Require (Test-Path -LiteralPath $sourceManifestPath -PathType Leaf) "Manifest de run candidat absent : $($sourceRun.manifest_path)"
            Require ((Get-FileHash -LiteralPath $sourceManifestPath -Algorithm SHA256).Hash -eq [string]$sourceRun.manifest_sha256) "Hash de run candidat invalide : $($sourceRun.manifest_path)"
            $sourceRunAssets = @($sourceRun.asset_ids | ForEach-Object { ([string]$_).ToUpperInvariant() })
            if ($relativeSourceRun -match '^animations/ressources/([A-Z0-9_]{1,8})/runs/') {
                Require ($sourceRunAssets.Count -eq 1 -and $sourceRunAssets[0] -eq $Matches[1]) "Run candidat mono-resref affecte a un autre asset : $relativeSourceRun"
            }
            foreach ($resref in $sourceRunAssets) {
                Require (-not $candidateRuns.ContainsKey($resref)) "Run candidat duplique pour $resref : $($candidate.area)"
                $candidateRuns[$resref] = @{
                    path = $relativeSourceRun
                    manifest_path = $relativeSourceManifest
                    manifest_sha256 = [string]$sourceRun.manifest_sha256
                }
            }
        }
        Require (-not (Compare-Object $requiredQaResrefs @($candidateRuns.Keys | Sort-Object))) "Couverture des runs candidats incoherente : $($candidate.area)"
        foreach ($resref in $requiredQaResrefs) {
            Require ($qaDecisionRuns.ContainsKey([string]$resref) -and $candidateRuns.ContainsKey([string]$resref)) "Decision/run final absent : $resref / $($candidate.area)"
            $decisionRun = $qaDecisionRuns[[string]$resref]
            $candidateRun = $candidateRuns[[string]$resref]
            Require ($decisionRun.path -eq $candidateRun.path -and $decisionRun.manifest_path -eq $candidateRun.manifest_path -and $decisionRun.manifest_sha256 -eq $candidateRun.manifest_sha256) "Run final different de la decision ingame : $resref / $($candidate.area)"
        }
    }
}

& (Join-Path $ReleaseRoot 'tools/Test-BG2HD-DependencyContract.ps1') -ReleaseRoot $ReleaseRoot

$languages = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/languages.json') -Raw | ConvertFrom-Json
$expectedLanguages = @('english', 'french', 'german', 'spanish', 'italian', 'polish', 'russian', 'korean', 'chinese')
Require (($languages.supported_game_languages.directory -join ',') -eq ($expectedLanguages -join ',')) 'Registre des langues inattendu.'
$expectedIds = 1..19
foreach ($language in $expectedLanguages) {
    $tra = Join-Path $ReleaseRoot "bg2hd/tra/$language/setup.tra"
    Require (Test-Path -LiteralPath $tra -PathType Leaf) "TRA absent : $language"
    $raw = [IO.File]::ReadAllBytes($tra)
    Require (-not ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF)) "Le TRA doit etre UTF-8 sans BOM : $language"
    $ids = Get-Content -LiteralPath $tra -Encoding utf8 | ForEach-Object {
        if ($_ -match '^@(\d+)\s*=') { [int]$Matches[1] }
    }
    Require (($ids -join ',') -eq ($expectedIds -join ',')) "Identifiants TRA invalides : $language"
}

$tempTp2 = Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-tp2-' + [Guid]::NewGuid().ToString('N') + '.tp2')
try {
    & (Join-Path $ReleaseRoot 'tools/Generate-BG2HD-Tp2.ps1') -ReleaseRoot $ReleaseRoot -OutputPath $tempTp2 | Out-Null
    $checkedInTp2 = Join-Path $ReleaseRoot 'bg2hd/bg2hd.tp2'
    Require ((Get-FileHash -LiteralPath $tempTp2 -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $checkedInTp2 -Algorithm SHA256).Hash) 'TP2 versionne different du TP2 regenere.'
} finally {
    if (Test-Path -LiteralPath $tempTp2) { Remove-Item -LiteralPath $tempTp2 }
}

$tp2 = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'bg2hd/bg2hd.tp2') -Raw
$components = (Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/components.json') -Raw | ConvertFrom-Json).components
$content = (Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/content.json') -Raw | ConvertFrom-Json).entries
$runtimeCompatibility = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests/runtime-compatibility.json') -Raw | ConvertFrom-Json

foreach ($candidate in @($animationCandidates.candidates | Where-Object { [string]$_.approval_status -eq 'approved-for-release' })) {
    $area = [string]$candidate.area
    $entries = @($content | Where-Object { [string]$_.kind -eq 'area-animation' -and [string]$_.area -eq $area })
    Require ($entries.Count -gt 0) "Contenu animation approuve absent : $area"
    $packRoot = [IO.Path]::GetFullPath((Join-Path $workspace ([string]$candidate.source_pack).Replace('/', '\')))
    $packManifest = Get-Content -LiteralPath (Join-Path $packRoot 'manifest.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedSources = [System.Collections.Generic.List[string]]::new()
    $expectedSources.Add("$([string]$candidate.source_pack)/manifest.json")
    $expectedSources.Add("$([string]$candidate.source_pack)/AreaAnimations-X4.registry")
    foreach ($resource in @($packManifest.resources)) {
        foreach ($frame in @($resource.frames)) {
            $expectedSources.Add("$([string]$candidate.source_pack)/$([string]$frame.asset)")
        }
    }
    $actualSources = @($entries | ForEach-Object { [string]$_.source })
    Require ($actualSources.Count -eq @($actualSources | Sort-Object -Unique).Count) "Source de contenu animation dupliquee : $area"
    Require (-not (Compare-Object @($expectedSources | Sort-Object) @($actualSources | Sort-Object) -CaseSensitive)) "Projection content.json incomplete ou surnumeraire : $area"
    $expectedDestinations = @($expectedSources | ForEach-Object { "iee-assets/areas/$area/$([IO.Path]::GetFileName($_))" } | Sort-Object)
    $actualDestinations = @($entries | ForEach-Object { [string]$_.destination })
    Require ($actualDestinations.Count -eq @($actualDestinations | Sort-Object -Unique).Count) "Destination de contenu animation dupliquee : $area"
    Require (-not (Compare-Object $expectedDestinations @($actualDestinations | Sort-Object) -CaseSensitive)) "Destinations content.json incompletes ou surnumeraires : $area"
    $expectedSourceRun = if ($null -ne $candidate.PSObject.Properties['source_runs']) {
        (@($candidate.source_runs | ForEach-Object { [string]$_.path } | Sort-Object -Unique) -join ';')
    } else {
        [string]$candidate.source_run
    }
    Require (-not [string]::IsNullOrWhiteSpace($expectedSourceRun)) "Provenance source_run absente : $area"
    foreach ($entry in $entries) {
        Require ([int]$entry.component_id -eq [int]$candidate.component_id) "Component_id contenu/candidat incoherent : $area"
        Require ([string]$entry.component_label -ceq [string]$candidate.component_label) "Label contenu/candidat incoherent : $area"
        Require ([string]$entry.payload_group -ceq [string]$candidate.payload_group) "Payload group contenu/candidat incoherent : $area"
        Require ([string]$entry.source_run -ceq $expectedSourceRun) "Provenance de run contenu/candidat incoherente : $area"
        Require ([string]$entry.source -clike "$([string]$candidate.source_pack)/*") "Source de contenu hors pack candidat : $area / $($entry.source)"
    }
    $component = @($components | Where-Object { [int]$_.id -eq [int]$candidate.component_id })
    Require ($component.Count -eq 1) "Composant animation absent ou duplique : $area"
    Require ([string]$component[0].label -ceq [string]$candidate.component_label) "Label composant/candidat incoherent : $area"
    Require (@($component[0].payload_groups) -ccontains [string]$candidate.payload_group) "Payload group candidat absent du composant : $area"
}
foreach ($entry in @($content | Where-Object { [string]$_.kind -eq 'area-animation' })) {
    $approvedCandidate = @($animationCandidates.candidates | Where-Object {
        [string]$_.area -eq [string]$entry.area -and [string]$_.approval_status -eq 'approved-for-release'
    })
    Require ($approvedCandidate.Count -eq 1) "Contenu animation sans candidat approuve unique : $($entry.area)"
}
foreach ($name in @('animation-release-candidates.json', 'content.json', 'components.json')) {
    $authority = Join-Path $ReleaseRoot "manifests/$name"
    $mirror = Join-Path $ReleaseRoot "bg2hd/manifests/$name"
    Require (Test-Path -LiteralPath $mirror -PathType Leaf) "Miroir package absent : $name"
    Require ((Get-FileHash -LiteralPath $authority -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $mirror -Algorithm SHA256).Hash) "Miroir package divergent : $name"
}

Require (([regex]::Matches($tp2, '(?m)^LANGUAGE ')).Count -eq 9) 'Le TP2 doit declarer neuf langues.'
Require (([regex]::Matches($tp2, '(?m)^BEGIN ')).Count -eq @($components).Count) 'Le TP2 ne couvre pas tous les composants declares.'
Require (([regex]::Matches($tp2, '(?m)^  COPY_LARGE ')).Count -eq @($content).Count) 'Le TP2 ne couvre pas toutes les entrees du manifeste de contenu.'
Require ($tp2 -match '(?m)^VERSION ~0\.1\.0-alpha\.2~\r?$') 'Version WeiDU absente.'
foreach ($id in @($components | ForEach-Object { [int]$_.id })) {
    Require ($tp2 -match "(?m)^  DESIGNATED $id\r?$") "DESIGNATED absent : $id"
}
Require ($tp2 -match 'REQUIRE_PREDICATE GAME_IS ~bg2ee~ @11') 'Garde BG2EE absente.'
Require ($tp2 -match '(?m)^  AT_NOW preflight_result ') 'Preflight Core absent.'
Require ($tp2 -match '(?m)^  AT_UNINSTALL ') 'Restauration Core absente.'
Require ($tp2 -match '(?m)^  AT_NOW ui_config_result ') 'Activation UI x4 absente.'
Require ($tp2 -match '(?m)^  MKDIR ~iee-assets~\r?$') 'Creation du dossier iee-assets absente.'
$copySources = [regex]::Matches($tp2, '(?m)^  COPY_LARGE ~([^~]+)~') | ForEach-Object { $_.Groups[1].Value }
Require (($copySources | Where-Object { $_ -match '(?i)(?:^|/)(?:override|backups|archive|captures|temp)(?:/|$)' }).Count -eq 0) 'Un chemin de source interdit apparait dans le TP2.'
Require ($runtimeCompatibility.owned_ini_keys.'core-steam'.Shaders.EnableNativeOcclusionBridge -eq 'true') 'Activation Core du bridge d occlusion absente.'
$ar0516Candidate = @($animationCandidates.candidates | Where-Object { $_.area -eq 'AR0516' })
Require ($ar0516Candidate.Count -eq 1 -and $null -ne $ar0516Candidate[0].occlusion_contract) 'Contrat occlusion AR0516 absent.'
$ar0516Wed = @($content | Where-Object { $_.destination -eq 'override/AR0516.WED' })
Require ($ar0516Wed.Count -eq 1 -and $ar0516Wed[0].sha256 -eq '8A0AA3CA4C5D7A9BD42DDD0F55F6CA5ED57241A5F4B141C3CBE7D18D9AA2DB1A' -and [int64]$ar0516Wed[0].bytes -eq 41502) 'Correction WED AR0516 absente ou invalide.'
$ar0516AnimationComponent = @($components | Where-Object { [int]$_.id -eq 3002 })
Require ($ar0516AnimationComponent.Count -eq 1 -and $ar0516AnimationComponent[0].depends_on -contains 1580) 'Le composant animation AR0516 ne depend pas de sa correction WED.'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $ReleaseRoot '..\..')).Path
$csv = Import-Csv -LiteralPath (Join-Path $workspaceRoot 'areas.csv') | Where-Object { $_.area_id -match '^(AR|OH)\d{4}$' }
$validated = [Collections.Generic.List[string]]::new()
foreach ($area in $csv) {
    if ($area.status -eq 'validated-installed') { $validated.Add([string]$area.area_id) }
    if ($area.status_nuit -eq 'validated-installed') { $validated.Add(([string]$area.area_id) + 'N') }
}
$manifestVariants = @($content | Where-Object { $_.kind -eq 'map' } | ForEach-Object { [string]$_.area } | Sort-Object -Unique)
Require (-not (Compare-Object (@($validated | Sort-Object -Unique) | Sort-Object) $manifestVariants)) 'Le manifeste ne couvre pas exactement les cartes validees du CSV.'

if ($WeiDUExecutable) {
    Require (Test-Path -LiteralPath $WeiDUExecutable -PathType Leaf) "WeiDU absent : $WeiDUExecutable"
    $weiduTestRoot = Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-tp2-runtime-' + [Guid]::NewGuid().ToString('N'))
    $locationPushed = $false
    try {
        New-Item -ItemType Directory -Path $weiduTestRoot | Out-Null
        Copy-Item -LiteralPath (Join-Path $ReleaseRoot 'bg2hd') -Destination (Join-Path $weiduTestRoot 'bg2hd') -Recurse
        $setup = Join-Path $weiduTestRoot 'setup-bg2hd.exe'
        Copy-Item -LiteralPath $WeiDUExecutable -Destination $setup
        Push-Location -LiteralPath $weiduTestRoot
        $locationPushed = $true
        $expectedLanguageNames = @('English', 'Francais', 'Deutsch', 'Espanol', 'Italiano', 'Polski', 'Russian', 'Korean', 'Simplified Chinese')
        for ($languageIndex = 0; $languageIndex -lt $expectedLanguageNames.Count; $languageIndex++) {
            $runtimeOutput = & $setup '--nogame' '--noautoupdate' '--force-install-list' '0' '--language' "$languageIndex" '--no-exit-pause' 2>&1 | Out-String
            $runtimeExitCode = $LASTEXITCODE
            Require ($runtimeExitCode -eq 0) "Code WeiDU inattendu pour la garde BG2EE, langue $languageIndex : $runtimeExitCode"
            Require ($runtimeOutput -match "Using Language \[$([regex]::Escape($expectedLanguageNames[$languageIndex]))\]") "WeiDU n a pas charge la langue attendue : $($expectedLanguageNames[$languageIndex])"
            Require ($runtimeOutput -match 'SKIPPING:') 'WeiDU n a pas evalue la garde BG2EE attendue.'
        }
    } finally {
        if ($locationPushed) { Pop-Location }
        if (Test-Path -LiteralPath $weiduTestRoot) { Remove-Item -LiteralPath $weiduTestRoot -Recurse }
    }
}

Write-Output 'Phase 2 static validation passed: schemas, translations, deterministic TP2 and component guards.'
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
