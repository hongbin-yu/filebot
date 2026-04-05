#!/usr/bin/env python3
"""
创建正确的配置文件 - 基于PO.TXT的精确分析
"""

import json

# 创建正确的配置（基于PO.TXT数据行的精确分析）
correct_config = {
    "app_name": "Purchase Order",
    "app_code": "PO",
    "template_name": "pcl_form.jasper",
    "file_extension": ".cld",
    "encoding": "latin-1",
    "description": "采购订单应用程序配置 - 基于PO.TXT样板文件分析",
    "field_definitions": [
        {
            "name": "record_type",
            "description": "记录类型标记",
            "keywords": ["-"],
            "start_pos": 0,
            "length": 3,
            "field_type": "code",
            "required": True,
            "validation_pattern": "^-$",
            "sample_value": "-"
        },
        {
            "name": "date",
            "description": "日期 (MM/DD/YY)",
            "keywords": ["04/09/12", "05/02/12", "01/26/12", "04/10/12", "05/23/12"],
            "start_pos": 3,
            "length": 12,
            "field_type": "date",
            "required": True,
            "validation_pattern": r"\d{2}/\d{2}/\d{2}",
            "sample_value": "04/09/12"
        },
        {
            "name": "status",
            "description": "状态代码",
            "keywords": ["E", "I", "O"],
            "start_pos": 15,
            "length": 6,
            "field_type": "code",
            "required": True,
            "validation_pattern": "^[EIO]$",
            "sample_value": "E"
        },
        {
            "name": "initials",
            "description": "人员缩写",
            "keywords": ["BD", "DL", "PH", "JM", "WO", "JD"],
            "start_pos": 21,
            "length": 5,
            "field_type": "code",
            "required": True,
            "validation_pattern": "^[A-Z]{2}$",
            "sample_value": "BD"
        },
        {
            "name": "first_name",
            "description": "名",
            "keywords": ["BRIAN", "DANNY", "GARY", "PAUL", "WILLIE", "JOHN"],
            "start_pos": 26,
            "length": 6,
            "field_type": "name",
            "required": True,
            "validation_pattern": "^[A-Z]+$",
            "sample_value": "BRIAN"
        },
        {
            "name": "last_name",
            "description": "姓",
            "keywords": ["DEARB", "LEUNG", "MCKENN", "HOLLMA", "ORTI", "DEUGEN"],
            "start_pos": 32,
            "length": 7,
            "field_type": "name",
            "required": True,
            "validation_pattern": "^[A-Z]+$",
            "sample_value": "DEARB"
        },
        {
            "name": "company_name",
            "description": "公司名称",
            "keywords": ["PARKER HANNIFIN CORPORATION", "PARKER HANNIFIN"],
            "start_pos": 40,
            "length": 40,
            "field_type": "string",
            "required": False,
            "validation_pattern": None,
            "sample_value": "PARKER HANNIFIN CORPORATION"
        },
        {
            "name": "phone",
            "description": "电话号码",
            "keywords": ["(619) 661-7000", "(619) 671-3208"],
            "start_pos": 20,
            "length": 20,
            "field_type": "phone",
            "required": False,
            "validation_pattern": r"\(\d{3}\) \d{3}-\d{4}",
            "sample_value": "(619) 661-7000"
        },
        {
            "name": "fax",
            "description": "传真号码",
            "keywords": ["(619) 671-3208"],
            "start_pos": 20,
            "length": 20,
            "field_type": "phone",
            "required": False,
            "validation_pattern": r"\(\d{3}\) \d{3}-\d{4}",
            "sample_value": "(619) 671-3208"
        },
        {
            "name": "address_line1",
            "description": "地址行1",
            "keywords": ["7664 PANASONIC WAY", "SAN DIEGO, CA 92154"],
            "start_pos": 80,
            "length": 40,
            "field_type": "address",
            "required": False,
            "validation_pattern": None,
            "sample_value": "7664 PANASONIC WAY"
        },
        {
            "name": "address_line2",
            "description": "地址行2",
            "keywords": ["SAN DIEGO, CA 92154"],
            "start_pos": 120,
            "length": 40,
            "field_type": "address",
            "required": False,
            "validation_pattern": None,
            "sample_value": "SAN DIEGO, CA 92154"
        }
    ]
}

# 保存配置文件
with open("correct_po_config.json", "w", encoding="utf-8") as f:
    json.dump(correct_config, f, indent=2, ensure_ascii=False)

print("正确的配置文件已创建: correct_po_config.json")
print(f"包含 {len(correct_config['field_definitions'])} 个字段定义")

# 显示字段摘要
print("\n字段摘要:")
for field in correct_config["field_definitions"]:
    print(f"  {field['name']}: 位置 {field['start_pos']}-{field['start_pos']+field['length']-1}, 类型 {field['field_type']}")
    if field.get('sample_value'):
        print(f"    样本: {field['sample_value']}")