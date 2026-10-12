[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$ManifestPath,
    [string]$PayloadRoot,
    [string]$RendererDllPath
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-Hash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') }
    finally { $sha.Dispose(); $stream.Dispose() }
}

$expectedSourceRun = 'maps/AR0413/runs/release-maps-20261012-v1/AR0413/05_build'
# QA acquise 2026-09-28: ar0413-final-user-qa-20260928-v1.json; no new QA inferred.
$expected = [ordered]@{
    'A041300.PVRZ' = @{ bytes = 33050; sha256 = 'CF50CEAFF4BC3ED2FFA382D27321F2F6EF48112302F0C69E198D9BB5E191110D' }
    'A041301.PVRZ' = @{ bytes = 198565; sha256 = 'E08977EF4087B5DD2A26BCD0519C666164499082B6E80C384CEEA90F328914F3' }
    'A041302.PVRZ' = @{ bytes = 464741; sha256 = '56F0F12F2E85E2CA805C48684B52BE2A42A727F2ADA5FA67554C8A8D5C8808A7' }
    'A041303.PVRZ' = @{ bytes = 602471; sha256 = 'F9F0D19C317FC61614FCE21682AC97E81EB0331AF9FB018A1E728780C43FE9AE' }
    'A041304.PVRZ' = @{ bytes = 810927; sha256 = 'F9B135BA7B43FAEDC0F4D8872F57233D1388DF1927AC9F00D7AF1211A8D8EAAF' }
    'A041305.PVRZ' = @{ bytes = 811969; sha256 = 'A14D08D8DE739A88D8EE5718D31CE0178108B0254870677A98B79CCA56F56A0F' }
    'A041306.PVRZ' = @{ bytes = 431865; sha256 = '3FA3FC4854E1B9EDA915392FCEBDBEF865187D0D6608F5FB98B6225830DC1DDE' }
    'A041307.PVRZ' = @{ bytes = 470419; sha256 = '9763CF3269A2EFAB2E88D0F70A9452D5269C7898399C8117BD837961FC6F5B12' }
    'A041308.PVRZ' = @{ bytes = 364087; sha256 = '546F586BB7EEC246793207798C085A51219B1D146F7B81D586F8B35CB0DFC653' }
    'A041309.PVRZ' = @{ bytes = 59442; sha256 = 'C061AE0AB4350316F39D567C39D5F3925E0AB9D93D86BEFFCC11BB55C990EE04' }
    'A041310.PVRZ' = @{ bytes = 47148; sha256 = '7422DF93E9293BAEA6C317FE9C5D7852A81DF14279024C82D5B927AA26FDC4F4' }
    'A041311.PVRZ' = @{ bytes = 231438; sha256 = '91718DDC9CEF2B0AA91A844B22DDE7C3EA3E1788F0286BC0529F993C5B41D9E5' }
    'A041312.PVRZ' = @{ bytes = 303203; sha256 = '4839980DB8FFEAD3C458892443FC65A2AFCAC8FE0665E9A698EFA432C4E3FFC2' }
    'A041313.PVRZ' = @{ bytes = 287209; sha256 = 'E611246DE6DFF1AFD09EAA1C527669B614283A38AB3AA8514E7F7E467D91E357' }
    'A041314.PVRZ' = @{ bytes = 303624; sha256 = 'A42146284B6A6E8EA50AE5774650FB69B6988208DAC84DBADC407096A473B782' }
    'A041315.PVRZ' = @{ bytes = 109368; sha256 = '9050CF4D9E63AF2742C3A23CDDA04C3AF1DCE213B2514D84507AA8A2989C102A' }
    'AR0413.TIS' = @{ bytes = 9924; sha256 = '6C4D5F49D8480CCD3B7C8D94150965943765F0CA3F67310198380BD721EC5BC3' }
    'AR0413.WED' = @{ bytes = 8338; sha256 = '4BEF1DFA4AB7A06532C3DE19F9B1005C6E4ACEB6D7DB7A340298D9595F2EE177' }
    'YFGPKI.TIS' = @{ bytes = 888; sha256 = '11EF690FD6C5D0AC447286E6B4E17A38B653616F07FB9468D133C32B9B1B94A6' }
    'YFGPKIR.TIS' = @{ bytes = 888; sha256 = '11EF690FD6C5D0AC447286E6B4E17A38B653616F07FB9468D133C32B9B1B94A6' }
    'YGPKI00.PVRZ' = @{ bytes = 1256542; sha256 = 'BB9DE65853181B332FB01475967A8F147CB9C6B93C1385ACFB76D332200C067C' }
    'YGPKIR00.PVRZ' = @{ bytes = 1256542; sha256 = 'BB9DE65853181B332FB01475967A8F147CB9C6B93C1385ACFB76D332200C067C' }
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$workspace = (Resolve-Path -LiteralPath (Join-Path $release '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
if (-not $ManifestPath) {
    $rootManifest = Join-Path $release 'manifests\content.json'
    $ManifestPath = if (Test-Path -LiteralPath $rootManifest) { $rootManifest } else { Join-Path $release 'bg2hd\manifests\content.json' }
}
if (-not $PayloadRoot) {
    $staged = Join-Path $release 'bg2hd\payload-allvalidated'
    $PayloadRoot = if (Test-Path -LiteralPath $staged) { $staged } else { Join-Path $release 'bg2hd\payload' }
}
if (-not $RendererDllPath) {
    $RendererDllPath = Join-Path $release 'bg2hd\renderer\InfinityEngine-Enhancer.dll'
}

Require (Test-Path -LiteralPath $ManifestPath -PathType Leaf) 'Manifeste content.json absent pour le contrat AR0413.'
Require (Test-Path -LiteralPath $PayloadRoot -PathType Container) 'Payload absent pour le contrat AR0413.'
Require (Test-Path -LiteralPath $RendererDllPath -PathType Leaf) 'DLL renderer absente pour le contrat AR0413.'

$content = Get-Content -LiteralPath $ManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$entries = @($content.entries | Where-Object { $_.area -eq 'AR0413' })
Require ($entries.Count -eq $expected.Count) "AR0413 doit avoir exactement $($expected.Count) fichiers declares."

foreach ($name in $expected.Keys) {
    $matches = @($entries | Where-Object { [IO.Path]::GetFileName(([string]$_.source).Replace('/', '\')) -eq $name })
    Require ($matches.Count -eq 1) "Entree AR0413 absente ou dupliquee : $name"
    $entry = $matches[0]
    $contract = $expected[$name]
    Require ([string]$entry.source_run -eq $expectedSourceRun) "Run AR0413 non canonique : $name"
    Require ([string]$entry.payload_group -eq 'map-ar0413') "Groupe payload AR0413 invalide : $name"
    Require ([int]$entry.component_id -eq 1300) "Composant AR0413 invalide : $name"
    Require ([int64]$entry.bytes -eq [int64]$contract.bytes) "Taille AR0413 non canonique : $name"
    Require ([string]$entry.sha256 -eq [string]$contract.sha256) "Hash AR0413 non canonique : $name"

    $payloadFile = Join-Path $PayloadRoot (Join-Path 'map-ar0413' $name)
    Require (Test-Path -LiteralPath $payloadFile -PathType Leaf) "Fichier AR0413 absent du payload : $name"
    Require ((Get-Item -LiteralPath $payloadFile).Length -eq [int64]$contract.bytes) "Taille payload AR0413 invalide : $name"
    Require ((Get-Hash $payloadFile) -eq [string]$contract.sha256) "Hash payload AR0413 invalide : $name"
}

$actualNames = @(Get-ChildItem -LiteralPath (Join-Path $PayloadRoot 'map-ar0413') -File | ForEach-Object { $_.Name } | Sort-Object)
Require (-not (Compare-Object ($expected.Keys | Sort-Object) $actualNames)) 'Le payload AR0413 contient un fichier absent du contrat canonique.'
Require (-not (Test-Path -LiteralPath (Join-Path $PayloadRoot 'map-ar0413\A041316.PVRZ'))) 'La page rejetee A041316.PVRZ ne doit jamais etre packagee.'

$rendererText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($RendererDllPath))
Require ($rendererText.IndexOf('WTOIL', [StringComparison]::Ordinal) -ge 0) 'La DLL renderer ne contient pas le classificateur WTOIL requis par AR0413.'

Require ($rendererText.IndexOf('YFGPKI', [StringComparison]::Ordinal) -ge 0) 'La DLL ne porte pas le contrat huile final YFGPKI.'
Write-Output 'AR0413_CANONICAL_CONTRACT=PASSED (final 2026-09-28 oil stack, 22 files)'
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
