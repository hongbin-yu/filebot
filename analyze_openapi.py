#!/usr/bin/env python3
"""
分析FileBot OpenAPI文档
"""

import json
import requests
import sys

def fetch_openapi():
    """获取OpenAPI JSON"""
    url = "http://localhost:8000/api/openapi.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 获取OpenAPI失败: {e}")
        sys.exit(1)

def analyze_openapi(data):
    """分析OpenAPI数据"""
    print("📚 FileBot API 文档分析\n")
    
    # 基本信息
    info = data.get("info", {})
    print(f"🔹 API名称: {info.get('title', '未知')}")
    print(f"🔹 描述: {info.get('description', '无描述')}")
    print(f"🔹 版本: {info.get('version', '未知')}")
    print(f"🔹 OpenAPI版本: {data.get('openapi', '未知')}")
    print()
    
    # 统计端点
    paths = data.get("paths", {})
    print(f"📊 端点统计: {len(paths)} 个端点")
    
    # 按标签分组
    endpoints_by_tag = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            tags = details.get("tags", ["未分类"])
            for tag in tags:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append({
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", "无标题"),
                    "description": details.get("description", "")
                })
    
    # 显示各模块
    print("\n🔧 主要功能模块:")
    for tag in sorted(endpoints_by_tag.keys()):
        count = len(endpoints_by_tag[tag])
        print(f"  ✅ {tag}: {count} 个端点")
    
    # 详细端点信息
    print("\n📋 关键端点:")
    
    # 认证模块
    auth_endpoints = endpoints_by_tag.get("认证", [])
    print("\n🔐 认证模块:")
    for ep in auth_endpoints:
        if ep["path"] in ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/me"]:
            print(f"  {ep['method']:6} {ep['path']:40} - {ep['summary']}")
    
    # 应用模块
    app_endpoints = endpoints_by_tag.get("应用", [])
    print("\n📦 应用模块:")
    for ep in app_endpoints[:5]:  # 显示前5个
        print(f"  {ep['method']:6} {ep['path']:40} - {ep['summary']}")
    if len(app_endpoints) > 5:
        print(f"  ... 还有 {len(app_endpoints)-5} 个端点")
    
    # 文档模块
    doc_endpoints = endpoints_by_tag.get("文档", [])
    print("\n📄 文档模块:")
    for ep in doc_endpoints[:5]:
        print(f"  {ep['method']:6} {ep['path']:40} - {ep['summary']}")
    if len(doc_endpoints) > 5:
        print(f"  ... 还有 {len(doc_endpoints)-5} 个端点")
    
    # 搜索模块
    search_endpoints = endpoints_by_tag.get("搜索", [])
    print("\n🔍 搜索模块:")
    for ep in search_endpoints:
        print(f"  {ep['method']:6} {ep['path']:40} - {ep['summary']}")
    
    # 转换模块
    conversion_endpoints = endpoints_by_tag.get("转换", [])
    print("\n⚙️  转换模块:")
    for ep in conversion_endpoints[:3]:
        print(f"  {ep['method']:6} {ep['path']:40} - {ep['summary']}")
    if len(conversion_endpoints) > 3:
        print(f"  ... 还有 {len(conversion_endpoints)-3} 个端点")
    
    # 模型统计
    schemas = data.get("components", {}).get("schemas", {})
    print(f"\n📁 数据模型: {len(schemas)} 个")
    
    # 显示重要模型
    important_schemas = ["UserCreate", "UserResponse", "AppCreate", "AppResponse", 
                         "DocumentResponse", "ConversionTaskResponse", "Token"]
    print("📊 关键数据模型:")
    for schema in important_schemas:
        if schema in schemas:
            desc = schemas[schema].get("description", "无描述")
            print(f"  ✅ {schema:25} - {desc[:50]}...")
    
    return endpoints_by_tag

def generate_access_instructions():
    """生成访问说明"""
    print("\n" + "="*60)
    print("🌐 API 访问说明")
    print("="*60)
    
    print("\n🔗 直接访问:")
    print(f"  1. Swagger UI: http://localhost:8000/api/docs")
    print(f"  2. OpenAPI JSON: http://localhost:8000/api/openapi.json")
    print(f"  3. 健康检查: http://localhost:8000/api/health")
    
    print("\n🔐 认证信息:")
    print(f"  用户名: admin")
    print(f"  密码: FileBot2026!")
    
    print("\n📝 登录示例 (curl):")
    print("""  curl -X POST http://localhost:8000/api/v1/auth/login \\
    -d "username=admin&password=FileBot2026!" """)
    
    print("\n🔧 常用操作:")
    print("  1. 获取应用列表: GET /api/v1/apps/")
    print("  2. 获取文档列表: GET /api/v1/documents/")
    print("  3. 上传文档: POST /api/v1/documents/upload/")
    print("  4. 搜索文档: GET /api/v1/search/documents")
    
    print("\n💡 提示:")
    print("  - 所有API都需要Bearer Token认证（登录后获取）")
    print("  - 应用ID: 28516d7d-e499-4be4-b150-7d69ab742055")
    print("  - 可在Swagger UI中直接测试API")

def main():
    """主函数"""
    print("正在分析FileBot API文档...")
    
    # 获取OpenAPI数据
    data = fetch_openapi()
    
    # 分析数据
    endpoints_by_tag = analyze_openapi(data)
    
    # 生成访问说明
    generate_access_instructions()
    
    # 保存到文件
    with open("/home/hongb/.openclaw/workspace/filebot_api_summary.txt", "w") as f:
        f.write("FileBot API 文档总结\n")
        f.write("="*50 + "\n\n")
        for tag, endpoints in endpoints_by_tag.items():
            f.write(f"{tag} ({len(endpoints)}个端点):\n")
            for ep in endpoints:
                f.write(f"  {ep['method']} {ep['path']} - {ep['summary']}\n")
            f.write("\n")
    
    print(f"\n✅ 详细端点列表已保存到: filebot_api_summary.txt")

if __name__ == "__main__":
    main()