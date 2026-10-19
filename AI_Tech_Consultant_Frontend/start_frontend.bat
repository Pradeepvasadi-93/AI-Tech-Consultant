@echo off
setlocal
cd /d "%~dp0"
if not exist node_modules (
  echo Installing frontend dependencies for the first run...
  call npm install
  if errorlevel 1 (
    echo.
    echo npm install failed. Check Node.js/npm and internet or registry access.
    pause
    exit /b 1
  )
)
call npm run dev
pause
