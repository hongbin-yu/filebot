@echo off
echo ============================================
echo PCL转PDF转换器 - Windows安装脚本
echo ============================================
echo.
echo 步骤1: 检查Python安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或未添加到PATH
    echo 请从 https://www.python.org/downloads/ 下载Python 3.9+
    echo 安装时务必勾选"Add Python to PATH"
    pause
    exit /b 1
)

python --version
echo.

echo 步骤2: 创建虚拟环境
if not exist "venv_win" (
    echo 创建虚拟环境...
    python -m venv venv_win
) else (
    echo 虚拟环境已存在
)

echo.
echo 步骤3: 激活虚拟环境并安装依赖
call venv_win\Scripts\activate
pip install flask requests python-dotenv

echo.
echo 步骤4: 检查PageTech PCLTSDK安装
if exist "C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe" (
    echo [成功] 找到PclXform.exe
    echo 位置: C:\Program Files (x86)\PageTech\PCLTSDK_870\
) else (
    echo [警告] 未找到PclXform.exe
    echo 请确保PageTech PCLTSDK已安装到默认位置
    echo 如果需要更改路径，请修改app_windows_optimized.py中的工具检测逻辑
)

echo.
echo 步骤5: 检查FileBot API配置
echo FileBot API URL: http://localhost:8000/api/v1
echo 如果需要更改，请修改.env文件或环境变量

echo.
echo 步骤6: 创建必要目录
if not exist "C:\workspace\pcl-uploads" mkdir "C:\workspace\pcl-uploads"
if not exist "C:\workspace\pcl-converted" mkdir "C:\workspace\pcl-converted"
echo 上传目录: C:\workspace\pcl-uploads
echo 转换目录: C:\workspace\pcl-converted

echo.
echo ============================================
echo 安装完成！
echo.
echo 启动应用:
echo 1. 双击 start_windows.bat
echo 2. 或在命令行中运行: python app_windows_optimized.py
echo.
echo 访问地址: http://localhost:5000
echo 健康检查: http://localhost:5000/health
echo ============================================
pause