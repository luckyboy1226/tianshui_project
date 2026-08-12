$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$backendScript = Join-Path $backendDir 'start_dev.ps1'
$frontendScript = Join-Path $frontendDir 'start_dev.ps1'
$redisScript = Join-Path $backendDir 'start_redis.ps1'
$celeryScript = Join-Path $backendDir 'start_celery_worker.ps1'

foreach ($scriptPath in @($backendScript, $frontendScript, $redisScript, $celeryScript)) {
    if (-not (Test-Path $scriptPath)) {
        throw "Missing startup script: $scriptPath"
    }
}

function Test-PortListening {
    param([int]$Port)

    return Test-NetConnection -ComputerName '127.0.0.1' -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
}

function Start-ProjectScript {
    param([string]$ScriptPath, [string]$WorkingDirectory)

    Start-Process -FilePath 'powershell.exe' `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-File', $ScriptPath `
        -WorkingDirectory $WorkingDirectory
}

Write-Host 'Checking Redis...' -ForegroundColor Cyan
& $redisScript

if (Test-PortListening -Port 8000) {
    Write-Host 'Django is already running on http://127.0.0.1:8000/' -ForegroundColor Yellow
} else {
    Write-Host 'Starting Django...' -ForegroundColor Cyan
    Start-ProjectScript -ScriptPath $backendScript -WorkingDirectory $backendDir
}

if (Test-PortListening -Port 3000) {
    Write-Host 'Frontend is already running on http://localhost:3000/' -ForegroundColor Yellow
} else {
    Write-Host 'Starting frontend...' -ForegroundColor Cyan
    Start-ProjectScript -ScriptPath $frontendScript -WorkingDirectory $frontendDir
}

$existingWorker = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'celery.*worker' -and $_.CommandLine -match 'tianshuipy' } |
    Select-Object -First 1

if ($existingWorker) {
    Write-Host 'Celery Worker is already running.' -ForegroundColor Yellow
} else {
    Write-Host 'Starting Celery Worker...' -ForegroundColor Cyan
    Start-ProjectScript -ScriptPath $celeryScript -WorkingDirectory $backendDir
}

Start-Sleep -Seconds 3
Start-Process 'http://localhost:3000/'

Write-Host ''
Write-Host 'Project startup command has completed.' -ForegroundColor Green
Write-Host 'Keep the Django, frontend, and Celery windows open while using the project.' -ForegroundColor Green
