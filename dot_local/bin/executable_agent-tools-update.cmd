@echo off
where python >nul 2>nul
if errorlevel 1 goto use_py
python "%~dp0agent-tools-update" %*
exit /b %errorlevel%
:use_py
py -3 "%~dp0agent-tools-update" %*
exit /b %errorlevel%
