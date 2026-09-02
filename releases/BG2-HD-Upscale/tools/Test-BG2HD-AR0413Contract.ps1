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

$expectedSourceRun = 'maps/AR0413/runs/wtoil-family-definitive/05_build/x4-alpha-release-installed'
$expected = [ordered]@{
    'A041300.PVRZ' = @{ bytes = 260339; sha256 = '2097FD13B9B92B4A4E18C070C5A45FC5B16E18EB777F01B00DB9B44B09A27340' }
    'A041301.PVRZ' = @{ bytes = 461967; sha256 = '79F5E86132BBA6120B8D7911934C1472AF96387E7CD290D4D99167BC46B84492' }
    'A041302.PVRZ' = @{ bytes = 625547; sha256 = 'B69E36A3A7950BFB0575288761DFB705DA9C95B937172C5BD29703E1832F4770' }
    'A041303.PVRZ' = @{ bytes = 679147; sha256 = 'D05DF5DB869CCAB862AA92302CB616C483B693753643CC76161BA8A3C4EFB203' }
    'A041304.PVRZ' = @{ bytes = 816836; sha256 = '7CAEE0198A7A5DAB288522D6675E4E628820AAC7EC76B02A42940D3D1812E6B4' }
    'A041305.PVRZ' = @{ bytes = 930520; sha256 = 'F98400824E05D0F438D43ED63421B103A2A3BF5008A3E4B77CBEB8210B349852' }
    'A041306.PVRZ' = @{ bytes = 789395; sha256 = 'D44E7E6DA26A1FF9D73AE8E408BA93E4051499A44D318B8029B075010CE86CCA' }
    'A041307.PVRZ' = @{ bytes = 768959; sha256 = 'AB4300ADC3362B56C6D88E08C43E22A4595751FDCE6792E9DE98A55FABEF1AFC' }
    'A041308.PVRZ' = @{ bytes = 731963; sha256 = '605D0D587201D55A4CAE1581A7C9B07F505F6820C8E620315367081FF265234C' }
    'A041309.PVRZ' = @{ bytes = 534145; sha256 = '157E1749F282B17D67B57984564DD5927EC116A53D32EE46309D9FC2C990858E' }
    'A041310.PVRZ' = @{ bytes = 468994; sha256 = '6FA50EA9AB82C1172CCAE71562DF891A9BFE92C9D057E22F7EFDFA61D1910286' }
    'A041311.PVRZ' = @{ bytes = 474229; sha256 = '24F61C645AEDE5B492437A37A73A0C1275271182D8B4C5E8CE830626F9885F14' }
    'A041312.PVRZ' = @{ bytes = 479282; sha256 = '8F0187E6A2B3DEFF3F81D9BAA94B1F4ED7F87A88716F69580F1FF0736B1FA772' }
    'A041313.PVRZ' = @{ bytes = 464906; sha256 = 'B283DD1A88149C98C13E262DEBDE9757E7017F388CED5EEBC4F6324364FEF349' }
    'A041314.PVRZ' = @{ bytes = 439032; sha256 = 'C2B28B704034368583DA54EBD5380F78058341B3FCFEA81230ED46FBC6CB0EB9' }
    'A041315.PVRZ' = @{ bytes = 273330; sha256 = '766057F478EA782931131C8B4D15798C3F3AF3E3097D7B12E7B750434FBFD55A' }
    'AR0413.TIS'   = @{ bytes = 9924;   sha256 = '6C4D5F49D8480CCD3B7C8D94150965943765F0CA3F67310198380BD721EC5BC3' }
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

Write-Output 'AR0413_CANONICAL_CONTRACT=PASSED'
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
