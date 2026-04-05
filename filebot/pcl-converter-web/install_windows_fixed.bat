@echo off
chcp 65001 >nul
echo ============================================
echo PCL to PDF Converter - Windows Installation
echo ============================================
echo.

echo Step 1: Check Python Installation
echo ----------------------------------
echo Searching for Python in PATH...
where python >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Python not found in PATH
    echo.
    echo Searching for Python in common locations...
    
    set FOUND=0
    
    if exist "C:\Python39\python.exe" (
        echo Found: C:\Python39\python.exe
        set "PYTHON_PATH=C:\Python39\python.exe"
        set FOUND=1
    )
    
    if exist "C:\Python310\python.exe" (
        echo Found: C:\Python310\python.exe
        set "PYTHON_PATH=C:\Python310\python.exe"
        set FOUND=1
    )
    
    if exist "C:\Python311\python.exe" (
        echo Found: C:\Python311\python.exe
        set "PYTHON_PATH=C:\Python311\python.exe"
        set FOUND=1
    )
    
    if exist "C:\Python312\python.exe" (
        echo Found: C:\Python312\python.exe
        set "PYTHON_PATH=C:\Python312\python.exe"
        set FOUND=1
    )
    
    if exist "C:\Python313\python.exe" (
        echo Found: C:\Python313\python.exe
        set "PYTHON_PATH=C:\Python313\python.exe"
        set FOUND=1
    )
    
    if exist "C:\Python314\python.exe" (
        echo Found: C:\Python314\python.exe
        set "PYTHON_PATH=C:\Python314\python.exe"
        set FOUND=1
    )
    
    if exist "C:\Program Files\Python*\python.exe" (
        for /f "delims=" %%i in ('dir /b "C:\Program Files\Python*\python.exe" 2^>nul') do (
            echo Found: %%i
            set "PYTHON_PATH=%%i"
            set FOUND=1
        )
    )
    
    if exist "C:\Program Files (x86)\Python*\python.exe" (
        for /f "delims=" %%i in ('dir /b "C:\Program Files (x86)\Python*\python.exe" 2^>nul') do (
            echo Found: %%i
            set "PYTHON_PATH=%%i"
            set FOUND=1
        )
    )
    
    if %FOUND%==0 (
        echo [ERROR] Python not found!
        echo.
        echo Please install Python 3.9+ from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation
        echo.
        pause
        exit /b 1
    ) else (
        echo.
        echo Using Python at: %PYTHON_PATH%
        echo To make Python available everywhere, add its folder to System PATH
        echo.
        set "PYTHON=%PYTHON_PATH%"
    )
) else (
    echo [OK] Python found in PATH
    python --version
    set "PYTHON=python"
)

echo.
echo Step 2: Create Virtual Environment
echo ----------------------------------
if not exist "venv_win" (
    echo Creating virtual environment...
    %PYTHON% -m venv venv_win
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        echo Trying without virtual environment...
        set "NO_VENV=1"
    ) else (
        echo Virtual environment created
        set "NO_VENV=0"
    )
) else (
    echo Virtual environment already exists
    set "NO_VENV=0"
)

echo.
echo Step 3: Install Dependencies
echo ----------------------------
if %NO_VENV%==0 (
    echo Activating virtual environment...
    call venv_win\Scripts\activate
    if errorlevel 1 (
        echo [WARNING] Failed to activate virtual environment
        echo Installing globally (not recommended)
        set "NO_VENV=1"
    )
)

if %NO_VENV%==1 (
    echo Installing Flask, requests, python-dotenv globally...
    %PYTHON% -m pip install flask requests python-dotenv
) else (
    echo Installing Flask, requests, python-dotenv in virtual environment...
    pip install flask requests python-dotenv
)

echo.
echo Step 4: Check PageTech PCLTSDK Installation
echo -------------------------------------------
if exist "C:\workspace\PCLTSDK_870\PclXform.exe" (
    echo [OK] Found PclXform.exe in workspace
    echo Location: C:\workspace\PCLTSDK_870\
) else if exist "C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe" (
    echo [OK] Found PclXform.exe in default location
    echo Location: C:\Program Files (x86)\PageTech\PCLTSDK_870\
) else (
    echo [WARNING] PclXform.exe not found
    echo Please ensure PageTech PCLTSDK is installed
    echo You can download it from: https://www.pagetechnology.com/
    echo.
    echo For testing, you can use the SDK in: C:\workspace\PCLTSDK_870\
)

echo.
echo Step 5: Check FileBot API Configuration
echo ---------------------------------------
echo FileBot API URL: http://localhost:8000/api/v1
echo Note: This is optional. The converter works without FileBot.
echo.

echo Step 6: Create Required Directories
echo -----------------------------------
if not exist "C:\workspace\pcl-uploads" (
    mkdir "C:\workspace\pcl-uploads"
    echo Created: C:\workspace\pcl-uploads
) else (
    echo Directory exists: C:\workspace\pcl-uploads
)

if not exist "C:\workspace\pcl-converted" (
    mkdir "C:\workspace\pcl-converted"
    echo Created: C:\workspace\pcl-converted
) else (
    echo Directory exists: C:\workspace\pcl-converted
)

echo.
echo ============================================
echo INSTALLATION COMPLETE!
echo.
echo To start the application:
echo.
if %NO_VENV%==0 (
    echo Option 1: Double-click start_windows.bat
    echo Option 2: Run in command line:
    echo    cd C:\workspace\pcl-converter-web
    echo    venv_win\Scripts\activate
    echo    python app_windows_optimized.py
) else (
    echo Run in command line:
    echo    cd C:\workspace\pcl-converter-web
    echo    python app_windows_optimized.py
)
echo.
echo Web Interface: http://localhost:5000
echo Health Check: http://localhost:5000/health
echo.
echo Troubleshooting:
echo - If port 5000 is in use, edit app_windows_optimized.py
echo - Check logs in: C:\workspace\pcl-converter-web\logs\
echo ============================================
echo.
pause