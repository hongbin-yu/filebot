@echo off
echo ========================================
echo PCL Conversion Command Test Script
echo ========================================
echo.

REM Set paths
set "PCL_DIR=C:\workspace\pcl_input"
set "OUTPUT_DIR=C:\workspace\pcl2pdf"
set "PCLXFORM_PATH=C:\Program Files (x86)\PageTech\PCLTSDK_190\PCLXForm.exe"
set "TEMPLATE_PATH=C:\Program Files (x86)\PageTech\PCLTSDK_870\default.tpt"

echo Checking if tool exists...
if exist "%PCLXFORM_PATH%" (
    echo ✓ PCLXForm.exe exists
) else (
    echo ✗ PCLXForm.exe does not exist: %PCLXFORM_PATH%
    pause
    exit /b 1
)

echo.
echo Checking if input directory exists...
if exist "%PCL_DIR%" (
    echo ✓ Input directory exists: %PCL_DIR%
) else (
    echo ✗ Input directory does not exist: %PCL_DIR%
    pause
    exit /b 1
)

echo.
echo Checking if template file exists...
if exist "%TEMPLATE_PATH%" (
    echo ✓ Template file exists
) else (
    echo ✗ Template file does not exist: %TEMPLATE_PATH%
    pause
    exit /b 1
)

echo.
echo ========================================
echo Test 1: List PCL files in input directory
echo ========================================
dir "%PCL_DIR%\*.pcl" /b

echo.
echo ========================================
echo Test 2: Test conversion command format
echo ========================================
echo Please manually test the following command formats:
echo.
echo Format A (inp=filename, inf=directory):
echo cd /d "C:\Program Files (x86)\PageTech\PCLTSDK_870"
echo PclXform.exe default.tpt inp="00000001.pcl" inf="C:\workspace\pcl_input" outp="test.pdf" outf="C:\workspace\pcl2pdf" Silent=true
echo.
echo Format B (inp=directory, inf=filename):
echo cd /d "C:\Program Files (x86)\PageTech\PCLTSDK_870"
echo PclXform.exe default.tpt inp="C:\workspace\pcl_input" inf="00000001.pcl" outp="C:\workspace\pcl2pdf" outf="test.pdf" Silent=true
echo.
echo Please copy one of the commands to command prompt for testing.
echo.
pause