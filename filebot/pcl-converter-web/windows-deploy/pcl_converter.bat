@echo off
REM ============================================================
REM PCL File Automatic Conversion Script
REM Function: Monitor C:\workspace\pcl_input directory, convert PCL files to PDF
REM ============================================================

REM Set paths
set "INPUT_DIR=C:\workspace\pcl_input"
set "OUTPUT_DIR=C:\workspace\pcl2pdf"
set "PROCESSED_DIR=C:\workspace\pcl_processed"
set "FAILED_DIR=C:\workspace\pcl_failed"
set "LOG_DIR=C:\workspace\pcl_logs"

set "PCLXFORM_PATH=C:\Program Files (x86)\PageTech\PCLTSDK_190\PCLXForm.exe"
set "TEMPLATE_PATH=C:\Program Files (x86)\PageTech\PCLTSDK_870\default.tpt"

REM Get current timestamp using PowerShell (robust method)
set "ps_command=powershell -Command \"Get-Date -Format 'yyyyMMdd_HHmmss'\""
for /f "delims=" %%t in ('%ps_command% 2^>nul') do set "timestamp=%%t"

if "%timestamp%"=="" (
    REM Fallback method if PowerShell fails
    REM Create a simple timestamp from date and time
    set "date_part=%date%"
    set "time_part=%time%"
    
    REM Remove problematic characters from date
    set "date_clean=%date_part:/=-%"
    set "date_clean=%date_clean: =-%"
    set "date_clean=%date_clean:.=-%"
    
    REM Remove problematic characters from time
    set "time_clean=%time_part::=-%"
    set "time_clean=%time_clean:.=-%"
    set "time_clean=%time_clean: =-%"
    
    REM Create timestamp
    set "timestamp=%date_clean%_%time_clean%"
    
    REM For log file, use today's date in simple format
    set "log_date=unknown"
)

REM Extract date portion for log file name (first 8 characters: yyyyMMdd)
set "log_date=%timestamp:~0,8%"

REM Validate log_date contains only digits (yyyyMMdd format)
echo %log_date% | findstr /r "^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$" >nul
if errorlevel 1 (
    REM If not valid date format, use fallback
    set "log_date=fallback"
)

set "log_file=%LOG_DIR%\pcl_converter_%log_date%.log"

REM Ensure directories exist
if not exist "%INPUT_DIR%" mkdir "%INPUT_DIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if not exist "%PROCESSED_DIR%" mkdir "%PROCESSED_DIR%"
if not exist "%FAILED_DIR%" mkdir "%FAILED_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Logging function
:log
echo [%date% %time%] %* >> "%log_file%"
echo [%date% %time%] %*
exit /b

REM Start execution
call :log "============================================================"
call :log "PCL file conversion service starting"
call :log "Input directory: %INPUT_DIR%"
call :log "Output directory: %OUTPUT_DIR%"
call :log "Processed directory: %PROCESSED_DIR%"
call :log "Failed directory: %FAILED_DIR%"
call :log "Log file: %log_file%"
call :log "============================================================"

REM Check PCLXform tool
if not exist "%PCLXFORM_PATH%" (
    call :log "Error: PCLXform tool does not exist - %PCLXFORM_PATH%"
    exit /b 1
)

REM Switch to PCLXform directory
cd /d "C:\Program Files (x86)\PageTech\PCLTSDK_190"
if errorlevel 1 (
    call :log "Error: Cannot switch to PCLXform directory"
    exit /b 1
)

REM Statistics variables
set "total_count=0"
set "success_count=0"
set "fail_count=0"

REM Process all PCL files
call :log "Starting PCL file scan..."
for %%f in ("%INPUT_DIR%\*.pcl") do (
    set /a total_count+=1
    
    set "input_file=%%~nxf"
    set "input_path=%%f"
    set "output_file=%%~nf.pdf"
    set "output_path=%OUTPUT_DIR%\%%~nf.pdf"
    
    call :log "Processing file: %input_file%"
    
    REM Build conversion command
    REM Note: Choose appropriate parameter format based on test results
    REM Format A (inp=filename, inf=directory):
    REM PCLXForm.exe "%TEMPLATE_PATH%" inp="%input_file%" inf="%INPUT_DIR%" outp="%output_file%" outf="%OUTPUT_DIR%" Silent=true
    REM Format B (inp=directory, inf=filename): 
    REM PCLXForm.exe "%TEMPLATE_PATH%" inp="%INPUT_DIR%" inf="%input_file%" outp="%OUTPUT_DIR%" outf="%output_file%" Silent=true
    
    REM Use Format B (verified effective by test_pclxform.bat)
    call :log "Executing conversion: %input_file% -> %output_file%"
    PCLXForm.exe "%TEMPLATE_PATH%" inf="%INPUT_DIR%" inp="%input_file%" outf="%OUTPUT_DIR%" outp="%output_file%" Silent=true
    
    if errorlevel 1 (
        call :log "Conversion failed: %input_file% (error code: %errorlevel%)"
        
        REM Move failed file to failed directory
        set "failed_file=%FAILED_DIR%\failed_%timestamp%_%input_file%"
        move "%%f" "%failed_file%" >nul
        if errorlevel 1 (
            call :log "Warning: Cannot move failed file"
        ) else (
            call :log "Moving failed file to: %failed_file%"
        )
        
        set /a fail_count+=1
    ) else (
        REM Check if output file exists
        if exist "%output_path%" (
            REM Get file size
            for %%s in ("%output_path%") do set "filesize=%%~zs"
            if "!filesize!" GTR "0" (
                call :log "Conversion successful: %output_file% (size: !filesize! bytes)"
                
                REM Move processed file to processed directory
                set "processed_file=%PROCESSED_DIR%\processed_%timestamp%_%input_file%"
                move "%%f" "%processed_file%" >nul
                if errorlevel 1 (
                    call :log "Warning: Cannot move processed file"
                ) else (
                    call :log "Moving processed file to: %processed_file%"
                )
                
                set /a success_count+=1
            ) else (
                call :log "Conversion failed: Output file is empty"
                
                REM Move failed file
                set "failed_file=%FAILED_DIR%\failed_%timestamp%_%input_file%"
                move "%%f" "%failed_file%" >nul
                call :log "Moving failed file to: %failed_file%"
                
                set /a fail_count+=1
                
                REM Delete empty output file
                del "%output_path%" >nul 2>&1
            )
        ) else (
            call :log "Conversion failed: Output file does not exist"
            
            set "failed_file=%FAILED_DIR%\failed_%timestamp%_%input_file%"
            move "%%f" "%failed_file%" >nul
            call :log "Moving failed file to: %failed_file%"
            
            set /a fail_count+=1
        )
    )
    
    call :log "----------------------------------------"
)

REM Output statistics
call :log "Processing complete: Total %total_count% files"
if %total_count% GTR 0 (
    call :log "Successful: %success_count% files"
    call :log "Failed: %fail_count% files"
    
    REM Calculate success rate
    set /a success_rate=(success_count*100)/total_count
    call :log "Success rate: %success_rate%%%"
) else (
    call :log "No PCL files found for processing"
)

call :log "============================================================"
call :log "PCL file conversion service completed"
call :log ""

REM If delayed variable expansion was used, need to restore
endlocal

exit /b 0