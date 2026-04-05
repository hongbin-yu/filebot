#!/usr/bin/env python3
"""
测试Ollama文档分类功能
"""

import requests
import json
import time

OLLAMA_URL = "http://localhost:11434"

def test_ollama_connection():
    """测试Ollama连接"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama连接正常，可用模型: {len(models)}个")
            for model in models:
                print(f"  - {model['name']} ({model.get('details', {}).get('parameter_size', '未知大小')})")
            return True
        else:
            print(f"❌ Ollama连接失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama连接异常: {e}")
        return False

def classify_document_text(text, model="llama3.1:latest"):
    """使用Ollama分类文档文本"""
    prompt = f"""请分析以下文档内容，并将其分类为以下类别之一：
1. 合同 (CONTRACT) - 法律协议、合同、协议文件
2. 发票 (INVOICE) - 账单、收据、付款通知
3. 报告 (REPORT) - 工作报告、分析报告、研究文档
4. 简历 (RESUME) - 个人简历、履历表
5. 技术文档 (TECH) - 技术说明、API文档、开发文档
6. 行政文档 (ADMIN) - 行政通知、内部备忘录
7. 通用文档 (GENERAL) - 其他类型的文档

文档内容：
{text[:1000]}...

请只返回分类类别（英文大写），不要包含其他文字。例如：INVOICE 或 CONTRACT 或 REPORT"""

    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": 50
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=data)
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            # 提取分类结果
            categories = ["CONTRACT", "INVOICE", "REPORT", "RESUME", "TECH", "ADMIN", "GENERAL"]
            for category in categories:
                if category in response_text:
                    return {
                        "category": category,
                        "raw_response": response_text,
                        "confidence": 0.8,  # 暂时使用固定值，后续可以计算置信度
                        "processing_time": end_time - start_time,
                        "model": model
                    }
            
            # 如果没有匹配到已知分类，使用GENERAL
            return {
                "category": "GENERAL",
                "raw_response": response_text,
                "confidence": 0.5,
                "processing_time": end_time - start_time,
                "model": model
            }
        else:
            print(f"❌ 分类请求失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 分类异常: {e}")
        return None

def test_classification():
    """测试分类功能"""
    test_cases = [
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
乙方应在合同签订后30个工作日内完成系统交付。
四、违约责任
任何一方违反本合同约定，应承担违约责任，赔偿对方因此造成的损失。
五、争议解决
本合同履行过程中如发生争议，双方应协商解决；协商不成的，提交甲方所在地人民法院诉讼解决。
本合同一式两份，甲乙双方各执一份，具有同等法律效力。
甲方（盖章）：某某科技有限公司
代表签字：张三
日期：2026年3月20日
乙方（盖章）：某某软件有限公司
代表签字：李四
日期：2026年3月20日"""
        },
        {
            "name": "发票文档",
            "text": """增值税专用发票
发票代码：123456789012
发票号码：87654321
开票日期：2026年3月19日
购方名称：某某科技有限公司
购方税号：123456789012345
购方地址电话：北京市朝阳区xxx路123号 010-12345678
购方开户行及账号：工商银行xxx支行 6222021234567890123
密码区：********************
货物或应税劳务名称：企业文档管理系统软件
规格型号：V2.0
单位：套
数量：1
单价：44,247.79
金额：44,247.79
税率：13%
税额：5,752.21
价税合计：50,000.00
大写：伍万元整
销方名称：某某软件有限公司
销方税号：987654321098765
销方地址电话：上海市浦东新区xxx路456号 021-87654321
销方开户行及账号：建设银行xxx支行 6222089876543210987
收款人：王五
复核：赵六
开票人：钱七"""
        },
        {
            "name": "工作报告",
            "text": """2026年第一季度技术部工作总结报告
一、工作完成情况
1. 完成了FileBot文档管理系统的开发工作，系统已上线运行
2. 实现了多格式文档转换功能，支持TIFF、PDF、Word等格式
3. 开发了智能搜索功能，提升了文档检索效率
4. 完成了系统性能优化，响应时间提升了30%
二、存在问题
1. 部分旧格式文档转换兼容性有待提高
2. 用户界面需要进一步优化
3. 系统文档需要完善
三、下一步工作计划
1. 开发AI文档分类功能，计划4月底完成
2. 优化移动端适配
3. 完善API接口文档
4. 开展用户培训工作
报告人：技术部 张三
日期：2026年3月20日"""
        }
    ]
    
    print("🧪 开始测试Ollama文档分类功能...")
    
    # 测试连接
    if not test_ollama_connection():
        print("❌ 无法连接到Ollama，请确保服务正在运行")
        return
    
    print("\n📄 测试文档分类:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试: {test_case['name']}")
        print(f"   内容长度: {len(test_case['text'])}字符")
        
        result = classify_document_text(test_case['text'])
        
        if result:
            print(f"   ✅ 分类结果: {result['category']}")
            print(f"   置信度: {result['confidence']:.2f}")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   原始响应: {result['raw_response'][:100]}...")
        else:
            print(f"   ❌ 分类失败")

if __name__ == "__main__":
    test_classification()