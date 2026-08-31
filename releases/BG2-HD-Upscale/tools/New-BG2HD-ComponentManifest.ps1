[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\manifests\components.json'),
    [string]$ContentPath = (Join-Path $PSScriptRoot '..\manifests\content.json'),
    [string]$AnimationCandidatesPath = (Join-Path $PSScriptRoot '..\manifests\animation-release-candidates.json')
)

$ErrorActionPreference = 'Stop'

function Read-Json([string]$Path) {
    Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$content = Read-Json $ContentPath
$existing = Read-Json (Join-Path $release 'manifests\components.json')
$animationCandidates = Read-Json $AnimationCandidatesPath

# Core and UI remain explicitly maintained because they have special lifecycle
# behavior. Every validated map component is then derived from content.json so
# it is impossible for an archived payload to have an orphan component ID.
$base = @($existing.components | Where-Object { [int]$_.id -in @(0, 100, 110) } | Sort-Object id)
if (@($base | Where-Object { [int]$_.id -eq 0 }).Count -ne 1) { throw 'Composant Core 0 absent ou duplique.' }
if (@($base | Where-Object { [int]$_.id -eq 100 }).Count -ne 1 -or @($base | Where-Object { [int]$_.id -eq 110 }).Count -ne 1) { throw 'Composants UI attendus absents.' }

$maps = @($content.entries | Where-Object { $_.kind -eq 'map' } | Group-Object component_id | Sort-Object { [int]$_.Name })
$mapOverlayDependencies = @{
    AR3000 = @(70, 80, 90, 95)
}
$mapComponents = foreach ($group in $maps) {
    $entries = @($group.Group)
    $labels = @($entries | ForEach-Object { [string]$_.component_label } | Sort-Object -Unique)
    $groups = @($entries | ForEach-Object { [string]$_.payload_group } | Sort-Object -Unique)
    $areas = @($entries | ForEach-Object { ([string]$_.area) -replace 'N$','' } | Sort-Object -Unique)
    if ($labels.Count -ne 1 -or $groups.Count -ne 1 -or $areas.Count -ne 1) { throw "Composant carte incoherent : $($group.Name)" }
    $hasNight = @($entries | Where-Object { ([string]$_.area).EndsWith('N') }).Count -gt 0
    $dependencies = @(0)
    if ($mapOverlayDependencies.ContainsKey($areas[0])) {
        $dependencies += @($mapOverlayDependencies[$areas[0]])
    }
    [ordered]@{
        id = [int]$group.Name
        label = $labels[0]
        name = if ($hasNight) { "$($areas[0]) (day and night, x4)" } else { "$($areas[0]) (x4)" }
        status = 'validated'
        depends_on = @($dependencies)
        payload_groups = @($groups[0])
    }
}

$overlays = @($content.entries | Where-Object { $_.kind -eq 'overlay' } | Group-Object component_id | Sort-Object { [int]$_.Name })
$overlayComponents = foreach ($group in $overlays) {
    $entries = @($group.Group)
    $labels = @($entries | ForEach-Object { [string]$_.component_label } | Sort-Object -Unique)
    $groups = @($entries | ForEach-Object { [string]$_.payload_group } | Sort-Object -Unique)
    $areas = @($entries | ForEach-Object { [string]$_.area } | Sort-Object -Unique)
    $scales = @($entries | ForEach-Object { [int]$_.scale } | Sort-Object -Unique)
    if ($labels.Count -ne 1 -or $groups.Count -ne 1 -or $areas.Count -ne 1 -or $scales.Count -ne 1) { throw "Composant overlay incoherent : $($group.Name)" }
    [ordered]@{
        id = [int]$group.Name
        label = $labels[0]
        name = "$($areas[0]) technical overlay (x$($scales[0]))"
        status = 'validated'
        depends_on = @(0)
        payload_groups = @($groups[0])
    }
}

$animations = @($content.entries | Where-Object { $_.kind -eq 'area-animation' } | Group-Object component_id | Sort-Object { [int]$_.Name })
$animationComponents = foreach ($group in $animations) {
    $entries = @($group.Group)
    $labels = @($entries | ForEach-Object { [string]$_.component_label } | Sort-Object -Unique)
    $groups = @($entries | ForEach-Object { [string]$_.payload_group } | Sort-Object -Unique)
    $areas = @($entries | ForEach-Object { [string]$_.area } | Sort-Object -Unique)
    $roots = @($entries | ForEach-Object { ([string]$_.destination -split '/', 4)[0..2] -join '/' } | Sort-Object -Unique)
    if ($labels.Count -ne 1 -or $groups.Count -ne 1 -or $areas.Count -ne 1 -or $roots.Count -ne 1 -or $roots[0] -ne "iee-assets/areas/$($areas[0])") {
        throw "Composant animation de zone incoherent : $($group.Name)"
    }
    $dependencies = @(0)
    $candidate = @($animationCandidates.candidates | Where-Object { [string]$_.area -eq $areas[0] })
    if ($candidate.Count -ne 1) { throw "Candidat animation absent ou duplique : $($areas[0])" }
    if ($null -ne $candidate[0].occlusion_contract) {
        $dependencies += [int]$candidate[0].occlusion_contract.map_component_id
    }
    [ordered]@{
        id = [int]$group.Name
        label = $labels[0]
        name = "$($areas[0]) area animations (x4)"
        status = 'validated'
        depends_on = @($dependencies | Sort-Object -Unique)
        payload_groups = @($groups[0])
    }
}

$components = @($base + $overlayComponents + $mapComponents + $animationComponents | Sort-Object id)
$ids = @($components | ForEach-Object { [int]$_.id })
if (@($ids | Sort-Object -Unique).Count -ne $ids.Count) { throw 'ID composant duplique apres generation.' }

$manifest = [ordered]@{
    '$schema' = '../schemas/components.schema.json'
    schema_version = 1
    components = $components
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $directory -Force | Out-Null
[IO.File]::WriteAllText($OutputPath, ($manifest | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
Write-Output "Wrote $($components.Count) components to $OutputPath"
