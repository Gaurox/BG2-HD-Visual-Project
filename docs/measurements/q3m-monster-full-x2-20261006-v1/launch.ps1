$ErrorActionPreference = 'Stop'
$spriteRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$spritePython = (Get-Content (Join-Path $spriteRoot 'config/workspace-paths.local.json') -Raw | ConvertFrom-Json).paths.chainner_python
$env:PYTHONPATH = Join-Path $spriteRoot 'sprite/.work/q3m-runtime-tools-20261003-v1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:Q3M_PLAN_PROGRESS = '1'
$env:Q3M_PACK_PROGRESS = '1'
$env:Q3M_GUIDE_WORKERS = '8'
$env:Q3M_ENCODE_WORKERS = '16'
$env:Q3M_TARGET_IO_WORKERS = '8'
$env:Q3M_TRIM_CUDA_CACHE = '1'
$env:Q3M_PALETTE_ENCODER = 'gpu-grouped-guarded-v1'
$env:CUBLAS_WORKSPACE_CONFIG = ':4096:8'
$spriteSuffix = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
$spriteWork = Join-Path $spriteRoot ('sprite/.work/' + (Split-Path $PSScriptRoot -Leaf))
New-Item -ItemType Directory -Path $spriteWork -Force | Out-Null
$spriteLog = Join-Path $PSScriptRoot ('production-' + $spriteSuffix + '.log')
$spriteError = Join-Path $PSScriptRoot ('production-error-' + $spriteSuffix + '.log')
$spriteProcess = Start-Process -FilePath $spritePython -ArgumentList @('-u', '-B', (Join-Path $PSScriptRoot 'produce.py')) -WorkingDirectory $spriteRoot -WindowStyle Hidden -RedirectStandardOutput $spriteLog -RedirectStandardError $spriteError -PassThru
$spriteState = [pscustomobject]@{pid=$spriteProcess.Id;started_at_utc=[DateTime]::UtcNow.ToString('o');stdout=$spriteLog;stderr=$spriteError}
$spriteState | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $spriteWork 'process.json') -Encoding utf8
$spriteState | ConvertTo-Json
