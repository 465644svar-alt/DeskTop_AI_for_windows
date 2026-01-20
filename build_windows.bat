@echo off
REM ============================================
REM AI Manager - Windows Build Script
REM ============================================

echo ============================================
echo AI Manager - Build for Windows
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo [3/4] Building executable...
pyinstaller --onefile ^
    --windowed ^
    --name "AI_Manager" ^
    --add-data "config.json;." ^
    --icon "icon.ico" ^
    --clean ^
    main_app.py

if errorlevel 1 (
    echo.
    echo Trying build without icon...
    pyinstaller --onefile ^
        --windowed ^
        --name "AI_Manager" ^
        --clean ^
        main_app.py
)

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Cleaning up...
rmdir /s /q build 2>nul
del /q *.spec 2>nul

echo.
echo ============================================
echo BUILD COMPLETE!
echo ============================================
echo.
echo Executable location: dist\AI_Manager.exe
echo.
echo To run: double-click AI_Manager.exe in the dist folder
echo.
pause
