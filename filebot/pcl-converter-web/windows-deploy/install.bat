@echo off
chcp 65001 >nul
title PCL Converter - Installation Program
echo ========================================
echo   PCL to PDF Converter - Windows Installer
echo ========================================
echo.

REM Check administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [Warning] Administrator privileges required to install PCL conversion tools
    echo Please right-click this file and select "Run as administrator"
    echo.
    set /p admin_confirm="Continue installation? (Y/N): "
    if /i not "%admin_confirm%"=="Y" (
        echo Installation cancelled
        pause
        exit /b 1
    )
)

echo Step 1: Checking system environment...
echo.

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] Python not found
    echo Opening Python download page...
    start https://www.python.org/downloads/
    echo Please install Python 3.8+ and check "Add Python to PATH" during installation
    echo Re-run this installer after Python installation
    pause
    exit /b 1
)

echo ✓ Python installed
python --version
echo.

REM Check pip
where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] pip not found
    echo Attempting to install pip...
    python -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        echo [Error] pip installation failed
        pause
        exit /b 1
    )
)

echo ✓ pip installed
pip --version
echo.

echo Step 2: Installing Python dependencies...
echo.
if exist "requirements.txt" (
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [Warning] Some dependencies failed to install, continuing...
    )
    echo ✓ Python dependencies installed
) else (
    echo [Error] requirements.txt not found
    pause
    exit /b 1
)

echo.
echo Step 3: Creating application directories...
echo.
if not exist "uploads" mkdir uploads
if not exist "converted" mkdir converted
if not exist "logs" mkdir logs
if not exist "tools" mkdir tools

echo ✓ Directory structure created
echo.
echo Step 4: Checking PCL conversion tools...
echo.

REM Check common PCL tools
set TOOL_FOUND=0

echo Checking system PATH for PCL conversion tools...
where gpcl6 >nul 2>nul && (
    echo ✓ Found GhostPCL (gpcl6.exe)
    set TOOL_FOUND=1
)

where pcl6 >nul 2>nul && (
    echo ✓ Found PCL6 (pcl6.exe)
    set TOOL_FOUND=1
)

where pcltopdf >nul 2>nul && (
    echo ✓ Found pcltopdf.exe
    set TOOL_FOUND=1
)

if %TOOL_FOUND%==0 (
    echo [Warning] No PCL conversion tools found
    echo.
    echo Please choose installation option:
    echo 1) Manually install PCL tools and re-run this program
    echo 2) Continue installation, configure tool path later
    echo.
    set /p tool_choice="Please choose (1/2): "
    
    if "%tool_choice%"=="1" (
        echo.
        echo Recommended installation:
        echo 1. GhostPCL - included in Ghostscript commercial version
        echo 2. pcltopdf - open source tool, requires compilation from source
        echo.
        echo Re-run this program after installation
        pause
        exit /b 0
    )
)

echo.
echo Step 5: Creating configuration file...
echo.
if not exist ".env" (
    (
        echo # Flask configuration
        echo SECRET_KEY=change-this-in-production-%RANDOM%-%RANDOM%-%RANDOM%
        echo DEBUG=False
        echo.
        echo # File storage
        echo UPLOAD_FOLDER=uploads
        echo CONVERTED_FOLDER=converted
        echo MAX_CONTENT_MB=100
        echo.
        echo # PCL tool configuration
        echo # Uncomment and modify the following path
        echo # PCL_TOOL_PATH=C:\Program Files\Ghostscript\bin\gpcl6.exe
        echo # Or use auto for automatic detection
        echo PCL_TOOL_PATH=auto
        echo.
        echo # FileBot backend API (optional)
        echo # FILEBOT_API_URL=http://localhost:8000/api/v1
        echo # FILEBOT_USERNAME=admin
        echo # FILEBOT_PASSWORD=admin123
    ) > .env
    echo ✓ Configuration file created (.env)
)

echo.
echo Step 6: Creating desktop shortcut...
echo.
set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=PCL Converter.lnk
set TARGET_PATH=%SCRIPT_DIR%run.bat
set ICON_PATH=%SCRIPT_DIR%..\..\..\..\..\..\..\windows\system32\shell32.dll

REM Check if creating desktop shortcut
echo Create desktop shortcut?
set /p create_shortcut="(Y/N): "
if /i "%create_shortcut%"=="Y" (
    REM Use powershell to create shortcut
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\%SHORTCUT_NAME%'); $s.TargetPath = '%TARGET_PATH%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()" >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✓ Desktop shortcut created
    ) else (
        echo [Warning] Shortcut creation failed, please create manually
    )
)

echo.
echo ========================================
echo           Installation Complete!
echo ========================================
echo.
echo Installation complete! Next steps:
echo.
echo 1. Start application: Double-click run.bat
echo 2. Open browser: http://localhost:5000
echo 3. Ensure PCL conversion tools are properly installed and configured
echo.
echo Configuration file: .env
echo Upload directory: uploads\
echo Converted files directory: converted\
echo.
echo To configure PCL tool path, edit .env file
echo Change PCL_TOOL_PATH=auto to actual path
echo Example: PCL_TOOL_PATH=C:\Program Files\Ghostscript\bin\gpcl6.exe
echo.
pause