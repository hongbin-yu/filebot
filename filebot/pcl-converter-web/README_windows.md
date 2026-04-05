# PCL转PDF转换器 - Windows原生版

专为Windows环境设计的PCL转PDF转换器，使用PageTech PCLTSDK进行快速转换，并支持上传到WSL中的FileBot API。

## 🔄 重启后指南（如果你启用了长路径支持）

如果你在Python安装时选择了**"启用长路径支持并重启"**，请按以下步骤继续：

### 步骤1：验证Python安装
```cmd
# 打开命令提示符（Win+R，输入cmd）
python --version
```
应显示：`Python 3.x.x`

### 步骤2：检查环境（推荐）
```cmd
# 进入项目目录
cd C:\workspace\pcl-converter-web

# 运行环境检查脚本
check_env.bat
```

### 步骤3：安装依赖
```cmd
# 如果check_env.bat显示一切正常，运行安装脚本
install_windows.bat
```

### 步骤4：启动应用
```cmd
# 安装完成后，启动应用
start_windows.bat
```

### 步骤5：访问Web界面
打开浏览器访问：http://localhost:5000

## 🚀 快速开始

### 前提条件
1. **Python 3.9+** 已安装并添加到PATH
2. **PageTech PCLTSDK v8.70** 已安装（默认位置：`C:\Program Files (x86)\PageTech\PCLTSDK_870\`）
3. **WSL FileBot API** 正在运行（可选，默认地址：`http://localhost:8000/api/v1`）

### 一键安装（推荐）
运行 `install_windows.bat` 自动完成所有配置。

### 手动安装步骤

#### 1. 安装Python
- 从 [python.org](https://www.python.org/downloads/) 下载Python 3.9+
- 安装时务必勾选 **"Add Python to PATH"**

#### 2. 创建虚拟环境
```cmd
cd C:\workspace\pcl-converter-web
python -m venv venv_win
```

#### 3. 激活虚拟环境并安装依赖
```cmd
venv_win\Scripts\activate
pip install flask requests python-dotenv
```

#### 4. 检查PageTech PCLTSDK安装
确保以下文件存在：
- `C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe`
- `C:\Program Files (x86)\PageTech\PCLTSDK_870\default.tpt`

#### 5. 创建必要目录
```cmd
mkdir C:\workspace\pcl-uploads
mkdir C:\workspace\pcl-converted
```

#### 6. 配置环境变量（可选）
复制 `.env.example` 为 `.env` 并修改：
```cmd
copy .env.example .env
```

## 🏃 启动应用

### 方法一：使用启动脚本
双击 `start_windows.bat`

### 方法二：命令行启动
```cmd
cd C:\workspace\pcl-converter-web
venv_win\Scripts\activate
python app_windows_optimized.py
```

## 🌐 访问地址
- **Web界面**: http://localhost:5000
- **健康检查**: http://localhost:5000/health
- **工具列表**: http://localhost:5000/api/tools

## ⚙️ 配置选项

### FileBot API集成
修改 `.env` 文件：
```env
USE_FILEBOT_API=true
FILEBOT_API_URL=http://localhost:8000/api/v1
FILEBOT_USERNAME=admin
FILEBOT_PASSWORD=admin123
```

### PCL工具路径
应用会自动检测以下位置：
1. `C:\Program Files (x86)\PageTech\PCLTSDK_870\`
2. `C:\workspace\PCLTSDK_870\`

如果需要自定义路径，修改 `app_windows_optimized.py` 中的 `PCL_TOOL_PATHS` 列表。

## 🎯 使用流程

### 1. 上传PCL文件
- 访问 http://localhost:5000
- 选择PCL文件（支持 .pcl, .prn, .ps, .eps）
- 点击上传

### 2. 自动转换
应用会：
1. 自动检测可用的PCL转换工具
2. 使用用户验证的命令格式进行转换：
   ```
   PclXform.exe "default.tpt" inp="目录" inf="文件名" outp="文件名" outf="目录"
   ```
3. 转换速度非常快（已验证）

### 3. 上传到FileBot（可选）
如果启用了FileBot API，转换后的PDF会自动上传到WSL中的FileBot。

### 4. 下载结果
- 直接下载转换后的PDF文件
- 或通过FileBot API处理结果

## 🔧 故障排除

### Q: 找不到PclXform.exe
**A**: 检查PageTech PCLTSDK是否已安装到默认位置，或修改工具检测路径。

### Q: 转换成功但没有PDF文件
**A**: 确保命令格式正确。用户已验证的命令格式为：
```
PclXform.exe "default.tpt" inp="C:\workspace\sample" inf="00000001.pcl" outp="test_user.pdf" outf="C:\workspace\sample"
```

### Q: FileBot API连接失败
**A**: 
1. 确保WSL中的FileBot正在运行
2. 检查 `.env` 文件中的API地址和凭据
3. 运行 `curl http://localhost:8000/api/v1/health` 测试连接

### Q: Python版本错误
**A**: 需要Python 3.9+。运行 `python --version` 检查。

## 📁 目录结构
```
pcl-converter-web/
├── app_windows_optimized.py  # Windows优化版主程序
├── app_win.py                # 原始版本（含WSL兼容代码）
├── install_windows.bat      # Windows安装脚本
├── start_windows.bat        # Windows启动脚本
├── check_env.bat           # 环境检查脚本（重启后使用）
├── .env.example             # 环境变量示例
├── requirements.txt         # Python依赖列表
├── templates/               # Web界面模板
├── uploads/                 # 本地上传目录
├── converted/               # 本地转换目录
└── logs/                    # 应用日志
```

## 💻 Windows命令行基础

### 如何打开命令提示符
1. **按 `Win + R`**，输入 `cmd`，回车
2. 或搜索"命令提示符"或"CMD"

### 常用命令
```cmd
# 切换目录
cd C:\workspace\pcl-converter-web

# 查看目录内容
dir

# 查看Python版本
python --version

# 运行批处理文件
install_windows.bat
```

### 如果遇到"Python未找到"错误
1. **重新打开命令提示符**：关闭后重新打开，让PATH变更生效
2. **重启电脑**：如果刚安装Python或修改了PATH
3. **使用完整路径**：
   ```cmd
   # 假设Python安装在 C:\Python39
   "C:\Python39\python.exe" --version
   ```

## 🛠️ 开发说明

### 为什么选择Windows原生？
- **已验证**: PageTech PCLTSDK在Windows中转换速度非常快
- **兼容性**: 避免WSL兼容性问题
- **性能**: 原生Windows调用，无中间层性能损失

### 主要优化
1. **移除WSL兼容代码**：简化路径处理
2. **Windows原生命令格式**：使用用户验证的命令格式
3. **自动工具检测**：自动寻找PCLTSDK安装位置
4. **FileBot API集成**：无缝对接WSL中的FileBot

## 📞 技术支持
如有问题，请检查：
1. `logs/app.log` 中的详细错误信息
2. Windows事件查看器中的系统日志
3. 访问 `/health` 端点检查应用状态

## 📄 许可证
MIT License

---
**最后更新**: 2026-03-17
**版本**: 1.0.0 Windows原生版