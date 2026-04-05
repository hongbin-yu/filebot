#!/bin/bash
# 从WSL复制文件到Windows的脚本
# 在WSL中运行此脚本

echo "============================================"
echo "复制PCL转换器文件到Windows"
echo "============================================"
echo

# 检查源目录
SRC_DIR="/home/hongb/.openclaw/workspace/filebot/pcl-converter-web"
if [ ! -d "$SRC_DIR" ]; then
    echo "[错误] 源目录不存在: $SRC_DIR"
    exit 1
fi

echo "源目录: $SRC_DIR"

# 检查目标目录
WIN_DIR="/mnt/c/workspace/pcl-converter-web"
echo "目标目录: $WIN_DIR"

# 创建目标目录
mkdir -p "$WIN_DIR"

# 复制核心文件
echo
echo "复制核心文件..."
cp -v "$SRC_DIR/app_windows_optimized.py" "$WIN_DIR/"
cp -v "$SRC_DIR/install_windows.bat" "$WIN_DIR/"
cp -v "$SRC_DIR/start_windows.bat" "$WIN_DIR/"
cp -v "$SRC_DIR/check_env.bat" "$WIN_DIR/"
cp -v "$SRC_DIR/README_windows.md" "$WIN_DIR/"
cp -v "$SRC_DIR/.env.example" "$WIN_DIR/"
cp -v "$SRC_DIR/requirements.txt" "$WIN_DIR/"
cp -v "$SRC_DIR/START_FILEBOT.md" "$WIN_DIR/"

# 复制模板目录
echo
echo "复制模板目录..."
if [ -d "$SRC_DIR/templates" ]; then
    cp -rv "$SRC_DIR/templates" "$WIN_DIR/"
else
    echo "[警告] 模板目录不存在"
fi

# 检查复制结果
echo
echo "============================================"
echo "复制完成！"
echo "在Windows中检查:"
echo "1. 打开文件资源管理器"
echo "2. 导航到 C:\workspace\pcl-converter-web"
echo "3. 确认有以下文件:"
echo "   - app_windows_optimized.py"
echo "   - install_windows.bat"
echo "   - start_windows.bat"
echo "   - templates/目录"
echo "============================================"