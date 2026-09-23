# Installe (ou restaure) la DLL InfinityEngine-Enhancer compilee avec un registre eau route2.
#
# Installation : jeu/InfinityLoader fermes ; la DLL live doit etre celle du pointeur
# pipeline/water/route2-registry-current.json (sinon on ignore quel registre elle porte).
# Sauvegarde + recu JSON sous backups/water/<Label>/runtime, puis pointeur mis a jour.
# Restauration : -Restore -Receipt <install-backup.json> remet la DLL et le pointeur precedents.
#
#   pwsh pipeline/scripts/Install-WaterRuntime.ps1 -Dll <build>/Release/InfinityEngine-Enhancer.dll `
#        -Registry pipeline/water/requests/<run>/registry-v3.json -Label <run>
#   pwsh pipeline/scripts/Install-WaterRuntime.ps1 -Restore -Receipt backups/water/<run>/runtime/install-backup.json

param(
    [string]$Dll,
    [string]$Registry,
    [string]$Label,
    [switch]$Restore,
    [string]$Receipt,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = $PSScriptRoot
while ($workspaceRoot -and -not (Test-Path -LiteralPath (Join-Path $workspaceRoot 'config\workspace-paths.json') -PathType Leaf)) {
    $workspaceRoot = Split-Path -Parent $workspaceRoot
}
if ([string]::IsNullOrWhiteSpace($workspaceRoot)) { throw 'Racine du workspace BG2 Upscale introuvable.' }
. (Join-Path $workspaceRoot 'pipeline\scripts\WorkspacePaths.ps1')
if ([string]::IsNullOrWhiteSpace($GameRoot)) { $GameRoot = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting }

$pointerPath = Join-Path $workspaceRoot 'pipeline\water\route2-registry-current.json'
$target = Join-Path $GameRoot 'InfinityEngine-Enhancer.dll'

function Resolve-InWorkspace([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) { return [IO.Path]::GetFullPath($Path) }
    return [IO.Path]::GetFullPath((Join-Path $workspaceRoot $Path))
}
function Get-Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Get-ShaLf([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $text = [Text.Encoding]::UTF8.GetString($bytes).Replace("`r`n", "`n")
    $sha = [Security.Cryptography.SHA256]::Create()
    ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text)))).Replace('-', '')
}
function Write-JsonLf([string]$Path, $Object) {
    $json = ($Object | ConvertTo-Json -Depth 8).Replace("`r`n", "`n") + "`n"
    [IO.File]::WriteAllText($Path, $json, (New-Object Text.UTF8Encoding($false)))
}
function Get-Relative([string]$Path) {
    [IO.Path]::GetRelativePath($workspaceRoot, $Path).Replace('\', '/')
}

if (Get-Process Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue) {
    throw 'Jeu ou InfinityLoader actif : fermer avant toute ecriture.'
}

if ($Restore) {
    if (-not $Receipt) { throw '-Restore exige -Receipt.' }
    $receiptPath = Resolve-InWorkspace $Receipt
    $r = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ((Get-Sha $r.target) -ne $r.installed_sha256) { throw 'DLL live differente de celle installee par ce recu : restauration refusee.' }
    if ((Get-Sha $r.backup) -ne $r.before_sha256) { throw 'Sauvegarde DLL divergente.' }
    Copy-Item -LiteralPath $r.backup -Destination $r.target -Force
    if ((Get-Sha $r.target) -ne $r.before_sha256) { throw 'Restauration DLL divergente.' }
    Write-JsonLf $pointerPath $r.previous_pointer
    Write-Output "DLL restauree ($($r.before_sha256)) ; pointeur registre remis a l'etat precedent."
    return
}

if (-not ($Dll -and $Registry -and $Label)) { throw 'Installation : -Dll, -Registry et -Label requis.' }
if ($Label -notmatch '^[a-z0-9][a-z0-9-]+$') { throw 'Label : minuscules, chiffres et tirets (nom du run).' }
$source = Resolve-InWorkspace $Dll
$registryPath = Resolve-InWorkspace $Registry
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "DLL introuvable : $source" }
if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) { throw "Registre introuvable : $registryPath" }
$requests = [IO.Path]::GetFullPath((Join-Path $workspaceRoot 'pipeline\water\requests')) + [IO.Path]::DirectorySeparatorChar
if (-not $registryPath.StartsWith($requests, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Le registre doit etre la copie versionnee sous pipeline/water/requests/<run>/.'
}
$pointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json
$before = Get-Sha $target
if ($before -ne $pointer.dll_sha256) {
    throw "DLL live $before absente du pointeur ($($pointer.dll_sha256)) : registre porte inconnu, installation refusee."
}
$backupDir = Join-Path $workspaceRoot "backups\water\$Label\runtime"
if (Test-Path -LiteralPath $backupDir) { throw "Sauvegarde deja presente : $backupDir (choisir un nouveau Label)." }
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$backup = Join-Path $backupDir 'InfinityEngine-Enhancer.dll'
Copy-Item -LiteralPath $target -Destination $backup
if ((Get-Sha $backup) -ne $before) { throw 'Sauvegarde DLL divergente.' }
Copy-Item -LiteralPath $source -Destination $target -Force
$installed = Get-Sha $target
if ($installed -ne (Get-Sha $source)) { throw 'Copie DLL divergente.' }

$receiptPath = Join-Path $backupDir 'install-backup.json'
Write-JsonLf $receiptPath ([ordered]@{
    schema = 'bg2-water-runtime-install-v1'; created_utc = (Get-Date).ToUniversalTime().ToString('o')
    label = $Label; target = $target; source = $source; backup = $backup
    before_sha256 = $before; installed_sha256 = $installed; bytes = (Get-Item $target).Length
    registry = [ordered]@{ path = (Get-Relative $registryPath); sha256_lf = (Get-ShaLf $registryPath) }
    previous_pointer = $pointer
})
$entries = (Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json).entries
Write-JsonLf $pointerPath ([ordered]@{
    schema = 'bg2-water-route2-registry-current-v1'
    note = $pointer.note
    registry = [ordered]@{ path = (Get-Relative $registryPath); sha256_lf = (Get-ShaLf $registryPath) }
    identities = @($entries | ForEach-Object { [ordered]@{ wed = $_.wed.resref; overlay = $_.overlay.tis_resref; slot = $_.overlay.slot; state = $_.state } })
    dll_sha256 = $installed
    installed_by = (Get-Relative $receiptPath)
    updated = (Get-Date -Format 'yyyy-MM-dd')
})
Write-Output "DLL installee ($installed). Recu : $(Get-Relative $receiptPath). Pointeur registre mis a jour."
