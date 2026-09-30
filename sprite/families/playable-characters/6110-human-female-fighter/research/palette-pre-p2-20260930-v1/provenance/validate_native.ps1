param([Parameter(Mandatory=$true)][string]$TaskPython)
$ErrorActionPreference = 'Stop'
$taskOutput = Split-Path $PSScriptRoot -Parent
$taskRoot = $taskOutput
while (-not (Test-Path (Join-Path $taskRoot 'pipeline/scripts/workspace_paths.py'))) {
    $taskRoot = Split-Path $taskRoot -Parent
    if (-not $taskRoot) { throw 'Workspace root not found' }
}
$taskSource = Join-Path $taskRoot 'engine/InfinityEngine-Enhancer/source-patchee'
$taskBuildRoot = Join-Path $taskRoot 'build/palette-pre-p2-20260930-v1'
$taskBuild = Join-Path $taskBuildRoot 'cmake'
$taskProof = Join-Path $taskOutput 'native.json'
if ((Test-Path $taskBuildRoot) -or (Test-Path $taskProof)) { throw 'Use a fresh audit/build run' }
$taskCmake = (Get-Command cmake).Source
$taskCtest = (Get-Command ctest).Source
$taskEnvTemp = $env:TEMP
$taskEnvTmp = $env:TMP
$taskEnvBytecode = $env:PYTHONDONTWRITEBYTECODE
$taskReport = [ordered]@{
    schema = 'bg2-upscale-character-pre-p2-native-v1'
    status = 'running'
    started_utc = [DateTime]::UtcNow.ToString('o')
    scope = 'Unmodified current Windows engine baseline only; no Q3m reader, pack or installation'
    git_head = (& git -C $taskRoot rev-parse HEAD)
    generator = 'Visual Studio 16 2019'
    architecture = 'x64'
    build_directory = $taskBuild
    python_reference = 'config://chainner_python'
    cmake_version = (& $taskCmake --version | Select-Object -First 1)
    dependencies = [ordered]@{}
    commands = @()
}
function Get-TaskSourceHashes {
    $taskHashes = [ordered]@{}
    $taskFiles = @('CMakeLists.txt', 'assets/water-route2/registry-v2.json')
    foreach ($taskDir in @('src', 'tests', 'tools')) {
        $taskFiles += @(Get-ChildItem -LiteralPath (Join-Path $taskSource $taskDir) -Recurse -File |
            Where-Object { $_.Extension -in @('.cpp','.c','.h','.hpp','.in','.py') } |
            ForEach-Object { [IO.Path]::GetRelativePath($taskSource, $_.FullName) })
    }
    foreach ($taskFile in ($taskFiles | Sort-Object -Unique)) {
        $taskHashes[$taskFile.Replace('\','/')] = (Get-FileHash -LiteralPath (Join-Path $taskSource $taskFile) -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $taskHashes['../../../pipeline/water/route2-registry-v1.json'] = (Get-FileHash -LiteralPath (Join-Path $taskRoot 'pipeline/water/route2-registry-v1.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    return $taskHashes
}
function Invoke-TaskCommand([string]$TaskExecutable, [string[]]$TaskArguments, [string]$TaskLogName) {
    $taskLog = Join-Path $taskOutput $TaskLogName
    $taskStart = [DateTime]::UtcNow
    & $TaskExecutable @TaskArguments *> $taskLog
    $taskCode = $LASTEXITCODE
    $taskReport.commands += [ordered]@{ executable=$TaskExecutable; arguments=$TaskArguments; log=$TaskLogName; exit_code=$taskCode; elapsed_seconds=([DateTime]::UtcNow-$taskStart).TotalSeconds }
    Write-Output "$TaskLogName exit=$taskCode"
    Get-Content -LiteralPath $taskLog -Tail 12
    if ($taskCode -ne 0) { throw "$TaskLogName failed ($taskCode)" }
}
try {
    $taskReport.source_sha256 = Get-TaskSourceHashes
    New-Item -ItemType Directory -Path $taskBuildRoot | Out-Null
    $taskDepRoot = Join-Path $taskBuildRoot 'dependencies'
    New-Item -ItemType Directory -Path $taskDepRoot | Out-Null
    $taskPins = [ordered]@{
        spdlog='6fa36017cfd5731d617e1a934f0e5ea9c4445b13'
        zlib='da607da739fa6047df13e66a2af6b8bec7c2a498'
        minhook='c3fcafdc10146beb5919319d0683e44e3c30d537'
    }
    foreach ($taskName in $taskPins.Keys) {
        $taskCache = Join-Path $taskSource "build-cache128/_deps/$taskName-src"
        $taskHead = & git -C $taskCache rev-parse HEAD
        if ($LASTEXITCODE -ne 0 -or $taskHead -ne $taskPins[$taskName]) { throw "Dependency pin mismatch: $taskName" }
        $taskChanges = & git -C $taskCache status --porcelain --untracked-files=all 2>$null
        if ($LASTEXITCODE -ne 0 -or $taskChanges) { throw "Dependency cache is not clean: $taskName" }
        $taskArchive = Join-Path $taskDepRoot "$taskName.tar"
        & git -C $taskCache archive --format=tar "--output=$taskArchive" $taskHead
        if ($LASTEXITCODE -ne 0) { throw "Dependency archive failed: $taskName" }
        $taskDestination = Join-Path $taskDepRoot $taskName
        New-Item -ItemType Directory -Path $taskDestination | Out-Null
        & tar -xf $taskArchive -C $taskDestination
        if ($LASTEXITCODE -ne 0) { throw "Dependency extraction failed: $taskName" }
        $taskReport.dependencies[$taskName] = [ordered]@{ commit=$taskHead; archive_sha256=(Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant(); source=$taskDestination }
    }
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Invoke-TaskCommand $taskCmake @('-S',$taskSource,'-B',$taskBuild,'-G','Visual Studio 16 2019','-A','x64',
        '-DIEE_BUILD_WINDOWS_DLL=ON','-DBUILD_TESTING=ON','-DFETCHCONTENT_FULLY_DISCONNECTED=ON',
        "-DPython3_EXECUTABLE=$TaskPython", "-DFETCHCONTENT_SOURCE_DIR_SPDLOG=$(Join-Path $taskDepRoot 'spdlog')",
        "-DFETCHCONTENT_SOURCE_DIR_ZLIB=$(Join-Path $taskDepRoot 'zlib')",
        "-DFETCHCONTENT_SOURCE_DIR_MINHOOK=$(Join-Path $taskDepRoot 'minhook')") 'native-configure.log'
    Invoke-TaskCommand $taskCmake @('--build',$taskBuild,'--config','Release','--parallel','4','--target',
        'iee_tests','iee_effect_animation_x4_registry_tests','iee_bridge_worker_tests','InfinityEngine-Enhancer') 'native-build.log'
    # Existing tests remove fixed fixture paths. Refuse any pre-existing source fixture;
    # redirect OS temporary paths to this new build run, preserving user files.
    $taskFixtures = @('creature-sprite-registry-format-test','area-animation-registry-format-test',
        'InfinityEngine-Enhancer-log-rotation-test','InfinityEngine-Enhancer-test.ini',
        'InfinityEngine-Enhancer-bounds-test.ini','InfinityEngine-Enhancer-invalid-test.ini',
        'InfinityEngine-Enhancer-creature-filter-test.ini','InfinityEngine-Enhancer-creature-hd-test.ini',
        'InfinityEngine-Enhancer-sprite-profiles-test.ini','InfinityEngine-Enhancer-shader-test.ini',
        'InfinityEngine-Enhancer-dds-test.dds')
    foreach ($taskFixture in $taskFixtures) {
        if (Test-Path -LiteralPath (Join-Path $taskSource $taskFixture)) { throw "Existing user fixture must be preserved: $taskFixture" }
    }
    $taskTemp = Join-Path $taskBuildRoot 'test-temp'
    New-Item -ItemType Directory -Path $taskTemp | Out-Null
    $env:TEMP = $taskTemp
    $env:TMP = $taskTemp
    Invoke-TaskCommand $taskCtest @('--test-dir',$taskBuild,'-C','Release','--output-on-failure','--no-tests=error') 'native-ctest.log'
    foreach ($taskFixture in $taskFixtures) {
        if (Test-Path -LiteralPath (Join-Path $taskSource $taskFixture)) { throw "Test did not clean its fixture: $taskFixture" }
    }
    $taskAfter = Get-TaskSourceHashes
    if (($taskAfter | ConvertTo-Json -Compress) -ne ($taskReport.source_sha256 | ConvertTo-Json -Compress)) { throw 'Native source changed during baseline validation' }
    $taskReport.source_unchanged = $true
    $taskReport.artifacts_sha256 = [ordered]@{}
    foreach ($taskArtifact in @('iee_tests.exe','iee_effect_animation_x4_registry_tests.exe','iee_bridge_worker_tests.exe','InfinityEngine-Enhancer.dll')) {
        $taskReport.artifacts_sha256[$taskArtifact] = (Get-FileHash -LiteralPath (Join-Path $taskBuild "Release/$taskArtifact") -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $taskReport.status = 'passed'
} catch {
    $taskReport.status = 'failed'
    $taskReport.error = $_.Exception.Message
    Write-Output $taskReport.error
} finally {
    $env:TEMP = $taskEnvTemp
    $env:TMP = $taskEnvTmp
    $env:PYTHONDONTWRITEBYTECODE = $taskEnvBytecode
    $taskReport.finished_utc = [DateTime]::UtcNow.ToString('o')
    $taskReport | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskProof -Encoding utf8
}
if ($taskReport.status -ne 'passed') { exit 1 }
