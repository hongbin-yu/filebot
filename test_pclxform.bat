@echo off
echo Testing PclXform.exe conversion...
echo.

REM Set paths
set TOOL_PATH="C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe"
set TEMPLATE_PATH="C:\Program Files (x86)\PageTech\PCLTSDK_870\default.tpt"
set INPUT_FILE=00000001.pcl
set INPUT_DIR=C:\workspace\sample
set OUTPUT_FILE=test_cmd.pdf
set OUTPUT_DIR=C:\workspace\pcl-converted

echo Tool: %TOOL_PATH%
echo Template: %TEMPLATE_PATH%
echo Input file: %INPUT_FILE%
echo Input dir: %INPUT_DIR%
echo Output file: %OUTPUT_FILE%
echo Output dir: %OUTPUT_DIR%
echo.

REM Run the conversion
echo Running conversion command...
cd /d "C:\Program Files (x86)\PageTech\PCLTSDK_870"
%TOOL_PATH% %TEMPLATE_PATH% inp="%INPUT_FILE%" inf="%INPUT_DIR%" outp="%OUTPUT_FILE%" outf="%OUTPUT_DIR%" Silent=true
echo Command executed.
set EXIT_CODE=%ERRORLEVEL%

echo.
echo Exit code: %EXIT_CODE%

REM Check if output file was created
if exist "%OUTPUT_DIR%\%OUTPUT_FILE%" (
    echo SUCCESS: Output file created at %OUTPUT_DIR%\%OUTPUT_FILE%
    dir "%OUTPUT_DIR%\%OUTPUT_FILE%"
) else (
    echo ERROR: Output file not found in %OUTPUT_DIR%\
    dir "%OUTPUT_DIR%\"
)

echo.
echo Test complete.