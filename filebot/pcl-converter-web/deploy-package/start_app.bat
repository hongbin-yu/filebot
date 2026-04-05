@echo off
chcp 65001 >nul
echo ========================================
echo   PCL转PDF转换器 - Windows启动脚本
echo ========================================
echo.

REM 重命名应用文件（如果存在）
if exist "app_win.py" (
    if not exist "app.py" (
        echo 正在设置应用文件...
        copy "app_win.py" "app.py" >nul
    )
)

REM 运行主启动脚本
if exist "run.bat" (
    call run.bat
) else (
    echo [错误] 未找到run.bat
    pause
)