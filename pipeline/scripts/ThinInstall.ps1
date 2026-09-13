. (Join-Path $PSScriptRoot 'WorkspacePaths.ps1')

function Read-JsonFile([string]$Path) {
    try { return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json }
    catch { throw "JSON illisible : $Path : $($_.Exception.Message)" }
}

function Get-FileSha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Resolve-WorkspaceInput([string]$Value, [switch]$RequireExisting) {
    if ([string]::IsNullOrWhiteSpace($Value)) { throw 'Chemin vide.' }
    if ($Value.StartsWith('config://', [StringComparison]::OrdinalIgnoreCase)) {
        $result = Resolve-BG2WorkspacePath -Key $Value.Substring(9) -RequireExisting:$RequireExisting
    } elseif ([IO.Path]::IsPathRooted($Value)) {
        $result = [IO.Path]::GetFullPath($Value)
    } else {
        $normalized = $Value.Replace('\', '/').Trim('/')
        $result = [IO.Path]::GetFullPath((Join-Path $script:BG2WorkspaceRoot $normalized))
        if (-not (Test-Path -LiteralPath $result)) {
            $migrationPath = Join-Path $script:BG2WorkspaceRoot 'sprite\index\path-migrations.json'
            if (Test-Path -LiteralPath $migrationPath -PathType Leaf) {
                $migrations = @((Read-JsonFile $migrationPath).migrations | Sort-Object {
                        ([string]$_.PSObject.Properties['from'].Value).Length
                    } -Descending)
                foreach ($entry in $migrations) {
                    $old = ([string]$entry.PSObject.Properties['from'].Value).Replace('\', '/').Trim('/')
                    if ($normalized -eq $old -or $normalized.StartsWith("$old/", [StringComparison]::Ordinal)) {
                        $suffix = $normalized.Substring($old.Length).TrimStart('/')
                        $new = ([string]$entry.to).Replace('\', '/').Trim('/')
                        $result = [IO.Path]::GetFullPath((Join-Path $script:BG2WorkspaceRoot "$new/$suffix"))
                        break
                    }
                }
            }
        }
    }
    if ($RequireExisting -and -not (Test-Path -LiteralPath $result)) {
        throw "Chemin absent : $result"
    }
    return $result
}

function Resolve-ChildPath([string]$Root, [string]$Relative, [switch]$RequireExisting) {
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)') {
        throw "Chemin relatif dangereux : $Relative"
    }
    $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $result = [IO.Path]::GetFullPath((Join-Path $rootFull $Relative))
    if (-not $result.StartsWith("$rootFull$([IO.Path]::DirectorySeparatorChar)", [StringComparison]::OrdinalIgnoreCase)) {
        throw "Chemin hors racine : $Relative"
    }
    if ($RequireExisting -and -not (Test-Path -LiteralPath $result)) {
        throw "Fichier absent : $result"
    }
    return $result
}

function Assert-GameClosed {
    if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count) {
        throw 'Fermez le jeu et InfinityLoader avant toute installation ou restauration.'
    }
}

function Copy-FileAtomic([string]$Source, [string]$Target) {
    $parent = Split-Path -Parent $Target
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = Join-Path $parent ('.' + [IO.Path]::GetFileName($Target) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        Copy-Item -LiteralPath $Source -Destination $temporary
        Move-Item -LiteralPath $temporary -Destination $Target -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Write-TextAtomic([string]$Target, [string]$Text) {
    $parent = Split-Path -Parent $Target
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = Join-Path $parent ('.' + [IO.Path]::GetFileName($Target) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllText($temporary, $Text, [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Target -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Write-JsonAtomic([string]$Target, $Value) {
    Write-TextAtomic $Target (($Value | ConvertTo-Json -Depth 12) + [char]10)
}

function Set-IniValue([string]$Text, [string]$Section, [string]$Key, [string]$Value) {
    $crlf = [string][char]13 + [char]10
    $newline = if ($Text.Contains($crlf)) { $crlf } else { [string][char]10 }
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in @($Text -split '\r?\n')) { $lines.Add($line) }
    $sectionIndex = -1
    $nextSection = $lines.Count
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[([^]]+)\]\s*$') {
            if ($sectionIndex -ge 0) { $nextSection = $index; break }
            if ([string]::Equals($Matches[1], $Section, [StringComparison]::OrdinalIgnoreCase)) {
                $sectionIndex = $index
            }
        }
    }
    if ($sectionIndex -lt 0) {
        if ($lines.Count -and $lines[$lines.Count - 1] -ne '') { $lines.Add('') }
        $lines.Add("[$Section]")
        $lines.Add("$Key = $Value")
    } else {
        for ($index = $sectionIndex + 1; $index -lt $nextSection; $index++) {
            if ($lines[$index] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) {
                $lines[$index] = "$Key = $Value"
                return ($lines -join $newline)
            }
        }
        $lines.Insert($nextSection, "$Key = $Value")
    }
    return ($lines -join $newline)
}
