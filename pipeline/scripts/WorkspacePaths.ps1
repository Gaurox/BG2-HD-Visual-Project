$script:BG2WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script:BG2WorkspacePathConfig = Get-Content -LiteralPath (Join-Path $script:BG2WorkspaceRoot 'config\workspace-paths.json') -Raw | ConvertFrom-Json
$script:BG2WorkspaceLocalPath = Join-Path $script:BG2WorkspaceRoot $script:BG2WorkspacePathConfig.local_override
$script:BG2WorkspaceLocal = if (Test-Path -LiteralPath $script:BG2WorkspaceLocalPath -PathType Leaf) {
    Get-Content -LiteralPath $script:BG2WorkspaceLocalPath -Raw | ConvertFrom-Json
} else {
    $null
}

function Resolve-BG2WorkspacePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [switch]$RequireExisting
    )

    $definition = $script:BG2WorkspacePathConfig.paths.$Key
    if ($null -eq $definition) {
        throw "Unknown workspace path key: $Key"
    }
    $value = [Environment]::GetEnvironmentVariable([string]$definition.environment)
    if ([string]::IsNullOrWhiteSpace($value)) {
        $legacyProperty = $definition.PSObject.Properties['legacy_environments']
        if ($null -ne $legacyProperty) {
            foreach ($legacyName in @($legacyProperty.Value)) {
                $value = [Environment]::GetEnvironmentVariable([string]$legacyName)
                if (-not [string]::IsNullOrWhiteSpace($value)) { break }
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($value) -and $null -ne $script:BG2WorkspaceLocal) {
        $property = $script:BG2WorkspaceLocal.paths.PSObject.Properties[$Key]
        if ($null -ne $property) { $value = [string]$property.Value }
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Workspace path '$Key' is not configured. Set $($definition.environment) or create config/workspace-paths.local.json."
    }
    $resolved = [System.IO.Path]::GetFullPath($value)
    if ($RequireExisting -and -not (Test-Path -LiteralPath $resolved)) {
        throw "Configured workspace path '$Key' does not exist: $resolved"
    }
    return $resolved
}

function Get-BG2WorkspaceService {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Key)

    $definition = $script:BG2WorkspacePathConfig.services.$Key
    if ($null -eq $definition) {
        throw "Unknown workspace service key: $Key"
    }
    $value = [Environment]::GetEnvironmentVariable([string]$definition.environment)
    if ([string]::IsNullOrWhiteSpace($value) -and $null -ne $script:BG2WorkspaceLocal) {
        $property = $script:BG2WorkspaceLocal.services.PSObject.Properties[$Key]
        if ($null -ne $property) { $value = [string]$property.Value }
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [string]$definition.default
    }
    return $value
}
