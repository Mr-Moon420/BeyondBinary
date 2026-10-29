param([switch]$Cpu, [int]$Port = 8001)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot 'venv\Scripts\python.exe'
$cudaRuntime = Join-Path $projectRoot 'scratch\cuda-runtime'
if (-not $Cpu) {
    if (-not (Test-Path -LiteralPath (Join-Path $cudaRuntime 'torch'))) {
        throw 'CUDA runtime missing. Use -Cpu or install the tested CUDA runtime first.'
    }
    $env:PYTHONPATH = $cudaRuntime
    $env:BEYONDBINARY_DEVICE = 'auto'
} else {
    $env:BEYONDBINARY_DEVICE = 'cpu'
}
$env:BEYONDBINARY_PREWARM = '1'
$env:BEYONDBINARY_PUBLIC = '1'
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$env:OMP_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
Write-Host 'Starting BeyondBinary. Wait for Application startup complete before opening the demo.'
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port $Port --workers 1
