# First installation of this immutable full x4 experiment; never launches the game.
$ErrorActionPreference = 'Stop'
$q3mRoot = $PSScriptRoot
$q3mWorkspace = $q3mRoot
while (-not (Test-Path -LiteralPath (Join-Path $q3mWorkspace 'pipeline/scripts/ThinInstall.ps1'))) {
    $q3mWorkspace = Split-Path -Parent $q3mWorkspace
    if (-not $q3mWorkspace) { throw 'Workspace introuvable.' }
}
$q3mScripts = Join-Path $q3mWorkspace 'pipeline/scripts'
. (Join-Path $q3mScripts 'ThinInstall.ps1')
Assert-GameClosed
$q3mProofPath = Join-Path $q3mRoot 'installation-verification.json'
if (Test-Path -LiteralPath $q3mProofPath) { throw 'Preuve finale immutable ; utiliser les commandes Verify du README.' }
$q3mProof = Read-JsonFile (Join-Path $q3mRoot 'verification.json')
if ($q3mProof.status -ne 'passed-offline-ready-for-manual-game' -or $q3mProof.frames -ne 178360 -or $q3mProof.scale -ne 4) {
    throw 'Verification native complete requise.'
}
$q3mGame = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
$q3mLiveCatalog = Join-Path $q3mGame 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
$q3mLiveIni = Join-Path $q3mGame 'InfinityEngine-Enhancer.ini'
$q3mLiveDll = Join-Path $q3mGame 'InfinityEngine-Enhancer.dll'
$q3mX2Hash = '82668F7A0E5664B07AD53B47DFD925B86056D071EF5EA2FB2EE4B431DBDBCFD6'
$q3mIniHash = 'D58A96E5C87E6A53A3AB0FB026733B5964C5D2E2D8271849E28D6E83765DF4AC'
$q3mOldDllHash = 'CB99A98A508172C2D7CAC939B2AEF303D9B17EE11F1C1261D2859EEFA6AD053F'
if ((Get-FileSha256 $q3mLiveCatalog) -eq '938DC483847F72BF327A58D1F7AD5F196FEA5ECFEB30D0A8B1F8702FC310A226') {
    $q3mPreviousJob = Join-Path (Split-Path -Parent $q3mRoot) 'palette-q3m-p3-20261001-v4-x4-existing-6110/x4-existing.job.json'
    & (Join-Path $q3mScripts 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mPreviousJob
}
if ((Get-FileSha256 $q3mLiveCatalog) -ne $q3mX2Hash -or (Get-FileSha256 $q3mLiveIni) -ne $q3mIniHash -or
    (Get-FileSha256 $q3mLiveDll) -ne $q3mOldDllHash) { throw 'Installation precedente divergente ; aucun remplacement.' }
Write-JsonAtomic (Join-Path $q3mRoot 'installation-baseline.json') ([ordered]@{
    schema = 'bg2-upscale-q3m-x4-installation-baseline-v1'; captured_at_utc = [DateTime]::UtcNow.ToString('o')
    game_root = $q3mGame; catalog_sha256 = $q3mX2Hash; ini_sha256 = $q3mIniHash; dll_sha256 = $q3mOldDllHash
})
$q3mManifest = Join-Path $q3mRoot 'runtime.json'
$q3mJob = Join-Path $q3mRoot 'x4-q3m-k6.job.json'
try {
    & (Join-Path $q3mScripts 'Start-Palette-Q3m-P3.ps1') -Run $q3mRoot -Scale 4 -Mode Q3m
    $q3mRuntimeResult = & (Join-Path $q3mScripts 'Install-IEE-Runtime-Test.ps1') -Mode Verify -Manifest $q3mManifest -StateRoot (Join-Path $q3mRoot 'ingame-runtime')
    $q3mInstallResult = & (Join-Path $q3mScripts 'Install-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mJob -RuntimeManifest $q3mManifest -CreatureSpriteFilter Nearest -VerifyOnly
    if (-not $q3mInstallResult.TargetActive -or $q3mInstallResult.InstalledShardsVerified -ne 656 -or
        $q3mInstallResult.CatalogSha256 -ne $q3mProof.catalog_sha256.ToUpperInvariant()) { throw 'Catalogue actif incomplet.' }
    $q3mIni = Get-Content -LiteralPath $q3mLiveIni -Raw
    foreach ($q3mSection in @('ShaderSuite.fpSprite', 'ShaderSuite.fpSELECT')) {
        if ((Get-IniValue $q3mIni $q3mSection 'Enabled') -ne 'false') { throw "Profil x1 actif : $q3mSection" }
    }
    if ((Get-IniValue $q3mIni 'Shaders' 'EnableCreatureSpritePaletteTrace') -ne 'false') { throw 'Trace palette active.' }
    $q3mState = Read-JsonFile $q3mInstallResult.State
    if ((Get-FileSha256 (Join-Path $q3mState.backup_root $q3mState.catalog_backup)) -ne $q3mX2Hash -or
        (Get-FileSha256 (Join-Path $q3mState.backup_root $q3mState.ini_backup)) -ne $q3mIniHash -or
        (Get-FileSha256 (Join-Path $q3mRoot 'ingame-runtime/previous-InfinityEngine-Enhancer.dll')) -ne $q3mOldDllHash) {
        throw 'Sauvegardes de retour arriere divergentes.'
    }
    $q3mRestoreResult = & (Join-Path $q3mScripts 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mJob -VerifyOnly
    Write-JsonAtomic $q3mProofPath ([ordered]@{
        schema = 'bg2-upscale-q3m-x4-installation-verification-v1'; status = 'installed-pending-manual-qa'
        verified_at_utc = [DateTime]::UtcNow.ToString('o'); animation_id = '0x6110'; scale = 4; method = 'Q3m'; k = 6
        resources = 656; frames = 178360; legacy_pixels_reused = 0
        installation = $q3mInstallResult; runtime_verification = $q3mRuntimeResult
        runtime_dll_sha256 = Get-FileSha256 $q3mLiveDll; nearest = $true
        x1_sprite_shader_profiles_disabled = $true; palette_trace = $false
        previous_x2_catalog_sha256 = $q3mX2Hash; previous_ini_sha256 = $q3mIniHash; previous_dll_sha256 = $q3mOldDllHash
        backup_bytes_verified = $true; restore_verification = $q3mRestoreResult
        offline_verification_sha256 = Get-FileSha256 (Join-Path $q3mRoot 'verification.json')
        installation_script_sha256 = Get-FileSha256 $PSCommandPath
        other_animations = 'native BAM during isolated 0x6110 x4 test'; ingame_validated = $false; visual_qa_accepted = $false
    })
    Get-Content -LiteralPath $q3mProofPath -Raw
} catch {
    & (Join-Path $q3mScripts 'Start-Palette-Q3m-P3.ps1') -Run $q3mRoot -Scale 4 -Mode Restore
    throw
}
