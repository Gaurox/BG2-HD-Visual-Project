# First installation of this immutable combined test; never launches the game.
$ErrorActionPreference = 'Stop'
$q3mRun = $PSScriptRoot
$q3mWorkspace = $q3mRun
while (-not (Test-Path -LiteralPath (Join-Path $q3mWorkspace 'pipeline/scripts/ThinInstall.ps1'))) {
    $q3mWorkspace = Split-Path -Parent $q3mWorkspace
    if (-not $q3mWorkspace) { throw 'Workspace introuvable.' }
}
$q3mScripts = Join-Path $q3mWorkspace 'pipeline/scripts'
. (Join-Path $q3mScripts 'ThinInstall.ps1')
Assert-GameClosed
$q3mFinal = Join-Path $q3mRun 'installation-verification.json'
$q3mBaselinePath = Join-Path $q3mRun 'installation-baseline.json'
if ((Test-Path -LiteralPath $q3mFinal) -or (Test-Path -LiteralPath $q3mBaselinePath)) {
    throw 'Run historique ; utiliser les commandes Install/Verify/Restore du README.'
}
$q3mProofPath = Join-Path $q3mRun 'verification.json'
$q3mProof = Read-JsonFile $q3mProofPath
if ($q3mProof.status -ne 'passed-offline-ready-for-install' -or $q3mProof.scale -ne 4 -or
    $q3mProof.method -ne 'Q3m' -or $q3mProof.k -ne 6 -or $q3mProof.shards -ne 1312 -or
    (@($q3mProof.animation_ids) -join ',') -ne '0x6100,0x6110') { throw 'Preuve du catalogue commun divergente.' }
$q3mBuild = Join-Path $q3mRun 'generation/build-manifest.json'
if ((Get-FileSha256 $q3mBuild) -ne $q3mProof.build_manifest_sha256) { throw 'Manifeste de generation divergent.' }
$q3mRuntimePath = Resolve-WorkspaceInput ([string]$q3mProof.runtime_manifest) -RequireExisting
if ((Get-FileSha256 $q3mRuntimePath) -ne $q3mProof.runtime_manifest_sha256) { throw 'Manifeste runtime divergent.' }
$q3mGame = Resolve-BG2WorkspacePath -Key bg2ee_game_root -RequireExisting
$q3mCatalog = Join-Path $q3mGame 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
$q3mIniPath = Join-Path $q3mGame 'InfinityEngine-Enhancer.ini'
$q3mDll = Join-Path $q3mGame 'InfinityEngine-Enhancer.dll'
$q3mFemale = @($q3mProof.source_bindings | Where-Object animation_id -eq '0x6110')[0]
if ((Get-FileSha256 $q3mCatalog) -ne $q3mFemale.source_catalog_sha256 -or
    (Get-FileSha256 $q3mDll) -ne $q3mProof.runtime_dll_sha256) {
    throw 'Catalogue feminin ou DLL divergents de la preparation ; aucun remplacement.'
}
$q3mBaseline = [ordered]@{
    schema = 'bg2-q3m-human-fighters-x4-installation-baseline-v1'
    captured_at_utc = [DateTime]::UtcNow.ToString('o'); game_root = $q3mGame
    catalog_sha256 = Get-FileSha256 $q3mCatalog
    ini_sha256 = Get-FileSha256 $q3mIniPath
    dll_sha256 = Get-FileSha256 $q3mDll
}
Write-JsonAtomic $q3mBaselinePath $q3mBaseline
$q3mJob = Join-Path $q3mRun 'x4-q3m-k6.job.json'
try {
    $q3mInstall = & (Join-Path $q3mScripts 'Install-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mJob -RuntimeManifest $q3mRuntimePath -CreatureSpriteFilter Nearest
    $q3mVerified = & (Join-Path $q3mScripts 'Install-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mJob -RuntimeManifest $q3mRuntimePath -CreatureSpriteFilter Nearest -VerifyOnly
    if (-not $q3mVerified.TargetActive -or $q3mVerified.InstalledShardsVerified -ne 1312 -or
        $q3mVerified.CatalogSha256 -ne $q3mProof.catalog_sha256) { throw 'Installation commune incomplete.' }
    if ((Get-FileSha256 $q3mDll) -ne $q3mBaseline.dll_sha256) { throw 'DLL modifiee pendant installation.' }
    $q3mIni = Get-Content -LiteralPath $q3mIniPath -Raw
    foreach ($q3mSection in @('ShaderSuite.fpSprite', 'ShaderSuite.fpSELECT')) {
        if ((Get-IniValue $q3mIni $q3mSection 'Enabled') -ne 'false') { throw "Profil x1 actif : $q3mSection" }
    }
    if ((Get-IniValue $q3mIni 'Shaders' 'EnableCreatureSpritePaletteTrace') -ne 'false') { throw 'Trace palette active.' }
    $q3mState = Read-JsonFile $q3mVerified.State
    if ((Get-FileSha256 (Join-Path $q3mState.backup_root $q3mState.catalog_backup)) -ne $q3mBaseline.catalog_sha256 -or
        (Get-FileSha256 (Join-Path $q3mState.backup_root $q3mState.ini_backup)) -ne $q3mBaseline.ini_sha256) {
        throw 'Sauvegardes de retour divergentes.'
    }
    $q3mRestore = & (Join-Path $q3mScripts 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mJob -VerifyOnly
    Write-JsonAtomic $q3mFinal ([ordered]@{
        schema = 'bg2-q3m-human-fighters-x4-installation-verification-v1'; status = 'installed-pending-manual-qa'
        verified_at_utc = [DateTime]::UtcNow.ToString('o'); animation_ids = @('0x6100', '0x6110')
        scale = 4; method = 'Q3m'; k = 6; resources = 1312; frames = 358697
        installation = $q3mInstall; installed_verification = $q3mVerified; restore_verification = $q3mRestore
        active_catalog_sha256 = Get-FileSha256 $q3mCatalog
        active_ini_sha256 = Get-FileSha256 $q3mIniPath
        runtime_dll_sha256 = Get-FileSha256 $q3mDll; runtime_dll_changed = $false
        active_pack_bytes = $q3mProof.active_pack_bytes; nearest = $true
        x1_sprite_shader_profiles_disabled = $true; palette_trace = $false
        backup_bytes_verified = $true; previous_catalog_sha256 = $q3mBaseline.catalog_sha256
        previous_ini_sha256 = $q3mBaseline.ini_sha256
        offline_verification_sha256 = Get-FileSha256 $q3mProofPath
        installation_script_sha256 = Get-FileSha256 $PSCommandPath
        ingame_validated = $false; visual_qa_accepted = $false
    })
    Get-Content -LiteralPath $q3mFinal -Raw
} catch {
    if (Test-Path -LiteralPath (Join-Path $q3mRun 'ingame-installation/active-test.json')) {
        & (Join-Path $q3mScripts 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $q3mJob
    }
    throw
}
