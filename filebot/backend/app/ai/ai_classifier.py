"""
AI文档分类器服务
使用本地Ollama模型进行文档分类
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
import time
from sqlalchemy.orm import Session

from ..models.document import Document, DocumentType

logger = logging.getLogger(__name__)

class AICategory(str, Enum):
    """AI分类类别枚举"""
    CONTRACT = "CONTRACT"
    INVOICE = "INVOICE" 
    REPORT = "REPORT"
    RESUME = "RESUME"
    TECH = "TECH"
    ADMIN = "ADMIN"
    GENERAL = "GENERAL"
    
    # 映射到现有DocumentType
    def to_document_type(self) -> DocumentType:
        """转换为现有的DocumentType枚举"""
        mapping = {
            AICategory.CONTRACT: DocumentType.CONTRACT,
            AICategory.INVOICE: DocumentType.INVOICE,
            AICategory.REPORT: DocumentType.REPORT,
            AICategory.RESUME: DocumentType.OTHER,
            AICategory.TECH: DocumentType.OTHER,
            AICategory.ADMIN: DocumentType.OTHER,
            AICategory.GENERAL: DocumentType.GENERAL
        }
        return mapping.get(self, DocumentType.GENERAL)

class AIClassifier:
    """AI文档分类器"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "llama3.1:latest"):
        self.ollama_url = ollama_url
        self.default_model = default_model
        
    def test_connection(self) -> bool:
        """测试Ollama连接"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.info(f"Ollama连接正常，可用模型: {len(models)}个")
                return True
            else:
                logger.error(f"Ollama连接失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Ollama连接异常: {e}")
            return False
    
    def _get_available_models(self) -> List[str]:
        """获取Ollama可用的模型列表"""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
        except Exception as e:
            logger.warning(f"获取Ollama模型列表失败: {e}")
        return []

    def _find_available_model(self, preferred: str) -> str:
        """查找可用的模型，优先使用preferred"""
        available = self._get_available_models()
        if not available:
            logger.warning("Ollama无可用模型，返回preferred")
            return preferred
        if preferred in available:
            return preferred
        # 回退到第一个可用的模型
        logger.warning(f"模型 {preferred} 不可用，可用列表: {available[:5]}, 使用: {available[0]}")
        return available[0]

    def classify_text(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        分类文档文本
        
        Args:
            text: 文档文本内容
            model: Ollama模型名称，默认为self.default_model
            
        Returns:
            包含分类结果的字典
        """
        model = model or self.default_model
        
        # 构建分类提示
        prompt = self._build_classification_prompt(text)
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 200  # 提高最大token数确保完整响应
            }
        }
        
        try:
            start_time = time.time()
            response = requests.post(f"{self.ollama_url}/api/generate", json=data, timeout=120)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()
                
                # Bug 3 修复：处理空响应
                if not response_text:
                    logger.warning(f"Ollama返回空响应 (model={model}), 尝试切换可用模型后重试...")
                    alt_model = self._find_available_model(model)
                    if alt_model != model:
                        # 有可用模型，用替代模型重试
                        data["model"] = alt_model
                        retry_start = time.time()
                        try:
                            retry_resp = requests.post(f"{self.ollama_url}/api/generate", json=data, timeout=120)
                            if retry_resp.status_code == 200:
                                retry_result = retry_resp.json()
                                response_text = retry_result.get("response", "").strip()
                                if response_text:
                                    model = alt_model
                                    end_time = time.time()
                        except Exception as retry_err:
                            logger.error(f"重试分类失败: {retry_err}")
                    
                    if not response_text:
                        logger.error(f"Ollama分类返回空内容 (model={model}), 原始结果: {result}")
                        return {
                            "category": AICategory.GENERAL,
                            "ai_category": AICategory.GENERAL.value,
                            "document_type": DocumentType.GENERAL.value,
                            "confidence": 0.0,
                            "raw_response": "",
                            "processing_time": end_time - start_time,
                            "model": model,
                            "error": "Ollama returned empty content",
                            "success": False
                        }
                
                # 解析分类结果
                category = self._parse_category(response_text)
                confidence = self._calculate_confidence(response_text, category)
                
                return {
                    "category": category,
                    "ai_category": category.value,
                    "document_type": category.to_document_type().value,
                    "confidence": confidence,
                    "raw_response": response_text,
                    "processing_time": end_time - start_time,
                    "model": model,
                    "success": True
                }
            elif response.status_code == 404:
                # 模型不存在 - 尝试自动切换可用模型
                logger.warning(f"模型 {model} 不存在 (HTTP 404), 尝试自动切换...")
                alt_model = self._find_available_model(model)
                if alt_model != model:
                    data["model"] = alt_model
                    try:
                        retry_resp = requests.post(f"{self.ollama_url}/api/generate", json=data, timeout=120)
                        if retry_resp.status_code == 200:
                            # 递归调用自身但使用新模型
                            return self.classify_text(text, model=alt_model)
                    except Exception:
                        pass
                return {
                    "category": AICategory.GENERAL,
                    "ai_category": AICategory.GENERAL.value,
                    "document_type": DocumentType.GENERAL.value,
                    "confidence": 0.0,
                    "error": f"HTTP {response.status_code}: Model '{model}' not found. Available: {self._get_available_models()}",
                    "success": False
                }
            else:
                logger.error(f"分类请求失败: HTTP {response.status_code}, 响应: {response.text}")
                return {
                    "category": AICategory.GENERAL,
                    "ai_category": AICategory.GENERAL.value,
                    "document_type": DocumentType.GENERAL.value,
                    "confidence": 0.0,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "success": False
                }
                
        except Exception as e:
            logger.error(f"分类异常: {e}")
            return {
                "category": AICategory.GENERAL,
                "ai_category": AICategory.GENERAL.value,
                "document_type": DocumentType.GENERAL.value,
                "confidence": 0.0,
                "error": str(e),
                "success": False
            }
    
    def classify_document(self, document: Document, db: Session, extract_text: bool = True) -> Dict[str, Any]:
        """
        分类文档对象
        
        Args:
            document: 文档对象
            db: 数据库会话
            extract_text: 是否从文档文件提取文本
            
        Returns:
            分类结果
        """
        # TODO: 从文档文件提取文本内容
        # 目前先使用文档描述或标题作为文本
        text_content = document.description or document.title or ""
        
        if not text_content and extract_text:
            # 未来可以从转换后的PDF提取文本
            logger.warning(f"文档 {document.path} 无文本内容，无法进行AI分类")
            return {
                "category": AICategory.GENERAL,
                "ai_category": AICategory.GENERAL.value,
                "document_type": DocumentType.GENERAL.value,
                "confidence": 0.0,
                "error": "文档无文本内容",
                "success": False
            }
        
        # 进行分类
        result = self.classify_text(text_content)
        
        # 更新文档的AI字段（如果需要）
        if result["success"]:
            self._update_document_ai_fields(document, db, result)
        
        return result
    
    def _build_classification_prompt(self, text: str) -> str:
        """构建分类提示"""
        # 截断文本以避免过长
        truncated_text = text[:2000] + "..." if len(text) > 2000 else text
        
        return f"""请分析以下文档内容，并将其分类为以下类别之一：
1. 合同 (CONTRACT) - 法律协议、合同、协议文件
2. 发票 (INVOICE) - 账单、收据、付款通知
3. 报告 (REPORT) - 工作报告、分析报告、研究文档
4. 简历 (RESUME) - 个人简历、履历表
5. 技术文档 (TECH) - 技术说明、API文档、开发文档
6. 行政文档 (ADMIN) - 行政通知、内部备忘录
7. 通用文档 (GENERAL) - 其他类型的文档

文档内容：
{truncated_text}

请只返回分类类别（英文大写），不要包含其他文字。例如：INVOICE 或 CONTRACT 或 REPORT"""
    
    def _parse_category(self, response_text: str) -> AICategory:
        """从响应文本解析分类类别"""
        response_text = response_text.upper()
        
        # 检查每个类别是否出现在响应中
        for category in AICategory:
            if category.value in response_text:
                return category
        
        # 如果没有匹配，使用GENERAL
        return AICategory.GENERAL
    
    def _calculate_confidence(self, response_text: str, category: AICategory) -> float:
        """
        计算分类置信度（简化版本）
        
        实际应用中可以使用更复杂的方法，如：
        1. 分析响应文本的确定性
        2. 使用模型输出的概率
        3. 基于响应格式的评分
        """
        response_text = response_text.upper()
        category_str = category.value
        
        # 简单的置信度计算
        if category_str in response_text and len(response_text) < 20:
            # 如果响应简短且包含分类，置信度较高
            return 0.85
        elif category_str in response_text:
            # 包含分类但可能有其他文字
            return 0.75
        else:
            # 使用默认分类
            return 0.5
    
    def _update_document_ai_fields(self, document: Document, db: Session, ai_result: Dict[str, Any]):
        """
        更新文档的AI相关字段
        
        注意：需要先在Document模型中添加AI字段
        """
        # 检查文档是否有AI字段（需要先修改模型）
        try:
            # 临时方案：记录到日志，实际更新需要模型修改
            logger.info(f"文档 {document.path} AI分类结果: {ai_result}")
            
            # TODO: 更新文档的AI字段
            # document.ai_category = ai_result['ai_category']
            # document.ai_confidence = ai_result['confidence']
            # document.ai_tags = self._extract_tags(ai_result['raw_response'])
            # db.commit()
            
        except Exception as e:
            logger.error(f"更新文档AI字段失败: {e}")

# 全局分类器实例
classifier = AIClassifier()