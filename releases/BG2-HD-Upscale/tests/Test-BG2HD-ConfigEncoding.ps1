[CmdletBinding()]
param([string]$ReleaseRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)
$ErrorActionPreference='Stop'
$workspace=[IO.Path]::GetFullPath((Join-Path $ReleaseRoot '../..'))
$scratch=Join-Path $workspace ('.tmp/config-encoding-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch | Out-Null
$helper=Join-Path $ReleaseRoot 'bg2hd/tools/bg2hd-config.ps1'
function Require([bool]$Value,[string]$Message){if(-not $Value){throw $Message}}
function Invoke-Config([string]$Action,[string]$Game){
    & powershell.exe -NoProfile -NonInteractive -File $helper -Action $Action -GameRoot $Game *> $null
    Require ($LASTEXITCODE-eq0) "$Action failed: $Game"
}
$encodings=@([Text.UTF8Encoding]::new($false),[Text.UTF8Encoding]::new($true),[Text.UnicodeEncoding]::new($false,$true),[Text.UnicodeEncoding]::new($true,$true))
try {
    for($i=0;$i-lt$encodings.Count;$i++){
        $encoding=$encodings[$i];$game=Join-Path $scratch "$i";New-Item -ItemType Directory -Path $game|Out-Null
        $ini=Join-Path $game 'InfinityEngine-Enhancer.ini'
        $original="; préserver éè`r`n[Shaders]`r`nEnableAreaAnimationX4 = false ; original`r`nEnableWaterOverlayRoute2 = false ; original water`r`nWaterOverlayStrength = 0.27`r`nForeign = avant`r`n"
        [IO.File]::WriteAllText($ini,$original,$encoding)
        $before=[Convert]::ToBase64String([IO.File]::ReadAllBytes($ini))
        Invoke-Config 'Apply' $game
        $bytes=[IO.File]::ReadAllBytes($ini);$bom=$encoding.GetPreamble()
        Require ($bom.Length-eq0 -or [Convert]::ToBase64String($bytes[0..($bom.Length-1)])-eq[Convert]::ToBase64String($bom)) "BOM changed: $i"
        $text=$encoding.GetString($bytes,$bom.Length,$bytes.Length-$bom.Length)
        Require ($text-match'(?m)^EnableAreaAnimationX4 = true ; original\r?$') "Animation activation missing: $i"
        Require ($text-match'(?m)^EnableWaterOverlayRoute2 = true ; original water\r?$' -and $text-match'(?m)^WaterOverlayStrength = 1\.00\r?$') "Water activation/strength missing: $i"
        Require ($text.Contains('; préserver éè') -and $text.Contains('Foreign = avant')) "Foreign text changed: $i"
        Invoke-Config 'Restore' $game
        Require ([Convert]::ToBase64String([IO.File]::ReadAllBytes($ini))-eq$before) "Exact restoration failed: $i"
        Invoke-Config 'Apply' $game
        $text=[IO.File]::ReadAllText($ini,$encoding).Replace('Foreign = avant','Foreign = après')
        [IO.File]::WriteAllText($ini,$text,$encoding)
        Invoke-Config 'Restore' $game
        $text=[IO.File]::ReadAllText($ini,$encoding)
        Require ($text.Contains('Foreign = après') -and $text.Contains('EnableAreaAnimationX4 = false ; original') -and $text.Contains('EnableWaterOverlayRoute2 = false ; original water') -and $text.Contains('WaterOverlayStrength = 0.27')) "Edited foreign key lost: $i"
    }
    Write-Output 'CONFIG_ENCODINGS=PASSED (UTF-8, UTF-8 BOM, UTF-16 LE, UTF-16 BE)'
} finally {
    $resolved=(Resolve-Path -LiteralPath $scratch).Path
    Require ([IO.Path]::GetDirectoryName($resolved)-eq(Join-Path $workspace '.tmp')) 'Unsafe fixture removal'
    Require (((Get-Item -LiteralPath $resolved).Attributes-band[IO.FileAttributes]::ReparsePoint)-eq0) 'Fixture is a reparse point'
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
