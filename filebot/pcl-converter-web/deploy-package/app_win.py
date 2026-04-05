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
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
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
        ('gpcl6', ['gpcl6', 'gpcl6.exe']),  # GhostPCL
        ('pcl6', ['pcl6', 'pcl6.exe']),      # PCL6
        ('pcltopdf', ['pcltopdf', 'pcltopdf.exe']),  # pcltopdf
        ('pcl2pdf', ['pcl2pdf', 'pcl2pdf.exe']),     # 其他变体
    ]
    
    detected_tools = []
    
    for tool_name, tool_commands in tools_to_check:
        for cmd in tool_commands:
            try:
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
                        'version': result.stdout[:100] if result.stdout else 'Unknown version'
                    })
                    logger.info(f"检测到PCL工具: {tool_name} ({cmd})")
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

@app.route('/')
def index():
    """主页面 - 文件上传表单"""
    # 检测可用工具
    available_tools = detect_pcl_tool()
    tool_status = "正常" if available_tools else "未检测到"
    
    return render_template('index_win.html', 
                         tools=available_tools,
                         tool_status=tool_status,
                         use_filebot=USE_FILEBOT_API)

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
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "未选择文件"})
    
    file = request.files['file']
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