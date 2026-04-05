@echo off
chcp 65001 >nul
title PCL转PDF专业转换器 - 增强版
echo ========================================
echo   PCL转PDF专业转换器 - 增强版启动器
echo ========================================
echo.

REM 检查Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Python
    echo 请安装Python 3.8+并确保已添加到PATH
    echo 或运行 install.bat 进行自动安装
    pause
    exit /b 1
)

echo ✓ Python已安装
python --version
echo.

REM 检查依赖
if exist "requirements.txt" (
    echo 检查Python依赖...
    pip install -r requirements.txt >nul 2>nul
    if %errorlevel% equ 0 (
        echo ✓ Python依赖检查完成
    ) else (
        echo [警告] 部分依赖安装失败，尝试继续...
    )
)

REM 确保目录存在
if not exist "uploads" mkdir uploads
if not exist "converted" mkdir converted
if not exist "logs" mkdir logs
if not exist "tools" mkdir tools

echo.
echo 正在启动增强版PCL转换器...
echo.

REM 启动应用
python app_enhanced.py

echo.
echo 应用已停止。
echo 按任意键退出...
pause >nul