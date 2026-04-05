#!/usr/bin/env python3
"""
测试AI集成功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai.ai_classifier import AIClassifier, AICategory

def test_ai_classifier():
    """测试AI分类器"""
    print("🧪 测试AI分类器集成...")
    
    # 创建分类器实例
    classifier = AIClassifier()
    
    # 测试连接
    print("1. 测试Ollama连接...")
    if not classifier.test_connection():
        print("❌ 无法连接到Ollama服务")
        return False
    print("✅ Ollama连接正常")
    
    # 测试文本分类
    print("\n2. 测试文本分类...")
    test_texts = [
        {
            "name": "合同文档",
            "text": """采购合同
甲方：某某科技有限公司
乙方：某某软件有限公司
根据《中华人民共和国合同法》及相关法律法规，甲乙双方经友好协商，就软件采购事宜达成如下协议：
一、采购内容
1. 企业文档管理系统一套
2. 包含一年的技术支持和维护服务
3. 总金额：人民币50,000元（大写：伍万元整）
二、付款方式
1. 合同签订后7个工作日内支付30%
2. 系统交付验收合格后支付60%
3. 一年维护期结束后支付10%
三、交付时间
乙方应在合同签订后30个工作日内完成系统交付。"""
        },
        {
            "name": "发票文档", 
            "text": """增值税专用发票
发票代码：123456789012
发票号码：87654321
开票日期：2026年3月19日
购方名称：某某科技有限公司
购方税号：123456789012345
货物或应税劳务名称：企业文档管理系统软件
金额：44,247.79
税率：13%
税额：5,752.21
价税合计：50,000.00
大写：伍万元整"""
        },
        {
            "name": "工作报告",
            "text": """2026年第一季度技术部工作总结报告
一、工作完成情况
1. 完成了FileBot文档管理系统的开发工作，系统已上线运行
2. 实现了多格式文档转换功能，支持TIFF、PDF、Word等格式
3. 开发了智能搜索功能，提升了文档检索效率
4. 完成了系统性能优化，响应时间提升了30%"""
        }
    ]
    
    for test in test_texts:
        print(f"\n   测试: {test['name']}")
        print(f"   文本长度: {len(test['text'])}字符")
        
        result = classifier.classify_text(test['text'])
        
        if result["success"]:
            print(f"   ✅ 分类结果: {result['category'].value}")
            print(f"   文档类型: {result['document_type']}")
            print(f"   置信度: {result['confidence']:.2f}")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   模型: {result['model']}")
        else:
            print(f"   ❌ 分类失败: {result.get('error', '未知错误')}")
    
    return True

def test_api_endpoints():
    """测试API端点（如果服务运行）"""
    print("\n3. 测试API端点（可选）...")
    
    try:
        import requests
        
        # 测试健康检查
        response = requests.get("http://localhost:8001/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ FileBot后端服务运行正常")
            
            # 测试AI连接端点
            ai_response = requests.get("http://localhost:8001/api/ai/test-connection", timeout=5)
            if ai_response.status_code == 200:
                print("✅ AI端点可访问")
                print(f"   AI服务状态: {ai_response.json()}")
            else:
                print(f"⚠️  AI端点不可用: HTTP {ai_response.status_code}")
                print("   可能需要重启后端服务以加载AI模块")
        else:
            print(f"⚠️  FileBot后端服务异常: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  API测试跳过: {e}")

def main():
    """主测试函数"""
    print("=" * 60)
    print("FileBot AI集成测试")
    print("=" * 60)
    
    # 测试分类器
    if not test_ai_classifier():
        print("\n❌ AI分类器测试失败")
        return
    
    # 测试API端点
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n🎯 下一步:")
    print("1. 重启FileBot后端服务以加载AI模块")
    print("2. 运行数据库迁移添加AI字段")
    print("3. 测试文档上传后的自动AI分类")
    print("4. 在前端添加AI分类结果显示")

if __name__ == "__main__":
    main()