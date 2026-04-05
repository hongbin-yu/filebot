#!/usr/bin/env python3
"""
处理转换任务脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.conversion_worker import ConversionWorker
import uuid

def main():
    if len(sys.argv) != 2:
        print("用法: python process_conversion_task.py <task_id>")
        sys.exit(1)
    
    task_id_str = sys.argv[1]
    try:
        task_id = uuid.UUID(task_id_str)
    except ValueError:
        print(f"错误: 无效的UUID格式: {task_id_str}")
        sys.exit(1)
    
    db = SessionLocal()
    try:
        worker = ConversionWorker(db)
        print(f"开始处理转换任务: {task_id}")
        success = worker.process_task(task_id)
        
        if success:
            print(f"转换任务处理成功: {task_id}")
        else:
            print(f"转换任务处理失败: {task_id}")
            
        # 重新查询任务状态
        from app.models.conversion_task import ConversionTask, TaskStatus
        task = db.query(ConversionTask).filter(ConversionTask.id == task_id).first()
        if task:
            print(f"任务状态: {task.status}")
            print(f"进度: {task.progress}%")
            print(f"当前步骤: {task.current_step}")
            if task.error_message:
                print(f"错误信息: {task.error_message}")
                
    except Exception as e:
        print(f"处理任务时发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()