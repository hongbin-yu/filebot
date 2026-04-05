#!/bin/bash

# FileBot 项目安装脚本

set -e

echo "=== FileBot 项目安装 ==="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 需要Python 3.10+，请先安装Python"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "警告: Node.js未安装，前端开发需要Node.js"
    read -p "继续安装后端? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
echo "安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 安装系统依赖
echo "安装系统依赖..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux系统
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ghostscript libreoffice-core tesseract-ocr \
            tesseract-ocr-eng imagemagick poppler-utils
    elif command -v yum &> /dev/null; then
        sudo yum install -y ghostscript libreoffice tesseract \
            tesseract-eng ImageMagick poppler-utils
    else
        echo "警告: 无法自动安装系统依赖，请手动安装："
        echo "  - Ghostscript"
        echo "  - LibreOffice"
        echo "  - Tesseract OCR"
        echo "  - ImageMagick"
        echo "  - Poppler"
    fi
else
    echo "警告: 非Linux系统，请手动安装系统依赖"
fi

# 初始化数据库
echo "初始化数据库..."
python -c "from backend.app.db.database import init_db; init_db()"
python -c "from backend.app.core.security import create_first_superuser; from backend.app.db.database import SessionLocal; db = SessionLocal(); create_first_superuser(db); db.close()"

# 创建目录
echo "创建数据目录..."
mkdir -p data/{files,temp,logs}

# 复制环境配置
if [ ! -f .env ]; then
    echo "创建环境配置文件..."
    cp .env.example .env
    echo "请编辑 .env 文件配置密钥和其他设置"
fi

# 前端安装（如果Node.js可用）
if command -v npm &> /dev/null; then
    echo "安装前端依赖..."
    cd frontend && npm install && cd ..
else
    echo "跳过前端安装 (Node.js未安装)"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "启动步骤:"
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 启动后端: uvicorn backend.main:app --reload"
echo "3. 启动前端: cd frontend && npm start"
echo ""
echo "默认管理员账户:"
echo "  用户名: admin"
echo "  密码: admin123"
echo "  邮箱: admin@filebot.com"
echo ""
echo "访问地址:"
echo "  前端: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/api/docs"