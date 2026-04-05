#!/usr/bin/env python3
import json
import subprocess
import shlex
from datetime import datetime, timezone

status_file = "/home/hongb/.openclaw/workspace/memory/task-status.json"

def get_current_timestamp():
    return datetime.now(timezone.utc).isoformat()

# 加载当前状态
with open(status_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 检查WebBot实际状态
webbot_status = {
    "pid": "unknown",
    "port": 8000,
    "health": "stopped",
    "lastChecked": get_current_timestamp(),
    "status": "未知"
}

# 检查端口监听
try:
    result = subprocess.run(shlex.split("netstat -tlnp 2>/dev/null | grep :8000 || ss -tlnp 2>/dev/null | grep :8000"), 
                           capture_output=True, text=True, shell=True)
    if result.returncode == 0 and ":8000" in result.stdout:
        # 提取PID
        import re
        match = re.search(r'LISTEN\s+(\d+)/', result.stdout)
        if match:
            webbot_status["pid"] = match.group(1)
        
        # 检查API响应
        import urllib.request
        try:
            req = urllib.request.Request("http://localhost:8000/api/v1/pages/", method="HEAD")
            response = urllib.request.urlopen(req, timeout=5)
            if response.status == 200:
                webbot_status["health"] = "healthy"
                webbot_status["status"] = f"运行正常，端口8000监听，HTTP {response.status}响应"
            else:
                webbot_status["health"] = "warning"
                webbot_status["status"] = f"端口监听但HTTP状态异常: {response.status}"
        except Exception as e:
            webbot_status["health"] = "warning"
            webbot_status["status"] = f"端口监听但API不可达: {str(e)}"
    else:
        webbot_status["health"] = "stopped"
        webbot_status["status"] = "服务停止，端口8000未监听"
except Exception as e:
    webbot_status["health"] = "error"
    webbot_status["status"] = f"检查过程出错: {str(e)}"

# 更新状态
data["activeProcesses"]["webbot"] = webbot_status

# 更新最后检查时间
data["lastChecks"]["processes"] = get_current_timestamp()

# 保存
with open(status_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"WebBot状态已更新: {webbot_status['health']} - {webbot_status['status']}")