"""
特性标志服务
用于管理AI功能开关，支持不同版本（AI版 vs 基础版）
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class FeatureFlag(Enum):
    """特性标志枚举"""
    AI_DOCUMENT_CLASSIFICATION = "ai_document_classification"  # AI文档分类
    AI_SEMANTIC_SEARCH = "ai_semantic_search"  # AI语义搜索
    AI_DOCUMENT_SUMMARY = "ai_document_summary"  # AI文档摘要
    AI_INTELLIGENT_TAGGING = "ai_intelligent_tagging"  # AI智能标签
    AI_WORKFLOW_AUTOMATION = "ai_workflow_automation"  # AI工作流自动化

class Edition(Enum):
    """产品版本枚举"""
    BASIC = "basic"  # 基础版（无AI功能）
    PROFESSIONAL = "professional"  # 专业版（含AI功能）
    ENTERPRISE = "enterprise"  # 企业版（全功能）

class FeatureService:
    """特性服务"""
    
    def __init__(self):
        # 版本特性映射
        self.edition_features = {
            Edition.BASIC: [],  # 基础版无AI功能
            Edition.PROFESSIONAL: [
                FeatureFlag.AI_DOCUMENT_CLASSIFICATION,
                FeatureFlag.AI_SEMANTIC_SEARCH,
                FeatureFlag.AI_INTELLIGENT_TAGGING
            ],
            Edition.ENTERPRISE: [
                FeatureFlag.AI_DOCUMENT_CLASSIFICATION,
                FeatureFlag.AI_SEMANTIC_SEARCH,
                FeatureFlag.AI_DOCUMENT_SUMMARY,
                FeatureFlag.AI_INTELLIGENT_TAGGING,
                FeatureFlag.AI_WORKFLOW_AUTOMATION
            ]
        }
        
        # 默认版本（可根据配置文件或数据库设置）
        self.default_edition = Edition.PROFESSIONAL
        
        # 特性状态缓存
        self.feature_cache: Dict[str, bool] = {}
    
    def is_feature_enabled(
        self, 
        feature: FeatureFlag, 
        edition: Optional[Edition] = None
    ) -> bool:
        """
        检查特性是否启用
        
        Args:
            feature: 特性标志
            edition: 产品版本，如果为None则使用默认版本
            
        Returns:
            是否启用
        """
        if edition is None:
            edition = self.default_edition
        
        # 检查版本是否支持该特性
        enabled_features = self.edition_features.get(edition, [])
        return feature in enabled_features
    
    def get_edition_features(self, edition: Edition) -> Dict[str, bool]:
        """
        获取指定版本的所有特性状态
        
        Args:
            edition: 产品版本
            
        Returns:
            特性状态字典
        """
        enabled_features = self.edition_features.get(edition, [])
        return {
            feature.value: feature in enabled_features
            for feature in FeatureFlag
        }
    
    def set_edition(self, edition: Edition):
        """
        设置当前产品版本
        
        Args:
            edition: 产品版本
        """
        if edition not in Edition:
            logger.warning(f"未知版本: {edition}")
            return
        
        self.default_edition = edition
        logger.info(f"产品版本已设置为: {edition.value}")
    
    def get_current_edition(self) -> Edition:
        """
        获取当前产品版本
        
        Returns:
            当前产品版本
        """
        return self.default_edition
    
    def get_feature_status(self, feature: FeatureFlag) -> Dict[str, Any]:
        """
        获取特性状态信息
        
        Args:
            feature: 特性标志
            
        Returns:
            特性状态信息
        """
        is_enabled = self.is_feature_enabled(feature)
        
        return {
            "feature": feature.value,
            "enabled": is_enabled,
            "edition": self.default_edition.value,
            "description": self.get_feature_description(feature)
        }
    
    @staticmethod
    def get_feature_description(feature: FeatureFlag) -> str:
        """
        获取特性描述
        
        Args:
            feature: 特性标志
            
        Returns:
            特性描述
        """
        descriptions = {
            FeatureFlag.AI_DOCUMENT_CLASSIFICATION: "AI文档自动分类，支持发票、合同、报告等7种文档类型",
            FeatureFlag.AI_SEMANTIC_SEARCH: "语义搜索，理解用户意图而非关键词匹配",
            FeatureFlag.AI_DOCUMENT_SUMMARY: "长文档智能摘要，快速了解文档核心内容",
            FeatureFlag.AI_INTELLIGENT_TAGGING: "智能标签生成，自动提取文档关键词和主题",
            FeatureFlag.AI_WORKFLOW_AUTOMATION: "AI工作流自动化，智能文档路由和审批"
        }
        return descriptions.get(feature, "未描述的特性")
    
    def get_all_features_status(self) -> Dict[str, Any]:
        """
        获取所有特性状态
        
        Returns:
            所有特性状态信息
        """
        return {
            "edition": self.default_edition.value,
            "features": {
                feature.value: self.get_feature_status(feature)
                for feature in FeatureFlag
            }
        }
    
    def validate_edition(self, edition_str: str) -> Optional[Edition]:
        """
        验证并转换版本字符串
        
        Args:
            edition_str: 版本字符串
            
        Returns:
            版本枚举或None
        """
        try:
            return Edition(edition_str.lower())
        except ValueError:
            logger.warning(f"无效的版本字符串: {edition_str}")
            return None

# 全局特性服务实例
feature_service = FeatureService()