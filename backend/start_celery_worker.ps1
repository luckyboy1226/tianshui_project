$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
  $env:TIANSHUI_PYTHON,
  'C:\Users\cumtGIS\miniforge3\envs\tianshui-gis\python.exe',
  'D:\Anaconda3\envs\ts\python.exe',
  (Join-Path $scriptDir '.venv\Scripts\python.exe')
)
$pythonExe = $pythonCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $pythonExe) {
  throw 'No usable Python interpreter was found. Set TIANSHUI_PYTHON first.'
}

& "$scriptDir\start_redis.ps1"

$envFile = Join-Path $scriptDir '.env'
if (-not (Test-Path $envFile)) {
  throw 'backend/.env is required for the Redis connection settings.'
}

function Get-DotEnvValue([string]$key) {
  $line = Get-Content $envFile | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
  if (-not $line) {
    throw "Missing $key in backend/.env."
  }
  return $line.Substring($key.Length + 1)
}

$env:CELERY_TASK_ALWAYS_EAGER = Get-DotEnvValue 'CELERY_TASK_ALWAYS_EAGER'
$env:CELERY_BROKER_URL = Get-DotEnvValue 'CELERY_BROKER_URL'
$env:CELERY_RESULT_BACKEND = Get-DotEnvValue 'CELERY_RESULT_BACKEND'
$env:DJANGO_SETTINGS_MODULE = 'tianshuipy.settings_dev'

Set-Location $scriptDir
$workerArgs = "-m celery -A tianshuipy worker --loglevel=INFO --pool=solo --concurrency=1"
& $pythonExe $workerArgs.Split(' ')
