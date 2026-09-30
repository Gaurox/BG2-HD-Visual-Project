[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WorkspaceRoot,
    [Parameter(Mandatory)] [string]$PackageRoot,
    [Parameter(Mandatory)] [string]$WeiDUExecutable,
    [string]$WeiDUSourceArchive
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$binaryHash = 'AD70F5897A6D0BA4B0D226F845A9B14CF345F56CC9697CA8D05CAC9FE4932C1A'
$sourceHash = 'C32725CE34D5B3F9D23094DB79A5EEDE079EAF9E69622306F51B8CD5373B8595'
$sourceUrl = 'https://codeload.github.com/WeiDUorg/weidu/tar.gz/refs/tags/v249.00'

# Bind GPL corresponding source to the actual unmodified installer executable.
if ((Get-FileHash -LiteralPath $WeiDUExecutable -Algorithm SHA256).Hash -ne $binaryHash) {
    throw 'WeiDU inconnu : mettre a jour le contrat de source et ses empreintes avant packaging.'
}
$licenseFiles = @(
    'LICENSE', 'THIRD_PARTY_NOTICES.md', 'licenses/README.md',
    'licenses/INFINITYENGINE-ENHANCER-MIT.txt', 'licenses/DSHADERS-MIT.txt',
    'licenses/SPDLOG-MIT.txt', 'licenses/FMT-MIT.txt', 'licenses/MINHOOK-BSD.txt',
    'licenses/ZLIB.txt', 'licenses/GPL-2.0.txt', 'licenses/NEARINFINITY-LICENSE.txt', 'licenses/WEIDU-SOURCE.md'
)
foreach ($relative in $licenseFiles) {
    $source = Join-Path $workspace $relative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Notice absente : $relative"
    }
    $destination = Join-Path $package $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}
$destination = Join-Path $package 'sources/weidu-v249.00.tar.gz'
New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
if ($WeiDUSourceArchive) {
    Copy-Item -LiteralPath $WeiDUSourceArchive -Destination $destination -Force
} else {
    Invoke-WebRequest -Uri $sourceUrl -OutFile $destination
}
if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $sourceHash) {
    throw 'Source WeiDU incorrecte : archive non conforme au contrat GPL 249.00.'
}
