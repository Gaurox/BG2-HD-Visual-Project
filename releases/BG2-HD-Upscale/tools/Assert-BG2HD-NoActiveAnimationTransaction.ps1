function Test-BG2HDInheritedAnimationAuthorityLock {
    param([string]$Workspace)

    $ownerPid = [string]$env:BG2HD_ANIMATION_AUTHORITY_LOCK_OWNER_PID
    if ($ownerPid -notmatch '^[1-9][0-9]*$') { return $false }
    $lockPath = Join-Path $Workspace '.tmp\workflow-locks\animation-authority.lock'
    if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) { return $false }
    $stream = $null
    try {
        # Byte 0 is the OS advisory-lock range on Windows. Read ownership only
        # from byte 1 so a child can identify its live parent without touching
        # the locked range.
        $stream = [IO.FileStream]::new(
            $lockPath,
            [IO.FileMode]::Open,
            [IO.FileAccess]::Read,
            [IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete
        )
        $null = $stream.Seek(1, [IO.SeekOrigin]::Begin)
        $remaining = [Math]::Max(0, [int]($stream.Length - 1))
        $buffer = [byte[]]::new($remaining)
        $read = if ($remaining -gt 0) { $stream.Read($buffer, 0, $remaining) } else { 0 }
        $ownerText = [Text.Encoding]::ASCII.GetString($buffer, 0, $read)
        if ($ownerText -notmatch ('pid=' + [regex]::Escape($ownerPid) + '(?:\r?\n|$)')) { return $false }
        $null = Get-Process -Id ([int]$ownerPid) -ErrorAction Stop
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
    }
}

function Assert-BG2HDNoActiveAnimationJournal {
    param(
        [string]$Workspace,
        [switch]$AllowPackageMetadataSyncRecovery
    )

    $transactionRoot = Join-Path $Workspace '.tmp\workflow-transactions'
    foreach ($name in @('animation-authority-active.json', 'animation-release-active.json')) {
        $journal = Join-Path $transactionRoot $name
        if (Test-Path -LiteralPath $journal) {
            throw "Transaction animation interrompue active : $journal. Relancer la commande d'origine pour recuperer la transaction avant toute lecture ou reconstruction release."
        }
    }
    $syncMarker = Join-Path $Workspace 'releases\BG2-HD-Upscale\bg2hd\manifests\.package-metadata-sync.partial'
    if (
        -not $AllowPackageMetadataSyncRecovery -and
        (Test-Path -LiteralPath $syncMarker)
    ) {
        throw "Synchronisation des miroirs release interrompue : $syncMarker. Relancer Sync-BG2HD-PackageMetadata.ps1 avant toute lecture ou reconstruction release."
    }
}

function Enter-BG2HDAnimationAuthorityLock {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
        [switch]$AllowPackageMetadataSyncRecovery
    )

    $workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
    if ($null -ne $global:BG2HDAnimationAuthorityLockLease) {
        if ([string]$global:BG2HDAnimationAuthorityLockLease.Workspace -cne $workspace) {
            throw 'Un verrou animation est deja tenu pour un autre workspace dans ce processus PowerShell.'
        }
        Assert-BG2HDNoActiveAnimationJournal -Workspace $workspace -AllowPackageMetadataSyncRecovery:$AllowPackageMetadataSyncRecovery
        return [pscustomobject]@{ Workspace = $workspace; OwnsLock = $false; Process = $null; PreviousOwnerEnvironment = $null }
    }
    if (Test-BG2HDInheritedAnimationAuthorityLock -Workspace $workspace) {
        Assert-BG2HDNoActiveAnimationJournal -Workspace $workspace -AllowPackageMetadataSyncRecovery:$AllowPackageMetadataSyncRecovery
        return [pscustomobject]@{ Workspace = $workspace; OwnsLock = $false; Process = $null; PreviousOwnerEnvironment = $null }
    }

    $holder = Join-Path $workspace 'pipeline\scripts\animation_authority_lock.py'
    if (-not (Test-Path -LiteralPath $holder -PathType Leaf)) {
        throw "Gestionnaire du verrou animation absent : $holder"
    }
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = 'python'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.ArgumentList.Add($holder)
    $startInfo.ArgumentList.Add('--hold')
    $startInfo.ArgumentList.Add($workspace)
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) { throw 'Demarrage du gestionnaire du verrou animation impossible.' }
    $ready = $process.StandardOutput.ReadLine()
    if ($ready -cne 'LOCKED') {
        $detail = $process.StandardError.ReadToEnd().Trim()
        $process.WaitForExit()
        $process.Dispose()
        $message = if ($detail) { $detail } else { 'Acquisition du verrou animation impossible.' }
        throw $message
    }
    $previousOwnerEnvironment = [string]$env:BG2HD_ANIMATION_AUTHORITY_LOCK_OWNER_PID
    $env:BG2HD_ANIMATION_AUTHORITY_LOCK_OWNER_PID = [string]$process.Id
    $lease = [pscustomobject]@{
        Workspace = $workspace
        OwnsLock = $true
        Process = $process
        PreviousOwnerEnvironment = $previousOwnerEnvironment
    }
    $global:BG2HDAnimationAuthorityLockLease = $lease
    try {
        Assert-BG2HDNoActiveAnimationJournal -Workspace $workspace -AllowPackageMetadataSyncRecovery:$AllowPackageMetadataSyncRecovery
    } catch {
        Exit-BG2HDAnimationAuthorityLock -Lease $lease
        throw
    }
    return $lease
}

function Exit-BG2HDAnimationAuthorityLock {
    param([Parameter(Mandatory = $true)][object]$Lease)

    if (-not [bool]$Lease.OwnsLock) { return }
    $process = $Lease.Process
    try {
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(10000)) {
            $process.Kill($true)
            $process.WaitForExit()
        }
        if ($process.ExitCode -ne 0) {
            $detail = $process.StandardError.ReadToEnd().Trim()
            throw "Liberation du verrou animation echouee (code $($process.ExitCode)) : $detail"
        }
    } finally {
        $process.Dispose()
        $global:BG2HDAnimationAuthorityLockLease = $null
        if ([string]::IsNullOrEmpty([string]$Lease.PreviousOwnerEnvironment)) {
            Remove-Item Env:BG2HD_ANIMATION_AUTHORITY_LOCK_OWNER_PID -ErrorAction SilentlyContinue
        } else {
            $env:BG2HD_ANIMATION_AUTHORITY_LOCK_OWNER_PID = [string]$Lease.PreviousOwnerEnvironment
        }
    }
}
