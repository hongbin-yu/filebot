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

# Update lastChecks
data['lastChecks'] = {
    "processes": now,
    "tasks": now,
    "system": now
}

# Update activeProcesses lastChecked times
for service in data['activeProcesses']:
    data['activeProcesses'][service]['lastChecked'] = now

# Add new recentTasks entry for manual check
new_task = {
    "id": f"manual-check-{now.replace(':', '').replace('-', '')}",
    "description": "用户手动检查 - 确认MySQL和前端服务仍停止",
    "completed": now,
    "notified": True,
    "status": "success",
    "details": "用户收到通知后手动检查确认：⚠️ MySQL数据库服务仍停止 (端口3306监听但无响应)、⚠️ WebBot组件API持续停止 (端口8000未监听)、⚠️ DoardingBot持续停止 (端口8002未监听)、⚠️ 前端React持续停止 (端口5173未监听)、⚠️ WebBot前端持续停止 (端口5175未监听)、✅ 核心后端服务运行正常"
}
data['recentTasks'].insert(0, new_task)

# Keep only last 24 hours of tasks
cutoff_time = datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp() - 86400
data['recentTasks'] = [task for task in data['recentTasks'] 
                       if datetime.fromisoformat(task['completed'].replace('Z', '+00:00')).timestamp() > cutoff_time]

# Write back
with open(status_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated status file at {now}")