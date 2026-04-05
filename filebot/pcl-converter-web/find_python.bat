@echo off
echo Python Diagnostic Tool
echo ======================
echo.

echo 1. Checking PATH...
where python
echo.

echo 2. Checking common Python locations...
if exist "C:\Python314\python.exe" echo Found: C:\Python314\python.exe
if exist "C:\Python313\python.exe" echo Found: C:\Python313\python.exe
if exist "C:\Python312\python.exe" echo Found: C:\Python312\python.exe
if exist "C:\Python311\python.exe" echo Found: C:\Python311\python.exe
if exist "C:\Python310\python.exe" echo Found: C:\Python310\python.exe
if exist "C:\Python39\python.exe" echo Found: C:\Python39\python.exe
if exist "C:\Program Files\Python*\python.exe" (
    for /f "delims=" %%i in ('dir /b "C:\Program Files\Python*\python.exe" 2^>nul') do echo Found: %%i
)
if exist "C:\Program Files (x86)\Python*\python.exe" (
    for /f "delims=" %%i in ('dir /b "C:\Program Files (x86)\Python*\python.exe" 2^>nul') do echo Found: %%i
)
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python*\python.exe" (
    for /f "delims=" %%i in ('dir /b "%USERPROFILE%\AppData\Local\Programs\Python\Python*\python.exe" 2^>nul') do echo Found: %%i
)

echo.
echo 3. Current Python version (if in PATH):
python --version 2>nul || echo Python not found in PATH

echo.
echo 4. Solution:
echo If Python is installed but not in PATH:
echo - Option A: Add Python to PATH (recommended)
echo - Option B: Use full path to Python
echo   Example: "C:\Python314\python.exe" app_windows_optimized.py
echo.

pause