[CmdletBinding()]
param([string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)

$ErrorActionPreference='Stop'
function Get-Hash([string]$Path){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()}}
$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
$manifest=Get-Content -LiteralPath (Join-Path $release 'manifests\renderer-bundle.json') -Raw -Encoding utf8|ConvertFrom-Json
if($manifest.status -notin @('integrated-awaiting-clean-lifecycle-test','integrated-in-place-awaiting-user-lifecycle-test')){throw "Bundle renderer non eligible : $($manifest.status)"}
$source=Join-Path $release ('release-inputs\renderer\'+$manifest.bundle_id)
$destination=Join-Path $release 'bg2hd\renderer'
foreach($file in @($manifest.files)){
    $relative=$file.path.Replace('/','\');$from=Join-Path $source $relative;$to=Join-Path $destination $relative
    if(-not(Test-Path -LiteralPath $from -PathType Leaf)){throw "Source renderer absente : $($file.path)"}
    if((Get-Item -LiteralPath $from).Length -ne [int64]$file.bytes -or (Get-Hash $from)-ne$file.sha256){throw "Source renderer invalide : $($file.path)"}
    New-Item -ItemType Directory -Path (Split-Path -Parent $to) -Force|Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Force
    if((Get-Item -LiteralPath $to).Length -ne [int64]$file.bytes -or (Get-Hash $to)-ne$file.sha256){throw "Payload renderer invalide : $($file.path)"}
}
$actual=@(Get-ChildItem -LiteralPath $destination -File -Recurse|ForEach-Object{[IO.Path]::GetRelativePath($destination,$_.FullName).Replace('\','/')})
$expected=@($manifest.files|ForEach-Object{$_.path})
if(Compare-Object ($actual|Sort-Object) ($expected|Sort-Object)){throw 'Payload renderer contient un fichier non declare.'}
Write-Output "Staged renderer payload: $($manifest.files.Count) files."
