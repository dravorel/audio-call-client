@echo off
setlocal
cd /d "%~dp0.."

REM Create virtual environment if it does not exist
if not exist "venv-windows\Scripts\python.exe" (
    python -m venv venv-windows
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call "venv-windows\Scripts\activate.bat"
if errorlevel 1 (
    echo Failed to activate environment
    exit /b 1
)

REM Install dependencies
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error installing dependencies
    exit /b 1
)

REM Install Pillow
python -m pip install Pillow
if errorlevel 1 (
    echo Error installing Pillow
    exit /b 1
)

REM Create icon
python scripts/png_to_ico.py icon.png build-windows/icon.ico
if errorlevel 1 (
    echo Error create icon
    exit /b 1
)

REM Install PyInstaller
python -m pip install PyInstaller
if errorlevel 1 (
    echo Error installing PyInstaller
    exit /b 1
)

REM Build executable
python -m PyInstaller ^
    --onefile ^
    --paths src ^
    --add-binary "external/windows/opus.dll;external/windows" ^
    --icon "icon.ico" ^
    --name voice-call ^
    --distpath dist ^
    --workpath build-windows ^
    --specpath build-windows ^
    --upx-dir "C:/Program Files/upx" ^
    src/main.py

if errorlevel 1 (
    echo Error building executable
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable: dist/voice-call.exe
