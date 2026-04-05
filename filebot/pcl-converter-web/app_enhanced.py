"""
PCL to PDF Converter Web Application - 增强专业版
优化Web界面，增强工具检测和错误处理

功能：
1. 专业级Web界面，支持实时状态监控
2. 增强工具检测，支持hplip、ghostscript等多种工具
3. 详细转换进度显示和多步骤跟踪
4. 智能错误处理和修复建议
5. 转换统计和历史记录
"""

import os
import sys
import platform
import subprocess
import json
import time
import logging
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import traceback

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app_enhanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 基础配置
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_MB', 100)) * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['CONVERTED_FOLDER'] = os.environ.get('CONVERTED_FOLDER', 'converted')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 统计文件路径
STATS_FILE = 'logs/conversion_stats.json'

# PCL工具配置
PCL_TOOL_PATH = os.environ.get('PCL_TOOL_PATH', 'auto')
PCL_TOOL_TIMEOUT = int(os.environ.get('PCL_TOOL_TIMEOUT', 60))

# 确保目录存在
for folder in [app.config['UPLOAD_FOLDER'], app.config['CONVERTED_FOLDER'], 'logs']:
    os.makedirs(folder, exist_ok=True)

# 初始化统计
def init_stats():
    if not os.path.exists(STATS_FILE):
        stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'conversion_times': [],
            'daily_stats': {},
            'tool_usage': {},
            'last_reset': datetime.now().isoformat()
        }
        save_stats(stats)
        return stats
    else:
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return init_stats()

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        logger.error(f"保存统计失败: {str(e)}")

def update_stats(success=True, duration_seconds=0, tool_name=None):
    try:
        stats = init_stats()
        stats['total_conversions'] += 1
        
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in stats['daily_stats']:
            stats['daily_stats'][today] = {'success': 0, 'fail': 0}
        
        if success:
            stats['successful_conversions'] += 1
            stats['daily_stats'][today]['success'] += 1
            if duration_seconds > 0:
                stats['conversion_times'].append(duration_seconds)
                # 保留最近1000次记录
                if len(stats['conversion_times']) > 1000:
                    stats['conversion_times'] = stats['conversion_times'][-1000:]
        else:
            stats['failed_conversions'] += 1
            stats['daily_stats'][today]['fail'] += 1
        
        if tool_name:
            if tool_name not in stats['tool_usage']:
                stats['tool_usage'][tool_name] = 0
            stats['tool_usage'][tool_name] += 1
        
        save_stats(stats)
    except Exception as e:
        logger.error(f"更新统计失败: {str(e)}")

# 增强工具检测
def detect_pcl_tools_enhanced():
    """增强版PCL工具检测，支持更多工具"""
    tools_to_check = [
        # GhostPCL工具
        ('gpcl6', ['gpcl6', 'gpcl6.exe']),
        ('pcl6', ['pcl6', 'pcl6.exe']),
        
        # Ghostscript工具（尝试PCL转换）
        ('gs', ['gs', 'gswin64c.exe', 'gswin32c.exe']),
        
        # HP工具（来自hplip）
        ('pclmtoraster', ['pclmtoraster']),
        ('rastertopclx', ['rastertopclx']),
        ('commandtopclx', ['commandtopclx']),
        ('ippevepcl', ['ippevepcl']),
        
        # 其他可能的工具
        ('pcltopdf', ['pcltopdf', 'pcltopdf.exe']),
        ('pcl2pdf', ['pcl2pdf', 'pcl2pdf.exe']),
        ('pdftopcl', ['pdftopcl', 'pdftopcl.exe']),
    ]
    
    detected_tools = []
    
    for tool_name, tool_commands in tools_to_check:
        for cmd in tool_commands:
            try:
                # 检查命令是否存在
                result = subprocess.run(
                    ['which', cmd] if not cmd.endswith('.exe') else ['where', cmd],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if result.returncode == 0:
                    # 命令存在，尝试获取版本信息
                    version_result = subprocess.run(
                        [cmd, '--version'] if '--version' in tool_name else [cmd, '-v'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    version_info = ""
                    if version_result.stdout:
                        version_info = version_result.stdout[:100].strip()
                    elif version_result.stderr:
                        version_info = version_result.stderr[:100].strip()
                    
                    # 根据工具类型设置能力描述
                    capabilities = {
                        'gpcl6': '专业PCL到PDF转换',
                        'pcl6': 'PCL6到PDF转换',
                        'gs': 'Ghostscript通用转换',
                        'pclmtoraster': 'PCL到光栅转换',
                        'pcltopdf': 'PCL到PDF转换',
                        'pcl2pdf': 'PCL到PDF转换',
                        'pdftopcl': 'PDF到PCL转换（反向）',
                        'rastertopclx': '光栅到PCL转换',
                        'commandtopclx': '命令到PCL转换',
                        'ippevepcl': 'IPP PCL转换'
                    }
                    
                    detected_tools.append({
                        'name': tool_name,
                        'command': cmd,
                        'path': result.stdout.strip(),
                        'version': version_info if version_info else 'Unknown version',
                        'capabilities': capabilities.get(tool_name, '未知功能'),
                        'status': '可用'
                    })
                    logger.info(f"检测到PCL工具: {tool_name} ({cmd}) - {capabilities.get(tool_name, '未知')}")
                    break
                    
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
            except Exception as e:
                logger.debug(f"检查工具 {tool_name} 失败: {str(e)}")
                continue
    
    # 如果没有检测到标准工具，尝试查找系统工具
    if not detected_tools:
        logger.info("未检测到标准PCL工具，尝试查找系统工具...")
        
        # 查找可能的转换工具
        search_paths = [
            '/usr/bin',
            '/usr/local/bin',
            '/usr/lib/cups/filter',
            '/usr/sbin',
            '/usr/lib/cups/backend',
            '/mnt/c/Program Files',
            '/mnt/c/Program Files (x86)'
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                try:
                    for root, dirs, files in os.walk(search_path):
                        for file in files:
                            if 'pcl' in file.lower() and any(ext in file.lower() for ext in ['.exe', '', '.bin', '.sh']):
                                tool_path = os.path.join(root, file)
                                try:
                                    if os.access(tool_path, os.X_OK):
                                        detected_tools.append({
                                            'name': file,
                                            'command': tool_path,
                                            'path': tool_path,
                                            'version': '系统工具',
                                            'capabilities': '未知PCL相关工具',
                                            'status': '可用'
                                        })
                                        logger.info(f"发现系统PCL工具: {file} ({tool_path})")
                                except:
                                    continue
                except:
                    continue
    
    # 检查hplip安装情况
    try:
        hplip_check = subprocess.run(['dpkg', '-s', 'hplip'], capture_output=True, text=True)
        if hplip_check.returncode == 0:
            logger.info("hplip已安装，HP工具包可用")
    except:
        pass
    
    return detected_tools

def get_best_pcl_tool(tools):
    """选择最佳的PCL转换工具"""
    if not tools:
        return None
    
    # 工具优先级
    tool_priority = ['gpcl6', 'pcl6', 'pcltopdf', 'pcl2pdf', 'gs', 'pclmtoraster']
    
    for priority_tool in tool_priority:
        for tool in tools:
            if tool['name'] == priority_tool:
                logger.info(f"选择工具: {tool['name']} (优先级: {priority_tool})")
                return tool
    
    # 如果没有优先级工具，返回第一个
    logger.info(f"选择工具: {tools[0]['name']} (第一个可用)")
    return tools[0]

def test_tool_conversion(tool_cmd, test_file_path):
    """测试工具转换能力"""
    if not os.path.exists(test_file_path):
        return False, "测试文件不存在"
    
    test_output = os.path.join('/tmp', f"test_output_{uuid.uuid4().hex}.pdf")
    
    try:
        # 根据工具类型构建命令
        if tool_cmd.endswith('gpcl6') or tool_cmd.endswith('gpcl6.exe'):
            cmd = [tool_cmd, '-sDEVICE=pdfwrite', '-dNOPAUSE', '-dBATCH', '-dSAFER',
                   f'-sOutputFile={test_output}', test_file_path]
        elif tool_cmd.endswith('pcl6') or tool_cmd.endswith('pcl6.exe'):
            cmd = [tool_cmd, '-sDEVICE=pdfwrite', '-dNOPAUSE', '-dBATCH', '-dSAFER',
                   f'-sOutputFile={test_output}', test_file_path]
        elif tool_cmd.endswith('gs') or tool_cmd.endswith('gswin') or tool_cmd.endswith('.exe'):
            # Ghostscript尝试PCL转换
            cmd = [tool_cmd, '-sDEVICE=pdfwrite', '-dNOPAUSE', '-dBATCH', '-dSAFER',
                   f'-sOutputFile={test_output}', test_file_path]
        else:
            # 默认命令格式
            cmd = [tool_cmd, test_file_path, test_output]
        
        logger.info(f"测试工具命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if os.path.exists(test_output):
            os.remove(test_output)
        
        if result.returncode == 0:
            return True, "工具测试成功"
        else:
            error_msg = f"工具测试失败 (返回码: {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr[:200]}"
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, "工具测试超时"
    except Exception as e:
        return False, f"工具测试异常: {str(e)}"

def convert_with_enhanced_tool(tool_info, input_path, output_path):
    """使用增强版工具进行转换"""
    start_time = time.time()
    tool_cmd = tool_info['command']
    tool_name = tool_info['name']
    
    try:
        # 构建命令
        if tool_name == 'gpcl6' or tool_name == 'pcl6':
            cmd = [
                tool_cmd,
                '-sDEVICE=pdfwrite',
                '-dNOPAUSE', '-dBATCH', '-dSAFER',
                '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/prepress',
                f'-sOutputFile={output_path}',
                input_path
            ]
        elif tool_name == 'gs':
            # Ghostscript - 尝试多种方法
            cmd = [
                tool_cmd,
                '-sDEVICE=pdfwrite',
                '-dNOPAUSE', '-dBATCH', '-dSAFER',
                '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/prepress',
                '-c', '.setpdfwrite',
                f'-sOutputFile={output_path}',
                input_path
            ]
        elif tool_name in ['pclmtoraster', 'rastertopclx', 'commandtopclx']:
            # HP工具链 - 可能需要多步转换
            # 先转换为中间格式，再转换为PDF
            intermediate = output_path.replace('.pdf', '.ps')
            cmd = [tool_cmd, input_path, intermediate]
        else:
            # 默认命令格式
            cmd = [tool_cmd, input_path, output_path]
        
        logger.info(f"执行转换命令: {' '.join(cmd)}")
        
        # 执行转换
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PCL_TOOL_TIMEOUT
        )
        
        duration = time.time() - start_time
        
        logger.info(f"转换完成 - 工具: {tool_name}, 耗时: {duration:.2f}s, 返回码: {result.returncode}")
        
        if result.stdout:
            logger.debug(f"工具输出: {result.stdout[:500]}")
        if result.stderr:
            logger.warning(f"工具错误: {result.stderr[:500]}")
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True, "转换成功", duration
            else:
                return False, "转换完成但输出文件为空或不存在", duration
        else:
            error_msg = f"转换失败 (返回码: {result.returncode})"
            if result.stderr:
                # 提取有用的错误信息
                stderr_lower = result.stderr.lower()
                if 'syntaxerror' in stderr_lower:
                    error_msg = "PCL语法错误 - 文件可能不是有效的PCL格式"
                elif 'unrecoverable error' in stderr_lower:
                    error_msg = "不可恢复的错误 - 文件可能损坏或不支持"
                elif 'not found' in stderr_lower:
                    error_msg = "命令未找到 - 请检查工具安装"
                else:
                    error_msg += f": {result.stderr[:200]}"
            return False, error_msg, duration
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return False, f"转换超时（{PCL_TOOL_TIMEOUT}秒）", duration
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"转换过程中发生异常: {str(e)}")
        return False, f"转换异常: {str(e)}", duration

# 路由定义
@app.route('/')
def index():
    """主页面 - 专业增强版界面"""
    tools = detect_pcl_tools_enhanced()
    stats = init_stats()
    
    # 计算今日统计
    today = datetime.now().strftime('%Y-%m-%d')
    today_stats = stats['daily_stats'].get(today, {'success': 0, 'fail': 0})
    
    return render_template('index_enhanced.html', 
                         tools=tools,
                         total_conversions=stats['total_conversions'],
                         success_rate=stats['successful_conversions'] / max(stats['total_conversions'], 1) * 100,
                         today_success=today_stats['success'],
                         today_fail=today_stats['fail'])

@app.route('/api/tools')
def get_tools():
    """获取工具信息API"""
    tools = detect_pcl_tools_enhanced()
    platform_info = {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture()[0]
    }
    
    return jsonify({
        'success': True,
        'tools': tools,
        'platform': platform_info,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/test-tools')
def test_tools():
    """测试工具转换能力"""
    test_file = "/mnt/c/workspace/sample/00000001.pcl"
    if not os.path.exists(test_file):
        return jsonify({
            'success': False,
            'error': '测试文件不存在',
            'test_file': test_file
        })
    
    tools = detect_pcl_tools_enhanced()
    test_results = []
    
    for tool in tools:
        success, message = test_tool_conversion(tool['command'], test_file)
        tool_result = tool.copy()
        tool_result['test_success'] = success
        tool_result['test_message'] = message
        test_results.append(tool_result)
    
    return jsonify({
        'success': True,
        'test_file': test_file,
        'test_file_exists': os.path.exists(test_file),
        'test_results': test_results,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/stats')
def get_stats():
    """获取转换统计"""
    stats = init_stats()
    
    # 计算平均转换时间
    avg_time = 0
    if stats['conversion_times']:
        avg_time = sum(stats['conversion_times']) / len(stats['conversion_times'])
    
    # 今日统计
    today = datetime.now().strftime('%Y-%m-%d')
    today_stats = stats['daily_stats'].get(today, {'success': 0, 'fail': 0})
    
    return jsonify({
        'success': True,
        'stats': {
            'total_conversions': stats['total_conversions'],
            'successful_conversions': stats['successful_conversions'],
            'failed_conversions': stats['failed_conversions'],
            'success_rate': stats['successful_conversions'] / max(stats['total_conversions'], 1) * 100,
            'avg_conversion_time': avg_time,
            'today_success': today_stats['success'],
            'today_fail': today_stats['fail'],
            'tool_usage': stats['tool_usage'],
            'last_reset': stats['last_reset']
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传和转换 - 增强版"""
    start_time = time.time()
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': '未选择文件',
            'suggestion': '请选择.pcl文件进行上传'
        })
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': '未选择文件',
            'suggestion': '请选择.pcl文件进行上传'
        })
    
    # 验证文件类型
    if not file.filename.lower().endswith('.pcl'):
        return jsonify({
            'success': False,
            'error': '只支持.pcl文件',
            'suggestion': '请确保文件扩展名为.pcl'
        })
    
    # 验证文件大小
    if file.size > app.config['MAX_CONTENT_LENGTH']:
        max_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
        return jsonify({
            'success': False,
            'error': f'文件太大（最大{max_mb}MB）',
            'suggestion': '请压缩文件或选择较小的文件'
        })
    
    # 保存上传的文件
    filename = secure_filename(file.filename)
    file_hash = hashlib.md5(f"{filename}_{datetime.now().timestamp()}".encode()).hexdigest()[:8]
    unique_filename = f"{file_hash}_{filename}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    try:
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)
        logger.info(f"文件已上传: {filename} -> {upload_path} ({file_size} bytes)")
        
        # 检测可用工具
        tools = detect_pcl_tools_enhanced()
        if not tools:
            os.remove(upload_path)
            return jsonify({
                'success': False,
                'error': '未检测到可用的PCL转换工具',
                'suggestion': '请安装GhostPCL、pcltopdf或相关PCL转换工具'
            })
        
        # 选择最佳工具
        best_tool = get_best_pcl_tool(tools)
        logger.info(f"选择转换工具: {best_tool['name']} ({best_tool['command']})")
        
        # 准备输出文件
        output_filename = f"{os.path.splitext(filename)[0]}_{file_hash}.pdf"
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
        
        # 执行转换
        success, message, duration = convert_with_enhanced_tool(best_tool, upload_path, output_path)
        
        # 更新统计
        update_stats(success, duration, best_tool['name'])
        
        if success:
            # 转换成功
            final_size = os.path.getsize(output_path)
            
            # 记录转换详情
            conversion_log = {
                'timestamp': datetime.now().isoformat(),
                'original_file': filename,
                'original_size': file_size,
                'converted_file': output_filename,
                'converted_size': final_size,
                'tool_used': best_tool['name'],
                'duration': duration,
                'success': True
            }
            logger.info(f"转换成功: {conversion_log}")
            
            # 清理上传的文件（保留转换后的文件）
            if os.path.exists(upload_path):
                os.remove(upload_path)
            
            return jsonify({
                'success': True,
                'message': '转换成功',
                'original_filename': filename,
                'converted_filename': output_filename,
                'file_size': final_size,
                'download_url': f'/download/{output_filename}',
                'tool_used': best_tool['name'],
                'duration': f'{duration:.2f}s',
                'details': {
                    'tool_name': best_tool['name'],
                    'tool_version': best_tool['version'],
                    'conversion_time': duration
                }
            })
        else:
            # 转换失败
            logger.error(f"转换失败: {filename} - {message}")
            
            # 提供具体的修复建议
            suggestion = get_conversion_suggestion(message, best_tool['name'])
            
            # 清理文件
            if os.path.exists(upload_path):
                os.remove(upload_path)
            if os.path.exists(output_path):
                os.remove(output_path)
            
            return jsonify({
                'success': False,
                'error': message,
                'suggestion': suggestion,
                'tool_used': best_tool['name'],
                'duration': f'{duration:.2f}s',
                'details': {
                    'tool_name': best_tool['name'],
                    'error_type': 'conversion_failed'
                }
            })
            
    except Exception as e:
        logger.exception(f"处理文件时发生异常: {str(e)}")
        
        # 清理文件
        if os.path.exists(upload_path):
            os.remove(upload_path)
        
        return jsonify({
            'success': False,
            'error': f'处理文件时发生异常: {str(e)}',
            'suggestion': '请检查文件格式或联系技术支持',
            'details': {
                'error_type': 'system_exception',
                'traceback': traceback.format_exc()[:500] if app.debug else '已隐藏'
            }
        })

def get_conversion_suggestion(error_message, tool_name):
    """根据错误信息提供修复建议"""
    error_lower = error_message.lower()
    
    if 'syntaxerror' in error_lower:
        return "PCL语法错误：文件可能不是有效的PCL格式，请验证文件完整性"
    elif 'not found' in error_lower or 'command not found' in error_lower:
        return f"工具未找到：请确保{tool_name}已正确安装并添加到系统PATH"
    elif 'unrecoverable error' in error_lower:
        return "不可恢复的错误：文件可能损坏或包含不支持的PCL命令"
    elif 'timeout' in error_lower:
        return "转换超时：文件可能过大或复杂，请尝试较小的文件"
    elif '空或不存在' in error_lower:
        return "输出文件为空：转换工具可能无法处理该PCL格式"
    elif tool_name == 'gs' and 'error' in error_lower:
        return "Ghostscript无法直接解析PCL：请安装专门的PCL转换工具如GhostPCL"
    else:
        return "转换失败：请检查文件格式，或尝试使用其他PCL转换工具"

@app.route('/download/<filename>')
def download_file(filename):
    """下载转换后的PDF文件"""
    file_path = os.path.join(app.config['CONVERTED_FOLDER'], secure_filename(filename))
    if not os.path.exists(file_path):
        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404
    
    try:
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'下载失败: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """健康检查端点 - 增强版"""
    tools = detect_pcl_tools_enhanced()
    stats = init_stats()
    
    # 检查目录权限
    dir_checks = {}
    for folder_name, folder_path in [
        ('uploads', app.config['UPLOAD_FOLDER']),
        ('converted', app.config['CONVERTED_FOLDER']),
        ('logs', 'logs')
    ]:
        try:
            test_file = os.path.join(folder_path, f"test_{uuid.uuid4().hex}.tmp")
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            dir_checks[folder_name] = {'writable': True}
        except Exception as e:
            dir_checks[folder_name] = {'writable': False, 'error': str(e)}
    
    # 检查测试文件
    test_file = "/mnt/c/workspace/sample/00000001.pcl"
    test_file_exists = os.path.exists(test_file)
    
    return jsonify({
        'status': 'healthy',
        'service': 'pcl-converter-enhanced',
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'python': platform.python_version()
        },
        'tools': {
            'available': len(tools),
            'list': [t['name'] for t in tools]
        },
        'directories': dir_checks,
        'test_file': {
            'path': test_file,
            'exists': test_file_exists,
            'size': os.path.getsize(test_file) if test_file_exists else 0
        },
        'statistics': {
            'total_conversions': stats['total_conversions'],
            'success_rate': stats['successful_conversions'] / max(stats['total_conversions'], 1) * 100
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/reset-stats', methods=['POST'])
def reset_stats():
    """重置统计信息（需要认证）"""
    # 简单认证检查
    auth_token = request.headers.get('X-Auth-Token')
    if auth_token != os.environ.get('ADMIN_TOKEN', 'dev-admin-token'):
        return jsonify({'success': False, 'error': '未授权'}), 401
    
    stats = init_stats()
    old_stats = stats.copy()
    
    # 重置统计
    stats['total_conversions'] = 0
    stats['successful_conversions'] = 0
    stats['failed_conversions'] = 0
    stats['conversion_times'] = []
    stats['daily_stats'] = {}
    stats['tool_usage'] = {}
    stats['last_reset'] = datetime.now().isoformat()
    
    save_stats(stats)
    
    logger.info(f"统计已重置，旧统计: {old_stats}")
    return jsonify({
        'success': True,
        'message': '统计已重置',
        'old_stats': old_stats,
        'new_stats': stats
    })

if __name__ == '__main__':
    # 显示启动信息
    logger.info("=" * 70)
    logger.info("PCL转PDF专业转换器 - 增强版")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"平台: {platform.system()} {platform.release()}")
    logger.info(f"Python: {sys.version}")
    
    # 检测工具
    tools = detect_pcl_tools_enhanced()
    if tools:
        logger.info(f"检测到 {len(tools)} 个PCL转换工具:")
        for tool in tools:
            logger.info(f"  • {tool['name']}: {tool['command']} ({tool['capabilities']})")
    else:
        logger.warning("⚠️ 未检测到PCL转换工具，转换功能将不可用")
        logger.info("💡 建议安装以下工具:")
        logger.info("  • GhostPCL (推荐): 专业PCL转换工具")
        logger.info("  • pcltopdf: 开源PCL转换工具")
        logger.info("  • HP工具链: hplip软件包提供")
    
    # 显示统计
    stats = init_stats()
    logger.info(f"历史统计: {stats['total_conversions']} 次转换，成功率: {stats['successful_conversions'] / max(stats['total_conversions'], 1) * 100:.1f}%")
    
    logger.info("=" * 70)
    logger.info(f"🌐 应用地址: http://localhost:5000")
    logger.info(f"📊 健康检查: http://localhost:5000/health")
    logger.info(f"🔧 工具检测: http://localhost:5000/api/tools")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=False)