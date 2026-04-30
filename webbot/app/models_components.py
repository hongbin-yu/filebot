"""
WebBot 组件系统数据模型
用于WET-BOEW组件模板管理和版本控制
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# 枚举定义
class ComponentCategory(str, Enum):
    """组件分类"""
    BASIC = "basic"           # 基础组件
    FORM = "form"             # 表单组件
    NAVIGATION = "navigation"  # 导航组件
    CONTENT = "content"       # 内容组件
    LAYOUT = "layout"         # 布局组件
    WET_BOEW = "wet_boew"    # WET-BOEW标准组件
    CUSTOM = "custom"         # 自定义组件

class ComponentStatus(str, Enum):
    """组件状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"

class PropertyType(str, Enum):
    """属性类型"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    COLOR = "color"
    URL = "url"
    TEXT = "text"  # 多行文本
    JSON = "json"  # JSON数据
    I18N = "i18n"  # 多语言文本

class AIMode(str, Enum):
    """AI模式"""
    LOCAL_LLM = "local_llm"
    OPENAI_API = "openai_api"
    HYBRID = "hybrid"

# 属性定义模型
class PropertyDefinition(BaseModel):
    """组件属性定义"""
    name: str = Field(..., description="属性名称")
    type: PropertyType = Field(PropertyType.STRING, description="属性类型")
    label: str = Field(..., description="显示标签")
    description: Optional[str] = Field(None, description="属性描述")
    default: Optional[Any] = Field(None, description="默认值")
    required: bool = Field(False, description="是否必需")
    
    # 对于select类型
    options: Optional[List[str]] = Field(None, description="选项列表（select类型用）")
    
    # 对于i18n类型
    i18n: bool = Field(False, description="是否支持多语言")
    
    # 验证规则
    min_length: Optional[int] = Field(None, description="最小长度（字符串）")
    max_length: Optional[int] = Field(None, description="最大长度（字符串）")
    min_value: Optional[float] = Field(None, description="最小值（数字）")
    max_value: Optional[float] = Field(None, description="最大值（数字）")
    
    class Config:
        from_attributes = True

# 依赖定义
class Dependency(BaseModel):
    """组件依赖定义"""
    type: str = Field(..., description="依赖类型：css, js, font, other")
    url: str = Field(..., description="依赖URL")
    version: Optional[str] = Field(None, description="版本号")
    required: bool = Field(True, description="是否必需")

# 组件模板模型
class ComponentTemplateBase(BaseModel):
    """组件模板基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="组件唯一名称")
    display_name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    category: ComponentCategory = Field(ComponentCategory.BASIC, description="组件分类")
    description: Optional[str] = Field(None, description="组件描述")
    icon: Optional[str] = Field(None, description="图标标识")
    
    # 模板内容
    html_template: str = Field(..., description="HTML模板（支持{{变量}}语法）")
    css_template: Optional[str] = Field(None, description="CSS模板")
    js_template: Optional[str] = Field(None, description="JavaScript模板")
    
    # 属性定义
    properties: Dict[str, PropertyDefinition] = Field(default_factory=dict, description="属性定义")
    
    # 依赖
    dependencies: List[Dependency] = Field(default_factory=list, description="外部依赖")
    
    # WET-BOEW特定
    wet_boew_version: Optional[str] = Field(None, description="WET-BOEW版本要求")
    wet_boew_compliant: bool = Field(False, description="是否符合WET-BOEW标准")
    accessibility_checked: bool = Field(False, description="是否通过可访问性检查")
    
    # 元数据
    tags: List[str] = Field(default_factory=list, description="标签")
    author: Optional[str] = Field(None, description="作者")
    version: str = Field("1.0.0", description="模板版本")
    
    class Config:
        from_attributes = True

class ComponentTemplateCreate(ComponentTemplateBase):
    """创建组件模板请求模型"""
    pass

class ComponentTemplateUpdate(BaseModel):
    """更新组件模板请求模型"""
    display_name: Optional[str] = None
    category: Optional[ComponentCategory] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    html_template: Optional[str] = None
    css_template: Optional[str] = None
    js_template: Optional[str] = None
    properties: Optional[Dict[str, PropertyDefinition]] = None
    dependencies: Optional[List[Dependency]] = None
    wet_boew_compliant: Optional[bool] = None
    accessibility_checked: Optional[bool] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None

class ComponentTemplateResponse(ComponentTemplateBase):
    """组件模板响应模型"""
    id: str
    status: ComponentStatus
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    usage_count: int = Field(0, description="使用次数")
    
    class Config:
        from_attributes = True

# 组件版本模型
class ComponentVersionBase(BaseModel):
    """组件版本基础模型"""
    component_id: str = Field(..., description="组件ID")
    version_number: int = Field(..., description="版本号")
    content: Dict[str, Any] = Field(..., description="版本内容（完整配置）")
    change_description: Optional[str] = Field(None, description="变更描述")

class ComponentVersionCreate(ComponentVersionBase):
    """创建组件版本请求模型"""
    pass

class ComponentVersionResponse(ComponentVersionBase):
    """组件版本响应模型"""
    id: int
    created_by: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# 组件实例模型（页面中使用的组件）
class ComponentInstanceBase(BaseModel):
    """组件实例基础模型"""
    page_id: str = Field(..., description="所属页面ID")
    template_id: str = Field(..., description="模板ID")
    instance_name: str = Field(..., description="实例名称")
    configuration: Dict[str, Any] = Field(..., description="配置值")
    position: Optional[Dict[str, Any]] = Field(None, description="位置信息")

class ComponentInstanceCreate(ComponentInstanceBase):
    """创建组件实例请求模型"""
    pass

class ComponentInstanceUpdate(BaseModel):
    """更新组件实例请求模型"""
    configuration: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None

class ComponentInstanceResponse(ComponentInstanceBase):
    """组件实例响应模型"""
    id: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# AI配置模型
class AIConfigurationBase(BaseModel):
    """AI配置基础模型"""
    name: str = Field(..., description="配置名称")
    mode: AIMode = Field(AIMode.LOCAL_LLM, description="AI模式")
    
    # 本地LLM配置
    local_model_path: Optional[str] = Field(None, description="本地模型路径")
    local_model_name: Optional[str] = Field(None, description="本地模型名称")
    local_gpu_enabled: bool = Field(False, description="是否启用GPU")
    
    # OpenAI配置
    openai_api_key: Optional[str] = Field(None, description="OpenAI API密钥")
    openai_model: Optional[str] = Field("gpt-4", description="OpenAI模型")
    
    # 混合模式配置
    hybrid_rules: Optional[Dict[str, Any]] = Field(None, description="混合模式路由规则")
    
    # 功能配置
    enabled_features: List[str] = Field(default_factory=list, description="启用的AI功能")
    
    class Config:
        from_attributes = True

class AIConfigurationCreate(AIConfigurationBase):
    """创建AI配置请求模型"""
    pass

class AIConfigurationUpdate(BaseModel):
    """更新AI配置请求模型"""
    name: Optional[str] = None
    mode: Optional[AIMode] = None
    local_model_path: Optional[str] = None
    local_model_name: Optional[str] = None
    local_gpu_enabled: Optional[bool] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    hybrid_rules: Optional[Dict[str, Any]] = None
    enabled_features: Optional[List[str]] = None

class AIConfigurationResponse(AIConfigurationBase):
    """AI配置响应模型"""
    id: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool = Field(False, description="是否激活")
    
    class Config:
        from_attributes = True

# AI请求/响应模型
class ComponentAIRequest(BaseModel):
    """组件AI处理请求"""
    action: str = Field(..., description="AI动作类型")
    component_data: Dict[str, Any] = Field(..., description="组件数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    language: str = Field("en", description="目标语言")

class ComponentAIResponse(BaseModel):
    """组件AI处理响应"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

# 版本比较模型
class VersionComparisonRequest(BaseModel):
    """版本比较请求"""
    version_a_id: int
    version_b_id: int

class VersionComparisonResponse(BaseModel):
    """版本比较响应"""
    differences: List[Dict[str, Any]] = Field(..., description="差异列表")
    summary: str = Field(..., description="差异摘要")