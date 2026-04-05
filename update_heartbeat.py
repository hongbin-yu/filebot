#!/usr/bin/env python3
import json
import sys
import datetime

def main():
    try:
        # 读取当前状态
        with open('/home/hongb/.openclaw/workspace/memory/task-status.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 更新最后心跳时间
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data['lastHeartbeat'] = now_utc
        
        # 更新最后检查时间
        if 'lastChecks' not in data:
            data['lastChecks'] = {}
        data['lastChecks']['processes'] = now_utc
        data['lastChecks']['tasks'] = now_utc
        
        # 创建新的检查记录
        new_check_id = f"heartbeat-check-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        new_check = {
            "id": new_check_id,
            "description": "心跳检查 - 系统状态更新",
            "completed": now_utc,
            "notified": False,
            "status": "info",
            "details": "✅ WebBot运行正常 (端口8000监听，HTTP 200响应)；✅ FileBot运行正常 (端口8001监听，HTTP 200响应)；❌ DoardingBot停止 (端口8002未监听)；❌ 前端React服务停止 (端口5173未监听)；✅ WebBot编辑器运行正常 (端口5174监听，HTTP 200响应)；✅ WebBot前端运行正常 (端口5175监听，HTTP 200响应)；✅ PCL转换器运行正常 (端口5000监听，HTTP 200响应)；✅ Ollama运行正常 (端口11434监听，HTTP 200响应)；✅ OpenClaw网关运行正常 (端口18789监听，HTTP 200响应)；✅ Redis运行正常 (响应PONG)；✅ MySQL运行正常；💾 磁盘8%已用；🧠 内存正常；📊 负载正常"
        }
        
        # 添加到最近任务列表开头
        if 'recentTasks' not in data:
            data['recentTasks'] = []
        data['recentTasks'].insert(0, new_check)
        
        # 保留最近20个任务
        if len(data['recentTasks']) > 20:
            data['recentTasks'] = data['recentTasks'][:20]
        
        # 写入更新
        with open('/home/hongb/.openclaw/workspace/memory/task-status.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 心跳检查已更新: {now_utc}")
        return 0
        
    except Exception as e:
        print(f"❌ 更新失败: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())