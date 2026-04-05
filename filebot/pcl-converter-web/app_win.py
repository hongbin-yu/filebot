"""
PCL to PDF Converter Web Application - Windows优化版
支持Windows环境下的多种PCL转换工具

功能：
1. 文件上传界面（支持.pcl文件）
2. 支持多种PCL转换工具：GhostPCL (gpcl6), PCL6, pcltopdf等
3. 显示转换进度和状态
4. 提供结果PDF下载
5. Windows环境优化
"""

import os
import sys
import platform
import subprocess
import requests
import time
import logging
import uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建必要的目录（必须在日志初始化之前）
import os
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

# 基础配置
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_MB', 100)) * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/mnt/c/workspace/pcl-uploads')
app.config['CONVERTED_FOLDER'] = os.environ.get('CONVERTED_FOLDER', '/mnt/c/workspace/pcl-converted')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# PCL工具配置
PCL_TOOL_PATH = os.environ.get('PCL_TOOL_PATH', 'auto')
PCL_TOOL_TIMEOUT = int(os.environ.get('PCL_TOOL_TIMEOUT', 60))

# FileBot后端API配置（可选）
FILEBOT_API_URL = os.environ.get('FILEBOT_API_URL', 'http://localhost:8000/api/v1')
FILEBOT_USERNAME = os.environ.get('FILEBOT_USERNAME', 'admin')
FILEBOT_PASSWORD = os.environ.get('FILEBOT_PASSWORD', 'admin123')
USE_FILEBOT_API = os.environ.get('USE_FILEBOT_API', 'false').lower() == 'true'

# 确保目录存在
for folder in [app.config['UPLOAD_FOLDER'], app.config['CONVERTED_FOLDER'], 'logs']:
    os.makedirs(folder, exist_ok=True)

def detect_pcl_tool():
    """检测系统中可用的PCL转换工具"""
    tools_to_check = [
        ('gpcl6', ['gpcl6', 'gpcl6.exe'], True),  # GhostPCL - 命令行工具，尝试运行
        ('pcl6', ['pcl6', 'pcl6.exe'], True),      # PCL6 - 命令行工具，尝试运行
        ('pcltopdf', ['pcltopdf', 'pcltopdf.exe'], True),  # pcltopdf - 命令行工具
        ('pcl2pdf', ['pcl2pdf', 'pcl2pdf.exe'], True),     # 其他变体 - 命令行工具
        ('pagetech', ['pagetech', 'pagetech.exe', 'pagetechcmd', 'pagetechcmd.exe'], True),  # Pagetech command line
        # PageTech PCLTSDK工具（用户提供的路径）- Windows GUI工具，只检查文件存在
        ('pclxform', [
            '/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe',  # 用户确认的新路径（工作正常）
            '/mnt/c/workspace/PageTech/PCLTSDK_870/PclXform.exe',  # 之前的路径
            '/mnt/c/workspace/PCLTSDK_870/PclXform.exe',  # 原始测试路径（旧）
            'C:\\Program Files (x86)\\PageTech\\PCLTSDK_870\\PclXform.exe',
            'C:\\workspace\\PageTech\\PCLTSDK_870\\PclXform.exe', 
            'C:\\workspace\\PCLTSDK_870\\PclXform.exe',  # 旧路径
            'PclXform.exe'
        ], False),
        ('pcltool', [
            '/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PCLTOOL.exe',  # 用户确认的新路径
            '/mnt/c/workspace/PageTech/PCLTSDK_870/PCLTOOL.exe',  # 之前的路径
            '/mnt/c/workspace/PCLTSDK_870/PCLTOOL.exe',  # 原始测试路径（旧）
            'C:\\Program Files (x86)\\PageTech\\PCLTSDK_870\\PCLTOOL.exe',
            'C:\\workspace\\PageTech\\PCLTSDK_870\\PCLTOOL.exe',
            'C:\\workspace\\PCLTSDK_870\\PCLTOOL.exe',  # 旧路径
            'PCLTOOL.exe'
        ], False),
    ]
    
    detected_tools = []
    
    for tool_name, tool_commands, is_cli_tool in tools_to_check:
        for cmd in tool_commands:
            try:
                if is_cli_tool:
                    # 命令行工具：尝试运行获取版本信息
                    result = subprocess.run(
                        [cmd, '--version'] if '--version' in tool_name else [cmd],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 or result.returncode == 1:  # 很多工具返回1显示帮助
                        detected_tools.append({
                            'name': tool_name,
                            'command': cmd,
                            'version': result.stdout[:100] if result.stdout else 'Unknown version',
                            'type': 'cli'
                        })
                        logger.info(f"检测到PCL命令行工具: {tool_name} ({cmd})")
                        break
                else:
                    # GUI工具或已知工具：只检查文件是否存在
                    # 检查路径是否存在（支持WSL路径转换）
                    import os
                    if cmd.startswith('/mnt/c/'):
                        # WSL路径，检查文件是否存在
                        if os.path.exists(cmd):
                            detected_tools.append({
                                'name': tool_name,
                                'command': cmd,
                                'version': 'Windows GUI工具 (只检查文件存在)',
                                'type': 'gui'
                            })
                            logger.info(f"检测到PCL GUI工具（文件存在）: {tool_name} ({cmd})")
                            break
                    else:
                        # Windows路径，在WSL中可能无法直接访问，但可以检查/mnt/c/对应路径
                        # 尝试转换为WSL路径
                        if cmd.startswith('C:\\'):
                            wsl_path = '/mnt/c/' + cmd[3:].replace('\\', '/')
                            if os.path.exists(wsl_path):
                                detected_tools.append({
                                    'name': tool_name,
                                    'command': wsl_path,  # 使用WSL路径
                                    'version': 'Windows GUI工具 (只检查文件存在)',
                                    'type': 'gui'
                                })
                                logger.info(f"检测到PCL GUI工具（WSL路径）: {tool_name} ({wsl_path})")
                                break
                        elif os.path.exists(cmd):
                            # 直接检查文件是否存在
                            detected_tools.append({
                                'name': tool_name,
                                'command': cmd,
                                'version': 'Windows GUI工具 (只检查文件存在)',
                                'type': 'gui'
                            })
                            logger.info(f"检测到PCL GUI工具（文件存在）: {tool_name} ({cmd})")
                            break
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
    
    return detected_tools

def get_pcl_tool_command():
    """获取PCL转换工具命令"""
    if PCL_TOOL_PATH.lower() == 'auto':
        # 自动检测
        tools = detect_pcl_tool()
        if tools:
            tool = tools[0]  # 使用第一个检测到的工具
            logger.info(f"自动选择PCL工具: {tool['name']} ({tool['command']})")
            return tool['command']
        else:
            logger.error("未检测到任何PCL转换工具")
            return None
    else:
        # 使用配置的路径
        if os.path.exists(PCL_TOOL_PATH):
            logger.info(f"使用配置的PCL工具: {PCL_TOOL_PATH}")
            return PCL_TOOL_PATH
        else:
            logger.error(f"配置的PCL工具不存在: {PCL_TOOL_PATH}")
            return None

def convert_with_tool(tool_cmd, input_path, output_path):
    """使用指定工具转换PCL文件"""
    try:
        # 尝试终止可能残留的PclXform.exe进程（避免"already running"错误）
        if platform.system() != 'Windows' and ('pclxform' in tool_cmd.lower() or 'pcltool' in tool_cmd.lower()):
            try:
                # 使用Windows taskkill终止PclXform.exe进程
                subprocess.run(['/mnt/c/Windows/System32/taskkill.exe', '/F', '/IM', 'PclXform.exe'], 
                              capture_output=True, timeout=5)
                logger.info("尝试终止残留的PclXform.exe进程")
            except Exception as e:
                logger.debug(f"终止进程时忽略错误: {e}")
        
        # 构建命令
        if tool_cmd.endswith('gpcl6') or tool_cmd.endswith('gpcl6.exe'):
            # GhostPCL命令格式: gpcl6 -sDEVICE=pdfwrite -o output.pdf input.pcl
            cmd = [
                tool_cmd,
                '-sDEVICE=pdfwrite',
                '-dNOPAUSE', '-dBATCH', '-dSAFER',
                f'-sOutputFile={output_path}',
                input_path
            ]
        elif tool_cmd.endswith('pcl6') or tool_cmd.endswith('pcl6.exe'):
            # PCL6命令格式: pcl6 -sDEVICE=pdfwrite -o output.pdf input.pcl
            cmd = [
                tool_cmd,
                '-sDEVICE=pdfwrite',
                '-dNOPAUSE', '-dBATCH', '-dSAFER',
                f'-sOutputFile={output_path}',
                input_path
            ]
        elif tool_cmd.endswith('pagetech') or tool_cmd.endswith('pagetech.exe') or tool_cmd.endswith('pagetechcmd') or tool_cmd.endswith('pagetechcmd.exe'):
            # Pagetech命令格式: pagetech input.pcl output.pdf
            # 支持通过环境变量PAGETECH_ARGS自定义参数
            pagetech_args = os.environ.get('PAGETECH_ARGS', '').strip()
            if pagetech_args:
                # 使用自定义参数，替换{input}和{output}占位符
                args = pagetech_args.replace('{input}', input_path).replace('{output}', output_path).split()
                cmd = [tool_cmd] + args
            else:
                # 默认命令格式: pagetech input.pcl output.pdf
                cmd = [tool_cmd, input_path, output_path]
        elif 'pclxform' in tool_cmd.lower() or 'pcltool' in tool_cmd.lower():
            # PageTech PCLTSDK工具命令格式 - 基于用户验证的命令格式
            # 用户验证的命令: "C:\workspace\PCLTSDK_870\PclXform.exe" "C:\workspace\PCLTSDK_870\default.tpt" inp="00000001.pcl" inf="c:\workspace\sample" outp="test.pdf" outf="c:\workspace\sample"
            
            # 支持通过环境变量PCLXFORM_ARGS自定义参数
            pclxform_args = os.environ.get('PCLXFORM_ARGS', '').strip()
            if pclxform_args:
                # 使用自定义参数，替换{input}和{output}占位符
                args = pclxform_args.replace('{input}', input_path).replace('{output}', output_path).split()
                cmd = [tool_cmd] + args
            else:
                # 默认命令格式: 使用用户验证的PCLTSDK命令格式
                # 需要将WSL路径转换为Windows路径（如果适用）
                def to_windows_path_if_wsl(path):
                    """如果是WSL路径，转换为Windows路径"""
                    if path.startswith('/mnt/c/'):
                        # /mnt/c/Users/... -> C:\Users\...
                        win_path = 'C:' + path[6:].replace('/', '\\')
                        return win_path
                    elif path.startswith('/mnt/'):
                        # 其他驱动器，如/mnt/d/ -> D:\
                        drive = path[5:6].upper()  # 获取驱动器字母
                        win_path = f'{drive}:' + path[7:].replace('/', '\\')
                        return win_path
                    else:
                        # 已经是Windows路径或相对路径
                        return path
                
                # 获取输入输出目录和文件名
                # 确保使用绝对路径
                input_path_abs = os.path.abspath(input_path)
                output_path_abs = os.path.abspath(output_path)
                input_dir = os.path.dirname(input_path_abs)
                input_file = os.path.basename(input_path_abs)
                output_dir = os.path.dirname(output_path_abs)
                output_file = os.path.basename(output_path_abs)
                
                # 转换路径为Windows格式（如果工具路径是Windows路径）
                tool_cmd_win = to_windows_path_if_wsl(tool_cmd)
                # 计算模板路径：根据平台选择合适的路径格式
                if platform.system() == 'Windows':
                    template_path = os.path.join(os.path.dirname(tool_cmd_win), 'default.tpt')
                else:
                    # Linux/WSL: 使用WSL路径计算，然后转换为Windows格式
                    template_path_wsl = os.path.join(os.path.dirname(tool_cmd), 'default.tpt')
                    template_path = to_windows_path_if_wsl(template_path_wsl)
                input_dir_win = to_windows_path_if_wsl(input_dir)
                output_dir_win = to_windows_path_if_wsl(output_dir)
                tool_dir_win = to_windows_path_if_wsl(os.path.dirname(tool_cmd))
                
                # 构建完整DOS命令
                # 注意：使用cmd /c包装，避免GUI阻塞问题
                # 根据用户验证的格式：inp=目录, inf=文件名, outp=目录, outf=文件名
                # （参数语义与通常直觉相反！）
                # 添加Silent=true以避免GUI窗口
                dos_command = f'cd /d "{tool_dir_win}" && "{tool_cmd_win}" "{template_path}" inp="{input_dir_win}" inf="{input_file}" outp="{output_dir_win}" outf="{output_file}" Silent=true'
                # 根据平台选择执行方式
                if platform.system() == 'Windows':
                    # Windows: 通过cmd运行
                    cmd = ['cmd', '/c', dos_command]
                else:
                    # Linux/WSL: 通过cmd运行Windows可执行文件
                    # 使用cmd /c包装，确保GUI程序在WSL中正常执行
                    cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]
                    # 设置工作目录为工具所在目录（WSL路径）
                    tool_dir = os.path.dirname(tool_cmd)
        else:
            # 默认命令格式: tool input.pcl output.pdf
            cmd = [tool_cmd, input_path, output_path]
        
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
    finally:
        # 确保转换后终止PclXform.exe进程，避免残留GUI窗口
        if platform.system() != 'Windows' and ('pclxform' in tool_cmd.lower() or 'pcltool' in tool_cmd.lower()):
            try:
                subprocess.run(['/mnt/c/Windows/System32/taskkill.exe', '/F', '/IM', 'PclXform.exe'], 
                              capture_output=True, timeout=5)
                logger.info("转换完成后终止PclXform.exe进程")
            except Exception as e:
                logger.debug(f"终止进程时忽略错误: {e}")

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

def get_user_token(username, password):
    """获取用户访问令牌"""
    try:
        login_url = f"{FILEBOT_API_URL}/auth/login"
        form_data = {
            'username': username,
            'password': password,
            'grant_type': 'password',
            'scope': ''
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(
            login_url,
            data=form_data,
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')
            user_info = result.get('user', {})
            logger.info(f"用户登录成功: {username}")
            return token, user_info
        else:
            logger.error(f"用户登录失败: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        logger.error(f"用户登录请求失败: {str(e)}")
        return None, None

def get_user_info(token):
    """获取用户信息"""
    try:
        user_url = f"{FILEBOT_API_URL}/auth/me"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(user_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"获取用户信息失败: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"获取用户信息请求失败: {str(e)}")
        return None

def login_user_to_session(username, password):
    """用户登录并设置session"""
    token, user_info = get_user_token(username, password)
    if token and user_info:
        session['user_token'] = token
        session['user_info'] = user_info
        session['username'] = username
        session['logged_in'] = True
        return True
    return False

def logout_user_from_session():
    """用户登出，清除session"""
    session.pop('user_token', None)
    session.pop('user_info', None)
    session.pop('username', None)
    session.pop('logged_in', None)
    return True

def get_current_user_from_session():
    """从session获取当前用户信息"""
    if session.get('logged_in'):
        return {
            'token': session.get('user_token'),
            'info': session.get('user_info'),
            'username': session.get('username')
        }
    return None

def login_required(f):
    """登录保护装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('请先登录')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def convert_pcl_via_filebot(file_path, original_filename):
    """通过FileBot后端API转换PCL文件"""
    try:
        token = get_filebot_token()
        if not token:
            return {"success": False, "error": "无法连接到FileBot API"}
        
        upload_url = f"{FILEBOT_API_URL}/conversion/convert"
        
        with open(file_path, 'rb') as f:
            files = {'file': (original_filename, f, 'application/octet-stream')}
            data = {'target_format': 'pdf', 'async_mode': 'false'}
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.post(
                upload_url,
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'converted_file' in result:
                    import base64
                    pdf_data = base64.b64decode(result['converted_file'])
                    output_path = os.path.join(
                        app.config['CONVERTED_FOLDER'],
                        f"{os.path.splitext(original_filename)[0]}.pdf"
                    )
                    with open(output_path, 'wb') as pdf_file:
                        pdf_file.write(pdf_data)
                    return {"success": True, "output_path": output_path}
                else:
                    return {"success": False, "error": "API响应格式不正确"}
            else:
                return {"success": False, "error": f"API错误: {response.status_code} - {response.text}"}
                
    except Exception as e:
        logger.error(f"FileBot转换失败: {str(e)}")
        return {"success": False, "error": f"转换失败: {str(e)}"}

def convert_pcl_local(file_path, original_filename):
    """本地转换PCL文件"""
    try:
        output_filename = f"{os.path.splitext(original_filename)[0]}.pdf"
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
        
        # 获取PCL工具
        tool_cmd = get_pcl_tool_command()
        if not tool_cmd:
            return {"success": False, "error": "未找到可用的PCL转换工具"}
        
        # 执行转换
        success, message = convert_with_tool(tool_cmd, file_path, output_path)
        
        if success:
            if os.path.exists(output_path):
                return {"success": True, "output_path": output_path}
            else:
                return {"success": False, "error": "转换完成但输出文件未找到"}
        else:
            return {"success": False, "error": message}
            
    except Exception as e:
        logger.error(f"本地转换失败: {str(e)}")
        return {"success": False, "error": f"转换失败: {str(e)}"}

@app.route('/api/tools')
def get_tools():
    """获取可用的转换工具API"""
    tools = detect_pcl_tool()
    return jsonify({
        "success": True,
        "tools": tools,
        "use_filebot": USE_FILEBOT_API,
        "platform": platform.system()
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传和转换"""
    logger.info(f"上传请求文件字段: {list(request.files.keys())}")
    
    # 支持'file'或'files'字段名（前端可能发送files）
    file_field = None
    if 'file' in request.files:
        file_field = 'file'
    elif 'files' in request.files:
        file_field = 'files'
    
    if not file_field:
        return jsonify({"success": False, "error": "未选择文件"})
    
    file = request.files[file_field]
    logger.info(f"接收到的文件: filename={file.filename}, content_type={file.content_type}, content_length={file.content_length}")
    if file.filename == '':
        return jsonify({"success": False, "error": "未选择文件"})
    
    if not file.filename.lower().endswith('.pcl'):
        return jsonify({"success": False, "error": "只支持.pcl文件"})
    
    # 保存上传的文件
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    try:
        file.save(upload_path)
        logger.info(f"文件已上传: {filename} -> {upload_path}")
        
        # 选择转换方式
        conversion_method = request.form.get('conversion_method', 'local')
        
        if conversion_method == 'filebot' and USE_FILEBOT_API:
            result = convert_pcl_via_filebot(upload_path, filename)
        else:
            result = convert_pcl_local(upload_path, filename)
        
        if result.get('success'):
            output_path = result['output_path']
            download_filename = os.path.basename(output_path)
            
            # 记录转换成功
            logger.info(f"转换成功: {filename} -> {download_filename}")
            
            return jsonify({
                "success": True,
                "message": "转换成功",
                "download_url": f"/download/{download_filename}",
                "original_filename": filename,
                "converted_filename": download_filename,
                "file_size": os.path.getsize(output_path)
            })
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"转换失败: {filename} - {error_msg}")
            
            # 清理上传的文件
            if os.path.exists(upload_path):
                os.remove(upload_path)
                
            return jsonify({
                "success": False, 
                "error": error_msg,
                "suggestion": "请检查PCL转换工具是否已正确安装"
            })
            
    except Exception as e:
        logger.exception(f"处理文件时发生错误: {str(e)}")
        
        # 清理上传的文件
        if os.path.exists(upload_path):
            os.remove(upload_path)
            
        return jsonify({"success": False, "error": f"处理文件时发生错误: {str(e)}"})

@app.route('/download/<filename>')
def download_file(filename):
    """下载转换后的PDF文件"""
    file_path = os.path.join(app.config['CONVERTED_FOLDER'], secure_filename(filename))
    if not os.path.exists(file_path):
        return "文件不存在", 404
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/health')
def health_check():
    """健康检查端点"""
    tools = detect_pcl_tool()
    return jsonify({
        "status": "healthy",
        "service": "pcl-converter-web",
        "platform": platform.system(),
        "available_tools": [t['name'] for t in tools],
        "use_filebot": USE_FILEBOT_API,
        "upload_folder": app.config['UPLOAD_FOLDER'],
        "converted_folder": app.config['CONVERTED_FOLDER']
    })

@app.route('/api/convert-test')
def convert_test():
    """测试转换功能"""
    # 使用示例文件测试（如果存在）
    test_file = "/mnt/c/workspace/sample/00000001.pcl"
    if not os.path.exists(test_file):
        return jsonify({
            "success": False,
            "error": "测试文件不存在",
            "test_file": test_file
        })
    
    # 测试工具检测
    tools = detect_pcl_tool()
    
    return jsonify({
        "success": True,
        "platform": platform.system(),
        "detected_tools": tools,
        "test_file": test_file,
        "test_file_exists": os.path.exists(test_file)
    })

# ==================== 用户账户系统路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('login.html')
        
        if login_user_to_session(username, password):
            flash('登录成功')
            return redirect(url_for('index'))
        else:
            flash('登录失败，请检查用户名和密码')
            return render_template('login.html')
    
    # GET请求，显示登录页面
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        
        # 验证输入
        if not username or not email or not password:
            flash('用户名、邮箱和密码不能为空')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致')
            return render_template('register.html')
        
        # 调用FileBot API注册用户
        try:
            register_url = f"{FILEBOT_API_URL}/auth/register"
            user_data = {
                'username': username,
                'email': email,
                'password': password,
                'full_name': full_name
            }
            response = requests.post(register_url, json=user_data, timeout=10)
            
            if response.status_code == 200:
                # 注册成功，自动登录
                if login_user_to_session(username, password):
                    flash('注册成功，已自动登录')
                    return redirect(url_for('index'))
                else:
                    flash('注册成功，但自动登录失败，请手动登录')
                    return redirect(url_for('login_page'))
            else:
                error_msg = response.json().get('detail', '注册失败')
                flash(f'注册失败: {error_msg}')
                return render_template('register.html')
                
        except Exception as e:
            logger.error(f"注册请求失败: {str(e)}")
            flash(f'注册请求失败: {str(e)}')
            return render_template('register.html')
    
    # GET请求，显示注册页面
    return render_template('register.html')

@app.route('/logout')
def logout_page():
    """登出"""
    logout_user_from_session()
    flash('已登出')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile_page():
    """个人资料页面"""
    current_user = get_current_user_from_session()
    if not current_user:
        return redirect(url_for('login_page'))
    
    # 获取最新用户信息
    user_info = get_user_info(current_user['token']) if current_user['token'] else current_user['info']
    
    return render_template('profile.html', user=user_info)

@app.route('/api/user/me')
def get_current_user_api():
    """获取当前用户信息API"""
    current_user = get_current_user_from_session()
    if current_user:
        return jsonify({
            "success": True,
            "user": current_user['info']
        })
    else:
        return jsonify({
            "success": False,
            "error": "未登录"
        })

# 更新主页，传递用户信息 - 使用优化界面
@app.route('/')
def index():
    """主页面 - 文件上传表单（优化版）"""
    # 获取当前用户信息
    current_user = get_current_user_from_session()
    
    # 只检查PCL工具配置，不进行完整检测以避免触发GUI应用
    available_tools = []
    if os.environ.get('PCL_TOOL_PATH', 'auto').lower() != 'auto':
        # 如果配置了具体路径，只显示该路径
        available_tools = [{'name': 'configured', 'command': os.environ['PCL_TOOL_PATH'], 'version': '配置路径', 'type': 'unknown'}]
    
    return render_template('index_optimized.html', 
                         tools=available_tools,
                         use_filebot=USE_FILEBOT_API,
                         current_user=current_user)

if __name__ == '__main__':
    # 显示启动信息
    logger.info("=" * 60)
    logger.info("PCL to PDF Converter - Windows优化版")
    logger.info(f"平台: {platform.system()} {platform.release()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"上传文件夹: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"转换文件夹: {app.config['CONVERTED_FOLDER']}")
    
    # 检测工具
    tools = detect_pcl_tool()
    if tools:
        logger.info(f"检测到PCL工具: {', '.join([t['name'] for t in tools])}")
    else:
        logger.warning("未检测到PCL转换工具，请安装GhostPCL或其他PCL工具")
    
    if USE_FILEBOT_API:
        logger.info("FileBot API模式: 已启用")
    else:
        logger.info("FileBot API模式: 已禁用")
    
    logger.info("=" * 60)
    logger.info(f"应用地址: http://localhost:5000")
    logger.info(f"健康检查: http://localhost:5000/health")
    logger.info("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)