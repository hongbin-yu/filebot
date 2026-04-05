# PCL to PDF Converter - Windows部署指南

## 版本说明

### 增强版特性 (推荐使用)
- **专业Web界面**: 现代化UI设计，实时状态监控
- **智能工具检测**: 支持hplip、ghostscript等多种工具自动检测
- **详细错误处理**: 提供具体的修复建议和解决方案
- **转换统计**: 记录转换历史、成功率和性能指标
- **多工具支持**: 自动选择最佳转换工具
- **实时进度**: 多步骤转换进度可视化

### 标准版特性
- 基础文件上传和转换功能
- 简单工具检测
- 基本错误提示

## 系统要求
- Windows 10/11 64位
- Python 3.8 或更高版本
- 至少 2GB 可用内存
- 至少 500MB 可用磁盘空间

## 快速开始

### 方法一：一键安装（推荐）
1. 下载所有文件到同一目录
2. 右键点击 `install.bat`，选择"以管理员身份运行"
3. 按照提示完成安装
4. 运行 `run_enhanced.bat` 启动增强版应用

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
   # 标准版
   run.bat
   # 增强版（推荐）
   run_enhanced.bat
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

### 选项3: 使用现有安装
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

---
*最后更新: 2026-03-17*