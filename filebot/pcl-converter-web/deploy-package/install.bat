@echo off
chcp 65001 >nul
title PCL转换器 - 安装程序
echo ========================================
echo   PCL to PDF Converter - Windows安装程序
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 需要管理员权限以安装PCL转换工具
    echo 请右键点击此文件，选择"以管理员身份运行"
    echo.
    set /p admin_confirm="继续安装？(Y/N): "
    if /i not "%admin_confirm%"=="Y" (
        echo 安装已取消
        pause
        exit /b 1
    )
)

echo 步骤1: 检查系统环境...
echo.

REM 检查Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Python
    echo 正在打开Python下载页面...
    start https://www.python.org/downloads/
    echo 请安装Python 3.8+，安装时勾选"Add Python to PATH"
    echo 安装完成后重新运行此安装程序
    pause
    exit /b 1
)

echo ✓ Python已安装
python --version
echo.

REM 检查pip
where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到pip
    echo 尝试安装pip...
    python -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        echo [错误] pip安装失败
        pause
        exit /b 1
    )
)

echo ✓ pip已安装
pip --version
echo.

echo 步骤2: 安装Python依赖...
echo.
if exist "requirements.txt" (
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [警告] 部分依赖安装失败，尝试继续...
    )
    echo ✓ Python依赖安装完成
) else (
    echo [错误] 未找到requirements.txt
    pause
    exit /b 1
)

echo.
echo 步骤3: 创建应用目录...
echo.
if not exist "uploads" mkdir uploads
if not exist "converted" mkdir converted
if not exist "logs" mkdir logs
if not exist "tools" mkdir tools

echo ✓ 目录结构创建完成
echo.
echo 步骤4: PCL转换工具检查...
echo.

REM 检查常见PCL工具
set TOOL_FOUND=0

echo 检查系统PATH中的PCL转换工具...
where gpcl6 >nul 2>nul && (
    echo ✓ 找到 GhostPCL (gpcl6.exe)
    set TOOL_FOUND=1
)

where pcl6 >nul 2>nul && (
    echo ✓ 找到 PCL6 (pcl6.exe)
    set TOOL_FOUND=1
)

where pcltopdf >nul 2>nul && (
    echo ✓ 找到 pcltopdf.exe
    set TOOL_FOUND=1
)

if %TOOL_FOUND%==0 (
    echo [警告] 未找到PCL转换工具
    echo.
    echo 请选择安装选项:
    echo 1) 手动安装PCL工具后重新运行此程序
    echo 2) 继续安装，稍后配置工具路径
    echo.
    set /p tool_choice="请选择 (1/2): "
    
    if "%tool_choice%"=="1" (
        echo.
        echo 推荐安装:
        echo 1. GhostPCL - 包含在Ghostscript商业版中
        echo 2. pcltopdf - 开源工具，需从源代码编译
        echo.
        echo 安装完成后重新运行此程序
        pause
        exit /b 0
    )
)

echo.
echo 步骤5: 创建配置文件...
echo.
if not exist ".env" (
    (
        echo # Flask配置
        echo SECRET_KEY=change-this-in-production-%RANDOM%-%RANDOM%-%RANDOM%
        echo DEBUG=False
        echo.
        echo # 文件存储
        echo UPLOAD_FOLDER=uploads
        echo CONVERTED_FOLDER=converted
        echo MAX_CONTENT_MB=100
        echo.
        echo # PCL工具配置
        echo # 取消注释并修改以下路径
        echo # PCL_TOOL_PATH=C:\Program Files\Ghostscript\bin\gpcl6.exe
        echo # 或使用auto自动检测（增强版推荐）
        echo PCL_TOOL_PATH=auto
        echo.
        echo # 增强版配置
        echo ADMIN_TOKEN=dev-admin-token-change-in-production
        echo STATS_ENABLED=True
        echo.
        echo # FileBot后端API（可选）
        echo # FILEBOT_API_URL=http://localhost:8000/api/v1
        echo # FILEBOT_USERNAME=admin
        echo # FILEBOT_PASSWORD=admin123
    ) > .env
    echo ✓ 配置文件已创建 (.env)
)

echo.
echo 步骤6: 创建桌面快捷方式...
echo.
set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=PCL转换器.lnk
set TARGET_PATH=%SCRIPT_DIR%run.bat
set ICON_PATH=%SCRIPT_DIR%..\..\..\..\..\..\..\windows\system32\shell32.dll

REM 检查是否在桌面创建快捷方式
echo 是否在桌面创建快捷方式？
set /p create_shortcut="(Y/N): "
if /i "%create_shortcut%"=="Y" (
    REM 需要powershell创建快捷方式
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\%SHORTCUT_NAME%'); $s.TargetPath = '%TARGET_PATH%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()" >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✓ 桌面快捷方式已创建
    ) else (
        echo [警告] 快捷方式创建失败，请手动创建
    )
)

echo.
echo ========================================
echo           安装完成！
echo ========================================
echo.
echo 安装完成！以下是下一步：
echo.
echo 1. 启动增强版应用（推荐）: 双击 run_enhanced.bat
echo 2. 或启动标准版应用: 双击 run.bat
echo 3. 打开浏览器访问: http://localhost:5000
echo 4. 确保PCL转换工具已正确安装和配置
echo.
echo 配置文件位置: .env
echo 上传文件目录: uploads\
echo 转换文件目录: converted\
echo.
echo 增强版功能:
echo   • 专业Web界面和实时监控
echo   • 智能工具检测和选择
echo   • 详细错误处理和统计
echo   • 多步骤转换进度显示
echo.
echo 如需配置PCL工具路径，请编辑 .env 文件
echo 将 PCL_TOOL_PATH=auto 修改为实际路径
echo 例如: PCL_TOOL_PATH=C:\Program Files\Ghostscript\bin\gpcl6.exe
echo.
pause