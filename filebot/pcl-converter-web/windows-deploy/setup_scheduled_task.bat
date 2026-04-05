@echo off
echo ========================================
echo PCL Conversion Scheduled Task Configuration Script
echo ========================================
echo.

REM Check administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Administrator privileges required to run this script
    echo Please run command prompt as administrator
    pause
    exit /b 1
)

set "TASK_NAME=PCL File Converter"
set "SCRIPT_PATH=%~dp0pcl_converter.bat"
set "TRIGGER_TYPE=MINUTE"  REM Trigger type: MINUTE=every minute, STARTUP=on startup, LOGON=on logon

echo Task name: %TASK_NAME%
echo Script path: %SCRIPT_PATH%
echo Trigger type: %TRIGGER_TYPE%
echo.

REM Check if script exists
if not exist "%SCRIPT_PATH%" (
    echo Error: Conversion script not found: %SCRIPT_PATH%
    echo Make sure pcl_converter.bat is in the same directory as this script
    pause
    exit /b 1
)

echo 1. Deleting existing task (if exists)...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
if errorlevel 0 (
    echo ✓ Existing task deleted
) else (
    echo ℹ No existing task found
)

echo.
echo 2. Creating new scheduled task...

REM Set parameters based on trigger type
if "%TRIGGER_TYPE%"=="MINUTE" (
    REM Run every minute
    set "TRIGGER=/sc minute /mo 1"
    set "TRIGGER_DESC=Run every minute"
) else if "%TRIGGER_TYPE%"=="STARTUP" (
    REM Run on system startup
    set "TRIGGER=/sc onstart"
    set "TRIGGER_DESC=Run on system startup"
) else if "%TRIGGER_TYPE%"=="LOGON" (
    REM Run on user logon
    set "TRIGGER=/sc onlogon"
    set "TRIGGER_DESC=Run on user logon"
) else (
    set "TRIGGER=/sc minute /mo 1"
    set "TRIGGER_DESC=Run every minute"
)

REM Create scheduled task
echo Task configuration: %TRIGGER_DESC%
echo Creating task, please wait...

schtasks /create /tn "%TASK_NAME%" /tr "%SCRIPT_PATH%" %TRIGGER% /ru SYSTEM /rl HIGHEST /f
if errorlevel 1 (
    echo Error: Failed to create scheduled task
    echo.
    echo Manual creation steps:
    echo 1. Open "Task Scheduler"
    echo 2. Click "Create Basic Task"
    echo 3. Name: "PCL File Converter"
    echo 4. Trigger: "Daily" -> Start time: now, Repeat interval: 1 minute
    echo 5. Action: "Start a program" -> Program: %SCRIPT_PATH%
    echo 6. Finish
    pause
    exit /b 1
)

echo ✓ Scheduled task created successfully
echo.

echo 3. Verifying task status...
schtasks /query /tn "%TASK_NAME%" /fo list | findstr /i "Status"
if errorlevel 1 (
    echo ℹ Unable to retrieve task status
) else (
    schtasks /query /tn "%TASK_NAME%" /fo list | findstr /i "Status"
)

echo.
echo 4. Testing task execution...
echo Manually running task for testing...
schtasks /run /tn "%TASK_NAME%"
if errorlevel 0 (
    echo ✓ Task triggered, check logs to confirm conversion works
) else (
    echo ⚠ Unable to trigger task, may need to wait for scheduled execution
)

echo.
echo ========================================
echo Configuration complete
echo ========================================
echo.
echo Important information:
echo 1. Conversion script: %SCRIPT_PATH%
echo 2. Input directory: C:\workspace\pcl_input
echo 3. Output directory: C:\workspace\pcl2pdf
echo 4. Log directory: C:\workspace\pcl_logs
echo 5. Task will run: %TRIGGER_DESC%
echo.
echo Place PCL files in: C:\workspace\pcl_input
echo Converted PDFs will be saved in: C:\workspace\pcl2pdf
echo Log files are saved in: C:\workspace\pcl_logs
echo.
echo To delete task, run:
echo schtasks /delete /tn "%TASK_NAME%" /f
echo.
pause