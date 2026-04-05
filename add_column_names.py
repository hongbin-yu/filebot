#!/usr/bin/env python3
"""
为Smart iAdmin CSV文件添加列名
基于Hibernate映射文件和已知的映射关系
"""

import csv
import os
import sys
from pathlib import Path

# 表列名映射（基于Hibernate映射和已知结构）
COLUMN_MAPPINGS = {
    'COLD_INDEXES': [
        'ID',           # 0: 主键ID
        'LEVELID',      # 1: 层级ID
        'AUDITID',      # 2: 审计ID
        'PAGE',         # 3: 页面
        'IROW',         # 4: 行索引
        'COLN',         # 5: 列号
        'LENGTH',       # 6: 长度
        'LITERAL',      # 7: 字面值
        'SAMPLE',       # 8: 样本
        'LEFTTRIM',     # 9: 左修剪
        'INVALID_ACTION', # 10: 无效操作
        'LEFT_OFFSET',  # 11: 左偏移
        'DATEFORMAT',   # 12: 日期格式
    ],
    'COLD_REPORT': [
        'ID',           # 0: 主键ID
        'SETID',        # 1: 集合ID
        'SOURCEID',     # 2: 数据源ID
        'DISPOSITIONID', # 3: 处置ID
        'APPID',        # 4: 应用ID
        'SAMPLEID',     # 5: 样本ID
        'EXTERN_ID',    # 6: 外部文件ID
        'FORMID',       # 7: 表单ID
        'RECORDCLASSID', # 8: 记录类ID
        'INDEXID',      # 9: 索引ID
        'NAME',         # 10: 名称
        'COMMENTS',     # 11: 注释
        'LEVELID',      # 12: 层级ID
        'TEXTFIELDSID', # 13: 文本字段ID
        'AUDITID',      # 14: 审计ID
        'INDEX_PAGES',  # 15: 索引页面标志
        'MODIFY_DATE',  # 16: 修改日期
    ],
    'COLD_FIELDS': [
        'ID',           # 0: 主键ID
        'FORMID',       # 1: 表单ID
        'LEVELID',      # 2: 层级ID
        'COLN',         # 3: 列号
        'LENGTH',       # 4: 长度
        'TYPE',         # 5: 类型
        'NAME',         # 6: 名称
        'DISPLAYNAME',  # 7: 显示名称
        'TABLENAME',    # 8: 表名
        'COLUMNNAME',   # 9: 列名
        'REQUIRED',     # 10: 是否必需
        'DEFAULTVALUE', # 11: 默认值
        'MASKID',       # 12: 掩码ID
        # 可能有更多列
    ],
    'COLD_FORM_FIELDS': [
        'ID',           # 0: 主键ID
        'FORMID',       # 1: 表单ID
        'LEVELID',      # 2: 层级ID
        'COLN',         # 3: 列号
        'FIELDNAME',    # 4: 字段名
        'TABLENAME',    # 5: 表名
        'COLUMNNAME',   # 6: 列名
        'TYPE',         # 7: 类型
        'LENGTH',       # 8: 长度
        'DECIMALS',     # 9: 小数位数
        'REQUIRED',     # 10: 是否必需
        'DEFAULTVALUE', # 11: 默认值
        'DISPLAYNAME',  # 12: 显示名称
        # 可能有更多列
    ],
    'APP': [
        'ID',           # 0: 主键ID
        'AUDITID',      # 1: 审计ID
        'NAME',         # 2: 名称
        'MODIFY_DATE',  # 3: 修改日期
        'DEFAULT_INDEXID', # 4: 默认索引ID
        'COMMENTS',     # 5: 注释
        'REPORTID',     # 6: 报表ID
        'OWNER',        # 7: 所有者
        'TEMPLATE',     # 8: 模板
        # 可能有更多列
    ],
    'DRAW': [
        'ID',           # 0: 主键ID
        'APPID',        # 1: 应用ID
        'NAME',         # 2: 名称
        'MODIFY_DATE',  # 3: 修改日期
        'COMMENTS',     # 4: 注释
        'AUDITID',      # 5: 审计ID
        # 可能有更多列
    ],
    'FOLD': [
        'ID',           # 0: 主键ID
        'DRAWID',       # 1: 抽屉ID
        'NAME',         # 2: 名称
        'MODIFY_DATE',  # 3: 修改日期
        'COMMENTS',     # 4: 注释
        'AUDITID',      # 5: 审计ID
        # 可能有更多列
    ],
    'DOC': [
        'ID',           # 0: 主键ID
        'FOLDID',       # 1: 文件夹ID
        'NAME',         # 2: 名称
        'MODIFY_DATE',  # 3: 修改日期
        'COMMENTS',     # 4: 注释
        'AUDITID',      # 5: 审计ID
        'PAGECOUNT',    # 6: 页数
        'FILESIZE',     # 7: 文件大小
        # 可能有更多列
    ],
}

def add_column_names(input_csv, output_csv, table_name):
    """为CSV文件添加列名"""
    table_name_upper = table_name.upper()
    
    if table_name_upper not in COLUMN_MAPPINGS:
        print(f"警告: 表 {table_name} 无预定义列名映射")
        # 使用通用列名
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 跳过可能的标题行
            first_row = next(reader, None)
            if not first_row:
                print(f"错误: 文件为空: {input_csv}")
                return False
            
            if first_row and len(first_row) > 0 and first_row[0].startswith('col'):
                # 这是标题行，跳过它
                rows = list(reader)
                if rows:
                    num_cols = len(rows[0])
                else:
                    print(f"错误: 文件只有标题行: {input_csv}")
                    return False
            else:
                # 不是标题行，包含第一行
                rows = [first_row] + list(reader)
                num_cols = len(first_row)
            
            columns = [f"col{i+1}" for i in range(num_cols)]
    else:
        columns = COLUMN_MAPPINGS[table_name_upper]
        
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 跳过可能的标题行（如果第一行是col1, col2, ...）
            first_row = next(reader, None)
            if first_row and len(first_row) > 0 and first_row[0].startswith('col'):
                # 这是标题行，跳过它
                rows = list(reader)
            else:
                # 不是标题行，包含第一行
                rows = [first_row] + list(reader) if first_row else []
        
        # 检查列数是否匹配
        if rows:
            actual_cols = len(rows[0])
            expected_cols = len(columns)
            if actual_cols != expected_cols:
                print(f"警告: 列数不匹配 - 表 {table_name}: 预期 {expected_cols}, 实际 {actual_cols}")
                # 调整列名
                if actual_cols > expected_cols:
                    # 添加额外的通用列名
                    for i in range(expected_cols, actual_cols):
                        columns.append(f"extra_col_{i+1}")
                else:
                    # 截断列名
                    columns = columns[:actual_cols]
    
    # 写入新文件
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    
    print(f"已添加列名: {input_csv} -> {output_csv}")
    print(f"列名: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
    return True

def process_directory(input_dir, output_dir):
    """处理目录中的所有CSV文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    csv_files = list(Path(input_dir).glob("*.csv"))
    if not csv_files:
        print(f"错误: 目录中无CSV文件: {input_dir}")
        return False
    
    success_count = 0
    for csv_file in csv_files:
        # 从文件名提取表名（去掉.csv，转为大写）
        table_name = csv_file.stem.upper()
        output_file = Path(output_dir) / csv_file.name
        
        if add_column_names(str(csv_file), str(output_file), table_name):
            success_count += 1
    
    print(f"\n处理完成: {success_count}/{len(csv_files)} 个文件")
    print(f"输出目录: {output_dir}")
    return success_count > 0

def main():
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <输入目录> <输出目录>")
        print(f"示例: {sys.argv[0]} ./hsqldb_export ./hsqldb_export_with_headers")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}")
        sys.exit(1)
    
    process_directory(input_dir, output_dir)

if __name__ == '__main__':
    main()