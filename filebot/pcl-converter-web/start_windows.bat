@echo off
echo ============================================
echo PCL转PDF转换器 - Windows启动脚本
echo ============================================
echo.

rem 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装
    pause
    exit /b 1
)

rem 激活虚拟环境
if not exist "venv_win\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在，请先运行install_windows.bat
    pause
    exit /b 1
)

call venv_win\Scripts\activate

rem 设置环境变量（可选）
set FLASK_APP=app_windows_optimized.py
set FLASK_ENV=production

rem 检查必要目录
if not exist "C:\workspace\pcl-uploads" mkdir "C:\workspace\pcl-uploads"
if not exist "C:\workspace\pcl-converted" mkdir "C:\workspace\pcl-converted"

echo.
echo 启动Flask应用...
echo 访问地址: http://localhost:5000
echo 按Ctrl+C停止应用
echo ============================================
echo.

python app_windows_optimized.py

pause