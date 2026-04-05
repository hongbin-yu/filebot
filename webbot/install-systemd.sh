#!/bin/bash
# WebBot systemd 服务安装脚本
# 需要 sudo 权限执行

echo "🚀 WebBot systemd 服务安装程序"
echo "================================="

# 检查是否以root或sudo运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 此脚本需要sudo权限运行"
    echo "请使用: sudo bash $0"
    exit 1
fi

# 1. 复制服务文件
echo "📦 复制服务文件到 /etc/systemd/system/"
cp /home/hongb/.openclaw/workspace/webbot/webbot.service /etc/systemd/system/webbot.service
chmod 644 /etc/systemd/system/webbot.service

# 2. 重新加载systemd配置
echo "🔄 重新加载systemd配置"
systemctl daemon-reload

# 3. 启用服务（开机自启）
echo "✅ 启用WebBot服务（开机自启）"
systemctl enable webbot.service

# 4. 启动服务
echo "🚀 启动WebBot服务"
systemctl start webbot.service

# 5. 检查服务状态
echo "📊 服务状态检查"
systemctl status webbot.service --no-pager

echo ""
echo "🎉 安装完成！"
echo ""
echo "📋 常用命令:"
echo "  sudo systemctl status webbot      # 查看服务状态"
echo "  sudo systemctl restart webbot     # 重启服务"
echo "  sudo systemctl stop webbot        # 停止服务"
echo "  sudo systemctl start webbot       # 启动服务"
echo "  sudo journalctl -u webbot -f      # 查看实时日志"
echo ""
echo "🌐 访问地址: http://localhost:8000/static/editor.html"
echo "📚 API文档: http://localhost:8000/docs"