# PCL自动化工作流部署指南

## 📋 项目概述
自动化的PCL转PDF工作流，包含两个主要组件：
1. **Windows端**: 监控文件夹并转换PCL文件为PDF
2. **Linux端**: 索引PDF到FileBot并清理源文件

## 🗂️ 目录结构
```
C:\workspace\
├── pcl_input\          # 监控目录（放入.pcl文件）
├── pcl2pdf\           # PDF输出目录（转换后的PDF）
├── pcl_processed\     # 已处理的PCL文件
├── pcl_failed\        # 转换失败的PCL文件
└── pcl_logs\          # 日志目录
```

## 🚀 快速部署

### 步骤1: 准备环境
1. 确保已安装 **Pagetech PCLTSDK 870**
   - 默认安装路径: `C:\Program Files (x86)\PageTech\PCLTSDK_870\`
   - 包含文件: `PclXform.exe`, `default.tpt`

2. 创建工作目录 (脚本会自动创建，也可手动创建):
   ```cmd
   mkdir C:\workspace\pcl_input
   mkdir C:\workspace\pcl2pdf
   mkdir C:\workspace\pcl_processed
   mkdir C:\workspace\pcl_failed
   mkdir C:\workspace\pcl_logs
   ```

### 步骤2: 部署Windows批处理脚本
将以下文件复制到Windows可访问的位置（如 `C:\workspace\` 或 `桌面\`）:
```
pcl_converter.bat              # 主转换脚本
setup_scheduled_task.bat       # 计划任务安装脚本
uninstall_scheduled_task.bat   # 计划任务卸载脚本
test_pcl_command.bat           # 命令测试脚本
```

### 步骤3: 测试转换命令
运行测试脚本验证PCLXform命令格式:
```cmd
cd C:\workspace\
test_pcl_command.bat
```

按照提示测试两种命令格式，确定哪种格式有效:
- **格式A**: `inp="文件名" inf="目录" outp="文件名" outf="目录"`
- **格式B**: `inp="目录" inf="文件名" outp="目录" outf="文件名"`

### 步骤4: 修改转换脚本（如果需要）
如果测试发现格式B有效，需要修改 `pcl_converter.bat`:
1. 用记事本打开 `pcl_converter.bat`
2. 找到以下部分:
   ```batch
   REM 默认使用格式A（根据用户之前的验证）
   call :log "执行转换: %input_file% -> %output_file%"
   PclXform.exe default.tpt inp="%input_file%" inf="%INPUT_DIR%" outp="%output_file%" outf="%OUTPUT_DIR%" Silent=true
   ```
3. 改为格式B:
   ```batch
   REM 使用格式B
   call :log "执行转换: %input_file% -> %output_file%"
   PclXform.exe default.tpt inp="%INPUT_DIR%" inf="%input_file%" outp="%OUTPUT_DIR%" outf="%output_file%" Silent=true
   ```

### 步骤5: 配置Windows计划任务
**方法A: 使用安装脚本（推荐）**
1. 右键点击 `setup_scheduled_task.bat`
2. 选择"以管理员身份运行"
3. 按照提示完成安装

**方法B: 手动配置**
1. 打开"任务计划程序"
2. 点击"创建基本任务"
3. 配置:
   - 名称: `PCL File Converter`
   - 触发器: `每天` → 开始时间: 现在，重复间隔: `1分钟`
   - 操作: `启动程序` → 程序: `C:\workspace\pcl_converter.bat`
   - 完成

### 步骤6: 部署Linux索引脚本
1. 确保FileBot后端运行在端口8000
2. 确保WSL/Linux可以访问Windows目录
3. 配置cron任务，每5分钟运行一次索引:

```bash
# 编辑cron任务
crontab -e

# 添加以下行
*/5 * * * * cd /home/hongb/.openclaw/workspace/filebot/pcl-converter-web && /usr/bin/python3 index_pdf_to_filebot.py >> /mnt/c/workspace/pcl_logs/cron.log 2>&1
```

### 步骤7: 测试完整工作流
1. 放入测试文件:
   ```cmd
   copy "C:\workspace\sample\00000001.pcl" "C:\workspace\pcl_input\"
   ```

2. 手动运行转换（或等待计划任务）:
   ```cmd
   C:\workspace\pcl_converter.bat
   ```

3. 手动运行索引:
   ```bash
   cd /home/hongb/.openclaw/workspace/filebot/pcl-converter-web
   python3 index_pdf_to_filebot.py
   ```

4. 验证结果:
   - 检查 `C:\workspace\pcl2pdf\` 是否有PDF文件
   - 检查FileBot网页界面是否有新文档
   - 检查 `C:\workspace\pcl_logs\` 日志文件

## ⚙️ 脚本说明

### 1. pcl_converter.bat
主转换脚本，功能:
- 扫描 `pcl_input\` 目录中的 `.pcl` 文件
- 使用PCLXform转换为PDF到 `pcl2pdf\` 目录
- 转换成功后移动源文件到 `pcl_processed\`
- 转换失败则移动源文件到 `pcl_failed\`
- 记录详细日志到 `pcl_logs\`

**日志示例:**
```
[2026-03-18 02:30:00] 处理文件: 00000001.pcl
[2026-03-18 02:30:05] 转换成功: 00000001.pdf (大小: 233534 字节)
[2026-03-18 02:30:05] 移动已处理文件到: C:\workspace\pcl_processed\processed_20260318_023000_00000001.pcl
```

### 2. setup_scheduled_task.bat
计划任务安装脚本，功能:
- 创建名为 `PCL File Converter` 的计划任务
- 配置为每分钟运行一次
- 以SYSTEM账户最高权限运行
- 自动测试任务运行

### 3. index_pdf_to_filebot.py
Linux端索引脚本，功能:
- 扫描 `pcl2pdf\` 目录中的PDF文件
- 通过FileBot API上传并创建文档记录
- 自动创建应用→抽屉→文件夹结构
- 索引成功后删除对应的PCL源文件

## 🔧 高级配置

### 修改转换参数
如果需要调整PCLXform参数，编辑 `pcl_converter.bat`:
- 超时时间: 脚本内置错误处理，但PCLXform可能需外部调整
- 输出质量: 可能需要修改 `default.tpt` 模板文件
- 内存设置: PCLXform可能有内存相关参数

### 调整计划任务频率
编辑计划任务:
1. 打开"任务计划程序"
2. 找到 `PCL File Converter` 任务
3. 右键 → 属性 → 触发器
4. 修改重复间隔

或使用命令行:
```cmd
schtasks /change /tn "PCL File Converter" /ri 2  # 每2分钟
```

### 监控和排错

**检查计划任务状态:**
```cmd
schtasks /query /tn "PCL File Converter" /fo list
```

**查看最近运行结果:**
```cmd
schtasks /query /tn "PCL File Converter" /v /fo csv
```

**手动测试转换:**
```cmd
cd "C:\Program Files (x86)\PageTech\PCLTSDK_870"
PclXform.exe default.tpt inp="test.pcl" inf="C:\workspace\pcl_input" outp="test.pdf" outf="C:\workspace\pcl2pdf" Silent=true
```

**查看日志:**
- Windows日志: `C:\workspace\pcl_logs\pcl_converter_YYYYMMDD.log`
- Linux cron日志: `/mnt/c/workspace/pcl_logs/cron.log`

## ⚠️ 故障排除

### 常见问题

**1. 计划任务不运行**
- 检查任务状态: `schtasks /query /tn "PCL File Converter"`
- 检查任务历史: 在"任务计划程序"中查看"上次运行结果"
- 确保脚本路径正确且可执行

**2. 转换失败**
- 检查PCLXform是否安装正确
- 验证命令格式（使用test_pcl_command.bat）
- 检查输入文件是否为有效PCL格式
- 查看日志文件中的错误信息

**3. 文件权限问题**
- 确保SYSTEM账户有权限访问所有目录
- 检查目录是否被其他程序锁定
- 尝试以管理员身份手动运行脚本

**4. WSL/Windows路径问题**
- 确保WSL可以访问Windows目录
- 检查 `/mnt/c/` 挂载点是否正常
- 验证FileBot后端可以从WSL访问

**5. FileBot索引失败**
- 检查FileBot后端是否运行: `http://localhost:8000`
- 验证API凭据（默认: admin/admin123）
- 检查网络连接和防火墙设置

## 📞 技术支持

遇到问题时请提供以下信息:
1. Windows版本和架构（64位/32位）
2. PCLTSDK版本和安装路径
3. 错误日志内容
4. 复现步骤

**检查清单:**
- [ ] PCLXform.exe 存在且可执行
- [ ] 工作目录结构完整
- [ ] 计划任务创建成功
- [ ] 日志文件正常生成
- [ ] FileBot后端可访问

---
*部署完成时间: 2026-03-18*
*最后更新: 2026-03-18 (初始版本)*