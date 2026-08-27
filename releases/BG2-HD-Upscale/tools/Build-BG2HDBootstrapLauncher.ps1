[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [Parameter(Mandatory)] [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$source = Join-Path $release 'bootstrap\Install-BG2HD.cs'
$output = [IO.Path]::GetFullPath($OutputPath)
$dotnet = (Get-Command dotnet -ErrorAction Stop).Source
$sdkVersion = (& $dotnet --version).Trim()
$compiler = Join-Path (Split-Path -Parent $dotnet) "sdk\$sdkVersion\Roslyn\bincore\csc.dll"
$references = Join-Path ${env:ProgramFiles(x86)} 'Reference Assemblies\Microsoft\Framework\.NETFramework\v4.0'
$referenceFiles = @('mscorlib.dll', 'System.dll', 'System.Core.dll') | ForEach-Object { Join-Path $references $_ }
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Source launcher absent : $source" }
if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) { throw "Compilateur Roslyn absent : $compiler" }
foreach ($reference in $referenceFiles) { if (-not (Test-Path -LiteralPath $reference -PathType Leaf)) { throw "Reference .NET Framework absente : $reference" } }
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
Remove-Item -LiteralPath $output -Force -ErrorAction SilentlyContinue
& $dotnet $compiler /noconfig /nostdlib /nologo /target:exe /platform:x64 /optimize+ /debug- /deterministic+ ("/out:$output") ("/r:$($referenceFiles[0])") ("/r:$($referenceFiles[1])") ("/r:$($referenceFiles[2])") $source
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $output -PathType Leaf)) { throw 'Compilation du launcher BG2HD echouee.' }
Write-Output "Built BG2HD bootstrap launcher: $output"
