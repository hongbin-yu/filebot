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

# Update activeProcesses
# MySQL: service running but authentication issue
if 'mysql' in data['activeProcesses']:
    data['activeProcesses']['mysql']['health'] = 'warning'
    data['activeProcesses']['mysql']['lastChecked'] = now
    data['activeProcesses']['mysql']['status'] = '服务运行但身份验证失败 (端口3306监听，mysqladmin无响应，连接被拒绝)'
    
# Update other services lastChecked
for service in data['activeProcesses']:
    if service != 'mysql':
        data['activeProcesses'][service]['lastChecked'] = now

# Add new recentTasks entry
new_task = {
    "id": f"heartbeat-check-{now.replace(':', '').replace('-', '')}",
    "description": "定期心跳检查 - 前端服务持续停止~11.8小时，MySQL运行但身份验证失败",
    "completed": now,
    "notified": False,
    "status": "success",
    "details": "⚠️ WebBot组件API持续停止约11.8小时 (端口8000未监听)、✅ FileBot后端持续运行 (端口8001监听, HTTP 200响应)、⚠️ DoardingBot持续停止约11.8小时 (端口8002未监听)、⚠️ 前端React持续停止约11.8小时 (端口5173未监听)、⚠️ WebBot前端持续停止约11.8小时 (端口5175未监听)、✅ WebBot前端编辑器运行正常 (端口5174监听, HTTP 200响应)、✅ PCL转换器运行正常 (端口5000监听, HTTP 200响应)、✅ Ollama运行正常 (端口11434监听, HTTP 200响应)、✅ OpenClaw网关运行正常 (端口18789监听, HTTP 200响应)、✅ Redis运行正常 (端口6379监听)、⚠️ MySQL服务运行但身份验证失败 (端口3306监听，mysqladmin无响应，连接被拒绝)；📱 WhatsApp网关重新连接 (05:17:38 EDT, +16132199788)；💾 磁盘8%已用 (69Gi/1007Gi)；🧠 内存29%已用 (2.1Gi/7.3Gi used, 5.2Gi available)；📊 负载0.00, 0.05, 0.07（极低负载）"
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
    "loadAvg": "0.00, 0.05, 0.07",
    "diskSpace": "8% used (69G/1007G)",
    "memory": "2.1Gi/7.3Gi used, 5.2Gi available",
    "timestamp": now
}

# Check if we need to add new notification for MySQL status clarification
# Remove old mysql_stop notification and add new one
mysql_notifications = [n for n in data['pendingNotifications'] if n['type'] == 'mysql_stop']
if mysql_notifications:
    # Remove old mysql stop notification
    data['pendingNotifications'] = [n for n in data['pendingNotifications'] if n['type'] != 'mysql_stop']
    # Add new notification about authentication issue
    new_mysql_notif = {
        "id": f"mysql-auth-issue-{now}",
        "type": "mysql_auth_issue",
        "service": "mysql",
        "timestamp": now,
        "message": "MySQL服务实际在运行但身份验证失败（端口3306监听，mysqladmin无响应，连接被拒绝）。需要检查密码/权限配置。",
        "priority": "medium",
        "acknowledged": False
    }
    data['pendingNotifications'].append(new_mysql_notif)

# Check frontend services: last notification was at 08:47, less than 1 hour ago, so no new notification

# Write back
with open(status_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated status file at {now}")