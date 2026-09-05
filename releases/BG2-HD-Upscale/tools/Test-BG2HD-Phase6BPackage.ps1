[CmdletBinding()]
param([Parameter(Mandatory)] [string]$ArchivePath)

$ErrorActionPreference = 'Stop'
function Require([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Hash-Stream([IO.Stream]$Stream) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash($Stream))).Replace('-', '') }
    finally { $sha.Dispose() }
}

$archive = (Resolve-Path -LiteralPath $ArchivePath).Path
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($archive)
try {
    $entries = @($zip.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
    $names = @($entries.FullName)
    $required = @('Install-BG2HD.exe', 'Uninstall-BG2HD.exe', 'setup-bg2hd.exe', 'BUILD-STATUS.txt', 'BUILD-MANIFEST.json', 'checksums.sha256', 'README.md', 'README_FR.md', 'README_EN.md', 'CHANGELOG.md', 'KNOWN_ISSUES.md', 'tools/Test-BG2HD-FutureSaveCompatibility.ps1', 'tools/Test-BG2HD-AR0413Contract.ps1', 'docs/ARCHITECTURE.md', 'docs/DEPENDENCY_BOOTSTRAP.md', 'docs/MANIFESTS.md', 'docs/MAINTENANCE.md', 'docs/INSTALLER_AND_UPSCALE_WORKFLOW.md', 'docs/LOCALIZATION.md', 'docs/STEAM_INTEGRATION.md', 'docs/TESTING.md', 'docs/RECOVERY.md', 'docs/COMPATIBILITY.md', 'docs/LICENCES.md', 'docs/DISTRIBUTION_POLICY.md', 'bg2hd/bg2hd.tp2', 'bg2hd/tools/Install-BG2HD.ps1', 'bg2hd/manifests/dependency-bootstrap.json', 'bg2hd/manifests/runtime-compatibility.json')
    foreach ($path in $required) { Require ($names -contains $path) "Archive incomplet : $path" }
    Require (($names | Where-Object { $_ -match '(^|/)(Baldur(?:Real)?\.exe|EEex\.dll|InfinityLoader\.exe|.*\.log|.*\.sav)$' }).Count -eq 0) 'Archive contient un fichier interdit.'
    Require (($names | Where-Object { $_ -match '(^|/)(PHASE[0-9]|release-inputs|validation|dist-local)/' }).Count -eq 0) 'Archive contient une preuve ou un input interne.'
    $checksums = @{}
    $reader = [IO.StreamReader]::new(($zip.GetEntry('checksums.sha256')).Open())
    try {
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ($line -match '^([0-9A-F]{64})  (.+)$') { $checksums[$Matches[2]] = $Matches[1] } else { throw "Ligne checksum invalide : $line" }
        }
    } finally { $reader.Dispose() }
    $hashedEntries = @($entries | Where-Object { $_.FullName -ne 'checksums.sha256' })
    Require ($checksums.Count -eq $hashedEntries.Count) 'Inventaire checksums incomplet.'
    foreach ($entry in $hashedEntries) {
        Require ($checksums.ContainsKey($entry.FullName)) "Checksum absent : $($entry.FullName)"
        $stream = $entry.Open(); try { Require ((Hash-Stream $stream) -eq $checksums[$entry.FullName]) "Checksum incorrect : $($entry.FullName)" } finally { $stream.Dispose() }
        # ZIP timestamps have no timezone.  ZipArchive exposes the same fixed
        # DOS value using the local offset, so compare its calendar value.
        Require ($entry.LastWriteTime.DateTime -eq [DateTime]::new(1980,1,1,0,0,0)) "Timestamp ZIP non deterministe : $($entry.FullName)"
    }
    $buildReader = [IO.StreamReader]::new(($zip.GetEntry('BUILD-MANIFEST.json')).Open())
    try { $buildText = $buildReader.ReadToEnd(); $build = $buildText | ConvertFrom-Json } finally { $buildReader.Dispose() }
    Require ($build.package_kind -eq 'local-alpha-not-public') 'Statut de package invalide.'
    Require ($build.bootstrap_launcher_sha256 -match '^[A-F0-9]{64}$') 'Empreinte bootstrap absente.'
    Require ($build.uninstall_launcher_sha256 -match '^[A-F0-9]{64}$') 'Empreinte lanceur de desinstallation absente.'
    $launcherEntry = $zip.GetEntry('Install-BG2HD.exe')
    $launcherStream = $launcherEntry.Open(); try { Require ((Hash-Stream $launcherStream) -eq $build.bootstrap_launcher_sha256) 'Empreinte bootstrap invalide.' } finally { $launcherStream.Dispose() }
    $uninstallEntry = $zip.GetEntry('Uninstall-BG2HD.exe')
    $uninstallStream = $uninstallEntry.Open(); try { Require ((Hash-Stream $uninstallStream) -eq $build.uninstall_launcher_sha256) 'Empreinte lanceur de desinstallation invalide.' } finally { $uninstallStream.Dispose() }
    $rendererReader = [IO.StreamReader]::new(($zip.GetEntry('bg2hd/manifests/renderer-bundle.json')).Open())
    try { $renderer = ($rendererReader.ReadToEnd() | ConvertFrom-Json) } finally { $rendererReader.Dispose() }
    Require ($renderer.status -eq 'integrated-in-place-awaiting-user-lifecycle-test') 'Statut renderer archive invalide.'
    foreach($file in @($renderer.files)) {
        $entry = $zip.GetEntry(('bg2hd/renderer/' + $file.path))
        Require ($null -ne $entry) "Renderer absent de l archive : $($file.path)"
        Require ($entry.Length -eq [int64]$file.bytes) "Taille renderer archive invalide : $($file.path)"
        $stream = $entry.Open(); try { Require ((Hash-Stream $stream) -eq $file.sha256) "Hash renderer archive invalide : $($file.path)" } finally { $stream.Dispose() }
    }
    Require ($buildText -match '"fixed_zip_timestamp_utc"\s*:\s*"1980-01-01T00:00:00Z"') 'Contrat d horodatage invalide.'
    'PHASE6B_PACKAGE=PASSED'
} finally { $zip.Dispose() }
