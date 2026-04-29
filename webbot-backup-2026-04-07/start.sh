#!/bin/bash
# WebBot启动脚本

echo "🚀 启动WebBot AI内容管理系统"
echo "================================="

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python3未安装"
    exit 1
fi

echo "✅ Python3可用: $(python3 --version)"

# 检查依赖
# cd app  # 现在在webbot根目录运行
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 安装依赖..."
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
    elif command -v pip &> /dev/null; then
        pip install -r requirements.txt
    else
        echo "❌ 错误: pip未安装，请手动安装依赖:"
        echo "    pip install fastapi uvicorn pydantic python-multipart aiofiles"
        exit 1
    fi
fi

echo "✅ 依赖检查完成"

# 检查FileBot数据库
DB_PATH="../filebot/backend/filebot.db"
if [ ! -f "$DB_PATH" ]; then
    echo "⚠️  警告: FileBot数据库未找到: $DB_PATH"
    echo "   将创建新的WebBot表结构"
fi

# 启动服务器
echo "🌐 启动WebBot服务器..."
echo "📊 API地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo "🖥️  前端界面: http://localhost:8000/static/index.html"
echo ""
echo "按Ctrl+C停止服务器"

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload