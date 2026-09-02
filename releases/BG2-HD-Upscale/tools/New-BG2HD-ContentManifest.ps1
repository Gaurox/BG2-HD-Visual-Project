[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\manifests\content.json'),
    [string]$AnimationCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\animation-release-candidates.json'),
    [string]$RuntimeCompatibilityPath = (Join-Path $PSScriptRoot '..\manifests\runtime-compatibility.json'),
    [string]$OverlayPolicyPath = (Join-Path $PSScriptRoot '..\manifests\overlay-sources.json'),
    [switch]$IncludePendingAnimationCandidates,
    [string]$AnimationQaApprovalOverridePath,
    [string[]]$OnlyAnimationArea
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $WorkspaceRoot
try {

$selectedAnimationAreas = [System.Collections.Generic.List[string]]::new()
foreach ($area in @($OnlyAnimationArea | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })) {
    $normalized = ([string]$area).Trim().ToUpperInvariant()
    if ($normalized -notmatch '^(AR|OH)[0-9]{4}$') {
        throw "Zone animation delta invalide : $area"
    }
    if (-not $selectedAnimationAreas.Contains($normalized)) {
        $selectedAnimationAreas.Add($normalized)
    }
}
$isAnimationDelta = $selectedAnimationAreas.Count -gt 0
if (-not [string]::IsNullOrWhiteSpace($AnimationQaApprovalOverridePath) -and $selectedAnimationAreas.Count -ne 1) {
    throw '-AnimationQaApprovalOverridePath exige exactement une zone via -OnlyAnimationArea.'
}

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

function Read-Json([string]$Path) {
    Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
}

function Test-BG2HDRegularFilePath([string]$Path, [string]$Label) {
    try {
        $attributes = [IO.File]::GetAttributes($Path)
    } catch {
        $exception = $_.Exception
        while ($null -ne $exception.InnerException) { $exception = $exception.InnerException }
        if (
            $exception -is [System.IO.FileNotFoundException] -or
            $exception -is [System.IO.DirectoryNotFoundException]
        ) {
            return $false
        }
        throw
    }
    if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label ReparsePoint interdit : $Path"
    }
    if (
        ($attributes -band [IO.FileAttributes]::Directory) -ne 0 -or
        ($attributes -band [IO.FileAttributes]::Device) -ne 0 -or
        -not [IO.File]::Exists($Path)
    ) {
        throw "$Label non regulier : $Path"
    }
    return $true
}

function Write-BG2HDAtomicUtf8NoBomFile([string]$Path, [string]$Text) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $directory = [IO.Path]::GetDirectoryName($fullPath)
    if ([string]::IsNullOrWhiteSpace($directory)) { throw "Dossier de sortie introuvable : $Path" }
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $temporaryPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullPath) + '.' + [Guid]::NewGuid().ToString('N') + '.partial')
    $backupPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullPath) + '.' + [Guid]::NewGuid().ToString('N') + '.replace-backup.partial')
    $stream = $null
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text)
        $stream = [IO.FileStream]::new(
            $temporaryPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None,
            65536,
            [IO.FileOptions]::WriteThrough
        )
        if ($bytes.Length -gt 0) { $stream.Write($bytes, 0, $bytes.Length) }
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        $targetExists = Test-BG2HDRegularFilePath -Path $fullPath -Label 'Cible de publication'
        if ($targetExists) {
            [IO.File]::Replace($temporaryPath, $fullPath, $backupPath, $true)
        } else {
            [IO.File]::Move($temporaryPath, $fullPath)
        }
    }
    finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ([IO.File]::Exists($temporaryPath)) { [IO.File]::Delete($temporaryPath) }
        if ([IO.File]::Exists($backupPath)) { [IO.File]::Delete($backupPath) }
    }
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

function Get-RelativeUnixPath([string]$Base, [string]$Path) {
    $relative = [IO.Path]::GetRelativePath($Base, $Path)
    return $relative.Replace('\', '/')
}

function New-ContentEntry([hashtable]$Spec, [IO.FileInfo]$File) {
    $relative = Get-RelativeUnixPath $WorkspaceRoot $File.FullName
    [ordered]@{
        component_id = $Spec.ComponentId
        component_label = $Spec.ComponentLabel
        payload_group = $Spec.PayloadGroup
        kind = $Spec.Kind
        area = $Spec.Area
        source = $relative
        source_run = $Spec.SourceRun
        destination = "$($Spec.DestinationRoot)/$($File.Name)"
        bytes = $File.Length
        sha256 = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
        qa_status = 'validated'
        scale = if ($Spec.ContainsKey('Scale')) { $Spec.Scale } else { 4 }
        model = $Spec.Model
        install_order = $Spec.InstallOrder
        replaces_component_output = [bool]$Spec.ReplacesComponentOutput
    }
}

function Get-AnimationCandidateEntries {
    param(
        [string]$Workspace,
        [string]$CandidatesPath,
        [string]$RuntimePath,
        [bool]$IncludePending,
        [string[]]$OnlyAreas
    )

    if (-not (Test-Path -LiteralPath $CandidatesPath -PathType Leaf)) {
        throw "Registre de candidats animation absent : $CandidatesPath"
    }
    $releaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    Require (Test-Json -Path $CandidatesPath -SchemaFile (Join-Path $releaseRoot 'schemas\animation-release-candidates.schema.json')) 'Schema du registre de candidats animation invalide.'
    $candidates = Read-Json $CandidatesPath
    $candidateAreas = @($candidates.candidates | ForEach-Object { [string]$_.area })
    $candidateComponentIds = @($candidates.candidates | ForEach-Object { [int]$_.component_id })
    Require ($candidateAreas.Count -eq @($candidateAreas | Sort-Object -Unique).Count) 'Zones dupliquees dans le registre de candidats animation.'
    Require ($candidateComponentIds.Count -eq @($candidateComponentIds | Sort-Object -Unique).Count) 'Component_id duplique dans le registre de candidats animation.'
    $requestedAreas = @($OnlyAreas | Sort-Object -Unique)
    foreach ($area in $requestedAreas) {
        $matches = @($candidates.candidates | Where-Object { [string]$_.area -eq $area })
        Require ($matches.Count -eq 1) "Candidat animation delta absent ou duplique : $area"
        $approved = ([string]$matches[0].approval_status -eq 'approved-for-release')
        Require ($approved -or $IncludePending) "Candidat animation delta non approuve : $area"
    }
    $result = [System.Collections.Generic.List[object]]::new()
    foreach ($candidate in @($candidates.candidates | Sort-Object component_id)) {
        if ($requestedAreas.Count -gt 0 -and [string]$candidate.area -notin $requestedAreas) { continue }
        $approved = ([string]$candidate.approval_status -eq 'approved-for-release')
        if (-not $approved -and -not $IncludePending) { continue }

        $sourceDirectory = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$candidate.source_pack).Replace('/', '\')))
        $relativeSource = [IO.Path]::GetRelativePath($Workspace, $sourceDirectory).Replace('\', '/')
        Require ($relativeSource -notmatch '(^|/)\.\.(/|$)') "Pack animation hors workspace : $($candidate.source_pack)"
        Require ($relativeSource -notmatch '(^|/)(archive|archives|backup|backups|capture|captures|override|proto|staging|temp|tmp)(/|$)') "Pack animation interdit : $relativeSource"
        Require ($relativeSource -ceq [string]$candidate.source_pack) "Chemin de pack animation non canonique : $($candidate.source_pack)"
        Require ($relativeSource.EndsWith('/' + [string]$candidate.area, [StringComparison]::Ordinal)) "Pack animation range sous une autre zone : $relativeSource"
        Require (Test-Path -LiteralPath $sourceDirectory -PathType Container) "Pack animation absent : $sourceDirectory"

        $declaredQaApprovalPath = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$candidate.qa_approval).Replace('/', '\')))
        $relativeQaApproval = [IO.Path]::GetRelativePath($Workspace, $declaredQaApprovalPath).Replace('\', '/')
        Require ($relativeQaApproval -notmatch '(^|/)\.\.(/|$)') "Approbation QA animation hors workspace : $($candidate.qa_approval)"
        Require ($relativeQaApproval -notmatch '(^|/)(archive|archives|backup|backups|capture|captures|override|proto|staging|temp|tmp)(/|$)') "Approbation QA animation interdite : $relativeQaApproval"
        Require ($relativeQaApproval -ceq [string]$candidate.qa_approval) "Chemin d'approbation QA animation non canonique : $($candidate.qa_approval)"
        $qaApprovalPrefix = "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/$($candidate.area)/"
        Require ($relativeQaApproval.StartsWith($qaApprovalPrefix, [StringComparison]::Ordinal)) "Approbation QA rangee sous une autre zone : $relativeQaApproval"
        $qaApprovalPath = if (-not [string]::IsNullOrWhiteSpace($AnimationQaApprovalOverridePath) -and [string]$candidate.area -eq $selectedAnimationAreas[0]) {
            [IO.Path]::GetFullPath($AnimationQaApprovalOverridePath)
        } else {
            $declaredQaApprovalPath
        }
        Require (Test-Path -LiteralPath $qaApprovalPath -PathType Leaf) "Approbation QA animation absente : $qaApprovalPath"
        Require ((Get-FileHash -LiteralPath $qaApprovalPath -Algorithm SHA256).Hash -eq [string]$candidate.qa_approval_sha256) "Hash approbation QA animation invalide : $($candidate.area)"
        Require (Test-Json -Path $qaApprovalPath -SchemaFile (Join-Path $releaseRoot 'schemas\animation-qa-approval.schema.json')) "Schema approbation QA animation invalide : $($candidate.area)"
        $qaApproval = Read-Json $qaApprovalPath
        $qaSchemaVersion = [int]$qaApproval.schema_version
        $acceptedOrigins = @{
            1 = 'preserved-existing-user-qa'
            2 = 'explicit-user-ingame-qa'
            3 = 'explicit-user-ingame-qa-with-byte-identical-carry-forward'
        }
        Require ($qaApproval.status -eq 'accepted' -and $acceptedOrigins.ContainsKey($qaSchemaVersion) -and $qaApproval.decision_origin -eq $acceptedOrigins[$qaSchemaVersion]) "Decision QA animation non acceptee : $($candidate.area)"
        Require ($qaApproval.area -eq [string]$candidate.area) "Zone de l'approbation QA animation incoherente : $($candidate.area)"
        Require ($qaApproval.source_pack -eq [string]$candidate.source_pack) "Pack de l'approbation QA animation incoherent : $($candidate.area)"
        Require ($qaApproval.pack_manifest_sha256 -eq [string]$candidate.pack_manifest_sha256) "Manifest de pack non couvert par la QA : $($candidate.area)"
        Require ($qaApproval.registry -eq [string]$candidate.registry -and [int]$qaApproval.registry_version -eq [int]$candidate.registry_version -and $qaApproval.registry_sha256 -eq [string]$candidate.registry_sha256) "Registre non couvert par la QA : $($candidate.area)"
        $qaResrefs = @($qaApproval.required_resrefs | Sort-Object -Unique)
        $candidateResrefs = @($candidate.required_resrefs | Sort-Object -Unique)
        Require (-not (Compare-Object $candidateResrefs $qaResrefs)) "Resrefs non couverts exactement par la QA : $($candidate.area)"
        $releaseVerifier = Join-Path $Workspace 'pipeline\scripts\verify_animation_release_candidate.py'
        Require (Test-Path -LiteralPath $releaseVerifier -PathType Leaf) 'Validateur de release animation absent.'
        $releaseArguments = @(
            $releaseVerifier,
            '--workspace-root', $Workspace,
            '--animation-candidates-path', $CandidatesPath,
            '--area', [string]$candidate.area
        )
        if ($qaApprovalPath -ne $declaredQaApprovalPath) {
            $releaseArguments += @('--animation-qa-approval-override-path', $qaApprovalPath)
        }
        if (-not $approved -and $IncludePending) {
            $releaseArguments += '--allow-pending'
        }
        $releaseOutput = @(& python @releaseArguments 2>&1)
        $releaseExitCode = $LASTEXITCODE
        Require ($releaseExitCode -eq 0) (
            "Release animation invalide : $($candidate.area)" +
            $(if ($releaseOutput.Count -gt 0) { [Environment]::NewLine + ($releaseOutput -join [Environment]::NewLine) } else { '' })
        )
        $coveredQaResrefs = @()
        $qaDecisionFinalRuns = @{}
        if ($qaSchemaVersion -eq 1) {
            $coveredQaResrefs = $candidateResrefs
        } else {
          foreach ($evidence in @($qaApproval.evidence)) {
            $evidencePath = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$evidence.path).Replace('/', '\')))
            $relativeEvidence = [IO.Path]::GetRelativePath($Workspace, $evidencePath).Replace('\', '/')
            Require ($relativeEvidence -notmatch '(^|/)\.\.(/|$)') "Preuve QA animation hors workspace : $($evidence.path)"
            Require ($relativeEvidence -notmatch '(^|/)(archive|archives|backup|backups|capture|captures|override|proto|staging|temp|tmp)(/|$)') "Preuve QA animation interdite : $relativeEvidence"
            Require (Test-Path -LiteralPath $evidencePath -PathType Leaf) "Preuve QA animation absente : $relativeEvidence"
            if ($qaSchemaVersion -in @(2, 3)) {
                Require ((Get-FileHash -LiteralPath $evidencePath -Algorithm SHA256).Hash -eq [string]$evidence.sha256) "Hash courant de preuve QA invalide : $relativeEvidence"
            } else {
                Require (Test-QAEvidenceHash $Workspace $relativeEvidence ([string]$evidence.sha256)) "Hash preuve QA animation invalide : $relativeEvidence"
            }
            switch ([string]$evidence.kind) {
                'run-qa-approval' {
                    Require ($relativeEvidence -match '^animations/runs/[^/]+/qa-approval[.]json$') "Chemin de preuve run QA invalide : $relativeEvidence"
                    $runApproval = Read-Json $evidencePath
                    Require ($runApproval.status -eq 'accepted') "Preuve run QA non acceptee : $relativeEvidence"
                }
                'canonical-registry' {
                    Require ($relativeEvidence -eq 'animations/index/animation_upscale_registry.csv') "Registre canonique QA inattendu : $relativeEvidence"
                }
                'canonical-alpha-corrections' {
                    Require ($relativeEvidence -eq 'animations/index/animation_alpha_corrections.csv') "Registre alpha QA inattendu : $relativeEvidence"
                }
                'ingame-qa-decision' {
                    Require ($qaSchemaVersion -in @(2, 3)) "Decision ingame interdite dans une approbation QA legacy : $relativeEvidence"
                    Require ($relativeEvidence -match '^animations/index/qa-decisions/[A-Z0-9_]{1,8}/[A-Za-z0-9._-]+[.]json$') "Chemin de decision ingame invalide : $relativeEvidence"
                    $decisionSchema = Join-Path $Workspace 'animations\schemas\animation-qa-decision.schema.json'
                    Require (Test-Json -Path $evidencePath -SchemaFile $decisionSchema) "Schema de decision ingame invalide : $relativeEvidence"
                    $decision = Read-Json $evidencePath
                    $evidenceResrefs = @($evidence.accepted_resrefs | Sort-Object -Unique)
                    Require ($evidenceResrefs.Count -eq 1) "Une decision ingame doit couvrir un seul resref : $relativeEvidence"
                    $decisionResref = ([string]$decision.resref).ToUpperInvariant()
                    Require ($decision.result_kind -eq 'x4') "Decision ingame non x4 interdite en release : $relativeEvidence"
                    Require ($decision.status -eq 'accepted' -and $decision.decision_origin -eq 'explicit-user-ingame-qa') "Decision ingame non acceptee : $relativeEvidence"
                    Require ($decisionResref -eq $evidenceResrefs[0] -and [string]$decision.asset_id -eq "animations:bam:$decisionResref") "Resref de decision ingame incoherent : $relativeEvidence"
                    $expectedDecisionPath = "animations/index/qa-decisions/$decisionResref/$($decision.decision_id).json"
                    Require ($relativeEvidence -ceq $expectedDecisionPath) "Decision ingame rangee sous un autre asset ou identifiant : $relativeEvidence"
                    Require (@($decision.tested_areas) -contains [string]$candidate.area) "Zone absente de la decision ingame : $relativeEvidence"
                    $decisionArea = @($decision.source_pack.areas | Where-Object { [string]$_.area -eq [string]$candidate.area })
                    Require ($decisionArea.Count -eq 1) "Pack de zone absent ou duplique dans la decision : $relativeEvidence"
                    Require ([string]$decisionArea[0].path -eq [string]$candidate.source_pack) "Pack de decision different du candidat : $relativeEvidence"
                    Require ([string]$decisionArea[0].manifest_sha256 -eq [string]$candidate.pack_manifest_sha256 -and [string]$decisionArea[0].registry_sha256 -eq [string]$candidate.registry_sha256) "Hashes du pack de decision differents du candidat : $relativeEvidence"

                    $decisionRunDirectory = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$decision.final_run.path).Replace('/', '\')))
                    $relativeDecisionRun = [IO.Path]::GetRelativePath($Workspace, $decisionRunDirectory).Replace('\', '/')
                    Require ($relativeDecisionRun -notmatch '(^|/)\.\.(/|$)' -and $relativeDecisionRun -notmatch '(^|/)(archive|archives|backup|backups|capture|captures|override|proto|staging|temp|tmp)(/|$)') "Run final QA interdit : $relativeDecisionRun"
                    Require ($relativeDecisionRun -ceq [string]$decision.final_run.path) "Chemin de run final QA non canonique : $($decision.final_run.path)"
                    $decisionRunLayoutValid = (
                        $relativeDecisionRun -match '^animations/(?:runs|batches)/[A-Za-z0-9][A-Za-z0-9._-]*$' -or
                        $relativeDecisionRun -match "^animations/ressources/$([regex]::Escape($decisionResref))/runs/[A-Za-z0-9][A-Za-z0-9._-]*$"
                    ) -and $relativeDecisionRun -notmatch '[.]partial$'
                    Require ($decisionRunLayoutValid) "Layout de run final QA invalide : $relativeDecisionRun"
                    Require (Test-Path -LiteralPath $decisionRunDirectory -PathType Container) "Run final QA absent : $relativeDecisionRun"
                    $decisionRunManifest = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$decision.final_run.manifest_path).Replace('/', '\')))
                    $relativeDecisionRunManifest = [IO.Path]::GetRelativePath($Workspace, $decisionRunManifest).Replace('\', '/')
                    Require ($relativeDecisionRunManifest -ceq [string]$decision.final_run.manifest_path) "Chemin de manifeste du run final QA non canonique : $($decision.final_run.manifest_path)"
                    Require ($relativeDecisionRunManifest -ceq "$relativeDecisionRun/manifest.json") "Manifest hors run final QA ou non canonique : $relativeDecisionRunManifest"
                    Require (Test-Path -LiteralPath $decisionRunManifest -PathType Leaf) "Manifest de run final QA absent : $relativeDecisionRunManifest"
                    Require ((Get-FileHash -LiteralPath $decisionRunManifest -Algorithm SHA256).Hash -eq [string]$decision.final_run.manifest_sha256) "Hash du run final QA invalide : $relativeDecisionRun"
                    $decisionFinalManifest = Read-Json $decisionRunManifest
                    Require ([string]$decisionFinalManifest.schema -eq [string]$decision.final_run.schema -and [string]$decisionFinalManifest.status -eq [string]$decision.final_run.status) "Identite du run final QA incoherente : $relativeDecisionRun"
                    Require ([string]$decisionFinalManifest.status -in @('completed', 'validated', 'validated-installed')) "Run final QA non termine : $relativeDecisionRun"
                    Require (@(Get-AnimationManifestResrefs $decisionFinalManifest) -contains $decisionResref) "Run final QA ne declare pas $decisionResref : $relativeDecisionRun"
                    Require (-not $qaDecisionFinalRuns.ContainsKey($decisionResref)) "Decision ingame dupliquee : $decisionResref"
                    $qaDecisionFinalRuns[$decisionResref] = @{
                        path = $relativeDecisionRun
                        manifest_path = $relativeDecisionRunManifest
                        manifest_sha256 = [string]$decision.final_run.manifest_sha256
                    }
                }
                'byte-identical-release-continuity' {
                    Require ($qaSchemaVersion -eq 3) "Preuve de continuite interdite hors QA v3 : $relativeEvidence"
                }
            }
            $coveredQaResrefs += @($evidence.accepted_resrefs)
          }
          $coveredQaResrefs = @($coveredQaResrefs | Sort-Object -Unique)
          Require (-not (Compare-Object $candidateResrefs $coveredQaResrefs)) "Preuves QA incompletes ou hors candidat : $($candidate.area)"
        }

        $packManifestPath = Join-Path $sourceDirectory ([string]$candidate.pack_manifest)
        Require (Test-Path -LiteralPath $packManifestPath -PathType Leaf) "Manifest de pack animation absent : $packManifestPath"
        Require ((Get-FileHash -LiteralPath $packManifestPath -Algorithm SHA256).Hash -eq [string]$candidate.pack_manifest_sha256) "Hash manifeste animation invalide : $($candidate.area)"
        $pack = Read-Json $packManifestPath
        $registryVersion = [int]$candidate.registry_version
        Require ($pack.schema -eq 'bg2-upscale-area-animation-runtime-pack-v2') "Schema de pack animation inattendu : $($candidate.area)"
        Require ($registryVersion -in @(2, 3)) "Version de registre animation non publiee : $($candidate.area)"
        Require ($pack.status -eq 'completed' -and [int]$pack.scale -eq 4 -and [int]$pack.registry_version -eq $registryVersion) "Pack animation non finalise, non x4 ou version incoherente : $($candidate.area)"
        Require ($pack.area_id -eq [string]$candidate.area) "Zone de pack animation incoherente : $($candidate.area)"
        Require ([string]$pack.registry -eq [string]$candidate.registry) "Nom de registre du pack animation incoherent : $($candidate.area)"
        Require ($pack.runtime_contract.feature -eq 'TimedTimeline' -and [int]$pack.runtime_contract.registry_version -eq $registryVersion) "Contrat runtime animation absent : $($candidate.area)"
        if ($qaSchemaVersion -in @(2, 3)) {
            Require ($pack.runtime_budget_enforced -is [bool] -and [bool]$pack.runtime_budget_enforced) "Pack auteur ou budget runtime non confirme interdit en release : $($candidate.area)"
            Require (-not ($pack.authoring_pack_for_area_split -is [bool] -and [bool]$pack.authoring_pack_for_area_split)) "Pack auteur non decoupe interdit en release : $($candidate.area)"
        }
        $expectedRendererContract = if ($registryVersion -eq 3) { 'area-animation-per-area-registry-v3-position-timed-timeline' } else { 'area-animation-per-area-registry-v2-timed-timeline' }
        Require ([string]$candidate.renderer_contract -eq $expectedRendererContract) "Contrat renderer animation incoherent : $($candidate.area)"

        if ($null -ne $candidate.occlusion_contract) {
            $occlusion = $candidate.occlusion_contract
            Require ([string]$occlusion.mode -eq 'native-wed-bridge-v1') "Mode occlusion release invalide : $($candidate.area)"
            Require ([string]$occlusion.destination -eq "override/$($candidate.area).WED") "Destination WED incoherente : $($candidate.area)"
            $wedSpecPath = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$occlusion.source_spec).Replace('/', '\')))
            $wedSourcePath = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$occlusion.source).Replace('/', '\')))
            $occlusionEvidencePath = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$occlusion.qa_evidence).Replace('/', '\')))
            foreach ($path in @($wedSpecPath, $wedSourcePath, $occlusionEvidencePath)) {
                Require ([IO.Path]::GetRelativePath($Workspace, $path) -notmatch '(^|[\\/])[.][.]([\\/]|$)') "Source occlusion hors workspace : $path"
                Require (Test-Path -LiteralPath $path -PathType Leaf) "Source occlusion absente : $path"
            }
            $wedSpec = Read-Json $wedSpecPath
            Require ($wedSpec.status -eq 'validated-installed' -and $wedSpec.qa.release_manifest -eq 'selected-pending-content-regeneration') "Correction WED non selectionnee : $($candidate.area)"
            Require ([string]$wedSpec.validated_output.release_source -eq [string]$occlusion.source) "Source release WED incoherente : $($candidate.area)"
            Require ((Get-Item -LiteralPath $wedSourcePath).Length -eq [int64]$occlusion.bytes) "Taille WED invalide : $($candidate.area)"
            Require ((Get-FileHash -LiteralPath $wedSourcePath -Algorithm SHA256).Hash -eq [string]$occlusion.sha256) "Hash WED invalide : $($candidate.area)"
            Require ((Get-FileHash -LiteralPath $occlusionEvidencePath -Algorithm SHA256).Hash -eq [string]$occlusion.qa_evidence_sha256) "Hash preuve occlusion invalide : $($candidate.area)"
            $runtime = Read-Json $RuntimePath
            Require ([string]$occlusion.ini_owner -eq 'core-steam' -and [string]$occlusion.ini_section -eq 'Shaders' -and [string]$occlusion.ini_key -eq 'EnableNativeOcclusionBridge' -and [string]$occlusion.ini_value -eq 'true') "Contrat INI occlusion invalide : $($candidate.area)"
            Require ([string]$runtime.owned_ini_keys.'core-steam'.Shaders.EnableNativeOcclusionBridge -eq 'true') "Le Core release n'active pas le bridge d'occlusion : $($candidate.area)"
        }

        $packResrefs = @($pack.resources | ForEach-Object { [string]$_.resref } | Sort-Object -Unique)
        $requiredResrefs = @($candidate.required_resrefs | Sort-Object -Unique)
        Require (-not (Compare-Object $requiredResrefs $packResrefs)) "Inventaire resref du pack animation incoherent : $($candidate.area)"

        $sourceRunText = [string]$candidate.source_run
        if ($qaSchemaVersion -in @(2, 3)) {
            Require ($null -ne $candidate.PSObject.Properties['source_runs']) "Runs source structures absents du candidat QA v$qaSchemaVersion : $($candidate.area)"
        }
        if ($null -ne $candidate.PSObject.Properties['source_runs']) {
            $sourceRunPaths = [System.Collections.Generic.List[string]]::new()
            $sourceRunResrefs = [System.Collections.Generic.List[string]]::new()
            $candidateSourceRunByResref = @{}
            foreach ($sourceRun in @($candidate.source_runs)) {
                $sourceRunDirectory = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$sourceRun.path).Replace('/', '\')))
                $relativeSourceRun = [IO.Path]::GetRelativePath($Workspace, $sourceRunDirectory).Replace('\', '/')
                Require ($relativeSourceRun -notmatch '(^|/)\.\.(/|$)') "Run source hors workspace : $($sourceRun.path)"
                Require ($relativeSourceRun -notmatch '(^|/)(archive|archives|backup|backups|capture|captures|override|proto|staging|temp|tmp)(/|$)') "Run source interdit : $relativeSourceRun"
                Require ($relativeSourceRun -ceq [string]$sourceRun.path) "Chemin de run source non canonique : $($sourceRun.path)"
                Require ($relativeSourceRun -notmatch '[.]partial$') "Run source partiel interdit : $relativeSourceRun"
                if ($qaSchemaVersion -in @(2, 3)) {
                    Require ([string]$sourceRun.role -eq 'final') "Role de run source non final : $relativeSourceRun"
                }
                Require (Test-Path -LiteralPath $sourceRunDirectory -PathType Container) "Run source absent : $relativeSourceRun"
                $sourceRunManifest = [IO.Path]::GetFullPath((Join-Path $Workspace ([string]$sourceRun.manifest_path).Replace('/', '\')))
                $relativeSourceRunManifest = [IO.Path]::GetRelativePath($Workspace, $sourceRunManifest).Replace('\', '/')
                Require ($relativeSourceRunManifest -ceq [string]$sourceRun.manifest_path) "Chemin de manifeste du run source non canonique : $($sourceRun.manifest_path)"
                Require ($relativeSourceRunManifest -ceq "$relativeSourceRun/manifest.json") "Manifest hors run source ou non canonique : $relativeSourceRunManifest"
                Require (Test-Path -LiteralPath $sourceRunManifest -PathType Leaf) "Manifest de run source absent : $relativeSourceRunManifest"
                Require ((Get-FileHash -LiteralPath $sourceRunManifest -Algorithm SHA256).Hash -eq [string]$sourceRun.manifest_sha256) "Hash de run source invalide : $relativeSourceRun"
                $sourceRunAssetIds = @($sourceRun.asset_ids)
                if ($relativeSourceRun -match '^animations/ressources/([A-Z0-9_]{1,8})/runs/') {
                    Require ($sourceRunAssetIds.Count -eq 1 -and ([string]$sourceRunAssetIds[0]).ToUpperInvariant() -eq $Matches[1]) "Run mono-resref affecte a un autre asset : $relativeSourceRun"
                }
                foreach ($assetId in $sourceRunAssetIds) {
                    $normalizedAssetId = ([string]$assetId).ToUpperInvariant()
                    Require ($normalizedAssetId -match '^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$') "Asset id invalide dans un run source : $assetId"
                    Require (-not $candidateSourceRunByResref.ContainsKey($normalizedAssetId)) "Run source duplique pour $normalizedAssetId : $($candidate.area)"
                    $sourceRunResrefs.Add($normalizedAssetId)
                    $candidateSourceRunByResref[$normalizedAssetId] = @{
                        path = $relativeSourceRun
                        manifest_path = $relativeSourceRunManifest
                        manifest_sha256 = [string]$sourceRun.manifest_sha256
                    }
                }
                $sourceRunPaths.Add($relativeSourceRun)
            }
            Require ($sourceRunPaths.Count -eq @($sourceRunPaths | Sort-Object -Unique).Count) "Run source duplique : $($candidate.area)"
            if ($qaSchemaVersion -ne 3) {
                Require (-not (Compare-Object $requiredResrefs @($sourceRunResrefs | Sort-Object -Unique))) "Couverture des runs source incoherente : $($candidate.area)"
            }
            if ($qaSchemaVersion -eq 2) {
                foreach ($resref in $requiredResrefs) {
                    Require ($qaDecisionFinalRuns.ContainsKey($resref) -and $candidateSourceRunByResref.ContainsKey($resref)) "Decision/run final non couvert : $resref / $($candidate.area)"
                    $decisionRun = $qaDecisionFinalRuns[$resref]
                    $candidateRun = $candidateSourceRunByResref[$resref]
                    Require ($decisionRun.path -eq $candidateRun.path -and $decisionRun.manifest_path -eq $candidateRun.manifest_path -and $decisionRun.manifest_sha256 -eq $candidateRun.manifest_sha256) "Run final du candidat different de la decision QA : $resref / $($candidate.area)"
                }
            }
            $sourceRunText = (@($sourceRunPaths | Sort-Object -Unique) -join ';')
        }
        Require (-not [string]::IsNullOrWhiteSpace($sourceRunText)) "Provenance de run source absente : $($candidate.area)"

        $destinationRoot = "iee-assets/areas/$($candidate.area)"
        $baseSpec = @{
            ComponentId = [int]$candidate.component_id
            ComponentLabel = [string]$candidate.component_label
            PayloadGroup = [string]$candidate.payload_group
            Area = [string]$candidate.area
            SourceRun = $sourceRunText
            Kind = 'area-animation'
            DestinationRoot = $destinationRoot
            Model = "AreaAnimationRuntimeV$registryVersion"
            InstallOrder = [int]$candidate.component_id
            ReplacesComponentOutput = $false
            Scale = 4
        }
        $expectedNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($name in @([string]$candidate.pack_manifest, [string]$candidate.registry)) { [void]$expectedNames.Add($name) }

        $manifestFile = Get-Item -LiteralPath $packManifestPath -ErrorAction Stop
        $result.Add((New-ContentEntry $baseSpec $manifestFile))
        $registryFile = Get-Item -LiteralPath (Join-Path $sourceDirectory ([string]$candidate.registry)) -ErrorAction Stop
        Require ($registryFile.Length -eq [int64]$candidate.registry_bytes) "Taille registre animation invalide : $($candidate.area)"
        Require ((Get-FileHash -LiteralPath $registryFile.FullName -Algorithm SHA256).Hash -eq [string]$candidate.registry_sha256) "Hash registre animation invalide : $($candidate.area)"
        Require ($pack.registry_sha256 -eq [string]$candidate.registry_sha256 -and [int64]$pack.registry_bytes -eq [int64]$candidate.registry_bytes) "Registre de pack animation incoherent : $($candidate.area)"
        $result.Add((New-ContentEntry $baseSpec $registryFile))

        foreach ($resource in @($pack.resources | Sort-Object resref)) {
            $resref = [string]$resource.resref
            $frames = @($resource.frames | Sort-Object frame)
            Require ($frames.Count -eq [int]$resource.frame_count) "Nombre de frames incoherent : $resref"
            $variantIndex = if ($null -ne $resource.PSObject.Properties['variant_index']) { [int]$resource.variant_index } else { 0 }
            $variantSuffix = if ($variantIndex -gt 0) { "-v$variantIndex" } else { '' }
            foreach ($frame in $frames) {
                $expectedName = "AAX4-$resref$variantSuffix-frame$(([int]$frame.frame).ToString('000')).rgba"
                Require ($frame.asset -eq $expectedName) "Nom de frame animation inattendu : $($frame.asset)"
                [void]$expectedNames.Add($expectedName)
                $frameFile = Get-Item -LiteralPath (Join-Path $sourceDirectory $expectedName) -ErrorAction Stop
                Require ($frameFile.Length -eq [int64]$frame.bytes) "Taille de frame animation invalide : $expectedName"
                Require ((Get-FileHash -LiteralPath $frameFile.FullName -Algorithm SHA256).Hash -eq [string]$frame.sha256) "Hash de frame animation invalide : $expectedName"
                $result.Add((New-ContentEntry $baseSpec $frameFile))
            }
        }

        $actualNames = @(Get-ChildItem -LiteralPath $sourceDirectory -File | ForEach-Object Name | Sort-Object)
        Require (-not (Compare-Object (@($expectedNames | Sort-Object)) $actualNames)) "Pack animation contient un fichier non declare ou manque un asset : $($candidate.area)"
    }
    return @($result)
}

$mapSpecs = @(
    @{ ComponentId = 1000; ComponentLabel = 'map-ar0300'; PayloadGroup = 'map-ar0300'; Area = 'AR0300'; SourceRun = 'maps/AR0300/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/AR0300/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 1000 },
    @{ ComponentId = 1000; ComponentLabel = 'map-ar0300'; PayloadGroup = 'map-ar0300'; Area = 'AR0300N'; SourceRun = 'maps/AR0300/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-page4096'; Path = 'maps/AR0300/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-page4096'; InstallOrder = 1000 },
    @{ ComponentId = 1010; ComponentLabel = 'map-ar0400'; PayloadGroup = 'map-ar0400'; Area = 'AR0400'; SourceRun = 'maps/AR0400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-jour/05_build'; Path = 'maps/AR0400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-jour/05_build'; InstallOrder = 1010 },
    @{ ComponentId = 1010; ComponentLabel = 'map-ar0400'; PayloadGroup = 'map-ar0400'; Area = 'AR0400N'; SourceRun = 'maps/AR0400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-nuit/05_build'; Path = 'maps/AR0400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-nuit/05_build'; InstallOrder = 1010 },
    @{ ComponentId = 1020; ComponentLabel = 'map-ar0500'; PayloadGroup = 'map-ar0500'; Area = 'AR0500'; SourceRun = 'maps/AR0500/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/AR0500/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 1020 },
    @{ ComponentId = 1020; ComponentLabel = 'map-ar0500'; PayloadGroup = 'map-ar0500'; Area = 'AR0500N'; SourceRun = 'maps/AR0500/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-page4096'; Path = 'maps/AR0500/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-page4096'; InstallOrder = 1020 },
    @{ ComponentId = 1030; ComponentLabel = 'map-ar0602'; PayloadGroup = 'map-ar0602'; Area = 'AR0602'; SourceRun = 'maps/AR0602/runs/seedvr2-7b-int8-lab-grid-2x5-x4-png-review/05_build/x4-7b-primary-secondary-dxt1-no-cgi-mask'; Path = 'maps/AR0602/runs/seedvr2-7b-int8-lab-grid-2x5-x4-png-review/05_build/x4-7b-primary-secondary-dxt1-no-cgi-mask'; InstallOrder = 1030 },
    @{ ComponentId = 1040; ComponentLabel = 'map-ar0603'; PayloadGroup = 'map-ar0603'; Area = 'AR0603'; SourceRun = 'maps/AR0603/runs/seedvr2-7b-int8-lab-grid-2x4-x4-primary-experimental-wtoil/05_build/x4-7b-primary-secondary-dxt5-global-alpha-feather-1.5-wtoil-stock'; Path = 'maps/AR0603/runs/seedvr2-7b-int8-lab-grid-2x4-x4-primary-experimental-wtoil/05_build/x4-7b-primary-secondary-dxt5-global-alpha-feather-1.5-wtoil-stock'; InstallOrder = 1040 },
    @{ ComponentId = 1050; ComponentLabel = 'map-ar0700'; PayloadGroup = 'map-ar0700'; Area = 'AR0700'; SourceRun = 'maps/AR0700/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/AR0700/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 1050 },
    @{ ComponentId = 1050; ComponentLabel = 'map-ar0700'; PayloadGroup = 'map-ar0700'; Area = 'AR0700N'; SourceRun = 'maps/AR0700/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/AR0700/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 1050 },
    @{ ComponentId = 1060; ComponentLabel = 'map-ar0703'; PayloadGroup = 'map-ar0703'; Area = 'AR0703'; SourceRun = 'maps/AR0703/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4-dxt5-water-bilinear'; Path = 'maps/AR0703/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4-dxt5-water-bilinear'; InstallOrder = 1060 },
    @{ ComponentId = 1070; ComponentLabel = 'map-ar0311'; PayloadGroup = 'map-ar0311'; Area = 'AR0311'; SourceRun = 'maps/AR0311/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0311/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1070 },
    @{ ComponentId = 1080; ComponentLabel = 'map-ar0312'; PayloadGroup = 'map-ar0312'; Area = 'AR0312'; SourceRun = 'maps/AR0312/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0312/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1080 },
    @{ ComponentId = 1090; ComponentLabel = 'map-ar0409'; PayloadGroup = 'map-ar0409'; Area = 'AR0409'; SourceRun = 'maps/AR0409/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0409/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1090 },
    @{ ComponentId = 1100; ComponentLabel = 'map-ar0408'; PayloadGroup = 'map-ar0408'; Area = 'AR0408'; SourceRun = 'maps/AR0408/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0408/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1100 },
    @{ ComponentId = 1110; ComponentLabel = 'map-ar0020'; PayloadGroup = 'map-ar0020'; Area = 'AR0020'; SourceRun = 'maps/AR0020/runs/seedvr2-7b-int8-lab-x4-jour/05_build/x4'; Path = 'maps/AR0020/runs/seedvr2-7b-int8-lab-x4-jour/05_build/x4'; InstallOrder = 1110 },
    @{ ComponentId = 1110; ComponentLabel = 'map-ar0020'; PayloadGroup = 'map-ar0020'; Area = 'AR0020N'; SourceRun = 'maps/AR0020/runs/seedvr2-7b-int8-lab-x4-nuit/05_build/x4'; Path = 'maps/AR0020/runs/seedvr2-7b-int8-lab-x4-nuit/05_build/x4'; InstallOrder = 1110 },
    @{ ComponentId = 1120; ComponentLabel = 'map-ar0800'; PayloadGroup = 'map-ar0800'; Area = 'AR0800'; SourceRun = 'maps/AR0800/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build/x4'; Path = 'maps/AR0800/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build/x4'; InstallOrder = 1120 },
    @{ ComponentId = 1120; ComponentLabel = 'map-ar0800'; PayloadGroup = 'map-ar0800'; Area = 'AR0800N'; SourceRun = 'maps/AR0800/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build/x4'; Path = 'maps/AR0800/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build/x4'; InstallOrder = 1120 },
    @{ ComponentId = 1130; ComponentLabel = 'map-ar0900'; PayloadGroup = 'map-ar0900'; Area = 'AR0900'; SourceRun = 'maps/AR0900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build/x4-water-alpha-antialias-page4096'; Path = 'maps/AR0900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build/x4-water-alpha-antialias-page4096'; InstallOrder = 1130 },
    @{ ComponentId = 1130; ComponentLabel = 'map-ar0900'; PayloadGroup = 'map-ar0900'; Area = 'AR0900N'; SourceRun = 'maps/AR0900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-water-alpha-antialias-page4096'; Path = 'maps/AR0900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-water-alpha-antialias-page4096'; InstallOrder = 1130 },
    @{ ComponentId = 1140; ComponentLabel = 'map-ar1000'; PayloadGroup = 'map-ar1000'; Area = 'AR1000'; SourceRun = 'maps/AR1000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build/x4'; Path = 'maps/AR1000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build/x4'; InstallOrder = 1140 },
    @{ ComponentId = 1140; ComponentLabel = 'map-ar1000'; PayloadGroup = 'map-ar1000'; Area = 'AR1000N'; SourceRun = 'maps/AR1000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-page4096'; Path = 'maps/AR1000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build/x4-page4096'; InstallOrder = 1140 },
    @{ ComponentId = 1160; ComponentLabel = 'map-ar0418'; PayloadGroup = 'map-ar0418'; Area = 'AR0418'; SourceRun = 'maps/AR0418/runs/upscale-01/05_build'; Path = 'maps/AR0418/runs/upscale-01/05_build'; InstallOrder = 1160 },
    @{ ComponentId = 1170; ComponentLabel = 'map-ar0701'; PayloadGroup = 'map-ar0701'; Area = 'AR0701'; SourceRun = 'maps/AR0701/runs/upscale-01/05_build'; Path = 'maps/AR0701/runs/upscale-01/05_build'; InstallOrder = 1170 },
    @{ ComponentId = 1180; ComponentLabel = 'map-ar0705'; PayloadGroup = 'map-ar0705'; Area = 'AR0705'; SourceRun = 'maps/AR0705/runs/upscale-01/05_build'; Path = 'maps/AR0705/runs/upscale-01/05_build'; InstallOrder = 1180 },
    @{ ComponentId = 1190; ComponentLabel = 'map-ar0711'; PayloadGroup = 'map-ar0711'; Area = 'AR0711'; SourceRun = 'maps/AR0711/runs/upscale-01/05_build'; Path = 'maps/AR0711/runs/upscale-01/05_build'; InstallOrder = 1190 },
    @{ ComponentId = 1200; ComponentLabel = 'map-ar1300'; PayloadGroup = 'map-ar1300'; Area = 'AR1300'; SourceRun = 'maps/AR1300/runs/seedvr2-7b-x4-grid-2x5-preview/05_build'; Path = 'maps/AR1300/runs/seedvr2-7b-x4-grid-2x5-preview/05_build'; InstallOrder = 1200 },
    @{ ComponentId = 1210; ComponentLabel = 'map-ar0406'; PayloadGroup = 'map-ar0406'; Area = 'AR0406'; SourceRun = 'maps/AR0406/runs/seedvr2-7b-int8-lab-grid-2x4-x4-main-test/05_build/x4-7b-primary-secondary-dxt1-official'; Path = 'maps/AR0406/runs/seedvr2-7b-int8-lab-grid-2x4-x4-main-test/05_build/x4-7b-primary-secondary-dxt1-official'; InstallOrder = 1210 },
    @{ ComponentId = 1220; ComponentLabel = 'map-ar0401'; PayloadGroup = 'map-ar0401'; Area = 'AR0401'; SourceRun = 'maps/AR0401/runs/upscale-01/05_build'; Path = 'maps/AR0401/runs/upscale-01/05_build'; InstallOrder = 1220 },
    @{ ComponentId = 1230; ComponentLabel = 'map-ar0402'; PayloadGroup = 'map-ar0402'; Area = 'AR0402'; SourceRun = 'maps/AR0402/runs/upscale-01/05_build'; Path = 'maps/AR0402/runs/upscale-01/05_build'; InstallOrder = 1230 },
    @{ ComponentId = 1240; ComponentLabel = 'map-ar0403'; PayloadGroup = 'map-ar0403'; Area = 'AR0403'; SourceRun = 'maps/AR0403/runs/upscale-01/05_build'; Path = 'maps/AR0403/runs/upscale-01/05_build'; InstallOrder = 1240 },
    @{ ComponentId = 1250; ComponentLabel = 'map-ar0405'; PayloadGroup = 'map-ar0405'; Area = 'AR0405'; SourceRun = 'maps/AR0405/runs/upscale-01/05_build'; Path = 'maps/AR0405/runs/upscale-01/05_build'; InstallOrder = 1250 },
    @{ ComponentId = 1260; ComponentLabel = 'map-ar0417'; PayloadGroup = 'map-ar0417'; Area = 'AR0417'; SourceRun = 'maps/AR0417/runs/upscale-01/05_build'; Path = 'maps/AR0417/runs/upscale-01/05_build'; InstallOrder = 1260 },
    @{ ComponentId = 1270; ComponentLabel = 'map-ar0410'; PayloadGroup = 'map-ar0410'; Area = 'AR0410'; SourceRun = 'maps/AR0410/runs/upscale-01/05_build'; Path = 'maps/AR0410/runs/upscale-01/05_build'; InstallOrder = 1270 },
    @{ ComponentId = 1280; ComponentLabel = 'map-ar0411'; PayloadGroup = 'map-ar0411'; Area = 'AR0411'; SourceRun = 'maps/AR0411/runs/upscale-01/05_build'; Path = 'maps/AR0411/runs/upscale-01/05_build'; InstallOrder = 1280 },
    @{ ComponentId = 1290; ComponentLabel = 'map-ar0412'; PayloadGroup = 'map-ar0412'; Area = 'AR0412'; SourceRun = 'maps/AR0412/runs/upscale-01/05_build'; Path = 'maps/AR0412/runs/upscale-01/05_build'; InstallOrder = 1290 },
    @{ ComponentId = 1300; ComponentLabel = 'map-ar0413'; PayloadGroup = 'map-ar0413'; Area = 'AR0413'; SourceRun = 'maps/AR0413/runs/wtoil-family-definitive/05_build/x4-alpha-release-installed'; Path = 'maps/AR0413/runs/wtoil-family-definitive/05_build/x4-alpha-release-installed'; InstallOrder = 1300 },
    @{ ComponentId = 1310; ComponentLabel = 'map-ar0414'; PayloadGroup = 'map-ar0414'; Area = 'AR0414'; SourceRun = 'maps/AR0414/runs/upscale-01/05_build'; Path = 'maps/AR0414/runs/upscale-01/05_build'; InstallOrder = 1310 },
    @{ ComponentId = 1320; ComponentLabel = 'map-ar0420'; PayloadGroup = 'map-ar0420'; Area = 'AR0420'; SourceRun = 'maps/AR0420/runs/upscale-01/05_build'; Path = 'maps/AR0420/runs/upscale-01/05_build'; InstallOrder = 1320 },
    @{ ComponentId = 1330; ComponentLabel = 'map-ar1301'; PayloadGroup = 'map-ar1301'; Area = 'AR1301'; SourceRun = 'maps/AR1301/runs/seedvr2-7b-x4-grid-2x2/05_build'; Path = 'maps/AR1301/runs/seedvr2-7b-x4-grid-2x2/05_build'; InstallOrder = 1330 },
    @{ ComponentId = 1340; ComponentLabel = 'map-ar1302'; PayloadGroup = 'map-ar1302'; Area = 'AR1302'; SourceRun = 'maps/AR1302/runs/seedvr2-7b-x4-grid-2x2/05_build'; Path = 'maps/AR1302/runs/seedvr2-7b-x4-grid-2x2/05_build'; InstallOrder = 1340 },
    @{ ComponentId = 1350; ComponentLabel = 'map-ar1303'; PayloadGroup = 'map-ar1303'; Area = 'AR1303'; SourceRun = 'maps/AR1303/runs/seedvr2-7b-x4-grid-2x2/05_build'; Path = 'maps/AR1303/runs/seedvr2-7b-x4-grid-2x2/05_build'; InstallOrder = 1350 },
    @{ ComponentId = 1360; ComponentLabel = 'map-ar1304'; PayloadGroup = 'map-ar1304'; Area = 'AR1304'; SourceRun = 'maps/AR1304/runs/seedvr2-7b-x4-grid-2x5/05_build'; Path = 'maps/AR1304/runs/seedvr2-7b-x4-grid-2x5/05_build'; InstallOrder = 1360 },
    @{ ComponentId = 1370; ComponentLabel = 'map-ar1001'; PayloadGroup = 'map-ar1001'; Area = 'AR1001'; SourceRun = 'maps/AR1001/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR1001/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1370 },
    @{ ComponentId = 1380; ComponentLabel = 'map-ar1002'; PayloadGroup = 'map-ar1002'; Area = 'AR1002'; SourceRun = 'maps/AR1002/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR1002/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1380 },
    @{ ComponentId = 1390; ComponentLabel = 'map-ar1003'; PayloadGroup = 'map-ar1003'; Area = 'AR1003'; SourceRun = 'maps/AR1003/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR1003/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1390 },
    @{ ComponentId = 1400; ComponentLabel = 'map-ar1004'; PayloadGroup = 'map-ar1004'; Area = 'AR1004'; SourceRun = 'maps/AR1004/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR1004/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1400 },
    @{ ComponentId = 1410; ComponentLabel = 'map-ar1005'; PayloadGroup = 'map-ar1005'; Area = 'AR1005'; SourceRun = 'maps/AR1005/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR1005/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1410 },
    @{ ComponentId = 1420; ComponentLabel = 'map-ar1008'; PayloadGroup = 'map-ar1008'; Area = 'AR1008'; SourceRun = 'maps/AR1008/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR1008/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1420 },
    @{ ComponentId = 1430; ComponentLabel = 'map-ar1010'; PayloadGroup = 'map-ar1010'; Area = 'AR1010'; SourceRun = 'maps/AR1010/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR1010/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1430 },
    @{ ComponentId = 1440; ComponentLabel = 'map-ar0501'; PayloadGroup = 'map-ar0501'; Area = 'AR0501'; SourceRun = 'maps/AR0501/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0501/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1440 },
    @{ ComponentId = 1450; ComponentLabel = 'map-ar0502'; PayloadGroup = 'map-ar0502'; Area = 'AR0502'; SourceRun = 'maps/AR0502/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0502/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1450 },
    @{ ComponentId = 1460; ComponentLabel = 'map-ar0504'; PayloadGroup = 'map-ar0504'; Area = 'AR0504'; SourceRun = 'maps/AR0504/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build/x4'; Path = 'maps/AR0504/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build/x4'; InstallOrder = 1460 },
    @{ ComponentId = 1470; ComponentLabel = 'map-ar0505'; PayloadGroup = 'map-ar0505'; Area = 'AR0505'; SourceRun = 'maps/AR0505/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build/x4'; Path = 'maps/AR0505/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build/x4'; InstallOrder = 1470 },
    @{ ComponentId = 1480; ComponentLabel = 'map-ar0506'; PayloadGroup = 'map-ar0506'; Area = 'AR0506'; SourceRun = 'maps/AR0506/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0506/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1480 },
    @{ ComponentId = 1490; ComponentLabel = 'map-ar0507'; PayloadGroup = 'map-ar0507'; Area = 'AR0507'; SourceRun = 'maps/AR0507/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0507/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1490 },
    @{ ComponentId = 1500; ComponentLabel = 'map-ar0508'; PayloadGroup = 'map-ar0508'; Area = 'AR0508'; SourceRun = 'maps/AR0508/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0508/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1500 },
    @{ ComponentId = 1510; ComponentLabel = 'map-ar0509'; PayloadGroup = 'map-ar0509'; Area = 'AR0509'; SourceRun = 'maps/AR0509/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0509/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1510 },
    @{ ComponentId = 1520; ComponentLabel = 'map-ar0510'; PayloadGroup = 'map-ar0510'; Area = 'AR0510'; SourceRun = 'maps/AR0510/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0510/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1520 },
    @{ ComponentId = 1530; ComponentLabel = 'map-ar0511'; PayloadGroup = 'map-ar0511'; Area = 'AR0511'; SourceRun = 'maps/AR0511/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0511/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1530 },
    @{ ComponentId = 1540; ComponentLabel = 'map-ar0512'; PayloadGroup = 'map-ar0512'; Area = 'AR0512'; SourceRun = 'maps/AR0512/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0512/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1540 },
    @{ ComponentId = 1550; ComponentLabel = 'map-ar0513'; PayloadGroup = 'map-ar0513'; Area = 'AR0513'; SourceRun = 'maps/AR0513/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0513/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1550 },
    @{ ComponentId = 1560; ComponentLabel = 'map-ar0514'; PayloadGroup = 'map-ar0514'; Area = 'AR0514'; SourceRun = 'maps/AR0514/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0514/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1560 },
    @{ ComponentId = 1570; ComponentLabel = 'map-ar0515'; PayloadGroup = 'map-ar0515'; Area = 'AR0515'; SourceRun = 'maps/AR0515/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0515/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1570 },
    @{ ComponentId = 1580; ComponentLabel = 'map-ar0516'; PayloadGroup = 'map-ar0516'; Area = 'AR0516'; SourceRun = 'maps/AR0516/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build/x4'; Path = 'maps/AR0516/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build/x4'; InstallOrder = 1580 },
    @{ ComponentId = 1590; ComponentLabel = 'map-ar0517'; PayloadGroup = 'map-ar0517'; Area = 'AR0517'; SourceRun = 'maps/AR0517/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0517/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1590 },
    @{ ComponentId = 1600; ComponentLabel = 'map-ar0526'; PayloadGroup = 'map-ar0526'; Area = 'AR0526'; SourceRun = 'maps/AR0526/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0526/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1600 },
    @{ ComponentId = 1610; ComponentLabel = 'map-ar0527'; PayloadGroup = 'map-ar0527'; Area = 'AR0527'; SourceRun = 'maps/AR0527/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0527/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1610 },
    @{ ComponentId = 1620; ComponentLabel = 'map-ar0528'; PayloadGroup = 'map-ar0528'; Area = 'AR0528'; SourceRun = 'maps/AR0528/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0528/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1620 },
    @{ ComponentId = 1630; ComponentLabel = 'map-ar0529'; PayloadGroup = 'map-ar0529'; Area = 'AR0529'; SourceRun = 'maps/AR0529/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0529/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1630 },
    @{ ComponentId = 1640; ComponentLabel = 'map-ar0530'; PayloadGroup = 'map-ar0530'; Area = 'AR0530'; SourceRun = 'maps/AR0530/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0530/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1640 },
    @{ ComponentId = 1650; ComponentLabel = 'map-ar0531'; PayloadGroup = 'map-ar0531'; Area = 'AR0531'; SourceRun = 'maps/AR0531/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0531/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1650 },
    @{ ComponentId = 1660; ComponentLabel = 'map-ar0301'; PayloadGroup = 'map-ar0301'; Area = 'AR0301'; SourceRun = 'maps/AR0301/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0301/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1660 },
    @{ ComponentId = 1670; ComponentLabel = 'map-ar0302'; PayloadGroup = 'map-ar0302'; Area = 'AR0302'; SourceRun = 'maps/AR0302/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0302/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1670 },
    @{ ComponentId = 1680; ComponentLabel = 'map-ar0303'; PayloadGroup = 'map-ar0303'; Area = 'AR0303'; SourceRun = 'maps/AR0303/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0303/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1680 },
    @{ ComponentId = 1690; ComponentLabel = 'map-ar0305'; PayloadGroup = 'map-ar0305'; Area = 'AR0305'; SourceRun = 'maps/AR0305/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0305/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1690 },
    @{ ComponentId = 1700; ComponentLabel = 'map-ar0306'; PayloadGroup = 'map-ar0306'; Area = 'AR0306'; SourceRun = 'maps/AR0306/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0306/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1700 },
    @{ ComponentId = 1710; ComponentLabel = 'map-ar0307'; PayloadGroup = 'map-ar0307'; Area = 'AR0307'; SourceRun = 'maps/AR0307/runs/seedvr2-7b-int8-lab-grid-2x5-x4/05_build/x4'; Path = 'maps/AR0307/runs/seedvr2-7b-int8-lab-grid-2x5-x4/05_build/x4'; InstallOrder = 1710 },
    @{ ComponentId = 1720; ComponentLabel = 'map-ar0308'; PayloadGroup = 'map-ar0308'; Area = 'AR0308'; SourceRun = 'maps/AR0308/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0308/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1720 },
    @{ ComponentId = 1730; ComponentLabel = 'map-ar0309'; PayloadGroup = 'map-ar0309'; Area = 'AR0309'; SourceRun = 'maps/AR0309/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0309/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 1730 },
    @{ ComponentId = 1740; ComponentLabel = 'map-ar0310'; PayloadGroup = 'map-ar0310'; Area = 'AR0310'; SourceRun = 'maps/AR0310/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0310/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1740 },
    @{ ComponentId = 1750; ComponentLabel = 'map-ar0313'; PayloadGroup = 'map-ar0313'; Area = 'AR0313'; SourceRun = 'maps/AR0313/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0313/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1750 },
    @{ ComponentId = 1760; ComponentLabel = 'map-ar0314'; PayloadGroup = 'map-ar0314'; Area = 'AR0314'; SourceRun = 'maps/AR0314/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0314/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1760 },
    @{ ComponentId = 1770; ComponentLabel = 'map-ar0315'; PayloadGroup = 'map-ar0315'; Area = 'AR0315'; SourceRun = 'maps/AR0315/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0315/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1770 },
    @{ ComponentId = 1780; ComponentLabel = 'map-ar0316'; PayloadGroup = 'map-ar0316'; Area = 'AR0316'; SourceRun = 'maps/AR0316/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0316/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1780 },
    @{ ComponentId = 1790; ComponentLabel = 'map-ar0317'; PayloadGroup = 'map-ar0317'; Area = 'AR0317'; SourceRun = 'maps/AR0317/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0317/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1790 },
    @{ ComponentId = 1800; ComponentLabel = 'map-ar0318'; PayloadGroup = 'map-ar0318'; Area = 'AR0318'; SourceRun = 'maps/AR0318/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0318/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1800 },
    @{ ComponentId = 1810; ComponentLabel = 'map-ar0319'; PayloadGroup = 'map-ar0319'; Area = 'AR0319'; SourceRun = 'maps/AR0319/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0319/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1810 },
    @{ ComponentId = 1820; ComponentLabel = 'map-ar0325'; PayloadGroup = 'map-ar0325'; Area = 'AR0325'; SourceRun = 'maps/AR0325/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0325/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1820 },
    @{ ComponentId = 1830; ComponentLabel = 'map-ar0330'; PayloadGroup = 'map-ar0330'; Area = 'AR0330'; SourceRun = 'maps/AR0330/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0330/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1830 },
    @{ ComponentId = 1840; ComponentLabel = 'map-ar0331'; PayloadGroup = 'map-ar0331'; Area = 'AR0331'; SourceRun = 'maps/AR0331/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0331/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1840 },
    @{ ComponentId = 1850; ComponentLabel = 'map-ar0332'; PayloadGroup = 'map-ar0332'; Area = 'AR0332'; SourceRun = 'maps/AR0332/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0332/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1850 },
    @{ ComponentId = 1860; ComponentLabel = 'map-ar0334'; PayloadGroup = 'map-ar0334'; Area = 'AR0334'; SourceRun = 'maps/AR0334/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0334/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1860 },
    @{ ComponentId = 1870; ComponentLabel = 'map-ar0335'; PayloadGroup = 'map-ar0335'; Area = 'AR0335'; SourceRun = 'maps/AR0335/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0335/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1870 },
    @{ ComponentId = 1880; ComponentLabel = 'map-ar0407'; PayloadGroup = 'map-ar0407'; Area = 'AR0407'; SourceRun = 'maps/AR0407/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0407/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1880 },
    @{ ComponentId = 1890; ComponentLabel = 'map-ar0415'; PayloadGroup = 'map-ar0415'; Area = 'AR0415'; SourceRun = 'maps/AR0415/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0415/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1890 },
    @{ ComponentId = 1900; ComponentLabel = 'map-ar0416'; PayloadGroup = 'map-ar0416'; Area = 'AR0416'; SourceRun = 'maps/AR0416/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0416/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1900 },
    @{ ComponentId = 1910; ComponentLabel = 'map-ar0503'; PayloadGroup = 'map-ar0503'; Area = 'AR0503'; SourceRun = 'maps/AR0503/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0503/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1910 },
    @{ ComponentId = 1920; ComponentLabel = 'map-ar0304'; PayloadGroup = 'map-ar0304'; Area = 'AR0304'; SourceRun = 'maps/AR0304/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0304/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1920 },
    @{ ComponentId = 1930; ComponentLabel = 'map-ar0021'; PayloadGroup = 'map-ar0021'; Area = 'AR0021'; SourceRun = 'maps/AR0021/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0021/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1930 },
    @{ ComponentId = 1940; ComponentLabel = 'map-ar0022'; PayloadGroup = 'map-ar0022'; Area = 'AR0022'; SourceRun = 'maps/AR0022/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0022/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1940 },
    @{ ComponentId = 1950; ComponentLabel = 'map-ar0082'; PayloadGroup = 'map-ar0082'; Area = 'AR0082'; SourceRun = 'maps/AR0082/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0082/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1950 },
    @{ ComponentId = 1960; ComponentLabel = 'map-ar0804'; PayloadGroup = 'map-ar0804'; Area = 'AR0804'; SourceRun = 'maps/AR0804/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0804/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1960 },
    @{ ComponentId = 1970; ComponentLabel = 'map-ar0805'; PayloadGroup = 'map-ar0805'; Area = 'AR0805'; SourceRun = 'maps/AR0805/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0805/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1970 },
    @{ ComponentId = 1980; ComponentLabel = 'map-ar0806'; PayloadGroup = 'map-ar0806'; Area = 'AR0806'; SourceRun = 'maps/AR0806/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0806/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1980 },
    @{ ComponentId = 1990; ComponentLabel = 'map-ar0807'; PayloadGroup = 'map-ar0807'; Area = 'AR0807'; SourceRun = 'maps/AR0807/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0807/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 1990 },
    @{ ComponentId = 2000; ComponentLabel = 'map-ar0811'; PayloadGroup = 'map-ar0811'; Area = 'AR0811'; SourceRun = 'maps/AR0811/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0811/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2000 },
    @{ ComponentId = 2010; ComponentLabel = 'map-oh7000'; PayloadGroup = 'map-oh7000'; Area = 'OH7000'; SourceRun = 'maps/OH7000/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; Path = 'maps/OH7000/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; InstallOrder = 2010 },
    @{ ComponentId = 2020; ComponentLabel = 'map-ar0803'; PayloadGroup = 'map-ar0803'; Area = 'AR0803'; SourceRun = 'maps/AR0803/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0803/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 2020 },
    @{ ComponentId = 2030; ComponentLabel = 'map-ar0802'; PayloadGroup = 'map-ar0802'; Area = 'AR0802'; SourceRun = 'maps/AR0802/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; Path = 'maps/AR0802/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; InstallOrder = 2030 },
    @{ ComponentId = 2040; ComponentLabel = 'map-ar0801'; PayloadGroup = 'map-ar0801'; Area = 'AR0801'; SourceRun = 'maps/AR0801/runs/seedvr2-7b-int8-lab-split-grid-2x5-x4/05_build/x4'; Path = 'maps/AR0801/runs/seedvr2-7b-int8-lab-split-grid-2x5-x4/05_build/x4'; InstallOrder = 2040 },
    @{ ComponentId = 2050; ComponentLabel = 'map-ar0710'; PayloadGroup = 'map-ar0710'; Area = 'AR0710'; SourceRun = 'maps/AR0710/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0710/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2050 },
    @{ ComponentId = 2060; ComponentLabel = 'map-ar0713'; PayloadGroup = 'map-ar0713'; Area = 'AR0713'; SourceRun = 'maps/AR0713/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0713/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2060 },
    @{ ComponentId = 2070; ComponentLabel = 'map-oh6300'; PayloadGroup = 'map-oh6300'; Area = 'OH6300'; SourceRun = 'maps/OH6300/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; Path = 'maps/OH6300/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; InstallOrder = 2070 },
    @{ ComponentId = 2080; ComponentLabel = 'map-ar0203'; PayloadGroup = 'map-ar0203'; Area = 'AR0203'; SourceRun = 'maps/AR0203/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0203/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2080 },
    @{ ComponentId = 2090; ComponentLabel = 'map-ar0206'; PayloadGroup = 'map-ar0206'; Area = 'AR0206'; SourceRun = 'maps/AR0206/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; Path = 'maps/AR0206/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4'; InstallOrder = 2090 },
    @{ ComponentId = 2100; ComponentLabel = 'map-ar0201'; PayloadGroup = 'map-ar0201'; Area = 'AR0201'; SourceRun = 'maps/AR0201/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; Path = 'maps/AR0201/runs/seedvr2-7b-int8-lab-split-grid-2x2-x4/05_build/x4'; InstallOrder = 2100 },
    @{ ComponentId = 2110; ComponentLabel = 'map-ar0205'; PayloadGroup = 'map-ar0205'; Area = 'AR0205'; SourceRun = 'maps/AR0205/runs/seedvr2-7b-int8-lab-split-grid-2x3-x4/05_build/x4'; Path = 'maps/AR0205/runs/seedvr2-7b-int8-lab-split-grid-2x3-x4/05_build/x4'; InstallOrder = 2110 },
    @{ ComponentId = 2120; ComponentLabel = 'map-ar0202'; PayloadGroup = 'map-ar0202'; Area = 'AR0202'; SourceRun = 'maps/AR0202/runs/seedvr2-7b-int8-lab-split-grid-2x3-x4/05_build/x4'; Path = 'maps/AR0202/runs/seedvr2-7b-int8-lab-split-grid-2x3-x4/05_build/x4'; InstallOrder = 2120 },
    @{ ComponentId = 2130; ComponentLabel = 'map-ar0204'; PayloadGroup = 'map-ar0204'; Area = 'AR0204'; SourceRun = 'maps/AR0204/runs/seedvr2-7b-int8-lab-split-grid-2x5-x4/05_build/x4'; Path = 'maps/AR0204/runs/seedvr2-7b-int8-lab-split-grid-2x5-x4/05_build/x4'; InstallOrder = 2130 },
    @{ ComponentId = 2140; ComponentLabel = 'map-ar0600'; PayloadGroup = 'map-ar0600'; Area = 'AR0600'; SourceRun = 'maps/AR0600/runs/seedvr2-7b-int8-lab-grid-2x2-x4-png-review/05_build/x4-7b-primary-dxt1-official'; Path = 'maps/AR0600/runs/seedvr2-7b-int8-lab-grid-2x2-x4-png-review/05_build/x4-7b-primary-dxt1-official'; InstallOrder = 2140 },
    @{ ComponentId = 2150; ComponentLabel = 'map-ar0601'; PayloadGroup = 'map-ar0601'; Area = 'AR0601'; SourceRun = 'maps/AR0601/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4-7b-primary-dxt1-official'; Path = 'maps/AR0601/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build/x4-7b-primary-dxt1-official'; InstallOrder = 2150 },
    @{ ComponentId = 2160; ComponentLabel = 'map-ar0604'; PayloadGroup = 'map-ar0604'; Area = 'AR0604'; SourceRun = 'maps/AR0604/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-secondary-dxt5-wtswam-stock-feather-1.25'; Path = 'maps/AR0604/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-secondary-dxt5-wtswam-stock-feather-1.25'; InstallOrder = 2160 },
    @{ ComponentId = 2170; ComponentLabel = 'map-ar0605'; PayloadGroup = 'map-ar0605'; Area = 'AR0605'; SourceRun = 'maps/AR0605/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-dxt1-official'; Path = 'maps/AR0605/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-dxt1-official'; InstallOrder = 2170 },
    @{ ComponentId = 2180; ComponentLabel = 'map-ar0606'; PayloadGroup = 'map-ar0606'; Area = 'AR0606'; SourceRun = 'maps/AR0606/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-dxt1-official'; Path = 'maps/AR0606/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-dxt1-official'; InstallOrder = 2180 },
    @{ ComponentId = 2190; ComponentLabel = 'map-ar0607'; PayloadGroup = 'map-ar0607'; Area = 'AR0607'; SourceRun = 'maps/AR0607/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-dxt1-official'; Path = 'maps/AR0607/runs/seedvr2-7b-int8-lab-direct-x4-png-review/05_build/x4-7b-primary-dxt1-official'; InstallOrder = 2190 },
    @{ ComponentId = 2200; ComponentLabel = 'map-ar0702'; PayloadGroup = 'map-ar0702'; Area = 'AR0702'; SourceRun = 'maps/AR0702/runs/seedvr2-7b-int8-lab-direct-x4-test/05_build/x4-test'; Path = 'maps/AR0702/runs/seedvr2-7b-int8-lab-direct-x4-test/05_build/x4-test'; InstallOrder = 2200 },
    @{ ComponentId = 2210; ComponentLabel = 'map-ar0704'; PayloadGroup = 'map-ar0704'; Area = 'AR0704'; SourceRun = 'maps/AR0704/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0704/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2210 },
    @{ ComponentId = 2220; ComponentLabel = 'map-ar0706'; PayloadGroup = 'map-ar0706'; Area = 'AR0706'; SourceRun = 'maps/AR0706/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0706/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2220 },
    @{ ComponentId = 2230; ComponentLabel = 'map-ar0707'; PayloadGroup = 'map-ar0707'; Area = 'AR0707'; SourceRun = 'maps/AR0707/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0707/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2230 },
    @{ ComponentId = 2240; ComponentLabel = 'map-ar0708'; PayloadGroup = 'map-ar0708'; Area = 'AR0708'; SourceRun = 'maps/AR0708/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0708/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2240 },
    @{ ComponentId = 2250; ComponentLabel = 'map-ar0709'; PayloadGroup = 'map-ar0709'; Area = 'AR0709'; SourceRun = 'maps/AR0709/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0709/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2250 },
    @{ ComponentId = 2260; ComponentLabel = 'map-ar0712'; PayloadGroup = 'map-ar0712'; Area = 'AR0712'; SourceRun = 'maps/AR0712/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; Path = 'maps/AR0712/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4'; InstallOrder = 2260 },
    @{ ComponentId = 2270; ComponentLabel = 'map-ar0901'; PayloadGroup = 'map-ar0901'; Area = 'AR0901'; SourceRun = 'maps/AR0901/runs/upscale-01/05_build'; Path = 'maps/AR0901/runs/upscale-01/05_build'; InstallOrder = 2270 },
    @{ ComponentId = 2280; ComponentLabel = 'map-ar0902'; PayloadGroup = 'map-ar0902'; Area = 'AR0902'; SourceRun = 'maps/AR0902/runs/upscale-01/05_build'; Path = 'maps/AR0902/runs/upscale-01/05_build'; InstallOrder = 2280 },
    @{ ComponentId = 2290; ComponentLabel = 'map-ar0903'; PayloadGroup = 'map-ar0903'; Area = 'AR0903'; SourceRun = 'maps/AR0903/runs/upscale-01/05_build'; Path = 'maps/AR0903/runs/upscale-01/05_build'; InstallOrder = 2290 },
    @{ ComponentId = 2300; ComponentLabel = 'map-ar0904'; PayloadGroup = 'map-ar0904'; Area = 'AR0904'; SourceRun = 'maps/AR0904/runs/upscale-01/05_build'; Path = 'maps/AR0904/runs/upscale-01/05_build'; InstallOrder = 2300 },
    @{ ComponentId = 2310; ComponentLabel = 'map-ar0905'; PayloadGroup = 'map-ar0905'; Area = 'AR0905'; SourceRun = 'maps/AR0905/runs/upscale-01/05_build'; Path = 'maps/AR0905/runs/upscale-01/05_build'; InstallOrder = 2310 },
    @{ ComponentId = 2320; ComponentLabel = 'map-ar0906'; PayloadGroup = 'map-ar0906'; Area = 'AR0906'; SourceRun = 'maps/AR0906/runs/upscale-01/05_build'; Path = 'maps/AR0906/runs/upscale-01/05_build'; InstallOrder = 2320 },
    @{ ComponentId = 2330; ComponentLabel = 'map-ar0907'; PayloadGroup = 'map-ar0907'; Area = 'AR0907'; SourceRun = 'maps/AR0907/runs/upscale-01/05_build'; Path = 'maps/AR0907/runs/upscale-01/05_build'; InstallOrder = 2330 },
    @{ ComponentId = 2340; ComponentLabel = 'map-oh5000'; PayloadGroup = 'map-oh5000'; Area = 'OH5000'; SourceRun = 'maps/OH5000/runs/upscale-01/05_build'; Path = 'maps/OH5000/runs/upscale-01/05_build'; InstallOrder = 2340 },
    @{ ComponentId = 2350; ComponentLabel = 'map-ar0012'; PayloadGroup = 'map-ar0012'; Area = 'AR0012'; SourceRun = 'maps/AR0012/runs/upscale-01/05_build'; Path = 'maps/AR0012/runs/upscale-01/05_build'; InstallOrder = 2350 },
    @{ ComponentId = 2360; ComponentLabel = 'map-ar0013'; PayloadGroup = 'map-ar0013'; Area = 'AR0013'; SourceRun = 'maps/AR0013/runs/upscale-01/05_build'; Path = 'maps/AR0013/runs/upscale-01/05_build'; InstallOrder = 2360 },
    @{ ComponentId = 2370; ComponentLabel = 'map-ar0014'; PayloadGroup = 'map-ar0014'; Area = 'AR0014'; SourceRun = 'maps/AR0014/runs/upscale-01/05_build'; Path = 'maps/AR0014/runs/upscale-01/05_build'; InstallOrder = 2370 },
    @{ ComponentId = 2380; ComponentLabel = 'map-ar0015'; PayloadGroup = 'map-ar0015'; Area = 'AR0015'; SourceRun = 'maps/AR0015/runs/upscale-01/05_build'; Path = 'maps/AR0015/runs/upscale-01/05_build'; InstallOrder = 2380 },
    @{ ComponentId = 2390; ComponentLabel = 'map-ar0018'; PayloadGroup = 'map-ar0018'; Area = 'AR0018'; SourceRun = 'maps/AR0018/runs/upscale-01/05_build'; Path = 'maps/AR0018/runs/upscale-01/05_build'; InstallOrder = 2390 },
    @{ ComponentId = 2400; ComponentLabel = 'map-ar0041'; PayloadGroup = 'map-ar0041'; Area = 'AR0041'; SourceRun = 'maps/AR0041/runs/upscale-01-jour/05_build'; Path = 'maps/AR0041/runs/upscale-01-jour/05_build'; InstallOrder = 2400 },
    @{ ComponentId = 2400; ComponentLabel = 'map-ar0041'; PayloadGroup = 'map-ar0041'; Area = 'AR0041N'; SourceRun = 'maps/AR0041/runs/upscale-01-nuit/05_build'; Path = 'maps/AR0041/runs/upscale-01-nuit/05_build'; InstallOrder = 2400 },
    @{ ComponentId = 2410; ComponentLabel = 'map-ar0042'; PayloadGroup = 'map-ar0042'; Area = 'AR0042'; SourceRun = 'maps/AR0042/runs/upscale-01/05_build'; Path = 'maps/AR0042/runs/upscale-01/05_build'; InstallOrder = 2410 },
    @{ ComponentId = 2420; ComponentLabel = 'map-ar0043'; PayloadGroup = 'map-ar0043'; Area = 'AR0043'; SourceRun = 'maps/AR0043/runs/upscale-01/05_build'; Path = 'maps/AR0043/runs/upscale-01/05_build'; InstallOrder = 2420 },
    @{ ComponentId = 2430; ComponentLabel = 'map-ar0044'; PayloadGroup = 'map-ar0044'; Area = 'AR0044'; SourceRun = 'maps/AR0044/runs/upscale-01/05_build'; Path = 'maps/AR0044/runs/upscale-01/05_build'; InstallOrder = 2430 },
    @{ ComponentId = 2440; ComponentLabel = 'map-ar0045'; PayloadGroup = 'map-ar0045'; Area = 'AR0045'; SourceRun = 'maps/AR0045/runs/upscale-01-jour/05_build'; Path = 'maps/AR0045/runs/upscale-01-jour/05_build'; InstallOrder = 2440 },
    @{ ComponentId = 2440; ComponentLabel = 'map-ar0045'; PayloadGroup = 'map-ar0045'; Area = 'AR0045N'; SourceRun = 'maps/AR0045/runs/upscale-01-nuit/05_build'; Path = 'maps/AR0045/runs/upscale-01-nuit/05_build'; InstallOrder = 2440 },
    @{ ComponentId = 2450; ComponentLabel = 'map-ar0069'; PayloadGroup = 'map-ar0069'; Area = 'AR0069'; SourceRun = 'maps/AR0069/runs/upscale-01/05_build'; Path = 'maps/AR0069/runs/upscale-01/05_build'; InstallOrder = 2450 },
    @{ ComponentId = 2460; ComponentLabel = 'map-ar0070'; PayloadGroup = 'map-ar0070'; Area = 'AR0070'; SourceRun = 'maps/AR0070/runs/upscale-01/05_build'; Path = 'maps/AR0070/runs/upscale-01/05_build'; InstallOrder = 2460 },
    @{ ComponentId = 2470; ComponentLabel = 'map-ar0071'; PayloadGroup = 'map-ar0071'; Area = 'AR0071'; SourceRun = 'maps/AR0071/runs/upscale-01/05_build'; Path = 'maps/AR0071/runs/upscale-01/05_build'; InstallOrder = 2470 },
    @{ ComponentId = 2480; ComponentLabel = 'map-ar0072'; PayloadGroup = 'map-ar0072'; Area = 'AR0072'; SourceRun = 'maps/AR0072/runs/upscale-01/05_build'; Path = 'maps/AR0072/runs/upscale-01/05_build'; InstallOrder = 2480 },
    @{ ComponentId = 2490; ComponentLabel = 'map-ar0016'; PayloadGroup = 'map-ar0016'; Area = 'AR0016'; SourceRun = 'maps/AR0016/runs/upscale-01/05_build'; Path = 'maps/AR0016/runs/upscale-01/05_build'; InstallOrder = 2490 },
    @{ ComponentId = 2500; ComponentLabel = 'map-ar0017'; PayloadGroup = 'map-ar0017'; Area = 'AR0017'; SourceRun = 'maps/AR0017/runs/upscale-01/05_build'; Path = 'maps/AR0017/runs/upscale-01/05_build'; InstallOrder = 2500 },
    @{ ComponentId = 2510; ComponentLabel = 'map-ar0046'; PayloadGroup = 'map-ar0046'; Area = 'AR0046'; SourceRun = 'maps/AR0046/runs/upscale-01-jour/05_build'; Path = 'maps/AR0046/runs/upscale-01-jour/05_build'; InstallOrder = 2510 },
    @{ ComponentId = 2510; ComponentLabel = 'map-ar0046'; PayloadGroup = 'map-ar0046'; Area = 'AR0046N'; SourceRun = 'maps/AR0046/runs/upscale-01-nuit/05_build'; Path = 'maps/AR0046/runs/upscale-01-nuit/05_build'; InstallOrder = 2510 },
    @{ ComponentId = 2520; ComponentLabel = 'map-ar1100'; PayloadGroup = 'map-ar1100'; Area = 'AR1100'; SourceRun = 'maps/AR1100/runs/upscale-01/05_build'; Path = 'maps/AR1100/runs/upscale-01/05_build'; InstallOrder = 2520 },
    @{ ComponentId = 2530; ComponentLabel = 'map-ar1101'; PayloadGroup = 'map-ar1101'; Area = 'AR1101'; SourceRun = 'maps/AR1101/runs/upscale-01/05_build'; Path = 'maps/AR1101/runs/upscale-01/05_build'; InstallOrder = 2530 },
    @{ ComponentId = 2540; ComponentLabel = 'map-ar1102'; PayloadGroup = 'map-ar1102'; Area = 'AR1102'; SourceRun = 'maps/AR1102/runs/upscale-01/05_build'; Path = 'maps/AR1102/runs/upscale-01/05_build'; InstallOrder = 2540 },
    @{ ComponentId = 2550; ComponentLabel = 'map-ar1103'; PayloadGroup = 'map-ar1103'; Area = 'AR1103'; SourceRun = 'maps/AR1103/runs/upscale-01/05_build'; Path = 'maps/AR1103/runs/upscale-01/05_build'; InstallOrder = 2550 },
    @{ ComponentId = 2560; ComponentLabel = 'map-ar1104'; PayloadGroup = 'map-ar1104'; Area = 'AR1104'; SourceRun = 'maps/AR1104/runs/upscale-01/05_build'; Path = 'maps/AR1104/runs/upscale-01/05_build'; InstallOrder = 2560 },
    @{ ComponentId = 2570; ComponentLabel = 'map-ar1105'; PayloadGroup = 'map-ar1105'; Area = 'AR1105'; SourceRun = 'maps/AR1105/runs/upscale-01/05_build'; Path = 'maps/AR1105/runs/upscale-01/05_build'; InstallOrder = 2570 },
    @{ ComponentId = 2580; ComponentLabel = 'map-ar1106'; PayloadGroup = 'map-ar1106'; Area = 'AR1106'; SourceRun = 'maps/AR1106/runs/upscale-01/05_build'; Path = 'maps/AR1106/runs/upscale-01/05_build'; InstallOrder = 2580 },
    @{ ComponentId = 2590; ComponentLabel = 'map-ar1200'; PayloadGroup = 'map-ar1200'; Area = 'AR1200'; SourceRun = 'maps/AR1200/runs/upscale-01/05_build'; Path = 'maps/AR1200/runs/upscale-01/05_build'; InstallOrder = 2590 },
    @{ ComponentId = 2600; ComponentLabel = 'map-ar1201'; PayloadGroup = 'map-ar1201'; Area = 'AR1201'; SourceRun = 'maps/AR1201/runs/upscale-01/05_build'; Path = 'maps/AR1201/runs/upscale-01/05_build'; InstallOrder = 2600 },
    @{ ComponentId = 2610; ComponentLabel = 'map-ar1202'; PayloadGroup = 'map-ar1202'; Area = 'AR1202'; SourceRun = 'maps/AR1202/runs/upscale-01/05_build'; Path = 'maps/AR1202/runs/upscale-01/05_build'; InstallOrder = 2610 },
    @{ ComponentId = 2620; ComponentLabel = 'map-ar1203'; PayloadGroup = 'map-ar1203'; Area = 'AR1203'; SourceRun = 'maps/AR1203/runs/upscale-01/05_build'; Path = 'maps/AR1203/runs/upscale-01/05_build'; InstallOrder = 2620 },
    @{ ComponentId = 2630; ComponentLabel = 'map-ar1204'; PayloadGroup = 'map-ar1204'; Area = 'AR1204'; SourceRun = 'maps/AR1204/runs/upscale-01/05_build'; Path = 'maps/AR1204/runs/upscale-01/05_build'; InstallOrder = 2630 },
    @{ ComponentId = 2640; ComponentLabel = 'map-ar3000'; PayloadGroup = 'map-ar3000'; Area = 'AR3000'; SourceRun = 'maps/AR3000/runs/seedvr2-7b-int8-lab-x4-primary-secondary-grid3x2/05_build/x4-water-primary-secondary'; Path = 'maps/AR3000/runs/seedvr2-7b-int8-lab-x4-primary-secondary-grid3x2/05_build/x4-water-primary-secondary'; InstallOrder = 2640 },
    @{ ComponentId = 2650; ComponentLabel = 'map-ar2100'; PayloadGroup = 'map-ar2100'; Area = 'AR2100'; SourceRun = 'maps/AR2100/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2100/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2650 },
    @{ ComponentId = 2660; ComponentLabel = 'map-ar2101'; PayloadGroup = 'map-ar2101'; Area = 'AR2101'; SourceRun = 'maps/AR2101/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2101/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2660 },
    @{ ComponentId = 2670; ComponentLabel = 'map-ar2102'; PayloadGroup = 'map-ar2102'; Area = 'AR2102'; SourceRun = 'maps/AR2102/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2102/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2670 },
    @{ ComponentId = 2680; ComponentLabel = 'map-ar2200'; PayloadGroup = 'map-ar2200'; Area = 'AR2200'; SourceRun = 'maps/AR2200/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2200/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2680 },
    @{ ComponentId = 2690; ComponentLabel = 'map-ar2201'; PayloadGroup = 'map-ar2201'; Area = 'AR2201'; SourceRun = 'maps/AR2201/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2201/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2690 },
    @{ ComponentId = 2700; ComponentLabel = 'map-ar2202'; PayloadGroup = 'map-ar2202'; Area = 'AR2202'; SourceRun = 'maps/AR2202/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2202/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2700 },
    @{ ComponentId = 2710; ComponentLabel = 'map-ar2203'; PayloadGroup = 'map-ar2203'; Area = 'AR2203'; SourceRun = 'maps/AR2203/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2203/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2710 },
    @{ ComponentId = 2720; ComponentLabel = 'map-ar2204'; PayloadGroup = 'map-ar2204'; Area = 'AR2204'; SourceRun = 'maps/AR2204/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2204/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2720 },
    @{ ComponentId = 2730; ComponentLabel = 'map-ar2205'; PayloadGroup = 'map-ar2205'; Area = 'AR2205'; SourceRun = 'maps/AR2205/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2205/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2730 },
    @{ ComponentId = 2740; ComponentLabel = 'map-ar2208'; PayloadGroup = 'map-ar2208'; Area = 'AR2208'; SourceRun = 'maps/AR2208/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2208/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2740 },
    @{ ComponentId = 2750; ComponentLabel = 'map-ar2210'; PayloadGroup = 'map-ar2210'; Area = 'AR2210'; SourceRun = 'maps/AR2210/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2210/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2750 },
    @{ ComponentId = 2760; ComponentLabel = 'map-ar2400'; PayloadGroup = 'map-ar2400'; Area = 'AR2400'; SourceRun = 'maps/AR2400/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2400/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2760 },
    @{ ComponentId = 2770; ComponentLabel = 'map-ar2401'; PayloadGroup = 'map-ar2401'; Area = 'AR2401'; SourceRun = 'maps/AR2401/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2401/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2770 },
    @{ ComponentId = 2780; ComponentLabel = 'map-ar2402'; PayloadGroup = 'map-ar2402'; Area = 'AR2402'; SourceRun = 'maps/AR2402/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2402/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2780 },
    @{ ComponentId = 2790; ComponentLabel = 'map-ar2500'; PayloadGroup = 'map-ar2500'; Area = 'AR2500'; SourceRun = 'maps/AR2500/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; Path = 'maps/AR2500/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/x4'; InstallOrder = 2790 },
    @{ ComponentId = 2800; ComponentLabel = 'map-ar2600'; PayloadGroup = 'map-ar2600'; Area = 'AR2600'; SourceRun = 'maps/AR2600/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2600/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2800 },
    @{ ComponentId = 2810; ComponentLabel = 'map-ar2602'; PayloadGroup = 'map-ar2602'; Area = 'AR2602'; SourceRun = 'maps/AR2602/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2602/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2810 },
    @{ ComponentId = 2820; ComponentLabel = 'map-ar2603'; PayloadGroup = 'map-ar2603'; Area = 'AR2603'; SourceRun = 'maps/AR2603/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2603/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2820 },
    @{ ComponentId = 2830; ComponentLabel = 'map-ar2700'; PayloadGroup = 'map-ar2700'; Area = 'AR2700'; SourceRun = 'maps/AR2700/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2700/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2830 },
    @{ ComponentId = 2840; ComponentLabel = 'map-ar2800'; PayloadGroup = 'map-ar2800'; Area = 'AR2800'; SourceRun = 'maps/AR2800/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-jour/05_build/x4-release'; Path = 'maps/AR2800/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-jour/05_build/x4-release'; InstallOrder = 2840 },
    @{ ComponentId = 2840; ComponentLabel = 'map-ar2800'; PayloadGroup = 'map-ar2800'; Area = 'AR2800N'; SourceRun = 'maps/AR2800/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-nuit/05_build/x4-release'; Path = 'maps/AR2800/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-nuit/05_build/x4-release'; InstallOrder = 2840 },
    @{ ComponentId = 2850; ComponentLabel = 'map-ar2801'; PayloadGroup = 'map-ar2801'; Area = 'AR2801'; SourceRun = 'maps/AR2801/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2801/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2850 },
    @{ ComponentId = 2860; ComponentLabel = 'map-ar2802'; PayloadGroup = 'map-ar2802'; Area = 'AR2802'; SourceRun = 'maps/AR2802/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2802/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2860 },
    @{ ComponentId = 2870; ComponentLabel = 'map-ar2803'; PayloadGroup = 'map-ar2803'; Area = 'AR2803'; SourceRun = 'maps/AR2803/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2803/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2870 },
    @{ ComponentId = 2880; ComponentLabel = 'map-ar2804'; PayloadGroup = 'map-ar2804'; Area = 'AR2804'; SourceRun = 'maps/AR2804/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2804/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2880 },
    @{ ComponentId = 2890; ComponentLabel = 'map-ar2805'; PayloadGroup = 'map-ar2805'; Area = 'AR2805'; SourceRun = 'maps/AR2805/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2805/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2890 },
    @{ ComponentId = 2900; ComponentLabel = 'map-ar2806'; PayloadGroup = 'map-ar2806'; Area = 'AR2806'; SourceRun = 'maps/AR2806/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2806/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2900 },
    @{ ComponentId = 2910; ComponentLabel = 'map-ar2807'; PayloadGroup = 'map-ar2807'; Area = 'AR2807'; SourceRun = 'maps/AR2807/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-jour/05_build/x4-release'; Path = 'maps/AR2807/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-jour/05_build/x4-release'; InstallOrder = 2910 },
    @{ ComponentId = 2910; ComponentLabel = 'map-ar2807'; PayloadGroup = 'map-ar2807'; Area = 'AR2807N'; SourceRun = 'maps/AR2807/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-nuit/05_build/x4-release'; Path = 'maps/AR2807/runs/seedvr2-7b-int8-lab-batch-tethyr-x4-nuit/05_build/x4-release'; InstallOrder = 2910 },
    @{ ComponentId = 2920; ComponentLabel = 'map-ar2900'; PayloadGroup = 'map-ar2900'; Area = 'AR2900'; SourceRun = 'maps/AR2900/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2900/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2920 },
    @{ ComponentId = 2930; ComponentLabel = 'map-ar2901'; PayloadGroup = 'map-ar2901'; Area = 'AR2901'; SourceRun = 'maps/AR2901/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2901/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2930 },
    @{ ComponentId = 2940; ComponentLabel = 'map-ar2902'; PayloadGroup = 'map-ar2902'; Area = 'AR2902'; SourceRun = 'maps/AR2902/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2902/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2940 },
    @{ ComponentId = 2950; ComponentLabel = 'map-ar2903'; PayloadGroup = 'map-ar2903'; Area = 'AR2903'; SourceRun = 'maps/AR2903/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2903/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2950 },
    @{ ComponentId = 2960; ComponentLabel = 'map-ar2904'; PayloadGroup = 'map-ar2904'; Area = 'AR2904'; SourceRun = 'maps/AR2904/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2904/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2960 },
    @{ ComponentId = 2970; ComponentLabel = 'map-ar2905'; PayloadGroup = 'map-ar2905'; Area = 'AR2905'; SourceRun = 'maps/AR2905/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; Path = 'maps/AR2905/runs/seedvr2-7b-int8-lab-batch-tethyr-x4/05_build/x4-release'; InstallOrder = 2970 },
    @{ ComponentId = 2980; ComponentLabel = 'map-ar2000'; PayloadGroup = 'map-ar2000'; Area = 'AR2000'; SourceRun = 'maps/AR2000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/AR2000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 2980 },
    @{ ComponentId = 2990; ComponentLabel = 'map-ar2000'; PayloadGroup = 'map-ar2000'; Area = 'AR2000N'; SourceRun = 'maps/AR2000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/AR2000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 2990 },
    @{ ComponentId = 3750; ComponentLabel = 'map-ar2001'; PayloadGroup = 'map-ar2001'; Area = 'AR2001'; SourceRun = 'maps/AR2001/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2001/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3750 },
    @{ ComponentId = 3010; ComponentLabel = 'map-ar2002'; PayloadGroup = 'map-ar2002'; Area = 'AR2002'; SourceRun = 'maps/AR2002/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2002/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3010 },
    @{ ComponentId = 3020; ComponentLabel = 'map-ar2006'; PayloadGroup = 'map-ar2006'; Area = 'AR2006'; SourceRun = 'maps/AR2006/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2006/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3020 },
    @{ ComponentId = 3030; ComponentLabel = 'map-ar2007'; PayloadGroup = 'map-ar2007'; Area = 'AR2007'; SourceRun = 'maps/AR2007/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2007/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3030 },
    @{ ComponentId = 3040; ComponentLabel = 'map-ar2008'; PayloadGroup = 'map-ar2008'; Area = 'AR2008'; SourceRun = 'maps/AR2008/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; Path = 'maps/AR2008/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; InstallOrder = 3040 },
    @{ ComponentId = 3050; ComponentLabel = 'map-ar2009'; PayloadGroup = 'map-ar2009'; Area = 'AR2009'; SourceRun = 'maps/AR2009/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2009/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3050 },
    @{ ComponentId = 3060; ComponentLabel = 'map-ar2010'; PayloadGroup = 'map-ar2010'; Area = 'AR2010'; SourceRun = 'maps/AR2010/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2010/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3060 },
    @{ ComponentId = 3070; ComponentLabel = 'map-ar2011'; PayloadGroup = 'map-ar2011'; Area = 'AR2011'; SourceRun = 'maps/AR2011/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2011/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3070 },
    @{ ComponentId = 3080; ComponentLabel = 'map-ar2012'; PayloadGroup = 'map-ar2012'; Area = 'AR2012'; SourceRun = 'maps/AR2012/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2012/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3080 },
    @{ ComponentId = 3090; ComponentLabel = 'map-ar2013'; PayloadGroup = 'map-ar2013'; Area = 'AR2013'; SourceRun = 'maps/AR2013/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2013/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3090 },
    @{ ComponentId = 3100; ComponentLabel = 'map-ar2014'; PayloadGroup = 'map-ar2014'; Area = 'AR2014'; SourceRun = 'maps/AR2014/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2014/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3100 },
    @{ ComponentId = 3110; ComponentLabel = 'map-ar2015'; PayloadGroup = 'map-ar2015'; Area = 'AR2015'; SourceRun = 'maps/AR2015/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR2015/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3110 },
    @{ ComponentId = 3120; ComponentLabel = 'map-ar1600'; PayloadGroup = 'map-ar1600'; Area = 'AR1600'; SourceRun = 'maps/AR1600/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; Path = 'maps/AR1600/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; InstallOrder = 3120 },
    @{ ComponentId = 3130; ComponentLabel = 'map-ar1601'; PayloadGroup = 'map-ar1601'; Area = 'AR1601'; SourceRun = 'maps/AR1601/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1601/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3130 },
    @{ ComponentId = 3140; ComponentLabel = 'map-ar1602'; PayloadGroup = 'map-ar1602'; Area = 'AR1602'; SourceRun = 'maps/AR1602/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1602/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3140 },
    @{ ComponentId = 3150; ComponentLabel = 'map-ar1603'; PayloadGroup = 'map-ar1603'; Area = 'AR1603'; SourceRun = 'maps/AR1603/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1603/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3150 },
    @{ ComponentId = 3160; ComponentLabel = 'map-ar1604'; PayloadGroup = 'map-ar1604'; Area = 'AR1604'; SourceRun = 'maps/AR1604/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1604/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3160 },
    @{ ComponentId = 3170; ComponentLabel = 'map-ar1605'; PayloadGroup = 'map-ar1605'; Area = 'AR1605'; SourceRun = 'maps/AR1605/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1605/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3170 },
    @{ ComponentId = 3180; ComponentLabel = 'map-ar1606'; PayloadGroup = 'map-ar1606'; Area = 'AR1606'; SourceRun = 'maps/AR1606/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1606/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3180 },
    @{ ComponentId = 3190; ComponentLabel = 'map-ar1608'; PayloadGroup = 'map-ar1608'; Area = 'AR1608'; SourceRun = 'maps/AR1608/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1608/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3190 },
    @{ ComponentId = 3200; ComponentLabel = 'map-ar1609'; PayloadGroup = 'map-ar1609'; Area = 'AR1609'; SourceRun = 'maps/AR1609/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1609/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3200 },
    @{ ComponentId = 3210; ComponentLabel = 'map-ar1610'; PayloadGroup = 'map-ar1610'; Area = 'AR1610'; SourceRun = 'maps/AR1610/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1610/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3210 },
    @{ ComponentId = 3220; ComponentLabel = 'map-ar1611'; PayloadGroup = 'map-ar1611'; Area = 'AR1611'; SourceRun = 'maps/AR1611/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1611/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3220 },
    @{ ComponentId = 3230; ComponentLabel = 'map-ar1612'; PayloadGroup = 'map-ar1612'; Area = 'AR1612'; SourceRun = 'maps/AR1612/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1612/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3230 },
    @{ ComponentId = 3240; ComponentLabel = 'map-ar1613'; PayloadGroup = 'map-ar1613'; Area = 'AR1613'; SourceRun = 'maps/AR1613/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1613/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3240 },
    @{ ComponentId = 3250; ComponentLabel = 'map-ar1500'; PayloadGroup = 'map-ar1500'; Area = 'AR1500'; SourceRun = 'maps/AR1500/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; Path = 'maps/AR1500/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; InstallOrder = 3250 },
    @{ ComponentId = 3260; ComponentLabel = 'map-ar1501'; PayloadGroup = 'map-ar1501'; Area = 'AR1501'; SourceRun = 'maps/AR1501/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1501/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3260 },
    @{ ComponentId = 3270; ComponentLabel = 'map-ar1502'; PayloadGroup = 'map-ar1502'; Area = 'AR1502'; SourceRun = 'maps/AR1502/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; Path = 'maps/AR1502/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; InstallOrder = 3270 },
    @{ ComponentId = 3280; ComponentLabel = 'map-ar1503'; PayloadGroup = 'map-ar1503'; Area = 'AR1503'; SourceRun = 'maps/AR1503/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1503/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3280 },
    @{ ComponentId = 3290; ComponentLabel = 'map-ar1504'; PayloadGroup = 'map-ar1504'; Area = 'AR1504'; SourceRun = 'maps/AR1504/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1504/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3290 },
    @{ ComponentId = 3300; ComponentLabel = 'map-ar1505'; PayloadGroup = 'map-ar1505'; Area = 'AR1505'; SourceRun = 'maps/AR1505/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1505/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3300 },
    @{ ComponentId = 3310; ComponentLabel = 'map-ar1506'; PayloadGroup = 'map-ar1506'; Area = 'AR1506'; SourceRun = 'maps/AR1506/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/AR1506/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3310 },
    @{ ComponentId = 3320; ComponentLabel = 'map-ar1507'; PayloadGroup = 'map-ar1507'; Area = 'AR1507'; SourceRun = 'maps/AR1507/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1507/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3320 },
    @{ ComponentId = 3330; ComponentLabel = 'map-ar1508'; PayloadGroup = 'map-ar1508'; Area = 'AR1508'; SourceRun = 'maps/AR1508/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1508/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3330 },
    @{ ComponentId = 3340; ComponentLabel = 'map-ar1509'; PayloadGroup = 'map-ar1509'; Area = 'AR1509'; SourceRun = 'maps/AR1509/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1509/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3340 },
    @{ ComponentId = 3350; ComponentLabel = 'map-ar1510'; PayloadGroup = 'map-ar1510'; Area = 'AR1510'; SourceRun = 'maps/AR1510/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1510/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3350 },
    @{ ComponentId = 3360; ComponentLabel = 'map-ar1511'; PayloadGroup = 'map-ar1511'; Area = 'AR1511'; SourceRun = 'maps/AR1511/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1511/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3360 },
    @{ ComponentId = 3370; ComponentLabel = 'map-ar1512'; PayloadGroup = 'map-ar1512'; Area = 'AR1512'; SourceRun = 'maps/AR1512/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/AR1512/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3370 },
    @{ ComponentId = 3380; ComponentLabel = 'map-ar1513'; PayloadGroup = 'map-ar1513'; Area = 'AR1513'; SourceRun = 'maps/AR1513/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; Path = 'maps/AR1513/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; InstallOrder = 3380 },
    @{ ComponentId = 3390; ComponentLabel = 'map-ar1514'; PayloadGroup = 'map-ar1514'; Area = 'AR1514'; SourceRun = 'maps/AR1514/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/AR1514/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3390 },
    @{ ComponentId = 3400; ComponentLabel = 'map-ar1515'; PayloadGroup = 'map-ar1515'; Area = 'AR1515'; SourceRun = 'maps/AR1515/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; Path = 'maps/AR1515/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; InstallOrder = 3400 },
    @{ ComponentId = 3410; ComponentLabel = 'map-ar1516'; PayloadGroup = 'map-ar1516'; Area = 'AR1516'; SourceRun = 'maps/AR1516/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/AR1516/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3410 },
    @{ ComponentId = 3420; ComponentLabel = 'map-ar1900'; PayloadGroup = 'map-ar1900'; Area = 'AR1900'; SourceRun = 'maps/AR1900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/AR1900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 3420 },
    @{ ComponentId = 3430; ComponentLabel = 'map-ar1900'; PayloadGroup = 'map-ar1900'; Area = 'AR1900N'; SourceRun = 'maps/AR1900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/AR1900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 3430 },
    @{ ComponentId = 3440; ComponentLabel = 'map-ar1400'; PayloadGroup = 'map-ar1400'; Area = 'AR1400'; SourceRun = 'maps/AR1400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-jour/05_build'; Path = 'maps/AR1400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-jour/05_build'; InstallOrder = 3440 },
    @{ ComponentId = 3450; ComponentLabel = 'map-ar1400'; PayloadGroup = 'map-ar1400'; Area = 'AR1400N'; SourceRun = 'maps/AR1400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-nuit/05_build'; Path = 'maps/AR1400/runs/seedvr2-7b-int8-lab-grid-2x4-x4-nuit/05_build'; InstallOrder = 3450 },
    @{ ComponentId = 3460; ComponentLabel = 'map-ar1404'; PayloadGroup = 'map-ar1404'; Area = 'AR1404'; SourceRun = 'maps/AR1404/runs/seedvr2-7b-int8-lab-grid-2x4-x4/05_build'; Path = 'maps/AR1404/runs/seedvr2-7b-int8-lab-grid-2x4-x4/05_build'; InstallOrder = 3460 },
    @{ ComponentId = 3470; ComponentLabel = 'map-ar1700'; PayloadGroup = 'map-ar1700'; Area = 'AR1700'; SourceRun = 'maps/AR1700/runs/seedvr2-7b-int8-lab-grid-2x4-x4/05_build'; Path = 'maps/AR1700/runs/seedvr2-7b-int8-lab-grid-2x4-x4/05_build'; InstallOrder = 3470 },
    @{ ComponentId = 3480; ComponentLabel = 'map-ar0011'; PayloadGroup = 'map-ar0011'; Area = 'AR0011'; SourceRun = 'maps/AR0011/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; Path = 'maps/AR0011/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; InstallOrder = 3480 },
    @{ ComponentId = 3490; ComponentLabel = 'map-ar1401'; PayloadGroup = 'map-ar1401'; Area = 'AR1401'; SourceRun = 'maps/AR1401/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; Path = 'maps/AR1401/runs/seedvr2-7b-int8-lab-grid-2x3-x4/05_build'; InstallOrder = 3490 },
    @{ ComponentId = 3500; ComponentLabel = 'map-ar1402'; PayloadGroup = 'map-ar1402'; Area = 'AR1402'; SourceRun = 'maps/AR1402/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/AR1402/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3500 },
    @{ ComponentId = 3510; ComponentLabel = 'map-ar1904'; PayloadGroup = 'map-ar1904'; Area = 'AR1904'; SourceRun = 'maps/AR1904/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; Path = 'maps/AR1904/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; InstallOrder = 3510 },
    @{ ComponentId = 3520; ComponentLabel = 'map-ar1901'; PayloadGroup = 'map-ar1901'; Area = 'AR1901'; SourceRun = 'maps/AR1901/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; Path = 'maps/AR1901/runs/seedvr2-7b-int8-lab-split-rows-x4/05_build'; InstallOrder = 3520 },
    @{ ComponentId = 3530; ComponentLabel = 'map-ar0714'; PayloadGroup = 'map-ar0714'; Area = 'AR0714'; SourceRun = 'maps/AR0714/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR0714/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3530 },
    @{ ComponentId = 3540; ComponentLabel = 'map-ar1403'; PayloadGroup = 'map-ar1403'; Area = 'AR1403'; SourceRun = 'maps/AR1403/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1403/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3540 },
    @{ ComponentId = 3550; ComponentLabel = 'map-ar1902'; PayloadGroup = 'map-ar1902'; Area = 'AR1902'; SourceRun = 'maps/AR1902/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1902/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3550 },
    @{ ComponentId = 3560; ComponentLabel = 'map-ar1905'; PayloadGroup = 'map-ar1905'; Area = 'AR1905'; SourceRun = 'maps/AR1905/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; Path = 'maps/AR1905/runs/seedvr2-7b-int8-lab-direct-x4/05_build'; InstallOrder = 3560 },
    @{ ComponentId = 3570; ComponentLabel = 'map-oh4000'; PayloadGroup = 'map-oh4000'; Area = 'OH4000'; SourceRun = 'maps/OH4000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/OH4000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 3570 },
    @{ ComponentId = 3580; ComponentLabel = 'map-oh4000'; PayloadGroup = 'map-oh4000'; Area = 'OH4000N'; SourceRun = 'maps/OH4000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/OH4000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 3580 },
    @{ ComponentId = 3590; ComponentLabel = 'map-oh4100'; PayloadGroup = 'map-oh4100'; Area = 'OH4100'; SourceRun = 'maps/OH4100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/OH4100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 3590 },
    @{ ComponentId = 3600; ComponentLabel = 'map-oh4100'; PayloadGroup = 'map-oh4100'; Area = 'OH4100N'; SourceRun = 'maps/OH4100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/OH4100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 3600 },
    @{ ComponentId = 3610; ComponentLabel = 'map-oh5100'; PayloadGroup = 'map-oh5100'; Area = 'OH5100'; SourceRun = 'maps/OH5100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/OH5100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 3610 },
    @{ ComponentId = 3620; ComponentLabel = 'map-oh5100'; PayloadGroup = 'map-oh5100'; Area = 'OH5100N'; SourceRun = 'maps/OH5100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/OH5100/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 3620 },
    @{ ComponentId = 3630; ComponentLabel = 'map-oh6000'; PayloadGroup = 'map-oh6000'; Area = 'OH6000'; SourceRun = 'maps/OH6000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; Path = 'maps/OH6000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build'; InstallOrder = 3630 },
    @{ ComponentId = 3640; ComponentLabel = 'map-oh6000'; PayloadGroup = 'map-oh6000'; Area = 'OH6000N'; SourceRun = 'maps/OH6000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; Path = 'maps/OH6000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/05_build'; InstallOrder = 3640 },
    @{ ComponentId = 3650; ComponentLabel = 'map-oh7100'; PayloadGroup = 'map-oh7100'; Area = 'OH7100'; SourceRun = 'maps/OH7100/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/OH7100/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3650 },
    @{ ComponentId = 3660; ComponentLabel = 'map-oh7200'; PayloadGroup = 'map-oh7200'; Area = 'OH7200'; SourceRun = 'maps/OH7200/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; Path = 'maps/OH7200/runs/seedvr2-7b-int8-lab-grid-2x2-x4/05_build'; InstallOrder = 3660 },
    @{ ComponentId = 3670; ComponentLabel = 'map-oh4101'; PayloadGroup = 'map-oh4101'; Area = 'OH4101'; SourceRun = 'maps/OH4101/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; Path = 'maps/OH4101/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; InstallOrder = 3670 },
    @{ ComponentId = 3680; ComponentLabel = 'map-oh4101'; PayloadGroup = 'map-oh4101'; Area = 'OH4101N'; SourceRun = 'maps/OH4101/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; Path = 'maps/OH4101/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; InstallOrder = 3680 },
    @{ ComponentId = 3690; ComponentLabel = 'map-oh5300'; PayloadGroup = 'map-oh5300'; Area = 'OH5300'; SourceRun = 'maps/OH5300/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; Path = 'maps/OH5300/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; InstallOrder = 3690 },
    @{ ComponentId = 3700; ComponentLabel = 'map-oh5300'; PayloadGroup = 'map-oh5300'; Area = 'OH5300N'; SourceRun = 'maps/OH5300/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; Path = 'maps/OH5300/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; InstallOrder = 3700 },
    @{ ComponentId = 3710; ComponentLabel = 'map-oh6100'; PayloadGroup = 'map-oh6100'; Area = 'OH6100'; SourceRun = 'maps/OH6100/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; Path = 'maps/OH6100/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; InstallOrder = 3710 },
    @{ ComponentId = 3720; ComponentLabel = 'map-oh6100'; PayloadGroup = 'map-oh6100'; Area = 'OH6100N'; SourceRun = 'maps/OH6100/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; Path = 'maps/OH6100/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; InstallOrder = 3720 },
    @{ ComponentId = 3730; ComponentLabel = 'map-oh6200'; PayloadGroup = 'map-oh6200'; Area = 'OH6200'; SourceRun = 'maps/OH6200/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; Path = 'maps/OH6200/runs/seedvr2-7b-int8-lab-grid-2x2-x4-jour/05_build'; InstallOrder = 3730 },
    @{ ComponentId = 3740; ComponentLabel = 'map-oh6200'; PayloadGroup = 'map-oh6200'; Area = 'OH6200N'; SourceRun = 'maps/OH6200/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; Path = 'maps/OH6200/runs/seedvr2-7b-int8-lab-grid-2x2-x4-nuit/05_build'; InstallOrder = 3740 }
)

# The CSV is the validation register.  Every validated day/night variant must
# have one explicit, reviewed canonical source above; this keeps a new CSV
# validation from silently disappearing from a package.
if (-not $isAnimationDelta) {
    $areasCsv = Join-Path $WorkspaceRoot 'areas.csv'
    if (-not (Test-Path -LiteralPath $areasCsv -PathType Leaf)) { throw "Registre des zones absent : $areasCsv" }
    $validatedAreas = Import-Csv -LiteralPath $areasCsv | Where-Object { $_.area_id -match '^(AR|OH)\d{4}$' }
    $areasById = @{}
    foreach ($area in $validatedAreas) { $areasById[[string]$area.area_id] = $area }
    $requiredVariants = [Collections.Generic.List[string]]::new()
    foreach ($area in $validatedAreas) {
        if ($area.status -eq 'validated-installed') { $requiredVariants.Add([string]$area.area_id) }
        if ($area.status_nuit -eq 'validated-installed') { $requiredVariants.Add(([string]$area.area_id) + 'N') }
    }
    $declaredVariants = @($mapSpecs | ForEach-Object { [string]$_.Area })
    $missingVariants = @($requiredVariants | Sort-Object -Unique | Where-Object { $_ -notin $declaredVariants })
    $extraVariants = @($declaredVariants | Sort-Object -Unique | Where-Object { $_ -notin $requiredVariants })
    if ($missingVariants.Count -gt 0 -or $extraVariants.Count -gt 0) {
        throw "Couverture CSV/manifeste invalide. Manquantes: $($missingVariants -join ', '). En trop: $($extraVariants -join ', ')"
    }

    # The release may select a reviewed sub-build below the current run, but it may
    # never silently package another run. This closes the previous state where the
    # CSV and the release covered the same areas while disagreeing on 37 run IDs.
    foreach ($spec in $mapSpecs) {
        $variant = [string]$spec.Area
        $isNight = $variant.EndsWith('N', [StringComparison]::Ordinal)
        $areaId = if ($isNight) { $variant.Substring(0, $variant.Length - 1) } else { $variant }
        Require ($areasById.ContainsKey($areaId)) "Zone de release absente de areas.csv : $variant"
        $area = $areasById[$areaId]
        $status = if ($isNight) { [string]$area.status_nuit } else { [string]$area.status }
        $runText = if ($isNight) { [string]$area.runs_nuit } else { [string]$area.runs }
        $catalogRuns = @($runText -split ';' | Where-Object { $_ })
        $prefix = "maps/$areaId/runs/"
        $path = ([string]$spec.Path).Replace('\', '/')
        Require ($status -eq 'validated-installed') "Variante release non validee dans areas.csv : $variant"
        Require ($path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) "Source release hors run de zone : $variant / $path"
        $runId = $path.Substring($prefix.Length).Split('/')[0]
        Require ($runId -in $catalogRuns) "Run release different du catalogue : $variant / release=$runId / catalogue=$($catalogRuns -join ';')"
        Require ([string]$spec.SourceRun -eq [string]$spec.Path) "SourceRun et Path divergent : $variant"
    }
}

$uiSpecs = @(
    @{ ComponentId = 100; ComponentLabel = 'ui-mainmenu-x4'; PayloadGroup = 'ui-mainmenu'; Area = 'UI'; SourceRun = 'interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/assets'; Path = 'interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/assets'; Names = @('BIGLOGO-MOS0017-x4.dxt5','MAINMENU-MOS0181-x4.dxt5','MAINMENU-MOS0257-x4.dxt5','MAINMENU-MOS0258-x4.dxt5','MAINMENU-MOS0261-x4.dxt5','MAINMENU-MOS0262-x4.dxt5','MAINMENU-MOS0265-x4.dxt5','MAINMENU-MOS0266-x4.dxt5'); InstallOrder = 100; ReplacesComponentOutput = $false },
    @{ ComponentId = 110; ComponentLabel = 'ui-selector-x4'; PayloadGroup = 'ui-selector'; Area = 'UI'; SourceRun = 'interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/selection-des-trois-jeux/assets'; Path = 'interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/selection-des-trois-jeux/assets'; Names = @('MAINMENU-MOS0181-x4.dxt5','SELECTOR-MOS0182-x4.dxt5','SELECTOR-MOS0183-x4.dxt5','SELECTOR-MOS0184-x4.dxt5','SELECTOR-MOS0185-x4.dxt5','MAINMENU-MOS0258-x4.dxt5','SELECTOR-MOS0259-x4.dxt5'); InstallOrder = 110; ReplacesComponentOutput = $true }
)

# Les overlays partages sont gouvernes par un manifeste explicite. Une politique
# `stock` interdit leur inclusion ; une politique `package` epingle inventaire,
# taille et hash afin qu'un essai x4 ne puisse pas remplacer silencieusement x2.
$overlaySpecs = @()
if (-not $isAnimationDelta) {
    $releaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    Require (Test-Path -LiteralPath $OverlayPolicyPath -PathType Leaf) "Politique overlays absente : $OverlayPolicyPath"
    Require (Test-Json -Path $OverlayPolicyPath -SchemaFile (Join-Path $releaseRoot 'schemas\overlay-sources.schema.json')) 'Schema de politique overlays invalide.'
    $overlayPolicy = Read-Json $OverlayPolicyPath
    $overlaySpecs = foreach ($policy in @($overlayPolicy.policies | Sort-Object component_id, resref)) {
        if ([string]$policy.policy -eq 'stock') { continue }
        Require ([string]$policy.validation_status -eq 'validated-installed') "Overlay non valide interdit en release : $($policy.resref)"
        @{
            ComponentId = [int]$policy.component_id
            ComponentLabel = [string]$policy.component_label
            PayloadGroup = [string]$policy.payload_group
            Area = [string]$policy.component_area
            SourceRun = [string]$policy.source_run
            Path = [string]$policy.source_path
            ExpectedFiles = @($policy.files)
            InstallOrder = [int]$policy.component_id
            ReplacesComponentOutput = $false
            Scale = [int]$policy.scale
        }
    }
}

$wedCorrectionSpecs = @()
if (-not $isAnimationDelta) {
    $candidateRegister = Read-Json $AnimationCandidatesPath
    foreach ($candidate in @($candidateRegister.candidates | Where-Object { $_.approval_status -eq 'approved-for-release' -and $null -ne $_.occlusion_contract })) {
        $occlusion = $candidate.occlusion_contract
        $sourcePath = [string]$occlusion.source
        $wedCorrectionSpecs += @{
            ComponentId = [int]$occlusion.map_component_id
            ComponentLabel = [string]$occlusion.map_component_label
            PayloadGroup = [string]$occlusion.map_payload_group
            Area = [string]$candidate.area
            SourceRun = [IO.Path]::GetDirectoryName($sourcePath).Replace('\', '/')
            Path = $sourcePath
            ExpectedDestination = [string]$occlusion.destination
            ExpectedBytes = [int64]$occlusion.bytes
            ExpectedSha256 = [string]$occlusion.sha256
            InstallOrder = [int]$occlusion.map_component_id
            ReplacesComponentOutput = $false
        }
    }
}

$entries = [System.Collections.Generic.List[object]]::new()
if (-not $isAnimationDelta) {
    foreach ($spec in $mapSpecs) {
        $sourceDirectory = Join-Path $WorkspaceRoot $spec.Path
        if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) { throw "Source canonique absente : $sourceDirectory" }
        $normalized = $spec + @{ Kind = 'map'; DestinationRoot = 'override'; Model = 'SeedVR2-7B-LAB'; ReplacesComponentOutput = $false }
        $files = Get-ChildItem -LiteralPath $sourceDirectory -File | Where-Object { $_.Extension -in '.TIS', '.PVRZ' } | Sort-Object Name
        if ($files.Count -eq 0) { throw "Aucun TIS/PVRZ dans : $sourceDirectory" }
        foreach ($file in $files) { $entries.Add((New-ContentEntry $normalized $file)) }
    }
    foreach ($spec in $wedCorrectionSpecs) {
        $file = Get-Item -LiteralPath (Join-Path $WorkspaceRoot $spec.Path) -ErrorAction Stop
        Require ($file.Length -eq [int64]$spec.ExpectedBytes) "Taille correction WED invalide : $($spec.Area)"
        Require ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq [string]$spec.ExpectedSha256) "Hash correction WED invalide : $($spec.Area)"
        $normalized = $spec + @{ Kind = 'map'; DestinationRoot = 'override'; Model = 'WED-Native-Occlusion-v1'; Scale = 4 }
        $entry = New-ContentEntry $normalized $file
        Require ([string]$entry.destination -eq [string]$spec.ExpectedDestination) "Destination correction WED invalide : $($spec.Area)"
        $entries.Add($entry)
    }
    foreach ($spec in $uiSpecs) {
        $sourceDirectory = Join-Path $WorkspaceRoot $spec.Path
        $normalized = $spec + @{ Kind = 'ui'; DestinationRoot = 'iee-assets'; Model = 'Topaz-Gigapixel-Recovery-v2-D50' }
        foreach ($name in $spec.Names) {
            $file = Get-Item -LiteralPath (Join-Path $sourceDirectory $name) -ErrorAction Stop
            $entries.Add((New-ContentEntry $normalized $file))
        }
    }
    foreach ($spec in $overlaySpecs) {
        $sourceDirectory = Join-Path $WorkspaceRoot $spec.Path
        Require (Test-Path -LiteralPath $sourceDirectory -PathType Container) "Source overlay absente : $sourceDirectory"
        $normalized = $spec + @{ Kind = 'overlay'; DestinationRoot = 'override'; Model = 'SeedVR2-7B-LAB' }
        $actualNames = @(Get-ChildItem -LiteralPath $sourceDirectory -File | Where-Object { $_.Extension -in '.TIS', '.PVRZ' } | ForEach-Object Name | Sort-Object)
        $expectedNames = @($spec.ExpectedFiles | ForEach-Object { [string]$_.name } | Sort-Object)
        Require (-not (Compare-Object $expectedNames $actualNames)) "Inventaire overlay inattendu : $($spec.Area)"
        foreach ($expected in $spec.ExpectedFiles) {
            $file = Get-Item -LiteralPath (Join-Path $sourceDirectory ([string]$expected.name)) -ErrorAction Stop
            Require ($file.Length -eq [int64]$expected.bytes) "Taille overlay invalide : $($file.Name)"
            Require ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq [string]$expected.sha256) "Hash overlay invalide : $($file.Name)"
            $entries.Add((New-ContentEntry $normalized $file))
        }
    }
}
foreach ($entry in @(Get-AnimationCandidateEntries -Workspace $WorkspaceRoot -CandidatesPath $AnimationCandidatesPath -RuntimePath $RuntimeCompatibilityPath -IncludePending $IncludePendingAnimationCandidates -OnlyAreas @($selectedAnimationAreas))) {
    $entries.Add($entry)
}
foreach ($entry in $entries) {
    Require ($entry -is [System.Collections.IDictionary]) 'Sortie non structuree interdite dans content.json.'
    Require (-not [string]::IsNullOrWhiteSpace([string]$entry.source)) 'Source vide interdite dans content.json.'
    Require (-not [string]::IsNullOrWhiteSpace([string]$entry.destination)) 'Destination vide interdite dans content.json.'
}

$manifest = [ordered]@{
    '$schema' = '../schemas/content.schema.json'
    schema_version = 1
    generated_by = 'tools/New-BG2HD-ContentManifest.ps1'
    entries = @($entries | Sort-Object component_id, install_order, destination, source)
}

Write-BG2HDAtomicUtf8NoBomFile -Path $OutputPath -Text (($manifest | ConvertTo-Json -Depth 8) + [Environment]::NewLine)
Write-Output "Wrote $($entries.Count) entries to $OutputPath"
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
