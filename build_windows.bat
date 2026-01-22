@echo off
REM ============================================
REM AI Manager v11.0 - Windows Build Script
REM ============================================

echo ============================================
echo AI Manager v11.0 - Build for Windows
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

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
    --hidden-import customtkinter ^
    --hidden-import requests ^
    --hidden-import keyring ^
    --hidden-import keyring.backends ^
    --collect-all customtkinter ^
    --clean ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo.
    echo Build failed. Trying without optional imports...
    pyinstaller --onefile ^
        --windowed ^
        --name "AI_Manager" ^
        --hidden-import customtkinter ^
        --collect-all customtkinter ^
        --clean ^
        --noconfirm ^
        main.py
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
echo Optional: Run "python build_windows.py --installer" to create
echo           Inno Setup installer script
echo.
pause
