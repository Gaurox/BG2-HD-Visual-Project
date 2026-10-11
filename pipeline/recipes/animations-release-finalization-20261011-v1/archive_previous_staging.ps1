$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$release = Join-Path $workspace 'releases/BG2-HD-Upscale'
$mod = Join-Path $release 'bg2hd'
$archive = Join-Path $release 'archive/staging-before-alpha6-20261011'
$names = @('payload-allvalidated', 'payload-allvalidated-20260921', 'payload-allvalidated-alpha5')
$moves = @()
foreach ($name in $names) {
    $source = [IO.Path]::GetFullPath((Join-Path $mod $name))
    $destination = [IO.Path]::GetFullPath((Join-Path $archive $name))
    if (-not $source.StartsWith($mod + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
        -not $destination.StartsWith($archive + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Chemin hors périmètre.' }
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw "Staging absent : $source" }
    if (Test-Path -LiteralPath $destination) { throw "Archive déjà présente : $destination" }
    $moves += [ordered]@{ source=$source; destination=$destination }
}
New-Item -ItemType Directory -Path $archive | Out-Null
foreach ($move in $moves) { Move-Item -LiteralPath $move.source -Destination $move.destination }
$receipt = [ordered]@{ operation='preserve previous release staging outside distributable bg2hd'; game_mutation=$false; moves=$moves }
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'previous-staging-moves.json'), ($receipt | ConvertTo-Json -Depth 6) + "`n", [Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 6
