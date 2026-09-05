[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^(AR|OH)[0-9]{4}$')]
    [string]$Area,
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$AnimationCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\animation-release-candidates.json'),
    [string]$AnimationQaApprovalOverridePath
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
$areaId = $Area.ToUpperInvariant()
$candidatePath = [IO.Path]::GetFullPath($AnimationCandidatesPath)
$candidateSchema = Join-Path $release 'schemas\animation-release-candidates.schema.json'
Require (Test-Json -Path $candidatePath -SchemaFile $candidateSchema) 'Schema du registre de candidats animation invalide.'
$candidates = Get-Content -LiteralPath $candidatePath -Raw -Encoding utf8 | ConvertFrom-Json
$candidate = @($candidates.candidates | Where-Object { [string]$_.area -eq $areaId })
Require ($candidate.Count -eq 1) "Candidat animation absent ou duplique : $areaId"
Require ([string]$candidate[0].approval_status -eq 'approved-for-release') "Candidat animation non approuve : $areaId"

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('bg2hd-animation-candidate-' + $areaId + '-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    $content = Join-Path $tempRoot 'content.json'
    $components = Join-Path $tempRoot 'components.json'
    $tp2 = Join-Path $tempRoot 'bg2hd.tp2'
    $payload = Join-Path $tempRoot 'payload'

    $contentArguments = @{
        WorkspaceRoot = $workspace
        AnimationCandidatesPath = $candidatePath
        OutputPath = $content
        OnlyAnimationArea = $areaId
    }
    if (-not [string]::IsNullOrWhiteSpace($AnimationQaApprovalOverridePath)) {
        $contentArguments.AnimationQaApprovalOverridePath = $AnimationQaApprovalOverridePath
    }
    & (Join-Path $release 'tools\New-BG2HD-ContentManifest.ps1') @contentArguments | Out-Null
    Require (Test-Json -Path $content -SchemaFile (Join-Path $release 'schemas\content.schema.json')) "Schema du contenu delta invalide : $areaId"
    $contentObject = Get-Content -LiteralPath $content -Raw -Encoding utf8 | ConvertFrom-Json
    $entries = @($contentObject.entries)
    Require ($entries.Count -gt 0 -and @($entries | Where-Object { $_.kind -ne 'area-animation' -or $_.area -ne $areaId }).Count -eq 0) "Le manifeste delta contient un contenu hors candidat : $areaId"

    $packPath = Join-Path $workspace (([string]$candidate[0].source_pack).Replace('/', '\') + '\manifest.json')
    $pack = Get-Content -LiteralPath $packPath -Raw -Encoding utf8 | ConvertFrom-Json
    $expectedFiles = 2 + [int]$pack.frame_count
    Require ($entries.Count -eq $expectedFiles) "Inventaire delta incomplet : $areaId ($($entries.Count)/$expectedFiles)"

    & python (Join-Path $release 'tools\Validate-BG2HD-Assets.py') --workspace $workspace --content $content --area-animation-only
    if ($LASTEXITCODE -ne 0) { throw "Validation structurelle delta echouee : $areaId" }

    # Stage-BG2HDPayload rechecks every byte and hash from the temporary delta
    # manifest; it never touches the persistent full-release payload.
    & (Join-Path $release 'tools\Stage-BG2HDPayload.ps1') `
        -WorkspaceRoot $workspace `
        -ReleaseRoot $release `
        -ContentPath $content `
        -PayloadRoot $payload | Out-Null
    $staged = @(Get-ChildItem -LiteralPath $payload -File -Recurse)
    Require ($staged.Count -eq $expectedFiles) "Staging delta incomplet : $areaId ($($staged.Count)/$expectedFiles)"

    & (Join-Path $release 'tools\New-BG2HD-ComponentManifest.ps1') `
        -ReleaseRoot $release `
        -AnimationCandidatesPath $candidatePath `
        -ContentPath $content `
        -OutputPath $components | Out-Null
    $componentId = [int]$candidate[0].component_id
    $component = @((Get-Content -LiteralPath $components -Raw -Encoding utf8 | ConvertFrom-Json).components | Where-Object { [int]$_.id -eq $componentId })
    Require ($component.Count -eq 1 -and $component[0].label -eq [string]$candidate[0].component_label -and $component[0].depends_on -contains 0) "Composant delta invalide : $areaId"

    & (Join-Path $release 'tools\Generate-BG2HD-Tp2.ps1') `
        -ReleaseRoot $release `
        -ContentPath $content `
        -ComponentsPath $components `
        -OutputPath $tp2 | Out-Null
    $tp2Raw = Get-Content -LiteralPath $tp2 -Raw -Encoding utf8
    Require ($tp2Raw -match ('(?m)^BEGIN ~' + [regex]::Escape("$areaId area animations (x4)") + '~\r?$')) "BEGIN WeiDU absent : $areaId"
    Require ($tp2Raw -match "(?m)^  DESIGNATED $componentId\r?$") "DESIGNATED WeiDU absent : $areaId"
    Require ($tp2Raw -match '(?m)^  REQUIRE_COMPONENT ~bg2hd/bg2hd\.tp2~ ~0~ @14\r?$') "Dependance Core absente : $areaId"
    $payloadGroup = [regex]::Escape([string]$candidate[0].payload_group)
    $copies = [regex]::Matches($tp2Raw, "(?m)^  COPY_LARGE ~bg2hd/payload/$payloadGroup/[^~]+~ ~iee-assets/areas/$areaId/[^~]+~\r?$")
    Require ($copies.Count -eq $expectedFiles) "COPY_LARGE delta incomplet : $areaId ($($copies.Count)/$expectedFiles)"

    $bytes = [int64]($entries | Measure-Object -Property bytes -Sum).Sum
    Write-Output "Area-animation delta validation passed: $areaId ($expectedFiles files, $bytes bytes)."
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
