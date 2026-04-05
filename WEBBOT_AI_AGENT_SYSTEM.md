# WebBot AI代理系统详细设计

## 🤖 概述

WebBot AI代理系统是一个**任务驱动的网站创建和修改自动化系统**，通过AI理解用户任务并自动生成符合Canada.CA要求的网站内容。

### 🎯 设计目标
1. **自动化**: 最小化人工编辑，最大化AI自动化
2. **合规性**: 确保所有生成内容符合Canada.CA政府网站要求
3. **效率**: 快速处理网站创建和修改任务
4. **质量**: 生成高质量、一致性的网站内容
5. **可扩展**: 支持多种AI后端和任务类型

### 🔄 核心工作流程
```
用户提交任务 → 任务队列 → AI处理 → 结果验证 → 静态生成 → 部署 → 任务完成
       ↑          ↓          ↓          ↓          ↓         ↓         ↓
    任务创建   任务调度   AI理解执行  合规检查  文件生成  网站更新  状态反馈
```

## 🏗️ 系统架构

### 整体架构组件
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  任务管理前端   │───▶│  FastAPI后端    │───▶│  FileBot AI服务 │
│  (原生HTML+htmx)│    │  (任务处理)     │    │  (共用基础设施) │
└─────────────────┘    └────────┬────────┘    └────────┬────────┘
        ↑                       │                       │
        │                       ▼                       ▼
        │               ┌─────────────────┐    ┌─────────────────┐
        └───────────────│  共享SQLite     │    │  静态生成工具   │
                        │  数据库         │◀───│  (Python脚本)   │
                        │  (FileBot扩展)  │    └────────┬────────┘
                        └─────────────────┘             │
                                │                       ▼
                                │               ┌─────────────────┐
                                └───────────────│  云服务器部署   │
                                                │  (纯静态文件)   │
                                                └─────────────────┘
```

## 📋 核心组件设计

### 1. 任务管理系统

#### 任务数据模型
```python
# 数据库表设计 (扩展FileBot SQLite)
class WebBotTask:
    id: str                     # 任务唯一ID
    title: str                  # 任务标题
    description: str            # 详细任务描述
    priority: enum              # 优先级: 高/中/低
    status: enum                # 状态: 待处理/处理中/已完成/失败
    created_at: datetime        # 创建时间
    deadline: datetime          # 截止时间
    submitted_by: str           # 提交用户 (关联FileBot用户)
    ai_model_used: str          # 使用的AI模型
    ai_processing_time: int     # AI处理耗时(秒)
    generated_content: json     # AI生成的内容和代码
    compliance_check_result: json  # 合规检查结果
    human_review_status: enum   # 人工审核状态: 待审核/通过/需修改/拒绝
    human_review_notes: str     # 人工审核意见
    final_website_url: str      # 最终部署的网站URL
    version_history: json       # 版本历史记录
```

#### 任务状态机
```
待处理 → 处理中 → 已完成
    ↓        ↓        ↓
   AI开始   AI处理   静态生成
   处理     中...    和部署
    ↓        ↓        ↓
  结果验证  合规检查  任务完成
    ↓        ↓        ↓
 人工审核  质量评估  状态反馈
```

#### 用户界面设计
- **任务列表**: 类似Jira的看板视图，按状态分组
- **任务创建**: 表单式任务创建，支持模板和示例
- **任务详情**: 显示任务详情、AI处理进度、生成结果
- **结果预览**: 实时预览AI生成的网站效果
- **审核界面**: 人工审核和修改界面

### 2. AI处理引擎

#### AI能力栈设计
```
┌─────────────────────────────────────┐
│          任务理解层                  │
│  • 自然语言理解 (NLP)               │
│  • 意图识别和分类                   │
│  • 需求提取和解析                   │
├─────────────────────────────────────┤
│          网站分析层                  │
│  • 现有网站结构分析                 │
│  • 内容评估和差距分析               │
│  • 技术约束识别                     │
├─────────────────────────────────────┤
│          内容生成层                  │
│  • HTML/CSS/JS代码生成              │
│  • 内容创作和优化                   │
│  • 多语言内容生成                   │
├─────────────────────────────────────┤
│          合规检查层                  │
│  • WCAG 2.1 AA可访问性检查          │
│  • 政府网站标准检查                 │
│  • 安全和隐私合规检查               │
├─────────────────────────────────────┤
│          质量评估层                  │
│  • 生成质量自我评估                 │
│  • 用户体验评估                     │
│  • 性能指标评估                     │
└─────────────────────────────────────┘
```

#### 与FileBot AI集成接口
```python
class FileBotAIIntegration:
    def __init__(self, filebot_ai_endpoint: str):
        self.endpoint = filebot_ai_endpoint
        
    def process_website_task(self, task_description: str, 
                            current_website_state: dict = None) -> dict:
        """调用FileBot AI处理网站任务"""
        payload = {
            "task_type": "website_creation_modification",
            "task_description": task_description,
            "requirements": {
                "compliance_standard": "canada_ca_simple",
                "accessibility_level": "wcag_2_1_aa",
                "multilingual_support": ["en", "fr"]
            },
            "current_state": current_website_state,
            "client_resources": {
                "css_files": ["client-styles.css"],
                "js_files": ["client-scripts.js"]
            }
        }
        
        response = requests.post(
            f"{self.endpoint}/api/v1/ai/process-website-task",
            json=payload
        )
        
        return response.json()
    
    def validate_compliance(self, generated_content: dict) -> dict:
        """调用FileBot AI验证合规性"""
        # 实现细节...
        pass
    
    def evaluate_quality(self, generated_content: dict) -> dict:
        """调用FileBot AI评估生成质量"""
        # 实现细节...
        pass
```

#### 支持的多AI后端
```python
class AIModelRegistry:
    """AI模型注册表，支持多种AI后端"""
    
    MODELS = {
        "ollama": {
            "type": "local_llm",
            "endpoint": "http://localhost:11434",
            "capabilities": ["text_generation", "code_generation"],
            "models": ["llama3", "mistral", "codellama"]
        },
        "openai": {
            "type": "cloud_api",
            "endpoint": "https://api.openai.com/v1",
            "capabilities": ["text_generation", "code_generation", "analysis"],
            "models": ["gpt-4", "gpt-3.5-turbo"]
        },
        "custom_trained": {
            "type": "custom",
            "endpoint": "http://localhost:8080",
            "capabilities": ["website_generation", "compliance_check"],
            "models": ["webgen-v1", "gov-comply-v1"]
        }
    }
    
    def get_model(self, model_name: str, backend: str = "ollama"):
        """获取配置的AI模型"""
        config = self.MODELS.get(backend)
        if not config:
            raise ValueError(f"Unsupported AI backend: {backend}")
        
        # 返回模型配置
        return {
            **config,
            "model_name": model_name,
            "full_endpoint": f"{config['endpoint']}/api/generate"
        }
```

### 3. 合规保障系统

#### 多层合规检查机制
```
┌─────────────────────────────────────┐
│         AI自检 (第一层)              │
│  • 生成时实时合规检查                │
│  • 规则引擎验证                     │
│  • 自动修正建议                    │
├─────────────────────────────────────┤
│       自动检查 (第二层)              │
│  • 静态分析工具                     │
│  • 可访问性扫描器                   │
│  • 安全漏洞扫描                     │
├─────────────────────────────────────┤
│       人工审核 (第三层)              │
│  • 专家审核                        │
│  • 客户确认                        │
│  • 政府合规专家审核                │
└─────────────────────────────────────┘
```

#### Canada.CA合规规则库
```python
class CanadaCAComplianceRules:
    """Canada.CA合规规则库"""
    
    RULES = {
        "accessibility": {
            "wcag_2_1_aa": {
                "perceivable": ["text_alternatives", "time_based_media", "adaptable", "distinguishable"],
                "operable": ["keyboard_accessible", "enough_time", "seizures", "navigable"],
                "understandable": ["readable", "predictable", "input_assistance"],
                "robust": ["compatible"]
            }
        },
        "design": {
            "simplicity": True,
            "consistency": True,
            "clarity": True,
            "responsive": True
        },
        "content": {
            "bilingual": ["en", "fr"],
            "government_tone": True,
            "clarity": True,
            "accuracy": True
        },
        "technical": {
            "security": ["https", "secure_headers", "privacy_protection"],
            "performance": ["fast_loading", "optimized_resources"],
            "compatibility": ["modern_browsers", "mobile_devices"]
        }
    }
    
    def check_compliance(self, html_content: str, css_content: str = None) -> dict:
        """检查HTML/CSS内容是否符合Canada.CA规则"""
        results = {
            "overall_compliant": True,
            "failed_checks": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 实现具体检查逻辑
        # ...
        
        return results
```

### 4. 静态生成和部署系统

#### 静态生成流程
```python
class StaticSiteGenerator:
    """静态网站生成器"""
    
    def generate_from_database(self, task_id: str):
        """从数据库生成静态网站"""
        # 1. 获取任务和生成的内容
        task = self.db.get_task(task_id)
        generated_content = task["generated_content"]
        
        # 2. 准备模板和数据
        template_data = {
            "html": generated_content["html"],
            "css": self._merge_client_css(generated_content["css"]),
            "js": self._merge_client_js(generated_content["js"]),
            "metadata": generated_content["metadata"]
        }
        
        # 3. 应用模板生成文件
        html_file = self._apply_template("base.html", template_data)
        css_file = template_data["css"]
        js_file = template_data["js"]
        
        # 4. 优化和压缩
        optimized_html = self._optimize_html(html_file)
        optimized_css = self._optimize_css(css_file)
        optimized_js = self._optimize_js(js_file)
        
        # 5. 生成文件结构
        output_dir = f"build/{task_id}"
        self._write_files(output_dir, {
            "index.html": optimized_html,
            "styles.css": optimized_css,
            "scripts.js": optimized_js,
            "assets/": generated_content["assets"]
        })
        
        return output_dir
    
    def _merge_client_css(self, ai_generated_css: str) -> str:
        """合并客户提供的CSS"""
        client_css = self._load_client_resource("css")
        return f"{client_css}\n\n{ai_generated_css}"
    
    def _merge_client_js(self, ai_generated_js: str) -> str:
        """合并客户提供的JS"""
        client_js = self._load_client_resource("js")
        return f"{client_js}\n\n{ai_generated_js}"
```

#### 部署管道
```
生成完成 → 文件验证 → 上传到云存储 → CDN刷新 → 健康检查 → 通知用户
    ↓          ↓           ↓           ↓          ↓          ↓
构建成功  完整性检查  安全传输   缓存失效  功能测试  状态更新
```

## 🔧 技术实现细节

### API设计
```python
# FastAPI路由设计
@app.post("/api/v1/tasks")
async def create_task(task_data: TaskCreateSchema):
    """创建新任务"""
    pass

@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    pass

@app.post("/api/v1/tasks/{task_id}/process")
async def process_task(task_id: str):
    """处理任务 (调用AI)"""
    pass

@app.get("/api/v1/tasks/{task_id}/preview")
async def preview_task_result(task_id: str):
    """预览任务生成结果"""
    pass

@app.post("/api/v1/tasks/{task_id}/deploy")
async def deploy_task_result(task_id: str):
    """部署任务生成结果"""
    pass

@app.post("/api/v1/ai/models")
async def list_ai_models():
    """列出可用的AI模型"""
    pass

@app.post("/api/v1/ai/test")
async def test_ai_connection():
    """测试AI服务连接"""
    pass
```

### 数据库扩展设计
```sql
-- 在FileBot SQLite数据库中新增表
CREATE TABLE webbot_tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT CHECK(priority IN ('high', 'medium', 'low')),
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP,
    submitted_by TEXT REFERENCES users(id),
    ai_model_used TEXT,
    ai_processing_time INTEGER,
    generated_content JSON,
    compliance_check_result JSON,
    human_review_status TEXT CHECK(human_review_status IN ('pending', 'approved', 'needs_revision', 'rejected')),
    human_review_notes TEXT,
    final_website_url TEXT,
    version_history JSON
);

CREATE TABLE webbot_ai_models (
    id TEXT PRIMARY KEY,
    backend_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    capabilities JSON,
    is_active BOOLEAN DEFAULT 1,
    config JSON
);

CREATE TABLE webbot_client_resources (
    id TEXT PRIMARY KEY,
    resource_type TEXT CHECK(resource_type IN ('css', 'js', 'template')),
    file_path TEXT NOT NULL,
    version TEXT,
    is_active BOOLEAN DEFAULT 1
);
```

## 🚀 实施路线图

### 阶段1: 基础框架 (4-6周)
- 任务管理系统前端和后端
- 基础AI集成 (简单任务处理)
- 静态生成基础功能

### 阶段2: AI能力建设 (6-8周)
- 任务理解AI模型训练
- 代码生成AI模型开发
- 合规检查AI能力实现

### 阶段3: 系统完善 (4-6周)
- 高级工作流和审批流程
- 性能优化和监控
- 用户体验改进

### 阶段4: 扩展和优化 (4-6周)
- 多AI后端支持优化
- 客户化功能开发
- 生产环境部署和调优

## 📊 监控和评估

### 关键性能指标 (KPI)
1. **任务处理成功率**: > 90%
2. **平均处理时间**: < 2小时
3. **合规通过率**: > 95%
4. **用户满意度**: > 4.5/5.0
5. **系统可用性**: > 99.5%

### 监控系统
- **任务队列监控**: 任务积压和处理速度
- **AI服务监控**: AI模型性能和可用性
- **生成质量监控**: 合规性和质量指标
- **部署监控**: 部署成功率和性能

### 持续改进机制
- **反馈循环**: 从人工审核中学习改进AI
- **A/B测试**: 测试不同AI模型和策略
- **性能优化**: 持续优化处理流程和性能
- **规则更新**: 根据政府要求更新合规规则

## 🚨 风险管理和缓解

### 技术风险
1. **AI能力不足**: 渐进实施，保留人工备选
2. **合规风险**: 多层检查机制，专家审核
3. **性能风险**: 优化AI模型和构建流程

### 运营风险
1. **AI服务中断**: 服务降级，人工处理流程
2. **构建失败**: 完善错误处理和回滚机制
3. **安全风险**: 严格的安全控制和审计

### 业务风险
1. **用户接受度**: 直观界面，渐进引入
2. **需求变化**: 灵活架构，快速适应
3. **竞争风险**: 持续创新，技术领先

---

**创建时间**: 2026-03-21 08:50 EDT  
**基于**: WebBot V3技术方案和用户AI需求  
**目的**: 为AI代理系统提供详细设计参考  
**状态**: 详细设计文档，用于开发和讨论  
**核心价值**: 自动化、合规、高效的政府网站AI解决方案