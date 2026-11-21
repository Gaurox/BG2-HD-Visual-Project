[CmdletBinding()]
param([string]$GameRoot = (Get-Location).Path,
      [string]$RendererManifestPath)
$ErrorActionPreference = 'Stop'
if (-not $RendererManifestPath) {
    $RendererManifestPath = Join-Path $PSScriptRoot '../manifests/renderer-bundle.json'
}
$manifest = Get-Content -LiteralPath $RendererManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$expected = @($manifest.files | Where-Object { $_.path -eq 'InfinityEngine-Enhancer.dll' })
$dll = Join-Path $GameRoot 'InfinityEngine-Enhancer.dll'
if ($expected.Count -ne 1 -or -not (Test-Path -LiteralPath $dll -PathType Leaf)) {
    throw 'Update the BG2 HD Core component before installing effects.'
}
$stream = [IO.File]::OpenRead($dll)
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $matches = $stream.Length -eq [int64]$expected[0].bytes -and
        ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') -eq $expected[0].sha256
} finally {
    $sha.Dispose()
    $stream.Dispose()
}
if (-not $matches) {
    throw 'Update the BG2 HD Core component before installing effects: renderer differs from this package.'
}
Write-Output 'EFFECT_STORAGE_RENDERER=PASSED'
