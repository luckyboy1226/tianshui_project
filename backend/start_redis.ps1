$ErrorActionPreference = 'Stop'

$redisRoot = if ($env:REDIS_HOME) { $env:REDIS_HOME } else { 'D:\Redis-x64-5.0.14.1' }
$redisServer = Join-Path $redisRoot 'redis-server.exe'
$redisCli = Join-Path $redisRoot 'redis-cli.exe'
$envFile = Join-Path $PSScriptRoot '.env'
$redisPassword = ''

if (Test-Path $envFile) {
  $passwordLine = Get-Content $envFile | Where-Object { $_ -match '^REDIS_PASSWORD=' } | Select-Object -First 1
  if ($passwordLine) {
    $redisPassword = $passwordLine.Substring('REDIS_PASSWORD='.Length)
  }
}

if (-not (Test-Path $redisServer) -or -not (Test-Path $redisCli)) {
  throw "Redis was not found. Set REDIS_HOME to the Redis installation directory."
}

$listener = Get-NetTCPConnection -State Listen -LocalPort 6379 -ErrorAction SilentlyContinue
if (-not $listener) {
  $startInfo = New-Object System.Diagnostics.ProcessStartInfo
  $startInfo.FileName = $redisServer
  $startInfo.Arguments = '--bind 127.0.0.1 --port 6379 --protected-mode yes'
  $startInfo.WorkingDirectory = $redisRoot
  $startInfo.UseShellExecute = $true
  $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
  [System.Diagnostics.Process]::Start($startInfo) | Out-Null
}

for ($attempt = 0; $attempt -lt 20; $attempt++) {
  if ($redisPassword) {
    $env:REDISCLI_AUTH = $redisPassword
  }
  $reply = & $redisCli ping 2>$null
  if ($reply -eq 'PONG') {
    Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue
    Write-Output 'Redis is ready at redis://127.0.0.1:6379/0'
    return
  }
  Start-Sleep -Milliseconds 500
}

Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue
throw 'Redis did not become ready within 10 seconds.'
