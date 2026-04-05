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
# We'll keep existing PID and other fields, just update health and lastChecked
for service in data['activeProcesses']:
    data['activeProcesses'][service]['lastChecked'] = now
    # Health will be updated later based on actual checks
    # For now keep as is

# Add new recentTasks entry
new_task = {
    "id": f"heartbeat-check-{now.replace(':', '').replace('-', '')}",
    "description": "定期心跳检查 - 多个前端服务持续停止超过10.5小时，急需人工干预",
    "completed": now,
    "notified": False,
    "status": "success",
    "details": "⚠️ WebBot组件API持续停止超过10.5小时 (端口8000未监听, HTTP无响应)、✅ FileBot后端持续运行 (PID 2630383, 端口8001监听, HTTP 200响应)、⚠️ DoardingBot持续停止超过10.5小时 (端口8002未监听, HTTP无响应)、⚠️ 前端React持续停止超过10.5小时 (端口5173未监听, HTTP无响应)、⚠️ WebBot前端持续停止超过10.5小时 (端口5175未监听, HTTP无响应)、✅ WebBot前端编辑器运行正常 (PID 2193238, 端口5174监听, HTTP 200响应)、✅ PCL转换器运行正常 (PID 461415, 端口5000监听, HTTP 200响应)、✅ Ollama运行正常 (端口11434监听, HTTP 200响应)、✅ OpenClaw网关运行正常 (PID 2630341, 端口18789监听, HTTP 200响应)、✅ Redis运行正常 (端口6379监听)、✅ MySQL运行正常 (端口3306监听)；📱 WhatsApp网关重新连接 (03:38:42 EDT, +16132199788)；💾 磁盘8%已用 (69Gi/1007Gi)；🧠 内存29%已用 (2.1Gi/7.3Gi used, 5.2Gi available)；📊 负载0.14, 0.09, 0.09（极低负载）"
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
    "memoryUsage": "2.1Gi/7.3Gi",
    "loadAvg": "0.14, 0.09, 0.09",
    "diskSpace": "8% used (69G/1007G)",
    "memory": "2.1Gi/7.3Gi used, 5.2Gi available",
    "timestamp": now
}

# Add new pending notification if services still stopped for extended period
# Check if we need to add a new notification (every hour)
frontend_services = ["webbot", "doardingbot", "frontend", "webbot-frontend"]
all_stopped = all(data['activeProcesses'][s]['health'] == 'stopped' for s in frontend_services if s in data['activeProcesses'])
if all_stopped:
    # Calculate hours stopped based on first notification timestamp
    # For simplicity, add notification if last notification was >1 hour ago
    last_notification_time = None
    for notif in data['pendingNotifications']:
        if notif['type'] == 'service_extended_stop':
            # Parse timestamp
            notif_time = datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00')).timestamp()
            if last_notification_time is None or notif_time > last_notification_time:
                last_notification_time = notif_time
    
    if last_notification_time is None or (datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp() - last_notification_time) > 3600:
        # Add new notification
        new_notif = {
            "id": f"frontend-services-stopped-10.5h-{now}",
            "type": "service_extended_stop",
            "service": "multiple_frontends",
            "timestamp": now,
            "message": "多个前端服务已持续停止超过10.5小时：WebBot组件API (8000)、前端React (5173)、WebBot前端 (5175)、DoardingBot (8002)。这些服务急需人工重启。核心后端服务运行正常。",
            "priority": "high",
            "acknowledged": False
        }
        data['pendingNotifications'].append(new_notif)

# Write back
with open(status_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated status file at {now}")