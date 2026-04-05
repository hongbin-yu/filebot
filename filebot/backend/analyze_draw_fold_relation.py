#!/usr/bin/env python3
"""
分析DRAW和FOLD关系，为修复层级做准备
"""

import re
import json
from collections import defaultdict

# 备份文件路径
backup_file = "/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924/smarti.script.backup"

def parse_inserts():
    """解析INSERT语句，提取DRAW和FOLD数据"""
    print("🔍 解析原始数据...")
    
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取DRAW数据
    draw_pattern = r"INSERT INTO DRAW VALUES\((\d+),(\d+),'([^']*)','([^']*)',([^,]*),([^,]*),([^)]*)\)"
    draw_matches = re.findall(draw_pattern, content)
    
    draws = []
    for match in draw_matches:
        draw_id, app_id, name, create_date, admin_id, deleted, draw_order = match
        draws.append({
            'draw_id': draw_id,
            'app_id': app_id,
            'name': name,
            'create_date': create_date,
            'admin_id': admin_id,
            'deleted': deleted,
            'draw_order': draw_order
        })
    
    print(f"  找到 {len(draws)} 个DRAW记录")
    
    # 提取FOLD数据
    fold_pattern = r"INSERT INTO FOLD VALUES\((\d+),(\d+),'([^']*)','([^']*)',([^,]*),([^,]*),([^)]*)\)"
    fold_matches = re.findall(fold_pattern, content)
    
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
    
    print(f"  找到 {len(folds)} 个FOLD记录")
    
    # 提取APP数据
    app_pattern = r"INSERT INTO APP VALUES\((\d+),([^,]*),'([^']*)','([^']*)',(\d+),'([^']*)',(\d+),(\d+),([^,]*),'([^']*)'\)"
    app_matches = re.findall(app_pattern, content)
    
    apps = []
    for match in app_matches:
        app_id, disposition_id, name, create_date, admin_id, comments, deleted, querysec, view_basic_query, formtitle = match
        apps.append({
            'app_id': app_id,
            'name': name,
            'create_date': create_date,
            'admin_id': admin_id,
            'comments': comments,
            'formtitle': formtitle
        })
    
    print(f"  找到 {len(apps)} 个APP记录")
    
    return draws, folds, apps

def analyze_relations(draws, folds, apps):
    """分析DRAW、FOLD、APP之间的关系"""
    print("\n🔗 分析关系...")
    
    # DRAW到APP映射
    draw_to_app = {draw['draw_id']: draw['app_id'] for draw in draws}
    
    # APP到DRAW列表
    app_to_draws = defaultdict(list)
    for draw in draws:
        app_to_draws[draw['app_id']].append(draw)
    
    # FOLD到DRAW映射（通过parent_id）
    fold_to_draw = {}
    for fold in folds:
        if fold['parent_id'] in draw_to_app:
            fold_to_draw[fold['fold_id']] = fold['parent_id']
    
    print(f"  FOLD关联到DRAW: {len(fold_to_draw)}/{len(folds)}")
    
    # DRAW到FOLD列表
    draw_to_folds = defaultdict(list)
    for fold in folds:
        if fold['parent_id'] in draw_to_app:
            draw_to_folds[fold['parent_id']].append(fold)
    
    # 统计
    print(f"\n📊 统计信息:")
    print(f"  APP数量: {len(apps)}")
    print(f"  DRAW数量: {len(draws)}")
    print(f"  FOLD数量: {len(folds)}")
    
    print(f"\n📱 每个APP的DRAW数量:")
    for app_id, app_draws in app_to_draws.items():
        app_name = next((app['name'] for app in apps if app['app_id'] == app_id), f"APP {app_id}")
        print(f"  {app_name}: {len(app_draws)}个DRAW")
    
    print(f"\n📂 每个DRAW的FOLD数量:")
    for draw_id, draw_folds in draw_to_folds.items():
        draw_name = next((draw['name'] for draw in draws if draw['draw_id'] == draw_id), f"DRAW {draw_id}")
        print(f"  {draw_name} ({draw_id}): {len(draw_folds)}个FOLD")
    
    # 显示一些示例
    print(f"\n📋 关系示例:")
    for draw_id in list(draw_to_folds.keys())[:5]:
        draw = next(d for d in draws if d['draw_id'] == draw_id)
        app = next(a for a in apps if a['app_id'] == draw['app_id'])
        folds_in_draw = draw_to_folds[draw_id]
        
        print(f"\n  APP: {app['name']} ({app['app_id']})")
        print(f"  DRAW: {draw['name']} ({draw_id})")
        print(f"    包含 {len(folds_in_draw)} 个文件夹:")
        for fold in folds_in_draw[:5]:
            print(f"      - {fold['name']} ({fold['fold_id']})")
        if len(folds_in_draw) > 5:
            print(f"      ... 还有 {len(folds_in_draw)-5} 个")
    
    return draw_to_app, draw_to_folds, app_to_draws

def check_current_mapping(draws, folds, apps):
    """检查当前导入的映射关系"""
    print("\n🔍 检查当前导入映射...")
    
    # 加载现有映射
    with open('smarti_import_mapping.json', 'r') as f:
        mapping = json.load(f)
    
    # 检查DRAW是否被导入（应该没有被导入）
    draw_ids_in_mapping = []
    for key in mapping['mappings'].keys():
        if key == 'draw':
            draw_ids_in_mapping.extend(mapping['mappings'][key].keys())
    
    if draw_ids_in_mapping:
        print(f"  发现 {len(draw_ids_in_mapping)} 个DRAW在映射中")
    else:
        print("  ⚠️  DRAW没有在导入映射中（这是问题的根源）")
    
    # 检查APP映射
    app_mapping = mapping['mappings']['app']
    print(f"\n  APP映射: {len(app_mapping)}个")
    for smarti_app_id, filebot_app_id in app_mapping.items():
        app = next((a for a in apps if a['app_id'] == smarti_app_id), None)
        if app:
            print(f"    {app['name']} ({smarti_app_id}) -> {filebot_app_id}")
    
    return mapping

def generate_fix_plan(draws, folds, apps, draw_to_app, draw_to_folds, mapping):
    """生成修复计划"""
    print("\n🔧 生成修复计划")
    print("=" * 60)
    
    # 获取APP映射
    app_mapping = mapping['mappings']['app']  # Smarti APP_ID -> FileBot app_id
    fold_mapping = mapping['mappings']['fold']  # Smarti FOLD_ID -> FileBot folder_id
    
    print("步骤1: 创建DRAW文件夹")
    print("  - 为每个DRAW在对应APP下创建文件夹")
    print("  - 使用DRAW名称作为文件夹名")
    print(f"  - 需要创建 {len(draws)} 个DRAW文件夹")
    
    print("\n步骤2: 更新FOLD文件夹的parent_folder_id")
    print("  - 将每个FOLD文件夹的parent_folder_id设置为对应DRAW文件夹的ID")
    print(f"  - 需要更新 {len(fold_to_folds)} 个FOLD文件夹")
    
    print("\n步骤3: 更新文件夹路径")
    print("  - 重新计算所有文件夹的path字段")
    print("  - 格式: /app-slug/draw-slug/fold-slug")
    
    print("\n步骤4: 处理重复名称")
    print("  - 为重复的文件夹名称添加后缀（如_Letters_1, _Letters_2）")
    
    print("\n📋 受影响的应用:")
    for app_id, app_draws in draw_to_app.items():
        if app_id in app_mapping:
            app = next((a for a in apps if a['app_id'] == app_id), None)
            if app:
                filebot_app_id = app_mapping[app_id]
                print(f"  - {app['name']}: {len([d for d in draws if d['app_id'] == app_id])}个DRAW, "
                      f"{len([f for f in folds if draw_to_app.get(f['parent_id']) == app_id])}个FOLD")
    
    return {
        'draws_to_create': draws,
        'folds_to_update': folds,
        'app_mapping': app_mapping,
        'fold_mapping': fold_mapping,
        'draw_to_folds': draw_to_folds
    }

def main():
    print("=" * 60)
    print("Smarti层级结构修复分析")
    print("=" * 60)
    
    # 解析原始数据
    draws, folds, apps = parse_inserts()
    
    # 分析关系
    draw_to_app, draw_to_folds, app_to_draws = analyze_relations(draws, folds, apps)
    
    # 检查当前映射
    mapping = check_current_mapping(draws, folds, apps)
    
    # 生成修复计划
    plan = generate_fix_plan(draws, folds, apps, draw_to_app, draw_to_folds, mapping)
    
    print("\n" + "=" * 60)
    print("下一步行动")
    print("=" * 60)
    print("执行修复脚本，将创建DRAW文件夹并更新层级结构")
    print("建议先备份数据库，然后运行修复")

if __name__ == "__main__":
    main()