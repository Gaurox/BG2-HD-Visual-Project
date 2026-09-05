[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\bg2hd\bg2hd.tp2'),
    [string]$ComponentsPath = (Join-Path $PSScriptRoot '..\manifests\components.json'),
    [string]$ContentPath = (Join-Path $PSScriptRoot '..\manifests\content.json')
)

$ErrorActionPreference = 'Stop'

function Get-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Manifeste absent : $Path" }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Test-BG2HDRegularFilePath([string]$Path, [string]$Label) {
    try {
        $attributes = [IO.File]::GetAttributes($Path)
    } catch {
        $exception = $_.Exception
        while ($null -ne $exception.InnerException) { $exception = $exception.InnerException }
        if (
            $exception -is [System.IO.FileNotFoundException] -or
            $exception -is [System.IO.DirectoryNotFoundException]
        ) {
            return $false
        }
        throw
    }
    if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label ReparsePoint interdit : $Path"
    }
    if (
        ($attributes -band [IO.FileAttributes]::Directory) -ne 0 -or
        ($attributes -band [IO.FileAttributes]::Device) -ne 0 -or
        -not [IO.File]::Exists($Path)
    ) {
        throw "$Label non regulier : $Path"
    }
    return $true
}

function Write-BG2HDAtomicUtf8NoBomFile([string]$Path, [string]$Text) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $directory = [IO.Path]::GetDirectoryName($fullPath)
    if ([string]::IsNullOrWhiteSpace($directory)) { throw "Dossier de sortie introuvable : $Path" }
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $temporaryPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullPath) + '.' + [Guid]::NewGuid().ToString('N') + '.partial')
    $backupPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullPath) + '.' + [Guid]::NewGuid().ToString('N') + '.replace-backup.partial')
    $stream = $null
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text)
        $stream = [IO.FileStream]::new(
            $temporaryPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None,
            65536,
            [IO.FileOptions]::WriteThrough
        )
        if ($bytes.Length -gt 0) { $stream.Write($bytes, 0, $bytes.Length) }
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        $targetExists = Test-BG2HDRegularFilePath -Path $fullPath -Label 'Cible de publication'
        if ($targetExists) {
            [IO.File]::Replace($temporaryPath, $fullPath, $backupPath, $true)
        } else {
            [IO.File]::Move($temporaryPath, $fullPath)
        }
    }
    finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ([IO.File]::Exists($temporaryPath)) { [IO.File]::Delete($temporaryPath) }
        if ([IO.File]::Exists($backupPath)) { [IO.File]::Delete($backupPath) }
    }
}

$workspace = (Resolve-Path -LiteralPath (Join-Path $ReleaseRoot '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
$components = (Get-Json $ComponentsPath).components | Sort-Object id
$content = (Get-Json $ContentPath).entries
$release = Get-Json (Join-Path $ReleaseRoot 'manifests/release.json')
$componentNames = @{
    0 = 1; 100 = 2; 110 = 3; 1000 = 4; 1010 = 5; 1020 = 6; 1030 = 7; 1040 = 8; 1050 = 9; 1060 = 10
}
$componentById = @{}
foreach ($component in $components) {
    if ($componentById.ContainsKey([int]$component.id)) { throw "ID composant duplique : $($component.id)" }
    $componentById[[int]$component.id] = $component
}
foreach ($entry in $content) {
    if (-not $componentById.ContainsKey([int]$entry.component_id)) { throw "Entree de contenu sans composant : $($entry.source)" }
    $validScale = ([int]$entry.scale -eq 4) -or ($entry.kind -eq 'overlay' -and [int]$entry.scale -eq 2)
    if ($entry.qa_status -ne 'validated' -or -not $validScale) { throw "Contenu non valide : $($entry.source)" }
    if ($entry.source -match '(^|/)(override|backups|archive|captures|temp)(/|$)') { throw "Source interdite : $($entry.source)" }
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('// Generated from manifests/components.json and manifests/content.json. Do not edit manually.')
$lines.Add('BACKUP ~bg2hd/backup~')
$lines.Add('AUTHOR ~BG2 Upscale Project~')
$lines.Add("VERSION ~$($release.version)~")
$lines.Add('AUTO_EVAL_STRINGS')
$lines.Add('')
foreach ($language in @('english', 'french', 'german', 'spanish', 'italian', 'polish', 'russian', 'korean', 'chinese')) {
    $label = switch ($language) {
        'english' { 'English' }; 'french' { 'Francais' }; 'german' { 'Deutsch' }; 'spanish' { 'Espanol' }; 'italian' { 'Italiano' }; 'polish' { 'Polski' }; 'russian' { 'Russian' }; 'korean' { 'Korean' }; 'chinese' { 'Simplified Chinese' }
    }
    $lines.Add("LANGUAGE ~$label~ ~$language~ ~bg2hd/tra/english/setup.tra~ ~bg2hd/tra/$language/setup.tra~")
}
$lines.Add('')
foreach ($component in $components) {
    $id = [int]$component.id
    # The original Core/UI entries are translated through the TRA files. Map
    # components use their stable area code as a language-neutral literal so a
    # newly validated map cannot be omitted merely because it lacks a sentence
    # translated in every UI language.
    $beginLabel = if ($componentNames.ContainsKey($id)) { "@$($componentNames[$id])" } else { "~$($component.name)~" }
    $lines.Add("BEGIN $beginLabel")
    $lines.Add("  DESIGNATED $id")
    $lines.Add("  LABEL ~$($component.label)~")
    if ($id -eq 0) {
        $lines.Add('  INSTALL_BY_DEFAULT')
        $lines.Add('  REQUIRE_PREDICATE GAME_IS ~bg2ee~ @11')
        $lines.Add('  REQUIRE_COMPONENT ~EEEX/EEEX.TP2~ ~0~ @12')
        $lines.Add('  REQUIRE_COMPONENT ~EEEX/EEEX.TP2~ ~1~ @13')
        $lines.Add('  AT_NOW preflight_result ~powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File bg2hd/tools/bg2hd-steam.ps1 -Action Test~')
        $lines.Add('  ACTION_IF preflight_result != 0 THEN BEGIN FAIL @17 END')
        $lines.Add('  AT_NOW install_result ~powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File bg2hd/tools/bg2hd-steam.ps1 -Action Install~')
        $lines.Add('  ACTION_IF install_result != 0 THEN BEGIN FAIL @18 END')
        $lines.Add('  AT_UNINSTALL ~powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File bg2hd/tools/bg2hd-steam.ps1 -Action Uninstall~')
    } else {
        $lines.Add('  REQUIRE_PREDICATE GAME_IS ~bg2ee~ @11')
        foreach ($dependency in $component.depends_on) {
            $message = if ([int]$dependency -eq 0) { '@14' } else { '@15' }
            $lines.Add("  REQUIRE_COMPONENT ~bg2hd/bg2hd.tp2~ ~$dependency~ $message")
        }
        $entries = @($content | Where-Object { [int]$_.component_id -eq $id } | Sort-Object install_order, destination, source)
        $directories = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($entry in $entries) {
            $segments = @(([string]$entry.destination).Split('/'))
            for ($segmentCount = 1; $segmentCount -lt $segments.Count; $segmentCount++) {
                [void]$directories.Add(($segments[0..($segmentCount - 1)] -join '/'))
            }
        }
        foreach ($directory in @($directories | Sort-Object { ($_ -split '/').Count }, { $_ })) {
            $lines.Add("  MKDIR ~$directory~")
        }
        foreach ($entry in $entries) {
            $sourceName = [IO.Path]::GetFileName($entry.source)
            $payload = "bg2hd/payload/$($entry.payload_group)/$sourceName"
            $lines.Add("  COPY_LARGE ~$payload~ ~$($entry.destination)~")
        }
        if ($component.label -eq 'ui-mainmenu-x4') {
            # The renderer only replaces UI uploads when these owned keys are
            # enabled.  Keep the UI component's state separate from Core so
            # either component can be uninstalled without overwriting the
            # other's configuration rollback journal.
            $lines.Add('  AT_NOW ui_config_result ~powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File bg2hd/tools/bg2hd-config.ps1 -Action Apply -GameRoot . -Owner ui-mainmenu-x4 -StatePath bg2hd/state/renderer-config-ui-mainmenu.json~')
            $lines.Add('  ACTION_IF ui_config_result != 0 THEN BEGIN FAIL @19 END')
            $lines.Add('  AT_UNINSTALL ~powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File bg2hd/tools/bg2hd-config.ps1 -Action Restore -GameRoot . -Owner ui-mainmenu-x4 -StatePath bg2hd/state/renderer-config-ui-mainmenu.json~')
        }
    }
    $lines.Add('')
}

$lastIndex = $lines.Count - 1
if ($lastIndex -ge 0 -and $lines[$lastIndex] -eq '') { $lines.RemoveAt($lastIndex) }
Write-BG2HDAtomicUtf8NoBomFile -Path $OutputPath -Text (($lines -join [Environment]::NewLine) + [Environment]::NewLine)
Write-Output "Generated $OutputPath with $($components.Count) components and $($content.Count) COPY_LARGE operations."
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
