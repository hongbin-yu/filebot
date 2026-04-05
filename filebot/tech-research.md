# FileBot 技术调研

## 文档转换技术方案

### 1. Python 方案

#### 1.1 核心转换库
- **TIFF → PDF**: 
  - `PIL/Pillow` + `pdf2image` (反向)
  - 或 `img2pdf`
- **JPEG → PDF**:
  - `PIL/Pillow` + `img2pdf`
- **Word → PDF**:
  - `python-docx` (读取) + `reportlab` (生成PDF)
  - 或调用 `LibreOffice` via `unoserver`/`pyuno`
  - 或使用 `docx2pdf` 库
- **PDF 处理**:
  - `PyPDF2` / `pypdf` (合并、拆分、提取)
  - `pdfplumber` (内容提取)
  - `pdf2image` (PDF转图像)
- **PCL → PDF**:
  - `Ghostscript` 命令行调用
  - `pcl2pdf` 专用工具
- **文本打印流 → PDF**:
  - 可能是 PostScript 或其他打印数据流
  - `Ghostscript` 处理 PS 到 PDF

#### 1.2 外部依赖
- **Ghostscript**: 处理 PCL, PostScript, PDF 优化
- **LibreOffice**: Word 转 PDF
- **Tesseract OCR**: 可选，用于扫描文档 OCR
- **ImageMagick**: 图像处理（可选）

#### 1.3 Python 后端框架
- **FastAPI**: 异步，高性能，自动 API 文档
- **Django**: 全功能，但较重
- **Flask**: 轻量级，灵活

### 2. Java 方案

#### 2.1 核心转换库
- **TIFF/JPEG → PDF**:
  - `Apache PDFBox` (图像转PDF)
  - `iText` (商业/开源)
- **Word → PDF**:
  - `Apache POI` (读取Word) + `iText` (生成PDF)
  - `JODConverter` (调用 LibreOffice)
  - `Aspose.Words` (商业)
- **PDF 处理**:
  - `Apache PDFBox`
  - `iText`
- **PCL → PDF**:
  - `Apache PDFBox` 可能支持
  - 或调用外部工具 (Ghostscript)
- **文本打印流 → PDF**:
  - 可能需要自定义解析器
  - 或调用 Ghostscript

#### 2.2 Java 后端框架
- **Spring Boot 3.x**: 现代 Java 框架
- **Micronaut**: 轻量级，启动快
- **Quarkus**: 云原生

### 3. 混合方案
- 文件管理: Java/Node.js
- 转换服务: Python 微服务（专门处理转换）
- 优点: 分离关注点，Python 处理转换更合适

### 4. 技术选型建议

#### 方案 A: Python 全栈 (推荐)
- **前端**: React + TypeScript
- **后端**: FastAPI (Python)
- **转换**: Python 库 + 外部工具调用
- **优点**:
  - Python 文档处理生态丰富
  - 开发效率高
  - 异步处理支持好
  - 易于调用命令行工具

#### 方案 B: Java 全栈
- **前端**: React + TypeScript  
- **后端**: Spring Boot 3.x
- **转换**: Apache PDFBox + 外部工具调用
- **优点**:
  - 与现有 smarti 技术栈一致
  - Java 类型安全
  - 企业级特性丰富

#### 方案 C: 混合架构
- **前端**: React
- **管理后端**: Spring Boot / Node.js
- **转换服务**: Python FastAPI 微服务
- **优点**:
  - 最佳工具做最佳工作
  - 可独立扩展转换服务
  - 容错性更好

### 5. 安装依赖检查
需要安装的系统级工具:
1. **Ghostscript** - PCL/PS/PDF 处理
2. **LibreOffice** - Word 转 PDF
3. **Tesseract OCR** - 可选，文字识别
4. **ImageMagick** - 可选，图像处理

### 6. 转换流程设计
```
上传文件 → 检测格式 → 路由到对应转换器 → 执行转换 → 生成PDF → 返回结果
                                 ↘ 错误处理 → 记录日志 → 通知用户
```