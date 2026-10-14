@echo off
where python >nul 2>&1 && (
  python "%~dp0agent-capacity" %*
  exit /b %ERRORLEVEL%
)
py -3 "%~dp0agent-capacity" %*
