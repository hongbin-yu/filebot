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

# Update activeProcesses lastChecked times
for service in data['activeProcesses']:
    data['activeProcesses'][service]['lastChecked'] = now

# Calculate frontend service stop duration
# The services have been stopped since at least 08:47 (11h notification)
# That's about 14.2 hours ago
stop_duration_hours = 14.2

# Add new recentTasks entry
new_task = {
    "id": f"heartbeat-check-{now.replace(':', '').replace('-', '')}",
    "description": f"定期心跳检查 - 前端服务持续停止约{stop_duration_hours:.1f}小时，MySQL身份验证问题持续",
    "completed": now,
    "notified": False,
    "status": "success",
    "details": f"⚠️ WebBot组件API持续停止约{stop_duration_hours:.1f}小时 (端口8000未监听)、✅ FileBot后端持续运行 (端口8001监听, HTTP 200响应)、⚠️ DoardingBot持续停止约{stop_duration_hours:.1f}小时 (端口8002未监听)、⚠️ 前端React持续停止约{stop_duration_hours:.1f}小时 (端口5173未监听)、⚠️ WebBot前端持续停止约{stop_duration_hours:.1f}小时 (端口5175未监听)、✅ WebBot前端编辑器运行正常 (端口5174监听, HTTP 200响应)、✅ PCL转换器运行正常 (端口5000监听, HTTP 200响应)、✅ Ollama运行正常 (端口11434监听, HTTP 200响应)、✅ OpenClaw网关运行正常 (端口18789监听, HTTP 200响应)、✅ Redis运行正常 (端口6379监听)、⚠️ MySQL身份验证问题持续 (端口3306监听但mysqladmin无响应)；📱 WhatsApp网关保持连接；💾 磁盘8%已用 (69Gi/1007Gi)；🧠 内存29%已用 (2.1Gi/7.3Gi used, 5.2Gi available)；📊 负载0.15, 0.19, 0.13（低负载）"
}
data['recentTasks'].insert(0, new_task)

# Keep only last 24 hours of tasks
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
    "loadAvg": "0.15, 0.19, 0.13",
    "diskSpace": "8% used (69G/1007G)",
    "memory": "2.1Gi/7.3Gi used, 5.2Gi available",
    "timestamp": now
}

# Check if we need to add new notification for frontend services
# Last frontend stop notification was at 10:37 (14h), less than 1 hour ago
# So no new notification needed

# MySQL notification already exists, no need to add again

# Write back
with open(status_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated status file at {now}")