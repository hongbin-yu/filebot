"""
特性标志API路由
提供版本管理和特性开关功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.feature_service import (
    FeatureService, FeatureFlag, Edition, feature_service
)

router = APIRouter()


# 请求/响应模型
class EditionRequest(BaseModel):
    """版本请求模型"""
    edition: str = Field(..., description="产品版本 (basic/professional/enterprise)")


class FeatureStatusResponse(BaseModel):
    """特性状态响应模型"""
    feature: str
    enabled: bool
    edition: str
    description: str


class AllFeaturesResponse(BaseModel):
    """所有特性响应模型"""
    edition: str
    features: Dict[str, FeatureStatusResponse]


@router.get("/status", response_model=FeatureStatusResponse)
async def get_feature_status(
    feature: str,
    edition: Optional[str] = None
):
    """
    获取特定特性状态
    
    Args:
        feature: 特性名称
        edition: 可选版本，不指定则使用当前版本
    
    Returns:
        特性状态
    """
    try:
        feature_flag = FeatureFlag(feature)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的特性名称: {feature}"
        )
    
    # 如果指定了版本，检查其有效性
    edition_enum = None
    if edition:
        edition_enum = feature_service.validate_edition(edition)
        if not edition_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的版本: {edition}"
            )
    
    status_info = feature_service.get_feature_status(feature_flag)
    return status_info


@router.get("/all", response_model=AllFeaturesResponse)
async def get_all_features_status(
    edition: Optional[str] = None
):
    """
    获取所有特性状态
    
    Args:
        edition: 可选版本，不指定则使用当前版本
    
    Returns:
        所有特性状态
    """
    # 如果指定了版本，临时设置
    original_edition = None
    if edition:
        original_edition = feature_service.get_current_edition()
        edition_enum = feature_service.validate_edition(edition)
        if not edition_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的版本: {edition}"
            )
        feature_service.set_edition(edition_enum)
    
    try:
        all_features = feature_service.get_all_features_status()
        return all_features
    finally:
        # 恢复原始版本
        if original_edition:
            feature_service.set_edition(original_edition)


@router.post("/edition")
async def set_edition(request: EditionRequest):
    """
    设置产品版本
    
    Args:
        request: 版本请求
    
    Returns:
        设置结果
    """
    edition = feature_service.validate_edition(request.edition)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的版本: {request.edition}"
        )
    
    feature_service.set_edition(edition)
    
    return {
        "message": "版本设置成功",
        "edition": edition.value,
        "features": feature_service.get_edition_features(edition)
    }


@router.get("/current-edition")
async def get_current_edition():
    """
    获取当前产品版本
    
    Returns:
        当前版本信息
    """
    edition = feature_service.get_current_edition()
    features = feature_service.get_edition_features(edition)
    
    return {
        "edition": edition.value,
        "description": get_edition_description(edition),
        "features": features
    }


def get_edition_description(edition: Edition) -> str:
    """
    获取版本描述
    
    Args:
        edition: 产品版本
    
    Returns:
        版本描述
    """
    descriptions = {
        Edition.BASIC: "基础版 - 无AI功能，适合预算有限的用户",
        Edition.PROFESSIONAL: "专业版 - 包含核心AI功能，性价比最高",
        Edition.ENTERPRISE: "企业版 - 全功能，适合大型企业"
    }
    return descriptions.get(edition, "未知版本")


@router.get("/editions")
async def get_available_editions():
    """
    获取所有可用版本
    
    Returns:
        可用版本列表
    """
    editions = []
    for edition in Edition:
        features = feature_service.get_edition_features(edition)
        editions.append({
            "name": edition.value,
            "description": get_edition_description(edition),
            "feature_count": len([f for f, enabled in features.items() if enabled]),
            "features": features
        })
    
    return {
        "editions": editions,
        "default": feature_service.get_current_edition().value
    }


@router.get("/check")
async def check_feature(
    feature: str,
    edition: Optional[str] = None
):
    """
    快速检查特性是否可用
    
    Args:
        feature: 特性名称
        edition: 可选版本
    
    Returns:
        检查结果
    """
    try:
        feature_flag = FeatureFlag(feature)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的特性名称: {feature}"
        )
    
    # 如果指定了版本，检查其有效性
    edition_enum = None
    if edition:
        edition_enum = feature_service.validate_edition(edition)
        if not edition_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的版本: {edition}"
            )
    
    is_enabled = feature_service.is_feature_enabled(feature_flag, edition_enum)
    
    return {
        "feature": feature,
        "enabled": is_enabled,
        "edition": edition_enum.value if edition_enum else feature_service.get_current_edition().value
    }