#!/bin/bash
# PCL转PDF转换器Web应用启动脚本

set -e

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv"
    echo "   然后运行: ./venv/bin/pip install flask python-dotenv requests flask-wtf"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 设置Flask环境变量
export FLASK_APP=app_win.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# 检查端口是否被占用
PORT=5000
if command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
        echo "⚠️  端口 $PORT 已被占用"
        echo "   正在查找占用进程..."
        netstat -tlnp 2>/dev/null | grep ":$PORT "
    fi
fi

echo "🚀 启动PCL转PDF转换器Web应用..."
echo "📁 工作目录: $(pwd)"
echo "🐍 Python版本: $(python --version)"
echo "🌐 应用地址: http://localhost:$PORT"

# 启动Flask应用
exec flask run --host=0.0.0.0 --port=$PORT