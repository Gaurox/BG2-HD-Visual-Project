[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile,
    [switch]$VerifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path.TrimEnd('\')
$script:SpritePathMigrations = $null

function Get-RequiredProperty($Object, [string]$Name, [string]$Label) {
    if ($null -eq $Object) { throw "$Label absent." }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { throw "$Label.$Name absent." }
    return $property.Value
}

function Assert-ExactPropertyNames($Object, [string[]]$Expected, [string]$Label) {
    if ($null -eq $Object) { throw "$Label absent." }
    $actualNames = @($Object.PSObject.Properties | ForEach-Object { $_.Name } | Sort-Object -CaseSensitive)
    $expectedNames = @($Expected | Sort-Object -CaseSensitive)
    if (($actualNames -join "`0") -cne ($expectedNames -join "`0")) {
        throw "$Label contient des champs absents ou inattendus."
    }
}

function Test-PathInsideRoot([string]$Path, [string]$Root) {
    $full = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    return [string]::Equals($full, $rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $full.StartsWith($rootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-NoReparseComponents([string]$Root, [string]$Path, [string]$Label) {
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $full = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    if (-not (Test-PathInsideRoot $full $rootFull)) { throw "$Label sort de sa racine de sécurité." }
    if (-not [System.IO.Directory]::Exists($rootFull)) {
        throw "$Label a une racine de sécurité absente : $rootFull"
    }
    $rootAttributes = [System.IO.File]::GetAttributes($rootFull)
    if (($rootAttributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label utilise une racine ReparsePoint interdite : $rootFull"
    }
    if ([string]::Equals($full, $rootFull, [System.StringComparison]::OrdinalIgnoreCase)) { return }
    $relative = $full.Substring($rootFull.Length + 1)
    $parts = @($relative.Split([char]'\') | Where-Object { $_ -ne '' })
    $current = $rootFull
    for ($index = 0; $index -lt $parts.Count; $index++) {
        $current = Join-Path $current $parts[$index]
        $fileExists = [System.IO.File]::Exists($current)
        $directoryExists = [System.IO.Directory]::Exists($current)
        if (-not $fileExists -and -not $directoryExists) { break }
        $attributes = [System.IO.File]::GetAttributes($current)
        if (($attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "$Label traverse un ReparsePoint interdit : $current"
        }
        if ($fileExists -and $index -lt $parts.Count - 1) {
            throw "$Label traverse un fichier intermédiaire : $current"
        }
    }
}

function Assert-SafeKnownPath([string]$Path, [string]$Label) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (Test-PathInsideRoot $full $script:WorkspaceRoot) {
        Assert-NoReparseComponents $script:WorkspaceRoot $full $Label
    }
    if ($null -ne (Get-Variable -Name ActiveGameRoot -Scope Script -ErrorAction SilentlyContinue) -and
        -not [string]::IsNullOrWhiteSpace([string]$script:ActiveGameRoot) -and
        (Test-PathInsideRoot $full $script:ActiveGameRoot)) {
        Assert-NoReparseComponents $script:ActiveGameRoot $full $Label
    }
}

function Assert-OrdinalEqual([string]$Actual, [string]$Expected, [string]$Label) {
    if (-not [string]::Equals($Actual, $Expected, [System.StringComparison]::Ordinal)) {
        throw "$Label incompatible : '$Actual', attendu '$Expected'."
    }
}

function Assert-HashText([string]$Value, [string]$Label) {
    if ($Value -notmatch '^[0-9A-Fa-f]{64}$') { throw "$Label n'est pas un SHA-256 valide." }
}

function Assert-Boolean($Value, [string]$Label) {
    if ($Value -isnot [bool]) { throw "$Label doit être un booléen JSON." }
}

function Get-SpritePathMigrations {
    if ($null -ne $script:SpritePathMigrations) { return $script:SpritePathMigrations }
    $indexPath = Join-Path $script:WorkspaceRoot 'sprite\index\path-migrations.json'
    if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
        $script:SpritePathMigrations = @()
        return $script:SpritePathMigrations
    }
    try {
        $index = Get-Content -LiteralPath $indexPath -Raw -Encoding utf8 | ConvertFrom-Json
    }
    catch {
        throw "Index de migration sprite illisible : $($_.Exception.Message)"
    }
    if ($index.schema -ne 'bg2-upscale-sprite-path-migrations-v1' -or $null -eq $index.migrations) {
        throw 'Index de migration sprite invalide.'
    }
    $seen = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    $rules = @()
    foreach ($entry in @($index.migrations)) {
        $from = ([string]$entry.from).Replace('\', '/').Trim('/')
        $to = ([string]$entry.to).Replace('\', '/').Trim('/')
        if (-not $from.StartsWith('sprite/', [System.StringComparison]::OrdinalIgnoreCase) -or
            -not $to.StartsWith('sprite/', [System.StringComparison]::OrdinalIgnoreCase) -or
            $from -eq $to -or -not $seen.Add($from)) {
            throw 'Règle de migration sprite invalide ou dupliquée.'
        }
        $rules += [pscustomobject]@{ from = $from; to = $to }
    }
    $script:SpritePathMigrations = @($rules | Sort-Object { $_.from.Length } -Descending)
    return $script:SpritePathMigrations
}

function Resolve-WorkspaceRelativePath([string]$Value) {
    $normalized = $Value.Replace('\', '/').Trim('/')
    $candidate = [System.IO.Path]::GetFullPath((Join-Path $script:WorkspaceRoot ($normalized.Replace('/', '\'))))
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    foreach ($rule in Get-SpritePathMigrations) {
        if ($normalized -eq $rule.from -or $normalized.StartsWith($rule.from + '/', [System.StringComparison]::OrdinalIgnoreCase)) {
            $suffix = $normalized.Substring($rule.from.Length).TrimStart('/')
            $redirected = $rule.to
            if (-not [string]::IsNullOrWhiteSpace($suffix)) { $redirected = "$redirected/$suffix" }
            return [System.IO.Path]::GetFullPath((Join-Path $script:WorkspaceRoot ($redirected.Replace('/', '\'))))
        }
    }
    return $candidate
}

function Resolve-ProjectPath([string]$Value, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Value)) { throw "$Label est vide." }
    $full = if ([System.IO.Path]::IsPathRooted($Value)) {
        [System.IO.Path]::GetFullPath($Value)
    } else {
        Resolve-WorkspaceRelativePath $Value
    }
    if ([System.IO.Path]::IsPathRooted($Value) -and
        -not (Test-Path -LiteralPath $full) -and
        $full.StartsWith($script:WorkspaceRoot + '\',
            [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $full.Substring($script:WorkspaceRoot.Length + 1)
        $full = Resolve-WorkspaceRelativePath $relative
    }
    if (-not ($full.StartsWith($script:WorkspaceRoot + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
            [string]::Equals($full, $script:WorkspaceRoot, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "$Label sort du workspace : $full"
    }
    Assert-NoReparseComponents $script:WorkspaceRoot $full $Label
    return $full
}

function Resolve-AnyPath([string]$Value, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Value)) { throw "$Label est vide." }
    if ([System.IO.Path]::IsPathRooted($Value)) { return [System.IO.Path]::GetFullPath($Value) }
    return Resolve-WorkspaceRelativePath $Value
}

function Resolve-ChildPath([string]$Root, [string]$Relative, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or [System.IO.Path]::IsPathRooted($Relative)) {
        throw "$Label doit être un chemin relatif."
    }
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $full = [System.IO.Path]::GetFullPath((Join-Path $rootFull ($Relative.Replace('/', '\'))))
    if (-not $full.StartsWith($rootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label sort de sa racine déclarée : $Relative"
    }
    Assert-NoReparseComponents $rootFull $full $Label
    return $full
}

function Get-ProjectRelativePath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($script:WorkspaceRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Chemin hors workspace : $full"
    }
    return $full.Substring($script:WorkspaceRoot.Length + 1).Replace('\', '/')
}

function Get-Sha256([string]$Path) {
    Assert-SafeKnownPath $Path 'Lecture SHA-256'
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Fichier absent : $Path" }
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '')
        } finally { $sha.Dispose() }
    } finally { $stream.Dispose() }
}

function ConvertTo-CanonicalJsonString([string]$Value) {
    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    foreach ($character in $Value.ToCharArray()) {
        $code = [int][char]$character
        switch ($code) {
            8 { [void]$builder.Append('\b'); continue }
            9 { [void]$builder.Append('\t'); continue }
            10 { [void]$builder.Append('\n'); continue }
            12 { [void]$builder.Append('\f'); continue }
            13 { [void]$builder.Append('\r'); continue }
            34 { [void]$builder.Append('\"'); continue }
            92 { [void]$builder.Append('\\'); continue }
        }
        if ($code -lt 32) { [void]$builder.Append(('\u{0:x4}' -f $code)) }
        else { [void]$builder.Append($character) }
    }
    [void]$builder.Append('"')
    return $builder.ToString()
}

function ConvertTo-CanonicalJson($Value) {
    if ($null -eq $Value) { return 'null' }
    if ($Value -is [bool]) { if ($Value) { return 'true' } else { return 'false' } }
    if ($Value -is [string] -or $Value -is [char]) {
        return ConvertTo-CanonicalJsonString ([string]$Value)
    }
    if ($Value -is [byte] -or $Value -is [sbyte] -or $Value -is [int16] -or
        $Value -is [uint16] -or $Value -is [int32] -or $Value -is [uint32] -or
        $Value -is [int64] -or $Value -is [uint64]) {
        return [System.Convert]::ToString($Value, [System.Globalization.CultureInfo]::InvariantCulture)
    }
    $properties = @()
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            if ($key -isnot [string]) { throw 'Clé JSON canonique non textuelle.' }
            $properties += [pscustomobject]@{ name = [string]$key; value = $Value[$key] }
        }
    } elseif ($Value -is [pscustomobject]) {
        foreach ($property in $Value.PSObject.Properties) {
            $properties += [pscustomobject]@{ name = $property.Name; value = $property.Value }
        }
    } elseif ($Value -is [System.Collections.IEnumerable]) {
        $items = @()
        foreach ($item in $Value) { $items += ,(ConvertTo-CanonicalJson $item) }
        return '[' + ($items -join ',') + ']'
    } else {
        throw "Type JSON canonique non supporté : $($Value.GetType().FullName)"
    }
    $members = @()
    foreach ($property in @($properties | Sort-Object -Property name -CaseSensitive)) {
        $members += (ConvertTo-CanonicalJsonString $property.name) + ':' +
            (ConvertTo-CanonicalJson $property.value)
    }
    return '{' + ($members -join ',') + '}'
}

function Get-CanonicalJsonSha256($Value) {
    $canonical = ConvertTo-CanonicalJson $Value
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString(
            $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($canonical)))).Replace('-', '')
    } finally { $sha.Dispose() }
}

function Assert-ExpectedHash([string]$Path, [string]$Expected, [string]$Label) {
    Assert-HashText $Expected "$Label.sha256"
    $actual = Get-Sha256 $Path
    if (-not [string]::Equals($actual, $Expected, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label altéré : SHA-256 $actual, attendu $Expected."
    }
}

function Write-JsonAtomic($Value, [string]$Path, [int]$Depth = 16) {
    Assert-SafeKnownPath $Path 'Écriture JSON atomique'
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Path))
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Dossier d'état absent : $parent"
    }
    $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Path) +
        '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $replaceBackup = $temporary + '.replace-backup'
    try {
        $json = ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine
        [System.IO.File]::WriteAllText($temporary, $json, (New-Object System.Text.UTF8Encoding($false)))
        Assert-SafeKnownPath $Path 'Publication JSON atomique'
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            [System.IO.File]::Replace($temporary, $Path, $replaceBackup, $true)
        } else {
            [System.IO.File]::Move($temporary, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) { Remove-Item -LiteralPath $temporary -Force }
        if (Test-Path -LiteralPath $replaceBackup -PathType Leaf) { Remove-Item -LiteralPath $replaceBackup -Force }
    }
}

function Write-TextAtomic([string]$Text, [string]$Path) {
    Assert-SafeKnownPath $Path 'Écriture texte atomique'
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Path))
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Dossier de destination absent : $parent"
    }
    $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Path) +
        '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $replaceBackup = $temporary + '.replace-backup'
    try {
        [System.IO.File]::WriteAllText($temporary, $Text, (New-Object System.Text.UTF8Encoding($false)))
        Assert-SafeKnownPath $Path 'Publication texte atomique'
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            [System.IO.File]::Replace($temporary, $Path, $replaceBackup, $true)
        } else {
            [System.IO.File]::Move($temporary, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) { Remove-Item -LiteralPath $temporary -Force }
        if (Test-Path -LiteralPath $replaceBackup -PathType Leaf) { Remove-Item -LiteralPath $replaceBackup -Force }
    }
}

function Copy-FileAtomic([string]$Source, [string]$Destination, [string]$ExpectedSha256) {
    Assert-SafeKnownPath $Source 'Source de copie atomique'
    Assert-SafeKnownPath $Destination 'Destination de copie atomique'
    Assert-ExpectedHash $Source $ExpectedSha256 'Source de copie atomique'
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Destination))
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Destination) +
        '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $replaceBackup = $temporary + '.replace-backup'
    try {
        Copy-Item -LiteralPath $Source -Destination $temporary
        Assert-ExpectedHash $temporary $ExpectedSha256 'Copie temporaire'
        Assert-SafeKnownPath $Destination 'Publication de copie atomique'
        if (Test-Path -LiteralPath $Destination -PathType Leaf) {
            [System.IO.File]::Replace($temporary, $Destination, $replaceBackup, $true)
        } else {
            [System.IO.File]::Move($temporary, $Destination)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) { Remove-Item -LiteralPath $temporary -Force }
        if (Test-Path -LiteralPath $replaceBackup -PathType Leaf) { Remove-Item -LiteralPath $replaceBackup -Force }
    }
    Assert-ExpectedHash $Destination $ExpectedSha256 'Destination de copie atomique'
}

function Publish-ImmutableFile([string]$Source, [string]$Destination, [string]$ExpectedSha256) {
    Assert-SafeKnownPath $Source 'Source immutable'
    Assert-SafeKnownPath $Destination 'Destination immutable'
    Assert-ExpectedHash $Source $ExpectedSha256 'Source immutable'
    if (Test-Path -LiteralPath $Destination) {
        throw "Une cible immutable est apparue après le preflight : $Destination"
    }
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Destination))
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Destination) +
        '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        Copy-Item -LiteralPath $Source -Destination $temporary
        Assert-ExpectedHash $temporary $ExpectedSha256 'Copie immutable temporaire'
        Assert-SafeKnownPath $Destination 'Publication immutable'
        # File.Move sans overwrite rend la publication fail-closed même si un
        # fichier apparaît entre le Test-Path et ce point.
        [System.IO.File]::Move($temporary, $Destination)
    } finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) { Remove-Item -LiteralPath $temporary -Force }
    }
    Assert-ExpectedHash $Destination $ExpectedSha256 'Destination immutable'
}

function Enter-GameMutationMutex([string]$GameRoot) {
    $normalized = [System.IO.Path]::GetFullPath($GameRoot).TrimEnd('\').ToUpperInvariant()
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $key = ([System.BitConverter]::ToString(
            $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($normalized)))).Replace('-', '')
    } finally { $sha.Dispose() }
    $mutex = New-Object System.Threading.Mutex($false, "Global\BG2UpscaleCreatureSpriteMutation_$key")
    $owned = $false
    try { $owned = $mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $owned = $true }
    if (-not $owned) {
        $mutex.Dispose()
        throw "Une installation ou restauration sprite modifie déjà ce GameRoot : $GameRoot"
    }
    return $mutex
}

function Exit-GameMutationMutex($Mutex) {
    if ($null -eq $Mutex) { return }
    try { $Mutex.ReleaseMutex() } finally { $Mutex.Dispose() }
}

function Get-Crc32([string]$Path) {
    Assert-SafeKnownPath $Path 'Lecture CRC32'
    if ($null -eq ('Bg2CreatureSpriteCatalogCrc32' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.IO;
public static class Bg2CreatureSpriteCatalogCrc32 {
    private static readonly uint[] Table = BuildTable();
    private static uint[] BuildTable() {
        uint[] table = new uint[256];
        for (uint i = 0; i < table.Length; ++i) {
            uint value = i;
            for (int bit = 0; bit < 8; ++bit)
                value = (value & 1U) != 0U ? (value >> 1) ^ 0xEDB88320U : value >> 1;
            table[i] = value;
        }
        return table;
    }
    public static uint Compute(string path) {
        uint crc = UInt32.MaxValue;
        byte[] buffer = new byte[1024 * 1024];
        using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read,
            FileShare.Read, buffer.Length, FileOptions.SequentialScan)) {
            int read;
            while ((read = stream.Read(buffer, 0, buffer.Length)) > 0)
                for (int i = 0; i < read; ++i)
                    crc = (crc >> 8) ^ Table[(crc ^ buffer[i]) & 0xFFU];
        }
        return crc ^ UInt32.MaxValue;
    }
}
'@
    }
    return [Bg2CreatureSpriteCatalogCrc32]::Compute($Path)
}

function Read-ExactBytes($Stream, [int]$Count, [string]$Label) {
    [byte[]]$buffer = New-Object byte[] $Count
    $offset = 0
    while ($offset -lt $Count) {
        $read = $Stream.Read($buffer, $offset, $Count - $offset)
        if ($read -eq 0) { throw "$Label tronqué." }
        $offset += $read
    }
    return ,$buffer
}

function Get-MaxRegistryBytes([int]$Scale) {
    if ($Scale -eq 2) { return [uint64](128MB) }
    if ($Scale -eq 4) { return [uint64](512MB) }
    throw "Échelle sans plafond de registre : $Scale"
}

function Convert-AnimationId($Value, [string]$Label) {
    if ($Value -is [string]) {
        if ([string]$Value -notmatch '^0x[0-9A-Fa-f]{4}$') { throw "$Label invalide." }
        $number = [Convert]::ToUInt32(([string]$Value).Substring(2), 16)
    } else {
        try { $number = [uint32]$Value } catch { throw "$Label invalide." }
    }
    if ($number -lt 1 -or $number -gt 65534) { throw "$Label hors plage 1..65534." }
    return [uint32]$number
}

function Format-AnimationId([uint32]$Value) { return ('0x{0:X4}' -f $Value) }

function Convert-Owner($Value, [string]$Label) {
    if ($Value -is [string]) {
        if ([string]::Equals([string]$Value, 'Character', [System.StringComparison]::Ordinal)) { return 1 }
        if ([string]::Equals([string]$Value, 'MonsterIcewind', [System.StringComparison]::Ordinal)) { return 2 }
        throw "$Label doit être Character ou MonsterIcewind."
    }
    $owner = [int]$Value
    if ($owner -notin @(1, 2)) { throw "$Label doit valoir 1 ou 2." }
    return $owner
}

function Get-OwnerName([int]$Owner) {
    if ($Owner -eq 1) { return 'Character' }
    if ($Owner -eq 2) { return 'MonsterIcewind' }
    throw "Owner binaire invalide : $Owner"
}

function Get-OwnerRuntimeProfile([int]$Owner) {
    if ($Owner -eq 1) { return 'character-bg2ee-2.7.3.0' }
    if ($Owner -eq 2) { return 'monster-icewind-bg2ee-2.7.3.0' }
    throw "Owner binaire invalide : $Owner"
}

function Assert-UpscaleContract($Contract, [int]$Scale, [string]$Label) {
    $algorithm = if ($Scale -eq 2) { 'XBR/xbr2X' } else { 'XBR/xbr4X' }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $Contract 'algorithm' $Label)) $algorithm "$Label.algorithm"
    if ([int](Get-RequiredProperty $Contract 'scale' $Label) -ne $Scale -or
        [int](Get-RequiredProperty $Contract 'passes' $Label) -ne 1) {
        throw "$Label scale/passes incompatible."
    }
    $aa = Get-RequiredProperty $Contract 'antialias' $Label
    $blend = Get-RequiredProperty $Contract 'xbr_blend' $Label
    Assert-Boolean $aa "$Label.antialias"
    Assert-Boolean $blend "$Label.xbr_blend"
    if ($aa -or $blend) { throw "$Label doit rester NEAREST sans AA ni blend." }
    if ($null -ne $Contract.PSObject.Properties['sampling']) {
        Assert-OrdinalEqual ([string]$Contract.sampling) 'NEAREST' "$Label.sampling"
    }
}

function Set-IniKey([string]$Text, [string]$Section, [string]$Key, [string]$Value) {
    $newline = if ($Text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [regex]::Split($Text, '\r?\n')) { [void]$lines.Add($line) }
    $ranges = @(); $start = -1; $matchesSection = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^\s*\[([^\]]+)\]\s*$') {
            if ($matchesSection) { $ranges += [pscustomobject]@{ Start = $start; End = $i } }
            $start = $i
            $matchesSection = [string]::Equals($Matches[1].Trim(), $Section,
                [System.StringComparison]::OrdinalIgnoreCase)
        }
    }
    if ($matchesSection) { $ranges += [pscustomobject]@{ Start = $start; End = $lines.Count } }
    if ($ranges.Count -eq 0) {
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') { [void]$lines.Add('') }
        [void]$lines.Add("[$Section]"); [void]$lines.Add("$Key = $Value")
        return [string]::Join($newline, $lines)
    }
    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    $indexes = @()
    foreach ($range in $ranges) {
        for ($i = [int]$range.Start + 1; $i -lt [int]$range.End; $i++) {
            if ($lines[$i] -match $pattern) { $indexes += $i }
        }
    }
    if ($indexes.Count -gt 1) { throw "Clé INI dupliquée dans [$Section] : $Key" }
    if ($indexes.Count -eq 1) { $lines[[int]$indexes[0]] = "$Key = $Value" }
    else { $lines.Insert([int]$ranges[0].End, "$Key = $Value") }
    return [string]::Join($newline, $lines)
}

function Get-IniKey([string]$Text, [string]$Section, [string]$Key, [switch]$AllowMissing) {
    $current = ''; $values = @()
    foreach ($line in [regex]::Split($Text, '\r?\n')) {
        if ($line -match '^\s*\[([^\]]+)\]\s*$') { $current = $Matches[1].Trim(); continue }
        if ([string]::Equals($current, $Section, [System.StringComparison]::OrdinalIgnoreCase) -and
            $line -match ('^\s*' + [regex]::Escape($Key) + '\s*=\s*(.*?)\s*$')) {
            $values += [string]$Matches[1]
        }
    }
    if ($values.Count -eq 0 -and $AllowMissing) { return $null }
    if ($values.Count -ne 1) { throw "Clé INI absente ou dupliquée dans [$Section] : $Key" }
    return $values[0]
}

function Get-EngineSourceContractSha256([string]$SourceRoot) {
    $relativeFiles = @(
        'CMakeLists.txt',
        'src/iee/hooks.cpp',
        'src/iee/native_occlusion_bridge.cpp',
        'src/iee/native_occlusion_bridge.h',
        'src/iee/dll_main.cpp',
        'src/iee/bridge_transition.cpp',
        'src/iee/bridge_transition.h',
        'src/iee/creature_sprite_x2.cpp',
        'src/iee/creature_sprite_x2.h',
        'src/iee/core/config.cpp',
        'src/iee/core/config.h',
        'src/iee/core/native_occlusion_probe.cpp',
        'src/iee/core/native_occlusion_probe.h',
        'src/iee/game/build_manifest.cpp',
        'src/iee/game/build_manifest.h',
        'tests/iee_tests.cpp',
        'tests/bridge_worker_lifecycle_tests.cpp'
    )
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        foreach ($relative in $relativeFiles) {
            $path = Join-Path $SourceRoot ($relative.Replace('/', '\'))
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "Contrat source runtime incomplet : $relative"
            }
            [byte[]]$prefix = [System.Text.Encoding]::UTF8.GetBytes($relative + [char]0)
            [void]$sha.TransformBlock($prefix, 0, $prefix.Length, $prefix, 0)
            $stream = [System.IO.File]::OpenRead($path)
            try {
                [byte[]]$buffer = New-Object byte[] (1024 * 1024)
                while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                    [void]$sha.TransformBlock($buffer, 0, $read, $buffer, 0)
                }
            } finally { $stream.Dispose() }
        }
        [void]$sha.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($sha.Hash)).Replace('-', '')
    } finally { $sha.Dispose() }
}

function Initialize-XpressHuffDecoder {
    if ('BG2Upscale.CatalogXpressHuffDecoder' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

namespace BG2Upscale {
    public sealed class CatalogXpressHuffDecoder : IDisposable {
        private const uint AlgorithmXpressHuff = 4;
        private IntPtr handle;

        [DllImport("cabinet.dll", SetLastError = true)]
        private static extern bool CreateDecompressor(
            uint algorithm, IntPtr allocationRoutines, out IntPtr decompressorHandle);

        [DllImport("cabinet.dll", SetLastError = true)]
        private static extern bool Decompress(
            IntPtr decompressorHandle,
            byte[] compressedData,
            UIntPtr compressedDataSize,
            byte[] uncompressedBuffer,
            UIntPtr uncompressedBufferSize,
            out UIntPtr uncompressedDataSize);

        [DllImport("cabinet.dll", SetLastError = true)]
        private static extern bool CloseDecompressor(IntPtr decompressorHandle);

        public CatalogXpressHuffDecoder() {
            if (!CreateDecompressor(AlgorithmXpressHuff, IntPtr.Zero, out handle)) {
                throw new Win32Exception(Marshal.GetLastWin32Error(),
                    "CreateDecompressor(XPRESS_HUFF) failed");
            }
        }

        public byte[] Decode(byte[] input, int logicalBytes) {
            if (handle == IntPtr.Zero || input == null || input.Length == 0 ||
                    logicalBytes <= 0 || logicalBytes > 134217728) {
                throw new ArgumentException("Invalid bounded XPRESS_HUFF decode request");
            }
            byte[] output = new byte[logicalBytes];
            UIntPtr written;
            if (!Decompress(handle, input, (UIntPtr)(ulong)input.Length,
                    output, (UIntPtr)(ulong)output.Length, out written)) {
                throw new Win32Exception(Marshal.GetLastWin32Error(),
                    "Decompress(XPRESS_HUFF) failed");
            }
            if (written.ToUInt64() != (ulong)logicalBytes) {
                throw new InvalidOperationException(
                    "XPRESS_HUFF decompressed size differs from the logical frame size");
            }
            return output;
        }

        public static bool RepresentativesCover(byte[] frameHeader, byte[] indices) {
            if (frameHeader == null || frameHeader.Length != 528 || indices == null) {
                return false;
            }
            for (int index = 0; index < indices.Length; index++) {
                int representative = 16 + indices[index] * 2;
                if (frameHeader[representative] == 0xFF &&
                        frameHeader[representative + 1] == 0xFF) {
                    return false;
                }
            }
            return true;
        }

        public void Dispose() {
            IntPtr current = handle;
            handle = IntPtr.Zero;
            if (current != IntPtr.Zero && !CloseDecompressor(current)) {
                throw new Win32Exception(Marshal.GetLastWin32Error(),
                    "CloseDecompressor failed");
            }
            GC.SuppressFinalize(this);
        }

        ~CatalogXpressHuffDecoder() {
            if (handle != IntPtr.Zero) {
                CloseDecompressor(handle);
                handle = IntPtr.Zero;
            }
        }
    }
}
'@
}

function Read-CatalogShard([string]$Path) {
    Assert-SafeKnownPath $Path 'Lecture shard catalogue'
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        if ($stream.Length -lt 24 -or [uint64]$stream.Length -gt [uint64](512MB)) {
            throw "Registre hors borne absolue : $($stream.Length) octets."
        }
        [byte[]]$header = Read-ExactBytes $stream 24 'En-tête shard catalogue'
        $magic = [System.Text.Encoding]::ASCII.GetString($header, 0, 7)
        if ($header[7] -ne 0 -or $magic -ne 'IEECSXN') { throw 'Magic shard catalogue invalide.' }
        $version = [System.BitConverter]::ToUInt32($header, 8)
        $scale = [System.BitConverter]::ToUInt32($header, 12)
        $resourceCount = [System.BitConverter]::ToUInt32($header, 16)
        $animationId = [System.BitConverter]::ToUInt32($header, 20)
        if ($version -notin @(3, 5) -or $scale -notin @(2, 4) -or
            $resourceCount -lt 1 -or $resourceCount -gt 128 -or $animationId -ne 0xFFFF) {
            throw 'En-tête shard catalogue invalide.'
        }
        if ([uint64]$stream.Length -gt (Get-MaxRegistryBytes ([int]$scale))) {
            throw "Registre x$scale trop volumineux."
        }
        $resourceNames = @()
        $resourceRecords = @()
        $resourceSet = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::OrdinalIgnoreCase)
        [uint64]$frameCountTotal = 0
        [uint64]$indexBytesTotal = 0
        [uint64]$storedIndexBytesTotal = 0
        [uint64]$compressedFrameCount = 0
        [uint64]$rawFrameCount = 0
        for ($resourceIndex = 0; $resourceIndex -lt $resourceCount; $resourceIndex++) {
            [byte[]]$resourceHeader = Read-ExactBytes $stream 48 "Ressource registre $resourceIndex"
            $nameEnd = [System.Array]::IndexOf($resourceHeader, [byte]0, 0, 8)
            if ($nameEnd -eq -1) { $nameEnd = 8 }
            if ($nameEnd -lt 1) { throw 'Resref vide dans un registre.' }
            $name = [System.Text.Encoding]::ASCII.GetString($resourceHeader, 0, $nameEnd)
            if ($name -notmatch '^[A-Z0-9_]{1,8}$') { throw "Resref registre invalide : $name" }
            for ($i = $nameEnd; $i -lt 8; $i++) {
                if ($resourceHeader[$i] -ne 0) { throw "Padding resref invalide : $name" }
            }
            if (-not $resourceSet.Add($name)) { throw "Resref dupliqué dans un registre : $name" }
            $resourceNames += $name
            [byte[]]$sourceSha256 = New-Object byte[] 32
            [System.Array]::Copy($resourceHeader, 8, $sourceSha256, 0, 32)
            if (@($sourceSha256 | Where-Object { $_ -ne 0 }).Count -eq 0) {
                throw "SHA source nul dans le registre : $name"
            }
            $frameCount = [System.BitConverter]::ToUInt32($resourceHeader, 40)
            $cycleCount = [System.BitConverter]::ToUInt32($resourceHeader, 44)
            if ($frameCount -lt 1 -or $frameCount -gt 4096 -or
                $cycleCount -lt 1 -or $cycleCount -gt 256) {
                throw "Compteurs invalides pour $name."
            }
            $frameCountTotal += [uint64]$frameCount
            [uint64]$recordLogicalBytes = 48
            for ($frameIndex = 0; $frameIndex -lt $frameCount; $frameIndex++) {
                [byte[]]$frameHeader = Read-ExactBytes $stream 528 "Frame $name/$frameIndex"
                $width = [System.BitConverter]::ToUInt16($frameHeader, 0)
                $height = [System.BitConverter]::ToUInt16($frameHeader, 2)
                $codec = [uint32]$frameHeader[9]
                $storedBytes = [System.BitConverter]::ToUInt32($frameHeader, 12)
                $expectedBytes = [uint64]$width * [uint64]$height * [uint64]$scale * [uint64]$scale
                if ($width -eq 0 -or $height -eq 0 -or
                    $frameHeader[10] -ne 0 -or $frameHeader[11] -ne 0 -or
                    $expectedBytes -lt 1 -or $expectedBytes -gt [uint64](128MB) -or
                    ($version -eq 3 -and ($codec -ne 0 -or [uint64]$storedBytes -ne $expectedBytes)) -or
                    ($version -eq 5 -and -not (
                        ($codec -eq 0 -and [uint64]$storedBytes -eq $expectedBytes) -or
                        ($codec -eq 1 -and $storedBytes -gt 0 -and [uint64]$storedBytes -lt $expectedBytes)))) {
                    throw "Frame incompatible : $name/$frameIndex."
                }
                [void](Read-ExactBytes $stream ([int]$storedBytes) "Payload $name/$frameIndex")
                $indexBytesTotal += $expectedBytes
                $storedIndexBytesTotal += [uint64]$storedBytes
                $recordLogicalBytes += [uint64]528 + $expectedBytes
                if ($codec -eq 1) { $compressedFrameCount++ } else { $rawFrameCount++ }
            }
            for ($cycleIndex = 0; $cycleIndex -lt $cycleCount; $cycleIndex++) {
                [byte[]]$cycleHeader = Read-ExactBytes $stream 4 "Cycle $name/$cycleIndex"
                $slots = [System.BitConverter]::ToUInt32($cycleHeader, 0)
                if ($slots -gt 65536) { throw "Cycle invalide : $name/$cycleIndex" }
                [byte[]]$lookups = Read-ExactBytes $stream ([int]([uint64]$slots * 4)) "Lookups $name/$cycleIndex"
                for ($slot = 0; $slot -lt $slots; $slot++) {
                    if ([System.BitConverter]::ToUInt32($lookups, $slot * 4) -ge $frameCount) {
                        throw "Lookup hors frame : $name/$cycleIndex/$slot"
                    }
                }
                $recordLogicalBytes += [uint64]4 + [uint64]$slots * 4
            }
            $resourceRecords += [pscustomobject]@{
                resref = $name; logical_bytes = [uint64]$recordLogicalBytes
                frame_count = [uint32]$frameCount; cycle_count = [uint32]$cycleCount
            }
        }
        if ($stream.Position -ne $stream.Length) { throw 'Octets résiduels dans le shard catalogue.' }
        if ($version -eq 3 -and $indexBytesTotal -gt [uint64]$stream.Length) {
            throw 'Un shard V3 ne peut pas avoir plus d indices logiques que d octets physiques.'
        }
        return [pscustomobject]@{
            magic = $magic; version = [uint32]$version; scale = [uint32]$scale
            animation_id = [uint32]$animationId; resource_count = [uint32]$resourceCount
            frame_count = [uint64]$frameCountTotal; index_bytes = [uint64]$indexBytesTotal
            stored_index_bytes = [uint64]$storedIndexBytesTotal
            compressed_frame_count = [uint64]$compressedFrameCount
            raw_frame_count = [uint64]$rawFrameCount
            registry_bytes = [uint64]$stream.Length; resources = $resourceNames
            resource_records = $resourceRecords
        }
    } finally { $stream.Dispose() }
}

function Get-ComponentDigest([int]$Scale, [byte[][]]$ShardEntries) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        [byte[]]$domain = [System.Text.Encoding]::ASCII.GetBytes("IEECSNC-COMPONENT-V1`0")
        [void]$sha.TransformBlock($domain, 0, $domain.Length, $domain, 0)
        [byte[]]$scaleBytes = [System.BitConverter]::GetBytes([uint32]$Scale)
        [void]$sha.TransformBlock($scaleBytes, 0, $scaleBytes.Length, $scaleBytes, 0)
        foreach ($entry in $ShardEntries) {
            if ($entry.Length -ne 64) { throw 'Entrée shard interne non canonique.' }
            [void]$sha.TransformBlock($entry, 0, $entry.Length, $entry, 0)
        }
        [void]$sha.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($sha.Hash)).Replace('-', '')
    } finally { $sha.Dispose() }
}

function Get-CatalogDirectoryDigest([int]$Scale, [byte[][]]$DirectoryEntries) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        [byte[]]$domain = [System.Text.Encoding]::ASCII.GetBytes("IEECSNC-DIRECTORY-V2`0")
        [void]$sha.TransformBlock($domain, 0, $domain.Length, $domain, 0)
        [byte[]]$scaleBytes = [System.BitConverter]::GetBytes([uint32]$Scale)
        [void]$sha.TransformBlock($scaleBytes, 0, $scaleBytes.Length, $scaleBytes, 0)
        foreach ($entry in $DirectoryEntries) {
            if ($entry.Length -ne 24) { throw 'Entrée directory catalogue non canonique.' }
            [void]$sha.TransformBlock($entry, 0, $entry.Length, $entry, 0)
        }
        [void]$sha.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($sha.Hash)).Replace('-', '')
    } finally { $sha.Dispose() }
}

function Add-Sha256Block($Sha, [byte[]]$Bytes) {
    if ($null -eq $Bytes -or $Bytes.Length -lt 1) { return }
    [void]$Sha.TransformBlock($Bytes, 0, $Bytes.Length, $Bytes, 0)
}

function Convert-HexDigestToBytes([string]$Value, [string]$Label) {
    Assert-HashText $Value $Label
    [byte[]]$bytes = New-Object byte[] 32
    for ($index = 0; $index -lt 32; $index++) {
        $bytes[$index] = [Convert]::ToByte($Value.Substring($index * 2, 2), 16)
    }
    return $bytes
}

function Get-CatalogSourceComponentDigest([int]$Scale, $ResolvedShards, [uint32]$ResourceCount) {
    $items = @($ResolvedShards)
    if ($Scale -notin @(2, 4) -or $items.Count -lt 1 -or $ResourceCount -lt 1) {
        throw 'Entrée de digest logique composant invalide.'
    }
    $versions = @($items | ForEach-Object { [uint32]$_.registry_info.version } | Sort-Object -Unique)
    if ($versions.Count -ne 1 -or $versions[0] -notin @(3, 5)) {
        throw 'Un composant logique mélange des versions de stockage.'
    }
    Initialize-XpressHuffDecoder
    $decoder = $null
    if ($versions[0] -eq 5) {
        $decoder = New-Object BG2Upscale.CatalogXpressHuffDecoder
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        Add-Sha256Block $sha ([System.Text.Encoding]::ASCII.GetBytes("IEECSNC-SOURCE-COMPONENT-V1`0"))
        Add-Sha256Block $sha ([System.BitConverter]::GetBytes([uint32]$Scale))
        Add-Sha256Block $sha ([System.BitConverter]::GetBytes([uint32]$ResourceCount))
        [uint32]$seenRecords = 0
        $previousResref = $null
        foreach ($resolved in $items) {
            $info = $resolved.registry_info
            $stream = [System.IO.File]::Open([string]$resolved.source_path,
                [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::Read)
            try {
                [void](Read-ExactBytes $stream 24 'En-tête shard pour digest logique')
                $records = @($info.resource_records)
                if ($records.Count -ne $info.resource_count) {
                    throw 'Inventaire resref incomplet pour digest logique.'
                }
                foreach ($record in $records) {
                    [byte[]]$resourceHeader = Read-ExactBytes $stream 48 'Ressource pour digest logique'
                    $nameEnd = [System.Array]::IndexOf($resourceHeader, [byte]0, 0, 8)
                    if ($nameEnd -eq -1) { $nameEnd = 8 }
                    $resref = [System.Text.Encoding]::ASCII.GetString($resourceHeader, 0, $nameEnd)
                    if ($resref -cne [string]$record.resref -or
                        ($null -ne $previousResref -and
                         [string]::CompareOrdinal($resref, $previousResref) -le 0)) {
                        throw "Ordre logique resref non canonique : $resref"
                    }
                    $previousResref = $resref
                    Add-Sha256Block $sha ([System.Text.Encoding]::ASCII.GetBytes($resref + [char]0))
                    Add-Sha256Block $sha ([System.BitConverter]::GetBytes([uint64]$record.logical_bytes))
                    Add-Sha256Block $sha $resourceHeader
                    $frameCount = [System.BitConverter]::ToUInt32($resourceHeader, 40)
                    $cycleCount = [System.BitConverter]::ToUInt32($resourceHeader, 44)
                    [uint64]$actualLogicalBytes = 48
                    for ($frameIndex = 0; $frameIndex -lt $frameCount; $frameIndex++) {
                        [byte[]]$frameHeader = Read-ExactBytes $stream 528 `
                            "Frame logique $resref/$frameIndex"
                        $width = [System.BitConverter]::ToUInt16($frameHeader, 0)
                        $height = [System.BitConverter]::ToUInt16($frameHeader, 2)
                        $codec = [uint32]$frameHeader[9]
                        $storedBytes = [System.BitConverter]::ToUInt32($frameHeader, 12)
                        [uint64]$logicalBytes64 = [uint64]$width * [uint64]$height *
                            [uint64]$Scale * [uint64]$Scale
                        if ($logicalBytes64 -lt 1 -or $logicalBytes64 -gt [uint64](128MB) -or
                            $frameHeader[10] -ne 0 -or $frameHeader[11] -ne 0 -or
                            ($info.version -eq 3 -and
                             ($codec -ne 0 -or [uint64]$storedBytes -ne $logicalBytes64)) -or
                            ($info.version -eq 5 -and -not (
                                ($codec -eq 0 -and [uint64]$storedBytes -eq $logicalBytes64) -or
                                ($codec -eq 1 -and $storedBytes -gt 0 -and
                                 [uint64]$storedBytes -lt $logicalBytes64)))) {
                            throw "Frame logique invalide : $resref/$frameIndex"
                        }
                        [byte[]]$stored = Read-ExactBytes $stream ([int]$storedBytes) `
                            "Payload logique $resref/$frameIndex"
                        [byte[]]$indices = if ($codec -eq 1) {
                            $decoder.Decode($stored, [int]$logicalBytes64)
                        } else { $stored }
                        if (-not [BG2Upscale.CatalogXpressHuffDecoder]::RepresentativesCover(
                                $frameHeader, $indices)) {
                            throw "Représentant palette absent : $resref/$frameIndex"
                        }
                        [byte[]]$canonicalHeader = [byte[]]$frameHeader.Clone()
                        $canonicalHeader[9] = 0; $canonicalHeader[10] = 0; $canonicalHeader[11] = 0
                        [System.BitConverter]::GetBytes([uint32]$logicalBytes64).CopyTo(
                            $canonicalHeader, 12)
                        Add-Sha256Block $sha $canonicalHeader
                        Add-Sha256Block $sha $indices
                        $actualLogicalBytes += [uint64]528 + $logicalBytes64
                    }
                    for ($cycleIndex = 0; $cycleIndex -lt $cycleCount; $cycleIndex++) {
                        [byte[]]$cycleHeader = Read-ExactBytes $stream 4 `
                            "Cycle logique $resref/$cycleIndex"
                        $slots = [System.BitConverter]::ToUInt32($cycleHeader, 0)
                        if ($slots -gt 65536) {
                            throw "Cycle logique invalide : $resref/$cycleIndex"
                        }
                        [byte[]]$lookups = Read-ExactBytes $stream ([int]([uint64]$slots * 4)) `
                            "Lookups logiques $resref/$cycleIndex"
                        for ($slot = 0; $slot -lt $slots; $slot++) {
                            if ([System.BitConverter]::ToUInt32($lookups, $slot * 4) -ge $frameCount) {
                                throw "Lookup logique hors frame : $resref/$cycleIndex/$slot"
                            }
                        }
                        Add-Sha256Block $sha $cycleHeader
                        Add-Sha256Block $sha $lookups
                        $actualLogicalBytes += [uint64]4 + [uint64]$slots * 4
                    }
                    if ($actualLogicalBytes -ne [uint64]$record.logical_bytes) {
                        throw "Taille logique ressource divergente : $resref"
                    }
                    $seenRecords++
                }
                if ($stream.Position -ne $stream.Length) {
                    throw 'Octets résiduels pendant le digest logique composant.'
                }
            } finally { $stream.Dispose() }
        }
        if ($seenRecords -ne $ResourceCount) {
            throw 'Nombre de ressources du digest logique composant divergent.'
        }
        [void]$sha.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($sha.Hash)).Replace('-', '')
    } finally {
        $sha.Dispose()
        if ($null -ne $decoder) { $decoder.Dispose() }
    }
}

function Get-CatalogLogicalContentDigest($Catalog, [string[]]$ComponentDigests) {
    $componentDigestItems = @($ComponentDigests)
    if ($componentDigestItems.Count -ne $Catalog.component_count) {
        throw 'Nombre de digests logiques composant incompatible.'
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        Add-Sha256Block $sha ([System.Text.Encoding]::ASCII.GetBytes("IEECSNC-LOGICAL-CONTENT-V1`0"))
        foreach ($value in @(
                [uint32]$Catalog.scale,
                [uint32]$Catalog.animation_count,
                [uint32]$Catalog.component_count)) {
            Add-Sha256Block $sha ([System.BitConverter]::GetBytes([uint32]$value))
        }
        foreach ($digest in $componentDigestItems) {
            Add-Sha256Block $sha (Convert-HexDigestToBytes $digest 'Digest logique composant')
        }
        [uint32]$previousAnimationId = 0
        foreach ($animation in $Catalog.animations) {
            $animationComponentIndices = @($animation.component_indices)
            if ($animation.animation_id -le $previousAnimationId -or
                $animationComponentIndices.Count -lt 1) {
                throw 'Mapping animation logique non canonique.'
            }
            foreach ($value in @(
                    [uint32]$animation.animation_id,
                    [uint32]$animation.owner,
                    [uint32]$animationComponentIndices.Count)) {
                Add-Sha256Block $sha ([System.BitConverter]::GetBytes([uint32]$value))
            }
            foreach ($componentIndex in $animationComponentIndices) {
                Add-Sha256Block $sha ([System.BitConverter]::GetBytes([uint32]$componentIndex))
            }
            $previousAnimationId = $animation.animation_id
        }
        [void]$sha.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($sha.Hash)).Replace('-', '')
    } finally { $sha.Dispose() }
}

function Get-CatalogLogicalIdentity($Catalog, $ResolvedShards) {
    $resolved = @($ResolvedShards)
    if ($resolved.Count -ne $Catalog.shard_count) {
        throw 'Inventaire de shards incomplet pour identité logique.'
    }
    $versions = @($resolved | ForEach-Object { [uint32]$_.registry_info.version } |
        Sort-Object -Unique)
    if ($versions.Count -ne 1 -or $versions[0] -notin @(3, 5)) {
        throw 'Le catalogue mélange des shards V3/V5 ou utilise une version inconnue.'
    }
    $shardVersion = [uint32]$versions[0]
    if (($Catalog.version -eq 1 -and $shardVersion -ne 3) -or
        ($shardVersion -eq 5 -and $Catalog.version -ne 2)) {
        throw 'Couplage version catalogue/shard interdit.'
    }
    [uint64]$storedIndexBytes = 0
    [uint64]$compressedFrameCount = 0
    [uint64]$rawFrameCount = 0
    foreach ($item in $resolved) {
        $storedIndexBytes += [uint64]$item.registry_info.stored_index_bytes
        $compressedFrameCount += [uint64]$item.registry_info.compressed_frame_count
        $rawFrameCount += [uint64]$item.registry_info.raw_frame_count
    }
    if ($shardVersion -eq 3 -and $Catalog.total_index_bytes -gt $Catalog.total_registry_bytes) {
        throw 'index_bytes logique ne peut dépasser registry_bytes physique que dans un shard V5.'
    }
    $componentDigests = @()
    foreach ($component in $Catalog.components) {
        $componentShards = @()
        for ($local = 0; $local -lt $component.shard_count; $local++) {
            $componentShards += $resolved[[int]$component.shard_start + $local]
        }
        $componentDigests += Get-CatalogSourceComponentDigest ([int]$Catalog.scale) `
            $componentShards ([uint32]$component.resource_count)
    }
    $logicalContentSha256 = Get-CatalogLogicalContentDigest $Catalog $componentDigests
    $frameStorage = if ($shardVersion -eq 5) {
        'XPRESS_HUFF-or-raw-per-frame-v1'
    } else { 'raw-v3' }
    foreach ($property in @(
            [pscustomobject]@{ name = 'shard_registry_version'; value = $shardVersion },
            [pscustomobject]@{ name = 'frame_storage'; value = $frameStorage },
            [pscustomobject]@{ name = 'logical_component_digests'; value = $componentDigests },
            [pscustomobject]@{ name = 'logical_content_sha256'; value = $logicalContentSha256 },
            [pscustomobject]@{ name = 'stored_index_bytes'; value = $storedIndexBytes },
            [pscustomobject]@{ name = 'compressed_frame_count'; value = $compressedFrameCount },
            [pscustomobject]@{ name = 'raw_frame_count'; value = $rawFrameCount })) {
        $Catalog | Add-Member -MemberType NoteProperty -Name $property.name `
            -Value $property.value -Force
    }
    return [pscustomobject]@{
        shard_registry_version = $shardVersion; frame_storage = $frameStorage
        logical_component_digests = $componentDigests
        logical_content_sha256 = $logicalContentSha256
        stored_index_bytes = $storedIndexBytes
        compressed_frame_count = $compressedFrameCount
        raw_frame_count = $rawFrameCount
        index_storage_ratio = [double]$storedIndexBytes / [double]$Catalog.total_index_bytes
    }
}

function Read-Catalog([string]$Path) {
    Assert-SafeKnownPath $Path 'Lecture catalogue'
    if (-not [string]::Equals([System.IO.Path]::GetFileName($Path), 'CreatureSprites-XN.catalog',
            [System.StringComparison]::Ordinal)) {
        throw 'Nom de fichier catalogue non canonique.'
    }
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        if ($stream.Length -lt 216 -or $stream.Length -gt 28450920) {
            throw "Taille catalogue hors contrat : $($stream.Length)."
        }
        [byte[]]$header = Read-ExactBytes $stream 64 'En-tête catalogue'
        $magic = [System.Text.Encoding]::ASCII.GetString($header, 0, 7)
        if ($header[7] -ne 0 -or $magic -ne 'IEECSNC') { throw 'Magic catalogue invalide.' }
        $version = [System.BitConverter]::ToUInt32($header, 8)
        $scale = [System.BitConverter]::ToUInt32($header, 12)
        $animationCount = [System.BitConverter]::ToUInt32($header, 16)
        $componentCount = [System.BitConverter]::ToUInt32($header, 20)
        $membershipCount = [System.BitConverter]::ToUInt32($header, 24)
        $shardCount = [System.BitConverter]::ToUInt32($header, 28)
        $totalResources = [System.BitConverter]::ToUInt64($header, 32)
        $totalFrames = [System.BitConverter]::ToUInt64($header, 40)
        $totalIndexBytes = [System.BitConverter]::ToUInt64($header, 48)
        $totalRegistryBytes = [System.BitConverter]::ToUInt64($header, 56)
        if ($version -notin @(1, 2) -or $scale -notin @(2, 4) -or
            $animationCount -lt 1 -or $animationCount -gt 512 -or
            $componentCount -lt 1 -or $componentCount -gt 16384 -or
            $membershipCount -lt $animationCount -or $membershipCount -gt 262144 -or
            $shardCount -lt $componentCount -or $shardCount -gt 16384 -or
            $totalResources -lt 1 -or $totalResources -gt 32768 -or
            $totalFrames -lt 1 -or $totalFrames -gt 4194304 -or
            $totalIndexBytes -lt 1 -or $totalIndexBytes -gt 137438953472 -or
            $totalRegistryBytes -lt 24 -or $totalRegistryBytes -gt 137438953472 -or
            ($version -eq 1 -and $totalIndexBytes -gt $totalRegistryBytes)) {
            throw 'En-tête catalogue hors limites runtime.'
        }
        [uint32]$directoryCount = 0
        [uint32]$directoryEntryBytes = 0
        $directorySha256 = $null
        [uint64]$headerBytes = 64
        if ($version -eq 2) {
            [byte[]]$extension = Read-ExactBytes $stream 40 'Extension catalogue V2'
            $directoryCount = [System.BitConverter]::ToUInt32($extension, 0)
            $directoryEntryBytes = [System.BitConverter]::ToUInt32($extension, 4)
            [byte[]]$directoryShaBytes = New-Object byte[] 32
            [System.Array]::Copy($extension, 8, $directoryShaBytes, 0, 32)
            $directorySha256 = ([System.BitConverter]::ToString($directoryShaBytes)).Replace('-', '')
            if ($directoryCount -lt $animationCount -or $directoryCount -gt 1048576 -or
                $directoryEntryBytes -ne 24 -or
                @($directoryShaBytes | Where-Object { $_ -ne 0 }).Count -eq 0) {
                throw 'Extension directory catalogue V2 hors limites.'
            }
            $headerBytes = 104
        }
        $expectedBytes = $headerBytes + [uint64]16 * $animationCount +
            [uint64]4 * $membershipCount + [uint64]72 * $componentCount +
            [uint64]64 * $shardCount + [uint64]$directoryEntryBytes * $directoryCount
        if ([uint64]$stream.Length -ne $expectedBytes) {
            throw "Taille catalogue incohérente : $($stream.Length), attendu $expectedBytes."
        }

        $animations = @(); $seenAnimations = @{}; [uint64]$nextMembership = 0
        [uint32]$previousAnimationId = 0
        for ($i = 0; $i -lt $animationCount; $i++) {
            [byte[]]$entry = Read-ExactBytes $stream 16 "Animation catalogue $i"
            $animationId = [System.BitConverter]::ToUInt32($entry, 0)
            $owner = [System.BitConverter]::ToUInt32($entry, 4)
            $membershipStart = [System.BitConverter]::ToUInt32($entry, 8)
            $members = [System.BitConverter]::ToUInt32($entry, 12)
            $family = $animationId -band 0xF000
            $ownerMatches = ($owner -eq 1 -and $family -in @(0x5000, 0x6000)) -or
                ($owner -eq 2 -and $family -eq 0xE000)
            if ($animationId -lt 1 -or $animationId -gt 65534 -or
                $animationId -le $previousAnimationId -or -not $ownerMatches -or
                $members -lt 1 -or [uint64]$membershipStart -ne $nextMembership -or
                [uint64]$membershipStart + [uint64]$members -gt $membershipCount) {
                throw "Entrée animation catalogue invalide : $i."
            }
            if ($seenAnimations.ContainsKey([string]$animationId)) { throw "Animation dupliquée : $animationId" }
            $seenAnimations[[string]$animationId] = $true
            $animations += [pscustomobject]@{
                index = $i; animation_id = [uint32]$animationId; owner = [uint32]$owner
                membership_start = [uint32]$membershipStart; membership_count = [uint32]$members
                component_indices = @(); component_digests = @()
            }
            $previousAnimationId = $animationId
            $nextMembership += [uint64]$members
        }
        if ($nextMembership -ne $membershipCount) { throw 'Table membership non couverte.' }
        $memberships = @()
        for ($i = 0; $i -lt $membershipCount; $i++) {
            [byte[]]$entry = Read-ExactBytes $stream 4 "Membership catalogue $i"
            $componentIndex = [System.BitConverter]::ToUInt32($entry, 0)
            if ($componentIndex -ge $componentCount) { throw "Membership hors composant : $i" }
            $memberships += [uint32]$componentIndex
        }

        $components = @(); $seenDigests = @{}; [uint64]$nextShard = 0
        for ($i = 0; $i -lt $componentCount; $i++) {
            [byte[]]$entry = Read-ExactBytes $stream 72 "Composant catalogue $i"
            [byte[]]$digestBytes = New-Object byte[] 32
            [System.Array]::Copy($entry, 0, $digestBytes, 0, 32)
            if (@($digestBytes | Where-Object { $_ -ne 0 }).Count -eq 0) { throw "Digest composant nul : $i" }
            $digest = ([System.BitConverter]::ToString($digestBytes)).Replace('-', '')
            $shardStart = [System.BitConverter]::ToUInt32($entry, 32)
            $componentShards = [System.BitConverter]::ToUInt32($entry, 36)
            $resources = [System.BitConverter]::ToUInt32($entry, 40)
            $reserved = [System.BitConverter]::ToUInt32($entry, 44)
            $frames = [System.BitConverter]::ToUInt64($entry, 48)
            $indexBytes = [System.BitConverter]::ToUInt64($entry, 56)
            $registryBytes = [System.BitConverter]::ToUInt64($entry, 64)
            if ($seenDigests.ContainsKey($digest)) { throw "Digest composant dupliqué : $digest" }
            if ([uint64]$shardStart -ne $nextShard -or $componentShards -lt 1 -or
                [uint64]$shardStart + [uint64]$componentShards -gt $shardCount -or
                $resources -lt 1 -or $resources -gt 32768 -or
                $frames -lt 1 -or $frames -gt 4194304 -or
                $indexBytes -lt 1 -or $indexBytes -gt 137438953472 -or
                $registryBytes -lt 24 -or $registryBytes -gt 137438953472 -or
                ($version -eq 1 -and $indexBytes -gt $registryBytes) -or $reserved -ne 0) {
                throw "Composant catalogue invalide : $i."
            }
            $seenDigests[$digest] = $true
            $components += [pscustomobject]@{
                index = $i; digest = $digest; shard_start = [uint32]$shardStart
                shard_count = [uint32]$componentShards; resource_count = [uint32]$resources
                frame_count = [uint64]$frames; index_bytes = [uint64]$indexBytes
                registry_bytes = [uint64]$registryBytes
            }
            $nextShard += [uint64]$componentShards
        }
        if ($nextShard -ne $shardCount) { throw 'Table shard non couverte par les composants.' }

        $shards = @(); $shardRaw = @(); $seenShards = @{}
        [uint64]$sumResources = 0; [uint64]$sumFrames = 0
        [uint64]$sumIndex = 0; [uint64]$sumRegistry = 0
        for ($i = 0; $i -lt $shardCount; $i++) {
            [byte[]]$entry = Read-ExactBytes $stream 64 "Shard catalogue $i"
            [byte[]]$shaBytes = New-Object byte[] 32
            [System.Array]::Copy($entry, 0, $shaBytes, 0, 32)
            if (@($shaBytes | Where-Object { $_ -ne 0 }).Count -eq 0) { throw "SHA shard nul : $i" }
            $sha256 = ([System.BitConverter]::ToString($shaBytes)).Replace('-', '')
            $crc32 = [System.BitConverter]::ToUInt32($entry, 32)
            $resources = [System.BitConverter]::ToUInt32($entry, 36)
            $frames = [System.BitConverter]::ToUInt64($entry, 40)
            $indexBytes = [System.BitConverter]::ToUInt64($entry, 48)
            $registryBytes = [System.BitConverter]::ToUInt64($entry, 56)
            if ($seenShards.ContainsKey($sha256)) { throw "SHA shard dupliqué : $sha256" }
            if ($resources -lt 1 -or $resources -gt 128 -or $frames -lt 1 -or
                $frames -gt [uint64]$resources * 4096 -or $indexBytes -lt 1 -or
                $registryBytes -lt 24 -or
                ($version -eq 1 -and $indexBytes -gt $registryBytes) -or
                $registryBytes -gt (Get-MaxRegistryBytes ([int]$scale))) {
                throw "Entrée shard catalogue invalide : $i."
            }
            $seenShards[$sha256] = $true
            $shards += [pscustomobject]@{
                index = $i; sha256 = $sha256; crc32 = [uint32]$crc32
                resource_count = [uint32]$resources; frame_count = [uint64]$frames
                index_bytes = [uint64]$indexBytes; registry_bytes = [uint64]$registryBytes
                raw = $entry
            }
            $shardRaw += ,$entry
            $sumResources += $resources; $sumFrames += $frames
            $sumIndex += $indexBytes; $sumRegistry += $registryBytes
        }
        if ($sumResources -ne $totalResources -or $sumFrames -ne $totalFrames -or $sumIndex -ne $totalIndexBytes -or
            $sumRegistry -ne $totalRegistryBytes) {
            throw 'Totaux catalogue incompatibles avec les shards.'
        }
        $componentReferenced = New-Object bool[] $componentCount
        $animationComponents = @{}
        foreach ($animation in $animations) {
            $seenMembership = @{}; $indices = @(); $digests = @()
            for ($m = 0; $m -lt $animation.membership_count; $m++) {
                $componentIndex = [int]$memberships[[int]$animation.membership_start + $m]
                if ($seenMembership.ContainsKey([string]$componentIndex)) {
                    throw "Composant répété pour l'animation $(Format-AnimationId $animation.animation_id)."
                }
                $seenMembership[[string]$componentIndex] = $true
                $componentReferenced[$componentIndex] = $true
                $indices += $componentIndex
                $digests += $components[$componentIndex].digest
            }
            $sortedIndices = @($indices | Sort-Object -Unique)
            if (($indices -join '|') -cne ($sortedIndices -join '|')) {
                throw "Membership non trié ou dupliqué : $(Format-AnimationId $animation.animation_id)"
            }
            $animation.component_indices = $indices
            $animation.component_digests = $digests
            $componentSet = [System.Collections.Generic.HashSet[uint32]]::new()
            foreach ($componentIndex in $indices) { [void]$componentSet.Add([uint32]$componentIndex) }
            $animationComponents[[string]$animation.animation_id] = $componentSet
        }
        for ($i = 0; $i -lt $componentCount; $i++) {
            if (-not $componentReferenced[$i]) { throw "Composant non référencé : $i" }
            $component = $components[$i]
            $entries = @(); [uint64]$resources = 0; [uint64]$frames = 0
            [uint64]$indexBytes = 0; [uint64]$registryBytes = 0
            for ($s = 0; $s -lt $component.shard_count; $s++) {
                $shardIndex = [int]$component.shard_start + $s
                $entries += ,([byte[]]$shardRaw[$shardIndex])
                $resources += $shards[$shardIndex].resource_count
                $frames += $shards[$shardIndex].frame_count
                $indexBytes += $shards[$shardIndex].index_bytes
                $registryBytes += $shards[$shardIndex].registry_bytes
            }
            $digest = Get-ComponentDigest ([int]$scale) $entries
            if ($digest -cne $component.digest -or $resources -ne $component.resource_count -or
                $frames -ne $component.frame_count -or $indexBytes -ne $component.index_bytes -or
                $registryBytes -ne $component.registry_bytes) {
                throw "Digest ou totaux du composant $i invalides."
            }
        }
        $directory = @(); $directoryRaw = @()
        if ($version -eq 2) {
            [uint32]$previousDirectoryAnimation = 0
            $previousDirectoryResref = $null
            for ($i = 0; $i -lt $directoryCount; $i++) {
                [byte[]]$entry = Read-ExactBytes $stream 24 "Directory catalogue $i"
                $animationId = [System.BitConverter]::ToUInt32($entry, 0)
                $nameEnd = [System.Array]::IndexOf($entry, [byte]0, 4, 8)
                if ($nameEnd -eq -1) { $nameEnd = 12 }
                $nameLength = $nameEnd - 4
                if ($nameLength -lt 1) { throw "Resref vide dans la directory : $i" }
                $resref = [System.Text.Encoding]::ASCII.GetString($entry, 4, $nameLength)
                if ($resref -notmatch '^[A-Z0-9_]{1,8}$') {
                    throw "Resref directory invalide : $resref"
                }
                for ($padding = $nameEnd; $padding -lt 12; $padding++) {
                    if ($entry[$padding] -ne 0) { throw "Padding directory invalide : $resref" }
                }
                $componentIndex = [System.BitConverter]::ToUInt32($entry, 12)
                $shardIndex = [System.BitConverter]::ToUInt32($entry, 16)
                $resourceOrdinal = [System.BitConverter]::ToUInt32($entry, 20)
                if (-not $seenAnimations.ContainsKey([string]$animationId) -or
                    $componentIndex -ge $componentCount -or $shardIndex -ge $shardCount -or
                    $resourceOrdinal -ge $shards[[int]$shardIndex].resource_count) {
                    throw "Entrée directory hors tables : $i"
                }
                if (-not $animationComponents.ContainsKey([string]$animationId) -or
                    -not $animationComponents[[string]$animationId].Contains([uint32]$componentIndex)) {
                    throw "Composant directory hors animation : $i"
                }
                $component = $components[[int]$componentIndex]
                if ($shardIndex -lt $component.shard_start -or
                    $shardIndex -ge [uint64]$component.shard_start + $component.shard_count) {
                    throw "Shard directory hors composant : $i"
                }
                if ($i -gt 0 -and ($animationId -lt $previousDirectoryAnimation -or
                    ($animationId -eq $previousDirectoryAnimation -and
                     [string]::CompareOrdinal($resref, $previousDirectoryResref) -le 0))) {
                    throw "Directory catalogue non triée ou dupliquée : $i"
                }
                $directory += [pscustomobject]@{
                    index = $i; animation_id = [uint32]$animationId; resref = $resref
                    component_index = [uint32]$componentIndex; shard_index = [uint32]$shardIndex
                    resource_ordinal = [uint32]$resourceOrdinal
                }
                $directoryRaw += ,$entry
                $previousDirectoryAnimation = $animationId
                $previousDirectoryResref = $resref
            }
            $actualDirectorySha256 = Get-CatalogDirectoryDigest ([int]$scale) $directoryRaw
            if ($actualDirectorySha256 -cne $directorySha256) {
                throw 'Digest directory catalogue V2 invalide.'
            }
        }
        if ($stream.Position -ne $stream.Length) { throw 'Octets résiduels dans le catalogue.' }
        return [pscustomobject]@{
            magic = $magic; version = [uint32]$version; scale = [uint32]$scale
            animation_count = [uint32]$animationCount; component_count = [uint32]$componentCount
            membership_count = [uint32]$membershipCount; shard_count = [uint32]$shardCount
            total_resources = [uint64]$totalResources; total_frames = [uint64]$totalFrames
            total_index_bytes = [uint64]$totalIndexBytes; total_registry_bytes = [uint64]$totalRegistryBytes
            bytes = [uint64]$stream.Length; animations = $animations; memberships = $memberships
            components = $components; shards = $shards
            directory_count = [uint32]$directoryCount
            directory_entry_bytes = [uint32]$directoryEntryBytes
            directory_sha256 = $directorySha256; directory = $directory
        }
    } finally { $stream.Dispose() }
}

function Assert-StringArray($Value, [string]$Label, [int]$Minimum = 1) {
    $items = @($Value)
    if ($items.Count -lt $Minimum) { throw "$Label contient trop peu d'éléments." }
    foreach ($item in $items) {
        if ($item -isnot [string] -or [string]::IsNullOrWhiteSpace([string]$item)) {
            throw "$Label contient une chaîne invalide."
        }
    }
    return $items
}

function Assert-ExactStringSet($Actual, $Expected, [string]$Label) {
    $actualItems = @($Actual | ForEach-Object { [string]$_ } | Sort-Object -CaseSensitive)
    $expectedItems = @($Expected | ForEach-Object { [string]$_ } | Sort-Object -CaseSensitive)
    if (($actualItems -join "`0") -cne ($expectedItems -join "`0")) {
        throw "$Label diffère du catalogue binaire."
    }
}

function Assert-BuildValidation($Validation, [int]$Scale, [int]$CatalogVersion = 1,
        [int]$ShardVersion = 3) {
    foreach ($name in @(
        'records_copied_without_xbr', 'game_launch_is_never_automatic',
        'release_manifest_is_out_of_scope'
    )) {
        $value = Get-RequiredProperty $Validation $name 'build.validation'
        Assert-Boolean $value "build.validation.$name"
        if (-not $value) { throw "build.validation.$name doit être true." }
    }
    foreach ($name in @('resource_records_sha256_verified', 'palette_frames_exactly_remapped')) {
        if ([uint64](Get-RequiredProperty $Validation $name 'build.validation') -lt 1) {
            throw "build.validation.$name doit être un compteur non nul."
        }
    }
    foreach ($name in @('partial_alpha_pixels', 'new_colors', 'override_collisions')) {
        if ([uint64](Get-RequiredProperty $Validation $name 'build.validation') -ne 0) {
            throw "build.validation.$name doit valoir zéro."
        }
    }
    $limits = [ordered]@{
        maximum_animations = 512; maximum_components = 16384
        maximum_memberships = 262144; maximum_shards = 16384
        maximum_physical_resources = 32768; maximum_frames = 4194304
        maximum_registry_bytes = [uint64]137438953472; maximum_resources_per_shard = 128
    }
    foreach ($entry in $limits.GetEnumerator()) {
        if ([uint64](Get-RequiredProperty $Validation $entry.Key 'build.validation') -ne [uint64]$entry.Value) {
            throw "build.validation.$($entry.Key) diffère de la limite runtime."
        }
    }
    if ($CatalogVersion -eq 2) {
        if ([uint64](Get-RequiredProperty $Validation 'maximum_directory_entries' 'build.validation') -ne
            [uint64]1048576) {
            throw 'build.validation.maximum_directory_entries incompatible.'
        }
    } elseif ($null -ne $Validation.PSObject.Properties['maximum_directory_entries'] -and
        [uint64]$Validation.maximum_directory_entries -ne [uint64]1048576) {
        throw 'build.validation.maximum_directory_entries V1 incompatible.'
    }
    $expectedShardBytes = if ($Scale -eq 2) {
        [uint64](128MB)
    } elseif ($Scale -eq 4) {
        [uint64](512MB)
    } else { throw 'Échelle de validation catalogue absente.' }
    if ([uint64](Get-RequiredProperty $Validation 'maximum_shard_bytes' 'build.validation') -ne
        $expectedShardBytes) {
        throw 'build.validation.maximum_shard_bytes incompatible.'
    }
    if ($ShardVersion -eq 5) {
        $logicalPreserved = Get-RequiredProperty $Validation `
            'logical_records_preserved_after_lossless_storage_repack' 'build.validation'
        Assert-Boolean $logicalPreserved `
            'build.validation.logical_records_preserved_after_lossless_storage_repack'
        if (-not $logicalPreserved -or
            [uint32](Get-RequiredProperty $Validation 'catalog_shard_registry_version' `
                'build.validation') -ne 5 -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $Validation 'frame_storage' 'build.validation'),
                'XPRESS_HUFF-or-raw-per-frame-v1', [System.StringComparison]::Ordinal)) {
            throw 'Validation storage-repack V5 incomplète.'
        }
    } elseif ($ShardVersion -ne 3) {
        throw 'Version shard de validation inconnue.'
    }
}

function Assert-RuntimeLimits($Limits, [int]$CatalogVersion = 1) {
    $expected = [ordered]@{
        maximum_animations = 512; maximum_components = 16384
        maximum_memberships = 262144; maximum_shards = 16384
        maximum_physical_resources = 32768; maximum_frames = 4194304
        maximum_registry_bytes = [uint64]137438953472; maximum_resources_per_shard = 128
        maximum_frames_per_resource = 4096; maximum_lazy_frame_index_bytes = [uint64](128MB)
        maximum_x2_shard_bytes = [uint64](128MB); maximum_x4_shard_bytes = [uint64](512MB)
    }
    foreach ($entry in $expected.GetEnumerator()) {
        if ([uint64](Get-RequiredProperty $Limits $entry.Key 'runtime.catalog_limits') -ne [uint64]$entry.Value) {
            throw "runtime.catalog_limits.$($entry.Key) incompatible."
        }
    }
    if ($CatalogVersion -eq 2) {
        if ([uint64](Get-RequiredProperty $Limits 'maximum_directory_entries' 'runtime.catalog_limits') -ne
            [uint64]1048576) {
            throw 'runtime.catalog_limits.maximum_directory_entries incompatible.'
        }
    } elseif ($null -ne $Limits.PSObject.Properties['maximum_directory_entries'] -and
        [uint64]$Limits.maximum_directory_entries -ne [uint64]1048576) {
        throw 'runtime.catalog_limits.maximum_directory_entries V1 incompatible.'
    }
}

function Assert-SourceMembers($Build, [string]$JobPath, $Catalog) {
    $members = @(Get-RequiredProperty $Build 'source_members' 'build')
    if ($members.Count -lt 1 -or $members.Count -gt 16384) { throw 'build.source_members hors limites.' }
    $seenJobs = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($member in $members) {
        $memberJobPath = Resolve-ProjectPath ([string](Get-RequiredProperty $member 'job_file' 'build.source_members[]')) `
            'build.source_members[].job_file'
        if (-not $seenJobs.Add($memberJobPath)) { throw "Job source dupliqué : $memberJobPath" }
        $memberJobHash = [string](Get-RequiredProperty $member 'job_sha256' 'build.source_members[]')
        Assert-ExpectedHash $memberJobPath $memberJobHash 'Job source'
        $memberJob = Get-Content -LiteralPath $memberJobPath -Raw | ConvertFrom-Json
        Assert-OrdinalEqual ([string](Get-RequiredProperty $memberJob 'job_id' 'source job')) `
            ([string](Get-RequiredProperty $member 'job_id' 'build.source_members[]')) 'source member job_id'

        $animationId = Convert-AnimationId (Get-RequiredProperty $member 'animation_id' 'build.source_members[]') `
            'build.source_members[].animation_id'
        if (@($Catalog.animations | Where-Object { $_.animation_id -eq $animationId }).Count -ne 1) {
            throw "Animation du membre absente du catalogue : $(Format-AnimationId $animationId)"
        }
        $runtimeProfile = [string](Get-RequiredProperty $member 'runtime_profile' 'build.source_members[]')
        if ($runtimeProfile -notin @('character-bg2ee-2.7.3.0', 'monster-icewind-bg2ee-2.7.3.0')) {
            throw "Profil runtime source non supporté : $runtimeProfile"
        }
        $binaryAnimation = @($Catalog.animations | Where-Object { $_.animation_id -eq $animationId })[0]
        if (-not [string]::Equals($runtimeProfile, (Get-OwnerRuntimeProfile $binaryAnimation.owner),
                [System.StringComparison]::Ordinal)) {
            throw 'Profil runtime source incompatible avec owner.'
        }
        $memberBuildPath = Resolve-ProjectPath `
            ([string](Get-RequiredProperty $member 'build_manifest' 'build.source_members[]')) `
            'build.source_members[].build_manifest'
        Assert-ExpectedHash $memberBuildPath `
            ([string](Get-RequiredProperty $member 'build_manifest_sha256' 'build.source_members[]')) `
            'Build membre source'
        $componentIndices = @(Get-RequiredProperty $member 'component_indices' 'build.source_members[]')
        if ($componentIndices.Count -lt 1) { throw 'Membre source sans composant.' }
        $seenComponents = @{}
        foreach ($rawIndex in $componentIndices) {
            $index = [int]$rawIndex
            if ($index -lt 0 -or $index -ge $Catalog.component_count -or
                $seenComponents.ContainsKey([string]$index)) {
                throw 'Index composant source invalide ou dupliqué.'
            }
            $seenComponents[[string]$index] = $true
        }
        $memberComponentText = @(($componentIndices | ForEach-Object { [int]$_ }) | Sort-Object) -join '|'
        $binaryComponentText = @(($binaryAnimation.component_indices | ForEach-Object { [int]$_ }) | Sort-Object) -join '|'
        if ($memberComponentText -cne $binaryComponentText) {
            throw 'Les composants du membre source diffèrent du mapping animation.'
        }
        $prefixes = Assert-StringArray (Get-RequiredProperty $member 'bam_prefixes' 'build.source_members[]') `
            'build.source_members[].bam_prefixes'
        foreach ($prefix in $prefixes) {
            if ($prefix -notmatch '^[A-Z0-9_]{1,8}$') { throw "Préfixe BAM source invalide : $prefix" }
        }
    }
    $locks = Get-RequiredProperty $Build 'locks' 'build'
    Assert-HashText ([string](Get-RequiredProperty $locks 'input_lock_sha256' 'build.locks')) `
        'build.locks.input_lock_sha256'
    Assert-HashText ([string](Get-RequiredProperty $locks 'engine_source_contract_sha256' 'build.locks')) `
        'build.locks.engine_source_contract_sha256'
    Assert-HashText ([string](Get-RequiredProperty $locks 'baldur_real_sha256' 'build.locks')) `
        'build.locks.baldur_real_sha256'
    if ([int](Get-RequiredProperty $locks 'member_count' 'build.locks') -ne $members.Count -or
        [int](Get-RequiredProperty $locks 'leaf_job_count' 'build.locks') -lt $members.Count -or
        [int]$locks.leaf_job_count -gt 16384) {
        throw 'Compteurs build.locks incompatibles avec source_members.'
    }
    return $members
}

function Assert-InputLock($Build, [string]$JobPath, [string]$JobSha256,
        [string]$GenerationId, [int]$Scale, [string]$EngineSource,
        [string]$EngineContract, [string]$BaldurRealSha256) {
    $locks = Get-RequiredProperty $Build 'locks' 'build'
    $inputLock = Get-RequiredProperty $locks 'input_lock' 'build.locks'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'schema' 'build.locks.input_lock')) `
        'bg2-upscale-creature-sprite-xn-catalog-input-lock-v1' 'build.locks.input_lock.schema'
    $lockJob = Resolve-ProjectPath ([string](Get-RequiredProperty $inputLock 'job_file' 'input_lock')) `
        'input_lock.job_file'
    if (-not [string]::Equals($lockJob, $JobPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'input_lock.job_file diffère du job courant.'
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'job_sha256' 'input_lock')) `
        $JobSha256 'input_lock.job_sha256'
    Assert-UpscaleContract (Get-RequiredProperty $inputLock 'method' 'input_lock') $Scale `
        'input_lock.method'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'baldur_real_sha256' 'input_lock')) `
        $BaldurRealSha256 'input_lock.baldur_real_sha256'
    $lockEngine = Resolve-ProjectPath ([string](Get-RequiredProperty $inputLock 'engine_source' 'input_lock')) `
        'input_lock.engine_source'
    if (-not [string]::Equals($lockEngine.TrimEnd('\'), $EngineSource.TrimEnd('\'),
            [System.StringComparison]::OrdinalIgnoreCase)) { throw 'input_lock.engine_source incompatible.' }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $inputLock 'engine_source_contract_sha256' 'input_lock')) `
        $EngineContract 'input_lock.engine_source_contract_sha256'
    $builder = Resolve-ProjectPath ([string](Get-RequiredProperty $inputLock 'catalog_builder' 'input_lock')) `
        'input_lock.catalog_builder'
    $expectedBuilder = Join-Path $script:WorkspaceRoot 'pipeline\scripts\run_creature_sprite_x2.py'
    if (-not [string]::Equals($builder, $expectedBuilder,
            [System.StringComparison]::OrdinalIgnoreCase)) { throw 'input_lock.catalog_builder non canonique.' }
    Assert-ExpectedHash $builder ([string](Get-RequiredProperty $inputLock 'catalog_builder_sha256' 'input_lock')) `
        'Builder catalogue verrouillé'

    $memberLocks = @(Get-RequiredProperty $inputLock 'members' 'input_lock')
    $sourceMembers = @(Get-RequiredProperty $Build 'source_members' 'build')
    if ($memberLocks.Count -ne $sourceMembers.Count -or
        [int](Get-RequiredProperty $locks 'member_count' 'build.locks') -ne $memberLocks.Count) {
        throw 'input_lock.members count incompatible.'
    }
    $seenMemberJobs = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    for ($i = 0; $i -lt $memberLocks.Count; $i++) {
        $entry = $memberLocks[$i]
        $jobFile = Resolve-ProjectPath ([string](Get-RequiredProperty $entry 'job_file' 'input_lock.members[]')) `
            'input_lock.members[].job_file'
        if (-not $seenMemberJobs.Add($jobFile)) { throw "Membre input lock dupliqué : $jobFile" }
        Assert-ExpectedHash $jobFile ([string](Get-RequiredProperty $entry 'job_sha256' 'input_lock.members[]')) `
            "Job membre verrouillé $i"
        $memberJob = Get-Content -LiteralPath $jobFile -Raw | ConvertFrom-Json
        Assert-OrdinalEqual ([string](Get-RequiredProperty $entry 'job_id' 'input_lock.members[]')) `
            ([string](Get-RequiredProperty $memberJob 'job_id' 'locked member job')) "input_lock.members[$i].job_id"
        $manifest = Resolve-ProjectPath `
            ([string](Get-RequiredProperty $entry 'build_manifest' 'input_lock.members[]')) `
            'input_lock.members[].build_manifest'
        Assert-ExpectedHash $manifest `
            ([string](Get-RequiredProperty $entry 'build_manifest_sha256' 'input_lock.members[]')) `
            "Build membre verrouillé $i"
        foreach ($name in @('job_file', 'job_sha256', 'job_id', 'build_manifest', 'build_manifest_sha256')) {
            if (-not [string]::Equals([string](Get-RequiredProperty $entry $name 'input_lock.members[]'),
                    [string](Get-RequiredProperty $sourceMembers[$i] $name 'build.source_members[]'),
                    [System.StringComparison]::Ordinal)) {
                throw "input_lock.members[$i].$name diffère de source_members."
            }
        }
    }

    $leafLocks = @(Get-RequiredProperty $inputLock 'leaf_jobs' 'input_lock')
    if ($leafLocks.Count -ne [int](Get-RequiredProperty $locks 'leaf_job_count' 'build.locks') -or
        $leafLocks.Count -lt $memberLocks.Count -or $leafLocks.Count -gt 16384) {
        throw 'input_lock.leaf_jobs count incompatible.'
    }
    $seenLeafJobs = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    $seenPayloads = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $leafLocks) {
        Assert-ExactPropertyNames $entry @(
            'job_file', 'job_sha256', 'job_id', 'source_manifest',
            'source_manifest_sha256', 'build_manifest', 'build_manifest_sha256', 'payloads'
        ) 'input_lock.leaf_jobs[]'
        $leafJob = Resolve-ProjectPath ([string](Get-RequiredProperty $entry 'job_file' 'input_lock.leaf_jobs[]')) `
            'input_lock.leaf_jobs[].job_file'
        if (-not $seenLeafJobs.Add($leafJob)) { throw "Leaf job verrouillé dupliqué : $leafJob" }
        Assert-ExpectedHash $leafJob ([string](Get-RequiredProperty $entry 'job_sha256' 'input_lock.leaf_jobs[]')) `
            'Leaf job verrouillé'
        $leafJson = Get-Content -LiteralPath $leafJob -Raw | ConvertFrom-Json
        Assert-OrdinalEqual ([string](Get-RequiredProperty $entry 'job_id' 'input_lock.leaf_jobs[]')) `
            ([string](Get-RequiredProperty $leafJson 'job_id' 'locked leaf job')) 'input_lock.leaf_jobs[].job_id'
        foreach ($pair in @(
            @('source_manifest', 'source_manifest_sha256'),
            @('build_manifest', 'build_manifest_sha256')
        )) {
            $path = Resolve-ProjectPath ([string](Get-RequiredProperty $entry $pair[0] 'input_lock.leaf_jobs[]')) `
                "input_lock.leaf_jobs[].$($pair[0])"
            Assert-ExpectedHash $path ([string](Get-RequiredProperty $entry $pair[1] 'input_lock.leaf_jobs[]')) `
                "Leaf $($pair[0]) verrouillé"
        }
        $payloads = @(Get-RequiredProperty $entry 'payloads' 'input_lock.leaf_jobs[]')
        if ($payloads.Count -lt 1 -or $payloads.Count -gt 16385) {
            throw 'input_lock.leaf_jobs[].payloads hors limites.'
        }
        foreach ($payload in $payloads) {
            Assert-ExactPropertyNames $payload @('path', 'sha256', 'crc32', 'bytes') `
                'input_lock.leaf_jobs[].payloads[]'
            $payloadPath = Resolve-ProjectPath `
                ([string](Get-RequiredProperty $payload 'path' 'input_lock.leaf_jobs[].payloads[]')) `
                'input_lock.leaf_jobs[].payloads[].path'
            if (-not $seenPayloads.Add($payloadPath)) {
                throw "Payload leaf verrouillé dupliqué : $payloadPath"
            }
            $rawPayloadBytes = Get-RequiredProperty $payload 'bytes' `
                'input_lock.leaf_jobs[].payloads[]'
            if ($rawPayloadBytes -isnot [int] -and $rawPayloadBytes -isnot [long]) {
                throw 'input_lock.leaf_jobs[].payloads[].bytes doit être un entier JSON.'
            }
            $payloadBytes = [uint64]$rawPayloadBytes
            if ($payloadBytes -eq 0) { throw 'Payload leaf verrouillé vide.' }
            $rawPayloadCrc32 = Get-RequiredProperty $payload 'crc32' `
                'input_lock.leaf_jobs[].payloads[]'
            if (($rawPayloadCrc32 -isnot [int] -and $rawPayloadCrc32 -isnot [long]) -or
                [long]$rawPayloadCrc32 -lt 0 -or [long]$rawPayloadCrc32 -gt [uint32]::MaxValue) {
                throw 'input_lock.leaf_jobs[].payloads[].crc32 doit être un uint32 JSON.'
            }
            Assert-ExpectedHash $payloadPath `
                ([string](Get-RequiredProperty $payload 'sha256' 'input_lock.leaf_jobs[].payloads[]')) `
                'Payload leaf verrouillé'
            if ((Get-Crc32 $payloadPath) -ne [uint32]$rawPayloadCrc32) {
                throw "CRC32 du payload leaf verrouillé incompatible : $payloadPath"
            }
            if ([uint64](Get-Item -LiteralPath $payloadPath).Length -ne $payloadBytes) {
                throw "Taille du payload leaf verrouillé incompatible : $payloadPath"
            }
        }
    }
    $actualLockSha256 = Get-CanonicalJsonSha256 $inputLock
    Assert-OrdinalEqual $actualLockSha256 `
        ([string](Get-RequiredProperty $locks 'input_lock_sha256' 'build.locks')) 'build.locks.input_lock_sha256'
    Assert-OrdinalEqual $actualLockSha256 $GenerationId 'generation_id/input_lock_sha256'
}

function Assert-CatalogManifest($Build, $Catalog, [string]$BuildRoot) {
    $declaredShardVersion = if ($null -ne $Build.PSObject.Properties['registry_catalog_shard_version']) {
        [uint32]$Build.registry_catalog_shard_version
    } elseif ($Catalog.version -eq 1) { [uint32]3 } else {
        throw 'build.registry_catalog_shard_version absent pour un catalogue V2.'
    }
    if ($declaredShardVersion -notin @(3, 5) -or
        ($Catalog.version -eq 1 -and $declaredShardVersion -ne 3) -or
        ($declaredShardVersion -eq 5 -and $Catalog.version -ne 2)) {
        throw 'Couplage build catalogue/shard incompatible.'
    }
    $declaredFrameStorage = if ($declaredShardVersion -eq 5) {
        [string](Get-RequiredProperty $Build 'registry_catalog_frame_storage' 'build')
    } elseif ($null -ne $Build.PSObject.Properties['registry_catalog_frame_storage']) {
        [string]$Build.registry_catalog_frame_storage
    } else { 'raw-v3' }
    if (($declaredShardVersion -eq 5 -and
         $declaredFrameStorage -cne 'XPRESS_HUFF-or-raw-per-frame-v1') -or
        ($declaredShardVersion -eq 3 -and $declaredFrameStorage -cne 'raw-v3')) {
        throw 'build.registry_catalog_frame_storage incompatible.'
    }
    $animationIds = @(Get-RequiredProperty $Build 'animation_ids' 'build')
    if ($animationIds.Count -ne $Catalog.animation_count) { throw 'build.animation_ids count incompatible.' }
    for ($i = 0; $i -lt $animationIds.Count; $i++) {
        if ((Convert-AnimationId $animationIds[$i] "build.animation_ids[$i]") -ne
            $Catalog.animations[$i].animation_id) {
            throw "build.animation_ids[$i] diffère du catalogue."
        }
    }
    $expectedProfiles = @($Catalog.animations | ForEach-Object { Get-OwnerRuntimeProfile $_.owner } |
        Sort-Object -Unique)
    Assert-ExactStringSet (Get-RequiredProperty $Build 'runtime_profiles' 'build') $expectedProfiles `
        'build.runtime_profiles'

    $manifestAnimations = @(Get-RequiredProperty $Build 'animations' 'build')
    if ($manifestAnimations.Count -ne $Catalog.animation_count) { throw 'build.animations count incompatible.' }
    for ($i = 0; $i -lt $manifestAnimations.Count; $i++) {
        $manifest = $manifestAnimations[$i]; $binary = $Catalog.animations[$i]
        if ((Convert-AnimationId (Get-RequiredProperty $manifest 'animation_id' 'build.animations[]') `
                "build.animations[$i].animation_id") -ne $binary.animation_id -or
            (Convert-Owner (Get-RequiredProperty $manifest 'owner' 'build.animations[]') `
                "build.animations[$i].owner") -ne $binary.owner -or
            -not [string]::Equals([string](Get-RequiredProperty $manifest 'runtime_profile' 'build.animations[]'),
                (Get-OwnerRuntimeProfile $binary.owner), [System.StringComparison]::Ordinal)) {
            throw "build.animations[$i] incompatible."
        }
        $indices = @(Get-RequiredProperty $manifest 'component_indices' 'build.animations[]')
        if ($indices.Count -ne $binary.component_indices.Count) { throw "Membership manifest incompatible : $i" }
        for ($j = 0; $j -lt $indices.Count; $j++) {
            if ([int]$indices[$j] -ne [int]$binary.component_indices[$j]) {
                throw "Membership manifest incompatible : $i/$j"
            }
        }
    }

    $manifestComponents = @(Get-RequiredProperty $Build 'components' 'build')
    if ($manifestComponents.Count -ne $Catalog.component_count) { throw 'build.components count incompatible.' }
    for ($i = 0; $i -lt $manifestComponents.Count; $i++) {
        $manifest = $manifestComponents[$i]; $binary = $Catalog.components[$i]
        if ([int](Get-RequiredProperty $manifest 'index' 'build.components[]') -ne $i -or
            -not [string]::Equals([string](Get-RequiredProperty $manifest 'digest' 'build.components[]'),
                $binary.digest, [System.StringComparison]::Ordinal) -or
            [uint32](Get-RequiredProperty $manifest 'shard_start' 'build.components[]') -ne $binary.shard_start -or
            [uint32](Get-RequiredProperty $manifest 'shard_count' 'build.components[]') -ne $binary.shard_count -or
            [uint32](Get-RequiredProperty $manifest 'resource_count' 'build.components[]') -ne $binary.resource_count -or
            [uint64](Get-RequiredProperty $manifest 'frame_count' 'build.components[]') -ne $binary.frame_count -or
            [uint64](Get-RequiredProperty $manifest 'index_bytes' 'build.components[]') -ne $binary.index_bytes -or
            [uint64](Get-RequiredProperty $manifest 'registry_bytes' 'build.components[]') -ne $binary.registry_bytes) {
            throw "build.components[$i] incompatible."
        }
    }

    $manifestShards = @(Get-RequiredProperty $Build 'shards' 'build')
    if ($manifestShards.Count -ne $Catalog.shard_count) { throw 'build.shards count incompatible.' }
    $allResources = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    $resourcesByShard = @()
    $resolvedShards = @()
    for ($i = 0; $i -lt $manifestShards.Count; $i++) {
        $manifest = $manifestShards[$i]; $binary = $Catalog.shards[$i]
        $expectedRelative = "iee-assets/creature-sprites/CreatureSprites-XN-$($binary.sha256).registry"
        $relative = ([string](Get-RequiredProperty $manifest 'registry' 'build.shards[]')).Replace('\', '/')
        if ([int](Get-RequiredProperty $manifest 'index' 'build.shards[]') -ne $i -or
            -not [string]::Equals($relative, $expectedRelative, [System.StringComparison]::Ordinal) -or
            -not [string]::Equals([string](Get-RequiredProperty $manifest 'sha256' 'build.shards[]'),
                $binary.sha256, [System.StringComparison]::Ordinal) -or
            [uint32](Get-RequiredProperty $manifest 'crc32' 'build.shards[]') -ne $binary.crc32 -or
            [uint32](Get-RequiredProperty $manifest 'resource_count' 'build.shards[]') -ne $binary.resource_count -or
            [uint64](Get-RequiredProperty $manifest 'frame_count' 'build.shards[]') -ne $binary.frame_count -or
            [uint64](Get-RequiredProperty $manifest 'index_bytes' 'build.shards[]') -ne $binary.index_bytes -or
            [uint64](Get-RequiredProperty $manifest 'registry_bytes' 'build.shards[]') -ne $binary.registry_bytes) {
            throw "build.shards[$i] incompatible."
        }
        $path = Resolve-ChildPath $BuildRoot $relative "build.shards[$i].registry"
        Assert-ExpectedHash $path $binary.sha256 "Shard source $i"
        if ((Get-Crc32 $path) -ne $binary.crc32) { throw "CRC32 source incompatible : shard $i" }
        $registry = Read-CatalogShard $path
        if ($registry.version -ne $declaredShardVersion -or
            $registry.scale -ne $Catalog.scale -or $registry.resource_count -ne $binary.resource_count -or
            $registry.frame_count -ne $binary.frame_count -or $registry.index_bytes -ne $binary.index_bytes -or
            $registry.registry_bytes -ne $binary.registry_bytes) {
            throw "En-tête/compteurs source incompatibles : shard $i"
        }
        foreach ($resource in $registry.resources) { [void]$allResources.Add($resource) }
        $resourcesByShard += ,@($registry.resources)
        $resolvedShards += [pscustomobject]@{
            index = $i; relative_path = $relative.Replace('/', '\'); source_path = $path
            sha256 = $binary.sha256; crc32 = $binary.crc32; resources = $registry.resources
            registry_info = $registry
        }
    }
    $logicalIdentity = Get-CatalogLogicalIdentity $Catalog $resolvedShards
    if ($logicalIdentity.shard_registry_version -ne $declaredShardVersion -or
        $logicalIdentity.frame_storage -cne $declaredFrameStorage) {
        throw 'Identité logique et stockage déclaré du build divergent.'
    }
    $manifestLogicalComponents = @(
        if ($null -ne $Build.PSObject.Properties['registry_catalog_logical_component_digests']) {
            $Build.registry_catalog_logical_component_digests | ForEach-Object {
                ([string]$_).ToUpperInvariant()
            }
        }
    )
    if ($declaredShardVersion -eq 5 -or $manifestLogicalComponents.Count -gt 0) {
        if (($manifestLogicalComponents -join '|') -cne
                (@($logicalIdentity.logical_component_digests) -join '|') -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $Build 'registry_catalog_logical_content_sha256' 'build'),
                [string]$logicalIdentity.logical_content_sha256,
                [System.StringComparison]::Ordinal)) {
            throw 'Digests logiques recalculés du build incompatibles.'
        }
    }
    if ($declaredShardVersion -eq 5) {
        $storage = Get-RequiredProperty $Build 'storage' 'build'
        if ([uint32](Get-RequiredProperty $storage 'shard_registry_version' 'build.storage') -ne 5 -or
            [string](Get-RequiredProperty $storage 'frame_storage' 'build.storage') -cne
                'XPRESS_HUFF-or-raw-per-frame-v1' -or
            [uint64](Get-RequiredProperty $storage 'stored_index_bytes' 'build.storage') -ne
                $logicalIdentity.stored_index_bytes -or
            [uint64](Get-RequiredProperty $storage 'compressed_frame_count' 'build.storage') -ne
                $logicalIdentity.compressed_frame_count -or
            [uint64](Get-RequiredProperty $storage 'raw_frame_count' 'build.storage') -ne
                $logicalIdentity.raw_frame_count -or
            [Math]::Abs([double](Get-RequiredProperty $storage 'index_storage_ratio' 'build.storage') -
                [double]$logicalIdentity.index_storage_ratio) -gt 0.000000000001) {
            throw 'build.storage diffère des shards V5 recalculés.'
        }
        if ([uint64](Get-RequiredProperty $Build.validation 'resource_records_sha256_verified' `
                'build.validation') -ne [uint64]$Catalog.total_resources) {
            throw 'Le compteur de records logiques vérifiés diffère du catalogue.'
        }
    }
    for ($componentIndex = 0; $componentIndex -lt $Catalog.component_count; $componentIndex++) {
        $component = $Catalog.components[$componentIndex]
        $componentSet = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::OrdinalIgnoreCase)
        for ($local = 0; $local -lt $component.shard_count; $local++) {
            foreach ($resource in $resourcesByShard[[int]$component.shard_start + $local]) {
                if (-not $componentSet.Add([string]$resource)) {
                    throw "Resref dupliqué dans le composant $componentIndex : $resource"
                }
            }
        }
    }
    foreach ($animation in $Catalog.animations) {
        $animationSet = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::OrdinalIgnoreCase)
        foreach ($componentIndex in $animation.component_indices) {
            $component = $Catalog.components[[int]$componentIndex]
            for ($local = 0; $local -lt $component.shard_count; $local++) {
                foreach ($resource in $resourcesByShard[[int]$component.shard_start + $local]) {
                    if (-not $animationSet.Add([string]$resource)) {
                        throw "Resref dupliqué dans l'animation $(Format-AnimationId $animation.animation_id) : $resource"
                    }
                }
            }
        }
    }
    if ($Catalog.version -eq 2) {
        if ([uint32](Get-RequiredProperty $Build 'registry_catalog_directory_count' 'build') -ne
                $Catalog.directory_count -or
            [uint32](Get-RequiredProperty $Build 'registry_catalog_directory_entry_bytes' 'build') -ne 24 -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $Build 'registry_catalog_directory_sha256' 'build'),
                [string]$Catalog.directory_sha256, [System.StringComparison]::Ordinal)) {
            throw 'Métadonnées directory V2 du build incompatibles.'
        }
        $expectedDirectory = [System.Collections.Generic.Dictionary[string,string]]::new(
            [System.StringComparer]::Ordinal)
        foreach ($animation in $Catalog.animations) {
            foreach ($componentIndex in $animation.component_indices) {
                $component = $Catalog.components[[int]$componentIndex]
                for ($local = 0; $local -lt $component.shard_count; $local++) {
                    $shardIndex = [int]$component.shard_start + $local
                    $resources = @($resourcesByShard[$shardIndex])
                    for ($ordinal = 0; $ordinal -lt $resources.Count; $ordinal++) {
                        $resref = [string]$resources[$ordinal]
                        $key = ('{0:D10}|{1}' -f [uint32]$animation.animation_id, $resref)
                        $value = ('{0}|{1}|{2}' -f [uint32]$componentIndex, [uint32]$shardIndex,
                            [uint32]$ordinal)
                        if ($expectedDirectory.ContainsKey($key)) {
                            throw "Mapping directory attendu dupliqué : $key"
                        }
                        $expectedDirectory.Add($key, $value)
                    }
                }
            }
        }
        if ($expectedDirectory.Count -ne $Catalog.directory_count -or
            @($Catalog.directory).Count -ne $Catalog.directory_count) {
            throw 'La directory V2 ne couvre pas exactement les ressources des animations.'
        }
        foreach ($entry in $Catalog.directory) {
            $key = ('{0:D10}|{1}' -f [uint32]$entry.animation_id, [string]$entry.resref)
            $value = ('{0}|{1}|{2}' -f [uint32]$entry.component_index, [uint32]$entry.shard_index,
                [uint32]$entry.resource_ordinal)
            if (-not $expectedDirectory.ContainsKey($key) -or
                $expectedDirectory[$key] -cne $value -or
                [string]$resourcesByShard[[int]$entry.shard_index][[int]$entry.resource_ordinal] -cne
                    [string]$entry.resref) {
                throw "Entrée directory V2 divergente : $key"
            }
        }
    } elseif ($Catalog.directory_count -ne 0 -or @($Catalog.directory).Count -ne 0) {
        throw 'Un catalogue V1 ne peut pas déclarer de directory.'
    }
    $totals = Get-RequiredProperty $Build 'totals' 'build'
    foreach ($name in @('total_resources', 'total_frames', 'total_index_bytes', 'total_registry_bytes')) {
        $expected = [uint64]$Catalog.$name
        if ([uint64](Get-RequiredProperty $totals $name 'build.totals') -ne $expected) {
            throw "build.totals.$name diffère du catalogue."
        }
    }
    $expectedShardNames = @($resolvedShards | ForEach-Object { Split-Path -Leaf $_.relative_path } | Sort-Object)
    $spriteRoot = Join-Path $BuildRoot 'iee-assets\creature-sprites'
    $actualShardNames = @(Get-ChildItem -LiteralPath $spriteRoot -File -ErrorAction Stop |
        Where-Object { $_.Name -match '^CreatureSprites-XN-[0-9A-F]{64}\.registry$' } |
        ForEach-Object { $_.Name } | Sort-Object)
    if (($actualShardNames -join '|') -cne ($expectedShardNames -join '|')) {
        throw 'Le dossier build contient des shards catalogue non déclarés ou en omet.'
    }
    return [pscustomobject]@{
        shards = $resolvedShards; resources = @($allResources | ForEach-Object { $_ })
        logical_identity = $logicalIdentity
    }
}

function Assert-GameChildRelative([string]$GameRoot, [string]$Relative, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or [System.IO.Path]::IsPathRooted($Relative)) {
        throw "$Label doit être relatif au jeu."
    }
    $root = [System.IO.Path]::GetFullPath($GameRoot).TrimEnd('\')
    $full = [System.IO.Path]::GetFullPath((Join-Path $root ($Relative.Replace('/', '\'))))
    if (-not $full.StartsWith($root + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label sort du GameRoot."
    }
    Assert-NoReparseComponents $root $full $Label
    return $full
}

function Assert-LiveStateTargets($State, [string]$GameRoot, [switch]$AllowInterrupted) {
    $targets = @(Get-RequiredProperty $State 'targets' 'active state')
    if ($targets.Count -lt 1 -or $targets.Count -gt 32772) { throw 'active state.targets hors limites.' }
    $seen = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($targetState in $targets) {
        $relative = ([string](Get-RequiredProperty $targetState 'relative_path' 'active state.targets[]')).Replace('/', '\')
        if (-not $seen.Add($relative)) { throw "Cible d'état dupliquée : $relative" }
        $target = Assert-GameChildRelative $GameRoot $relative 'active state.targets[].relative_path'
        if ($AllowInterrupted) { continue }
        $installedPresent = Get-RequiredProperty $targetState 'installed_present' 'active state.targets[]'
        Assert-Boolean $installedPresent 'active state.targets[].installed_present'
        $present = Test-Path -LiteralPath $target -PathType Leaf
        if ([bool]$installedPresent -ne $present) { throw "Présence live divergente : $relative" }
        if ($present) {
            $installedHash = [string](Get-RequiredProperty $targetState 'installed_sha256' 'active state.targets[]')
            Assert-HashText $installedHash 'active state.targets[].installed_sha256'
            $actualHash = Get-Sha256 $target
            if (-not [string]::Equals($actualHash, $installedHash,
                    [System.StringComparison]::OrdinalIgnoreCase)) {
                if ([string]$targetState.role -eq 'runtime-ini') {
                    Assert-CatalogIniOwnedContract (Get-Content -LiteralPath $target -Raw)
                } else {
                    throw "Cible live $relative altéré : SHA-256 $actualHash, attendu $installedHash."
                }
            }
        } elseif ($null -ne $targetState.PSObject.Properties['installed_sha256'] -and
            $null -ne $targetState.installed_sha256) {
            throw "Hash installed inattendu pour une cible absente : $relative"
        }
    }
    return $targets
}

function Assert-CatalogIniOwnedContract([string]$Text) {
    if ((Get-IniKey $Text 'Shaders' 'EnableCreatureSpriteUpscaleTest') -cne 'true' -or
        (Get-IniKey $Text 'Shaders' 'EnableCreatureSpriteX2Test') -cne 'false' -or
        (Get-IniKey $Text 'Shaders' 'EnableCreatureSpriteLinearFiltering') -cne 'false') {
        throw 'Les trois clés INI catalogue ne sont pas exactes.'
    }
}

function Get-ActiveSpriteStates([string]$OwnStatePath, [string]$GameRoot) {
    $states = @()
    foreach ($scanRoot in @((Join-Path $script:WorkspaceRoot 'proto'), (Join-Path $script:WorkspaceRoot 'sprite'))) {
        if (-not (Test-Path -LiteralPath $scanRoot -PathType Container)) { continue }
        foreach ($candidate in Get-ChildItem -LiteralPath $scanRoot -Filter 'active-test.json' -File -Recurse -ErrorAction Stop) {
            Assert-NoReparseComponents $scanRoot $candidate.FullName 'État sprite découvert'
            if ([string]::Equals($candidate.FullName, $OwnStatePath, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
            try { $candidateState = Get-Content -LiteralPath $candidate.FullName -Raw | ConvertFrom-Json }
            catch { throw "État sprite illisible : $($candidate.FullName) : $($_.Exception.Message)" }
            if ([string](Get-RequiredProperty $candidateState 'status' 'sprite state') -notin @(
                    'installing', 'restoring', 'installed-pending-qa', 'validated-installed', 'qa-failed')) {
                continue
            }
            $candidateGame = [string](Get-RequiredProperty $candidateState 'game_root' 'sprite state')
            if ([string]::Equals([System.IO.Path]::GetFullPath($candidateGame).TrimEnd('\'),
                    [System.IO.Path]::GetFullPath($GameRoot).TrimEnd('\'),
                    [System.StringComparison]::OrdinalIgnoreCase)) {
                $states += [pscustomobject]@{ path = $candidate.FullName; state = $candidateState }
            }
        }
    }
    return $states
}

function Get-DeclaredParentStateRecords([string]$TopPath, $TopState, [string]$GameRoot,
        $Candidates) {
    $candidateByPath = @{}
    foreach ($candidate in @($Candidates)) {
        $candidateByPath[[System.IO.Path]::GetFullPath([string]$candidate.path).ToUpperInvariant()] = $candidate
    }
    $visited = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    [void]$visited.Add([System.IO.Path]::GetFullPath($TopPath))
    $queue = [System.Collections.Generic.Queue[object]]::new()
    $queue.Enqueue([pscustomobject]@{ path = $TopPath; state = $TopState })
    $records = @()
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        $declaredParents = @()
        if ($null -ne $current.state.PSObject.Properties['parent_active_tests'] -and
            $null -ne $current.state.parent_active_tests) {
            $declaredParents = @($current.state.parent_active_tests)
        }
        foreach ($declared in $declaredParents) {
            $parentPath = Resolve-ProjectPath `
                ([string](Get-RequiredProperty $declared 'state_path' 'parent_active_tests[]')) `
                'parent_active_tests[].state_path'
            if (-not $visited.Add($parentPath)) { throw "Cycle ou parent dupliqué : $parentPath" }
            $key = [System.IO.Path]::GetFullPath($parentPath).ToUpperInvariant()
            if (-not $candidateByPath.ContainsKey($key)) {
                throw "Parent déclaré absent des états actifs : $parentPath"
            }
            $parentState = $candidateByPath[$key].state
            $declaredJobId = [string](Get-RequiredProperty $declared 'job_id' 'parent_active_tests[]')
            $declaredStatus = [string](Get-RequiredProperty $declared 'status' 'parent_active_tests[]')
            Assert-OrdinalEqual ([string](Get-RequiredProperty $parentState 'job_id' 'parent state')) `
                $declaredJobId 'parent state.job_id'
            Assert-OrdinalEqual ([string](Get-RequiredProperty $parentState 'status' 'parent state')) `
                $declaredStatus 'parent state.status'
            if ($declaredStatus -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
                throw "Statut parent non importable : $declaredStatus"
            }
            if (-not [string]::Equals([string](Get-RequiredProperty $parentState 'game_root' 'parent state'),
                    $GameRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "GameRoot parent incompatible : $parentPath"
            }
            $parentJobPath = Resolve-ProjectPath `
                ([string](Get-RequiredProperty $parentState 'job_file' 'parent state')) 'parent state.job_file'
            $parentJob = Get-Content -LiteralPath $parentJobPath -Raw | ConvertFrom-Json
            Assert-OrdinalEqual ([string](Get-RequiredProperty $parentJob 'job_id' 'parent job')) `
                $declaredJobId 'parent job.job_id'
            $record = [pscustomobject]@{
                path = $parentPath; relative_path = Get-ProjectRelativePath $parentPath
                job_id = $declaredJobId; sha256 = Get-Sha256 $parentPath
                schema = [string](Get-RequiredProperty $parentState 'schema' 'parent state')
                status = $declaredStatus
            }
            $records += $record
            $queue.Enqueue([pscustomobject]@{ path = $parentPath; state = $parentState })
        }
    }
    foreach ($candidate in @($Candidates)) {
        if (-not $visited.Contains([string]$candidate.path)) {
            throw "État actif hors chaîne parent_active_tests : $($candidate.path)"
        }
    }
    return $records
}

function Get-ImportRecord($Job, [string]$OwnStatePath, [string]$GameRoot, $PreviousState) {
    $candidates = @(Get-ActiveSpriteStates $OwnStatePath $GameRoot)
    if ($null -ne $PreviousState) {
        $record = $null
        if ($null -ne $PreviousState.PSObject.Properties['imported_active_state'] -and
            $null -ne $PreviousState.imported_active_state) {
            $record = $PreviousState.imported_active_state
        }
        $recordedStates = @()
        if ($null -ne $record) {
            $recordedStates += $record
            if ($null -ne $record.PSObject.Properties['parents'] -and $null -ne $record.parents) {
                $recordedStates += @($record.parents)
            }
        }
        if ($candidates.Count -ne $recordedStates.Count) {
            throw "La chaîne d'états importés enregistrée a changé."
        }
        foreach ($recorded in $recordedStates) {
            $recordedPath = Resolve-ProjectPath ([string]$recorded.path) `
                'imported_active_state.path'
            $matches = @($candidates | Where-Object {
                [string]::Equals([System.IO.Path]::GetFullPath([string]$_.path),
                    [System.IO.Path]::GetFullPath($recordedPath),
                    [System.StringComparison]::OrdinalIgnoreCase)
            })
            if ($matches.Count -ne 1) { throw "État importé enregistré absent : $($recorded.path)" }
            Assert-ExpectedHash $matches[0].path ([string]$recorded.sha256) 'État actif importé'
            Assert-OrdinalEqual ([string]$matches[0].state.job_id) ([string]$recorded.job_id) `
                'État actif importé job_id'
            Assert-OrdinalEqual ([string]$matches[0].state.status) ([string]$recorded.status) `
                'État actif importé status'
        }
        return $record
    }

    $configured = $null
    if ($null -ne $Job.PSObject.Properties['installation'] -and
        $null -ne $Job.installation -and
        $null -ne $Job.installation.PSObject.Properties['import_active_state'] -and
        $null -ne $Job.installation.import_active_state) {
        $configured = $Job.installation.import_active_state
    }
    if ($null -ne $configured) {
        Assert-ExactPropertyNames $configured @('state_path', 'job_id') `
            'job.installation.import_active_state'
    }
    if ($candidates.Count -eq 0) {
        if ($null -ne $configured) { throw 'installation.import_active_state est configuré sans état actif à migrer.' }
        return $null
    }
    if ($null -eq $configured) {
        throw 'La première installation catalogue exige installation.import_active_state explicite.'
    }
    $configuredPath = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $configured 'state_path' 'job.installation.import_active_state')) `
        'job.installation.import_active_state.state_path'
    $configuredJobId = [string](Get-RequiredProperty $configured 'job_id' 'job.installation.import_active_state')
    $candidateMatches = @($candidates | Where-Object {
        [string]::Equals([System.IO.Path]::GetFullPath([string]$_.path), $configuredPath,
            [System.StringComparison]::OrdinalIgnoreCase)
    })
    if ($candidateMatches.Count -ne 1) {
        throw 'installation.import_active_state ne désigne pas un unique état top actif.'
    }
    $candidate = $candidateMatches[0]
    if (
        -not [string]::Equals([string](Get-RequiredProperty $candidate.state 'job_id' 'imported state'),
            $configuredJobId, [System.StringComparison]::Ordinal)) {
        throw "installation.import_active_state ne correspond pas exactement à l'état actif."
    }
    if ([string]$candidate.state.status -in @('installing', 'restoring')) {
        throw "L'état à importer est interrompu : $($candidate.state.status)"
    }
    if (-not [string]::Equals([string]$candidate.state.game_root, $GameRoot,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Le GameRoot de l'état importé diffère."
    }
    [void](Assert-LiveStateTargets $candidate.state $GameRoot)
    $topJobPath = Resolve-ProjectPath ([string](Get-RequiredProperty $candidate.state 'job_file' 'imported state')) `
        'imported state.job_file'
    $topJob = Get-Content -LiteralPath $topJobPath -Raw | ConvertFrom-Json
    Assert-OrdinalEqual ([string](Get-RequiredProperty $topJob 'job_id' 'imported top job')) `
        $configuredJobId 'imported top job.job_id'
    $parents = @(Get-DeclaredParentStateRecords $candidate.path $candidate.state $GameRoot $candidates)
    return [pscustomobject]@{
        path = $candidate.path
        relative_path = Get-ProjectRelativePath $candidate.path
        job_id = $configuredJobId
        sha256 = Get-Sha256 $candidate.path
        schema = [string](Get-RequiredProperty $candidate.state 'schema' 'imported state')
        status = [string]$candidate.state.status
        parents = $parents
    }
}

function Assert-CatalogSuperset($Old, $New) {
    if ($Old.scale -ne $New.scale) { throw "Le nouveau catalogue change l'échelle active." }
    if ($Old.version -ne $New.version) {
        throw "Un append ne peut pas changer la version du catalogue actif. Effectuer d'abord une migration de contenu identique."
    }
    if ($Old.shard_registry_version -ne $New.shard_registry_version) {
        throw "Un append ne peut pas changer la version de stockage des shards actifs."
    }
    $newComponents = @{}
    foreach ($component in $New.components) { $newComponents[$component.digest] = $component }
    foreach ($oldComponent in $Old.components) {
        if (-not $newComponents.ContainsKey($oldComponent.digest)) {
            throw "Composant actif supprimé : $($oldComponent.digest)"
        }
        $newComponent = $newComponents[$oldComponent.digest]
        if ($oldComponent.resource_count -ne $newComponent.resource_count -or
            $oldComponent.frame_count -ne $newComponent.frame_count -or
            $oldComponent.index_bytes -ne $newComponent.index_bytes -or
            $oldComponent.registry_bytes -ne $newComponent.registry_bytes -or
            $oldComponent.shard_count -ne $newComponent.shard_count) {
            throw "Composant actif modifié : $($oldComponent.digest)"
        }
        for ($i = 0; $i -lt $oldComponent.shard_count; $i++) {
            $oldShard = $Old.shards[[int]$oldComponent.shard_start + $i]
            $newShard = $New.shards[[int]$newComponent.shard_start + $i]
            if ($oldShard.sha256 -cne $newShard.sha256 -or $oldShard.crc32 -ne $newShard.crc32 -or
                $oldShard.resource_count -ne $newShard.resource_count -or
                $oldShard.frame_count -ne $newShard.frame_count -or
                $oldShard.index_bytes -ne $newShard.index_bytes -or
                $oldShard.registry_bytes -ne $newShard.registry_bytes) {
                throw "Shards du composant actif modifiés : $($oldComponent.digest)"
            }
        }
    }
    $newAnimations = @{}
    foreach ($animation in $New.animations) { $newAnimations[[string]$animation.animation_id] = $animation }
    foreach ($oldAnimation in $Old.animations) {
        if (-not $newAnimations.ContainsKey([string]$oldAnimation.animation_id)) {
            throw "Animation active supprimée : $(Format-AnimationId $oldAnimation.animation_id)"
        }
        $newAnimation = $newAnimations[[string]$oldAnimation.animation_id]
        if ($oldAnimation.owner -ne $newAnimation.owner) {
            throw "Animation active modifiée : $(Format-AnimationId $oldAnimation.animation_id)"
        }
        $newDigestSet = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal)
        foreach ($digest in $newAnimation.component_digests) { [void]$newDigestSet.Add([string]$digest) }
        foreach ($digest in $oldAnimation.component_digests) {
            if (-not $newDigestSet.Contains([string]$digest)) {
                throw "Mapping actif supprimé : $(Format-AnimationId $oldAnimation.animation_id)/$digest"
            }
        }
    }
    if ($New.membership_count -le $Old.membership_count) {
        throw "Le catalogue proposé n'est pas un strict superset du catalogue actif."
    }
}

function Assert-CatalogSemanticIdentity($Old, $New) {
    if ($Old.scale -ne $New.scale) { throw "Le runtime-refresh change l'échelle active." }
    if ($Old.version -eq 2 -and $New.version -eq 1) {
        throw 'Le runtime-refresh refuse une rétrogradation catalogue V2 vers V1.'
    }
    if ($Old.version -notin @(1, 2) -or $New.version -notin @(1, 2) -or
        ($Old.version -ne $New.version -and -not ($Old.version -eq 1 -and $New.version -eq 2))) {
        throw 'Transition de version catalogue non autorisée pour runtime-refresh.'
    }
    $storageRepack = $Old.version -eq 1 -and $Old.shard_registry_version -eq 3 -and
        $New.version -eq 2 -and $New.shard_registry_version -eq 5
    if (-not $storageRepack -and $Old.shard_registry_version -ne $New.shard_registry_version) {
        throw 'Transition de version shard non autorisée pour runtime-refresh.'
    }
    foreach ($field in @(
            'animation_count', 'component_count', 'membership_count',
            'total_resources', 'total_frames', 'total_index_bytes')) {
        if ($Old.$field -ne $New.$field) {
            throw "Le runtime-refresh modifie le compteur catalogue $field."
        }
    }
    if (@($Old.logical_component_digests).Count -ne $Old.component_count -or
        @($New.logical_component_digests).Count -ne $New.component_count -or
        (@($Old.logical_component_digests) -join '|') -cne
            (@($New.logical_component_digests) -join '|') -or
        [string]$Old.logical_content_sha256 -cne [string]$New.logical_content_sha256) {
        throw 'Le runtime-refresh/storage-repack modifie le contenu logique recalculé.'
    }

    if ($storageRepack) {
        for ($index = 0; $index -lt $Old.animations.Count; $index++) {
            $oldAnimation = $Old.animations[$index]
            $newAnimation = $New.animations[$index]
            if ($oldAnimation.animation_id -ne $newAnimation.animation_id -or
                $oldAnimation.owner -ne $newAnimation.owner -or
                (@($oldAnimation.component_indices) -join '|') -cne
                    (@($newAnimation.component_indices) -join '|')) {
                throw 'Le storage-repack modifie un mapping animation logique.'
            }
        }
        return 'storage-repack'
    }

    foreach ($field in @('shard_count', 'total_registry_bytes')) {
        if ($Old.$field -ne $New.$field) {
            throw "Le runtime-refresh modifie le compteur physique catalogue $field."
        }
    }

    $newComponents = @{}
    foreach ($component in $New.components) {
        if ($newComponents.ContainsKey([string]$component.digest)) {
            throw "Composant dupliqué dans le nouveau catalogue : $($component.digest)"
        }
        $newComponents[[string]$component.digest] = $component
    }
    if ($newComponents.Count -ne $Old.components.Count) {
        throw 'Le runtime-refresh modifie ensemble des composants.'
    }
    foreach ($oldComponent in $Old.components) {
        $digest = [string]$oldComponent.digest
        if (-not $newComponents.ContainsKey($digest)) {
            throw "Le runtime-refresh retire ou remplace le composant $digest."
        }
        $newComponent = $newComponents[$digest]
        foreach ($field in @('shard_count', 'resource_count', 'frame_count', 'index_bytes', 'registry_bytes')) {
            if ($oldComponent.$field -ne $newComponent.$field) {
                throw "Le runtime-refresh modifie $field pour le composant $digest."
            }
        }
        for ($i = 0; $i -lt $oldComponent.shard_count; $i++) {
            $oldShard = $Old.shards[[int]$oldComponent.shard_start + $i]
            $newShard = $New.shards[[int]$newComponent.shard_start + $i]
            foreach ($field in @('sha256', 'crc32', 'resource_count', 'frame_count', 'index_bytes', 'registry_bytes')) {
                if ([string]$field -ceq 'sha256') {
                    if ([string]$oldShard.$field -cne [string]$newShard.$field) {
                        throw "Le runtime-refresh remplace un shard du composant $digest."
                    }
                } elseif ($oldShard.$field -ne $newShard.$field) {
                    throw "Le runtime-refresh modifie $field pour un shard du composant $digest."
                }
            }
        }
    }

    $newAnimations = @{}
    foreach ($animation in $New.animations) {
        $key = [string]$animation.animation_id
        if ($newAnimations.ContainsKey($key)) { throw "Animation dupliquée : $key" }
        $newAnimations[$key] = $animation
    }
    if ($newAnimations.Count -ne $Old.animations.Count) {
        throw 'Le runtime-refresh modifie ensemble des animations.'
    }
    foreach ($oldAnimation in $Old.animations) {
        $key = [string]$oldAnimation.animation_id
        if (-not $newAnimations.ContainsKey($key)) {
            throw "Le runtime-refresh retire l'animation $(Format-AnimationId $oldAnimation.animation_id)."
        }
        $newAnimation = $newAnimations[$key]
        if ($oldAnimation.owner -ne $newAnimation.owner -or
            (@($oldAnimation.component_digests) -join '|') -cne
                (@($newAnimation.component_digests) -join '|')) {
            throw "Le runtime-refresh modifie les mappings de l'animation $(Format-AnimationId $oldAnimation.animation_id)."
        }
    }
    return 'runtime-refresh'
}

function Assert-SourceMembersSemanticIdentity($OldBuild, $NewBuild) {
    $oldMembers = @(Get-RequiredProperty $OldBuild 'source_members' 'historical build')
    $newMembers = @(Get-RequiredProperty $NewBuild 'source_members' 'build')
    if ($oldMembers.Count -lt 1 -or $oldMembers.Count -ne $newMembers.Count -or
        (ConvertTo-CanonicalJson $oldMembers) -cne (ConvertTo-CanonicalJson $newMembers)) {
        throw 'Le storage-repack modifie build.source_members ou sa provenance scellée.'
    }
}

function Get-LiveCatalogLogicalIdentity($Catalog, [string]$GameRoot) {
    $resolved = @()
    foreach ($shard in $Catalog.shards) {
        $relative = "iee-assets\creature-sprites\CreatureSprites-XN-$($shard.sha256).registry"
        $path = Assert-GameChildRelative $GameRoot $relative 'Shard catalogue live'
        Assert-ExpectedHash $path $shard.sha256 "Shard catalogue live $($shard.index)"
        if ((Get-Crc32 $path) -ne [uint32]$shard.crc32) {
            throw "CRC32 shard catalogue live divergent : $($shard.index)"
        }
        $info = Read-CatalogShard $path
        if ($info.scale -ne $Catalog.scale -or
            $info.resource_count -ne $shard.resource_count -or
            $info.frame_count -ne $shard.frame_count -or
            $info.index_bytes -ne $shard.index_bytes -or
            $info.registry_bytes -ne $shard.registry_bytes) {
            throw "Compteurs shard catalogue live divergents : $($shard.index)"
        }
        $resolved += [pscustomobject]@{
            index = $shard.index; relative_path = $relative; source_path = $path
            sha256 = $shard.sha256; crc32 = $shard.crc32; resources = $info.resources
            registry_info = $info
        }
    }
    return Get-CatalogLogicalIdentity $Catalog $resolved
}

function Assert-CatalogOwnerAndState($State, [string]$StatePath, [string]$GameRoot,
        [string]$OwnerPath, [string]$CatalogPath) {
    Assert-OrdinalEqual ([string](Get-RequiredProperty $State 'schema' 'catalog state')) `
        'bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1' 'catalog state.schema'
    if ([string]$State.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
        throw "État catalogue non appendable : $($State.status)"
    }
    if (-not [string]::Equals([string]$State.game_root, $GameRoot,
            [System.StringComparison]::OrdinalIgnoreCase)) { throw "GameRoot de l'état catalogue incompatible." }
    [void](Assert-LiveStateTargets $State $GameRoot)
    if (-not (Test-Path -LiteralPath $OwnerPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $CatalogPath -PathType Leaf)) {
        throw 'Owner ou catalogue actif absent.'
    }
    $owner = Get-Content -LiteralPath $OwnerPath -Raw | ConvertFrom-Json
    Assert-OrdinalEqual ([string](Get-RequiredProperty $owner 'schema' 'catalog owner')) `
        'bg2-upscale-creature-sprite-xn-catalog-owner-v1' 'catalog owner.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $owner 'status' 'catalog owner')) `
        'active' 'catalog owner.status'
    foreach ($name in @('transaction_id', 'generation_id', 'job_id', 'job_sha256', 'catalog_sha256')) {
        if (-not [string]::Equals([string](Get-RequiredProperty $owner $name 'catalog owner'),
                [string](Get-RequiredProperty $State $name 'catalog state'),
                [System.StringComparison]::Ordinal)) {
            throw "catalog owner.$name diffère de l'etat actif."
        }
    }
    $ownerStatePath = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $owner 'state_path' 'catalog owner')) `
        'catalog owner.state_path'
    if (-not [string]::Equals([System.IO.Path]::GetFullPath($ownerStatePath),
            [System.IO.Path]::GetFullPath($StatePath),
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "catalog owner.state_path ne résout pas vers l'état actif."
    }
    Assert-ExpectedHash $CatalogPath ([string]$State.catalog_sha256) 'Catalogue actif'
    $catalog = Read-Catalog $CatalogPath
    if ([uint32](Get-RequiredProperty $State 'catalog_version' 'catalog state') -ne $catalog.version) {
        throw 'catalog state.catalog_version diffère du binaire actif.'
    }
    $logicalIdentity = Get-LiveCatalogLogicalIdentity $catalog $GameRoot
    $stateShardVersion = if ($null -ne $State.PSObject.Properties['shard_registry_version']) {
        [uint32]$State.shard_registry_version
    } elseif ($catalog.version -eq 1) { [uint32]3 } else {
        throw 'catalog state.shard_registry_version absent pour un catalogue V2.'
    }
    if ($stateShardVersion -ne $logicalIdentity.shard_registry_version) {
        throw 'catalog state.shard_registry_version diffère des shards actifs.'
    }
    if ($catalog.version -eq 2 -or
        $null -ne $State.PSObject.Properties['logical_content_sha256']) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $State 'logical_content_sha256' `
                'catalog state')) $logicalIdentity.logical_content_sha256 `
            'catalog state.logical_content_sha256'
    }
    if ($catalog.version -eq 2) {
        foreach ($source in @(
                [pscustomobject]@{ value = $State; label = 'catalog state' },
                [pscustomobject]@{ value = $owner; label = 'catalog owner' })) {
            if ([uint32](Get-RequiredProperty $source.value 'directory_count' $source.label) -ne
                    $catalog.directory_count -or
                [uint32](Get-RequiredProperty $source.value 'directory_entry_bytes' $source.label) -ne 24 -or
                -not [string]::Equals(
                    [string](Get-RequiredProperty $source.value 'directory_sha256' $source.label),
                    [string]$catalog.directory_sha256, [System.StringComparison]::Ordinal)) {
                throw "$($source.label) directory V2 diffère du binaire actif."
            }
        }
        if ([uint32](Get-RequiredProperty $owner 'catalog_version' 'catalog owner') -ne 2) {
            throw 'catalog owner.catalog_version diffère du binaire actif.'
        }
    }
    if ($catalog.version -eq 2) {
        if ([uint32](Get-RequiredProperty $owner 'shard_registry_version' 'catalog owner') -ne
                $logicalIdentity.shard_registry_version -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $owner 'logical_content_sha256' 'catalog owner'),
                [string]$logicalIdentity.logical_content_sha256,
                [System.StringComparison]::Ordinal)) {
            throw 'catalog owner identité logique/storage diffère du binaire actif.'
        }
    }
    $sealedBuildPath = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $State 'build_manifest' 'catalog state')) `
        'catalog state.build_manifest'
    Assert-ExpectedHash $sealedBuildPath `
        ([string](Get-RequiredProperty $State 'build_manifest_sha256' 'catalog state')) `
        'Build historique catalogue actif'
    $sealedBuild = Get-Content -LiteralPath $sealedBuildPath -Raw | ConvertFrom-Json
    Assert-OrdinalEqual ([string](Get-RequiredProperty $sealedBuild 'schema' 'historical build')) `
        'bg2-upscale-creature-sprite-xn-catalog-pack-v1' 'historical build.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $sealedBuild 'generation_id' 'historical build')) `
        ([string]$State.generation_id) 'historical build.generation_id'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $sealedBuild 'registry_catalog_sha256' `
            'historical build')) ([string]$State.catalog_sha256) `
        'historical build.registry_catalog_sha256'
    return [pscustomobject]@{
        owner = $owner; catalog = $catalog; logical_identity = $logicalIdentity
        build = $sealedBuild
    }
}

# Restore-CreatureSprite-XN-Catalog-Test.ps1 réutilise uniquement ces validateurs
# par dot-sourcing. Une exécution normale continue dans le workflow ci-dessous.
if ($MyInvocation.InvocationName -eq '.') { return }

$jobPath = (Resolve-Path -LiteralPath $JobFile).Path
$jobPath = Resolve-ProjectPath $jobPath 'JobFile'
$jobSha256 = Get-Sha256 $jobPath
try { $job = Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json }
catch { throw "Job JSON illisible : $($_.Exception.Message)" }
Assert-OrdinalEqual ([string](Get-RequiredProperty $job 'schema' 'job')) `
    'bg2-upscale-creature-sprite-xn-catalog-job-v1' 'job.schema'
$jobId = [string](Get-RequiredProperty $job 'job_id' 'job')
if ($jobId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$') { throw 'job.job_id invalide.' }
$paths = Get-RequiredProperty $job 'paths' 'job'
$runRoot = Resolve-ProjectPath ([string](Get-RequiredProperty $paths 'run_dir' 'job.paths')) 'job.paths.run_dir'
if (-not (Test-Path -LiteralPath $runRoot -PathType Container)) { throw "run_dir absent : $runRoot" }
$gameCandidate = Resolve-AnyPath ([string](Get-RequiredProperty $paths 'game_root' 'job.paths')) 'job.paths.game_root'
if (-not (Test-Path -LiteralPath $gameCandidate -PathType Container)) { throw "GameRoot absent : $gameCandidate" }
$gameRoot = (Resolve-Path -LiteralPath $gameCandidate).Path.TrimEnd('\')
$script:ActiveGameRoot = $gameRoot
Assert-NoReparseComponents $gameRoot $gameRoot 'GameRoot'

$mutex = Enter-GameMutationMutex $gameRoot
try {
    if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
        throw "Le jeu ou InfinityLoader est en cours d'execution."
    }

    $upscale = Get-RequiredProperty $job 'upscale' 'job'
    $scale = [int](Get-RequiredProperty $upscale 'scale' 'job.upscale')
    if ($scale -notin @(2, 4)) { throw 'job.upscale.scale doit valoir 2 ou 4.' }
    Assert-UpscaleContract $upscale $scale 'job.upscale'

    $pointerPath = Join-Path $runRoot 'current-generation.json'
    Assert-SafeKnownPath $pointerPath 'Pointeur de génération'
    if (-not (Test-Path -LiteralPath $pointerPath -PathType Leaf)) {
        throw "Pointeur de génération absent : $pointerPath"
    }
    try { $pointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json }
    catch { throw "Pointeur de génération illisible : $($_.Exception.Message)" }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointer 'schema' 'pointer')) `
        'bg2-upscale-creature-sprite-xn-catalog-current-generation-v1' 'pointer.schema'
    Assert-ExactPropertyNames $pointer @(
        'schema', 'generation_id', 'job_sha256', 'generation_dir',
        'build_manifest', 'build_manifest_sha256', 'runtime_manifest',
        'runtime_manifest_sha256'
    ) 'pointer'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $pointer 'job_sha256' 'pointer')) `
        $jobSha256 'pointer.job_sha256'
    $generationId = [string](Get-RequiredProperty $pointer 'generation_id' 'pointer')
    if ($generationId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$') { throw 'pointer.generation_id invalide.' }
    $generationDir = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $pointer 'generation_dir' 'pointer')) 'pointer.generation_dir'
    if (-not $generationDir.StartsWith($runRoot.TrimEnd('\') + '\',
            [System.StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $generationDir -PathType Container)) {
        throw 'pointer.generation_dir est absent ou sort du run_dir.'
    }
    $buildManifestPath = Resolve-ChildPath $generationDir `
        ([string](Get-RequiredProperty $pointer 'build_manifest' 'pointer')) 'pointer.build_manifest'
    $runtimeManifestPath = Resolve-ChildPath $generationDir `
        ([string](Get-RequiredProperty $pointer 'runtime_manifest' 'pointer')) 'pointer.runtime_manifest'
    Assert-ExpectedHash $buildManifestPath `
        ([string](Get-RequiredProperty $pointer 'build_manifest_sha256' 'pointer')) 'Build de génération'
    Assert-ExpectedHash $runtimeManifestPath `
        ([string](Get-RequiredProperty $pointer 'runtime_manifest_sha256' 'pointer')) 'Runtime de génération'
    $buildManifestSha256 = Get-Sha256 $buildManifestPath
    $runtimeManifestSha256 = Get-Sha256 $runtimeManifestPath
    try { $build = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json }
    catch { throw "Build manifest illisible : $($_.Exception.Message)" }
    try { $runtime = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json }
    catch { throw "Runtime manifest illisible : $($_.Exception.Message)" }

    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'schema' 'build')) `
        'bg2-upscale-creature-sprite-xn-catalog-pack-v1' 'build.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'status' 'build')) `
        'built-pending-ingame-qa' 'build.status'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'job_id' 'build')) $jobId 'build.job_id'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'job_sha256' 'build')) $jobSha256 'build.job_sha256'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'generation_id' 'build')) $generationId 'build.generation_id'
    $declaredJobPath = Resolve-ProjectPath ([string](Get-RequiredProperty $build 'job_file' 'build')) 'build.job_file'
    if (-not [string]::Equals($declaredJobPath, $jobPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'build.job_file ne désigne pas le job courant.'
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'registry_layout' 'build')) 'catalog' `
        'build.registry_layout'
    Assert-UpscaleContract (Get-RequiredProperty $build 'method' 'build') $scale 'build.method'
    Assert-OrdinalEqual (([string](Get-RequiredProperty $build 'registry_catalog' 'build')).Replace('\', '/')) `
        'iee-assets/creature-sprites/CreatureSprites-XN.catalog' 'build.registry_catalog'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $build 'registry_catalog_magic' 'build')) `
        'IEECSNC' 'build.registry_catalog_magic'
    $buildCatalogVersion = [uint32](Get-RequiredProperty $build 'registry_catalog_version' 'build')
    if ($buildCatalogVersion -notin @(1, 2) -or
        [uint32](Get-RequiredProperty $build 'registry_scale' 'build') -ne $scale) {
        throw 'Version/échelle du catalogue build incompatible.'
    }
    $buildRoot = Split-Path -Parent $buildManifestPath
    $sourceCatalog = Resolve-ChildPath $buildRoot `
        ([string]$build.registry_catalog) 'build.registry_catalog'
    $expectedCatalogSha256 = [string](Get-RequiredProperty $build 'registry_catalog_sha256' 'build')
    Assert-ExpectedHash $sourceCatalog $expectedCatalogSha256 'Catalogue source'
    if ([uint64](Get-RequiredProperty $build 'registry_catalog_bytes' 'build') -ne
        [uint64](Get-Item -LiteralPath $sourceCatalog).Length) {
        throw 'build.registry_catalog_bytes diffère du fichier source.'
    }
    $catalog = Read-Catalog $sourceCatalog
    if ($catalog.scale -ne $scale -or $catalog.version -ne $buildCatalogVersion -or
        $catalog.bytes -ne [uint64]$build.registry_catalog_bytes) {
        throw 'Catalogue binaire incompatible avec le build.'
    }
    $buildShardVersion = if ($null -ne $build.PSObject.Properties['registry_catalog_shard_version']) {
        [uint32]$build.registry_catalog_shard_version
    } elseif ($catalog.version -eq 1) { [uint32]3 } else { [uint32]0 }
    Assert-BuildValidation (Get-RequiredProperty $build 'validation' 'build') $scale `
        $catalog.version $buildShardVersion
    $catalogArtifacts = Assert-CatalogManifest $build $catalog $buildRoot
    $sourceMembers = @(Assert-SourceMembers $build $jobPath $catalog)

    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'schema' 'runtime')) `
        'bg2-upscale-creature-sprite-runtime-v1' 'runtime.schema'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'status' 'runtime')) 'built-tested' 'runtime.status'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'tests_status' 'runtime')) 'passed' 'runtime.tests_status'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'job_id' 'runtime')) $jobId 'runtime.job_id'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'generation_id' 'runtime')) $generationId `
        'runtime.generation_id'
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'job_sha256' 'runtime')) $jobSha256 `
        'runtime.job_sha256'
    Assert-UpscaleContract (Get-RequiredProperty $runtime 'method' 'runtime') $scale 'runtime.method'
    Assert-ExactStringSet (Get-RequiredProperty $runtime 'runtime_profiles' 'runtime') `
        (Get-RequiredProperty $build 'runtime_profiles' 'build') 'runtime.runtime_profiles'
    $tests = @(Get-RequiredProperty $runtime 'tests' 'runtime')
    if ($tests.Count -lt 1) { throw 'runtime.tests est vide.' }
    [void](Get-RequiredProperty $runtime 'engine_build' 'runtime')
    $engineSource = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $paths 'engine_source' 'job.paths')) 'job.paths.engine_source'
    $runtimeEngineSource = Resolve-ProjectPath `
        ([string](Get-RequiredProperty $runtime 'engine_source' 'runtime')) 'runtime.engine_source'
    if (-not [string]::Equals($engineSource.TrimEnd('\'), $runtimeEngineSource.TrimEnd('\'),
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'runtime.engine_source diffère du job.'
    }
    $engineContract = [string](Get-RequiredProperty $runtime 'engine_source_contract_sha256' 'runtime')
    Assert-HashText $engineContract 'runtime.engine_source_contract_sha256'
    $currentEngineContract = Get-EngineSourceContractSha256 $engineSource
    Assert-OrdinalEqual $currentEngineContract $engineContract 'runtime.engine_source_contract_sha256'
    Assert-OrdinalEqual ([string]$build.locks.engine_source_contract_sha256) $engineContract `
        'build.locks.engine_source_contract_sha256'

    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_magic' 'runtime')) 'IEECSNC' `
        'runtime.catalog_magic'
    if ([uint32](Get-RequiredProperty $runtime 'catalog_version' 'runtime') -ne $catalog.version) {
        throw 'runtime.catalog_version diffère du catalogue.'
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_shard_registry_magic' 'runtime')) `
        'IEECSXN' 'runtime.catalog_shard_registry_magic'
    if ([uint32](Get-RequiredProperty $runtime 'catalog_shard_registry_version' 'runtime') -ne
            $catalog.shard_registry_version) {
        throw 'runtime.catalog_shard_registry_version diffère des shards.'
    }
    if ($catalog.version -eq 2) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'bridge_worker_tests_status' 'runtime')) `
            'passed' 'runtime.bridge_worker_tests_status'
    }
    if ($catalog.shard_registry_version -eq 5) {
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_frame_storage' 'runtime')) `
            'XPRESS_HUFF-or-raw-per-frame-v1' 'runtime.catalog_frame_storage'
        Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_logical_content_sha256' `
                'runtime')) $catalog.logical_content_sha256 `
            'runtime.catalog_logical_content_sha256'
    }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $runtime 'catalog_shard_animation_id_sentinel' 'runtime')) `
        '0xFFFF' 'runtime.catalog_shard_animation_id_sentinel'
    Assert-RuntimeLimits (Get-RequiredProperty $runtime 'catalog_limits' 'runtime') $catalog.version
    if ($catalog.version -eq 2) {
        if ([uint32](Get-RequiredProperty $runtime 'catalog_directory_count' 'runtime') -ne
                $catalog.directory_count -or
            [uint32](Get-RequiredProperty $runtime 'catalog_directory_entry_bytes' 'runtime') -ne 24 -or
            -not [string]::Equals(
                [string](Get-RequiredProperty $runtime 'catalog_directory_sha256' 'runtime'),
                [string]$catalog.directory_sha256, [System.StringComparison]::Ordinal)) {
            throw 'Métadonnées directory V2 du runtime incompatibles.'
        }
    }

    $runtimeRoot = Split-Path -Parent $runtimeManifestPath
    $sourceDll = Resolve-ChildPath $runtimeRoot ([string](Get-RequiredProperty $runtime 'dll' 'runtime')) `
        'runtime.dll'
    $expectedDllSha256 = [string](Get-RequiredProperty $runtime 'dll_sha256' 'runtime')
    Assert-ExpectedHash $sourceDll $expectedDllSha256 'DLL runtime source'

    $compatibility = Get-RequiredProperty $job 'compatibility' 'job'
    $expectedExeSha256 = [string](Get-RequiredProperty $compatibility 'baldur_real_sha256' 'job.compatibility')
    Assert-HashText $expectedExeSha256 'job.compatibility.baldur_real_sha256'
    Assert-OrdinalEqual ([string]$build.locks.baldur_real_sha256) $expectedExeSha256 `
        'build.locks.baldur_real_sha256'
    Assert-InputLock $build $jobPath $jobSha256 $generationId $scale $engineSource `
        $engineContract $expectedExeSha256
    $baldurReal = Join-Path $gameRoot 'BaldurReal.exe'
    Assert-ExpectedHash $baldurReal $expectedExeSha256 'BaldurReal.exe'

    $dllTarget = Assert-GameChildRelative $gameRoot 'InfinityEngine-Enhancer.dll' 'DLL cible'
    $iniTarget = Assert-GameChildRelative $gameRoot 'InfinityEngine-Enhancer.ini' 'INI cible'
    $catalogRelative = 'iee-assets\creature-sprites\CreatureSprites-XN.catalog'
    $ownerRelative = 'iee-assets\creature-sprites\CreatureSprites-XN.catalog-owner.json'
    $catalogTarget = Assert-GameChildRelative $gameRoot $catalogRelative 'Catalogue cible'
    $ownerTarget = Assert-GameChildRelative $gameRoot $ownerRelative 'Owner cible'
    if (-not (Test-Path -LiteralPath $iniTarget -PathType Leaf)) { throw 'InfinityEngine-Enhancer.ini est absent.' }
    $iniBefore = Get-Content -LiteralPath $iniTarget -Raw
    [void](Get-IniKey $iniBefore 'Shaders' 'EnableCreatureSpriteUpscaleTest' -AllowMissing)
    [void](Get-IniKey $iniBefore 'Shaders' 'EnableCreatureSpriteX2Test' -AllowMissing)
    [void](Get-IniKey $iniBefore 'Shaders' 'EnableCreatureSpriteLinearFiltering' -AllowMissing)

    $activeStatePath = Join-Path $runRoot 'ingame-installation\active-test.json'
    Assert-SafeKnownPath $activeStatePath 'État catalogue actif'
    $previousState = $null
    $previousCatalog = $null
    $installMode = 'initial'
    if (Test-Path -LiteralPath $activeStatePath -PathType Leaf) {
        try { $candidateState = Get-Content -LiteralPath $activeStatePath -Raw | ConvertFrom-Json }
        catch { throw "État catalogue actif illisible : $($_.Exception.Message)" }
        if ([string]$candidateState.status -in @('installing', 'restoring')) {
            throw "Transaction catalogue interrompue ($($candidateState.status)); restaurer avec -RecoverInterrupted."
        }
        if ([string]$candidateState.status -in @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
            $previousState = $candidateState
            $activeInfo = Assert-CatalogOwnerAndState $previousState $activeStatePath $gameRoot `
                $ownerTarget $catalogTarget
            $previousCatalog = $activeInfo.catalog
            Assert-OrdinalEqual ([string]$previousState.job_id) $jobId 'catalog state.job_id'
            Assert-UpscaleContract $previousState.method $scale 'catalog state.method'
            if ($catalog.membership_count -eq $previousCatalog.membership_count) {
                $semanticMode = Assert-CatalogSemanticIdentity $previousCatalog $catalog
                if ($semanticMode -eq 'storage-repack') {
                    Assert-SourceMembersSemanticIdentity $activeInfo.build $build
                }
                if ($semanticMode -eq 'runtime-refresh' -and
                    $catalog.version -eq $previousCatalog.version -and
                    [string]$previousState.catalog_sha256 -cne $expectedCatalogSha256) {
                    throw 'Un runtime-refresh de même version exige un catalogue octet pour octet identique.'
                }
                if ([string]$previousState.generation_id -ceq $generationId) {
                    throw 'La migration runtime/storage exige une nouvelle génération scellée.'
                }
                if (-not (Test-Path -LiteralPath $dllTarget -PathType Leaf)) {
                    throw 'La migration runtime/storage exige la DLL active propriétaire.'
                }
                $previousDllSha256 = Get-Sha256 $dllTarget
                if ($null -ne $previousState.PSObject.Properties['installed_dll_sha256'] -and
                    -not [string]::IsNullOrWhiteSpace([string]$previousState.installed_dll_sha256) -and
                    [string]$previousState.installed_dll_sha256 -cne $previousDllSha256) {
                    throw 'Le hash DLL récapitulatif de etat actif diverge de la cible live.'
                }
                if ($previousDllSha256 -ceq $expectedDllSha256) {
                    throw 'La migration runtime/storage exige une nouvelle DLL runtime testée.'
                }
                $installMode = $semanticMode
            } else {
                Assert-CatalogSuperset $previousCatalog $catalog
                $installMode = 'append'
            }
        } elseif ([string]$candidateState.status -notin @('restored', 'rolled-back-after-install-error')) {
            throw "État catalogue existant non reconnu : $($candidateState.status)"
        }
    }
    if ($null -eq $previousState -and
        ((Test-Path -LiteralPath $catalogTarget -PathType Leaf) -or
         (Test-Path -LiteralPath $ownerTarget -PathType Leaf))) {
        throw 'Catalogue ou owner live présent sans état catalogue actif propriétaire.'
    }
    $importRecord = Get-ImportRecord $job $activeStatePath $gameRoot $previousState
    if ($null -eq $previousState -and $null -ne $importRecord) { $installMode = 'migration' }

    $resourceSet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($resource in $catalogArtifacts.resources) { [void]$resourceSet.Add([string]$resource) }
    $override = Join-Path $gameRoot 'override'
    $collisions = @()
    if (Test-Path -LiteralPath $override -PathType Container) {
        foreach ($bam in Get-ChildItem -LiteralPath $override -Filter '*.BAM' -File -ErrorAction Stop) {
            if ($resourceSet.Contains([System.IO.Path]::GetFileNameWithoutExtension($bam.Name))) {
                $collisions += $bam.Name
            }
        }
    }
    if ($collisions.Count -ne 0) {
        throw "Collision override exacte avec le catalogue actif : $(@($collisions | Sort-Object -Unique) -join ', ')"
    }

    $desiredShards = @()
    foreach ($shard in $catalogArtifacts.shards) {
        $target = Assert-GameChildRelative $gameRoot $shard.relative_path 'Shard cible'
        $present = Test-Path -LiteralPath $target -PathType Leaf
        if ((Test-Path -LiteralPath $target) -and -not $present) { throw "Cible shard non-fichier : $target" }
        if ($present) {
            $actual = Get-Sha256 $target
            if (-not [string]::Equals($actual, $shard.sha256, [System.StringComparison]::Ordinal)) {
                throw "Shard content-addressed divergent : $($shard.relative_path)"
            }
            if ((Get-Crc32 $target) -ne $shard.crc32) { throw "CRC32 live divergent : $($shard.relative_path)" }
        }
        $desiredShards += [pscustomobject]@{
            index = $shard.index; relative_path = $shard.relative_path; source_path = $shard.source_path
            target_path = $target; sha256 = $shard.sha256; crc32 = $shard.crc32
            existed_before = [bool]$present
        }
    }
    $retiredShards = @()
    if ($installMode -eq 'storage-repack') {
        $desiredRelativeSet = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::OrdinalIgnoreCase)
        foreach ($shard in $desiredShards) { [void]$desiredRelativeSet.Add($shard.relative_path) }
        $historicalManifestShards = @(Get-RequiredProperty $activeInfo.build 'shards' 'historical build')
        if ($historicalManifestShards.Count -ne $previousCatalog.shard_count) {
            throw 'Le build historique ne couvre pas tous les shards V3 actifs.'
        }
        $historicalBuildPath = Resolve-ProjectPath ([string]$previousState.build_manifest) `
            'catalog state.build_manifest'
        $historicalBuildRoot = Split-Path -Parent $historicalBuildPath
        foreach ($oldShard in $previousCatalog.shards) {
            $relative = "iee-assets\creature-sprites\CreatureSprites-XN-$($oldShard.sha256).registry"
            if ($desiredRelativeSet.Contains($relative)) { continue }
            $manifestShard = $historicalManifestShards[[int]$oldShard.index]
            $manifestRelative = ([string](Get-RequiredProperty $manifestShard 'registry' `
                    'historical build.shards[]')).Replace('/', '\')
            if ([uint32](Get-RequiredProperty $manifestShard 'index' 'historical build.shards[]') -ne
                    $oldShard.index -or $manifestRelative -cne $relative -or
                [string](Get-RequiredProperty $manifestShard 'sha256' 'historical build.shards[]') -cne
                    [string]$oldShard.sha256 -or
                [uint32](Get-RequiredProperty $manifestShard 'crc32' 'historical build.shards[]') -ne
                    $oldShard.crc32) {
                throw "Source historique shard V3 divergente : $($oldShard.index)"
            }
            $restoreSource = Resolve-ChildPath $historicalBuildRoot $manifestRelative `
                'historical build.shards[].registry'
            Assert-ExpectedHash $restoreSource $oldShard.sha256 `
                "Source de restauration shard V3 $($oldShard.index)"
            if ((Get-Crc32 $restoreSource) -ne [uint32]$oldShard.crc32) {
                throw "CRC32 source de restauration shard V3 divergent : $($oldShard.index)"
            }
            $target = Assert-GameChildRelative $gameRoot $relative 'Shard V3 à retirer'
            Assert-ExpectedHash $target $oldShard.sha256 "Shard V3 live à retirer $($oldShard.index)"
            $retiredShards += [pscustomobject]@{
                relative_path = $relative; target_path = $target
                sha256 = $oldShard.sha256; crc32 = $oldShard.crc32
                restore_source_path = $restoreSource
            }
        }
        if ($retiredShards.Count -lt 1) {
            throw 'Le storage-repack ne retire aucun shard V3 historique.'
        }
    }

    if ($VerifyOnly) {
        [pscustomobject]@{
            Status = 'verified'; Mode = $installMode
            GenerationId = $generationId; Scale = $scale; CatalogVersion = $catalog.version
            ShardRegistryVersion = $catalog.shard_registry_version
            DirectoryEntries = $catalog.directory_count; Animations = $catalog.animation_count
            Components = $catalog.component_count; Shards = $catalog.shard_count
            RetiredShards = $retiredShards.Count
            GameRoot = $gameRoot; State = $activeStatePath
        }
        return
    }

    $transactionId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') +
        "-$PID-$([Guid]::NewGuid().ToString('N'))"
    $backupRoot = Join-Path $runRoot "ingame-installation\backups\$transactionId"
    Assert-SafeKnownPath $backupRoot 'Nouveau backup_root'
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $previousStateBackup = $null
    if ($null -ne $previousState) {
        $previousStateBackup = Join-Path $backupRoot 'previous-active-test.json'
        Assert-SafeKnownPath $previousStateBackup 'Sauvegarde état précédent'
        Copy-Item -LiteralPath $activeStatePath -Destination $previousStateBackup
        Assert-ExpectedHash $previousStateBackup (Get-Sha256 $activeStatePath) 'Sauvegarde état précédent'
    }

    $targets = [System.Collections.Generic.List[object]]::new()
    foreach ($definition in @(
        [pscustomobject]@{ relative = 'InfinityEngine-Enhancer.dll'; role = 'runtime-dll'; immutable = $false },
        [pscustomobject]@{ relative = 'InfinityEngine-Enhancer.ini'; role = 'runtime-ini'; immutable = $false }
    )) {
        $target = Assert-GameChildRelative $gameRoot $definition.relative 'Cible transactionnelle'
        $existed = Test-Path -LiteralPath $target -PathType Leaf
        $backup = $null; $original = $null
        if ($existed) {
            $original = Get-Sha256 $target
            $backup = Join-Path $backupRoot $definition.relative
            Assert-SafeKnownPath $backup "Sauvegarde $($definition.relative)"
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $backup
            Assert-ExpectedHash $backup $original "Sauvegarde $($definition.relative)"
        }
        $targets.Add([pscustomobject]@{
            relative_path = $definition.relative; role = $definition.role; immutable_noop = $false
            existed_before = [bool]$existed; original_sha256 = $original
            backup_path = if ($null -ne $backup) { Get-ProjectRelativePath $backup } else { $null }
            installed_present = $null; installed_sha256 = $null
        })
    }
    foreach ($shard in $desiredShards) {
        $targets.Add([pscustomobject]@{
            relative_path = $shard.relative_path; role = 'content-addressed-shard'
            immutable_noop = [bool]$shard.existed_before; existed_before = [bool]$shard.existed_before
            original_sha256 = if ($shard.existed_before) { $shard.sha256 } else { $null }
            backup_path = $null; installed_present = $null; installed_sha256 = $null
        })
    }
    foreach ($shard in $retiredShards) {
        $targets.Add([pscustomobject]@{
            relative_path = $shard.relative_path; role = 'retired-content-addressed-shard'
            immutable_noop = $false; existed_before = $true
            original_sha256 = $shard.sha256; backup_path = $null
            restore_source_path = Get-ProjectRelativePath $shard.restore_source_path
            restore_source_sha256 = $shard.sha256
            installed_present = $null; installed_sha256 = $null
        })
    }
    foreach ($definition in @(
        [pscustomobject]@{ relative = $ownerRelative; role = 'catalog-owner' },
        [pscustomobject]@{ relative = $catalogRelative; role = 'catalog' }
    )) {
        $target = Assert-GameChildRelative $gameRoot $definition.relative 'Cible transactionnelle'
        $existed = Test-Path -LiteralPath $target -PathType Leaf
        $backup = $null; $original = $null
        if ($existed) {
            $original = Get-Sha256 $target
            $backup = Join-Path $backupRoot $definition.relative
            Assert-SafeKnownPath $backup "Sauvegarde $($definition.relative)"
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $backup
            Assert-ExpectedHash $backup $original "Sauvegarde $($definition.relative)"
        }
        $targets.Add([pscustomobject]@{
            relative_path = $definition.relative; role = $definition.role; immutable_noop = $false
            existed_before = [bool]$existed; original_sha256 = $original
            backup_path = if ($null -ne $backup) { Get-ProjectRelativePath $backup } else { $null }
            installed_present = $null; installed_sha256 = $null
        })
    }

    $state = [ordered]@{
        schema = 'bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1'
        status = 'installing'; transaction_id = $transactionId
        install_started_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        job_file = Get-ProjectRelativePath $jobPath; job_id = $jobId; job_sha256 = $jobSha256
        generation_id = $generationId; game_root = $gameRoot; baldureal_sha256 = $expectedExeSha256
        installation_mode = $installMode
        method = [ordered]@{
            algorithm = [string]$upscale.algorithm; scale = $scale; passes = 1
            antialias = $false; xbr_blend = $false; sampling = 'NEAREST'
        }
        registry_layout = 'catalog'; catalog_relative_path = $catalogRelative
        catalog_magic = 'IEECSNC'; catalog_version = [uint32]$catalog.version; catalog_scale = $scale
        catalog_sha256 = $expectedCatalogSha256; catalog_bytes = [uint64]$catalog.bytes
        shard_registry_version = [uint32]$catalog.shard_registry_version
        frame_storage = [string]$catalog.frame_storage
        logical_content_sha256 = [string]$catalog.logical_content_sha256
        storage = [ordered]@{
            stored_index_bytes = [uint64]$catalog.stored_index_bytes
            compressed_frame_count = [uint64]$catalog.compressed_frame_count
            raw_frame_count = [uint64]$catalog.raw_frame_count
        }
        directory_count = [uint32]$catalog.directory_count
        directory_entry_bytes = [uint32]$catalog.directory_entry_bytes
        directory_sha256 = $catalog.directory_sha256
        animation_ids = @($catalog.animations | ForEach-Object { Format-AnimationId $_.animation_id })
        runtime_profiles = @($build.runtime_profiles)
        animation_count = [uint32]$catalog.animation_count; component_count = [uint32]$catalog.component_count
        membership_count = [uint32]$catalog.membership_count; shard_count = [uint32]$catalog.shard_count
        total_resources = [uint64]$catalog.total_resources; total_frames = [uint64]$catalog.total_frames
        total_index_bytes = [uint64]$catalog.total_index_bytes
        total_registry_bytes = [uint64]$catalog.total_registry_bytes
        source_dll_sha256 = $expectedDllSha256
        build_manifest = Get-ProjectRelativePath $buildManifestPath
        build_manifest_sha256 = $buildManifestSha256
        runtime_manifest = Get-ProjectRelativePath $runtimeManifestPath
        runtime_manifest_sha256 = $runtimeManifestSha256
        backup_root = Get-ProjectRelativePath $backupRoot
        previous_active_state = if ($null -ne $previousState) {
            [ordered]@{ path = Get-ProjectRelativePath $previousStateBackup; sha256 = Get-Sha256 $previousStateBackup
                generation_id = [string]$previousState.generation_id; transaction_id = [string]$previousState.transaction_id }
        } else { $null }
        imported_active_state = $importRecord
        targets = @($targets)
    }
    $backupStatePath = Join-Path $backupRoot 'install-state.json'
    New-Item -ItemType Directory -Path (Split-Path -Parent $activeStatePath) -Force | Out-Null
    Write-JsonAtomic $state $backupStatePath 20
    Write-JsonAtomic $state $activeStatePath 20

    $owner = [ordered]@{
        schema = 'bg2-upscale-creature-sprite-xn-catalog-owner-v1'
        status = 'active'; transaction_id = $transactionId
        installation_mode = $installMode
        generation_id = $generationId; job_id = $jobId; job_sha256 = $jobSha256
        state_path = Get-ProjectRelativePath $activeStatePath
        game_root = $gameRoot; method = $state.method
        catalog_relative_path = $catalogRelative; catalog_sha256 = $expectedCatalogSha256
        catalog_bytes = [uint64]$catalog.bytes; catalog_version = [uint32]$catalog.version
        shard_registry_version = [uint32]$catalog.shard_registry_version
        frame_storage = [string]$catalog.frame_storage
        logical_content_sha256 = [string]$catalog.logical_content_sha256
        directory_count = [uint32]$catalog.directory_count
        directory_entry_bytes = [uint32]$catalog.directory_entry_bytes
        directory_sha256 = $catalog.directory_sha256
        animation_ids = $state.animation_ids
    }

    try {
        Copy-FileAtomic $sourceDll $dllTarget $expectedDllSha256
        $iniText = Get-Content -LiteralPath $iniTarget -Raw
        $iniText = Set-IniKey $iniText 'Shaders' 'EnableCreatureSpriteUpscaleTest' 'true'
        $iniText = Set-IniKey $iniText 'Shaders' 'EnableCreatureSpriteX2Test' 'false'
        $iniText = Set-IniKey $iniText 'Shaders' 'EnableCreatureSpriteLinearFiltering' 'false'
        Write-TextAtomic $iniText $iniTarget
        foreach ($shard in $desiredShards) {
            if ($shard.existed_before) {
                Assert-ExpectedHash $shard.target_path $shard.sha256 "Shard immutable $($shard.index)"
            } else {
                Publish-ImmutableFile $shard.source_path $shard.target_path $shard.sha256
            }
            if ((Get-Crc32 $shard.target_path) -ne $shard.crc32) {
                throw "CRC32 installé incompatible : shard $($shard.index)"
            }
        }
        foreach ($shard in $retiredShards) {
            Assert-ExpectedHash $shard.target_path $shard.sha256 'Shard V3 avant retrait transactionnel'
            Remove-Item -LiteralPath $shard.target_path -Force
            if (Test-Path -LiteralPath $shard.target_path) {
                throw "Le shard V3 retiré subsiste : $($shard.relative_path)"
            }
        }
        if (-not (Test-Path -LiteralPath (Split-Path -Parent $ownerTarget) -PathType Container)) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $ownerTarget) -Force | Out-Null
        }
        Write-JsonAtomic $owner $ownerTarget 12
        # Le catalogue est le point d'activation runtime et reste la dernière
        # mutation d'asset dans le dossier du jeu. Un runtime-refresh de même
        # version conserve le fichier actif octet pour octet sans le republier.
        if ($installMode -eq 'runtime-refresh' -and
            $null -ne $previousCatalog -and $previousCatalog.version -eq $catalog.version) {
            Assert-ExpectedHash $catalogTarget $expectedCatalogSha256 'Catalogue runtime-refresh immuable'
        } else {
            Copy-FileAtomic $sourceCatalog $catalogTarget $expectedCatalogSha256
        }

        Assert-ExpectedHash $dllTarget $expectedDllSha256 'DLL installée'
        Assert-ExpectedHash $catalogTarget $expectedCatalogSha256 'Catalogue installé'
        $installedCatalog = Read-Catalog $catalogTarget
        if ($installedCatalog.animation_count -ne $catalog.animation_count -or
            $installedCatalog.shard_count -ne $catalog.shard_count) { throw 'Catalogue installé divergent.' }
        Assert-CatalogIniOwnedContract (Get-Content -LiteralPath $iniTarget -Raw)
        foreach ($targetState in $targets) {
            $target = Assert-GameChildRelative $gameRoot ([string]$targetState.relative_path) 'Cible installée'
            $present = Test-Path -LiteralPath $target -PathType Leaf
            $targetState.installed_present = [bool]$present
            $targetState.installed_sha256 = if ($present) { Get-Sha256 $target } else { $null }
        }
        $state.status = 'installed-pending-qa'
        $state.installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        $state.installed_dll_sha256 = Get-Sha256 $dllTarget
        $state.installed_ini_sha256 = Get-Sha256 $iniTarget
        $state.installed_owner_sha256 = Get-Sha256 $ownerTarget
        $state.installed_catalog_sha256 = Get-Sha256 $catalogTarget
        Write-JsonAtomic $state $backupStatePath 20
        Write-JsonAtomic $state $activeStatePath 20
    }
    catch {
        $installError = $_.Exception.Message
        $rollbackError = $null
        try {
            foreach ($targetState in @($targets | Where-Object {
                    $_.role -ne 'catalog' -and -not $_.immutable_noop })) {
                $target = Assert-GameChildRelative $gameRoot ([string]$targetState.relative_path) 'Rollback cible'
                if ($targetState.role -eq 'retired-content-addressed-shard') {
                    $restoreSource = Resolve-ProjectPath `
                        ([string]$targetState.restore_source_path) 'target.restore_source_path'
                    Copy-FileAtomic $restoreSource $target ([string]$targetState.original_sha256)
                } elseif ($targetState.existed_before) {
                    $backup = Resolve-ProjectPath ([string]$targetState.backup_path) 'target.backup_path'
                    Copy-FileAtomic $backup $target ([string]$targetState.original_sha256)
                } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
                    Remove-Item -LiteralPath $target -Force
                }
            }
            $catalogTargetState = @($targets | Where-Object { $_.role -eq 'catalog' })[0]
            if ($catalogTargetState.existed_before) {
                $backup = Resolve-ProjectPath ([string]$catalogTargetState.backup_path) 'catalog backup_path'
                Copy-FileAtomic $backup $catalogTarget ([string]$catalogTargetState.original_sha256)
            } elseif (Test-Path -LiteralPath $catalogTarget -PathType Leaf) {
                Remove-Item -LiteralPath $catalogTarget -Force
            }
            $state.status = 'rolled-back-after-install-error'; $state.error = $installError
            $state.rolled_back_at_utc = (Get-Date).ToUniversalTime().ToString('o')
            Write-JsonAtomic $state $backupStatePath 20
            if ($null -ne $previousStateBackup) {
                Copy-FileAtomic $previousStateBackup $activeStatePath (Get-Sha256 $previousStateBackup)
            } else {
                Write-JsonAtomic $state $activeStatePath 20
            }
        }
        catch { $rollbackError = $_.Exception.Message }
        if ($null -ne $rollbackError) {
            throw "Installation échouée : $installError ; rollback incomplet : $rollbackError"
        }
        throw "Installation échouée puis rollback fidèle : $installError"
    }

    [pscustomobject]@{
        Status = $state.status; Mode = $installMode
        GenerationId = $generationId; Scale = $scale; CatalogVersion = $catalog.version
        ShardRegistryVersion = $catalog.shard_registry_version
        DirectoryEntries = $catalog.directory_count; Animations = $catalog.animation_count
        Components = $catalog.component_count; Shards = $catalog.shard_count
        GameRoot = $gameRoot; Backup = $backupRoot; State = $activeStatePath
    }
}
finally {
    Exit-GameMutationMutex $mutex
}
