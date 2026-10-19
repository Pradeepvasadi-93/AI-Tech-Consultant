param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Load-Env([string]$File) {
  if (!(Test-Path $File)) { return }
  Get-Content $File | ForEach-Object {
    $line = $_.Trim()
    if ($line -and !$line.StartsWith('#') -and $line.Contains('=')) {
      $pair = $line.Split('=', 2); $key = $pair[0].Trim(); $val = $pair[1].Trim().Trim('"').Trim("'")
      if ($key -and -not [Environment]::GetEnvironmentVariable($key, 'Process')) { [Environment]::SetEnvironmentVariable($key, $val, 'Process') }
    }
  }
}
function Get-TaskDir([string[]]$Names, [string]$Label) {
  foreach ($n in $Names) { $p = Join-Path $Root $n; if (Test-Path $p) { return (Resolve-Path $p).Path } }
  throw "$Label folder not found. Expected one of: $($Names -join ', ')"
}
function Get-Python([string]$Dir) {
  foreach ($p in @((Join-Path $Dir '.venv\Scripts\python.exe'), (Join-Path $Root '.venv\Scripts\python.exe'))) { if (Test-Path $p) { return $p } }
  $c = Get-Command python -ErrorAction SilentlyContinue; if ($c) { return $c.Source }
  throw 'Python not found. Install Python or create a task .venv.'
}
function Start-App([string]$Name, [string]$Dir, [string]$Exe, [string[]]$AppArgs) {
  $id = $Name.ToLower() -replace '[^a-z0-9-]', '-'
  $o = Join-Path $LogDir "$id.out.log"; $e = Join-Path $LogDir "$id.err.log"
  Write-Host "Starting $Name in $Dir" -ForegroundColor Cyan
  if ([string]::IsNullOrWhiteSpace($Exe)) { throw "Executable is empty for $Name." }
  if ($null -eq $AppArgs -or $AppArgs.Count -eq 0 -or @($AppArgs | Where-Object { $null -eq $_ }).Count -gt 0) { throw "Startup arguments are empty or contain null values for $Name." }
  $p = Start-Process -FilePath $Exe -ArgumentList $AppArgs -WorkingDirectory $Dir -RedirectStandardOutput $o -RedirectStandardError $e -PassThru
  [PSCustomObject]@{Name=$Name; PID=$p.Id; Out=$o; Err=$e}
}
function Wait-Health([string]$Name, [string]$Url) {
  $until = (Get-Date).AddSeconds(60)
  while ((Get-Date) -lt $until) {
    try { $r = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -lt 500) { Write-Host "$Name healthy: $Url" -ForegroundColor Green; return $true } } catch {}
    Start-Sleep -Seconds 2
  }
  Write-Warning "$Name did not respond at $Url within 60 seconds. Check logs/"
  return $false
}

Load-Env (Join-Path $Root '.env')
$t1 = Get-TaskDir @('task1-knowledge-brain','task1','Task1') 'Task 1'
$t2 = Get-TaskDir @('task2-inbox-agent','task2','Task2') 'Task 2'
$t3 = Get-TaskDir @('task3-meeting-to-scope','task3','Task3') 'Task 3'
$started = @()

# Task 1: Knowledge Brain, port 8000
$py1 = Get-Python $t1
$started += Start-App 'Task 1 Knowledge Brain' $t1 $py1 @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000')

# Task 2: Inbox Agent, port 8001. Uses the detected project entry point.
Load-Env (Join-Path $t2 '.env')
if (Test-Path (Join-Path $t2 'package.json')) {
  $npm = Get-Command npm -ErrorAction SilentlyContinue; if (!$npm) { throw 'Task 2 package.json found but npm is missing.' }
  $started += Start-App 'Task 2 Inbox Agent' $t2 $npm.Source @('run','dev','--','--port','8001')
} elseif (Test-Path (Join-Path $t2 'backend\package.json')) {
  $npm = Get-Command npm -ErrorAction SilentlyContinue; if (!$npm) { throw 'Task 2 backend/package.json found but npm is missing.' }
  $started += Start-App 'Task 2 Inbox Agent' (Join-Path $t2 'backend') $npm.Source @('run','dev','--','--port','8001')
} elseif (Test-Path (Join-Path $t2 'app\main.py')) {
  $py2 = Get-Python $t2; $started += Start-App 'Task 2 Inbox Agent' $t2 $py2 @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001')
} elseif (Test-Path (Join-Path $t2 'main.py')) {
  $py2 = Get-Python $t2; $started += Start-App 'Task 2 Inbox Agent' $t2 $py2 @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8001')
} elseif (Test-Path (Join-Path $t2 'server.js')) {
  $node = Get-Command node -ErrorAction SilentlyContinue; if (!$node) { throw 'Task 2 server.js found but Node.js is missing.' }
  $started += Start-App 'Task 2 Inbox Agent' $t2 $node.Source @('server.js')
} else { throw "Task 2 entry point not recognized in $t2. Update the Task 2 block in start_all.ps1 to match its actual startup command." }

# Task 3: Meeting-to-Scope, port 8002
$py3 = Get-Python $t3
$started += Start-App 'Task 3 Meeting-to-Scope' $t3 $py3 @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8002')

Start-Sleep -Seconds 3
$null = Wait-Health 'Task 1' 'http://127.0.0.1:8000/health'
$null = Wait-Health 'Task 2' 'http://127.0.0.1:8001/health'
$null = Wait-Health 'Task 3' 'http://127.0.0.1:8002/health'
Write-Host "`nStarted processes (logs in $LogDir):" -ForegroundColor Green
$started | Format-Table -AutoSize
Write-Host 'Task 1 health:  http://127.0.0.1:8000/health'
Write-Host 'Task 1 Swagger: http://127.0.0.1:8000/docs'
Write-Host 'Task 2 health:  http://127.0.0.1:8001/health'
Write-Host 'Task 2 Swagger: http://127.0.0.1:8001/docs'
Write-Host 'Task 3 health:  http://127.0.0.1:8002/health'
Write-Host 'Task 3 Swagger: http://127.0.0.1:8002/docs'
if (!$NoBrowser) { Start-Process 'http://127.0.0.1:8000/docs' -ErrorAction SilentlyContinue }
