$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$powerShell = Join-Path $PSHOME 'powershell.exe'
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $powerShell
$startInfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptDir\start_celery_worker.ps1`""
$startInfo.WorkingDirectory = $scriptDir
$startInfo.UseShellExecute = $true
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
[System.Diagnostics.Process]::Start($startInfo) | Out-Null

Write-Output 'Celery Worker launch requested. Run celery inspect ping to confirm it is ready.'
