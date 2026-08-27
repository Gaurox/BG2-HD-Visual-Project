[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Apply,
    [switch]$Resume,
    [switch]$RepairJobEncoding,
    [switch]$RestoreActiveCatalogJobContract
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$SpriteRoot = Join-Path $ProjectRoot 'sprite'
$ExternalSpriteRoot = 'G:\AI\BG2\_Upscale\sprite'
$ExternalLeafRelative = 'families\monster-icewind\e4xx-goblins\e400-mgo1-goblin-axe'
$MonsterGoblinRelative = 'families\monster-icewind\e4xx-goblins\e400-mgo1-goblin-axe'
$StandardRootDirectories = @('.work', 'catalogs', 'docs', 'experiments', 'families', 'index', 'jobs')

function To-ProjectRelative([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = "$ProjectRoot\"
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside project: $full"
    }
    return $full.Substring($prefix.Length).Replace('\', '/')
}

function Get-WorkspaceTarget([string]$Name) {
    switch -Regex ($Name) {
        '^dwarf_male_fighter_complete_xn_xbr2x$' {
            return 'families\playable-characters\6102-dwarf-male-fighter\family-runs\complete-xn-xbr2x'
        }
        '^human_female_fighter_complete_xn_xbr2x$' {
            return 'families\playable-characters\6110-human-female-fighter\family-runs\complete-xn-xbr2x'
        }
        '^human_female_fighter_(character_set|armor_set)$' {
            return "families\playable-characters\6110-human-female-fighter\family-runs\$($Matches[1].Replace('_', '-'))"
        }
        '^dwarf-male-fighter-cdmb1$' {
            return 'families\playable-characters\6102-dwarf-male-fighter\cdmb1\variants\xbr2x-legacy'
        }
        '^dwarf-male-fighter-cdmb1-aa$' {
            return 'families\playable-characters\6102-dwarf-male-fighter\cdmb1\variants\xbr2x-aa'
        }
        '^dwarf-male-fighter-cdmb1-x4$' {
            return 'families\playable-characters\6102-dwarf-male-fighter\cdmb1\variants\xbr4-direct'
        }
        '^dwarf_male_fighter_(.+)$' {
            return "families\playable-characters\6102-dwarf-male-fighter\$($Matches[1].Replace('_', '-'))"
        }
        '^dwarf-male-fighter-(.+)$' {
            return "families\playable-characters\6102-dwarf-male-fighter\$($Matches[1])"
        }
        '^gaurox_dwarf_male_(.+)$' {
            return "families\playable-characters\6102-dwarf-male-fighter\gaurox-$($Matches[1].Replace('_', '-'))"
        }
        '^gaurox-dwarf-male-(.+)$' {
            return "families\playable-characters\6102-dwarf-male-fighter\gaurox-$($Matches[1])"
        }
        '^human_female_fighter_(.+)$' {
            return "families\playable-characters\6110-human-female-fighter\$($Matches[1].Replace('_', '-'))"
        }
        '^human-female-fighter-(.+)$' {
            return "families\playable-characters\6110-human-female-fighter\$($Matches[1])"
        }
        '^goblin_axe$' {
            return "$MonsterGoblinRelative\legacy-workspace"
        }
        '^goblin-mgo1-xbr2x-catalog$' {
            return "$MonsterGoblinRelative\catalog-x2-nearest"
        }
        '^creature_sprites_progressive_xn_xbr2x$' {
            return 'catalogs\creature-x2-nearest\runs\catalog-x2-nearest'
        }
        '^minsc$' {
            return 'families\playable-characters\6100-minsc\minsc'
        }
        default {
            throw "No standardized family destination is defined for sprite workspace '$Name'."
        }
    }
}

function Get-SpriteRootFromJob([object]$Job, [string]$JobName) {
    if ($null -eq $Job.paths) {
        throw "Job '$JobName' has no paths object."
    }
    $pathValues = @()
    foreach ($field in @('source_dir', 'run_dir')) {
        $property = $Job.paths.PSObject.Properties[$field]
        if ($null -ne $property) {
            $pathValues += $property.Value
        }
    }
    foreach ($value in $pathValues) {
        $text = [string]$value
        if ($text -match '^sprite[\\/]([^\\/]+)') {
            return $Matches[1]
        }
    }
    throw "Cannot derive workspace root from job '$JobName'."
}

function Get-FileInventory([string]$Root) {
    return @(
        Get-ChildItem -LiteralPath $Root -File -Recurse -Force | ForEach-Object {
            [pscustomobject]@{
                relative_path = $_.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/')
                length = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        } | Sort-Object relative_path
    )
}

function Write-JsonAtomic([string]$Path, [object]$Payload) {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $temporary = Join-Path $parent ('.' + [IO.Path]::GetFileName($Path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        $json = $Payload | ConvertTo-Json -Depth 12
        [IO.File]::WriteAllText($temporary, $json, [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Read-Utf8([string]$Path) {
    return [IO.File]::ReadAllText($Path, [Text.UTF8Encoding]::new($false))
}

function Test-Mojibake([string]$Text) {
    return $Text.IndexOf([char]0x00C3) -ge 0 -or $Text.IndexOf([char]0x00E2) -ge 0
}

function Replace-JobPaths([string]$JobPath, [object[]]$Replacements) {
    $text = Read-Utf8 $JobPath
    foreach ($replacement in $Replacements | Sort-Object { $_.from.Length } -Descending) {
        $text = $text.Replace([string]$replacement.from, [string]$replacement.to)
    }
    [IO.File]::WriteAllText($JobPath, $text, [Text.UTF8Encoding]::new($false))
}

function Repair-JobEncoding {
    $jobFiles = @(
        Get-ChildItem -LiteralPath $SpriteRoot -Recurse -File -Filter '*.json' |
            Where-Object { $_.Directory.Name -eq 'jobs' }
    )
    if ($jobFiles.Count -ne 140) {
        throw "Encoding repair requires exactly 140 relocated job descriptors; found $($jobFiles.Count)."
    }
    $ansi = [Text.Encoding]::GetEncoding(1252)
    $utf8 = [Text.UTF8Encoding]::new($false)
    $repaired = 0
    foreach ($file in $jobFiles) {
        $text = Read-Utf8 $file.FullName
        if (-not (Test-Mojibake $text)) {
            continue
        }
        $corrected = $text
        for ($pass = 0; $pass -lt 4 -and (Test-Mojibake $corrected); $pass++) {
            $next = $utf8.GetString($ansi.GetBytes($corrected))
            if ($next -eq $corrected) {
                throw "UTF-8 repair made no progress: $($file.FullName)"
            }
            $corrected = $next
        }
        if (Test-Mojibake $corrected) {
            throw "UTF-8 repair exceeded the safe pass limit: $($file.FullName)"
        }
        try {
            $null = $corrected | ConvertFrom-Json
        }
        catch {
            throw "UTF-8 repair produced invalid JSON: $($file.FullName)"
        }
        [IO.File]::WriteAllText($file.FullName, $corrected, $utf8)
        $repaired++
    }
    "Repaired UTF-8 job descriptors: $repaired"
}

function Restore-ActiveCatalogJobContract {
    $runRoot = Join-Path $SpriteRoot 'catalogs\creature-x2-nearest\runs\catalog-x2-nearest\runs\catalog-xbr2x-x2'
    $statePath = Join-Path $runRoot 'ingame-installation\active-test.json'
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        throw "Active catalog state is missing: $statePath"
    }
    $state = Read-Utf8 $statePath | ConvertFrom-Json
    $legacyJob = [string]$state.job_file
    $expectedHash = [string]$state.job_sha256
    if ($legacyJob -notmatch '^sprite/jobs/[a-z0-9][a-z0-9-]*\.json$' -or $expectedHash -notmatch '^[0-9A-F]{64}$') {
        throw 'Active catalog state has no valid sealed job identity.'
    }
    $indexPath = Join-Path $SpriteRoot 'index\path-migrations.json'
    $index = Read-Utf8 $indexPath | ConvertFrom-Json
    $entry = @($index.migrations | Where-Object { [string]$_.from -eq $legacyJob })
    if ($entry.Count -ne 1) {
        throw "No unique current location for sealed active job: $legacyJob"
    }
    $jobPath = Join-Path $ProjectRoot ([string]$entry[0].to).Replace('/', '\')
    if (-not (Test-Path -LiteralPath $jobPath -PathType Leaf)) {
        throw "Current active job is missing: $jobPath"
    }
    $text = Read-Utf8 $jobPath
    foreach ($rule in @($index.migrations | Sort-Object { $_.to.Length } -Descending)) {
        $text = $text.Replace([string]$rule.to, [string]$rule.from)
    }
    $text = $text.Replace('sprite/.work/cmake/catalog', 'sprite/.cmake-catalog')
    $text = $text.Replace('sprite/.work/cmake/monster-icewind/e400-mgo1', 'sprite/.cmake-goblin-mgo1')
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = ([BitConverter]::ToString($sha256.ComputeHash([Text.UTF8Encoding]::new($false).GetBytes($text)))).Replace('-', '')
    }
    finally {
        $sha256.Dispose()
    }
    if ($hash -ne $expectedHash) {
        throw "Reconstructed active job hash differs from sealed state: $hash"
    }
    [IO.File]::WriteAllText($jobPath, $text, [Text.UTF8Encoding]::new($false))
    $actual = (Get-FileHash -LiteralPath $jobPath -Algorithm SHA256).Hash
    if ($actual -ne $expectedHash) {
        throw "Active job write hash differs from sealed state: $actual"
    }
    "Restored sealed active catalog job contract: $legacyJob"
}

function Resume-PartialSpriteLayoutMigration {
    $openGame = Get-Process -Name BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
    if ($openGame) {
        throw 'BG2EE is running. Close BaldurReal/InfinityLoader before resuming the active sprite run migration.'
    }
    $catalogJobsDirectory = Join-Path $SpriteRoot 'catalogs\creature-x2-nearest\jobs'
    $jobFiles = @(
        Get-ChildItem -LiteralPath $SpriteRoot -Recurse -File -Filter '*.json' |
            Where-Object { $_.Directory.Name -eq 'jobs' } |
            Sort-Object FullName
    )
    if ($jobFiles.Count -ne 140) {
        throw "Resume requires exactly 140 relocated job descriptors; found $($jobFiles.Count)."
    }
    $workspaceByOldRoot = @{}
    $jobRecords = @(
        foreach ($file in $jobFiles) {
            $job = Read-Utf8 $file.FullName | ConvertFrom-Json
            $legacyRoot = Get-SpriteRootFromJob $job $file.Name
            $workspacePath = if ($file.Directory.FullName -ieq $catalogJobsDirectory) {
                Join-Path $SpriteRoot 'catalogs\creature-x2-nearest\runs\catalog-x2-nearest'
            }
            else {
                $file.Directory.Parent.FullName
            }
            $workspaceRelative = To-ProjectRelative $workspacePath
            $existing = $workspaceByOldRoot[$legacyRoot]
            if ($null -ne $existing -and $existing -ne $workspaceRelative) {
                throw "Legacy workspace '$legacyRoot' maps to more than one current location."
            }
            $workspaceByOldRoot[$legacyRoot] = $workspaceRelative
            [pscustomobject]@{
                from = "sprite/jobs/$($file.Name)"
                to = To-ProjectRelative $file.FullName
                destination = $file.FullName
            }
        }
    )
    $minscWorkspace = 'sprite/families/playable-characters/6100-minsc/minsc'
    if (-not $workspaceByOldRoot.ContainsKey('minsc')) {
        if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot $minscWorkspace) -PathType Container)) {
            throw "Expected Minsc workspace is missing: $minscWorkspace"
        }
        $workspaceByOldRoot['minsc'] = $minscWorkspace
    }
    if ($workspaceByOldRoot.Count -ne 140) {
        throw "Resume requires 140 unique legacy workspaces; found $($workspaceByOldRoot.Count)."
    }
    $workspaceRecords = @(
        foreach ($name in $workspaceByOldRoot.Keys | Sort-Object) {
            [pscustomobject]@{ from = "sprite/$name"; to = $workspaceByOldRoot[$name] }
        }
    )
    $cacheRecords = @(
        [pscustomobject]@{ from = 'sprite/.cmake-catalog'; to = 'sprite/.work/cmake/archive/catalog-pre-layout' },
        [pscustomobject]@{ from = 'sprite/.cmake-goblin-mgo1'; to = 'sprite/.work/cmake/archive/goblin-mgo1-pre-layout' }
    )
    foreach ($record in $cacheRecords) {
        if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot $record.to) -PathType Container)) {
            throw "Expected archived CMake cache is missing: $($record.to)"
        }
    }
    $migrations = @($workspaceRecords + $jobRecords + $cacheRecords | ForEach-Object {
        [ordered]@{ from = $_.from; to = $_.to }
    })
    $jobReplacements = @($workspaceRecords + $jobRecords)
    foreach ($record in $jobRecords) {
        Replace-JobPaths -JobPath $record.destination -Replacements $jobReplacements
        $text = Read-Utf8 $record.destination
        $text = $text.Replace('sprite/.cmake-catalog', 'sprite/.work/cmake/catalog')
        $text = $text.Replace('sprite/.cmake-goblin-mgo1', 'sprite/.work/cmake/monster-icewind/e400-mgo1')
        [IO.File]::WriteAllText($record.destination, $text, [Text.UTF8Encoding]::new($false))
    }

    $externalLeaf = Join-Path $ExternalSpriteRoot $ExternalLeafRelative
    if (-not (Test-Path -LiteralPath $externalLeaf -PathType Container)) {
        throw "Expected external MGO1 archive is missing: $externalLeaf"
    }
    $externalInventory = Get-FileInventory $ExternalSpriteRoot
    if ($externalInventory.Count -eq 0) {
        throw 'External sprite repository has no files. Refusing to delete it.'
    }
    $goblinRoot = Join-Path $SpriteRoot $MonsterGoblinRelative
    $researchRoot = Join-Path $goblinRoot 'research'
    if (Test-Path -LiteralPath $researchRoot) {
        throw "Research import destination already exists: $researchRoot"
    }
    New-Item -ItemType Directory -Force -Path $researchRoot | Out-Null
    Get-ChildItem -LiteralPath $externalLeaf -Force | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination (Join-Path $researchRoot $_.Name)
    }
    $externalRootReadme = Join-Path $ExternalSpriteRoot 'README.md'
    if (Test-Path -LiteralPath $externalRootReadme -PathType Leaf) {
        Move-Item -LiteralPath $externalRootReadme -Destination (Join-Path $researchRoot 'EXTERNAL_REPOSITORY_README.md')
    }
    foreach ($item in $externalInventory) {
        $target = if ($item.relative_path -eq 'README.md') {
            Join-Path $researchRoot 'EXTERNAL_REPOSITORY_README.md'
        }
        else {
            $prefix = "$($ExternalLeafRelative.Replace('\', '/'))/"
            if (-not $item.relative_path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Unexpected external file location: $($item.relative_path)"
            }
            Join-Path $researchRoot $item.relative_path.Substring($prefix.Length).Replace('/', '\')
        }
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
            throw "Imported external file is missing: $target"
        }
        $actual = Get-FileHash -LiteralPath $target -Algorithm SHA256
        if ($actual.Hash -ne $item.sha256 -or (Get-Item -LiteralPath $target).Length -ne $item.length) {
            throw "External file integrity mismatch: $target"
        }
    }
    $migrationIndex = [ordered]@{
        schema = 'bg2-upscale-sprite-path-migrations-v1'
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        purpose = 'Resolve immutable pre-layout manifests after sprite workspace reorganization.'
        migrations = $migrations
    }
    $layoutIndex = [ordered]@{
        schema = 'bg2-upscale-sprite-layout-v1'
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        workspaces = @($workspaceRecords | ForEach-Object { [ordered]@{ legacy_root = $_.from; location = $_.to } })
        jobs = @($jobRecords | ForEach-Object { [ordered]@{ legacy_job = $_.from; location = $_.to } })
        external_import = [ordered]@{
            source = $ExternalSpriteRoot
            files = $externalInventory.Count
            bytes = [long](($externalInventory | Measure-Object length -Sum).Sum)
            destination = "sprite/$($MonsterGoblinRelative.Replace('\', '/'))/research"
        }
    }
    Write-JsonAtomic -Path (Join-Path $SpriteRoot 'index\path-migrations.json') -Payload $migrationIndex
    Write-JsonAtomic -Path (Join-Path $SpriteRoot 'index\sprite-layout.json') -Payload $layoutIndex
    if ((Get-ChildItem -LiteralPath $ExternalSpriteRoot -File -Recurse -Force | Measure-Object).Count -ne 0) {
        throw 'External sprite repository still contains files; refusing deletion.'
    }
    $externalResolved = (Resolve-Path -LiteralPath $ExternalSpriteRoot).Path
    if ($externalResolved -ne $ExternalSpriteRoot) {
        throw "External deletion target changed unexpectedly: $externalResolved"
    }
    Remove-Item -LiteralPath $externalResolved -Recurse -Force
    $legacyJobsRoot = Join-Path $SpriteRoot 'jobs'
    if (Test-Path -LiteralPath $legacyJobsRoot) {
        if ((Get-ChildItem -LiteralPath $legacyJobsRoot -Force | Measure-Object).Count -ne 0) {
            throw 'Legacy sprite/jobs directory is not empty after migration.'
        }
        Remove-Item -LiteralPath $legacyJobsRoot -Force
    }
    [ordered]@{
        status = 'sprite-layout-migration-resumed'
        workspace_moves = $workspaceRecords.Count
        job_moves = $jobRecords.Count
        external_files_imported = $externalInventory.Count
        external_repository_removed = -not (Test-Path -LiteralPath $ExternalSpriteRoot)
        path_migration_index = 'sprite/index/path-migrations.json'
        layout_index = 'sprite/index/sprite-layout.json'
    } | ConvertTo-Json -Depth 4
}

if ($Resume) {
    if (-not $Apply) {
        throw '-Resume requires -Apply.'
    }
    Resume-PartialSpriteLayoutMigration
    return
}

if ($RepairJobEncoding) {
    if (-not $Apply) {
        throw '-RepairJobEncoding requires -Apply.'
    }
    Repair-JobEncoding
    return
}

if ($RestoreActiveCatalogJobContract) {
    if (-not $Apply) {
        throw '-RestoreActiveCatalogJobContract requires -Apply.'
    }
    Restore-ActiveCatalogJobContract
    return
}

$openGame = Get-Process -Name BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($openGame) {
    throw 'BG2EE is running. Close BaldurReal/InfinityLoader before moving the active sprite run.'
}
if (-not (Test-Path -LiteralPath $SpriteRoot -PathType Container)) {
    throw "Sprite root does not exist: $SpriteRoot"
}
if (-not (Test-Path -LiteralPath $ExternalSpriteRoot -PathType Container)) {
    throw "External sprite repository does not exist: $ExternalSpriteRoot"
}

$workspaceDirectories = @(
    Get-ChildItem -LiteralPath $SpriteRoot -Directory -Force |
        Where-Object { $_.Name -notin $StandardRootDirectories -and $_.Name -notmatch '^\.cmake-' } |
        Sort-Object Name
)
if ($workspaceDirectories.Count -eq 0) {
    throw 'No legacy top-level sprite workspaces found. Refusing a partial migration.'
}

$workspaceRecords = @(
    foreach ($directory in $workspaceDirectories) {
        $targetRelative = Get-WorkspaceTarget $directory.Name
        [pscustomobject]@{
            legacy_name = $directory.Name
            from = "sprite/$($directory.Name)"
            to = "sprite/$($targetRelative.Replace('\', '/'))"
            source = $directory.FullName
            destination = Join-Path $SpriteRoot $targetRelative
        }
    }
)
if (@($workspaceRecords | Group-Object to | Where-Object Count -gt 1).Count -gt 0) {
    throw 'Two legacy workspaces resolve to the same standardized destination.'
}
foreach ($record in $workspaceRecords) {
    if (Test-Path -LiteralPath $record.destination) {
        throw "Standardized destination already exists: $($record.destination)"
    }
}

$recordsByLegacyName = @{}
foreach ($record in $workspaceRecords) {
    $recordsByLegacyName[$record.legacy_name] = $record
}

$legacyJobsRoot = Join-Path $SpriteRoot 'jobs'
if (-not (Test-Path -LiteralPath $legacyJobsRoot -PathType Container)) {
    throw "Legacy jobs directory does not exist: $legacyJobsRoot"
}
$jobRecords = @(
    Get-ChildItem -LiteralPath $legacyJobsRoot -File -Filter '*.json' | Sort-Object Name | ForEach-Object {
        $job = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        $legacyRoot = Get-SpriteRootFromJob $job $_.Name
        if (-not $recordsByLegacyName.ContainsKey($legacyRoot)) {
            throw "Job '$($_.Name)' refers to unknown workspace '$legacyRoot'."
        }
        $workspace = $recordsByLegacyName[$legacyRoot]
        $destinationDirectory = if ($legacyRoot -eq 'creature_sprites_progressive_xn_xbr2x') {
            Join-Path $SpriteRoot 'catalogs\creature-x2-nearest\jobs'
        }
        else {
            Join-Path $workspace.destination 'jobs'
        }
        [pscustomobject]@{
            from = "sprite/jobs/$($_.Name)"
            to = (To-ProjectRelative (Join-Path $destinationDirectory $_.Name))
            source = $_.FullName
            destination = Join-Path $destinationDirectory $_.Name
        }
    }
)
if ($jobRecords.Count -eq 0) {
    throw 'No JSON jobs found. Refusing a migration without job descriptors.'
}
if (@($jobRecords | Group-Object to | Where-Object Count -gt 1).Count -gt 0) {
    throw 'Two legacy jobs resolve to the same standardized destination.'
}

$cacheRecords = @(
    [pscustomobject]@{
        from = 'sprite/.cmake-catalog'
        to = 'sprite/.work/cmake/archive/catalog-pre-layout'
        source = Join-Path $SpriteRoot '.cmake-catalog'
        destination = Join-Path $SpriteRoot '.work\cmake\archive\catalog-pre-layout'
    },
    [pscustomobject]@{
        from = 'sprite/.cmake-goblin-mgo1'
        to = 'sprite/.work/cmake/archive/goblin-mgo1-pre-layout'
        source = Join-Path $SpriteRoot '.cmake-goblin-mgo1'
        destination = Join-Path $SpriteRoot '.work\cmake\archive\goblin-mgo1-pre-layout'
    }
)
foreach ($record in $cacheRecords) {
    if (-not (Test-Path -LiteralPath $record.source -PathType Container)) {
        throw "Expected CMake cache is missing: $($record.source)"
    }
    if (Test-Path -LiteralPath $record.destination) {
        throw "CMake archive destination already exists: $($record.destination)"
    }
}

$externalLeaf = Join-Path $ExternalSpriteRoot $ExternalLeafRelative
if (-not (Test-Path -LiteralPath $externalLeaf -PathType Container)) {
    throw "Expected external MGO1 archive is missing: $externalLeaf"
}
$externalInventory = Get-FileInventory $ExternalSpriteRoot
if ($externalInventory.Count -eq 0) {
    throw 'External sprite repository has no files. Refusing to delete it.'
}

$migrations = @($workspaceRecords + $jobRecords + $cacheRecords | ForEach-Object {
    [ordered]@{ from = $_.from; to = $_.to }
})
$migrationIndex = [ordered]@{
    schema = 'bg2-upscale-sprite-path-migrations-v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    purpose = 'Resolve immutable pre-layout manifests after sprite workspace reorganization.'
    migrations = $migrations
}
$layoutIndex = [ordered]@{
    schema = 'bg2-upscale-sprite-layout-v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    workspaces = @($workspaceRecords | ForEach-Object {
        [ordered]@{ legacy_root = $_.from; location = $_.to }
    })
    jobs = @($jobRecords | ForEach-Object {
        [ordered]@{ legacy_job = $_.from; location = $_.to }
    })
    external_import = [ordered]@{
        source = $ExternalSpriteRoot
        files = $externalInventory.Count
        bytes = [long](($externalInventory | Measure-Object length -Sum).Sum)
        destination = "sprite/$($MonsterGoblinRelative.Replace('\', '/'))/research"
    }
}

"Planned workspace moves: $($workspaceRecords.Count)"
"Planned job moves: $($jobRecords.Count)"
"External files to import: $($externalInventory.Count)"
if (-not $Apply) {
    $workspaceRecords | Select-Object from, to | Format-Table -AutoSize
    $jobRecords | Select-Object from, to | Format-Table -AutoSize
    Write-Output 'Dry run only. Re-run with -Apply to perform the migration.'
    return
}

foreach ($record in $workspaceRecords) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $record.destination) | Out-Null
    Move-Item -LiteralPath $record.source -Destination $record.destination
}
foreach ($record in $jobRecords) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $record.destination) | Out-Null
    Move-Item -LiteralPath $record.source -Destination $record.destination
}
foreach ($record in $cacheRecords) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $record.destination) | Out-Null
    Move-Item -LiteralPath $record.source -Destination $record.destination
}

$archiveDocsRoot = Join-Path $SpriteRoot 'docs\archive'
New-Item -ItemType Directory -Force -Path $archiveDocsRoot | Out-Null
Get-ChildItem -LiteralPath $SpriteRoot -File -Filter '*.md' | Where-Object {
    $_.Name -notin @('README.md', 'FOLDER_LAYOUT.md')
} | ForEach-Object {
    $destination = Join-Path $archiveDocsRoot $_.Name
    if (Test-Path -LiteralPath $destination) {
        throw "Historical documentation destination already exists: $destination"
    }
    Move-Item -LiteralPath $_.FullName -Destination $destination
}
$legacyExperimentsRoot = Join-Path $SpriteRoot 'experiments'
if (Test-Path -LiteralPath $legacyExperimentsRoot -PathType Container) {
    $legacyExperimentEntries = @(Get-ChildItem -LiteralPath $legacyExperimentsRoot -Force)
    if ($legacyExperimentEntries.Count -ne 1 -or $legacyExperimentEntries[0].Name -ne 'README.md') {
        throw 'Legacy sprite/experiments is not the known empty documentation stub.'
    }
    Move-Item -LiteralPath $legacyExperimentEntries[0].FullName -Destination (Join-Path $archiveDocsRoot 'EXPERIMENTS_ROOT_README.md')
    Remove-Item -LiteralPath $legacyExperimentsRoot -Force
}

$jobReplacements = @($migrations | ForEach-Object { [pscustomobject]$_ })
foreach ($record in $jobRecords) {
    Replace-JobPaths -JobPath $record.destination -Replacements $jobReplacements
}

$goblinRoot = Join-Path $SpriteRoot $MonsterGoblinRelative
$researchRoot = Join-Path $goblinRoot 'research'
New-Item -ItemType Directory -Force -Path $researchRoot | Out-Null
Get-ChildItem -LiteralPath $externalLeaf -Force | ForEach-Object {
    $destinationName = if ($_.Name -eq 'README.md') { 'README.md' } else { $_.Name }
    $destination = Join-Path $researchRoot $destinationName
    if (Test-Path -LiteralPath $destination) {
        throw "External import destination already exists: $destination"
    }
    Move-Item -LiteralPath $_.FullName -Destination $destination
}
$externalRootReadme = Join-Path $ExternalSpriteRoot 'README.md'
if (Test-Path -LiteralPath $externalRootReadme -PathType Leaf) {
    Move-Item -LiteralPath $externalRootReadme -Destination (Join-Path $researchRoot 'EXTERNAL_REPOSITORY_README.md')
}

Write-JsonAtomic -Path (Join-Path $SpriteRoot 'index\path-migrations.json') -Payload $migrationIndex
Write-JsonAtomic -Path (Join-Path $SpriteRoot 'index\sprite-layout.json') -Payload $layoutIndex

foreach ($item in $externalInventory) {
    $target = if ($item.relative_path -eq 'README.md') {
        Join-Path $researchRoot 'EXTERNAL_REPOSITORY_README.md'
    }
    else {
        $prefix = "$($ExternalLeafRelative.Replace('\', '/'))/"
        if (-not $item.relative_path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Unexpected external file location: $($item.relative_path)"
        }
        Join-Path $researchRoot $item.relative_path.Substring($prefix.Length).Replace('/', '\')
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "Imported external file is missing: $target"
    }
    $actual = Get-FileHash -LiteralPath $target -Algorithm SHA256
    if ($actual.Hash -ne $item.sha256 -or (Get-Item -LiteralPath $target).Length -ne $item.length) {
        throw "External file integrity mismatch: $target"
    }
}

if ((Get-ChildItem -LiteralPath $ExternalSpriteRoot -File -Recurse -Force | Measure-Object).Count -ne 0) {
    throw 'External sprite repository still contains files; refusing deletion.'
}
$externalResolved = (Resolve-Path -LiteralPath $ExternalSpriteRoot).Path
if ($externalResolved -ne $ExternalSpriteRoot) {
    throw "External deletion target changed unexpectedly: $externalResolved"
}
Remove-Item -LiteralPath $externalResolved -Recurse -Force

$remainingLegacy = Get-ChildItem -LiteralPath $SpriteRoot -Directory -Force |
    Where-Object { $_.Name -notin $StandardRootDirectories -and $_.Name -notmatch '^\.cmake-' }
if ($remainingLegacy) {
    throw "Unexpected top-level sprite directories remain: $($remainingLegacy.Name -join ', ')"
}
if (Test-Path -LiteralPath $legacyJobsRoot) {
    if ((Get-ChildItem -LiteralPath $legacyJobsRoot -Force | Measure-Object).Count -ne 0) {
        throw 'Legacy sprite/jobs directory is not empty after migration.'
    }
    Remove-Item -LiteralPath $legacyJobsRoot -Force
}

[ordered]@{
    status = 'sprite-layout-migrated'
    workspace_moves = $workspaceRecords.Count
    job_moves = $jobRecords.Count
    external_files_imported = $externalInventory.Count
    external_repository_removed = -not (Test-Path -LiteralPath $ExternalSpriteRoot)
    path_migration_index = 'sprite/index/path-migrations.json'
    layout_index = 'sprite/index/sprite-layout.json'
} | ConvertTo-Json -Depth 4
