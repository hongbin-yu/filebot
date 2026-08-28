# FileBot — 数字资产管理平台 (DAM)

加拿大政府数字资产全生命周期管理平台。AI 自动标签，零数据出境。

## 核心能力

- 多格式支持（图片 / PDF / 视频 / 文档）
- AI 自动标签（Ollama/Phi3 本地运行，零数据外泄）
- 格式转换（WebP / AVIF / 多尺寸）
- 版本管理与回滚
- CMS-DAM 联动（CMS 编辑器中直接选取资产）
- AI 图片分类与搜索

## 技术栈

|组件|选型|
|-|-|
|AI 引擎|Ollama + Phi3（本地，零数据流出）|
|存储|PostgreSQL + 对象存储|
|格式转换|本机 ImageMagick / FFmpeg|

## 项目结构

```
filebot/
├── docs/       # 设计文档、架构图
├── src/        # 核心代码
├── scripts/    # 部署、配置脚本
├── tests/      # 测试
└── README.md   # 本文件
```
