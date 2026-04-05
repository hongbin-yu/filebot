@echo off
chcp 65001 >nul
echo ========================================
echo   PCL to PDF Converter - Windows Launcher
echo ========================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] Python not found, please install Python 3.8+ first
    echo Download URL: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if pip is installed
where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] pip not found, make sure "Add Python to PATH" was checked during Python installation
    pause
    exit /b 1
)

REM Check dependencies
if not exist "requirements.txt" (
    echo [Error] requirements.txt file not found
    pause
    exit /b 1
)

echo Checking Python version...
python --version
echo.

echo Checking dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Warning] Dependencies installation failed, attempting to continue...
)

echo.
echo ========================================
echo   Starting PCL Converter Web Application...
echo ========================================
echo.
echo Application will open in browser: http://localhost:5000
echo Press Ctrl+C to stop application
echo.

REM Create necessary directories
if not exist "uploads" mkdir uploads
if not exist "converted" mkdir converted
if not exist "logs" mkdir logs

REM Set environment variables
set FLASK_APP=app.py
set FLASK_ENV=production

REM Start Flask application
python -m flask run --host=0.0.0.0 --port=5000

pause