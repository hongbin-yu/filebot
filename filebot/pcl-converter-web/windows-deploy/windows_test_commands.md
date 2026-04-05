# Windows PCL转换测试命令指南

## 📋 测试前提条件
1. **Windows环境**：Windows 10/11 64位
2. **PCLXForm工具**：已安装PageTech PCLXForm工具
3. **目录结构**：已创建以下目录：
   - `C:\workspace\pcl_input` - 输入PCL文件目录
   - `C:\workspace\pcl2pdf` - 输出PDF目录
   - `C:\workspace\PCLTSDK_870` - PCLXForm工具目录

## 🔍 环境验证命令

### 1. 检查工具是否存在
```cmd
REM 检查PCLXForm.exe
dir "C:\workspace\PCLTSDK_870\PCLXForm.exe"
dir "C:\Program Files (x86)\PageTech\PCLTSDK_190\PCLXForm.exe"
dir "C:\Program Files\PageTech\PCLTSDK_870\PCLXForm.exe"

REM 检查模板文件
dir "C:\workspace\PCLTSDK_870\default.tpt"
dir "C:\Program Files (x86)\PageTech\PCLTSDK_870\default.tpt"
```

### 2. 检查测试目录
```cmd
REM 创建测试目录（如果不存在）
mkdir C:\workspace 2>nul
mkdir C:\workspace\pcl_input 2>nul
mkdir C:\workspace\pcl2pdf 2>nul
mkdir C:\workspace\test_results 2>nul

REM 验证目录权限
echo Testing write permissions... > C:\workspace\test_results\test.txt
if exist C:\workspace\test_results\test.txt (
    echo ✓ 目录可写权限正常
    del C:\workspace\test_results\test.txt
) else (
    echo ✗ 目录写权限失败
)
```

### 3. 检查网络连通性（用于FileBot API）
```cmd
REM 测试本地FileBot API
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/v1/auth/login -X POST -d "username=admin&password=admin123"

REM 如果curl不可用，使用powershell
powershell -Command "Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -Method GET"
```

## 🧪 PCL转换测试命令

### 1. 快速功能测试
```cmd
REM 切换到PCLXForm目录
cd /d "C:\workspace\PCLTSDK_870"

REM 测试1：显示帮助信息
PCLXForm.exe --help
PCLXForm.exe /?

REM 测试2：检查版本
PCLXForm.exe default.tpt -version
```

### 2. 单文件转换测试

**准备测试文件：**
```cmd
REM 如果没有PCL文件，可以创建测试文件或从示例复制
REM 创建简单的测试PCL文件（16字节最小PCL文件）
echo -e "\x1B%-12345X" > C:\workspace\pcl_input\test0001.pcl
echo "测试PCL文件" >> C:\workspace\pcl_input\test0001.pcl
echo -e "\x1B%-12345X" >> C:\workspace\pcl_input\test0001.pcl
```

**转换测试（格式A）：**
```cmd
cd /d "C:\workspace\PCLTSDK_870"
PCLXForm.exe default.tpt inp="test0001.pcl" inf="C:\workspace\pcl_input" outp="test_output.pdf" outf="C:\workspace\pcl2pdf" Silent=true
```

**转换测试（格式B）：**
```cmd
cd /d "C:\workspace\PCLTSDK_870"
PCLXForm.exe default.tpt inp="C:\workspace\pcl_input" inf="test0001.pcl" outp="C:\workspace\pcl2pdf" outf="test_output.pdf" Silent=true
```

**验证输出：**
```cmd
REM 检查PDF文件是否生成
dir C:\workspace\pcl2pdf\test_output.pdf

REM 检查文件大小
for %%f in ("C:\workspace\pcl2pdf\test_output.pdf") do (
    echo 文件大小: %%~zf 字节
    if %%~zf LEQ 0 (
        echo ✗ 警告：输出文件为空
    ) else (
        echo ✓ 输出文件正常
    )
)
```

### 3. 批量转换测试
```cmd
REM 创建多个测试文件
for /l %%i in (1,1,3) do (
    copy C:\workspace\pcl_input\test0001.pcl C:\workspace\pcl_input\test%%i.pcl >nul
)

REM 运行批量转换
cd /d "C:\workspace\PCLTSDK_870"
for %%f in ("C:\workspace\pcl_input\*.pcl") do (
    echo 转换文件: %%~nxf
    PCLXForm.exe default.tpt inp="C:\workspace\pcl_input" inf="%%~nxf" outf="C:\workspace\pcl2pdf" outp="%%~nf.pdf" Silent=true
    if !errorlevel! equ 0 (
        echo ✓ 成功: %%~nf.pdf
    ) else (
        echo ✗ 失败: %%~nxf
    )
)
```

## 🔄 完整工作流测试

### 1. 自动化脚本测试
```cmd
REM 测试主转换脚本
C:\workspace\pcl_converter.bat

REM 或直接运行
cd /d "C:\workspace"
call pcl_converter.bat
```

### 2. 计划任务测试
```cmd
REM 手动触发计划任务（模拟）
schtasks /run /tn "PCL File Converter"

REM 检查任务状态
schtasks /query /tn "PCL File Converter" /fo list

REM 查看最近运行记录
schtasks /query /tn "PCL File Converter" /v /fo csv | findstr /i "last"
```

### 3. FileBot集成测试
```cmd
REM 测试PDF上传到FileBot
python C:\workspace\index_pdf_to_filebot.py C:\workspace\pcl2pdf\test_output.pdf

REM 或使用curl直接测试API
set TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -d "username=admin&password=admin123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer %TOKEN%" http://localhost:8000/api/v1/documents
```

## 📊 验证和诊断

### 1. 转换结果验证
```cmd
REM 检查PDF文件有效性
REM 使用Python验证（如果安装了PyPDF2）
python -c "
try:
    from PyPDF2 import PdfReader
    with open('C:\\workspace\\pcl2pdf\\test_output.pdf', 'rb') as f:
        pdf = PdfReader(f)
        print(f'✓ PDF有效: {len(pdf.pages)} 页')
        print(f'  创建者: {pdf.metadata.get(\"/Creator\", \"Unknown\")}')
        print(f'  标题: {pdf.metadata.get(\"/Title\", \"Unknown\")}')
except Exception as e:
    print(f'✗ PDF无效: {e}')
"

REM 使用系统工具验证
REM 如果有Acrobat或阅读器
start C:\workspace\pcl2pdf\test_output.pdf
```

### 2. 错误诊断
```cmd
REM 获取详细错误信息
cd /d "C:\workspace\PCLTSDK_870"
PCLXForm.exe default.tpt inp="test0001.pcl" inf="C:\workspace\pcl_input" outp="test_output.pdf" outf="C:\workspace\pcl2pdf" Silent=false Debug=true

REM 检查日志文件
type C:\workspace\PCLTSDK_870\PCLXForm.log 2>nul
type C:\workspace\pcl_logs\*.log 2>nul
```

### 3. 性能测试
```cmd
REM 计时测试
powershell -Command "
$sw = [System.Diagnostics.Stopwatch]::StartNew()
cd 'C:\workspace\PCLTSDK_870'
.\PCLXForm.exe default.tpt inp='test0001.pcl' inf='C:\workspace\pcl_input' outp='test_output.pdf' outf='C:\workspace\pcl2pdf' Silent=true
$sw.Stop()
Write-Host ('转换耗时: ' + $sw.Elapsed.TotalSeconds.ToString('F2') + ' 秒')
"
```

## 🚀 一键测试脚本

创建 `test_all.bat`：
```batch
@echo off
echo ========================================
echo PCL转换全面测试
echo ========================================
echo.

echo 1. 检查环境...
call :check_env

echo.
echo 2. 测试单文件转换...
call :test_single_file

echo.
echo 3. 测试批量转换...
call :test_batch

echo.
echo 4. 验证结果...
call :verify_results

echo.
echo ========================================
echo 测试完成！
echo ========================================
pause
exit /b

:check_env
dir "C:\workspace\PCLTSDK_870\PCLXForm.exe" >nul 2>&1
if errorlevel 1 (
    echo ✗ PCLXForm.exe 未找到
    exit /b 1
) else (
    echo ✓ PCLXForm.exe 找到
)
goto :eof

:test_single_file
cd /d "C:\workspace\PCLTSDK_870"
echo 正在转换测试文件...
PCLXForm.exe default.tpt inp="test0001.pcl" inf="C:\workspace\pcl_input" outp="test_output.pdf" outf="C:\workspace\pcl2pdf" Silent=true
if errorlevel 1 (
    echo ✗ 单文件转换失败
) else (
    echo ✓ 单文件转换成功
)
goto :eof

:test_batch
echo 批量转换测试跳过（可选）
goto :eof

:verify_results
if exist "C:\workspace\pcl2pdf\test_output.pdf" (
    for %%f in ("C:\workspace\pcl2pdf\test_output.pdf") do (
        if %%~zf GTR 0 (
            echo ✓ 输出文件有效 (%%~zf 字节)
        ) else (
            echo ✗ 输出文件为空
        )
    )
) else (
    echo ✗ 输出文件未生成
)
goto :eof
```

## 🐛 故障排除

### 常见问题及解决

**问题1：`PCLXForm.exe` 未找到**
```
解决方案：
1. 检查安装路径：dir "C:\Program Files*\PageTech*\PCLXForm.exe" /s
2. 更新脚本中的路径
3. 添加系统PATH：setx PATH "%PATH%;C:\Path\To\PCLXForm"
```

**问题2：权限错误**
```
解决方案：
1. 以管理员身份运行命令提示符
2. 检查目录权限：icacls "C:\workspace"
3. 关闭防病毒软件临时测试
```

**问题3：转换失败但无错误信息**
```
解决方案：
1. 移除 Silent=true 参数查看详细输出
2. 添加 Debug=true 参数
3. 检查 PCLXForm.log 文件
```

**问题4：输出文件为空**
```
解决方案：
1. 验证输入PCL文件格式
2. 尝试不同参数顺序（inp/inf 交换）
3. 检查模板文件 default.tpt 是否有效
```

## 📝 测试记录模板

```
测试日期: _______________
测试人员: _______________
测试环境: Windows ___ (版本: ______)

✅ 通过项目:
- [ ] PCLXForm.exe 可执行
- [ ] 输入目录可访问
- [ ] 输出目录可写
- [ ] 单文件转换成功
- [ ] 输出PDF文件有效
- [ ] 批量转换正常
- [ ] FileBot API连通

❌ 发现问题:
1. __________________________________
2. __________________________________
3. __________________________________

📋 后续步骤:
1. __________________________________
2. __________________________________
3. __________________________________
```

---

## 💡 快速参考

### 最简测试命令
```cmd
cd /d "C:\workspace\PCLTSDK_870"
PCLXForm.exe default.tpt inp="test.pcl" inf="C:\workspace\pcl_input" outp="output.pdf" outf="C:\workspace\pcl2pdf" Silent=true
```

### 验证命令
```cmd
if exist "C:\workspace\pcl2pdf\output.pdf" (
    echo ✓ 转换成功
) else (
    echo ✗ 转换失败
)
```

### 调试命令
```cmd
PCLXForm.exe default.tpt inp="test.pcl" inf="C:\workspace\pcl_input" outp="output.pdf" outf="C:\workspace\pcl2pdf" Silent=false
```

---

*最后更新: 2026-03-18*
*文档版本: 1.0*