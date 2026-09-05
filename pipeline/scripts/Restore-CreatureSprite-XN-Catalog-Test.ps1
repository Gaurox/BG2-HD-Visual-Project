[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile,
    [switch]$VerifyOnly,
    [Alias('RecoverInstalling')]
    [switch]$RecoverInterrupted
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Le fichier d'installation expose ses validateurs sans exécuter son workflow
# lorsqu'il est dot-sourcé. Cela garde un seul parseur fail-closed pour les deux
# opérations transactionnelles.
$restoreVerifyOnly = [bool]$VerifyOnly
$restoreRecoverInterrupted = [bool]$RecoverInterrupted
. (Join-Path $PSScriptRoot 'Install-CreatureSprite-XN-Catalog-Test.ps1') `
    -JobFile $JobFile
$VerifyOnly = $restoreVerifyOnly
$RecoverInterrupted = $restoreRecoverInterrupted

# Une restauration consomme une génération déjà scellée. Ces validateurs
# contrôlent toute sa provenance déclarée sans rouvrir les sources de build,
# qui peuvent légitimement avoir évolué après l'installation.
function Resolve-SealedProjectPath([string]$Value, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Value)) { throw "$Label est vide." }
    $full = if ([System.IO.Path]::IsPathRooted($Value)) {
        [System.IO.Path]::GetFullPath($Value)
    } else {
        Resolve-WorkspaceRelativePath $Value
    }
    if (-not (Test-PathInsideRoot $full $script:WorkspaceRoot)) {
        throw "$Label sort du workspace."
    }
    return $full
}

function Assert-SealedJobId([string]$Value, [string]$Label) {
    if ($Value -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$') {
        throw "$Label invalide."
    }
}

function Assert-SealedSourceMembers($Build, $Catalog) {
    $members = @(Get-RequiredProperty $Build 'source_members' 'build')
    if ($members.Count -lt 1 -or $members.Count -gt 16384) {
        throw 'build.source_members hors limites.'
    }
    $seenJobs = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($member in $members) {
        Assert-ExactPropertyNames $member @(
            'job_file', 'job_sha256', 'job_id', 'animation_id', 'runtime_profile',
            'build_manifest', 'build_manifest_sha256', 'component_indices', 'bam_prefixes'
        ) 'build.source_members[]'
        $memberJobPath = Resolve-SealedProjectPath `
            ([string](Get-RequiredProperty $member 'job_file' 'build.source_members[]')) `
            'build.source_members[].job_file'
        if (-not $seenJobs.Add($memberJobPath)) {
            throw "Job source scellé dupliqué : $memberJobPath"
        }
        Assert-HashText ([string](Get-RequiredProperty $member 'job_sha256' 'build.source_members[]')) `
            'build.source_members[].job_sha256'
        Assert-SealedJobId ([string](Get-RequiredProperty $member 'job_id' 'build.source_members[]')) `
            'build.source_members[].job_id'
        [void](Resolve-SealedProjectPath `
            ([string](Get-RequiredProperty $member 'build_manifest' 'build.source_members[]')) `
            'build.source_members[].build_manifest')
        Assert-HashText `
            ([string](Get-RequiredProperty $member 'build_manifest_sha256' 'build.source_members[]')) `
            'build.source_members[].build_manifest_sha256'

        $animationId = Convert-AnimationId `
            (Get-RequiredProperty $member 'animation_id' 'build.source_members[]') `
            'build.source_members[].animation_id'
        $binaryAnimations = @($Catalog.animations | Where-Object { $_.animation_id -eq $animationId })
        if ($binaryAnimations.Count -ne 1) {
            throw "Animation du membre scellé absente du catalogue : $(Format-AnimationId $animationId)"
        }
        $binaryAnimation = $binaryAnimations[0]
        $runtimeProfile = [string](Get-RequiredProperty $member 'runtime_profile' 'build.source_members[]')
        if ($runtimeProfile -notin @(
                'character-bg2ee-2.7.3.0', 'monster-icewind-bg2ee-2.7.3.0')) {
            throw "Profil runtime source non supporté : $runtimeProfile"
        }
        Assert-OrdinalEqual $runtimeProfile (Get-OwnerRuntimeProfile $binaryAnimation.owner) `
            'build.source_members[].runtime_profile'

        $componentIndices = @(Get-RequiredProperty $member 'component_indices' 'build.source_members[]')
        if ($componentIndices.Count -lt 1) { throw 'Membre source scellé sans composant.' }
        $seenComponents = @{}
        foreach ($rawIndex in $componentIndices) {
            $index = [int]$rawIndex
            if ($index -lt 0 -or $index -ge $Catalog.component_count -or
                $seenComponents.ContainsKey([string]$index)) {
                throw 'Index composant source scellé invalide ou dupliqué.'
            }
            $seenComponents[[string]$index] = $true
        }
        $memberComponents = @(($componentIndices | ForEach-Object { [int]$_ }) | Sort-Object) -join '|'
        $binaryComponents = @(($binaryAnimation.component_indices | ForEach-Object { [int]$_ }) |
            Sort-Object) -join '|'
        Assert-OrdinalEqual $memberComponents $binaryComponents `
            'build.source_members[].component_indices'
        $prefixes = Assert-StringArray `
            (Get-RequiredProperty $member 'bam_prefixes' 'build.source_members[]') `
            'build.source_members[].bam_prefixes'
        foreach ($prefix in $prefixes) {
            if ($prefix -notmatch '^[A-Z0-9_]{1,8}$') {
                throw "Préfixe BAM source invalide : $prefix"
            }
        }
    }

    $locks = Get-RequiredProperty $Build 'locks' 'build'
    foreach ($name in @(
            'input_lock_sha256', 'engine_source_contract_sha256', 'baldur_real_sha256')) {
        Assert-HashText ([string](Get-RequiredProperty $locks $name 'build.locks')) "build.locks.$name"
    }
    if ([int](Get-RequiredProperty $locks 'member_count' 'build.locks') -ne $members.Count -or
        [int](Get-RequiredProperty $locks 'leaf_job_count' 'build.locks') -lt $members.Count -or
        [int]$locks.leaf_job_count -gt 16384) {
        throw 'Compteurs build.locks incompatibles avec source_members.'
    }
    return $members
}

function Assert-SealedInputLock($Build, $Runtime, $Job, [string]$JobPath,
        [string]$JobSha256, [string]$GenerationId, [int]$Scale,
        [string]$BaldurRealSha256) {
    $locks = Get-RequiredProperty $Build 'locks' 'build'
    $inputLock = Get-RequiredProperty $locks 'input_lock' 'build.locks'
    Assert-ExactPropertyNames $inputLock @(
        'schema', 'job_file', 'job_sha256', 'method', 'baldur_real_sha256',
        'engine_source', 'engine_source_contract_sha256', 'catalog_builder',
        'catalog_builder_sha256', 'members', 'leaf_jobs'
    ) 'build.locks.input_lock'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'schema' 'input_lock')) `
        'bg2-upscale-creature-sprite-xn-catalog-input-lock-v1' 'input_lock.schema'

    $buildJob = Resolve-SealedProjectPath `
        ([string](Get-RequiredProperty $Build 'job_file' 'build')) 'build.job_file'
    $lockJob = Resolve-SealedProjectPath `
        ([string](Get-RequiredProperty $inputLock 'job_file' 'input_lock')) 'input_lock.job_file'
    foreach ($declaredJob in @($buildJob, $lockJob)) {
        if (-not [string]::Equals($declaredJob, $JobPath,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'La génération scellée ne désigne pas le JobFile fourni.'
        }
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'job_sha256' 'input_lock')) `
        $JobSha256 'input_lock.job_sha256'
    Assert-UpscaleContract (Get-RequiredProperty $inputLock 'method' 'input_lock') $Scale `
        'input_lock.method'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'baldur_real_sha256' 'input_lock')) `
        $BaldurRealSha256 'input_lock.baldur_real_sha256'

    $jobEngine = Resolve-SealedProjectPath `
        ([string](Get-RequiredProperty (Get-RequiredProperty $Job 'paths' 'job') 'engine_source' `
            'job.paths')) 'job.paths.engine_source'
    $runtimeEngine = Resolve-SealedProjectPath `
        ([string](Get-RequiredProperty $Runtime 'engine_source' 'runtime')) 'runtime.engine_source'
    $lockEngine = Resolve-SealedProjectPath `
        ([string](Get-RequiredProperty $inputLock 'engine_source' 'input_lock')) 'input_lock.engine_source'
    if (-not [string]::Equals($jobEngine, $runtimeEngine,
            [System.StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals($jobEngine, $lockEngine,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Les chemins engine_source scellés sont incohérents.'
    }
    $engineContract = [string](Get-RequiredProperty $inputLock `
        'engine_source_contract_sha256' 'input_lock')
    Assert-HashText $engineContract 'input_lock.engine_source_contract_sha256'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $Runtime `
            'engine_source_contract_sha256' 'runtime')) $engineContract `
        'runtime.engine_source_contract_sha256'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $locks `
            'engine_source_contract_sha256' 'build.locks')) $engineContract `
        'build.locks.engine_source_contract_sha256'

    $builder = Resolve-SealedProjectPath `
        ([string](Get-RequiredProperty $inputLock 'catalog_builder' 'input_lock')) `
        'input_lock.catalog_builder'
    $expectedBuilder = [System.IO.Path]::GetFullPath(
        (Join-Path $script:WorkspaceRoot 'pipeline\scripts\run_creature_sprite_x2.py'))
    if (-not [string]::Equals($builder, $expectedBuilder,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'input_lock.catalog_builder non canonique.'
    }
    Assert-HashText ([string](Get-RequiredProperty $inputLock `
            'catalog_builder_sha256' 'input_lock')) 'input_lock.catalog_builder_sha256'

    $memberLocks = @(Get-RequiredProperty $inputLock 'members' 'input_lock')
    $sourceMembers = @(Get-RequiredProperty $Build 'source_members' 'build')
    if ($memberLocks.Count -ne $sourceMembers.Count -or
        [int](Get-RequiredProperty $locks 'member_count' 'build.locks') -ne $memberLocks.Count) {
        throw 'input_lock.members count incompatible.'
    }
    $seenMemberJobs = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    for ($i = 0; $i -lt $memberLocks.Count; $i++) {
        $entry = $memberLocks[$i]
        Assert-ExactPropertyNames $entry @(
            'job_file', 'job_sha256', 'job_id', 'build_manifest', 'build_manifest_sha256'
        ) 'input_lock.members[]'
        $memberJob = Resolve-SealedProjectPath `
            ([string](Get-RequiredProperty $entry 'job_file' 'input_lock.members[]')) `
            'input_lock.members[].job_file'
        if (-not $seenMemberJobs.Add($memberJob)) {
            throw "Membre input lock scellé dupliqué : $memberJob"
        }
        Assert-SealedJobId ([string](Get-RequiredProperty $entry 'job_id' 'input_lock.members[]')) `
            'input_lock.members[].job_id'
        Assert-HashText ([string](Get-RequiredProperty $entry 'job_sha256' 'input_lock.members[]')) `
            'input_lock.members[].job_sha256'
        [void](Resolve-SealedProjectPath `
            ([string](Get-RequiredProperty $entry 'build_manifest' 'input_lock.members[]')) `
            'input_lock.members[].build_manifest')
        Assert-HashText `
            ([string](Get-RequiredProperty $entry 'build_manifest_sha256' 'input_lock.members[]')) `
            'input_lock.members[].build_manifest_sha256'
        foreach ($name in @(
                'job_file', 'job_sha256', 'job_id', 'build_manifest', 'build_manifest_sha256')) {
            Assert-OrdinalEqual ([string](Get-RequiredProperty $entry $name 'input_lock.members[]')) `
                ([string](Get-RequiredProperty $sourceMembers[$i] $name 'build.source_members[]')) `
                "input_lock.members[$i].$name"
        }
    }

    $leafLocks = @(Get-RequiredProperty $inputLock 'leaf_jobs' 'input_lock')
    if ($leafLocks.Count -ne [int](Get-RequiredProperty $locks 'leaf_job_count' 'build.locks') -or
        $leafLocks.Count -lt $memberLocks.Count -or $leafLocks.Count -gt 16384) {
        throw 'input_lock.leaf_jobs count incompatible.'
    }
    $seenLeafJobs = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    $seenPayloads = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $leafLocks) {
        Assert-ExactPropertyNames $entry @(
            'job_file', 'job_sha256', 'job_id', 'source_manifest',
            'source_manifest_sha256', 'build_manifest', 'build_manifest_sha256', 'payloads'
        ) 'input_lock.leaf_jobs[]'
        $leafJob = Resolve-SealedProjectPath `
            ([string](Get-RequiredProperty $entry 'job_file' 'input_lock.leaf_jobs[]')) `
            'input_lock.leaf_jobs[].job_file'
        if (-not $seenLeafJobs.Add($leafJob)) {
            throw "Leaf job scellé dupliqué : $leafJob"
        }
        Assert-SealedJobId ([string](Get-RequiredProperty $entry 'job_id' 'input_lock.leaf_jobs[]')) `
            'input_lock.leaf_jobs[].job_id'
        Assert-HashText ([string](Get-RequiredProperty $entry 'job_sha256' 'input_lock.leaf_jobs[]')) `
            'input_lock.leaf_jobs[].job_sha256'
        foreach ($pair in @(
                @('source_manifest', 'source_manifest_sha256'),
                @('build_manifest', 'build_manifest_sha256'))) {
            [void](Resolve-SealedProjectPath `
                ([string](Get-RequiredProperty $entry $pair[0] 'input_lock.leaf_jobs[]')) `
                "input_lock.leaf_jobs[].$($pair[0])")
            Assert-HashText ([string](Get-RequiredProperty $entry $pair[1] `
                    'input_lock.leaf_jobs[]')) "input_lock.leaf_jobs[].$($pair[1])"
        }
        $payloads = @(Get-RequiredProperty $entry 'payloads' 'input_lock.leaf_jobs[]')
        if ($payloads.Count -lt 1 -or $payloads.Count -gt 16385) {
            throw 'input_lock.leaf_jobs[].payloads hors limites.'
        }
        foreach ($payload in $payloads) {
            Assert-ExactPropertyNames $payload @('path', 'sha256', 'crc32', 'bytes') `
                'input_lock.leaf_jobs[].payloads[]'
            $payloadPath = Resolve-SealedProjectPath `
                ([string](Get-RequiredProperty $payload 'path' 'input_lock.leaf_jobs[].payloads[]')) `
                'input_lock.leaf_jobs[].payloads[].path'
            if (-not $seenPayloads.Add($payloadPath)) {
                throw "Payload leaf scellé dupliqué : $payloadPath"
            }
            Assert-HashText ([string](Get-RequiredProperty $payload 'sha256' `
                    'input_lock.leaf_jobs[].payloads[]')) `
                'input_lock.leaf_jobs[].payloads[].sha256'
            $rawPayloadBytes = Get-RequiredProperty $payload 'bytes' `
                'input_lock.leaf_jobs[].payloads[]'
            if (($rawPayloadBytes -isnot [int] -and $rawPayloadBytes -isnot [long]) -or
                [long]$rawPayloadBytes -le 0) {
                throw 'Payload leaf scellé vide.'
            }
            $rawPayloadCrc32 = Get-RequiredProperty $payload 'crc32' `
                'input_lock.leaf_jobs[].payloads[]'
            if (($rawPayloadCrc32 -isnot [int] -and $rawPayloadCrc32 -isnot [long]) -or
                [long]$rawPayloadCrc32 -lt 0 -or [long]$rawPayloadCrc32 -gt [uint32]::MaxValue) {
                throw 'input_lock.leaf_jobs[].payloads[].crc32 doit être un uint32 JSON.'
            }
        }
    }

    $actualLockSha256 = Get-CanonicalJsonSha256 $inputLock
    Assert-OrdinalEqual $actualLockSha256 `
        ([string](Get-RequiredProperty $locks 'input_lock_sha256' 'build.locks')) `
        'build.locks.input_lock_sha256'
    Assert-OrdinalEqual $actualLockSha256 $GenerationId 'generation_id/input_lock_sha256'
}

function New-CurrentPointerFromSealedState($PreviousState, [string]$RunRoot) {
    $generationId = [string](Get-RequiredProperty $PreviousState 'generation_id' 'previous state')
    $jobSha256 = [string](Get-RequiredProperty $PreviousState 'job_sha256' 'previous state')
    Assert-HashText $generationId 'previous state.generation_id'
    Assert-HashText $jobSha256 'previous state.job_sha256'

    $buildPath = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $PreviousState 'build_manifest' 'previous state')) `
        'previous state.build_manifest'
    $runtimePath = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $PreviousState 'runtime_manifest' 'previous state')) `
        'previous state.runtime_manifest'
    $generationDir = Split-Path -Parent (Split-Path -Parent $buildPath)
    $expectedRoot = (Join-Path $RunRoot 'generations').TrimEnd('\') + '\'
    if (-not $generationDir.StartsWith($expectedRoot,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'La génération précédente sort du run_dir.'
    }
    $expectedGenerationDir = [System.IO.Path]::GetFullPath(
        (Join-Path $RunRoot "generations\$($generationId.ToLowerInvariant())"))
    if (-not [string]::Equals($generationDir, $expectedGenerationDir,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Le dossier de la génération précédente ne correspond pas à generation_id.'
    }
    $expectedBuild = [System.IO.Path]::GetFullPath(
        (Join-Path $generationDir 'build\build-manifest.json'))
    $expectedRuntime = [System.IO.Path]::GetFullPath(
        (Join-Path $generationDir 'runtime\runtime-manifest.json'))
    if (-not [string]::Equals($buildPath, $expectedBuild,
            [System.StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals($runtimePath, $expectedRuntime,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Chemins des manifests de la génération précédente non canoniques.'
    }

    $buildSha256 = [string](Get-RequiredProperty $PreviousState `
        'build_manifest_sha256' 'previous state')
    $runtimeSha256 = [string](Get-RequiredProperty $PreviousState `
        'runtime_manifest_sha256' 'previous state')
    Assert-ExpectedHash $buildPath $buildSha256 'Build de la génération précédente'
    Assert-ExpectedHash $runtimePath $runtimeSha256 'Runtime de la génération précédente'
    try { $build = Get-Content -LiteralPath $buildPath -Raw | ConvertFrom-Json }
    catch { throw "Build de la génération précédente illisible : $($_.Exception.Message)" }
    try { $runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json }
    catch { throw "Runtime de la génération précédente illisible : $($_.Exception.Message)" }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'schema' 'previous build')) `
        'bg2-upscale-creature-sprite-xn-catalog-pack-v1' 'previous build.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'schema' 'previous runtime')) `
        'bg2-upscale-creature-sprite-runtime-v1' 'previous runtime.schema'
    foreach ($manifest in @(
            [pscustomobject]@{ value = $build; label = 'previous build' },
            [pscustomobject]@{ value = $runtime; label = 'previous runtime' })) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $manifest.value 'job_sha256' `
                $manifest.label)) $jobSha256 "$($manifest.label).job_sha256"
        Assert-OrdinalEqual ([string](Get-RequiredProperty $manifest.value 'generation_id' `
                $manifest.label)) $generationId "$($manifest.label).generation_id"
    }
    $locks = Get-RequiredProperty $build 'locks' 'previous build'
    $inputLock = Get-RequiredProperty $locks 'input_lock' 'previous build.locks'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'job_sha256' `
            'previous input_lock')) $jobSha256 'previous input_lock.job_sha256'
    $canonicalGenerationId = Get-CanonicalJsonSha256 $inputLock
    Assert-OrdinalEqual $canonicalGenerationId `
        ([string](Get-RequiredProperty $locks 'input_lock_sha256' 'previous build.locks')) `
        'previous build.locks.input_lock_sha256'
    Assert-OrdinalEqual $canonicalGenerationId $generationId `
        'previous state.generation_id/input_lock_sha256'

    return [ordered]@{
        schema = 'bg2-upscale-creature-sprite-xn-catalog-current-generation-v1'
        generation_id = $generationId
        job_sha256 = $jobSha256
        generation_dir = Get-ProjectRelativePath $generationDir
        build_manifest = 'build/build-manifest.json'
        build_manifest_sha256 = $buildSha256
        runtime_manifest = 'runtime/runtime-manifest.json'
        runtime_manifest_sha256 = $runtimeSha256
    }
}

$jobPath = (Resolve-Path -LiteralPath $JobFile).Path
$jobPath = Resolve-ProjectPath $jobPath 'JobFile'
$jobSha256 = Get-Sha256 $jobPath
try { $job = Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json }
catch { throw "Job JSON illisible : $($_.Exception.Message)" }
Assert-OrdinalEqual ([string](Get-RequiredProperty $job 'schema' 'job')) `
    'bg2-upscale-creature-sprite-xn-catalog-job-v1' 'job.schema'
$jobId = [string](Get-RequiredProperty $job 'job_id' 'job')
Assert-SealedJobId $jobId 'job.job_id'
$paths = Get-RequiredProperty $job 'paths' 'job'
$runRoot = Resolve-ProjectPath ([string](Get-RequiredProperty $paths 'run_dir' 'job.paths')) `
    'job.paths.run_dir'
$gameCandidate = Resolve-AnyPath ([string](Get-RequiredProperty $paths 'game_root' 'job.paths')) `
    'job.paths.game_root'
if (-not (Test-Path -LiteralPath $gameCandidate -PathType Container)) {
    throw "GameRoot absent : $gameCandidate"
}
$gameRoot = (Resolve-Path -LiteralPath $gameCandidate).Path.TrimEnd('\')
$script:ActiveGameRoot = $gameRoot
Assert-NoReparseComponents $gameRoot $gameRoot 'GameRoot'

$mutex = Enter-GameMutationMutex $gameRoot
try {
    if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
        throw "Le jeu ou InfinityLoader est en cours d'execution."
    }
    $activeStatePath = Join-Path $runRoot 'ingame-installation\active-test.json'
    Assert-SafeKnownPath $activeStatePath 'État catalogue actif'
    if (-not (Test-Path -LiteralPath $activeStatePath -PathType Leaf)) {
        throw "État catalogue absent : $activeStatePath"
    }
    try { $state = Get-Content -LiteralPath $activeStatePath -Raw | ConvertFrom-Json }
    catch { throw "État catalogue illisible : $($_.Exception.Message)" }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $state 'schema' 'state')) `
        'bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1' 'state.schema'
    $interrupted = [string]$state.status -in @('installing', 'restoring')
    if ($interrupted -and -not $RecoverInterrupted) {
        throw "État $($state.status) détecté ; relancer avec -RecoverInterrupted."
    }
    if (-not $interrupted -and [string]$state.status -notin @(
            'installed-pending-qa', 'validated-installed', 'qa-failed')) {
        throw "État non restaurable : $($state.status)"
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $state 'job_id' 'state')) $jobId 'state.job_id'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $state 'job_sha256' 'state')) $jobSha256 `
        'state.job_sha256'
    $stateJobPath = Resolve-ProjectPath ([string](Get-RequiredProperty $state 'job_file' 'state')) `
        'state.job_file'
    if (-not [string]::Equals($stateJobPath, $jobPath,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'state.job_file ne désigne pas le JobFile fourni.'
    }
    if (-not [string]::Equals([string](Get-RequiredProperty $state 'game_root' 'state'), $gameRoot,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'state.game_root diffère du job.'
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $state 'registry_layout' 'state')) 'catalog' `
        'state.registry_layout'
    $upscale = Get-RequiredProperty $job 'upscale' 'job'
    $scale = [int](Get-RequiredProperty $upscale 'scale' 'job.upscale')
    if ($scale -notin @(2, 4)) { throw 'job.upscale.scale doit valoir 2 ou 4.' }
    Assert-UpscaleContract $upscale $scale 'job.upscale'
    Assert-UpscaleContract (Get-RequiredProperty $state 'method' 'state') $scale 'state.method'
    $stateCatalogVersion = [uint32](Get-RequiredProperty $state 'catalog_version' 'state')
    if ([uint32](Get-RequiredProperty $state 'catalog_scale' 'state') -ne $scale -or
        $stateCatalogVersion -notin @(1, 2) -or
        [string](Get-RequiredProperty $state 'catalog_magic' 'state') -cne 'IEECSNC') {
        throw "Contrat catalogue de l'etat incompatible."
    }
    $stateShardVersion = if ($null -ne $state.PSObject.Properties['shard_registry_version']) {
        [uint32]$state.shard_registry_version
    } elseif ($stateCatalogVersion -eq 1) { [uint32]3 } else {
        throw 'state.shard_registry_version absent pour un catalogue V2.'
    }
    if ($stateShardVersion -notin @(3, 5) -or
        ($stateCatalogVersion -eq 1 -and $stateShardVersion -ne 3) -or
        ($stateShardVersion -eq 5 -and $stateCatalogVersion -ne 2)) {
        throw 'Couplage catalogue/shard de etat incompatible.'
    }

    # Le pointeur courant est validé même s'il désigne déjà une génération
    # construite après celle installée. La restauration reste liée aux manifests
    # immuables consignés dans l'état actif, pas arbitrairement au dernier build.
    $pointerPath = Join-Path $runRoot 'current-generation.json'
    Assert-SafeKnownPath $pointerPath 'Pointeur courant'
    if (-not (Test-Path -LiteralPath $pointerPath -PathType Leaf)) { throw 'Pointeur courant absent.' }
    $pointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointer 'schema' 'pointer')) `
        'bg2-upscale-creature-sprite-xn-catalog-current-generation-v1' 'pointer.schema'
    Assert-ExactPropertyNames $pointer @(
        'schema', 'generation_id', 'job_sha256', 'generation_dir',
        'build_manifest', 'build_manifest_sha256', 'runtime_manifest',
        'runtime_manifest_sha256'
    ) 'pointer'
    $pointerJobSha256 = [string](Get-RequiredProperty $pointer 'job_sha256' 'pointer')
    Assert-HashText $pointerJobSha256 'pointer.job_sha256'
    $pointerGenerationId = [string](Get-RequiredProperty $pointer 'generation_id' 'pointer')
    Assert-HashText $pointerGenerationId 'pointer.generation_id'
    $pointerGenerationDir = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $pointer 'generation_dir' 'pointer')) 'pointer.generation_dir'
    if (-not $pointerGenerationDir.StartsWith($runRoot.TrimEnd('\') + '\',
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'pointer.generation_dir sort du run_dir.'
    }
    $expectedPointerGenerationDir = [System.IO.Path]::GetFullPath(
        (Join-Path $runRoot "generations\$($pointerGenerationId.ToLowerInvariant())"))
    if (-not [string]::Equals($pointerGenerationDir, $expectedPointerGenerationDir,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'pointer.generation_dir ne correspond pas à pointer.generation_id.'
    }
    Assert-OrdinalEqual (([string](Get-RequiredProperty $pointer 'build_manifest' `
            'pointer')).Replace('\', '/')) 'build/build-manifest.json' 'pointer.build_manifest'
    Assert-OrdinalEqual (([string](Get-RequiredProperty $pointer 'runtime_manifest' `
            'pointer')).Replace('\', '/')) 'runtime/runtime-manifest.json' 'pointer.runtime_manifest'
    $pointerBuild = Resolve-ChildPath $pointerGenerationDir `
        ([string](Get-RequiredProperty $pointer 'build_manifest' 'pointer')) 'pointer.build_manifest'
    $pointerRuntime = Resolve-ChildPath $pointerGenerationDir `
        ([string](Get-RequiredProperty $pointer 'runtime_manifest' 'pointer')) 'pointer.runtime_manifest'
    Assert-ExpectedHash $pointerBuild ([string](Get-RequiredProperty $pointer 'build_manifest_sha256' 'pointer')) `
        'Build du pointeur courant'
    Assert-ExpectedHash $pointerRuntime ([string](Get-RequiredProperty $pointer 'runtime_manifest_sha256' 'pointer')) `
        'Runtime du pointeur courant'
    try { $pointerBuildManifest = Get-Content -LiteralPath $pointerBuild -Raw | ConvertFrom-Json }
    catch { throw "Build du pointeur courant illisible : $($_.Exception.Message)" }
    try { $pointerRuntimeManifest = Get-Content -LiteralPath $pointerRuntime -Raw | ConvertFrom-Json }
    catch { throw "Runtime du pointeur courant illisible : $($_.Exception.Message)" }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointerBuildManifest 'schema' 'pointer build')) `
        'bg2-upscale-creature-sprite-xn-catalog-pack-v1' 'pointer build.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointerRuntimeManifest 'schema' 'pointer runtime')) `
        'bg2-upscale-creature-sprite-runtime-v1' 'pointer runtime.schema'
    foreach ($pointerManifest in @(
            [pscustomobject]@{ value = $pointerBuildManifest; label = 'pointer build' },
            [pscustomobject]@{ value = $pointerRuntimeManifest; label = 'pointer runtime' }
        )) {
        Assert-OrdinalEqual `
            ([string](Get-RequiredProperty $pointerManifest.value 'job_sha256' $pointerManifest.label)) `
            $pointerJobSha256 "$($pointerManifest.label).job_sha256"
        Assert-OrdinalEqual `
            ([string](Get-RequiredProperty $pointerManifest.value 'generation_id' $pointerManifest.label)) `
            $pointerGenerationId "$($pointerManifest.label).generation_id"
    }
    $pointerLocks = Get-RequiredProperty $pointerBuildManifest 'locks' 'pointer build'
    $pointerInputLock = Get-RequiredProperty $pointerLocks 'input_lock' 'pointer build.locks'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointerInputLock 'schema' `
            'pointer input_lock')) 'bg2-upscale-creature-sprite-xn-catalog-input-lock-v1' `
        'pointer input_lock.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointerInputLock 'job_sha256' `
            'pointer input_lock')) $pointerJobSha256 'pointer input_lock.job_sha256'
    $pointerCanonicalGeneration = Get-CanonicalJsonSha256 $pointerInputLock
    Assert-OrdinalEqual $pointerCanonicalGeneration `
        ([string](Get-RequiredProperty $pointerLocks 'input_lock_sha256' 'pointer build.locks')) `
        'pointer build.locks.input_lock_sha256'
    Assert-OrdinalEqual $pointerCanonicalGeneration $pointerGenerationId `
        'pointer.generation_id/input_lock_sha256'

    $buildManifestPath = Resolve-ProjectPath ([string](Get-RequiredProperty $state 'build_manifest' 'state')) `
        'state.build_manifest'
    $runtimeManifestPath = Resolve-ProjectPath ([string](Get-RequiredProperty $state 'runtime_manifest' 'state')) `
        'state.runtime_manifest'
    foreach ($manifestPath in @($buildManifestPath, $runtimeManifestPath)) {
        if (-not $manifestPath.StartsWith((Join-Path $runRoot 'generations').TrimEnd('\') + '\',
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Manifest de l'état hors des générations immuables : $manifestPath"
        }
    }
    $stateGenerationId = [string](Get-RequiredProperty $state 'generation_id' 'state')
    Assert-HashText $stateGenerationId 'state.generation_id'
    $stateGenerationDir = [System.IO.Path]::GetFullPath(
        (Join-Path $runRoot "generations\$($stateGenerationId.ToLowerInvariant())"))
    $expectedStateBuild = [System.IO.Path]::GetFullPath(
        (Join-Path $stateGenerationDir 'build\build-manifest.json'))
    $expectedStateRuntime = [System.IO.Path]::GetFullPath(
        (Join-Path $stateGenerationDir 'runtime\runtime-manifest.json'))
    if (-not [string]::Equals($buildManifestPath, $expectedStateBuild,
            [System.StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals($runtimeManifestPath, $expectedStateRuntime,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Les manifests de l'etat ne correspondent pas à state.generation_id."
    }
    Assert-ExpectedHash $buildManifestPath ([string](Get-RequiredProperty $state 'build_manifest_sha256' 'state')) `
        'Build de la génération installée'
    Assert-ExpectedHash $runtimeManifestPath ([string](Get-RequiredProperty $state 'runtime_manifest_sha256' 'state')) `
        'Runtime de la génération installée'
    $build = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
    $runtime = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'schema' 'build')) `
        'bg2-upscale-creature-sprite-xn-catalog-pack-v1' 'build.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'status' 'build')) `
        'built-pending-ingame-qa' 'build.status'
    foreach ($name in @('job_id', 'job_sha256', 'generation_id')) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $build $name 'build')) `
            ([string](Get-RequiredProperty $state $name 'state')) "build.$name"
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'registry_layout' 'build')) 'catalog' `
        'build.registry_layout'
    Assert-UpscaleContract (Get-RequiredProperty $build 'method' 'build') $scale 'build.method'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'registry_catalog_magic' 'build')) `
        'IEECSNC' 'build.registry_catalog_magic'
    if ([uint32](Get-RequiredProperty $build 'registry_catalog_version' 'build') -ne
            $stateCatalogVersion -or
        [uint32](Get-RequiredProperty $build 'registry_scale' 'build') -ne $scale) {
        throw 'Version/échelle du catalogue build incompatible.'
    }
    $buildShardVersion = if ($null -ne $build.PSObject.Properties['registry_catalog_shard_version']) {
        [uint32]$build.registry_catalog_shard_version
    } elseif ($stateCatalogVersion -eq 1) { [uint32]3 } else { [uint32]0 }
    if ($buildShardVersion -ne $stateShardVersion) {
        throw 'Version shard du build incompatible avec etat.'
    }
    Assert-BuildValidation (Get-RequiredProperty $build 'validation' 'build') $scale `
        $stateCatalogVersion $stateShardVersion
    $buildRoot = Split-Path -Parent $buildManifestPath
    $sourceCatalog = Resolve-ChildPath $buildRoot `
        ([string](Get-RequiredProperty $build 'registry_catalog' 'build')) 'build.registry_catalog'
    $sourceCatalogHash = [string](Get-RequiredProperty $build 'registry_catalog_sha256' 'build')
    Assert-OrdinalEqual $sourceCatalogHash ([string](Get-RequiredProperty $state 'catalog_sha256' 'state')) `
        'state.catalog_sha256'
    Assert-ExpectedHash $sourceCatalog $sourceCatalogHash 'Catalogue source restaurable'
    $catalog = Read-Catalog $sourceCatalog
    if ($catalog.scale -ne $scale -or $catalog.version -ne $stateCatalogVersion -or
        $catalog.bytes -ne [uint64]$state.catalog_bytes) {
        throw 'Catalogue source de restauration incompatible.'
    }
    if ($catalog.version -eq 2) {
        if ([uint32](Get-RequiredProperty $state 'directory_count' 'state') -ne
                $catalog.directory_count -or
            [uint32](Get-RequiredProperty $state 'directory_entry_bytes' 'state') -ne 24 -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $state 'directory_sha256' 'state'),
                [string]$catalog.directory_sha256, [System.StringComparison]::Ordinal)) {
            throw 'Directory V2 de etat incompatible.'
        }
    }
    $catalogArtifacts = Assert-CatalogManifest $build $catalog $buildRoot
    if ($catalog.shard_registry_version -ne $stateShardVersion -or
        ($stateCatalogVersion -eq 2 -and
         [string](Get-RequiredProperty $state 'logical_content_sha256' 'state') -cne
            [string]$catalog.logical_content_sha256)) {
        throw 'Identité logique/storage du catalogue source incompatible avec etat.'
    }
    [void](Assert-SealedSourceMembers $build $catalog)

    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'schema' 'runtime')) `
        'bg2-upscale-creature-sprite-runtime-v1' 'runtime.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'status' 'runtime')) 'built-tested' 'runtime.status'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'tests_status' 'runtime')) 'passed' `
        'runtime.tests_status'
    foreach ($name in @('job_id', 'job_sha256', 'generation_id')) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime $name 'runtime')) `
            ([string](Get-RequiredProperty $state $name 'state')) "runtime.$name"
    }
    Assert-UpscaleContract (Get-RequiredProperty $runtime 'method' 'runtime') $scale 'runtime.method'
    Assert-ExactStringSet (Get-RequiredProperty $runtime 'runtime_profiles' 'runtime') `
        (Get-RequiredProperty $build 'runtime_profiles' 'build') 'runtime.runtime_profiles'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_magic' 'runtime')) 'IEECSNC' `
        'runtime.catalog_magic'
    if ([uint32](Get-RequiredProperty $runtime 'catalog_version' 'runtime') -ne
            $stateCatalogVersion -or
        [uint32](Get-RequiredProperty $runtime 'catalog_shard_registry_version' 'runtime') -ne
            $stateShardVersion) {
        throw 'Runtime catalogue version incompatible.'
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_shard_registry_magic' 'runtime')) `
        'IEECSXN' 'runtime.catalog_shard_registry_magic'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_shard_animation_id_sentinel' 'runtime')) `
        '0xFFFF' 'runtime.catalog_shard_animation_id_sentinel'
    Assert-RuntimeLimits (Get-RequiredProperty $runtime 'catalog_limits' 'runtime') $stateCatalogVersion
    if ($stateCatalogVersion -eq 2) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'bridge_worker_tests_status' 'runtime')) `
            'passed' 'runtime.bridge_worker_tests_status'
    }
    if ($stateShardVersion -eq 5) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_frame_storage' 'runtime')) `
            'XPRESS_HUFF-or-raw-per-frame-v1' 'runtime.catalog_frame_storage'
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_logical_content_sha256' `
                'runtime')) ([string]$catalog.logical_content_sha256) `
            'runtime.catalog_logical_content_sha256'
    }
    if ($stateCatalogVersion -eq 2) {
        if ([uint32](Get-RequiredProperty $runtime 'catalog_directory_count' 'runtime') -ne
                $catalog.directory_count -or
            [uint32](Get-RequiredProperty $runtime 'catalog_directory_entry_bytes' 'runtime') -ne 24 -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $runtime 'catalog_directory_sha256' 'runtime'),
                [string]$catalog.directory_sha256, [System.StringComparison]::Ordinal)) {
            throw 'Directory V2 du runtime incompatible.'
        }
    }
    $runtimeRoot = Split-Path -Parent $runtimeManifestPath
    $sourceDll = Resolve-ChildPath $runtimeRoot ([string](Get-RequiredProperty $runtime 'dll' 'runtime')) `
        'runtime.dll'
    $sourceDllHash = [string](Get-RequiredProperty $runtime 'dll_sha256' 'runtime')
    Assert-OrdinalEqual $sourceDllHash ([string](Get-RequiredProperty $state 'source_dll_sha256' 'state')) `
        'state.source_dll_sha256'
    Assert-ExpectedHash $sourceDll $sourceDllHash 'DLL source restaurable'
    $expectedExeHash = [string](Get-RequiredProperty $job.compatibility 'baldur_real_sha256' 'job.compatibility')
    Assert-ExpectedHash (Join-Path $gameRoot 'BaldurReal.exe') $expectedExeHash 'BaldurReal.exe'
    Assert-OrdinalEqual ([string]$build.locks.baldur_real_sha256) $expectedExeHash `
        'build.locks.baldur_real_sha256'
    Assert-SealedInputLock $build $runtime $job $jobPath $jobSha256 `
        ([string]$state.generation_id) $scale $expectedExeHash

    $catalogRelative = 'iee-assets\creature-sprites\CreatureSprites-XN.catalog'
    $ownerRelative = 'iee-assets\creature-sprites\CreatureSprites-XN.catalog-owner.json'
    Assert-OrdinalEqual (([string](Get-RequiredProperty $state 'catalog_relative_path' 'state')).Replace('/', '\')) `
        $catalogRelative 'state.catalog_relative_path'
    $catalogTarget = Assert-GameChildRelative $gameRoot $catalogRelative 'Catalogue cible'
    $ownerTarget = Assert-GameChildRelative $gameRoot $ownerRelative 'Owner cible'

    $targets = @(Get-RequiredProperty $state 'targets' 'state')
    if ($targets.Count -lt 4 -or $targets.Count -gt 32772) { throw 'state.targets hors limites.' }
    $seenTargets = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    $required = @{
        'InfinityEngine-Enhancer.dll' = 'runtime-dll'
        'InfinityEngine-Enhancer.ini' = 'runtime-ini'
        $ownerRelative = 'catalog-owner'
        $catalogRelative = 'catalog'
    }
    $expectedShardTargets = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($shard in $catalogArtifacts.shards) { [void]$expectedShardTargets.Add($shard.relative_path) }
    foreach ($targetState in $targets) {
        $relative = ([string](Get-RequiredProperty $targetState 'relative_path' 'state.targets[]')).Replace('/', '\')
        if (-not $seenTargets.Add($relative)) { throw "Cible dupliquée : $relative" }
        [void](Assert-GameChildRelative $gameRoot $relative 'state.targets[].relative_path')
        $role = [string](Get-RequiredProperty $targetState 'role' 'state.targets[]')
        $immutable = Get-RequiredProperty $targetState 'immutable_noop' 'state.targets[]'
        $existed = Get-RequiredProperty $targetState 'existed_before' 'state.targets[]'
        Assert-Boolean $immutable 'state.targets[].immutable_noop'
        Assert-Boolean $existed 'state.targets[].existed_before'
        if ($required.ContainsKey($relative)) {
            if ($role -cne $required[$relative] -or $immutable) { throw "Rôle de cible invalide : $relative" }
        } elseif ($relative -match '^iee-assets\\creature-sprites\\CreatureSprites-XN-[0-9A-F]{64}\.registry$') {
            if ($role -eq 'content-addressed-shard') {
                if (-not $expectedShardTargets.Contains($relative) -or $immutable -ne $existed) {
                    throw "Shard cible non déclaré ou invariant invalide : $relative"
                }
            } elseif ($role -eq 'retired-content-addressed-shard') {
                if ([string]$state.installation_mode -cne 'storage-repack' -or
                    $expectedShardTargets.Contains($relative) -or $immutable -or -not $existed -or
                    $null -ne $targetState.backup_path) {
                    throw "Shard historique retiré invalide : $relative"
                }
                $restoreSource = Resolve-ProjectPath `
                    ([string](Get-RequiredProperty $targetState 'restore_source_path' `
                        'state.targets[]')) 'state.targets[].restore_source_path'
                $restoreHash = [string](Get-RequiredProperty $targetState `
                    'restore_source_sha256' 'state.targets[]')
                Assert-OrdinalEqual $restoreHash ([string]$targetState.original_sha256) `
                    'state.targets[].restore_source_sha256'
                Assert-ExpectedHash $restoreSource $restoreHash "Source shard retiré $relative"
            } else {
                throw "Rôle shard cible invalide : $relative"
            }
        } else {
            throw "Cible hors namespace catalogue : $relative"
        }
    }
    foreach ($entry in $required.GetEnumerator()) {
        if (-not $seenTargets.Contains([string]$entry.Key)) { throw "Cible requise absente : $($entry.Key)" }
    }
    foreach ($relative in $expectedShardTargets) {
        if (-not $seenTargets.Contains($relative)) { throw "Shard requis absent de l'etat : $relative" }
    }

    if (-not $interrupted) {
        [void](Assert-CatalogOwnerAndState $state $activeStatePath $gameRoot $ownerTarget $catalogTarget)
        $iniTarget = Assert-GameChildRelative $gameRoot 'InfinityEngine-Enhancer.ini' 'INI cible'
        Assert-CatalogIniOwnedContract (Get-Content -LiteralPath $iniTarget -Raw)
    }

    $backupRoot = Resolve-ProjectPath ([string](Get-RequiredProperty $state 'backup_root' 'state')) `
        'state.backup_root'
    $backupBase = [System.IO.Path]::GetFullPath((Join-Path $runRoot 'ingame-installation\backups')).TrimEnd('\')
    if (-not $backupRoot.StartsWith($backupBase + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $backupRoot -PathType Container)) {
        throw 'state.backup_root sort de la racine de sauvegarde.'
    }
    $backupStatePath = Join-Path $backupRoot 'install-state.json'
    if (-not (Test-Path -LiteralPath $backupStatePath -PathType Leaf)) { throw 'Historique install-state absent.' }
    $backupState = Get-Content -LiteralPath $backupStatePath -Raw | ConvertFrom-Json
    foreach ($name in @('schema', 'transaction_id', 'generation_id', 'job_id', 'job_sha256')) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $backupState $name 'backup state')) `
            ([string](Get-RequiredProperty $state $name 'state')) "backup state.$name"
    }

    foreach ($targetState in $targets) {
        $relative = ([string]$targetState.relative_path).Replace('/', '\')
        $target = Assert-GameChildRelative $gameRoot $relative 'Cible de restauration'
        if (-not $interrupted) {
            $installedPresent = Get-RequiredProperty $targetState 'installed_present' 'state.targets[]'
            Assert-Boolean $installedPresent 'state.targets[].installed_present'
            $present = Test-Path -LiteralPath $target -PathType Leaf
            if ($present -ne [bool]$installedPresent) { throw "Présence live modifiée : $relative" }
            if ($present) {
                $installedHash = [string](Get-RequiredProperty $targetState 'installed_sha256' 'state.targets[]')
                Assert-HashText $installedHash 'state.targets[].installed_sha256'
                $actualHash = Get-Sha256 $target
                if (-not [string]::Equals($actualHash, $installedHash,
                        [System.StringComparison]::OrdinalIgnoreCase)) {
                    if ([string]$targetState.role -eq 'runtime-ini') {
                        Assert-CatalogIniOwnedContract (Get-Content -LiteralPath $target -Raw)
                    } else {
                        throw "Cible live $relative altéré : SHA-256 $actualHash, attendu $installedHash."
                    }
                }
            }
        }
        if ($targetState.role -eq 'retired-content-addressed-shard') {
            $restoreSource = Resolve-ProjectPath ([string]$targetState.restore_source_path) `
                'state.targets[].restore_source_path'
            Assert-ExpectedHash $restoreSource ([string]$targetState.original_sha256) `
                "Source de restauration $relative"
            if ($null -ne $targetState.backup_path -or -not $targetState.existed_before) {
                throw "Métadonnées shard retiré invalides : $relative"
            }
        } elseif ($targetState.immutable_noop) {
            if ($null -ne $targetState.backup_path -or -not $targetState.existed_before) {
                throw "Métadonnées immutable invalides : $relative"
            }
            Assert-ExpectedHash $target ([string]$targetState.original_sha256) "Shard immutable $relative"
        } elseif ($targetState.existed_before) {
            $backup = Resolve-ProjectPath ([string](Get-RequiredProperty $targetState 'backup_path' 'state.targets[]')) `
                'state.targets[].backup_path'
            $expectedBackup = [System.IO.Path]::GetFullPath((Join-Path $backupRoot $relative))
            if (-not [string]::Equals($backup, $expectedBackup, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Chemin backup non canonique : $relative"
            }
            Assert-ExpectedHash $backup ([string](Get-RequiredProperty $targetState 'original_sha256' 'state.targets[]')) `
                "Backup $relative"
        } elseif ($null -ne $targetState.backup_path -or $null -ne $targetState.original_sha256) {
            throw "Métadonnées backup inattendues : $relative"
        }
    }

    $previousRecord = $null
    $previousPointer = $null
    if ($null -ne $state.PSObject.Properties['previous_active_state'] -and
        $null -ne $state.previous_active_state) {
        $previousRecord = $state.previous_active_state
        $previousPath = Resolve-ProjectPath ([string](Get-RequiredProperty $previousRecord 'path' 'previous_active_state')) `
            'state.previous_active_state.path'
        $expectedPrevious = Join-Path $backupRoot 'previous-active-test.json'
        if (-not [string]::Equals($previousPath, $expectedPrevious,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'previous_active_state.path non canonique.'
        }
        Assert-ExpectedHash $previousPath ([string](Get-RequiredProperty $previousRecord 'sha256' 'previous_active_state')) `
            'État catalogue précédent'
        $previousJson = Get-Content -LiteralPath $previousPath -Raw | ConvertFrom-Json
        Assert-OrdinalEqual ([string](Get-RequiredProperty $previousJson 'schema' 'previous state')) `
            'bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1' 'previous state.schema'
        Assert-OrdinalEqual ([string]$previousJson.generation_id) ([string]$previousRecord.generation_id) `
            'previous state.generation_id'
        $previousPointer = New-CurrentPointerFromSealedState $previousJson $runRoot
    }
    if ($null -ne $state.PSObject.Properties['imported_active_state'] -and
        $null -ne $state.imported_active_state) {
        $importedRecords = @($state.imported_active_state)
        if ($null -ne $state.imported_active_state.PSObject.Properties['parents'] -and
            $null -ne $state.imported_active_state.parents) {
            $importedRecords += @($state.imported_active_state.parents)
        }
        foreach ($importedRecord in $importedRecords) {
            $importPath = Resolve-ProjectPath `
                ([string](Get-RequiredProperty $importedRecord 'path' 'imported_active_state')) `
                'imported_active_state.path'
            Assert-ExpectedHash $importPath ([string](Get-RequiredProperty $importedRecord 'sha256' `
                'imported_active_state')) 'État historique importé'
            $importJson = Get-Content -LiteralPath $importPath -Raw | ConvertFrom-Json
            Assert-OrdinalEqual ([string](Get-RequiredProperty $importJson 'job_id' 'imported state')) `
                ([string](Get-RequiredProperty $importedRecord 'job_id' 'imported record')) `
                'imported state.job_id'
            Assert-OrdinalEqual ([string](Get-RequiredProperty $importJson 'status' 'imported state')) `
                ([string](Get-RequiredProperty $importedRecord 'status' 'imported record')) `
                'imported state.status'
        }
    }

    if ($VerifyOnly) {
        [pscustomobject]@{
            Status = 'verified'; CurrentStatus = [string]$state.status
            RecoverInterrupted = [bool]$interrupted; GenerationId = [string]$state.generation_id
            RestoreTo = if ($null -ne $previousRecord) { [string]$previousRecord.generation_id } else { 'baseline' }
            GameRoot = $gameRoot; State = $activeStatePath
        }
        return
    }

    $state.status = 'restoring'
    $state | Add-Member -MemberType NoteProperty -Name restore_started_at_utc `
        -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
    $state | Add-Member -MemberType NoteProperty -Name recovered_interrupted_transaction `
        -Value ([bool]$interrupted) -Force
    Write-JsonAtomic $state $backupStatePath 20
    Write-JsonAtomic $state $activeStatePath 20

    # Désactiver d'abord le catalogue courant. Les autres fichiers sont remis
    # ensuite; le catalogue précédent, s'il existe, redevient le dernier asset
    # publié dans le dossier du jeu.
    if (Test-Path -LiteralPath $catalogTarget -PathType Leaf) {
        Remove-Item -LiteralPath $catalogTarget -Force
    }
    foreach ($targetState in @($targets | Where-Object { $_.role -ne 'catalog' })) {
        $target = Assert-GameChildRelative $gameRoot ([string]$targetState.relative_path) 'Cible restaurée'
        if ($targetState.role -eq 'retired-content-addressed-shard') {
            $restoreSource = Resolve-ProjectPath ([string]$targetState.restore_source_path) `
                'target.restore_source_path'
            Copy-FileAtomic $restoreSource $target ([string]$targetState.original_sha256)
        } elseif ($targetState.immutable_noop) {
            Assert-ExpectedHash $target ([string]$targetState.original_sha256) 'Shard immutable restauré'
        } elseif ($targetState.existed_before) {
            $backup = Resolve-ProjectPath ([string]$targetState.backup_path) 'target.backup_path'
            Copy-FileAtomic $backup $target ([string]$targetState.original_sha256)
        } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    $catalogState = @($targets | Where-Object { $_.role -eq 'catalog' })[0]
    if ($catalogState.existed_before) {
        $catalogBackup = Resolve-ProjectPath ([string]$catalogState.backup_path) 'catalog.backup_path'
        Copy-FileAtomic $catalogBackup $catalogTarget ([string]$catalogState.original_sha256)
    }

    foreach ($targetState in $targets) {
        $target = Assert-GameChildRelative $gameRoot ([string]$targetState.relative_path) 'Cible restaurée'
        if ($targetState.existed_before) {
            Assert-ExpectedHash $target ([string]$targetState.original_sha256) `
                "Restauration $($targetState.relative_path)"
        } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            throw "Fichier ajouté subsistant après restauration : $($targetState.relative_path)"
        }
    }

    $state.status = 'restored'
    $state | Add-Member -MemberType NoteProperty -Name restored_at_utc `
        -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
    Write-JsonAtomic $state $backupStatePath 20
    if ($null -ne $previousRecord) {
        $previousPath = Resolve-ProjectPath ([string]$previousRecord.path) 'previous_active_state.path'
        Write-JsonAtomic $previousPointer $pointerPath 20
        Copy-FileAtomic $previousPath $activeStatePath ([string]$previousRecord.sha256)
    } else {
        Write-JsonAtomic $state $activeStatePath 20
    }

    [pscustomobject]@{
        Status = 'restored'; RecoveredInterrupted = [bool]$interrupted
        GenerationId = [string]$state.generation_id
        RestoredGenerationId = if ($null -ne $previousRecord) { [string]$previousRecord.generation_id } else { $null }
        RestoreTo = if ($null -ne $previousRecord) { 'previous-generation' } else { 'baseline' }
        GameRoot = $gameRoot; Backup = $backupRoot; State = $activeStatePath
    }
}
finally {
    Exit-GameMutationMutex $mutex
}
