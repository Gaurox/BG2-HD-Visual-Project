$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..')).TrimEnd([char[]]'\/')
Set-Location -LiteralPath $root
$release=Join-Path $root 'releases/BG2-HD-Upscale'
$env:TEMP=Join-Path $root '.tmp/maps-release-finalization-tests-20261012-v1';$env:TMP=$env:TEMP
[IO.Directory]::CreateDirectory($env:TEMP)|Out-Null
$weidu=Join-Path $release 'release-inputs/weidu/setup-bg2hd.exe'
$source=Join-Path $release 'release-inputs/weidu/weidu-v249.00.tar.gz'
$output=Join-Path $root '.tmp/maps-release-build-uncompressed-20261012-v1'
$final=Join-Path $release 'dist-local/alpha6-maps-20261012-v1'
foreach($p in @($output,$final)){if(Test-Path -LiteralPath $p){throw "Output already exists: $p"}}
function Record([string]$Name,[object]$Value){
    $p=Join-Path $PSScriptRoot ($Name+'.json');if(Test-Path -LiteralPath $p){throw "Immutable receipt exists: $p"}
    [IO.File]::WriteAllText($p,($Value|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
}
function Gate([string]$Name,[string]$Script,[string[]]$Arguments=@()){
    $log=Join-Path $PSScriptRoot ($Name+'.log');if(Test-Path -LiteralPath $log){throw "Existing gate log: $log"}
    Write-Host "START $Name"
    & pwsh -NoProfile -File $Script @Arguments > $log 2>&1
    $code=$LASTEXITCODE
    if($code-ne0){Get-Content -LiteralPath $log -Tail 30;throw "FAILED $Name ($code)"}
    Record ($Name+'-receipt') ([ordered]@{state='passed';script=$Script;script_sha256=(Get-FileHash -LiteralPath $Script -Algorithm SHA256).Hash;arguments=$Arguments;log_sha256=(Get-FileHash -LiteralPath $log -Algorithm SHA256).Hash})
    Write-Host "PASSED $Name"
}
Gate 'phase2' (Join-Path $release 'tools/Test-BG2HD-Phase2.ps1') @('-WeiDUExecutable',$weidu)
# Preserve the prior animation staging outside the package tree before official restaging.
$old=Join-Path $release 'bg2hd/payload-allvalidated'
$before=Join-Path $release 'release-inputs/maps-finalization-before-20261012-v1/payload-allvalidated'
foreach($p in @($old,$before)){
    $absolute=[IO.Path]::GetFullPath($p)
    if(-not $absolute.StartsWith($release+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe staging path: $absolute"}
    if((Test-Path -LiteralPath $absolute)-and((Get-Item -LiteralPath $absolute).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw "Reparse staging path: $absolute"}
}
if(Test-Path -LiteralPath $before){throw "Previous staging target exists: $before"}
New-Item -ItemType Directory -Path (Split-Path -Parent $before)|Out-Null
Move-Item -LiteralPath $old -Destination $before
Record 'previous-staging' ([ordered]@{from=$old;to=$before;preserved=$true;game_mutation=$false})
Gate 'stage' (Join-Path $release 'tools/Stage-BG2HDPayload.ps1')
Gate 'phase4' (Join-Path $release 'tools/Test-BG2HD-Phase4.ps1')
Gate 'build-uncompressed' (Join-Path $release 'tools/Build-BG2HD-LocalReproducible.ps1') @('-WeiDUExecutable',$weidu,'-WeiDUSourceArchive',$source,'-OutputRoot',$output,'-ZipCompression','NoCompression')
$text=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-uncompressed.log') -Raw
$json=[regex]::Match($text,'(?s)\{\s*"package":.*?\}\s*$').Value
if(-not $json){throw 'Build metadata missing'}
$build=$json|ConvertFrom-Json;Record 'build-uncompressed' $build
Gate 'phase6b' (Join-Path $release 'tools/Test-BG2HD-Phase6BPackage.ps1') @('-ArchivePath',$build.archive)
Gate 'phase5a' (Join-Path $release 'tools/Test-BG2HD-Phase5A.ps1') @('-WeiDUExecutable',$weidu,'-ArchivePath',$build.archive)
& python (Join-Path $PSScriptRoot 'verify_zip.py') $build.archive
if($LASTEXITCODE-ne0){throw 'Stored ZIP verification failed'}
New-Item -ItemType Directory -Path $final|Out-Null
$archive=Join-Path $final ([IO.Path]::GetFileName($build.archive))
Move-Item -LiteralPath $build.archive -Destination $archive
Move-Item -LiteralPath $build.checksum_file -Destination ($archive+'.sha256')
$resolved=(Resolve-Path -LiteralPath $output).Path
if([IO.Path]::GetDirectoryName($resolved)-ne(Join-Path $root '.tmp')-or-not $resolved.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe scratch target: $resolved"}
if(((Get-Item -LiteralPath $resolved).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'Scratch is a reparse point'}
Remove-Item -LiteralPath $resolved -Recurse -Force
Record 'package-finalization' ([ordered]@{archive=$archive;archive_sha256=$build.archive_sha256;archive_bytes=$build.archive_bytes;zip_compression='NoCompression';zip_storage_verified=$true;independent_builds_comparison_performed=$false;archive_integrity='phase6b-passed';installer_fixtures='phase5a-passed';scratch_removed=$resolved;previous_animation_staging_retained=$before;public_status='blocked';game_mutation=$false})
Write-Output "PACKAGE_FINAL=$archive"
