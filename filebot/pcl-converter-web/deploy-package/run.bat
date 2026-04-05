@echo off
chcp 65001 >nul
echo ========================================
echo   PCL to PDF Converter - Windows启动脚本
echo ========================================
echo.

REM 检查Python是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查pip是否安装
where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到pip，请确保Python安装时勾选了"Add Python to PATH"
    pause
    exit /b 1
)

REM 检查依赖
if not exist "requirements.txt" (
    echo [错误] 未找到requirements.txt文件
    pause
    exit /b 1
)

echo 检查Python版本...
python --version
echo.

echo 检查依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [警告] 依赖安装失败，尝试继续运行...
)

echo.
echo ========================================
echo   启动PCL转换器Web应用...
echo ========================================
echo.
echo 应用将在浏览器中打开: http://localhost:5000
echo 按Ctrl+C停止应用
echo.

REM 创建必要的目录
if not exist "uploads" mkdir uploads
if not exist "converted" mkdir converted
if not exist "logs" mkdir logs

REM 设置环境变量
set FLASK_APP=app.py
set FLASK_ENV=production

REM 启动Flask应用
python -m flask run --host=0.0.0.0 --port=5000

pause