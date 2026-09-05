[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$PayloadRoot = (Join-Path $PSScriptRoot '..\bg2hd\payload-allvalidated')
)

$ErrorActionPreference = 'Stop'
function Get-Hash([string]$Path) { $sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()} }
function Require([bool]$Condition,[string]$Message) { if(-not $Condition){throw $Message} }

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$workspace = (Resolve-Path -LiteralPath (Join-Path $release '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
$payload = (Resolve-Path -LiteralPath $PayloadRoot).Path
$contentPath = Join-Path $release 'manifests/content.json'
Require (Test-Json -Path $contentPath -SchemaFile (Join-Path $release 'schemas/content.schema.json')) 'Schema content.json invalide.'
$content = Get-Content -LiteralPath $contentPath -Raw -Encoding utf8 | ConvertFrom-Json
$expected = @{}
foreach($entry in $content.entries) {
    $validScale = ([int]$entry.scale -eq 4) -or ($entry.kind -eq 'overlay' -and [int]$entry.scale -eq 2)
    Require ($entry.qa_status -eq 'validated' -and $validScale) "Entree non validee : $($entry.source)"
    Require ($entry.source -notmatch '(^|/)(override|backups|archive|captures|temp)(/|$)') "Source interdite : $($entry.source)"
    $relative = (Join-Path $entry.payload_group ([IO.Path]::GetFileName($entry.source))).Replace('\','/')
    if($expected.ContainsKey($relative)){throw "Collision de payload : $relative"}
    $expected[$relative]=$entry
}
foreach($relative in $expected.Keys) {
    $file=Join-Path $payload $relative
    Require (Test-Path -LiteralPath $file -PathType Leaf) "Payload absent : $relative"
    $entry=$expected[$relative]
    Require ((Get-Item -LiteralPath $file).Length -eq [Int64]$entry.bytes) "Taille payload incorrecte : $relative"
    Require ((Get-Hash $file) -eq $entry.sha256) "Hash payload incorrect : $relative"
}
$actual = @(Get-ChildItem -LiteralPath $payload -File -Recurse | ForEach-Object {[IO.Path]::GetRelativePath($payload,$_.FullName).Replace('\','/')})
Require ($actual.Count -eq $expected.Count) 'Le payload contient des fichiers non declares.'

$releaseManifest=Get-Content -LiteralPath (Join-Path $release 'manifests/release.json') -Raw -Encoding utf8|ConvertFrom-Json
$rendererManifest=Get-Content -LiteralPath (Join-Path $release 'manifests/renderer-bundle.json') -Raw -Encoding utf8|ConvertFrom-Json
$runtimeManifestPath=Join-Path $release 'manifests/runtime-compatibility.json'
Require (Test-Json -Path $runtimeManifestPath -SchemaFile (Join-Path $release 'schemas/runtime-compatibility.schema.json')) 'Schema runtime-compatibility.json invalide.'
$runtimeManifest=Get-Content -LiteralPath $runtimeManifestPath -Raw -Encoding utf8|ConvertFrom-Json
$tp2=Get-Content -LiteralPath (Join-Path $release 'bg2hd/bg2hd.tp2') -Raw
$rendererPayload=Join-Path $release 'bg2hd/renderer'
Require ($releaseManifest.release_status -eq 'blocked' -and $releaseManifest.payload_status -eq 'not-buildable') 'Le statut public ne doit pas etre promu avant la levee des blocages.'
Require ($runtimeManifest.steam_launch_contract.installed_steam_shim -eq 'Baldur.exe becomes a verified copy of InfinityLoader.exe') 'Le contrat du shim Steam integre est incorrect.'
Require ($runtimeManifest.steam_launch_contract.preserved_original -eq 'BaldurReal.exe') 'La preservation de l executable officiel est absente.'
Require ($tp2 -match ('VERSION ~'+[regex]::Escape([string]$releaseManifest.version)+'~')) 'La version TP2 ne correspond pas au manifeste de release.'
Require ($rendererManifest.status -eq 'integrated-in-place-awaiting-user-lifecycle-test') 'Statut renderer local integre inattendu.'
Require ($runtimeManifest.renderer.area_animation_runtime.status -eq 'integrated') 'Le runtime animation de zone doit etre integre.'
foreach($file in @($rendererManifest.files)){
    $path=Join-Path $rendererPayload $file.path.Replace('/','\')
    Require (Test-Path -LiteralPath $path -PathType Leaf) "Payload renderer absent : $($file.path)"
    Require ((Get-Item -LiteralPath $path).Length -eq [int64]$file.bytes -and (Get-Hash $path) -eq $file.sha256) "Payload renderer invalide : $($file.path)"
}
$rendererDllPath=Join-Path $rendererPayload 'InfinityEngine-Enhancer.dll'
$rendererBinaryText=[Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($rendererDllPath))
foreach($marker in @('WTSEW','WTOIL','AreaAnimations-X4.registry','TimedTimeline','EnableAreaAnimationX4','EnableNativeOcclusionBridge','FXRenderClippingPolys','LoadArea')){
    Require ($rendererBinaryText.IndexOf($marker,[StringComparison]::Ordinal) -ge 0) "Classificateur liquide absent de la DLL renderer : $marker"
}
$rendererActual=@(Get-ChildItem -LiteralPath $rendererPayload -File -Recurse|ForEach-Object{[IO.Path]::GetRelativePath($rendererPayload,$_.FullName).Replace('\','/')})
Require (-not (Compare-Object ($rendererActual|Sort-Object) (@($rendererManifest.files|ForEach-Object{$_.path})|Sort-Object))) 'Payload renderer contient un fichier non declare.'
Require ((Get-Content -LiteralPath (Join-Path $release 'bg2hd/tools/bg2hd-steam.ps1') -Raw) -match 'bg2hd-renderer\.ps1') 'Le Core ne declenche pas la transaction renderer.'
$coreHelper=Get-Content -LiteralPath (Join-Path $release 'bg2hd/tools/bg2hd-steam.ps1') -Raw
Require ($coreHelper -match "launch_mode='steam-shim-in-place'") 'Le Core ne declare pas le layout Steam integre.'
Require ($coreHelper -match 'BaldurReal\.exe:Baldur\.exe') 'Le Core ne configure pas l alias InfinityLoader attendu.'
Require ($coreHelper -match 'Move-Item\s+-LiteralPath\s+\$baldur') 'Le Core ne publie pas transactionnellement le shim Baldur.exe.'
& (Join-Path $release 'tools/Test-BG2HD-FutureSaveCompatibility.ps1') -ReleaseRoot $release
& (Join-Path $release 'tools/Test-BG2HD-AR0413Contract.ps1') -ReleaseRoot $release -PayloadRoot $payload
Write-Output "Phase 4 payload validation passed: $($expected.Count) declared x4 files verified."
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
