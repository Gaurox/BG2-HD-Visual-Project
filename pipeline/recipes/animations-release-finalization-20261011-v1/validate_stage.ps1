$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
Set-Location -LiteralPath $root
$release=Join-Path $root 'releases/BG2-HD-Upscale'
$env:TEMP=Join-Path $root '.tmp/release-finalization-tests'
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
function Gate([string]$Name,[string]$Script,[string[]]$Arguments=@()) {
    Write-Output "START $Name"
    & pwsh -NoProfile -File $Script @Arguments > (Join-Path $PSScriptRoot ($Name+'.log')) 2>&1
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Name+'.log')) -Tail 30;throw "FAILED $Name"}
    Write-Output "PASSED $Name"
}
Gate 'phase2' (Join-Path $release 'tools/Test-BG2HD-Phase2.ps1') @('-WeiDUExecutable',(Join-Path $release 'release-inputs/weidu/setup-bg2hd.exe'))
Gate 'staging' (Join-Path $release 'tools/Stage-BG2HDPayload.ps1')
Gate 'phase4' (Join-Path $release 'tools/Test-BG2HD-Phase4.ps1')
