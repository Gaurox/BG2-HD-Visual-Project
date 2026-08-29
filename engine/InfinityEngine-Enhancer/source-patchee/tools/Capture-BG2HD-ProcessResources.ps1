[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$GameRoot,

    [Parameter(Mandatory)]
    [string]$OutputPath,

    [string[]]$ProcessNames = @('Baldur', 'BaldurReal'),

    [ValidateRange(250, 5000)]
    [int]$IntervalMilliseconds = 1000,

    [ValidateRange(1, 3600)]
    [int]$WaitTimeoutSeconds = 900,

    [ValidateRange(1, 7200)]
    [int]$MaximumCaptureSeconds = 1800,

    [ValidateRange(1, 120)]
    [int]$StopGraceSeconds = 10
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-OutputPath([string]$Path) {
    $expanded = [Environment]::ExpandEnvironmentVariables($Path)
    if (-not [IO.Path]::IsPathRooted($expanded)) {
        $expanded = Join-Path (Get-Location).Path $expanded
    }
    return [IO.Path]::GetFullPath($expanded)
}

function Write-Json([string]$Path, [object]$Value) {
    [IO.File]::WriteAllText(
        $Path,
        ($Value | ConvertTo-Json -Depth 8),
        [Text.UTF8Encoding]::new($false)
    )
}

function Get-TargetProcesses([string[]]$Names, [string]$RootPrefix) {
    $found = foreach ($name in $Names) {
        Get-Process -Name $name -ErrorAction SilentlyContinue
    }
    return @($found | Where-Object {
        try {
            $_.Path -and $_.Path.StartsWith($RootPrefix, [StringComparison]::OrdinalIgnoreCase)
        }
        catch {
            $false
        }
    } | Sort-Object Id -Unique)
}

function Resolve-CounterCategory([string[]]$Candidates) {
    foreach ($candidate in $Candidates) {
        if ([Diagnostics.PerformanceCounterCategory]::Exists($candidate)) {
            return $candidate
        }
    }
    return $null
}

$counterHandles = [Collections.Generic.List[IDisposable]]::new()
function New-Counter(
    [string]$Category,
    [string[]]$CounterCandidates,
    [string]$Instance = ''
) {
    if (-not $Category) {
        return $null
    }
    $categoryObject = [Diagnostics.PerformanceCounterCategory]::new($Category)
    foreach ($candidate in $CounterCandidates) {
        if (-not $categoryObject.CounterExists($candidate)) {
            continue
        }
        $counter = if ($Instance) {
            [Diagnostics.PerformanceCounter]::new($Category, $candidate, $Instance, $true)
        }
        else {
            [Diagnostics.PerformanceCounter]::new($Category, $candidate, $true)
        }
        $counterHandles.Add($counter)
        return $counter
    }
    return $null
}

function Read-Raw([Diagnostics.PerformanceCounter]$Counter) {
    if ($null -eq $Counter) {
        return [uint64]0
    }
    try {
        return [uint64]$Counter.RawValue
    }
    catch {
        return [uint64]0
    }
}

function Read-Next([Diagnostics.PerformanceCounter]$Counter) {
    if ($null -eq $Counter) {
        return [double]0
    }
    try {
        return [double]$Counter.NextValue()
    }
    catch {
        return [double]0
    }
}

$resolvedGameRoot = (Resolve-Path -LiteralPath $GameRoot -ErrorAction Stop).Path.TrimEnd('\')
$gameRootPrefix = $resolvedGameRoot + '\'
$volumeRoot = [IO.Path]::GetPathRoot($resolvedGameRoot)
if ($volumeRoot -notmatch '^([A-Za-z]):\\$') {
    throw "Le collecteur requiert un jeu installe sur un volume Windows lettre : $volumeRoot"
}
$logicalDiskName = $Matches[1].ToUpperInvariant() + ':'

$resolvedOutput = Resolve-OutputPath $OutputPath
if ([IO.Path]::GetExtension($resolvedOutput) -ne '.csv') {
    throw 'OutputPath doit utiliser une extension .csv.'
}
$outputDirectory = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
if (Test-Path -LiteralPath $resolvedOutput) {
    throw "La capture existe deja : $resolvedOutput"
}

$metadataPath = [IO.Path]::ChangeExtension($resolvedOutput, '.metadata.json')
$statusPath = [IO.Path]::ChangeExtension($resolvedOutput, '.status.json')
$createdAt = [DateTimeOffset]::UtcNow
$metadata = [ordered]@{
    schema_version = 1
    created_at = $createdAt.ToString('o')
    game_root = $resolvedGameRoot
    logical_disk = $logicalDiskName
    process_names = @($ProcessNames)
    interval_milliseconds = $IntervalMilliseconds
    wait_timeout_seconds = $WaitTimeoutSeconds
    maximum_capture_seconds = $MaximumCaptureSeconds
    stop_grace_seconds = $StopGraceSeconds
    caveats = @(
        'GPU counters are WDDM process and adapter diagnostics, not an OpenGL allocation ledger.',
        'Windows documents a legacy GPU Process Memory over-reporting issue; use trends and cross-checks.',
        'Logical-disk counters are volume-wide and can include I/O from other processes.',
        'OS cache and memory counters are system-wide.'
    )
}
Write-Json $metadataPath $metadata

function Write-Status([string]$Phase, [string]$Reason = '', [object]$Extra = $null) {
    $record = [ordered]@{
        schema_version = 1
        phase = $Phase
        reason = $Reason
        updated_at = [DateTimeOffset]::UtcNow.ToString('o')
        output_path = $resolvedOutput
    }
    if ($null -ne $Extra) {
        foreach ($property in $Extra.PSObject.Properties) {
            $record[$property.Name] = $property.Value
        }
    }
    Write-Json $statusPath $record
}

$logicalDiskCategory = Resolve-CounterCategory @('LogicalDisk', 'Disque logique')
$memoryCategory = Resolve-CounterCategory @('Memory', 'Mémoire')
$cacheCategory = Resolve-CounterCategory @('Cache')
$gpuProcessCategory = Resolve-CounterCategory @('GPU Process Memory')
$gpuAdapterCategory = Resolve-CounterCategory @('GPU Adapter Memory')

$volumeReadBytes = New-Counter $logicalDiskCategory @('Disk Read Bytes/sec', 'Lectures disque, octets/s') $logicalDiskName
$volumeReads = New-Counter $logicalDiskCategory @('Disk Reads/sec', 'Lectures disque/s') $logicalDiskName
$volumeWriteBytes = New-Counter $logicalDiskCategory @('Disk Write Bytes/sec', 'Écritures disque, octets/s') $logicalDiskName
$volumeReadPercent = New-Counter $logicalDiskCategory @('% Disk Read Time', 'Pourcentage du temps de lecture du disque') $logicalDiskName

$availableBytes = New-Counter $memoryCategory @('Available Bytes', 'Octets disponibles')
$cacheBytes = New-Counter $memoryCategory @('Cache Bytes', 'Octets du cache')
$systemCacheResidentBytes = New-Counter $memoryCategory @('System Cache Resident Bytes', 'Octets résidants dans le cache système')
$standbyReserveBytes = New-Counter $memoryCategory @('Standby Cache Reserve Bytes', 'Octets de réserve du cache en attente')
$standbyNormalBytes = New-Counter $memoryCategory @('Standby Cache Normal Priority Bytes', 'Octets du cache en attente de priorité normale')
$standbyCoreBytes = New-Counter $memoryCategory @('Standby Cache Core Bytes', 'Octets de base du cache en attente')
$cacheFaults = New-Counter $memoryCategory @('Cache Faults/sec', 'Défauts de cache/s')
$pageReads = New-Counter $memoryCategory @('Page Reads/sec', 'Lectures de pages/s')
$pageFaults = New-Counter $memoryCategory @('Page Faults/sec', 'Défauts de page/s')

$copyReadHits = New-Counter $cacheCategory @('Copy Read Hits %', 'Pourcentage de présence des lectures avec copie')
$mdlReadHits = New-Counter $cacheCategory @('MDL Read Hits %', 'Pourcentage de présence des données MDL')
$pinReadHits = New-Counter $cacheCategory @('Pin Read Hits %', 'Pourcentage de présence des données épinglées')

$gpuCounters = @{}
function Get-GpuCounter([string]$Category, [string]$CounterName, [string]$Instance) {
    $key = "$Category|$CounterName|$Instance"
    if (-not $gpuCounters.ContainsKey($key)) {
        try {
            $counter = [Diagnostics.PerformanceCounter]::new($Category, $CounterName, $Instance, $true)
            $counterHandles.Add($counter)
            $gpuCounters[$key] = $counter
        }
        catch {
            return $null
        }
    }
    return $gpuCounters[$key]
}

function Read-GpuInstances([string]$Category, [string[]]$Instances) {
    [uint64]$dedicated = 0
    [uint64]$shared = 0
    [uint64]$local = 0
    [uint64]$nonLocal = 0
    [uint64]$committed = 0
    foreach ($instance in $Instances) {
        $dedicated += Read-Raw (Get-GpuCounter $Category 'Dedicated Usage' $instance)
        $shared += Read-Raw (Get-GpuCounter $Category 'Shared Usage' $instance)
        if ($Category -eq 'GPU Process Memory') {
            $local += Read-Raw (Get-GpuCounter $Category 'Local Usage' $instance)
            $nonLocal += Read-Raw (Get-GpuCounter $Category 'Non Local Usage' $instance)
        }
        $committed += Read-Raw (Get-GpuCounter $Category 'Total Committed' $instance)
    }
    return [pscustomobject]@{
        available = ($Instances.Count -gt 0)
        dedicated = $dedicated
        shared = $shared
        local = $local
        non_local = $nonLocal
        committed = $committed
    }
}

$header = @(
    'timestampUtc', 'elapsedMilliseconds', 'sampleDurationMilliseconds',
    'processNames', 'processIds', 'workingSetBytes', 'privateBytes',
    'gpuProcessCounterAvailable', 'gpuDedicatedBytes', 'gpuSharedBytes',
    'gpuLocalBytes', 'gpuNonLocalBytes', 'gpuTotalCommittedBytes',
    'gpuAdapterCounterAvailable', 'adapterDedicatedBytes', 'adapterSharedBytes',
    'adapterTotalCommittedBytes',
    'volumeCounterAvailable', 'volumeReadBytesPerSec', 'volumeReadsPerSec',
    'volumeWriteBytesPerSec', 'volumeDiskReadPercent',
    'memoryCounterAvailable', 'osAvailableBytes', 'osCacheBytes',
    'osSystemCacheResidentBytes', 'osStandbyBytes', 'osCacheFaultsPerSec',
    'osPageReadsPerSec', 'osPageFaultsPerSec',
    'cacheCounterAvailable', 'cacheCopyReadHitsPercent',
    'cacheMdlReadHitsPercent', 'cachePinReadHitsPercent'
)

$writer = $null
$invariant = [Globalization.CultureInfo]::InvariantCulture
try {
    Write-Status 'waiting-for-game'
    $waitStopwatch = [Diagnostics.Stopwatch]::StartNew()
    $targets = @()
    while ($waitStopwatch.Elapsed.TotalSeconds -lt $WaitTimeoutSeconds) {
        $targets = @(Get-TargetProcesses $ProcessNames $gameRootPrefix)
        if ($targets.Count -gt 0) {
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if ($targets.Count -eq 0) {
        Write-Status 'timed-out' 'game-process-not-found'
        exit 2
    }

    $writer = [IO.StreamWriter]::new($resolvedOutput, $false, [Text.UTF8Encoding]::new($false))
    $writer.AutoFlush = $true
    $writer.WriteLine(($header -join ','))

    $captureStartedAt = [DateTimeOffset]::UtcNow
    $captureStopwatch = [Diagnostics.Stopwatch]::StartNew()
    $missingSince = $null
    $sampleCount = 0
    Write-Status 'capturing' '' ([pscustomobject]@{ started_at = $captureStartedAt.ToString('o') })

    while ($captureStopwatch.Elapsed.TotalSeconds -lt $MaximumCaptureSeconds) {
        $sampleStopwatch = [Diagnostics.Stopwatch]::StartNew()
        $targets = @(Get-TargetProcesses $ProcessNames $gameRootPrefix)
        if ($targets.Count -eq 0) {
            if ($null -eq $missingSince) {
                $missingSince = [DateTimeOffset]::UtcNow
            }
            elseif (([DateTimeOffset]::UtcNow - $missingSince).TotalSeconds -ge $StopGraceSeconds) {
                break
            }
            Start-Sleep -Milliseconds $IntervalMilliseconds
            continue
        }
        $missingSince = $null

        $pids = @($targets | Select-Object -ExpandProperty Id)
        $pidLookup = @{}
        foreach ($processId in $pids) {
            $pidLookup[[string]$processId] = $true
        }

        $gpuProcessInstances = @()
        if ($gpuProcessCategory) {
            $gpuProcessInstances = @(([Diagnostics.PerformanceCounterCategory]::new($gpuProcessCategory)).GetInstanceNames() | Where-Object {
                $_ -match '^pid_(\d+)_' -and $pidLookup.ContainsKey($Matches[1])
            })
        }
        $gpuAdapterInstances = @()
        if ($gpuAdapterCategory) {
            $gpuAdapterInstances = @(([Diagnostics.PerformanceCounterCategory]::new($gpuAdapterCategory)).GetInstanceNames())
        }

        $gpuProcess = Read-GpuInstances $gpuProcessCategory $gpuProcessInstances
        $gpuAdapter = Read-GpuInstances $gpuAdapterCategory $gpuAdapterInstances
        $standbyBytes = (Read-Raw $standbyReserveBytes) +
                        (Read-Raw $standbyNormalBytes) +
                        (Read-Raw $standbyCoreBytes)

        $volumeReadBytesValue = Read-Next $volumeReadBytes
        $volumeReadsValue = Read-Next $volumeReads
        $volumeWriteBytesValue = Read-Next $volumeWriteBytes
        $volumeReadPercentValue = Read-Next $volumeReadPercent
        $availableBytesValue = Read-Raw $availableBytes
        $cacheBytesValue = Read-Raw $cacheBytes
        $systemCacheResidentBytesValue = Read-Raw $systemCacheResidentBytes
        $cacheFaultsValue = Read-Next $cacheFaults
        $pageReadsValue = Read-Next $pageReads
        $pageFaultsValue = Read-Next $pageFaults
        $copyReadHitsValue = Read-Next $copyReadHits
        $mdlReadHitsValue = Read-Next $mdlReadHits
        $pinReadHitsValue = Read-Next $pinReadHits

        $sampleStopwatch.Stop()
        $sampleDuration = [math]::Round($sampleStopwatch.Elapsed.TotalMilliseconds, 3)
        $values = @(
            [DateTimeOffset]::UtcNow.ToString('o'),
            [math]::Round($captureStopwatch.Elapsed.TotalMilliseconds, 3),
            $sampleDuration,
            (($targets | Select-Object -ExpandProperty ProcessName) -join '+'),
            ($pids -join '+'),
            [uint64](($targets | Measure-Object WorkingSet64 -Sum).Sum),
            [uint64](($targets | Measure-Object PrivateMemorySize64 -Sum).Sum),
            $gpuProcess.available,
            $gpuProcess.dedicated,
            $gpuProcess.shared,
            $gpuProcess.local,
            $gpuProcess.non_local,
            $gpuProcess.committed,
            $gpuAdapter.available,
            $gpuAdapter.dedicated,
            $gpuAdapter.shared,
            $gpuAdapter.committed,
            ($null -ne $volumeReadBytes),
            $volumeReadBytesValue,
            $volumeReadsValue,
            $volumeWriteBytesValue,
            $volumeReadPercentValue,
            ($null -ne $availableBytes),
            $availableBytesValue,
            $cacheBytesValue,
            $systemCacheResidentBytesValue,
            $standbyBytes,
            $cacheFaultsValue,
            $pageReadsValue,
            $pageFaultsValue,
            ($null -ne $copyReadHits),
            $copyReadHitsValue,
            $mdlReadHitsValue,
            $pinReadHitsValue
        )
        $formattedValues = foreach ($value in $values) {
            if ($value -is [IFormattable]) {
                $value.ToString($null, $invariant)
            }
            else {
                [string]$value
            }
        }
        $writer.WriteLine(($formattedValues -join ','))
        ++$sampleCount

        $remaining = $IntervalMilliseconds - $sampleStopwatch.ElapsedMilliseconds
        if ($remaining -gt 0) {
            Start-Sleep -Milliseconds $remaining
        }
    }

    $reason = if ($captureStopwatch.Elapsed.TotalSeconds -ge $MaximumCaptureSeconds) {
        'maximum-duration'
    }
    else {
        'game-process-exited'
    }
    Write-Status 'completed' $reason ([pscustomobject]@{
        started_at = $captureStartedAt.ToString('o')
        completed_at = [DateTimeOffset]::UtcNow.ToString('o')
        samples = $sampleCount
    })
}
catch {
    Write-Status 'failed' $_.Exception.Message
    throw
}
finally {
    if ($null -ne $writer) {
        $writer.Dispose()
    }
    foreach ($counter in $counterHandles) {
        $counter.Dispose()
    }
}
