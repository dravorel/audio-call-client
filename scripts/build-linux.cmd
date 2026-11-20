@echo off
setlocal
cd /d "%~dp0"

echo %cd%
wsl bash -c "./build-linux.sh"
if errorlevel 1 (
    echo Linux build failed
    exit /b 1
)

echo Linux build completed!
