@echo off
echo ========================================
echo PCL Conversion Scheduled Task Uninstall Script
echo ========================================
echo.

set "TASK_NAME=PCL File Converter"

echo Task name: %TASK_NAME%
echo.

REM Check administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: Administrator privileges required to fully delete task
    echo But attempting to delete anyway...
)

echo 1. Stopping task (if running)...
schtasks /end /tn "%TASK_NAME%" >nul 2>&1
if errorlevel 0 (
    echo ✓ Task stopped
) else (
    echo ℹ Task not running or does not exist
)

echo.
echo 2. Deleting scheduled task...
schtasks /delete /tn "%TASK_NAME%" /f
if errorlevel 0 (
    echo ✓ Scheduled task deleted: %TASK_NAME%
) else (
    echo ✗ Deletion failed or task does not exist
    echo.
    echo Manual deletion steps:
    echo 1. Open "Task Scheduler"
    echo 2. Select "Task Scheduler Library" on the left
    echo 3. Find task "%TASK_NAME%" in the middle
    echo 4. Right-click -> Delete
)

echo.
echo 3. Cleanup suggestions (optional):
echo To clean up all related directories, manually delete:
echo   C:\workspace\pcl_input\
echo   C:\workspace\pcl2pdf\
echo   C:\workspace\pcl_processed\
echo   C:\workspace\pcl_failed\
echo   C:\workspace\pcl_logs\
echo.
echo Note: These directories may contain important files, delete with caution
echo.
echo ========================================
echo Uninstallation complete
echo ========================================
echo.
pause