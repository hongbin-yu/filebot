#!/bin/bash
# FileBot监控脚本 - 自动检测并重启后端服务
# 放置于: /home/hongb/.openclaw/workspace/filebot/

# 配置
CHECK_INTERVAL=60  # 检查间隔（秒）
HEALTH_URL="http://localhost:8001/api/health"
NGINX_HEALTH_URL="https://localhost/api/v1/auth/login"
HTTPS_PROXY_URL="https://localhost:8443/api/health"
HTTPS_PROXY_DIR="/home/hongb/.openclaw/workspace/filebot"
HTTPS_PROXY_CERT="/tmp/filebot-cert.pem"
HTTPS_PROXY_KEY="/tmp/filebot-key.pem"
BACKEND_ROOT="/home/hongb/.openclaw/workspace/filebot/backend"
LOG_FILE="$BACKEND_ROOT/filebot_monitor.log"
MAX_LOG_SIZE=10485760  # 10MB

# 日志函数
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查日志大小，如果太大就轮转
check_log_size() {
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]; then
        log_message "日志文件超过${MAX_LOG_SIZE}字节，进行轮转..."
        mv "$LOG_FILE" "${LOG_FILE}.$(date '+%Y%m%d_%H%M%S')"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始新的监控日志" > "$LOG_FILE"
    fi
}

# 检查服务健康状态
check_health() {
    # 使用curl检查健康端点，设置超时和重试
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 --retry 2 "$HEALTH_URL" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        # 进一步验证响应内容
        content=$(curl -s --max-time 5 "$HEALTH_URL" 2>/dev/null)
        if echo "$content" | grep -q '"status":"ok"' && echo "$content" | grep -q '"database":"connected"'; then
            log_message "✅ FileBot服务健康检查通过 (HTTP $response)"
            return 0
        else
            log_message "⚠️  FileBot服务响应异常: $content"
            return 1
        fi
    else
        log_message "❌ FileBot服务健康检查失败 (HTTP $response)"
        return 1
    fi
}

# 重启服务
restart_service() {
    log_message "🔄 开始重启FileBot后端服务..."
    
    # 杀死现有进程
    # 检测uvicorn进程或监听端口8001的进程
    pids=$(ps aux | grep "uvicorn.*main:app" | grep "port 8001" | grep -v grep | awk '{print $2}')
    if [ -z "$pids" ]; then
        # 如果没找到uvicorn进程，尝试通过端口8001查找
        pids=$(lsof -ti:8001 2>/dev/null || ss -tlnp | grep :8001 | awk '{print $7}' | cut -d',' -f2 | cut -d'=' -f2)
    fi
    
    if [ -n "$pids" ]; then
        log_message "正在停止进程: $pids"
        for pid in $pids; do
            kill -TERM "$pid" 2>/dev/null
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null
                log_message "强制杀死进程 $pid"
            fi
        done
    fi
    
    # 确保端口释放
    sleep 3
    
    # 启动新进程（使用start-backend.sh，自动设置LLM API key）
    cd "$BACKEND_ROOT" || exit 1
    nohup ./start-backend.sh > filebot_run.log 2>&1 &
    new_pid=$!
    
    # 等待服务启动
    sleep 10
    
    # 检查新进程是否运行
    if kill -0 "$new_pid" 2>/dev/null; then
        log_message "✅ FileBot服务重启成功，新进程PID: $new_pid"
        
        # 验证服务确实启动
        if check_health; then
            log_message "✅ FileBot服务验证通过，正常运行"
        else
            log_message "⚠️  FileBot服务已启动但健康检查未通过，请检查日志"
        fi
    else
        log_message "❌ FileBot服务启动失败，请检查filebot_run.log"
    fi
}

# 主循环
main() {
    log_message "🚀 FileBot监控脚本启动"
    log_message "📊 配置: 每${CHECK_INTERVAL}秒检查一次, 健康端点: $HEALTH_URL"
    
    while true; do
        check_log_size
        
        if ! check_health; then
            log_message "💥 检测到FileBot服务不可用，尝试重启..."
            restart_service
        fi
        
        # 检查 nginx（统一入口 + IP白名单）
        if ! check_nginx; then
            log_message "🔒 nginx不可用，尝试重启..."
            restart_nginx
        fi
        
        # 检查 HTTPS 代理（跨機器訪問用）
        if ! check_https_proxy; then
            log_message "🔐 HTTPS代理不可用，尝试重启..."
            restart_https_proxy
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# 检查 nginx
check_nginx() {
    response=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 "$NGINX_HEALTH_URL" 2>/dev/null)
    if [ "$response" = "200" ] || [ "$response" = "405" ] || [ "$response" = "422" ]; then
        return 0
    fi
    return 1
}

# 重启 nginx
restart_nginx() {
    if sudo nginx -t 2>/dev/null; then
        sudo nginx -s reload 2>/dev/null || sudo nginx 2>/dev/null
        sleep 2
        if check_nginx; then
            log_message "✅ nginx重启成功"
        else
            log_message "❌ nginx重启失败"
        fi
    else
        log_message "❌ nginx配置异常，无法重启"
    fi
}

# 检查 HTTPS 代理
check_https_proxy() {
    response=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 "$HTTPS_PROXY_URL" 2>/dev/null)
    if [ "$response" = "200" ]; then
        return 0
    fi
    log_message "⚠️  HTTPS代理响应: $response"
    return 1
}

# 重启 HTTPS 代理
restart_https_proxy() {
    # 确保证书存在
    if [ ! -f "$HTTPS_PROXY_CERT" ] || [ ! -f "$HTTPS_PROXY_KEY" ]; then
        log_message "📜 证书缺失，重新生成自签名证书..."
        openssl req -x509 -newkey rsa:2048 -keyout "$HTTPS_PROXY_KEY" -out "$HTTPS_PROXY_CERT" -days 3650 -nodes -subj "/CN=10.0.0.91" 2>/dev/null
    fi
    
    # 杀掉旧进程
    pids=$(ps aux | grep "https-proxy.py" | grep -v grep | awk '{print $2}')
    if [ -n "$pids" ]; then
        for pid in $pids; do
            kill -TERM "$pid" 2>/dev/null
        done
        sleep 2
    fi
    
    # 启动新进程
    cd "$HTTPS_PROXY_DIR" || return 1
    nohup python3 https-proxy.py > /tmp/https-proxy.log 2>&1 &
    sleep 3
    
    if check_https_proxy; then
        log_message "✅ HTTPS代理重启成功"
    else
        log_message "❌ HTTPS代理重启失败"
    fi
}

# 运行主函数
main