#!/bin/bash
# WebBot 服务状态检查脚本

echo "📊 WebBot 服务状态检查"
echo "========================"

# 检查systemd服务
echo "🔍 检查systemd服务状态..."
if systemctl is-active webbot.service >/dev/null 2>&1; then
    echo "✅ WebBot systemd服务正在运行"
    systemctl status webbot.service --no-pager | head -20
else
    echo "⚠️  WebBot systemd服务未运行或未安装"
fi

echo ""
echo "🔍 检查端口监听..."
if ss -tlnp | grep -q ':8000\b'; then
    echo "✅ 端口8000正在监听"
    ss -tlnp | grep ':8000\b'
else
    echo "❌ 端口8000未监听"
fi

echo ""
echo "🔍 检查进程..."
if pgrep -f "uvicorn.*8000" >/dev/null; then
    echo "✅ WebBot进程正在运行"
    ps aux | grep "uvicorn.*8000" | grep -v grep
else
    echo "❌ WebBot进程未运行"
fi

echo ""
echo "🔍 快速功能测试..."
if command -v curl >/dev/null; then
    echo "测试API端点..."
    if curl -s http://localhost:8000/api/v1/pages/ >/dev/null; then
        echo "✅ API响应正常"
    else
        echo "❌ API无响应"
    fi
    
    echo "测试编辑器页面..."
    if curl -s http://localhost:8000/static/editor.html >/dev/null; then
        echo "✅ 编辑器页面可访问"
    else
        echo "❌ 编辑器页面不可访问"
    fi
else
    echo "⚠️  curl未安装，跳过功能测试"
fi

echo ""
echo "📋 建议操作:"
if ! systemctl is-active webbot.service >/dev/null 2>&1; then
    echo "  1. 安装systemd服务: sudo bash /home/hongb/.openclaw/workspace/webbot/install-systemd.sh"
fi
if ! ss -tlnp | grep -q ':8000\b'; then
    echo "  2. 手动启动: cd /home/hongb/.openclaw/workspace/webbot && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
fi