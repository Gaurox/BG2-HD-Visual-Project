$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..')).TrimEnd([char[]]'\/')
Set-Location -LiteralPath $root
if(((Get-Item -LiteralPath (Join-Path $root '.tmp')).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'Workspace scratch parent is a reparse point'}
$release=Join-Path $root 'releases/BG2-HD-Upscale'
$env:TEMP=Join-Path $root '.tmp/release-finalization-tests';$env:TMP=$env:TEMP
$weidu=Join-Path $release 'release-inputs/weidu/setup-bg2hd.exe'
$source=Join-Path $release 'release-inputs/weidu/weidu-v249.00.tar.gz'
$outputA=Join-Path $root '.tmp/animation-release-build-uncompressed-20261012-v1'
$final=Join-Path $release 'dist-local/alpha6-animations-20261012-v1'
foreach($path in @($outputA,$final)){if(Test-Path -LiteralPath $path){throw "Output already exists: $path"}}
function Record([string]$Name,[object]$Value){$path=Join-Path $PSScriptRoot ($Name+'.json');if(Test-Path -LiteralPath $path){throw "Immutable receipt exists: $path"};[IO.File]::WriteAllText($path,($Value|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))}
function Gate([string]$Name,[string]$Script,[string[]]$Arguments=@()) {
    Write-Host "START $Name"
    $log=Join-Path $PSScriptRoot ($Name+'.log')
    & pwsh -NoProfile -File $Script @Arguments > $log 2>&1
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $log -Tail 35;throw "FAILED $Name"}
    Write-Host "PASSED $Name"
}
function Build([string]$Name,[string]$Output){
    Gate $Name (Join-Path $release 'tools/Build-BG2HD-LocalReproducible.ps1') @('-WeiDUExecutable',$weidu,'-WeiDUSourceArchive',$source,'-OutputRoot',$Output,'-ZipCompression','NoCompression')
    $text=Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Name+'.log')) -Raw
    $json=[regex]::Match($text,'(?s)\{\s*"package":.*?\}\s*$').Value
    if(-not $json){throw "Build metadata missing: $Name"}
    $result=$json|ConvertFrom-Json;Record $Name $result;return $result
}
$a=Build 'build-uncompressed' $outputA
Gate 'phase6b-uncompressed' (Join-Path $release 'tools/Test-BG2HD-Phase6BPackage.ps1') @('-ArchivePath',$a.archive)
Gate 'phase5a-uncompressed' (Join-Path $release 'tools/Test-BG2HD-Phase5A.ps1') @('-WeiDUExecutable',$weidu,'-ArchivePath',$a.archive)
& python (Join-Path $PSScriptRoot 'verify_stored_zip.py') $a.archive
if($LASTEXITCODE-ne0){throw 'ZIP storage verification failed'}
New-Item -ItemType Directory -Path $final | Out-Null
$archive=Join-Path $final ([IO.Path]::GetFileName($a.archive))
Move-Item -LiteralPath $a.archive -Destination $archive
Move-Item -LiteralPath $a.checksum_file -Destination ($archive+'.sha256')
# Only disposable scratch created by this recipe, including the superseded
# compressed trial; retained releases and historical archives stay untouched.
foreach($path in @($outputA,(Join-Path $root '.tmp/animation-release-build-a-20261012-v1'))) {
    $resolved=(Resolve-Path -LiteralPath $path).Path
    $tmpRoot=[IO.Path]::GetFullPath((Join-Path $root '.tmp'))
    if([IO.Path]::GetDirectoryName($resolved)-ne$tmpRoot -or -not $resolved.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe scratch target: $resolved"}
    if(((Get-Item -LiteralPath $resolved).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw "Scratch root is a reparse point: $resolved"}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Record 'package-finalization' ([ordered]@{archive=$archive;archive_sha256=$a.archive_sha256;archive_bytes=$a.archive_bytes;zip_compression='NoCompression';zip_storage_verified=$true;independent_builds_comparison_performed=$false;archive_integrity='phase6b-uncompressed-passed';installer_fixtures='phase5a-uncompressed-passed';scratch_removed=@($outputA,(Join-Path $root '.tmp/animation-release-build-a-20261012-v1'));superseded_build_receipt='build-a.json';public_status='blocked';game_mutation=$false})
Write-Output "PACKAGE_FINAL=$archive"
