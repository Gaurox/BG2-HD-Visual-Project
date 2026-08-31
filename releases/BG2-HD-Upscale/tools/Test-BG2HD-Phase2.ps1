[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$WeiDUExecutable
)

$ErrorActionPreference = 'Stop'

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

$workspace = (Resolve-Path -LiteralPath (Join-Path $ReleaseRoot '..\..')).Path
$animationQaSchema = Join-Path $ReleaseRoot 'schemas\animation-qa-approval.schema.json'
$animationCandidates = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'manifests\animation-release-candidates.json') -Raw -Encoding utf8 | ConvertFrom-Json
foreach ($candidate in @($animationCandidates.candidates)) {
    $qaPath = [IO.Path]::GetFullPath((Join-Path $workspace ([string]$candidate.qa_approval).Replace('/', '\')))
    Require (Test-Path -LiteralPath $qaPath -PathType Leaf) "Approbation QA animation absente : $($candidate.area)"
    Require (Test-Json -Path $qaPath -SchemaFile $animationQaSchema) "Schema approbation QA animation invalide : $($candidate.area)"
    Require ((Get-FileHash -LiteralPath $qaPath -Algorithm SHA256).Hash -eq [string]$candidate.qa_approval_sha256) "Hash approbation QA animation invalide : $($candidate.area)"
    $qaApproval = Get-Content -LiteralPath $qaPath -Raw -Encoding utf8 | ConvertFrom-Json
    foreach ($evidence in @($qaApproval.evidence)) {
        $evidencePath = [IO.Path]::GetFullPath((Join-Path $workspace ([string]$evidence.path).Replace('/', '\')))
        $relativeEvidence = [IO.Path]::GetRelativePath($workspace, $evidencePath).Replace('\', '/')
        Require ($relativeEvidence -notmatch '(^|/)\.\.(/|$)') "Preuve QA animation hors workspace : $($evidence.path)"
        Require (Test-Path -LiteralPath $evidencePath -PathType Leaf) "Preuve QA animation absente : $relativeEvidence"
        Require (Test-QAEvidenceHash $workspace $relativeEvidence ([string]$evidence.sha256)) "Hash preuve QA animation invalide : $relativeEvidence"
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
