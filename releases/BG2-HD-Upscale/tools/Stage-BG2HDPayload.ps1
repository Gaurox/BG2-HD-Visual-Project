[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$PayloadRoot = (Join-Path $PSScriptRoot '..\bg2hd\payload-allvalidated'),
    [string]$ContentPath = (Join-Path $PSScriptRoot '..\manifests\content.json')
)

$ErrorActionPreference = 'Stop'
function Get-Hash([string]$Path) { $sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()} }
function Require([bool]$Condition,[string]$Message) { if(-not $Condition){throw $Message} }
function RelativePath([string]$Base,[string]$Target) { [IO.Path]::GetRelativePath($Base,$Target).Replace('\','/') }

$workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
$payload = [IO.Path]::GetFullPath($PayloadRoot)
$contentPath = [IO.Path]::GetFullPath($ContentPath)
$content = Get-Content -LiteralPath $contentPath -Raw -Encoding utf8 | ConvertFrom-Json
Require ($content.entries.Count -gt 0) 'Le manifeste de contenu est vide.'

if (Test-Path -LiteralPath $payload) {
    throw "Payload deja present : $payload. Une reconstruction doit d abord etre explicitement archivee hors de ce script."
}
$temporary = Join-Path (Split-Path -Parent $payload) ('.payload-bg2hd-' + [Guid]::NewGuid().ToString('N') + '.tmp')
try {
    New-Item -ItemType Directory -Path $temporary -Force | Out-Null
    $targets = @{}
    $totalBytes = [Int64]0
    foreach ($entry in @($content.entries | Sort-Object component_id, install_order, destination, source)) {
        $validScale = ([int]$entry.scale -eq 4) -or ($entry.kind -eq 'overlay' -and [int]$entry.scale -eq 2)
        Require ($entry.qa_status -eq 'validated' -and $validScale) "Entree non validee : $($entry.source)"
        Require ($entry.source -notmatch '(^|/)(override|backups|archive|captures|temp)(/|$)') "Source interdite : $($entry.source)"
        $source = [IO.Path]::GetFullPath((Join-Path $workspace ($entry.source.Replace('/','\'))))
        Require ((RelativePath $workspace $source) -notmatch '(^|/)\.\.(/|$)') "Source hors workspace : $($entry.source)"
        Require (Test-Path -LiteralPath $source -PathType Leaf) "Source absente : $source"
        Require ((Get-Item -LiteralPath $source).Length -eq [Int64]$entry.bytes) "Taille source incorrecte : $($entry.source)"
        Require ((Get-Hash $source) -eq $entry.sha256) "Hash source incorrect : $($entry.source)"
        $target = Join-Path $temporary (Join-Path $entry.payload_group ([IO.Path]::GetFileName($entry.source)))
        if ($targets.ContainsKey($target)) { throw "Collision de payload : $target" }
        $targets[$target] = $entry
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target
        Require ((Get-Item -LiteralPath $target).Length -eq [Int64]$entry.bytes) "Taille stagee incorrecte : $target"
        Require ((Get-Hash $target) -eq $entry.sha256) "Hash stage incorrect : $target"
        $totalBytes += [Int64]$entry.bytes
    }
    Move-Item -LiteralPath $temporary -Destination $payload
    [pscustomobject]@{payload_root=$payload;files=$targets.Count;bytes=$totalBytes;sha256_verified=$true}|ConvertTo-Json
}
catch {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    throw
}
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
