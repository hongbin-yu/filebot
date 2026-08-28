# 录影场景 & 旁白对应表 — v2

根据你实际录制的画面重新编排。

## Scene 01 — Opening (30s)
**画面：** Logo → 团队成员头像 → 公司名
**旁白：** 保持不变（已可用的那段）

## Scene 02 — FileBot Dashboard (1.5min)
**画面：** 菜单扫过 → 筛选 → 树结构 → 缩略图
**旁白：** 保持不变（已可用的那段）

## Scene 03 — Data Migration (1.5min)
**画面：** canada.ca/en.html → 点击 Bookmarklet → Site Import 弹出 → 输入 https://www.canada.ca/en/services/environment.html → Start Import → 输出 "page and images crawled OK Done"
**旁白：** 需重写——描述页面操作过程

## Scene 04 — AI Import via Younai (1min)
**画面：** 你和油奈的对话记录（完整对话）：
  1. 你：Import one URL and related French page
  2. 油奈：asks details
  3. 你：https://www.canada.ca/en/services/environment.html
  4. 油奈：导入成功，显示 EN+FR 结果表
  5. 你：Publish both pages
  6. 油奈：Both pages published，显示发布状态表
**旁白：** 需重写——说明 AI 助手如何完成多语言导入+发布

## Scene 05 — Webbot: 创建 + 编辑页面 (2min)
**画面：**
  1. 导航页 → 选 Demo 栏 → Create New Page
  2. 输入 "Managed canadasite" → 点 Translate → 法语自动生成
  3. 点 Create → 返回导航页 → 选中新页 → Edit
**旁白：** 需重写——描述创建双语页面的简单流程

## Scene 06 — Components (1min)
**画面：**
  1. 页面导航 → 展示所有组件列表（system components）
  2. 打开从 AEM 导入的页面 → 切到 HTML 源码
  3. AEM 组件 → 很多只能用 generic HTML
  4. 强调：Webfilebot 完全支持 AEM 组件，任何 HTML 片段都可视为 component
  5. 任何组合可编辑 → 不加额外 tag/CSS/JS
  6. Designer / Publisher 在线制作，不需要 programmer
**旁白：** 需重写——核心卖点，对比 AEM

## Scene 07 — Editor 完整流程 (1.5min)
**画面（同一段长视频）：**
  1. 编辑器 → Resources → Templates → 插入 Topic → 改标题
  2. Resources → Pages → 选页插链接 + 输入文字
  3. Resources → Images → 插图片 → 拖拽
  4. 选中图片 → 上传本地图片（预览选了一张）
  5. Preview（显示当前效果）
  6. Save → Publish → 弹出 "The page not approved"
  7. 回导航页 → Properties → Approve → Save
  8. 再 Publish → 发布成功
**旁白：** 需重写——描述完整流程，强调审批工作流

## Scene 08 — AI Assistant (1min)
**画面：**
  1. 编辑器打开 Demo 页
  2. Resources → AI Q&A → Insert Page Title "Demo"
  3. Resources → Components → Insert Alert → Insert Panel
  4. 打开 AI Assistant 对话框
  5. 选中 Alert → 输入 "change it blue" → Alert 变蓝色
  6. 选中 Panel → 输入 "change it red" → Panel header 变红色
  7. 输入 "help" → 列出所有 help 命令
**旁白：** 需重写——演示自然语言操控组件样式

## Scene 09 — AI Q&A Search (30s)
**画面：**
  1. AI Q&A 面板 → Ask a question 输入框
  2. 输入 "What is different AI search with keywords search"
  3. 点 Ask AI → 等待（事先跑了第一次所以快）
  4. 返回结果 → 点 Insert 插入编辑器
**旁白：** 需重写

## Scene 10 — AI Search vs Keyword Search (1min)
**画面：**
  1. 左：canada.ca 搜索 "find a job" → 41K 结果，描述无意义
  2. 右：Webbot AI Search 搜索 "find a job" → 精准结果 + 有意义描述 + Top 10 keyword result
**旁白：** 需重写——核心对比

## Scene 11 — AI Image Tagging (30s)
**画面：**
  1. FileBot → 个人照片文件夹
  2. AI Tag 选项 → 展示已标注的标签
  3. 选择不同标签 → 实时过滤显示对应照片
**旁白：** 需重写

## Scene 12 — CanadaSite on WebFileBot (30s)
**画面：**
  左：https://www.canada.ca
  右：https://canadasite.webfilebot
  同页面并排对比，视觉一模一样
**旁白：** 需重写

## Scene 13 — AnalyBot (30s)
**画面：**
  www.webfilebot.com → AnalyBot 模块 → 展示空仪表盘（暂无数据）
**旁白：** 需重写

## Scene 14 — Closing + Feature Comparison (1.5min)
**画面：** PPT 对比表（含 Security 新行）逐行动画展示
**旁白：** 需重写——含 Security 对比
