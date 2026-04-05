#!/usr/bin/env python3
"""
SimpleIndex 扫描器
根据文件命名规则解析文件路径并填充 simpleindex 表

命名规则（修正后）：
1. 文件夹结构：应用/抽屉/文件夹/文档文件夹/文件
2. 文档文件夹名：doc（仅文档名称，不包含其他信息）
3. 文件名：p1-p2-p3-p4-p5.扩展名

示例：
/存储路径/ERP系统/财务部/2023Q3/合同/001-02-003-04-005.pdf

解析结果：
- Application: ERP系统（从路径倒数第5层）
- drawer: 财务部（从路径倒数第4层）
- folder: 2023Q3（从路径倒数第3层）
- document: 合同（从路径倒数第2层，文档文件夹名）
- page-index1: 001
- page-index2: 02
- page-index3: 003
- page-index4: 04
- page-index5: 005
- file-path: 完整路径
- recordclass: 通过AI分类确定（如"合同"）
"""

import os
import sys
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



def parse_file_name(file_name: str) -> Optional[Dict[str, str]]:
    """
    解析文件名称
    格式：p1-p2-p3-p4-p5.扩展名
    """
    # 去掉扩展名
    name_without_ext = os.path.splitext(file_name)[0]
    parts = name_without_ext.split('-')
    
    if len(parts) == 5:
        return {
            'page_index1': parts[0],
            'page_index2': parts[1],
            'page_index3': parts[2],
            'page_index4': parts[3],
            'page_index5': parts[4]
        }
    else:
        logger.warning(f"文件名称格式错误: {file_name} (期望5部分，得到{len(parts)})")
        return None

def parse_file_path(file_path: Path) -> Optional[Dict[str, str]]:
    """
    从完整文件路径解析所有字段（修正版）
    路径结构：根目录/Application/drawer/folder/doc/p1-p2-p3-p4-p5.ext
    """
    try:
        # 确保是绝对路径
        abs_path = file_path.resolve()
        
        # 获取路径部分
        parts = abs_path.parts
        
        # 需要至少5层：应用/抽屉/文件夹/文档文件夹/文件
        if len(parts) < 5:
            logger.warning(f"路径深度不足: {abs_path} (需要至少5层，实际{len(parts)}层)")
            return None
        
        # 从文件名获取页面索引
        file_name = parts[-1]
        page_info = parse_file_name(file_name)
        if not page_info:
            return None
        
        # 从路径层级提取字段
        # 倒数第5层：Application (如果深度正好5层，parts[-5]是Application)
        # 倒数第4层：drawer
        # 倒数第3层：folder
        # 倒数第2层：document (文档文件夹名)
        application = parts[-5] if len(parts) >= 5 else ""
        drawer = parts[-4] if len(parts) >= 4 else ""
        folder = parts[-3] if len(parts) >= 3 else ""
        document = parts[-2] if len(parts) >= 2 else ""
        
        # 验证字段非空
        if not all([application, drawer, folder, document]):
            logger.warning(f"字段提取不完整: application={application}, drawer={drawer}, folder={folder}, document={document}")
            return None
        
        result = {
            'Application': application,
            'drawer': drawer,
            'folder': folder,
            'document': document,
            'file_path': str(abs_path),
            **page_info
        }
        
        logger.debug(f"解析成功: {result}")
        return result
        
    except Exception as e:
        logger.error(f"解析文件路径失败 {file_path}: {e}")
        return None

def get_recordclass_from_ai(file_path: str) -> str:
    """
    调用AI分类服务获取recordclass
    尝试读取文件内容并调用 localhost:8001/api/v1/ai/classify
    如果失败或文件无法读取，返回空字符串
    """
    try:
        import json
        import urllib.request
        import urllib.error
        
        # 尝试读取文件内容（仅文本文件）
        file_ext = os.path.splitext(file_path)[1].lower()
        text_content = ""
        
        # 如果是文本文件，尝试读取
        if file_ext in ['.txt', '.md', '.json', '.xml', '.html', '.htm']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read(5000)  # 只读取前5000字符
        elif file_ext == '.pdf':
            # PDF文件需要特殊处理，暂时跳过
            logger.debug(f"PDF文件暂不处理AI分类: {file_path}")
            return ""
        else:
            # 其他格式暂不处理
            logger.debug(f"不支持的文件格式: {file_path} ({file_ext})")
            return ""
        
        if not text_content.strip():
            logger.debug(f"文件内容为空: {file_path}")
            return ""
        
        # 调用AI分类服务
        url = "http://localhost:8001/api/v1/ai/classify"
        data = json.dumps({"text": text_content}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        # 设置超时
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('success'):
                category = result.get('category', '')
                logger.debug(f"AI分类成功: {file_path} -> {category}")
                return category
            else:
                logger.warning(f"AI分类失败: {file_path} - {result.get('error')}")
                return ""
                
    except urllib.error.URLError as e:
        logger.warning(f"AI服务不可用: {e}")
        return ""
    except Exception as e:
        logger.warning(f"AI分类处理失败 {file_path}: {e}")
        return ""

def scan_directory(root_dir: str, db_path: str, dry_run: bool = False) -> Tuple[int, int]:
    """
    扫描目录并填充数据库
    
    Args:
        root_dir: 要扫描的根目录
        db_path: 数据库文件路径
        dry_run: 是否试运行（不实际插入数据）
    
    Returns:
        (成功数量, 失败数量)
    """
    root_path = Path(root_dir)
    if not root_path.exists():
        logger.error(f"根目录不存在: {root_dir}")
        return 0, 0
    
    logger.info(f"开始扫描目录: {root_dir}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    success_count = 0
    fail_count = 0
    
    # 遍历目录树
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = Path(dirpath) / filename
            
            # 解析文件路径
            parsed = parse_file_path(file_path)
            if not parsed:
                fail_count += 1
                continue
            
            # 准备数据库插入
            try:
                # 检查是否已存在
                cursor.execute(
                    "SELECT id FROM simpleindex WHERE file_path = ?",
                    (parsed['file_path'],)
                )
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"文件已存在: {parsed['file_path']}")
                    success_count += 1  # 视为成功（已存在）
                    continue
                
                # 插入新记录
                insert_sql = """
                INSERT INTO simpleindex 
                (Application, drawer, folder, document, 
                 page_index1, page_index2, page_index3, page_index4, page_index5,
                 file_path, recordclass)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                params = (
                    parsed['Application'],
                    parsed['drawer'],
                    parsed['folder'],
                    parsed['document'],
                    parsed['page_index1'],
                    parsed['page_index2'],
                    parsed['page_index3'],
                    parsed['page_index4'],
                    parsed['page_index5'],
                    parsed['file_path'],
                    get_recordclass_from_ai(parsed['file_path'])  # 暂时为空
                )
                
                if not dry_run:
                    cursor.execute(insert_sql, params)
                    conn.commit()
                    logger.info(f"插入成功: {parsed['file_path']}")
                else:
                    logger.info(f"[DRY RUN] 将插入: {parsed['file_path']}")
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"数据库操作失败 {parsed['file_path']}: {e}")
                fail_count += 1
                conn.rollback()
    
    conn.close()
    
    logger.info(f"扫描完成: 成功 {success_count}, 失败 {fail_count}")
    return success_count, fail_count

def main():
    parser = argparse.ArgumentParser(description='SimpleIndex 扫描器')
    parser.add_argument('--root-dir', required=True, help='要扫描的根目录')
    parser.add_argument('--db-path', default='filebot.db', help='数据库文件路径 (默认: filebot.db)')
    parser.add_argument('--dry-run', action='store_true', help='试运行，不实际插入数据')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    success, fail = scan_directory(args.root_dir, args.db_path, args.dry_run)
    
    print(f"\n{'='*50}")
    print(f"扫描结果:")
    print(f"  成功: {success}")
    print(f"  失败: {fail}")
    print(f"  总计: {success + fail}")
    
    if args.dry_run:
        print(f"  模式: 试运行（未实际插入数据）")
    print(f"{'='*50}")
    
    sys.exit(0 if fail == 0 else 1)

if __name__ == "__main__":
    main()