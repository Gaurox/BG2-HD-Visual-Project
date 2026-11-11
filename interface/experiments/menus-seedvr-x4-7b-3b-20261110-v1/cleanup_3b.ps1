$ErrorActionPreference = 'Stop'
$runRoot = (Resolve-Path -LiteralPath 'G:\AI\BG2_Upscale\interface\experiments\menus-seedvr-x4-7b-3b-20261110-v1').Path
if (Test-Path -LiteralPath (Join-Path $runRoot 'cleanup-3b-20261111.json')) { throw 'Cleanup receipt already exists; do not overwrite.' }
$comfyRoot = 'E:\AI\ComfyUI_windows_portable\ComfyUI\output\BG2_UIAB_20261110'
$targets = @((Join-Path $runRoot 'seedvr-3b-x4'), (Join-Path $comfyRoot '3b'))
$targets += @(Get-ChildItem -LiteralPath (Join-Path $runRoot 'workflows') -Filter '*-3b-x4.api.json' -File | ForEach-Object { $_.FullName })
$entries = @()
foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) { continue }
    $resolved = (Resolve-Path -LiteralPath $target).Path
    if (-not ($resolved.StartsWith($runRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or $resolved -eq (Join-Path $comfyRoot '3b'))) { throw "Unexpected delete target: $resolved" }
    $item = Get-Item -LiteralPath $resolved
    $files = if ($item.PSIsContainer) { @(Get-ChildItem -LiteralPath $resolved -File -Recurse) } else { @($item) }
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    $entries += [pscustomobject]@{ path = $resolved; files = $files.Count; bytes = $bytes }
}
$receipt = [pscustomobject]@{ schema = 'bg2-ui-3b-cleanup-v1'; scope = 'Four-menu comparison only; other domains, historical runs and model weights preserved'; deleted = $entries; total_bytes = ($entries | Measure-Object -Property bytes -Sum).Sum }
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runRoot 'cleanup-3b-20261111.json') -Encoding utf8
foreach ($entry in $entries) { Remove-Item -LiteralPath $entry.path -Recurse -Force }
Write-Output ($receipt | ConvertTo-Json -Depth 5)
