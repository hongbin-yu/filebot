from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class FileNamingRuleBase(BaseModel):
    """文档编号生成规则（对应旧系统的recordclass）"""
    name: Optional[str] = Field(None, max_length=100, description="规则名称（可选）")
    basename: str = Field(..., max_length=50, description="文档编号前缀，如'PO-'")
    max_number: int = Field(default=0, ge=0, description="当前最大序列号")
    increment_by: int = Field(default=1, ge=1, description="序列号增量")
    description: Optional[str] = Field(None, max_length=500, description="规则描述")
    subfolder_name: Optional[str] = Field(None, max_length=100, description="子文件夹名称，用于文件分目录存储")


class FileNamingRuleCreate(FileNamingRuleBase):
    """文件命名规则创建模型"""
    app_id: uuid.UUID = Field(..., description="所属应用ID")
    created_by: Optional[str] = Field(None, description="创建者用户名")


class FileNamingRuleUpdate(BaseModel):
    """文档编号生成规则更新模型"""
    name: Optional[str] = Field(None, max_length=100, description="规则名称（可选）")
    basename: Optional[str] = Field(None, max_length=50, description="文档编号前缀，如'PO-'")
    max_number: Optional[int] = Field(None, ge=0, description="当前最大序列号")
    increment_by: Optional[int] = Field(None, ge=1, description="序列号增量")
    description: Optional[str] = Field(None, max_length=500, description="规则描述")
    updated_by: Optional[str] = Field(None, description="更新者用户名")


class FileNamingRuleResponse(FileNamingRuleBase):
    """文件命名规则响应模型"""
    id: uuid.UUID
    app_id: uuid.UUID
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class FileNamingRuleWithNext(FileNamingRuleResponse):
    """包含下一个文档编号的规则响应"""
    next_document_number: str = Field(..., description="下一个生成的文档编号")
    
    @classmethod
    def from_orm_with_next(cls, rule):
        """从ORM对象创建响应，包含下一个文档编号"""
        data = cls.from_orm(rule)
        data.next_document_number = f"{rule.basename}{rule.max_number:04d}"
        return data