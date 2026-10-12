[CmdletBinding()]
param([string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $ReleaseRoot '../..')).Path
$fixture = Join-Path $workspace ('.tmp/sprite-config-test-' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($fixture) | Out-Null
$ini = Join-Path $fixture 'InfinityEngine-Enhancer.ini'
$initial = "[Core]`r`nUserSetting = keep`r`n[Shaders]`r`nEnableCreatureSpriteUpscaleTest = false`r`nCreatureSpriteFilter = CatmullRom`r`nEnablePaperdollQ3mTest = false`r`nEnablePaperdollUIProbe = true`r`n"
$helper = Join-Path $ReleaseRoot 'bg2hd/tools/bg2hd-config.ps1'
$manifest = Join-Path $ReleaseRoot 'manifests/runtime-compatibility.json'
function Run-Config([string]$Action, [string]$Owner) {
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Action $Action -GameRoot $fixture -CompatibilityManifestPath $manifest -Owner $Owner -StatePath (Join-Path $fixture "$Owner.json")
    if ($LASTEXITCODE -ne 0) { throw "Config $Action failed: $Owner" }
}
function Require([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
try {
    foreach ($encoding in @([Text.UTF8Encoding]::new($false), [Text.UnicodeEncoding]::new($false,$true))) {
        foreach ($order in @('world-first', 'ui-first')) {
            [IO.File]::WriteAllText($ini, $initial, $encoding)
            $world = 'sprites-approved-creatures-x2'; $ui = 'paperdolls-q3m-6110-x2'
            Run-Config Apply $world
            Run-Config Apply $ui
            $text = [IO.File]::ReadAllText($ini)
            Require ($text -match 'CreatureSpriteFilter = Nearest' -and $text -match 'EnablePaperdollQ3mTest = true' -and $text -match 'EnablePaperdollUIProbe = false') 'Q3m activation/probe contract failed.'
            [IO.File]::WriteAllText($ini, $text.Replace('UserSetting = keep', 'UserSetting = custom'), $encoding)
            if ($order -eq 'world-first') {
                Run-Config Restore $world
                $text = [IO.File]::ReadAllText($ini)
                Require ($text -match 'CreatureSpriteFilter = CatmullRom' -and $text -match 'EnablePaperdollQ3mTest = true') 'World restore overwrote UI ownership.'
                Run-Config Restore $ui
            } else {
                Run-Config Restore $ui
                $text = [IO.File]::ReadAllText($ini)
                Require ($text -match 'EnablePaperdollQ3mTest = false' -and $text -match 'CreatureSpriteFilter = Nearest') 'UI restore overwrote world ownership.'
                Run-Config Restore $world
            }
            $text = [IO.File]::ReadAllText($ini)
            Require ($text -eq $initial.Replace('UserSetting = keep', 'UserSetting = custom')) 'Restoration altered independent user settings or prior keys.'
            if ($encoding -is [Text.UnicodeEncoding]) {
                $bytes = [IO.File]::ReadAllBytes($ini)
                Require ($bytes[0] -eq 255 -and $bytes[1] -eq 254) 'UTF-16 encoding lost.'
            }
        }
    }
    Write-Output 'SPRITE_CONFIG=PASSED; four owner/encoding lifecycles; independent user setting preserved.'
} finally {
    $resolved = [IO.Path]::GetFullPath($fixture)
    if (-not $resolved.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Fixture outside workspace.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
