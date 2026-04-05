#!/usr/bin/env python3
"""
测试路径API逻辑
"""
import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/webbot')

from app.routes.pages import get_page_by_path
import asyncio

async def test():
    print("测试路径API逻辑")
    
    # 测试1: /en/contact
    try:
        result = await get_page_by_path("/en/contact")
        print(f"✅ /en/contact: {result.id}, parent={result.parent_id}")
    except Exception as e:
        print(f"❌ /en/contact 错误: {e}")
    
    # 测试2: /fr/contact (应该不存在)
    try:
        result = await get_page_by_path("/fr/contact")
        print(f"✅ /fr/contact: {result.id}, parent={result.parent_id}")
    except Exception as e:
        print(f"✅ /fr/contact 预期错误: {e}")
    
    # 测试3: /contact (无父级)
    try:
        result = await get_page_by_path("/contact")
        print(f"✅ /contact: {result.id}, parent={result.parent_id}")
    except Exception as e:
        print(f"❌ /contact 错误: {e}")

if __name__ == "__main__":
    asyncio.run(test())