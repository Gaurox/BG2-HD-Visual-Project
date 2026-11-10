[CmdletBinding()]
param([string]$GameRoot = (Get-Location).Path,
      [string]$RendererManifestPath = (Join-Path $PSScriptRoot '../manifests/renderer-bundle.json'))
$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath $RendererManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$expected = @($manifest.files | Where-Object { $_.path -eq 'InfinityEngine-Enhancer.dll' })
$dll = Join-Path $GameRoot 'InfinityEngine-Enhancer.dll'
if ($expected.Count -ne 1 -or -not (Test-Path -LiteralPath $dll -PathType Leaf)) {
    throw 'Update the BG2 HD Core component before installing effects.'
}
if ((Get-Item -LiteralPath $dll).Length -ne [int64]$expected[0].bytes -or
    (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash -ne $expected[0].sha256) {
    throw 'Update the BG2 HD Core component before installing effects: renderer differs from this package.'
}
Write-Output 'EFFECT_STORAGE_RENDERER=PASSED'
