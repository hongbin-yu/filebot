#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime, timezone

# Load current status
status_path = '/home/hongb/.openclaw/workspace/memory/task-status.json'
with open(status_path, 'r') as f:
    data = json.load(f)

# Update lastHeartbeat
now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
data['lastHeartbeat'] = now

# Update activeProcesses health based on actual checks
# Update MySQL status to stopped (still)
if 'mysql' in data['activeProcesses']:
    data['activeProcesses']['mysql']['health'] = 'stopped'
    data['activeProcesses']['mysql']['lastChecked'] = now
    data['activeProcesses']['mysql']['status'] = '服务停止，端口3306监听但MySQL无响应'
    
# Update other services lastChecked
for service in data['activeProcesses']:
    if service != 'mysql':
        data['activeProcesses'][service]['lastChecked'] = now

# Add new recentTasks entry
new_task = {
    "id": f"heartbeat-check-{now.replace(':', '').replace('-', '')}",
    "description": "定期心跳检查 - 多个前端服务持续停止超过11.5小时，MySQL服务停止",
    "completed": now,
    "notified": False,
    "status": "success",
    "details": "⚠️ WebBot组件API持续停止超过11.5小时 (端口8000未监听, HTTP无响应)、✅ FileBot后端持续运行 (PID 2630383, 端口8001监听, HTTP 200响应)、⚠️ DoardingBot持续停止超过11.5小时 (端口8002未监听, HTTP无响应)、⚠️ 前端React持续停止超过11.5小时 (端口5173未监听, HTTP无响应)、⚠️ WebBot前端持续停止超过11.5小时 (端口5175未监听, HTTP无响应)、✅ WebBot前端编辑器运行正常 (PID 2193238, 端口5174监听, HTTP 200响应)、✅ PCL转换器运行正常 (PID 461415, 端口5000监听, HTTP 200响应)、✅ Ollama运行正常 (端口11434监听, HTTP 200响应)、✅ OpenClaw网关运行正常 (PID 2630341, 端口18789监听, HTTP 200响应)、✅ Redis运行正常 (端口6379监听)、⚠️ MySQL服务停止 (端口3306监听但无响应)；📱 WhatsApp网关重新连接 (04:44:46 EDT, +16132199788)；💾 磁盘8%已用 (69Gi/1007Gi)；🧠 内存27%已用 (2.0Gi/7.3Gi used, 5.3Gi available)；📊 负载0.00, 0.06, 0.07（极低负载）"
}
data['recentTasks'].insert(0, new_task)  # Add to beginning

# Keep only last 24 hours of tasks (approx 48 entries if every 30 min)
cutoff_time = datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp() - 86400
data['recentTasks'] = [task for task in data['recentTasks'] 
                       if datetime.fromisoformat(task['completed'].replace('Z', '+00:00')).timestamp() > cutoff_time]

# Update lastChecks
data['lastChecks'] = {
    "processes": now,
    "tasks": now,
    "system": now
}

# Update systemStatus
data['systemStatus'] = {
    "lastUpdate": now,
    "diskUsage": "8%",
    "memoryUsage": "2.0Gi/7.3Gi",
    "loadAvg": "0.00, 0.06, 0.07",
    "diskSpace": "8% used (69G/1007G)",
    "memory": "2.0Gi/7.3Gi used, 5.3Gi available",
    "timestamp": now
}

# Check if we need to add new notification for frontend services
# (Only add if last notification was >1 hour ago)
frontend_services = ["webbot", "doardingbot", "frontend", "webbot-frontend"]
frontend_stopped = all(data['activeProcesses'][s]['health'] == 'stopped' for s in frontend_services if s in data['activeProcesses'])

if frontend_stopped:
    # Find most recent frontend stop notification
    last_notification_time = None
    for notif in data['pendingNotifications']:
        if notif['type'] == 'service_extended_stop':
            notif_time = datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00')).timestamp()
            if last_notification_time is None or notif_time > last_notification_time:
                last_notification_time = notif_time
    
    # If no notification or last notification >1 hour ago, add new
    if last_notification_time is None or (datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp() - last_notification_time) > 3600:
        new_notif = {
            "id": f"frontend-services-stopped-11.5h-{now}",
            "type": "service_extended_stop",
            "service": "multiple_frontends",
            "timestamp": now,
            "message": "多个前端服务已持续停止超过11.5小时：WebBot组件API (8000)、前端React (5173)、WebBot前端 (5175)、DoardingBot (8002)。这些服务急需人工重启。核心后端服务运行正常。",
            "priority": "high",
            "acknowledged": False
        }
        data['pendingNotifications'].append(new_notif)

# MySQL notification already exists, no need to add again

# Write back
with open(status_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated status file at {now}")