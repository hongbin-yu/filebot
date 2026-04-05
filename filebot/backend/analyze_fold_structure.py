#!/usr/bin/env python3
"""
分析Smarti FOLD表结构，理解文件夹层级关系
"""

import re
import json
from collections import defaultdict

# 备份文件路径
backup_file = "/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924/smarti.script.backup"

def analyze_fold_table():
    """分析FOLD表数据"""
    print("🔍 分析FOLD表结构...")
    
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取FOLD表数据
    fold_pattern = r"INSERT INTO FOLD VALUES\((\d+),([^,]*),'([^']*)','([^']*)',([^,]*),([^,]*),'([^']*)'\)"
    fold_matches = re.findall(fold_pattern, content)
    
    if not fold_matches:
        print("未找到FOLD表数据，尝试其他格式...")
        # 尝试更宽松的匹配
        fold_pattern2 = r"INSERT INTO FOLD VALUES\((.*?)\)"
        matches2 = re.findall(fold_pattern2, content, re.MULTILINE | re.DOTALL)
        if matches2:
            print(f"找到 {len(matches2)} 行FOLD数据（原始格式）")
            # 显示前几行
            for i, row in enumerate(matches2[:3]):
                print(f"  示例{i+1}: {row}")
        return
    
    print(f"找到 {len(fold_matches)} 个文件夹记录")
    
    # 解析字段
    folds = []
    for match in fold_matches:
        fold_id, parent_id, name, create_date, admin_id, deleted, reports = match
        folds.append({
            'fold_id': fold_id,
            'parent_id': parent_id,
            'name': name,
            'create_date': create_date,
            'admin_id': admin_id,
            'deleted': deleted,
            'reports': reports
        })
    
    # 分析parent_id分布
    parent_id_counts = defaultdict(int)
    for fold in folds:
        parent_id_counts[fold['parent_id']] += 1
    
    print("\n📊 parent_id分布:")
    print(f"  不同的parent_id值: {len(parent_id_counts)}")
    print(f"  最常见的parent_id:")
    for parent_id, count in sorted(parent_id_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {parent_id}: {count}个文件夹")
    
    # 检查parent_id是否为数字（可能是DRAW ID）
    numeric_parents = sum(1 for fold in folds if fold['parent_id'].isdigit())
    print(f"\n  parent_id为数字: {numeric_parents}/{len(folds)}")
    
    # 检查是否有文件夹指向其他文件夹作为父级
    # 查找parent_id在fold_id列表中的情况
    fold_ids = set(fold['fold_id'] for fold in folds)
    parent_refs_to_fold = sum(1 for fold in folds if fold['parent_id'] in fold_ids)
    print(f"  parent_id指向现有文件夹: {parent_refs_to_fold}/{len(folds)}")
    
    # 显示示例数据
    print("\n📋 文件夹示例（前10个）:")
    for i, fold in enumerate(folds[:10]):
        parent_info = f" -> 父文件夹ID: {fold['parent_id']}" if fold['parent_id'] != 'NULL' else " (根文件夹)"
        print(f"  {fold['fold_id']}: {fold['name']}{parent_info}")
    
    return folds

def analyze_draw_table():
    """分析DRAW表结构"""
    print("\n🔍 分析DRAW表结构...")
    
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取DRAW表数据
    draw_pattern = r"INSERT INTO DRAW VALUES\((\d+),(\d+),([^,]*),'([^']*)'\)"
    draw_matches = re.findall(draw_pattern, content)
    
    if not draw_matches:
        print("未找到DRAW表数据，尝试其他格式...")
        return []
    
    print(f"找到 {len(draw_matches)} 个DRAW记录")
    
    draws = []
    for match in draw_matches:
        draw_id, app_id, draw_order, name = match
        draws.append({
            'draw_id': draw_id,
            'app_id': app_id,
            'draw_order': draw_order,
            'name': name
        })
    
    # 建立DRAW到APP的映射
    draw_to_app = {draw['draw_id']: draw['app_id'] for draw in draws}
    
    print("\n📊 DRAW到APP映射:")
    for draw_id, app_id in list(draw_to_app.items())[:10]:
        print(f"  DRAW {draw_id} -> APP {app_id}")
    
    # 统计每个APP的DRAW数量
    app_draw_counts = defaultdict(int)
    for draw in draws:
        app_draw_counts[draw['app_id']] += 1
    
    print(f"\n  每个APP的DRAW数量:")
    for app_id, count in app_draw_counts.items():
        print(f"    APP {app_id}: {count}个DRAW")
    
    return draws, draw_to_app

def analyze_folder_hierarchy(folds, draw_to_app):
    """分析文件夹层级结构"""
    print("\n🔍 分析文件夹层级结构...")
    
    # 建立FOLD到APP的映射（通过DRAW）
    fold_to_app = {}
    fold_to_draw = {}
    
    for fold in folds:
        if fold['parent_id'] in draw_to_app:
            fold_to_app[fold['fold_id']] = draw_to_app[fold['parent_id']]
            fold_to_draw[fold['fold_id']] = fold['parent_id']
        elif fold['parent_id'] == 'NULL':
            # 根文件夹，没有父DRAW
            pass
        else:
            # parent_id可能指向其他FOLD？
            pass
    
    print(f"  通过DRAW关联到APP的文件夹: {len(fold_to_app)}/{len(folds)}")
    
    # 检查是否有文件夹指向其他文件夹
    fold_parent_map = {}
    for fold in folds:
        if fold['parent_id'] != 'NULL' and fold['parent_id'].isdigit():
            # 检查这个parent_id是DRAW还是FOLD
            if fold['parent_id'] in draw_to_app:
                fold_parent_map[fold['fold_id']] = ('draw', fold['parent_id'])
            elif fold['parent_id'] in [f['fold_id'] for f in folds]:
                fold_parent_map[fold['fold_id']] = ('fold', fold['parent_id'])
            else:
                fold_parent_map[fold['fold_id']] = ('unknown', fold['parent_id'])
    
    # 统计层级类型
    type_counts = defaultdict(int)
    for fold_id, (type_name, _) in fold_parent_map.items():
        type_counts[type_name] += 1
    
    print(f"\n  父级类型分布:")
    for type_name, count in type_counts.items():
        print(f"    {type_name}: {count}个")
    
    # 找出潜在的文件夹层级
    fold_to_fold = {}
    for fold_id, (type_name, parent_id) in fold_parent_map.items():
        if type_name == 'fold':
            fold_to_fold[fold_id] = parent_id
    
    if fold_to_fold:
        print(f"\n📂 发现的文件夹嵌套关系 ({len(fold_to_fold)} 个):")
        for fold_id, parent_fold_id in list(fold_to_fold.items())[:10]:
            # 查找文件夹名称
            child_name = next((f['name'] for f in folds if f['fold_id'] == fold_id), '未知')
            parent_name = next((f['name'] for f in folds if f['fold_id'] == parent_fold_id), '未知')
            print(f"  {child_name} ({fold_id}) -> {parent_name} ({parent_fold_id})")
        
        # 分析层级深度
        print("\n🔍 分析层级深度...")
        depths = {}
        for fold_id in fold_to_fold.keys():
            depth = 0
            current = fold_id
            visited = set()
            while current in fold_to_fold and current not in visited:
                visited.add(current)
                current = fold_to_fold[current]
                depth += 1
                if depth > 20:  # 防止无限循环
                    break
            depths[fold_id] = depth
        
        max_depth = max(depths.values()) if depths else 0
        print(f"  最大嵌套深度: {max_depth}")
    
    return fold_to_fold

def main():
    print("=" * 60)
    print("Smarti文件夹层级结构分析")
    print("=" * 60)
    
    # 分析FOLD表
    folds = analyze_fold_table()
    if not folds:
        return
    
    # 分析DRAW表
    draws, draw_to_app = analyze_draw_table()
    
    # 分析层级结构
    fold_to_fold = analyze_folder_hierarchy(folds, draw_to_app)
    
    print("\n" + "=" * 60)
    print("分析结论")
    print("=" * 60)
    
    if fold_to_fold:
        print("✅ 发现文件夹嵌套关系，需要修复parent_folder_id字段")
        print("   建议: 更新数据库中的folders表，设置正确的parent_folder_id")
    else:
        print("ℹ️  未发现文件夹嵌套关系，所有文件夹可能都是平级")
        print("   注意: 当前导入可能已正确反映了原始结构")
    
    print("\n🔧 修复建议:")
    print("  1. 重新分析原始数据中的文件夹关系")
    print("  2. 更新folders表中的parent_folder_id字段")
    print("  3. 重新计算文件夹路径（path字段）")
    print("  4. 验证修复后的结构")

if __name__ == "__main__":
    main()