[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$exitCode = 0
$createdNodeModulesLink = $false
$nodeModulesLink = $null
$nodeModules = $null

try {
    $workspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
    $workbookPath = Join-Path $workspaceRoot 'outputs\bg2ee-hd-human-tracking\BG2EE-HD-suivi-global.xlsx'
    $workspaceScript = Join-Path $workspaceRoot 'pipeline\scripts\workspace.py'
    $generator = Join-Path $workspaceRoot 'pipeline\scripts\generate_human_tracking_xlsx.mjs'

    if (Test-Path -LiteralPath $workbookPath -PathType Leaf) {
        try {
            $stream = [IO.File]::Open(
                $workbookPath,
                [IO.FileMode]::Open,
                [IO.FileAccess]::ReadWrite,
                [IO.FileShare]::None
            )
            $stream.Dispose()
        } catch {
            throw "Fermez BG2EE-HD-suivi-global.xlsx dans Excel avant la mise a jour."
        }
    }

    $python = @(
        Get-Command python.exe -All -CommandType Application -ErrorAction SilentlyContinue |
            Where-Object { $_.Source -notmatch '\\WindowsApps\\' }
    ) | Select-Object -First 1
    if ($null -eq $python) {
        throw "Python est introuvable dans PATH."
    }

    $dependencyRoot = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
    $node = Join-Path $dependencyRoot 'node\bin\node.exe'
    $nodeModules = Join-Path $dependencyRoot 'node\node_modules'
    $artifactTool = Join-Path $nodeModules '@oai\artifact-tool'
    if (-not (Test-Path -LiteralPath $node -PathType Leaf) -or
        -not (Test-Path -LiteralPath $artifactTool -PathType Container)) {
        throw "Le runtime tableur Codex est introuvable. Ouvrez Codex une fois pour installer ses dependances de workspace."
    }

    $nodeModulesLink = Join-Path $PSScriptRoot 'node_modules'
    if (Test-Path -LiteralPath $nodeModulesLink) {
        if (-not (Test-Path -LiteralPath (Join-Path $nodeModulesLink '@oai\artifact-tool') -PathType Container)) {
            throw "pipeline\scripts\node_modules existe mais ne contient pas @oai/artifact-tool."
        }
    } else {
        New-Item -ItemType Junction -Path $nodeModulesLink -Target $nodeModules | Out-Null
        $createdNodeModulesLink = $true
    }

    Write-Host '[1/2] Reconstruction du registre global depuis les autorites CSV...'
    & $python.Source $workspaceScript refresh --scope registry --run
    if ($LASTEXITCODE -ne 0) {
        throw "La reconstruction du registre global a echoue (code $LASTEXITCODE)."
    }

    Write-Host '[2/2] Reconstruction du classeur de suivi...'
    & $node $generator
    if ($LASTEXITCODE -ne 0) {
        throw "La reconstruction du classeur a echoue (code $LASTEXITCODE)."
    }

    & $node $generator --check
    if ($LASTEXITCODE -ne 0) {
        throw "Le controle du classeur reconstruit a echoue (code $LASTEXITCODE)."
    }

    Write-Host ''
    Write-Host "Mise a jour terminee : $workbookPath" -ForegroundColor Green
} catch {
    $exitCode = 1
    Write-Host ''
    Write-Host "ECHEC : $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if ($createdNodeModulesLink -and $null -ne $nodeModulesLink -and (Test-Path -LiteralPath $nodeModulesLink)) {
        $link = Get-Item -LiteralPath $nodeModulesLink -Force
        $expectedTarget = [IO.Path]::GetFullPath($nodeModules)
        $actualTargets = @($link.Target | ForEach-Object { [IO.Path]::GetFullPath([string]$_) })
        if ($link.LinkType -eq 'Junction' -and $actualTargets -contains $expectedTarget) {
            [IO.Directory]::Delete($nodeModulesLink, $false)
        } else {
            Write-Warning "Jonction temporaire inattendue conservee : $nodeModulesLink"
        }
    }
}

exit $exitCode
