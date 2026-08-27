[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$EEexInstallerPath
)

$ErrorActionPreference = 'Stop'
function Require([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }

$contractPath = Join-Path $ReleaseRoot 'manifests/dependency-bootstrap.json'
$schemaPath = Join-Path $ReleaseRoot 'schemas/dependency-bootstrap.schema.json'
$runtimePath = Join-Path $ReleaseRoot 'manifests/runtime-compatibility.json'
$releasePath = Join-Path $ReleaseRoot 'manifests/release.json'
Require (Test-Json -Path $contractPath -SchemaFile $schemaPath) 'Schema invalide : dependency-bootstrap.json'
Require (Test-Json -Path $runtimePath -SchemaFile (Join-Path $ReleaseRoot 'schemas/runtime-compatibility.schema.json')) 'Schema invalide : runtime-compatibility.json'

$contract = Get-Content -LiteralPath $contractPath -Raw -Encoding utf8 | ConvertFrom-Json
$runtime = Get-Content -LiteralPath $runtimePath -Raw -Encoding utf8 | ConvertFrom-Json
 $release = Get-Content -LiteralPath $releasePath -Raw -Encoding utf8 | ConvertFrom-Json
Require (($release.manifest_files -contains 'manifests/dependency-bootstrap.json')) 'Le manifeste de release doit declarer le contrat de dependances.'
Require ($runtime.eeex.version -eq $contract.eeex.required_version) 'Version EEex incoherente entre runtime et contrat.'
Require ($runtime.eeex.dependency_contract -eq 'manifests/dependency-bootstrap.json') 'Lien runtime vers contrat de dependances invalide.'
Require (($runtime.eeex.weidu_components | ForEach-Object { "$($_.tp2)#$($_.id)" }) -join ',' -eq (($contract.eeex.installation.required_weidu_components | ForEach-Object { "$($_.tp2)#$($_.id)" }) -join ',')) 'Composants WeiDU EEex incoherents.'
foreach ($runtimeFile in $runtime.eeex.files) {
    $contractFile = @($contract.eeex.detection.exact_files | Where-Object { $_.path -eq $runtimeFile.path })
    Require ($contractFile.Count -eq 1) "Fichier runtime absent du contrat : $($runtimeFile.path)"
    Require ($contractFile[0].sha256 -eq $runtimeFile.sha256 -and $contractFile[0].bytes -eq $runtimeFile.bytes) "Empreinte runtime incoherente : $($runtimeFile.path)"
}
Require (($contract.eeex.detection.exact_files | Where-Object { $_.path -eq 'InfinityLoader.exe' }).Count -eq 1) 'InfinityLoader.exe doit etre controle par le contrat.'
Require (($contract.eeex.detection.mutable_runtime_files | Where-Object { $_ -eq 'InfinityLoader.db' }).Count -eq 1) 'InfinityLoader.db doit etre declare comme cache mutable.'
Require (($contract.eeex.detection.exact_files | Where-Object { $_.path -eq 'InfinityLoader.db' }).Count -eq 0) 'InfinityLoader.db ne doit pas etre traite comme binaire immuable.'
Require ($contract.eeex.state_policy.inactive -eq 'offer-official-eeex-install') 'Un EEex desinstalle doit etre reinstallable par le flux officiel.'
foreach ($path in @('EEex/EEex.tp2', 'EEex/EEex.ini', 'EEex/loader', 'EEex/copy/EEex_scripts', 'EEex/copy/override', 'setup-EEex.exe')) {
    Require ($contract.eeex.detection.inactive_residue_paths -contains $path) "Residus EEex inactifs incomplets dans le contrat : $path"
}
Require ($contract.eeex.update_policy.uninstall_bg2hd -eq 'standard-uninstall-keeps-eeex-and-steam-shim; explicit-confirmed-full-vanilla-restore-uses-official-eeex-uninstaller') 'La regle de desinstallation EEex est invalide.'
Require ($runtime.steam_launch_contract.steam_keeps_launching -eq 'Baldur.exe') 'Le contrat Steam doit conserver Baldur.exe comme entree.'
Require ($runtime.steam_launch_contract.preserved_original -eq 'BaldurReal.exe') 'Le contrat Steam ne preserve pas explicitement l executable officiel.'
Require ($runtime.steam_launch_contract.launcher_ini_alias -eq 'BaldurReal.exe:Baldur.exe') 'L alias InfinityLoader est invalide.'
Require ($runtime.save_compatibility_contract.eeex_extra_creature_marshalling -eq 'disabled') 'Le contrat save-neutral est absent.'
Require ($contract.bootstrap_protocol.order[0] -eq 'locate-and-verify-target-steam-game') 'Le bootstrap doit commencer par verifier le jeu Steam cible.'
Require ($contract.bootstrap_protocol.order[-1] -eq 'verify-steam-shim-and-installed-save-compatibility-guard') 'Le bootstrap doit verifier le shim et le garde save-neutral apres WeiDU.'

if ($EEexInstallerPath) {
    Require (Test-Path -LiteralPath $EEexInstallerPath -PathType Leaf) "Archive EEex absente : $EEexInstallerPath"
    $item = Get-Item -LiteralPath $EEexInstallerPath
    Require ($item.Name -eq $contract.eeex.official_release.filename) 'Nom d archive EEex inattendu.'
    Require ($item.Length -eq $contract.eeex.official_release.bytes) 'Taille d archive EEex inattendue.'
    Require ((Get-FileHash -LiteralPath $EEexInstallerPath -Algorithm SHA256).Hash -eq $contract.eeex.official_release.sha256) 'SHA-256 d archive EEex inattendu.'
}

Write-Output 'Dependency bootstrap contract validation passed.'
