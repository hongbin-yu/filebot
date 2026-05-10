#!/bin/bash
# WebBot监控脚本的自守护包装器
# 确保监控脚本在意外退出时自动重启

WEBROOT="/home/hongb/.openclaw/workspace/webbot"
MONITOR_SCRIPT="$WEBROOT/webbot_monitor.sh"
WRAPPER_LOG="$WEBROOT/webbot_wrapper.log"
MAX_RESTARTS=10  # 最大重启次数（防止循环重启）
RESTART_DELAY=5  # 重启延迟（秒）

# 日志函数
log_wrapper() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WRAPPER] $1" | tee -a "$WRAPPER_LOG"
}

# 检查日志大小
check_wrapper_log_size() {
    MAX_SIZE=5242880  # 5MB
    if [ -f "$WRAPPER_LOG" ] && [ $(stat -f%z "$WRAPPER_LOG" 2>/dev/null || stat -c%s "$WRAPPER_LOG") -gt $MAX_SIZE ]; then
        log_wrapper "包装器日志超过5MB，进行轮转..."
        mv "$WRAPPER_LOG" "${WRAPPER_LOG}.$(date '+%Y%m%d_%H%M%S')"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WRAPPER] 开始新的包装器日志" > "$WRAPPER_LOG"
    fi
}

# 信号处理函数
cleanup() {
    log_wrapper "收到停止信号，正在停止监控脚本..."
    # 向监控脚本进程发送TERM信号
    pkill -TERM -f "webbot_monitor.sh" 2>/dev/null
    sleep 2
    # 确保所有相关进程停止
    pkill -KILL -f "webbot_monitor.sh" 2>/dev/null
    log_wrapper "包装器停止完成"
    exit 0
}

# 设置信号处理
trap cleanup INT TERM EXIT

# 主守护循环
main() {
    log_wrapper "🚀 WebBot监控包装器启动"
    log_wrapper "📊 监控脚本: $MONITOR_SCRIPT"
    log_wrapper "📊 最大重启次数: $MAX_RESTARTS"
    log_wrapper "📊 重启延迟: ${RESTART_DELAY}秒"
    
    restart_count=0
    last_restart_time=$(date +%s)
    
    while [ $restart_count -lt $MAX_RESTARTS ]; do
        check_wrapper_log_size
        
        # 检查监控脚本是否存在
        if [ ! -f "$MONITOR_SCRIPT" ]; then
            log_wrapper "❌ 监控脚本不存在: $MONITOR_SCRIPT"
            log_wrapper "💥 包装器停止，因为监控脚本不存在"
            exit 1
        fi
        
        # 检查监控脚本是否可执行
        if [ ! -x "$MONITOR_SCRIPT" ]; then
            log_wrapper "⚠️  监控脚本不可执行，尝试添加执行权限"
            chmod +x "$MONITOR_SCRIPT"
        fi
        
        log_wrapper "▶️  启动监控脚本 (重启次数: $((restart_count + 1))/$MAX_RESTARTS)"
        
        # 运行监控脚本
        "$MONITOR_SCRIPT" &
        monitor_pid=$!
        log_wrapper "📊 监控脚本进程PID: $monitor_pid"
        
        # 等待监控脚本退出
        wait $monitor_pid
        exit_code=$?
        
        current_time=$(date +%s)
        time_since_last_restart=$((current_time - last_restart_time))
        last_restart_time=$current_time
        
        log_wrapper "⚠️  监控脚本退出，退出码: $exit_code"
        log_wrapper "📊 上次运行时长: ${time_since_last_restart}秒"
        
        if [ $exit_code -eq 0 ]; then
            log_wrapper "ℹ️  监控脚本正常退出，包装器也正常退出"
            exit 0
        else
            restart_count=$((restart_count + 1))
            
            if [ $restart_count -ge $MAX_RESTARTS ]; then
                log_wrapper "💥 达到最大重启次数 ($MAX_RESTARTS)，停止重启"
                log_wrapper "📧 建议：检查监控脚本是否存在问题"
                exit 1
            fi
            
            log_wrapper "⏳ 等待 ${RESTART_DELAY} 秒后重启监控脚本..."
            sleep "$RESTART_DELAY"
            
            # 清理可能残留的进程
            pkill -TERM -f "webbot_monitor.sh" 2>/dev/null
            sleep 2
            pkill -KILL -f "webbot_monitor.sh" 2>/dev/null
        fi
    done
    
    log_wrapper "🔚 包装器主循环结束"
}

# 运行主函数
main "$@"