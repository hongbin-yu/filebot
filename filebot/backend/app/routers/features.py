"""
Feature flag API routes
Provides version management and feature toggle functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.feature_service import (
    FeatureService, FeatureFlag, Edition, feature_service
)

router = APIRouter()


# Request/Response models
class EditionRequest(BaseModel):
    """Edition request model"""
    edition: str = Field(..., description="Product edition (basic/professional/enterprise)")


class FeatureStatusResponse(BaseModel):
    """Feature status response model"""
    feature: str
    enabled: bool
    edition: str
    description: str


class AllFeaturesResponse(BaseModel):
    """All features response model"""
    edition: str
    features: Dict[str, FeatureStatusResponse]


@router.get("/status", response_model=FeatureStatusResponse)
async def get_feature_status(
    feature: str,
    edition: Optional[str] = None
):
    """
    Get feature status for a specific feature
    
    Args:
        feature: Feature name
        edition: Optional edition, uses current edition if not specified
    
    Returns:
        Feature status
    """
    try:
        feature_flag = FeatureFlag(feature)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feature name: {feature}"
        )
    
    # If edition specified, validate it
    edition_enum = None
    if edition:
        edition_enum = feature_service.validate_edition(edition)
        if not edition_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid edition: {edition}"
            )
    
    status_info = feature_service.get_feature_status(feature_flag)
    return status_info


@router.get("/all", response_model=AllFeaturesResponse)
async def get_all_features_status(
    edition: Optional[str] = None
):
    """
    Get status of all features
    
    Args:
        edition: Optional edition, uses current edition if not specified
    
    Returns:
        All features status
    """
    # If edition specified, temporarily set it
    original_edition = None
    if edition:
        original_edition = feature_service.get_current_edition()
        edition_enum = feature_service.validate_edition(edition)
        if not edition_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid edition: {edition}"
            )
        feature_service.set_edition(edition_enum)
    
    try:
        all_features = feature_service.get_all_features_status()
        return all_features
    finally:
        # Restore original edition
        if original_edition:
            feature_service.set_edition(original_edition)


@router.post("/edition")
async def set_edition(request: EditionRequest):
    """
    Set product edition
    
    Args:
        request: Edition request
    
    Returns:
        Setting result
    """
    edition = feature_service.validate_edition(request.edition)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid edition: {request.edition}"
        )
    
    feature_service.set_edition(edition)
    
    return {
        "message": "Edition set successfully",
        "edition": edition.value,
        "features": feature_service.get_edition_features(edition)
    }


@router.get("/current-edition")
async def get_current_edition():
    """
    Get current product edition
    
    Returns:
        Current edition info
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
    Get edition description
    
    Args:
        edition: Product edition
    
    Returns:
        Edition description
    """
    descriptions = {
        Edition.BASIC: "Basic - No AI features, suitable for budget-conscious users",
        Edition.PROFESSIONAL: "Professional - Core AI features, best value",
        Edition.ENTERPRISE: "Enterprise - Full features, suitable for large organizations"
    }
    return descriptions.get(edition, "Unknown edition")


@router.get("/editions")
async def get_available_editions():
    """
    Get all available editions
    
    Returns:
        List of available editions
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
    Quick check if a feature is available
    
    Args:
        feature: Feature name
        edition: Optional edition
    
    Returns:
        Check result
    """
    try:
        feature_flag = FeatureFlag(feature)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feature name: {feature}"
        )
    
    # If edition specified, validate it
    edition_enum = None
    if edition:
        edition_enum = feature_service.validate_edition(edition)
        if not edition_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid edition: {edition}"
            )
    
    is_enabled = feature_service.is_feature_enabled(feature_flag, edition_enum)
    
    return {
        "feature": feature,
        "enabled": is_enabled,
        "edition": edition_enum.value if edition_enum else feature_service.get_current_edition().value
    }
