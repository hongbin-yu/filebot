# PCL to PDF Converter - Windows部署指南

## 系统要求
- Windows 10/11 64位
- Python 3.8 或更高版本
- 至少 2GB 可用内存
- 至少 500MB 可用磁盘空间

## 快速开始

### 方法一：一键安装（推荐）
1. 下载 `install.bat` 和所有文件到同一目录
2. 右键点击 `install.bat`，选择"以管理员身份运行"
3. 按照提示完成安装

### 方法二：手动安装
1. 安装 Python 3.8+
   - 从 https://www.python.org/downloads/ 下载
   - 安装时勾选"Add Python to PATH"

2. 安装依赖包
   ```cmd
   cd /d "应用程序目录"
   pip install -r requirements.txt
   ```

3. 安装PCL转换工具（见下文）

4. 运行应用
   ```cmd
   run.bat
   ```

## PCL转换工具安装

本应用需要PCL到PDF的转换工具。以下是推荐的选项：

### 选项1: GhostPCL (推荐)
GhostPCL 是 Artifex 提供的专业PCL解释器，包含在 Ghostscript 商业版本中。

**安装步骤:**
1. 访问 https://www.artifex.com/downloads/
2. 下载 Ghostscript 商业版 (包含 GhostPCL)
3. 安装并添加 `gpcl6.exe` 到系统 PATH

**验证安装:**
```cmd
gpcl6 --version
```

### 选项2: pcltopdf (开源)
开源PCL转换工具，可能需要从源代码编译。

**安装步骤:**
1. 下载预编译版本或从源代码编译
2. 将 `pcltopdf.exe` 放在系统 PATH 或应用目录的 `tools/` 文件夹中

### 选项3: Pagetech command line (商业软件)
Pagetech是商业PCL转换工具，功能强大，支持多种PCL格式。

**安装步骤:**
1. 从Pagetech官方渠道获取安装程序
2. 安装Pagetech command line工具
3. 确保 `pagetech.exe` 或 `pagetechcmd.exe` 在系统PATH中

**验证安装:**
```cmd
pagetech --version
```

**配置Pagetech参数:**
如果Pagetech需要特定参数，可在 `.env` 文件中配置:
```env
# Pagetech自定义参数（使用{input}和{output}占位符）
PAGETECH_ARGS={input} {output}
# 或带参数格式: PAGETECH_ARGS=-o {output} {input}
```

### 选项4: 使用现有安装
如果系统中已安装PCL转换工具，确保其在系统PATH中或配置应用使用。

## 应用配置

### 配置文件
创建 `.env` 文件进行配置:
```env
# Flask配置
SECRET_KEY=your-secret-key-change-in-production
DEBUG=False

# 文件存储
UPLOAD_FOLDER=uploads
CONVERTED_FOLDER=converted
MAX_CONTENT_MB=100

# PCL转换工具路径
PCL_TOOL_PATH=C:\Program Files\Ghostscript\bin\gpcl6.exe
# 或使用系统PATH中的工具
# PCL_TOOL_PATH=auto

# Pagetech自定义参数（可选，使用{input}和{output}占位符）
# PAGETECH_ARGS={input} {output}
# 或带参数格式: PAGETECH_ARGS=-o {output} {input}

# FileBot后端API（可选）
FILEBOT_API_URL=http://localhost:8000/api/v1
FILEBOT_USERNAME=admin
FILEBOT_PASSWORD=admin123
```

### 目录结构
```
pcl-converter-web/
├── app.py              # 主应用文件
├── requirements.txt    # Python依赖
├── templates/         # HTML模板
├── uploads/           # 上传文件存储
├── converted/         # 转换后的PDF存储
├── logs/              # 日志文件
└── tools/             # 第三方工具（可选）
```

## 运行应用

### 启动方式
1. **双击运行**: 运行 `run.bat`
2. **命令行运行**: 
   ```cmd
   cd /d "应用目录"
   python -m flask run --host=0.0.0.0 --port=5000
   ```

### 访问应用
- 本地访问: http://localhost:5000
- 网络访问: http://[你的IP地址]:5000

## 故障排除

### 常见问题

**1. "Python未找到"错误**
- 确保Python已安装并添加到PATH
- 重新启动命令行窗口

**2. 依赖安装失败**
- 使用管理员权限运行命令提示符
- 尝试: `pip install --upgrade pip`
- 或使用: `python -m pip install -r requirements.txt`

**3. PCL转换失败**
- 检查PCL工具是否安装正确
- 验证工具路径配置
- 测试命令行转换: `gpcl6 input.pcl output.pdf`

**4. 端口占用**
- 修改端口: `python -m flask run --port=5001`
- 或关闭占用5000端口的程序

### 日志查看
应用日志位于 `logs/` 目录:
- `app.log` - 应用日志
- `conversion.log` - 转换任务日志

## 高级配置

### 作为Windows服务运行
使用 `nssm` (Non-Sucking Service Manager):

1. 下载 nssm: https://nssm.cc/download
2. 安装服务:
   ```cmd
   nssm install "PCL Converter" "C:\Python39\python.exe" "app.py"
   ```
3. 启动服务: `nssm start "PCL Converter"`

### 使用反向代理
配置Nginx或Apache反向代理:
```nginx
server {
    listen 80;
    server_name converter.example.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 安全建议

1. **更改默认密码**: 修改FileBot API凭据
2. **启用HTTPS**: 在生产环境使用SSL/TLS
3. **防火墙配置**: 限制访问IP范围
4. **定期备份**: 备份 `uploads/` 和 `converted/` 目录
5. **日志监控**: 定期检查日志文件

## 技术支持

遇到问题请检查:
1. Windows事件查看器
2. 应用日志文件
3. Python错误信息

如需帮助，提供:
- 操作系统版本
- Python版本
- 错误日志内容
- 复现步骤

## 🤖 自动化工作流（新功能）

### 概述
新增自动化PCL转PDF工作流，包含Windows计划任务和FileBot集成。

### 核心文件
```
windows-deploy/
├── pcl_converter.bat              # 主转换脚本
├── setup_scheduled_task.bat       # 计划任务安装脚本
├── uninstall_scheduled_task.bat   # 计划任务卸载脚本
├── test_pcl_command.bat           # 命令测试脚本
└── PCL_Automation_Deployment.md   # 详细部署指南
```

### 快速开始
1. **测试命令格式**: 运行 `test_pcl_command.bat`
2. **安装计划任务**: 以管理员运行 `setup_scheduled_task.bat`
3. **配置Linux索引**: 设置cron运行 `index_pdf_to_filebot.py`

### 工作流
```
放入PCL文件 → Windows计划任务 → PCLXform转换 → PDF生成
    ↓
PDF存入pcl2pdf/ → Linux cron任务 → FileBot API上传 → 文档记录创建
    ↓
索引成功后删除源PCL文件 → 清理完成
```

### 详细指南
请参考 [PCL_Automation_Deployment.md](PCL_Automation_Deployment.md) 获取完整部署步骤。

---
*最后更新: 2026-03-18 (添加自动化工作流支持)*