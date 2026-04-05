@echo off
chcp 65001 >nul
echo ============================================
echo PCL to PDF Converter - Simple Launcher
echo ============================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Try these options:
    echo 1. Use full path to Python (e.g., C:\Python314\python.exe)
    echo 2. Add Python to System PATH
    echo.
    echo Quick test: check if Python is installed...
    if exist "C:\Python314\python.exe" (
        echo Found Python 3.14 at C:\Python314\
        set "PYTHON=C:\Python314\python.exe"
    ) else if exist "C:\Python313\python.exe" (
        echo Found Python 3.13 at C:\Python313\
        set "PYTHON=C:\Python313\python.exe"
    ) else if exist "C:\Python312\python.exe" (
        echo Found Python 3.12 at C:\Python312\
        set "PYTHON=C:\Python312\python.exe"
    ) else if exist "C:\Python311\python.exe" (
        echo Found Python 3.11 at C:\Python311\
        set "PYTHON=C:\Python311\python.exe"
    ) else if exist "C:\Python39\python.exe" (
        echo Found Python 3.9 at C:\Python39\
        set "PYTHON=C:\Python39\python.exe"
    ) else (
        echo Python not found in standard locations
        echo Please install Python from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
) else (
    echo [OK] Python found
    python --version
    set "PYTHON=python"
)

echo.
echo Checking dependencies...
%PYTHON% -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    %PYTHON% -m pip install flask requests python-dotenv
) else (
    echo [OK] Dependencies already installed
)

echo.
echo Creating directories...
if not exist "C:\workspace\pcl-uploads" mkdir "C:\workspace\pcl-uploads"
if not exist "C:\workspace\pcl-converted" mkdir "C:\workspace\pcl-converted"

echo.
echo Starting Flask application...
echo Web Interface: http://localhost:5000
echo Health Check: http://localhost:5000/health
echo Press Ctrl+C to stop
echo ============================================
echo.

%PYTHON% app_windows_optimized.py

pause