[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\manifests\content.json'),
    [string]$MapCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\map-release-candidates.csv'),
    [string]$MapAssembliesPath = (Join-Path $PSScriptRoot '..\manifests\map-release-assemblies.json'),
    [string]$AnimationCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\animation-release-candidates.json'),
    [string]$SpriteCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\sprite-release-candidates.json'),
    [string]$EffectCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\effect-release-candidates.json'),
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
    $verifiableCandidates = @($candidates.candidates | Where-Object {
        ($requestedAreas.Count -eq 0 -or [string]$_.area -in $requestedAreas) -and
        ([string]$_.approval_status -eq 'approved-for-release' -or $IncludePending)
    } | Sort-Object component_id)
    if ($verifiableCandidates.Count -gt 0) {
        $releaseVerifier = Join-Path $Workspace 'pipeline\scripts\verify_animation_release_candidate.py'
        Require (Test-Path -LiteralPath $releaseVerifier -PathType Leaf) 'Validateur de release animation absent.'
        $releaseArguments = @($releaseVerifier, '--workspace-root', $Workspace, '--animation-candidates-path', $CandidatesPath)
        foreach ($item in $verifiableCandidates) { $releaseArguments += @('--area', [string]$item.area) }
        if (-not [string]::IsNullOrWhiteSpace($AnimationQaApprovalOverridePath)) {
            $releaseArguments += @('--animation-qa-approval-override-path', [IO.Path]::GetFullPath($AnimationQaApprovalOverridePath))
        }
        if ($IncludePending) { $releaseArguments += '--allow-pending' }
        $releaseOutput = @(& python @releaseArguments 2>&1)
        Require ($LASTEXITCODE -eq 0) ('Preuves release animation invalides : ' + ($releaseOutput -join [Environment]::NewLine))
    }
    $result = [System.Collections.Generic.List[object]]::new()
    foreach ($candidate in $verifiableCandidates) {
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
        $coveredQaResrefs = @()
        $qaDecisionFinalRuns = @{}
        $runtimeResrefByAsset = @{}
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
                    # Une decision peut valider une ressource servie sous un autre resref runtime
                    # (porteur fusionne, ex. AM2805C servi comme AM28ADD) : la preuve et le
                    # candidat portent alors le resref runtime, champ prevu par le schema.
                    $decisionRuntimeResref = if ([string]::IsNullOrWhiteSpace([string]$decision.runtime_resref)) { $decisionResref } else { ([string]$decision.runtime_resref).ToUpperInvariant() }
                    Require ($decision.result_kind -eq 'x4') "Decision ingame non x4 interdite en release : $relativeEvidence"
                    Require ($decision.status -eq 'accepted' -and $decision.decision_origin -eq 'explicit-user-ingame-qa') "Decision ingame non acceptee : $relativeEvidence"
                    Require ($decisionRuntimeResref -eq $evidenceResrefs[0] -and [string]$decision.asset_id -eq "animations:bam:$decisionResref") "Resref de decision ingame incoherent : $relativeEvidence"
                    $expectedDecisionPath = "animations/index/qa-decisions/$decisionResref/$($decision.decision_id).json"
                    Require ($relativeEvidence -ceq $expectedDecisionPath) "Decision ingame rangee sous un autre asset ou identifiant : $relativeEvidence"
                    Require (@($decision.tested_areas) -contains [string]$candidate.area) "Zone absente de la decision ingame : $relativeEvidence"
                    $decisionArea = @($decision.source_pack.areas | Where-Object { [string]$_.area -eq [string]$candidate.area })
                    Require ($decisionArea.Count -eq 1) "Pack de zone absent ou duplique dans la decision : $relativeEvidence"
                    # Un pack de zone compose reunit des ressources validees dans des packs
                    # distincts : la decision reference alors son propre pack. La preuve que
                    # chaque ressource du candidat est identique a celle de sa decision est
                    # faite par verify_animation_release_candidate.py, execute juste au-dessus
                    # pour ce candidat ; ici on n'exige l'egalite stricte que pour un pack direct.
                    if ([string]$decisionArea[0].path -eq [string]$candidate.source_pack) {
                        Require ([string]$decisionArea[0].manifest_sha256 -eq [string]$candidate.pack_manifest_sha256 -and [string]$decisionArea[0].registry_sha256 -eq [string]$candidate.registry_sha256) "Hashes du pack de decision differents du candidat : $relativeEvidence"
                    } else {
                        Require ($qaSchemaVersion -in @(2, 3)) "Pack de decision different du candidat : $relativeEvidence"
                    }

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
                    $declaredFinalResrefs = @(Get-AnimationManifestResrefs $decisionFinalManifest)
                    Require ($declaredFinalResrefs -contains $decisionResref -or $declaredFinalResrefs -contains $decisionRuntimeResref) "Run final QA ne declare pas $decisionResref : $relativeDecisionRun"
                    Require (-not $qaDecisionFinalRuns.ContainsKey($decisionRuntimeResref)) "Decision ingame dupliquee : $decisionRuntimeResref"
                    $runtimeResrefByAsset[$decisionResref] = $decisionRuntimeResref
                    $qaDecisionFinalRuns[$decisionRuntimeResref] = @{
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
                    # Un run source porte l'asset suivi ; le candidat et sa preuve portent le resref runtime.
                    if ($runtimeResrefByAsset.ContainsKey($normalizedAssetId)) { $normalizedAssetId = [string]$runtimeResrefByAsset[$normalizedAssetId] }
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

function Get-SpriteCandidateEntries {
    param([string]$Workspace, [string]$CandidatesPath)

    $result = [System.Collections.Generic.List[object]]::new()
    $register = Read-Json $CandidatesPath
    foreach ($candidate in @($register.candidates | Where-Object { $_.approval_status -eq 'approved-for-release' -and $_.payload_projection.status -eq 'integrated' })) {
        Require ([bool]$candidate.payload_projection.content_manifest_integration) "Projection sprite non integree : $($candidate.candidate_id)"
        $source = $candidate.source_generation
        $evidence = @(
            @{ Path = [string]$source.current_generation; Hash = [string]$source.current_generation_sha256 },
            @{ Path = [string]$source.build_manifest; Hash = [string]$source.build_manifest_sha256 },
            @{ Path = [string]$source.runtime_manifest; Hash = [string]$source.runtime_manifest_sha256 },
            @{ Path = [string]$source.job_file; Hash = [string]$source.job_sha256 },
            @{ Path = [string]$candidate.qa_approval.path; Hash = [string]$candidate.qa_approval.sha256 }
        )
        if ($source.sealed_verification -and $source.sealed_verification_sha256) {
            $evidence += @{ Path = [string]$source.sealed_verification; Hash = [string]$source.sealed_verification_sha256 }
        }
        foreach ($record in $evidence) {
            $path = Join-Path $Workspace ($record.Path.Replace('/', '\'))
            Require (Test-Path -LiteralPath $path -PathType Leaf) "Preuve sprite absente : $($record.Path)"
            Require ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -eq $record.Hash) "Hash de preuve sprite invalide : $($record.Path)"
        }

        $pointer = Read-Json (Join-Path $Workspace ($source.current_generation.Replace('/', '\')))
        $build = Read-Json (Join-Path $Workspace ($source.build_manifest.Replace('/', '\')))
        $proof = if ($source.sealed_verification) { Read-Json (Join-Path $Workspace ($source.sealed_verification.Replace('/', '\'))) } else { $null }
        $runtime = Read-Json (Join-Path $Workspace ($source.runtime_manifest.Replace('/', '\')))
        $expectedIds = @($candidate.asset_scope.animation_ids | ForEach-Object { [string]$_ } | Sort-Object)
        $selectedIds = @($candidate.runtime_contract.selected_animation_ids | ForEach-Object { [string]$_ } | Sort-Object)
        $buildIds = @($build.animation_ids | ForEach-Object { [string]$_ } | Sort-Object)
        Require (-not (Compare-Object $expectedIds $selectedIds)) "Selection runtime sprite incoherente : $($candidate.candidate_id)"
        Require (-not (Compare-Object $expectedIds $buildIds)) "Catalogue sprite non restreint a la selection approuvee : $($candidate.candidate_id)"
        Require (@($buildIds | Where-Object { @($candidate.runtime_contract.excluded_animation_ids) -contains $_ }).Count -eq 0) "Animation sprite exclue presente : $($candidate.candidate_id)"
        $runtimeMode = if ($source.runtime_mode) { [string]$source.runtime_mode } else { 'generation-bound' }
        Require ($pointer.generation_id -eq $source.generation_id -and $build.generation_id -eq $source.generation_id) "Generation sprite incoherente : $($candidate.candidate_id)"
        if ($runtimeMode -eq 'generation-bound') {
            Require ($runtime.generation_id -eq $source.generation_id) "Runtime sprite non lie a la generation : $($candidate.candidate_id)"
        }
        Require ($build.schema -eq 'bg2-upscale-creature-sprite-xn-catalog-pack-v1' -and $build.status -eq 'built-pending-ingame-qa') "Build sprite non finalise : $($candidate.candidate_id)"
        if ($proof) {
            Require ($proof.status -eq 'sealed-verified') "Verification scellee sprite absente : $($candidate.candidate_id)"
        }
        Require ($runtime.status -eq 'built-tested' -and $runtime.tests_status -eq 'passed' -and $runtime.bridge_worker_tests_status -eq 'passed') "Runtime sprite non teste : $($candidate.candidate_id)"
        Require ($runtime.dll_sha256 -eq [string]$candidate.runtime_contract.dll_sha256) "DLL runtime sprite differente du contrat : $($candidate.candidate_id)"
        Require ([int]$build.registry_scale -eq [int]$candidate.runtime_contract.scale -and [int]$build.registry_catalog_version -eq [int]$candidate.runtime_contract.catalog_version -and [int]$build.registry_catalog_shard_version -eq [int]$candidate.runtime_contract.shard_registry_version) "Format de catalogue sprite incoherent : $($candidate.candidate_id)"

        $generationRoot = Split-Path -Parent (Split-Path -Parent (Join-Path $Workspace ($source.build_manifest.Replace('/', '\'))))
        $buildRoot = Join-Path $generationRoot 'build'
        $baseSpec = @{
            ComponentId = [int]$candidate.component_id
            ComponentLabel = [string]$candidate.component_label
            PayloadGroup = [string]$candidate.payload_group
            Area = 'SPRITES'
            SourceRun = [IO.Path]::GetRelativePath($Workspace, $generationRoot).Replace('\', '/')
            Kind = 'sprite'
            DestinationRoot = 'iee-assets/creature-sprites'
            Model = [string]$candidate.runtime_contract.filter
            InstallOrder = [int]$candidate.component_id
            ReplacesComponentOutput = $false
            Scale = 2
        }
        $payloads = @(
            @{ Path = [string]$build.registry_catalog; Hash = [string]$build.registry_catalog_sha256; Bytes = [int64]$build.registry_catalog_bytes }
        ) + @($build.shards | ForEach-Object { @{ Path = [string]$_.registry; Hash = [string]$_.sha256; Bytes = [int64]$_.registry_bytes } })
        $expectedNames = @($payloads | ForEach-Object { [IO.Path]::GetFileName([string]$_.Path) } | Sort-Object)
        Require (@($expectedNames | Sort-Object -Unique).Count -eq $expectedNames.Count) "Noms de payload sprite dupliques : $($candidate.candidate_id)"
        foreach ($payload in $payloads) {
            $file = Get-Item -LiteralPath (Join-Path $buildRoot ($payload.Path.Replace('/', '\'))) -ErrorAction Stop
            Require ($file.Length -eq $payload.Bytes) "Taille payload sprite invalide : $($file.Name)"
            Require ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq $payload.Hash) "Hash payload sprite invalide : $($file.Name)"
            $result.Add((New-ContentEntry $baseSpec $file))
        }
        $packRoot = Join-Path $buildRoot 'iee-assets\creature-sprites'
        $actualNames = @(Get-ChildItem -LiteralPath $packRoot -File | ForEach-Object Name | Sort-Object)
        Require (-not (Compare-Object $expectedNames $actualNames)) "Inventaire du catalogue sprite inattendu : $($candidate.candidate_id)"
    }
    return @($result)
}

function Get-EffectCandidateEntries {
    param([string]$Workspace, [string]$CandidatesPath)

    $result = [System.Collections.Generic.List[object]]::new()
    $register = Read-Json $CandidatesPath
    foreach ($candidate in @($register.candidates | Where-Object { $_.approval_status -eq 'approved-for-release' -and $_.payload_projection.status -eq 'integrated' })) {
        Require ([bool]$candidate.payload_projection.content_manifest_integration) "Projection effet non integree : $($candidate.candidate_id)"
        foreach ($resource in @($candidate.resources)) {
            Require (Test-QAEvidenceHash -Workspace $Workspace -RelativePath ([string]$resource.qa_evidence) -ExpectedHash ([string]$resource.qa_evidence_sha256)) "Preuve QA effet invalide : $($resource.resref)"
        }
        $packRoot = Join-Path $Workspace ($candidate.runtime_pack.path.Replace('/', '\'))
        $manifestPath = Join-Path $packRoot ([string]$candidate.runtime_pack.manifest)
        Require (Test-Path -LiteralPath $manifestPath -PathType Leaf) "Manifest effet absent : $($candidate.candidate_id)"
        Require ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash -eq [string]$candidate.runtime_pack.manifest_sha256) "Hash manifest effet invalide : $($candidate.candidate_id)"
        $pack = Read-Json $manifestPath
        $expectedResrefs = @($candidate.resources | ForEach-Object { ([string]$_.resref).ToUpperInvariant() } | Sort-Object)
        $packResrefs = @($pack.resources | ForEach-Object { ([string]$_.resref).ToUpperInvariant() } | Sort-Object)
        Require (-not (Compare-Object $expectedResrefs $packResrefs)) "Ressources du pack effet incoherentes : $($candidate.candidate_id)"
        Require ($pack.schema -eq 'bg2-upscale-effect-animation-runtime-pack-v1' -and $pack.status -eq 'completed' -and [int]$pack.scale -eq 4) "Pack effet non finalise : $($candidate.candidate_id)"
        Require ([string]$pack.registry -eq [string]$candidate.runtime_pack.registry -and [int]$pack.registry_version -eq [int]$candidate.runtime_pack.registry_version -and [int64]$pack.registry_bytes -eq [int64]$candidate.runtime_pack.registry_bytes -and [string]$pack.registry_sha256 -eq [string]$candidate.runtime_pack.registry_sha256) "Registre effet incoherent : $($candidate.candidate_id)"

        $baseSpec = @{
            ComponentId = [int]$candidate.component_id
            ComponentLabel = [string]$candidate.component_label
            PayloadGroup = [string]$candidate.payload_group
            Area = 'EFFECTS'
            SourceRun = [string]$candidate.runtime_pack.path
            Kind = 'effect'
            DestinationRoot = 'iee-assets/effects'
            Model = "EffectAnimationRuntimeV$([int]$pack.registry_version)"
            InstallOrder = [int]$candidate.component_id
            ReplacesComponentOutput = $false
            Scale = 4
        }
        $expectedNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($name in @([string]$candidate.runtime_pack.manifest, [string]$candidate.runtime_pack.registry)) { [void]$expectedNames.Add($name) }
        $result.Add((New-ContentEntry $baseSpec (Get-Item -LiteralPath $manifestPath)))
        $registryFile = Get-Item -LiteralPath (Join-Path $packRoot ([string]$pack.registry)) -ErrorAction Stop
        Require ($registryFile.Length -eq [int64]$pack.registry_bytes -and (Get-FileHash -LiteralPath $registryFile.FullName -Algorithm SHA256).Hash -eq [string]$pack.registry_sha256) "Payload registre effet invalide : $($candidate.candidate_id)"
        $result.Add((New-ContentEntry $baseSpec $registryFile))
        foreach ($frame in @($pack.frames)) {
            $name = [string]$frame.asset
            Require ($name -match '^EFX4-[A-Z0-9_]{1,8}-frame[0-9]{3}[.]rgba$') "Nom de frame effet invalide : $name"
            [void]$expectedNames.Add($name)
            $file = Get-Item -LiteralPath (Join-Path $packRoot $name) -ErrorAction Stop
            Require ($file.Length -eq [int64]$frame.bytes -and (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq [string]$frame.sha256) "Payload frame effet invalide : $name"
            $result.Add((New-ContentEntry $baseSpec $file))
        }
        $actualNames = @(Get-ChildItem -LiteralPath $packRoot -File | ForEach-Object Name | Sort-Object)
        Require (-not (Compare-Object (@($expectedNames | Sort-Object)) $actualNames)) "Inventaire du pack effet inattendu : $($candidate.candidate_id)"
    }
    return @($result)
}

# All map variants are now explicit data; historical component IDs remain stable.
$candidateMapSpecs = @()
if (-not $isAnimationDelta) {
    Require (Test-Path -LiteralPath $MapCandidatesPath -PathType Leaf) "Registre candidats map absent : $MapCandidatesPath"
    & python (Join-Path $WorkspaceRoot 'pipeline/scripts/verify_map_release_candidates.py') --workspace-root $WorkspaceRoot --candidates $MapCandidatesPath --assemblies $MapAssembliesPath --metadata-only
    Require ($LASTEXITCODE -eq 0) 'Acquired map selection / final water assembly verification failed.'
    $candidateMapSpecs = @(Import-Csv -LiteralPath $MapCandidatesPath | ForEach-Object {
        $area = ([string]$_.area).Trim().ToUpperInvariant()
        Require ($area -match '^(AR|OH)[0-9]{4}N?$') "Zone candidate map invalide : $area"
        $baseArea = $area -replace 'N$',''
        $sourcePath = ([string]$_.source_path).Trim().Replace('\', '/')
        Require ($sourcePath -like "maps/$baseArea/runs/*/*") "Source candidate map invalide : $area / $sourcePath"
        $componentId = [int]$_.component_id
        Require ($componentId -gt 0) "ComponentId candidat map invalide : $area"
        $includeWed = ([string]$_.include_wed).Trim().ToLowerInvariant()
        Require ($includeWed -in @('true', 'false')) "include_wed candidat map invalide : $area"
        @{
            ComponentId = $componentId
            ComponentLabel = "map-$($baseArea.ToLowerInvariant())"
            PayloadGroup = "map-$($baseArea.ToLowerInvariant())"
            Area = $area
            SourceRun = $sourcePath
            Path = $sourcePath
            InstallOrder = $componentId
            IncludeWed = $includeWed -eq 'true'
            Scale = 4
            CandidateModel = [string]$_.model
            CatalogSourcePath = [string]$_.catalog_source_path
            # ReplacesComponentOutput est pose par la normalisation map commune ; le declarer ici
            # aussi ferait echouer la fusion de tables ($spec + @{...} refuse une cle deja presente).
        }
    })
}
$mapSpecs = @($candidateMapSpecs)
$duplicateMapAreas = @($mapSpecs | Group-Object Area | Where-Object Count -gt 1 | ForEach-Object Name)
Require ($duplicateMapAreas.Count -eq 0) "Variantes map candidates dupliquees : $($duplicateMapAreas -join ', ')"
foreach ($group in @($mapSpecs | Group-Object ComponentId)) {
    $labels = @($group.Group | ForEach-Object { [string]$_.ComponentLabel } | Sort-Object -Unique)
    $payloadGroups = @($group.Group | ForEach-Object { [string]$_.PayloadGroup } | Sort-Object -Unique)
    $baseAreas = @($group.Group | ForEach-Object { ([string]$_.Area) -replace 'N$','' } | Sort-Object -Unique)
    Require ($labels.Count -eq 1 -and $payloadGroups.Count -eq 1 -and $baseAreas.Count -eq 1) "ComponentId map partage entre zones incoherentes : $($group.Name)"
}

# The CSV proves production/QA state. Package inclusion is independent: only the historical
# explicit map candidates are compiled. Every included map must still match the CSV.
if (-not $isAnimationDelta) {
    $areasCsv = Join-Path $WorkspaceRoot 'areas.csv'
    if (-not (Test-Path -LiteralPath $areasCsv -PathType Leaf)) { throw "Registre des zones absent : $areasCsv" }
    $validatedAreas = Import-Csv -LiteralPath $areasCsv | Where-Object { $_.area_id -match '^(AR|OH)\d{4}$' }
    $areasById = @{}
    foreach ($area in $validatedAreas) { $areasById[[string]$area.area_id] = $area }
    # The release may select a reviewed sub-build below the current run, but it may never silently
    # package another run.
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
        $path = ([string]$spec.CatalogSourcePath).Replace('\', '/')
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
        $model = if ([string]::IsNullOrWhiteSpace([string]$spec.CandidateModel)) { 'SeedVR2-7B-LAB' } else { [string]$spec.CandidateModel }
        $normalized = $spec + @{ Kind = 'map'; DestinationRoot = 'override'; Model = $model; ReplacesComponentOutput = $false }
        $extensions = if ($spec.IncludeWed) { @('.TIS', '.PVRZ', '.WED') } else { @('.TIS', '.PVRZ') }
        $files = Get-ChildItem -LiteralPath $sourceDirectory -File | Where-Object { $_.Extension -in $extensions } | Sort-Object Name
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
if (-not $isAnimationDelta) {
    foreach ($entry in @(Get-SpriteCandidateEntries -Workspace $WorkspaceRoot -CandidatesPath $SpriteCandidatesPath)) {
        $entries.Add($entry)
    }
    foreach ($entry in @(Get-EffectCandidateEntries -Workspace $WorkspaceRoot -CandidatesPath $EffectCandidatesPath)) {
        $entries.Add($entry)
    }
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
    entries = @($entries | Sort-Object { [int]$_['component_id'] }, { [int]$_['install_order'] }, { [string]$_['destination'] }, { [string]$_['source'] })
}

Write-BG2HDAtomicUtf8NoBomFile -Path $OutputPath -Text (($manifest | ConvertTo-Json -Depth 8) + [Environment]::NewLine)
Write-Output "Wrote $($entries.Count) entries to $OutputPath"
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
