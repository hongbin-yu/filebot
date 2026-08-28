# WebBot — Headless/Hybrid CMS + DXP

加拿大政府网站内容管理平台。静态 HTML 架构，天然 Protected B 安全合规。

## 定位

替代 Adobe AEM 的加拿大自研 CMS。Mustache 模板引擎 + TinyMCE WYSIWYG 编辑器。

## 核心能力

- Headless/Hybrid 双模式
- Mustache 模板系统（语义化 HTML）
- TinyMCE WYSIWYG 所见即所得编辑
- RBAC 四级权限
- 多语言（EN/FR + 可扩展）
- 页面版本管理
- Metadata 管理（受控词表、Schema.org）
- 工作流引擎

## 技术栈

|组件|选型|
|-|-|
|渲染引擎|Mustache 模板（静态 HTML）|
|编辑器|TinyMCE WYSIWYG|
|存储|PostgreSQL|
|发布|Publish Server → CDN|

## 项目结构

```
webbot/
├── docs/       # 设计文档、架构图
├── src/        # 核心代码
├── scripts/    # 部署、配置脚本
├── tests/      # 测试
└── README.md   # 本文件
```
