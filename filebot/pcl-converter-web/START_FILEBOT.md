# FileBot API启动指南

如果需要在WSL中使用FileBot API接收转换后的PDF文件，请按以下步骤启动FileBot服务。

## 🚀 快速启动

### 方法一：使用docker-compose（推荐）
```bash
# 在WSL终端中执行
cd /home/hongb/.openclaw/workspace/filebot
docker-compose -f docker-compose-simple.yml up -d backend
```

### 方法二：仅启动后端API
```bash
# 如果只需要API服务
cd /home/hongb/.openclaw/workspace/filebot
docker-compose -f docker-compose-simple.yml up -d backend
```

### 方法三：完整启动（前后端）
```bash
# 启动所有服务
cd /home/hongb/.openclaw/workspace/filebot
docker-compose -f docker-compose-simple.yml up -d
```

## 🌐 验证服务

### 1. 检查容器状态
```bash
docker ps | grep filebot
```

### 2. 测试API连接
```bash
# 等待30秒让服务完全启动
sleep 30
curl http://localhost:8000/api/v1/health
```

预期响应：
```json
{"status":"healthy","version":"1.0.0"}
```

### 3. 查看日志
```bash
docker logs filebot-backend
```

## ⚙️ 配置说明

### 默认配置
- **API地址**: http://localhost:8000/api/v1
- **用户名**: admin
- **密码**: admin123
- **端口**: 8000

### 修改配置
如果需要修改配置，编辑 `.env` 文件：
```bash
cd /home/hongb/.openclaw/workspace/filebot
cp .env.example .env
# 编辑 .env 文件
```

## 🔧 故障排除

### Q: 端口8000被占用
**A**: 停止现有服务或修改端口：
```yaml
# 修改 docker-compose-simple.yml
ports:
  - "8001:8000"  # 外部端口:容器端口
```

### Q: 容器启动失败
**A**: 检查依赖安装：
```bash
# 查看详细日志
docker logs filebot-backend --tail 50

# 重新构建镜像
docker-compose -f docker-compose-simple.yml build --no-cache backend
```

### Q: API连接超时
**A**: 确保WSL网络配置正确：
```bash
# 检查WSL IP地址
ip addr show eth0

# Windows中测试连接
curl.exe http://localhost:8000/api/v1/health
```

## 📊 服务管理

### 启动服务
```bash
docker-compose -f docker-compose-simple.yml start backend
```

### 停止服务
```bash
docker-compose -f docker-compose-simple.yml stop backend
```

### 重启服务
```bash
docker-compose -f docker-compose-simple.yml restart backend
```

### 查看状态
```bash
docker-compose -f docker-compose-simple.yml ps
```

### 删除服务
```bash
docker-compose -f docker-compose-simple.yml down
```

## 🔄 与Windows Flask集成

### 配置 .env 文件
在Windows Flask应用的 `.env` 文件中配置：
```env
USE_FILEBOT_API=true
FILEBOT_API_URL=http://localhost:8000/api/v1
FILEBOT_USERNAME=admin
FILEBOT_PASSWORD=admin123
```

### 测试集成
1. 启动FileBot API（WSL）
2. 启动Windows Flask应用
3. 上传PCL文件测试转换和上传

## 📝 注意事项

1. **首次启动较慢**：需要下载和安装依赖（约5-10分钟）
2. **WSL网络**：Windows可以通过 `localhost:8000` 直接访问WSL中的服务
3. **文件权限**：确保WSL和Windows有足够的文件读写权限
4. **资源占用**：FileBot API内存占用约200-300MB

## 🆘 技术支持

如果遇到问题：
1. 查看容器日志：`docker logs filebot-backend`
2. 检查WSL网络：`ping localhost`
3. 验证端口开放：`netstat -tlnp | grep :8000`
4. 重启WSL：`wsl --shutdown` 然后在Windows中重新打开

---

**重要**：如果不使用FileBot API，可以在Windows Flask的 `.env` 文件中设置 `USE_FILEBOT_API=false` 禁用此功能。