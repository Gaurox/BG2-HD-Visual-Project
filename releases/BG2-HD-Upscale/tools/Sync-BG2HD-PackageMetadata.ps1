[CmdletBinding()]
param([string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)
$ErrorActionPreference='Stop'
$source=Join-Path $ReleaseRoot 'manifests';$destination=Join-Path $ReleaseRoot 'bg2hd/manifests';New-Item -ItemType Directory -Path $destination -Force|Out-Null
foreach($name in @('release.json','runtime-compatibility.json','dependency-bootstrap.json','components.json','content.json','animation-release-candidates.json','overlay-sources.json','renderer-bundle.json','languages.json','licenses-and-exclusions.json')){Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $destination $name) -Force}
Write-Output "Synced package metadata to $destination"
