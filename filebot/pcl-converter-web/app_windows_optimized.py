"""
PCL转PDF转换器 - Windows原生优化版
专为Windows环境设计，使用PageTech PCLTSDK进行快速转换
"""

import os
import sys
import platform
import subprocess
import requests
import time
import logging
import uuid
import tempfile
import shutil
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建必要的目录
logs_dir = 'logs'
uploads_dir = 'uploads'
converted_dir = 'converted'
os.makedirs(logs_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(converted_dir, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 配置
PCL_TOOL_TIMEOUT = 60  # 转换超时时间（秒）
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.pcl', '.tiff', '.tif', '.jpg', '.jpeg', '.png', '.txt', '.text'}

def to_windows_path_if_wsl(path):
    """
    将WSL/Linux路径转换为Windows路径
    
    支持以下路径格式：
    1. WSL /mnt/ 挂载点: /mnt/c/Users/... -> C:\\Users\\...
    2. WSL /drive/ 格式: /c/Users/... -> C:\\Users\\...
    3. Linux用户目录: ~/ 或 /home/user/... -> C:\\Users\\用户名\\...
    4. 网络路径: //server/share -> \\\\server\\share
    5. 相对路径: 保持原样或转换为绝对路径
    6. 符号链接: 解析为实际路径
    
    参数:
        path (str): 输入路径
    
    返回:
        str: Windows格式路径
    """
    if not path:
        return path
    
    # 展开用户主目录 (~/ -> /home/user/)
    expanded_path = os.path.expanduser(path)
    
    # 解析符号链接（获取实际路径）
    real_path = os.path.realpath(expanded_path) if os.path.exists(expanded_path) else expanded_path
    
    # 处理网络路径 (UNC格式)
    if real_path.startswith('//') or real_path.startswith('\\\\'):
        # 已经是网络路径，统一为Windows格式
        return real_path.replace('/', '\\')
    
    # 检查是否是Windows路径 (已经包含驱动器字母)
    if len(real_path) > 1 and real_path[1] == ':' and real_path[0].isalpha():
        # 已经是Windows路径，确保使用反斜杠
        return real_path.replace('/', '\\')
    
    # 处理WSL /mnt/ 挂载点格式
    if real_path.startswith('/mnt/'):
        if real_path.startswith('/mnt/c/'):
            # /mnt/c/Users/... -> C:\\Users\\...
            # 确保路径部分有反斜杠分隔符
            path_part = real_path[6:]
            if path_part.startswith('/'):
                path_part = path_part[1:]
            win_path = 'C:\\' + path_part.replace('/', '\\')
            return win_path
        elif len(real_path) > 5 and real_path[5].isalpha():
            # /mnt/d/... -> D:\\...
            drive = real_path[5].upper()
            # 获取路径部分（跳过 /mnt/d/ 中的最后一个斜杠）
            path_part = real_path[7:] if len(real_path) > 7 else ''
            if path_part.startswith('/'):
                path_part = path_part[1:]
            win_path = f'{drive}:\\' + path_part.replace('/', '\\')
            return win_path
    
    # 处理WSL /drive/ 格式 (如 /c/Users/...)
    if len(real_path) > 1 and real_path.startswith('/') and real_path[1].isalpha() and real_path[2] == '/':
        drive = real_path[1].upper()
        # 获取路径部分（跳过 /c/ 后的斜杠）
        path_part = real_path[3:]
        if path_part.startswith('/'):
            path_part = path_part[1:]
        win_path = f'{drive}:\\' + path_part.replace('/', '\\')
        return win_path
    
    # 处理Linux用户目录 (/home/user/...)
    # 尝试映射到Windows用户目录
    if real_path.startswith('/home/'):
        # 提取用户名
        parts = real_path.split('/')
        if len(parts) >= 3:
            username = parts[2]
            # 映射到Windows用户目录
            # 注意：这是简化的映射，实际映射可能更复杂
            remaining_path = '/'.join(parts[3:]) if len(parts) > 3 else ''
            # 构建Windows路径
            if remaining_path:
                # C:\Users\username\remaining_path
                win_path = f'C:\\Users\\{username}\\{remaining_path.replace("/", "\\")}'
            else:
                win_path = f'C:\\Users\\{username}'
            return win_path
    
    # 处理根目录路径
    if real_path.startswith('/'):
        # 其他Linux绝对路径，默认映射到C盘根目录
        # 注意：这假设所有Linux根目录路径映射到C:\
        path_part = real_path[1:]  # 移除开头的斜杠
        if path_part:
            win_path = f'C:\\{path_part.replace("/", "\\")}'
        else:
            win_path = 'C:\\'
        return win_path
    
    # 相对路径或无法识别的格式，保持原样
    # 注意：相对路径在Windows环境下可能有问题，但保持原样让调用方处理
    return path

# FileBot API配置
FILEBOT_API_URL = os.environ.get('FILEBOT_API_URL', 'http://localhost:8001/api/v1')
FILEBOT_USERNAME = os.environ.get('FILEBOT_USERNAME', 'admin')
FILEBOT_PASSWORD = os.environ.get('FILEBOT_PASSWORD', 'admin123')
USE_FILEBOT_API = os.environ.get('USE_FILEBOT_API', 'true').lower() == 'true'

# Windows特定路径配置
PCL_TOOL_PATHS = [
    r'C:\Program Files (x86)\PageTech\PCLTSDK_870\PclXform.exe',
    r'C:\Program Files (x86)\PageTech\PCLTSDK_870\PCLTOOL.exe',
    r'C:\workspace\PCLTSDK_870\PclXform.exe',
    r'C:\workspace\PCLTSDK_870\PCLTOOL.exe',
    # WSL路径
    r'/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe',
    r'/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PCLTOOL.exe',
    r'/mnt/c/workspace/PCLTSDK_870/PclXform.exe',
    r'/mnt/c/workspace/PCLTSDK_870/PCLTOOL.exe',
]

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def detect_pcl_tools():
    """检测系统中可用的PCL转换工具"""
    available_tools = []
    
    for tool_path in PCL_TOOL_PATHS:
        if os.path.exists(tool_path):
            tool_name = os.path.basename(tool_path)
            if 'pclxform' in tool_name.lower():
                available_tools.append({
                    'name': 'pclxform',
                    'path': tool_path,
                    'display_name': 'PageTech PCLTSDK (PclXform.exe)'
                })
            elif 'pcltool' in tool_name.lower():
                available_tools.append({
                    'name': 'pcltool',
                    'path': tool_path,
                    'display_name': 'PageTech PCLTSDK (PCLTOOL.exe)'
                })
            else:
                available_tools.append({
                    'name': tool_name.lower().replace('.exe', ''),
                    'path': tool_path,
                    'display_name': tool_name
                })
    
    logger.info(f"检测到PCL工具: {[tool['name'] for tool in available_tools]}")
    return available_tools

def select_best_tool(available_tools):
    """选择最佳的PCL转换工具"""
    if not available_tools:
        return None
    
    # 优先选择pclxform
    for tool in available_tools:
        if tool['name'] == 'pclxform':
            logger.info(f"自动选择PCL工具: {tool['display_name']}")
            return tool
    
    # 其次选择pcltool
    for tool in available_tools:
        if tool['name'] == 'pcltool':
            logger.info(f"自动选择PCL工具: {tool['display_name']}")
            return tool
    
    # 否则选择第一个可用工具
    selected = available_tools[0]
    logger.info(f"自动选择PCL工具: {selected['display_name']}")
    return selected

def convert_with_pclxform(tool_cmd, input_path, output_path):
    """使用PclXform.exe转换PCL文件（Windows原生版本）"""
    try:
        # 检查文件扩展名，仅支持.pcl文件
        if not input_path.lower().endswith('.pcl'):
            return False, "只支持.pcl文件"
        
        # 构建Windows原生命令（用户验证的格式）
        # 注意：根据用户测试，PclXform.exe的参数语义是：
        # inp=输入目录, inf=输入文件名, outp=输出目录, outf=输出文件名
        # 这与通常的命名直觉相反！
        # 格式: PclXform.exe "default.tpt" inp="目录" inf="文件名" outp="目录" outf="文件名"
        
        # 获取输入输出目录和文件名
        input_dir = os.path.dirname(input_path)
        input_file = os.path.basename(input_path)
        output_dir = os.path.dirname(output_path)
        output_file = os.path.basename(output_path)
        
        # 模板路径
        tool_dir = os.path.dirname(tool_cmd)
        template_path = os.path.join(tool_dir, 'default.tpt')
        
        # 转换路径为Windows格式（如果工具路径是Windows路径）
        tool_cmd_win = to_windows_path_if_wsl(tool_cmd)
        template_path_win = to_windows_path_if_wsl(template_path)
        input_dir_win = to_windows_path_if_wsl(input_dir)
        output_dir_win = to_windows_path_if_wsl(output_dir)
        tool_dir_win = to_windows_path_if_wsl(tool_dir)
        
        # 构建完整DOS命令（根据用户验证的正确格式）
        # 添加Silent=true以避免GUI窗口
        dos_command = f'cd /d "{tool_dir_win}" && "{tool_cmd_win}" "{template_path_win}" inp="{input_dir_win}" inf="{input_file}" outp="{output_dir_win}" outf="{output_file}" Silent=true'
        
        # 根据平台选择执行方式
        if platform.system() == 'Windows':
            # Windows: 通过cmd运行
            cmd = ['cmd', '/c', dos_command]
        else:
            # Linux/WSL: 通过cmd运行Windows可执行文件
            # 使用cmd /c包装，确保GUI程序在WSL中正常执行
            cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]
        
        logger.info(f"执行转换命令: {' '.join(cmd)}")
        

        
        # 执行转换
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PCL_TOOL_TIMEOUT
        )
        
        logger.info(f"转换返回码: {result.returncode}")
        if result.stdout:
            logger.debug(f"转换输出: {result.stdout[:500]}")
        if result.stderr:
            logger.warning(f"转换错误: {result.stderr[:500]}")
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True, "转换成功"
            else:
                # 检查工具目录中是否有生成的PDF文件
                tool_dir_output = os.path.join(tool_dir, output_file)
                if os.path.exists(tool_dir_output) and os.path.getsize(tool_dir_output) > 0:
                    # 将文件移动到目标目录
                    os.rename(tool_dir_output, output_path)
                    logger.info(f"从工具目录移动文件: {tool_dir_output} -> {output_path}")
                    return True, "转换成功"
                else:
                    return False, "转换完成但输出文件为空或不存在"
        else:
            error_msg = f"转换失败 (返回码: {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr[:200]}"
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, f"转换超时（{PCL_TOOL_TIMEOUT}秒）"
    except Exception as e:
        return False, f"转换过程中发生错误: {str(e)}"

def convert_with_tool(tool_cmd, input_path, output_path):
    """使用指定工具转换PCL文件"""
    tool_name = os.path.basename(tool_cmd).lower()
    
    if 'pclxform' in tool_name or 'pcltool' in tool_name:
        return convert_with_pclxform(tool_cmd, input_path, output_path)
    else:
        # 其他工具使用默认命令格式
        cmd = [tool_cmd, input_path, output_path]
        
        logger.info(f"执行转换命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PCL_TOOL_TIMEOUT
        )
        
        logger.info(f"转换返回码: {result.returncode}")
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True, "转换成功"
            else:
                return False, "转换完成但输出文件为空或不存在"
        else:
            error_msg = f"转换失败 (返回码: {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr[:200]}"
            return False, error_msg

def convert_image_to_pdf(input_path, output_path):
    """使用Ghostscript将图像文件转换为PDF"""
    try:
        # 检查Ghostscript是否可用
        gs_path = shutil.which('gs')
        if not gs_path:
            return False, "Ghostscript未安装"
        
        # Ghostscript命令：将图像转换为PDF
        # -sDEVICE=pdfwrite 输出PDF
        # -dNOPAUSE -dBATCH 非交互式处理
        # -dSAFER 安全模式
        # -sOutputFile=输出文件 输出路径
        cmd = [
            gs_path,
            '-sDEVICE=pdfwrite',
            '-dNOPAUSE',
            '-dBATCH',
            '-dSAFER',
            f'-sOutputFile={output_path}',
            input_path
        ]
        
        logger.info(f"执行Ghostscript命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PCL_TOOL_TIMEOUT
        )
        
        logger.info(f"Ghostscript返回码: {result.returncode}")
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True, "图像转换成功"
            else:
                return False, "转换完成但输出文件为空"
        else:
            error_msg = f"图像转换失败 (返回码: {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr[:200]}"
            return False, error_msg
            
    except Exception as e:
        return False, f"图像转换过程中发生错误: {str(e)}"

def convert_text_to_pdf(input_path, output_path):
    """将文本文件转换为PDF（简单实现）"""
    try:
        import shutil
        
        # 检查是否安装了enscript或pandoc
        enscript_path = shutil.which('enscript')
        if enscript_path:
            # 使用enscript将文本转换为PostScript，再转换为PDF
            # 先创建PostScript中间文件
            with tempfile.NamedTemporaryFile(suffix='.ps', delete=False) as tmp_ps:
                ps_path = tmp_ps.name
            
            # enscript命令：将文本转换为PostScript
            enscript_cmd = [
                enscript_path,
                '-B',  # 不显示页眉
                '-o', ps_path,
                input_path
            ]
            
            logger.info(f"执行enscript命令: {' '.join(enscript_cmd)}")
            
            result = subprocess.run(
                enscript_cmd,
                capture_output=True,
                text=True,
                timeout=PCL_TOOL_TIMEOUT
            )
            
            if result.returncode != 0:
                os.unlink(ps_path)
                return False, f"enscript文本转换失败: {result.stderr[:200] if result.stderr else '未知错误'}"
            
            # 使用Ghostscript将PostScript转换为PDF
            gs_path = shutil.which('gs')
            if not gs_path:
                os.unlink(ps_path)
                return False, "Ghostscript未安装"
            
            gs_cmd = [
                gs_path,
                '-sDEVICE=pdfwrite',
                '-dNOPAUSE',
                '-dBATCH',
                '-dSAFER',
                f'-sOutputFile={output_path}',
                ps_path
            ]
            
            logger.info(f"执行Ghostscript命令: {' '.join(gs_cmd)}")
            
            result = subprocess.run(
                gs_cmd,
                capture_output=True,
                text=True,
                timeout=PCL_TOOL_TIMEOUT
            )
            
            # 清理临时文件
            os.unlink(ps_path)
            
            if result.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True, "文本转换成功"
                else:
                    return False, "转换完成但输出文件为空"
            else:
                error_msg = f"文本转换失败 (返回码: {result.returncode})"
                if result.stderr:
                    error_msg += f": {result.stderr[:200]}"
                return False, error_msg
        else:
            # 如果没有enscript，使用简单的Python实现
            # 使用reportlab如果可用，否则创建简单的文本PDF
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                
                c = canvas.Canvas(output_path, pagesize=letter)
                width, height = letter
                
                # 读取文本文件
                with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                
                # 简单文本渲染
                text_lines = text.split('\n')
                y = height - 40
                for line in text_lines[:100]:  # 限制行数
                    if y < 40:
                        c.showPage()
                        y = height - 40
                    c.drawString(40, y, line[:100])  # 限制每行长度
                    y -= 15
                
                c.save()
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True, "文本转换成功（使用reportlab）"
                else:
                    return False, "文本转换失败，输出文件为空"
                    
            except ImportError:
                # reportlab不可用，创建最简单的PDF
                # 使用Ghostscript直接创建空PDF并添加文本（复杂）
                # 暂时返回错误
                return False, "文本转换需要安装enscript或reportlab"
                
    except Exception as e:
        return False, f"文本转换过程中发生错误: {str(e)}"

def convert_file(input_path, output_path):
    """根据文件类型调用适当的转换函数"""
    file_ext = Path(input_path).suffix.lower()
    
    # PCL文件使用PCL工具
    if file_ext == '.pcl':
        # 检测可用工具
        available_tools = detect_pcl_tools()
        if not available_tools:
            return False, "未找到可用的PCL转换工具"
        
        # 选择最佳工具
        selected_tool = select_best_tool(available_tools)
        return convert_with_tool(selected_tool['path'], input_path, output_path)
    
    # 图像文件
    elif file_ext in ['.tiff', '.tif', '.jpg', '.jpeg', '.png']:
        return convert_image_to_pdf(input_path, output_path)
    
    # 文本文件
    elif file_ext in ['.txt', '.text']:
        return convert_text_to_pdf(input_path, output_path)
    
    else:
        return False, f"不支持的文件类型: {file_ext}"

def get_filebot_token():
    """获取FileBot API访问令牌"""
    if not USE_FILEBOT_API:
        return None
    
    try:
        login_url = f"{FILEBOT_API_URL}/auth/login"
        response = requests.post(
            login_url,
            data={'username': FILEBOT_USERNAME, 'password': FILEBOT_PASSWORD},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        if response.status_code == 200:
            token = response.json().get('access_token')
            logger.info("成功获取FileBot API令牌")
            return token
        else:
            logger.error(f"FileBot登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"获取FileBot令牌失败: {str(e)}")
        return None

def upload_to_filebot(file_path, original_filename):
    """上传文件到FileBot API"""
    if not USE_FILEBOT_API:
        return None, "FileBot API未启用"
    
    try:
        token = get_filebot_token()
        if not token:
            return None, "无法获取FileBot访问令牌"
        
        upload_url = f"{FILEBOT_API_URL}/conversion/convert"
        
        with open(file_path, 'rb') as f:
            files = {'file': (original_filename, f)}
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.post(
                upload_url,
                files=files,
                headers=headers,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"FileBot API上传成功: {result}")
            return result, "上传成功"
        else:
            logger.error(f"FileBot API上传失败: {response.status_code} - {response.text}")
            return None, f"FileBot API上传失败: {response.status_code}"
            
    except Exception as e:
        logger.error(f"上传到FileBot失败: {str(e)}")
        return None, f"上传到FileBot失败: {str(e)}"

@app.route('/')
def index():
    """首页 - 文件上传界面"""
    available_tools = detect_pcl_tools()
    
    return render_template('index.html',
                         available_tools=available_tools,
                         use_filebot=USE_FILEBOT_API)

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传和转换"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未选择文件'})
        
        file = request.files['file']
        
        # 检查文件是否为空
        if file.filename == '':
            return jsonify({'success': False, 'error': '未选择文件'})
        
        # 检查文件扩展名
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': f'不支持的文件类型。支持格式: {", ".join([ext.lstrip(".") for ext in ALLOWED_EXTENSIONS])}'})
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': f'文件过大（最大{MAX_FILE_SIZE // (1024*1024)}MB）'})
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4().hex)[:16]
        safe_filename = f"{file_id}_{original_filename}"
        
        # 保存上传的文件
        upload_path = os.path.join('uploads', safe_filename)
        file.save(upload_path)
        
        logger.info(f"文件已上传: {original_filename} -> {upload_path}")
        
        # 生成输出文件路径
        output_filename = Path(original_filename).stem + '.pdf'
        output_path = os.path.join('converted', f"{file_id}_{output_filename}")
        
        # 执行转换
        success, message = convert_file(upload_path, output_path)
        
        if success:
            # 如果启用了FileBot API，上传转换后的文件
            if USE_FILEBOT_API:
                filebot_result, filebot_msg = upload_to_filebot(output_path, output_filename)
                if filebot_result:
                    return jsonify({
                        'success': True,
                        'message': f'转换成功并已上传到FileBot',
                        'original_filename': original_filename,
                        'converted_filename': output_filename,
                        'filebot_result': filebot_result
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': f'转换成功，但上传到FileBot失败: {filebot_msg}',
                        'original_filename': original_filename,
                        'converted_filename': output_filename,
                        'warning': f'FileBot上传失败: {filebot_msg}'
                    })
            else:
                return jsonify({
                    'success': True,
                    'message': '转换成功',
                    'original_filename': original_filename,
                    'converted_filename': output_filename,
                    'download_url': f'/download/{Path(output_path).name}'
                })
        else:
            return jsonify({
                'success': False,
                'error': f'{original_filename} - {message}',
                'suggestion': '请检查PCL转换工具是否已正确安装'
            })
            
    except Exception as e:
        logger.error(f"上传处理失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理失败: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    """下载转换后的文件"""
    try:
        file_path = os.path.join('converted', filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return jsonify({'success': False, 'error': f'下载失败: {str(e)}'})

@app.route('/health')
def health_check():
    """健康检查端点"""
    available_tools = detect_pcl_tools()
    
    return jsonify({
        'status': 'healthy',
        'platform': platform.system(),
        'available_tools': [tool['name'] for tool in available_tools],
        'supported_formats': [ext.lstrip('.') for ext in ALLOWED_EXTENSIONS],
        'upload_folder': 'uploads',
        'converted_folder': 'converted',
        'use_filebot': USE_FILEBOT_API,
        'filebot_api_url': FILEBOT_API_URL if USE_FILEBOT_API else None
    })

@app.route('/api/tools')
def api_tools():
    """获取可用工具列表"""
    available_tools = detect_pcl_tools()
    return jsonify(available_tools)

if __name__ == '__main__':
    # 创建Windows专用的目录结构
    windows_upload_dir = r'C:\workspace\pcl-uploads'
    windows_converted_dir = r'C:\workspace\pcl-converted'
    
    os.makedirs(windows_upload_dir, exist_ok=True)
    os.makedirs(windows_converted_dir, exist_ok=True)
    
    # 检查是否已安装Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
        logger.error(f"Python版本过低: {sys.version}. 需要Python 3.9+")
        print(f"错误: Python版本过低: {sys.version}. 需要Python 3.9+")
        print("请从 https://www.python.org/downloads/ 下载Python 3.9+")
        sys.exit(1)
    
    # 检测PCL工具
    available_tools = detect_pcl_tools()
    if not available_tools:
        logger.warning("未找到PCL转换工具，请确保PageTech PCLTSDK已安装")
        print("警告: 未找到PCL转换工具")
        print("请确保PageTech PCLTSDK已安装到以下位置之一:")
        for path in PCL_TOOL_PATHS:
            print(f"  - {path}")
    
    print("=" * 50)
    print("PCL转PDF转换器 - Windows原生优化版")
    print(f"平台: {platform.system()} {platform.release()}")
    print(f"Python版本: {sys.version}")
    print(f"可用工具: {[tool['name'] for tool in available_tools]}")
    print(f"上传目录: {windows_upload_dir}")
    print(f"转换目录: {windows_converted_dir}")
    print(f"FileBot API: {'已启用' if USE_FILEBOT_API else '已禁用'}")
    print("=" * 50)
    print("访问地址: http://localhost:5000")
    print("健康检查: http://localhost:5000/health")
    print("按Ctrl+C停止应用")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)