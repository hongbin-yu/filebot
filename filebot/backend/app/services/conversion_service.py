"""
文档转换服务

提供同步和异步的文档转换功能，支持多种格式到PDF的转换。
"""
import os
import shutil
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, BinaryIO, Dict, Any
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConversionFormat(str, Enum):
    """支持的转换格式"""
    TIFF = "tiff"
    TIF = "tif"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    PCL = "pcl"
    PS = "ps"
    TXT = "txt"
    CLD = "cld"


class ConversionError(Exception):
    """转换错误"""
    pass


class UnsupportedFormatError(ConversionError):
    """不支持的格式错误"""
    pass


class ConversionService:
    """文档转换服务"""
    
    def __init__(self):
        self.supported_formats = {
            ConversionFormat.TIFF: self._convert_image_to_pdf,
            ConversionFormat.TIF: self._convert_image_to_pdf,
            ConversionFormat.JPG: self._convert_image_to_pdf,
            ConversionFormat.JPEG: self._convert_image_to_pdf,
            ConversionFormat.PNG: self._convert_image_to_pdf,
            ConversionFormat.PDF: self._convert_pdf_to_pdf,  # 实际上是复制或优化
            ConversionFormat.DOC: self._convert_doc_to_pdf,
            ConversionFormat.DOCX: self._convert_docx_to_pdf,
            ConversionFormat.TXT: self._convert_txt_to_pdf,
            ConversionFormat.CLD: self._convert_cld_to_pdf,
            ConversionFormat.PCL: self._convert_pcl_to_pdf,
            ConversionFormat.PS: self._convert_ps_to_pdf,
        }
        
        # 初始化转换器状态
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """检查必要的依赖库"""
        missing_deps = []
        
        # 检查图像处理依赖
        try:
            import PIL
        except ImportError:
            missing_deps.append("Pillow (PIL)")
        
        # 检查PDF处理依赖
        try:
            import PyPDF2
        except ImportError:
            missing_deps.append("PyPDF2")
        
        # 检查Word文档处理
        try:
            import docx
        except ImportError:
            missing_deps.append("python-docx")
        
        # 检查图像转PDF
        try:
            import img2pdf
        except ImportError:
            missing_deps.append("img2pdf")
        
        if missing_deps:
            logger.warning(f"缺少依赖库: {', '.join(missing_deps)}")
            logger.warning("部分转换功能可能受限")
    
    def convert_file(
        self,
        source_path: Path | str,
        target_path: Path | str,
        source_format: Optional[str] = None,
        target_format: str = "pdf"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        转换单个文件
        
        Args:
            source_path: 源文件路径
            target_path: 目标文件路径
            source_format: 源文件格式（可选，自动检测）
            target_format: 目标格式（目前仅支持PDF）
            
        Returns:
            Tuple[是否成功, 消息, 元数据]
        """
        source_path = Path(source_path)
        target_path = Path(target_path)
        
        # 参数验证
        if not source_path.exists():
            return False, f"源文件不存在: {source_path}", None
        
        if target_format.lower() != "pdf":
            return False, f"目前仅支持转换为PDF格式，不支持: {target_format}", None
        
        # 自动检测源格式
        if not source_format:
            source_format = self._detect_format(source_path)
        
        # 检查格式支持
        try:
            format_enum = ConversionFormat(source_format.lower())
        except ValueError:
            supported = [f.value for f in ConversionFormat]
            return False, f"不支持的源格式: {source_format}，支持的格式: {', '.join(supported)}", None
        
        if format_enum not in self.supported_formats:
            return False, f"格式 {source_format} 的转换器未实现", None
        
        # 创建目标目录
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 执行转换
        try:
            logger.info(f"开始转换: {source_path} -> {target_path} ({source_format}->{target_format})")
            
            # 调用对应的转换函数
            converter = self.supported_formats[format_enum]
            metadata = converter(source_path, target_path)
            
            # 验证输出文件
            if not target_path.exists() or target_path.stat().st_size == 0:
                return False, f"转换失败: 输出文件为空或不存在", None
            
            logger.info(f"转换成功: {source_path} -> {target_path} ({target_path.stat().st_size} 字节)")
            return True, "转换成功", metadata
            
        except UnsupportedFormatError as e:
            return False, f"不支持的格式: {str(e)}", None
        except ConversionError as e:
            return False, f"转换失败: {str(e)}", None
        except Exception as e:
            logger.exception(f"转换过程中发生未知错误: {str(e)}")
            return False, f"转换过程中发生未知错误: {str(e)}", None
    
    def _detect_format(self, file_path: Path) -> str:
        """检测文件格式"""
        # 首先通过扩展名检测
        ext = file_path.suffix.lower().lstrip('.')
        if ext in [f.value for f in ConversionFormat]:
            return ext
        
        # TODO: 使用python-magic进行更精确的检测
        # 暂时回退到扩展名
        if ext:
            return ext
        
        raise UnsupportedFormatError(f"无法检测文件格式: {file_path}")
    
    # ========== 具体转换实现 ==========
    
    def _convert_image_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """图像转PDF"""
        try:
            import img2pdf
            from PIL import Image
            
            # 使用Pillow验证图像
            with Image.open(source_path) as img:
                img.verify()
            
            # 使用img2pdf转换
            with open(source_path, 'rb') as f:
                img_data = f.read()
            
            pdf_data = img2pdf.convert(img_data)
            
            with open(target_path, 'wb') as f:
                f.write(pdf_data)
            
            return {
                "converter": "img2pdf",
                "original_size": source_path.stat().st_size,
                "output_size": len(pdf_data),
                "format": "image_to_pdf"
            }
            
        except ImportError as e:
            logger.error(f"缺少图像转换依赖: {e}")
            # 回退到Pillow
            return self._convert_image_to_pdf_pillow(source_path, target_path)
        except Exception as e:
            raise ConversionError(f"图像转PDF失败: {str(e)}")
    
    def _convert_image_to_pdf_pillow(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """使用Pillow进行图像转PDF（备选方案）"""
        try:
            from PIL import Image
            
            # 打开图像并转换为RGB模式（如果需要）
            with Image.open(source_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 保存为PDF
                img.save(target_path, "PDF", resolution=100.0)
            
            return {
                "converter": "Pillow",
                "original_size": source_path.stat().st_size,
                "output_size": target_path.stat().st_size,
                "format": "image_to_pdf_pillow"
            }
            
        except Exception as e:
            raise ConversionError(f"Pillow图像转PDF失败: {str(e)}")
    
    def _convert_pdf_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """PDF到PDF（优化或复制）"""
        try:
            import PyPDF2
            
            # 简单复制（未来可以添加优化功能）
            shutil.copy2(source_path, target_path)
            
            return {
                "converter": "copy",
                "original_size": source_path.stat().st_size,
                "output_size": target_path.stat().st_size,
                "format": "pdf_copy"
            }
            
        except Exception as e:
            raise ConversionError(f"PDF处理失败: {str(e)}")
    
    def _convert_doc_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """DOC转PDF"""
        # TODO: 实现DOC到PDF转换（可能需要unoconv或LibreOffice）
        raise UnsupportedFormatError("DOC到PDF转换暂未实现，需要LibreOffice或unoconv")
    
    def _convert_docx_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """DOCX转PDF"""
        # TODO: 实现DOCX到PDF转换
        raise UnsupportedFormatError("DOCX到PDF转换暂未实现")
    
    def _convert_txt_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """文本文件转PDF"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            from reportlab.lib.units import inch
            
            # 读取文本内容
            with open(source_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # 创建PDF
            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # 创建样式
            styles = getSampleStyleSheet()
            normal_style = styles['Normal']
            
            # 准备内容
            story = []
            story.append(Paragraph("文本转换", styles['Title']))
            story.append(Spacer(1, 12))
            
            # 分割文本行
            lines = text_content.split('\n')
            for line in lines:
                if line.strip():
                    story.append(Paragraph(line.strip(), normal_style))
                    story.append(Spacer(1, 6))
            
            # 生成PDF
            doc.build(story)
            
            return {
                "converter": "reportlab",
                "original_size": source_path.stat().st_size,
                "output_size": target_path.stat().st_size,
                "line_count": len(lines),
                "format": "txt_to_pdf"
            }
            
        except ImportError as e:
            logger.error(f"缺少reportlab依赖: {e}")
            raise ConversionError("文本转PDF需要reportlab库")
        except Exception as e:
            raise ConversionError(f"文本转PDF失败: {str(e)}")
    
    def _convert_cld_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """CLD文件转PDF - 固定宽度文本格式处理
        
        .cld文件格式说明（根据用户提供）:
        - 自定义文件格式，每行固定255个字符
        - 包含大量空格（需要压缩去掉空格）
        - 旧系统使用JasperReports (.jasper模板) + 压缩后的内容生成PDF
        
        当前实现:
        1. 读取.cld文件，验证每行长度（应为255字符）
        2. 压缩每行：去掉所有空格
        3. 使用reportlab生成PDF（临时方案，未来需集成JasperReports）
        """
        try:
            import datetime
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            from reportlab.lib.units import inch
            
            # 读取.cld文件内容
            with open(source_path, 'r', encoding='utf-8') as f:
                cld_lines = f.readlines()
            
            original_line_count = len(cld_lines)
            logger.info(f"读取.cld文件: {original_line_count} 行")
            
            # 验证每行长度并压缩空格
            processed_lines = []
            line_length_stats = []
            compression_stats = []
            
            for i, line in enumerate(cld_lines, 1):
                # 去除换行符
                line = line.rstrip('\n')
                
                # 记录原始长度
                original_len = len(line)
                line_length_stats.append(original_len)
                
                # 验证长度（应为255字符，但允许轻微偏差）
                if original_len != 255:
                    logger.warning(f"第 {i} 行: 长度 {original_len} 字符 (预期255)")
                
                # 压缩空格：去掉所有空格
                compressed_line = line.replace(' ', '')
                compressed_len = len(compressed_line)
                compression_stats.append({
                    'line': i,
                    'original': original_len,
                    'compressed': compressed_len,
                    'spaces_removed': original_len - compressed_len
                })
                
                # 只保留非空行
                if compressed_line.strip():
                    processed_lines.append(compressed_line)
            
            # 统计信息
            valid_lines = len(processed_lines)
            avg_original_len = sum(line_length_stats) / len(line_length_stats) if line_length_stats else 0
            total_spaces_removed = sum(stat['spaces_removed'] for stat in compression_stats)
            
            logger.info(f"CLD文件统计: {original_line_count} 行, {valid_lines} 行非空")
            logger.info(f"平均行长度: {avg_original_len:.1f} 字符")
            logger.info(f"总共移除空格: {total_spaces_removed} 个")
            
            # 创建PDF
            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # 创建样式
            styles = getSampleStyleSheet()
            normal_style = styles['Normal']
            
            # 准备内容
            story = []
            story.append(Paragraph("CLD文件转换 (空格压缩后)", styles['Title']))
            story.append(Spacer(1, 12))
            
            # 添加文件信息
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            info_text = f"""
            文件: {source_path.name}<br/>
            原始行数: {original_line_count}<br/>
            非空行数: {valid_lines}<br/>
            平均行长度: {avg_original_len:.1f} 字符<br/>
            移除空格总数: {total_spaces_removed}<br/>
            转换时间: {current_time}<br/>
            注意: 这是临时文本转换，未使用JasperReports模板
            """
            story.append(Paragraph(info_text, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # 添加压缩后的内容
            story.append(Paragraph("=== 压缩后内容 ===", styles['Heading2']))
            story.append(Spacer(1, 6))
            
            for line in processed_lines:
                if line.strip():  # 再次检查非空
                    # 限制显示长度，避免PDF过长
                    display_line = line[:100] + ("..." if len(line) > 100 else "")
                    story.append(Paragraph(display_line, normal_style))
                    story.append(Spacer(1, 3))
            
            # 生成PDF
            doc.build(story)
            
            return {
                "converter": "reportlab (CLD空格压缩)",
                "original_size": source_path.stat().st_size,
                "output_size": target_path.stat().st_size,
                "line_count": original_line_count,
                "valid_line_count": valid_lines,
                "avg_line_length": round(avg_original_len, 1),
                "total_spaces_removed": total_spaces_removed,
                "format": "cld_to_pdf",
                "note": "已应用空格压缩，但未使用JasperReports模板。未来需集成JasperReports引擎。"
            }
            
        except ImportError as e:
            logger.error(f"缺少reportlab依赖: {e}")
            raise ConversionError("CLD转PDF需要reportlab库")
        except Exception as e:
            raise ConversionError(f"CLD转PDF失败: {str(e)}")
    
    def _convert_pcl_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """PCL转PDF - 使用pcltopdf命令行工具
        
        依赖: pcltopdf (第三方工具)
        安装: 需要用户手动安装pcltopdf
        """
        try:
            # 检查pcltopdf是否可用
            try:
                subprocess.run(["pcltopdf", "--version"], capture_output=True, check=False)
            except FileNotFoundError:
                raise ConversionError(
                    "pcltopdf命令未找到。请安装pcltopdf工具:\n"
                    "Ubuntu/Debian: sudo apt-get install pcltops (可能包含pcltopdf)\n"
                    "或从源代码编译: https://www.pclinuxos.com/forum/index.php?topic=150245.0\n"
                    "或使用替代方案: ghostscript (gs)"
                )
            
            # 执行转换
            logger.info(f"使用pcltopdf转换PCL文件: {source_path} -> {target_path}")
            
            # 构建命令: pcltopdf input.pcl output.pdf
            cmd = ["pcltopdf", str(source_path), str(target_path)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode != 0:
                error_msg = f"pcltopdf转换失败 (exit code: {result.returncode}):\n"
                if result.stderr:
                    error_msg += f"stderr: {result.stderr[:500]}"
                raise ConversionError(error_msg)
            
            # 检查输出文件是否存在
            if not target_path.exists():
                raise ConversionError(f"转换输出文件不存在: {target_path}")
            
            return {
                "converter": "pcltopdf",
                "original_size": source_path.stat().st_size,
                "output_size": target_path.stat().st_size,
                "format": "pcl_to_pdf",
                "command": " ".join(cmd),
                "success": True
            }
            
        except subprocess.TimeoutExpired:
            raise ConversionError("pcltopdf转换超时（超过30秒）")
        except ConversionError:
            raise  # 重新抛出已有的ConversionError
        except Exception as e:
            raise ConversionError(f"PCL转PDF失败: {str(e)}")
    
    def _convert_ps_to_pdf(self, source_path: Path, target_path: Path) -> Dict[str, Any]:
        """PostScript转PDF - 使用ghostscript (gs)命令行工具
        
        依赖: ghostscript (gs)
        安装: Ubuntu/Debian: sudo apt-get install ghostscript
        """
        try:
            # 检查ghostscript是否可用
            try:
                subprocess.run(["gs", "--version"], capture_output=True, check=False)
            except FileNotFoundError:
                raise ConversionError(
                    "ghostscript (gs)命令未找到。请安装ghostscript:\n"
                    "Ubuntu/Debian: sudo apt-get install ghostscript\n"
                    "或从官网下载: https://www.ghostscript.com/"
                )
            
            # 执行转换: gs -sDEVICE=pdfwrite -o output.pdf input.ps
            logger.info(f"使用ghostscript转换PS文件: {source_path} -> {target_path}")
            
            cmd = [
                "gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                f"-sOutputFile={target_path}",
                str(source_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode != 0:
                error_msg = f"ghostscript转换失败 (exit code: {result.returncode}):\n"
                if result.stderr:
                    error_msg += f"stderr: {result.stderr[:500]}"
                raise ConversionError(error_msg)
            
            # 检查输出文件是否存在
            if not target_path.exists():
                raise ConversionError(f"转换输出文件不存在: {target_path}")
            
            return {
                "converter": "ghostscript",
                "original_size": source_path.stat().st_size,
                "output_size": target_path.stat().st_size,
                "format": "ps_to_pdf",
                "command": " ".join(cmd),
                "success": True
            }
            
        except subprocess.TimeoutExpired:
            raise ConversionError("ghostscript转换超时（超过30秒）")
        except ConversionError:
            raise  # 重新抛出已有的ConversionError
        except Exception as e:
            raise ConversionError(f"PostScript转PDF失败: {str(e)}")
    
    def get_supported_formats(self) -> Dict[str, list]:
        """获取支持的格式列表"""
        source_formats = [f.value for f in self.supported_formats.keys()]
        return {
            "source_formats": source_formats,
            "target_formats": ["pdf"]
        }


# 全局单例实例
_conversion_service_instance = None

def get_conversion_service() -> ConversionService:
    """获取转换服务单例"""
    global _conversion_service_instance
    if _conversion_service_instance is None:
        _conversion_service_instance = ConversionService()
    return _conversion_service_instance