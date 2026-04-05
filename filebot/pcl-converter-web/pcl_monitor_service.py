#!/usr/bin/env python3
"""
PCL文件监控转换服务 - Windows/WSL环境
监控输入目录中的.pcl文件，使用PCLXform转换为PDF，移动已处理文件

使用方式：
1. 在WSL中运行：python3 pcl_monitor_service.py
2. 或设置为cron任务：*/1 * * * * cd /path && python3 pcl_monitor_service.py

注意：此脚本设计在WSL中运行，调用Windows的PCLXform.exe工具
"""

import os
import sys
import time
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# ========== 配置 ==========
# 输入输出目录（使用WSL路径格式）
INPUT_DIR = "/mnt/c/workspace/pcl_input"        # 监控的PCL文件目录
OUTPUT_DIR = "/mnt/c/workspace/pcl2pdf"         # PDF输出目录
PROCESSED_DIR = "/mnt/c/workspace/pcl_processed" # 已处理的PCL文件目录
FAILED_DIR = "/mnt/c/workspace/pcl_failed"      # 转换失败的PCL文件目录

# PCL转换工具配置
PCLXFORM_PATH = "/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe"
TEMPLATE_PATH = "/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/default.tpt"
CONVERSION_TIMEOUT = 120  # 转换超时时间（秒）

# 日志配置
LOG_DIR = "/mnt/c/workspace/pcl_logs"
LOG_FILE = os.path.join(LOG_DIR, f"pcl_monitor_{datetime.now().strftime('%Y%m%d')}.log")

# 确保目录存在
for dir_path in [INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR, FAILED_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== 辅助函数 ==========

def to_windows_path(wsl_path):
    """将WSL路径转换为Windows路径"""
    if wsl_path.startswith('/mnt/c/'):
        return 'C:' + wsl_path[6:].replace('/', '\\')
    elif wsl_path.startswith('/mnt/'):
        drive = wsl_path[5:6].upper()
        return f'{drive}:' + wsl_path[7:].replace('/', '\\')
    else:
        # 已经是Windows路径或相对路径
        return wsl_path

def convert_pcl_to_pdf(input_pcl_path, output_pdf_path):
    """
    使用PCLXform转换PCL文件为PDF
    
    Args:
        input_pcl_path: 输入PCL文件路径（WSL格式）
        output_pdf_path: 输出PDF文件路径（WSL格式）
    
    Returns:
        (success, message): 转换是否成功和消息
    """
    try:
        # 验证输入文件存在
        if not os.path.exists(input_pcl_path):
            return False, f"输入文件不存在: {input_pcl_path}"
        
        # 验证工具存在
        if not os.path.exists(PCLXFORM_PATH):
            return False, f"PCLXform工具不存在: {PCLXFORM_PATH}"
        
        # 转换路径为Windows格式
        tool_path_win = to_windows_path(PCLXFORM_PATH)
        template_path_win = to_windows_path(TEMPLATE_PATH)
        input_dir_win = to_windows_path(os.path.dirname(input_pcl_path))
        input_file_win = os.path.basename(input_pcl_path)
        output_dir_win = to_windows_path(os.path.dirname(output_pdf_path))
        output_file_win = os.path.basename(output_pdf_path)
        tool_dir_win = to_windows_path(os.path.dirname(PCLXFORM_PATH))
        
        # 构建DOS命令（基于用户验证的格式）
        # 格式: PclXform.exe template.tpt inp="文件名" inf="目录" outp="文件名" outf="目录" Silent=true
        # 用户验证的命令: PclXform.exe default.tpt inp="00000001.pcl" inf="c:\workspace\sample" outp="test.pdf" outf="c:\workspace\sample"
        # 使用相对路径，因为工作目录已切换到工具目录
        dos_command = (
            f'PclXform.exe default.tpt '
            f'inp="{input_file_win}" inf="{input_dir_win}" '
            f'outp="{output_file_win}" outf="{output_dir_win}" '
            f'Silent=true'
        )
        
        # 在WSL中通过cmd.exe执行Windows命令
        # 设置工作目录为工具所在的WSL路径，避免UNC路径问题
        cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]
        tool_dir_wsl = os.path.dirname(PCLXFORM_PATH)
        
        logger.info(f"执行转换命令: {dos_command}")
        logger.info(f"工作目录: {tool_dir_wsl}")
        
        # 保存当前目录并切换到工具目录，避免cmd.exe的UNC路径问题
        original_cwd = os.getcwd()
        os.chdir(tool_dir_wsl)
        
        try:
            # 执行转换（不设置cwd，因为当前目录已切换）
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT
            )
        finally:
            # 恢复原始目录
            os.chdir(original_cwd)
        
        logger.info(f"转换返回码: {result.returncode}")
        if result.stdout:
            logger.debug(f"转换输出: {result.stdout[:500]}")
        if result.stderr:
            logger.warning(f"转换错误: {result.stderr[:500]}")
        
        # 检查转换结果
        if result.returncode == 0:
            if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
                return True, "转换成功"
            else:
                return False, "转换完成但输出文件为空或不存在"
        else:
            error_msg = f"转换失败 (返回码: {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr[:200]}"
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, f"转换超时（{CONVERSION_TIMEOUT}秒）"
    except Exception as e:
        return False, f"转换过程中发生错误: {str(e)}"
    finally:
        # 确保转换后终止PclXform.exe进程，避免残留GUI窗口
        try:
            subprocess.run(
                ['/mnt/c/Windows/System32/taskkill.exe', '/F', '/IM', 'PclXform.exe'],
                capture_output=True,
                timeout=5
            )
            logger.debug("转换完成后终止PclXform.exe进程")
        except Exception as e:
            logger.debug(f"终止进程时忽略错误: {e}")

def move_file(source_path, target_dir, prefix=""):
    """
    移动文件到目标目录，添加前缀避免文件名冲突
    
    Args:
        source_path: 源文件路径
        target_dir: 目标目录
        prefix: 文件名前缀（可选）
    
    Returns:
        移动后的文件路径，如果失败则返回None
    """
    try:
        if not os.path.exists(source_path):
            return None
        
        filename = os.path.basename(source_path)
        if prefix:
            # 添加时间戳前缀避免冲突
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}_{filename}"
        
        target_path = os.path.join(target_dir, filename)
        
        # 如果目标文件已存在，先删除
        if os.path.exists(target_path):
            os.remove(target_path)
        
        shutil.move(source_path, target_path)
        logger.info(f"移动文件: {source_path} -> {target_path}")
        return target_path
    except Exception as e:
        logger.error(f"移动文件失败 {source_path} -> {target_dir}: {e}")
        return None

# ========== 主监控函数 ==========

def monitor_and_convert():
    """监控输入目录并转换PCL文件"""
    logger.info("开始扫描PCL文件...")
    
    # 扫描输入目录中的.pcl文件
    pcl_files = []
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith('.pcl'):
            file_path = os.path.join(INPUT_DIR, filename)
            pcl_files.append(file_path)
    
    if not pcl_files:
        logger.info("未发现新的PCL文件")
        return 0
    
    logger.info(f"发现 {len(pcl_files)} 个PCL文件需要处理")
    
    success_count = 0
    failed_count = 0
    
    for pcl_path in pcl_files:
        filename = os.path.basename(pcl_path)
        logger.info(f"处理文件: {filename}")
        
        # 生成输出PDF文件名（相同名称，扩展名改为.pdf）
        pdf_filename = os.path.splitext(filename)[0] + ".pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
        
        # 执行转换
        success, message = convert_pcl_to_pdf(pcl_path, pdf_path)
        
        if success:
            logger.info(f"转换成功: {filename} -> {pdf_filename}")
            
            # 移动已处理的PCL文件到processed目录
            moved_path = move_file(pcl_path, PROCESSED_DIR, "processed")
            if moved_path:
                success_count += 1
            else:
                logger.warning(f"无法移动已处理文件: {pcl_path}")
        else:
            logger.error(f"转换失败: {filename} - {message}")
            
            # 移动失败的PCL文件到failed目录
            moved_path = move_file(pcl_path, FAILED_DIR, "failed")
            if moved_path:
                failed_count += 1
            else:
                logger.warning(f"无法移动失败文件: {pcl_path}")
    
    logger.info(f"处理完成: 成功 {success_count}, 失败 {failed_count}, 总计 {len(pcl_files)}")
    return success_count

# ========== 主程序 ==========

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("PCL文件监控转换服务启动")
    logger.info(f"输入目录: {INPUT_DIR}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info(f"已处理目录: {PROCESSED_DIR}")
    logger.info(f"失败目录: {FAILED_DIR}")
    logger.info(f"PCL工具: {PCLXFORM_PATH}")
    logger.info("=" * 60)
    
    try:
        # 单次执行模式（适合cron任务）
        success_count = monitor_and_convert()
        
        if success_count > 0:
            logger.info(f"本次转换成功 {success_count} 个文件")
        else:
            logger.info("本次没有文件需要转换或转换失败")
            
    except Exception as e:
        logger.error(f"服务执行异常: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())