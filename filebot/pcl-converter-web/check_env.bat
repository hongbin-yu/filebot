@echo off
echo ============================================
echo PCL转PDF转换器 - 环境检查脚本
echo ============================================
echo.
echo [1] 检查Python安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未找到
    echo 请确保:
    echo 1. 已从python.org下载安装Python 3.9+
    echo 2. 安装时勾选了"Add Python to PATH"
    echo 3. 已重启电脑（长路径设置需要重启）
    echo.
    echo 临时解决方案:
    echo 使用完整路径运行Python，例如:
    echo "C:\Python39\python.exe" --version
) else (
    echo [成功] Python已安装
    python --version
)

echo.
echo [2] 检查PIP包管理器
pip --version >nul 2>&1
if errorlevel 1 (
    echo [警告] PIP未找到，尝试使用python -m pip
    python -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] PIP完全不可用
    ) else (
        echo [成功] PIP可通过python -m pip使用
        python -m pip --version
    )
) else (
    echo [成功] PIP已安装
    pip --version
)

echo.
echo [3] 检查PageTech PCLTSDK安装
echo 检查默认位置...
set FOUND=0
if exist "C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe" (
    echo [成功] 找到: C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe
    set FOUND=1
)
if exist "C:\workspace\PCLTSDK_870\PclXform.exe" (
    echo [成功] 找到: C:\workspace\PCLTSDK_870\PclXform.exe
    set FOUND=1
)
if %FOUND%==0 (
    echo [警告] 未找到PclXform.exe
    echo 请确保PageTech PCLTSDK已安装
    echo 默认检查位置:
    echo 1. C:\Program Files (x86)\PageTech\PCLTSDK_870\
    echo 2. C:\workspace\PCLTSDK_870\
)

echo.
echo [4] 检查项目文件
if exist "app_windows_optimized.py" (
    echo [成功] 主程序文件存在: app_windows_optimized.py
) else (
    echo [错误] 主程序文件不存在
    echo 请重新从WSL复制文件
)

if exist "templates\index.html" (
    echo [成功] 模板文件存在
) else (
    echo [警告] 模板文件缺失
)

echo.
echo [5] 检查工作目录
echo 当前目录: %CD%
echo 请确保在 C:\workspace\pcl-converter-web 目录下运行

echo.
echo [6] 检查FileBot API（可选）
curl --version >nul 2>&1
if errorlevel 1 (
    echo [信息] curl未安装，无法测试FileBot API连接
    echo 但这不是必须的，可以忽略
) else (
    echo [信息] 可以使用curl测试FileBot API
    echo 命令: curl http://localhost:8000/api/v1/health
)

echo.
echo ============================================
echo 环境检查完成
echo.
if exist "install_windows.bat" (
    echo 下一步: 运行 install_windows.bat
) else (
    echo 下一步: 手动安装依赖
    echo 1. python -m venv venv_win
    echo 2. venv_win\Scripts\activate
    echo 3. pip install flask requests python-dotenv
)

echo.
echo 按任意键退出...
pause >nul