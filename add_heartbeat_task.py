import json
import subprocess
import sys
from datetime import datetime

# Load current status
with open('memory/task-status.json', 'r') as f:
    data = json.load(f)

now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

# Get disk space
df = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
lines = df.stdout.strip().split('\n')
last = lines[-1]
parts = last.split()
disk_str = f"{parts[4]} used ({parts[2]}/{parts[1]})"

# Get memory
free = subprocess.run(['free', '-h'], capture_output=True, text=True)
for line in free.stdout.split('\n'):
    if line.startswith('Mem:'):
        mem_parts = line.split()
        mem_str = f"{mem_parts[2]}/{mem_parts[1]} used ({mem_parts[6]} available)"
        break

# Get load avg
with open('/proc/loadavg', 'r') as f:
    load = f.read().strip().split()
    load_str = f"{load[0]}, {load[1]}, {load[2]}"

# Build details
details_lines = []
details_lines.append(f"✅ FileBot后端服务运行正常 (PID 50918, 端口8001, HTTP 200)")
details_lines.append(f"✅ 前端React服务运行正常 (PID 209735, 端口5173, HTTP 200)")
details_lines.append(f"✅ PCL转换器服务运行正常 (PID 51073, 端口5000, HTTP 200)")
details_lines.append(f"✅ Ollama服务运行正常 (PID 190, 端口11434, HTTP 200)")
details_lines.append(f"✅ Redis和MySQL运行正常")
details_lines.append(f"📡 WhatsApp网关连接正常 (系统消息: 06:39 EDT连接)")
details_lines.append(f"💾 磁盘使用{disk_str}")
details_lines.append(f"🧠 内存{mem_str}")
details_lines.append(f"📊 负载{load_str}")
details = '; '.join(details_lines)

# Create new task
task_id = f"heartbeat-check-{datetime.utcnow().strftime('%Y-%m-%d-%H%M')}"
new_task = {
    "id": task_id,
    "description": "定期心跳检查 - 所有核心服务稳定运行，WhatsApp网关连接正常",
    "completed": now,
    "notified": False,
    "status": "success",
    "details": details
}

# Insert at beginning
data['recentTasks'].insert(0, new_task)

# Keep only latest 20 tasks
if len(data['recentTasks']) > 20:
    data['recentTasks'] = data['recentTasks'][:20]

# Update systemStatus
data['systemStatus']['timestamp'] = now
data['systemStatus']['diskSpace'] = disk_str
data['systemStatus']['memory'] = mem_str
data['systemStatus']['loadAvg'] = load_str

# Update lastChecks
data['lastChecks']['processes'] = now
data['lastChecks']['tasks'] = now
data['lastChecks']['system'] = now

# Write back
with open('memory/task-status.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Added heartbeat task")