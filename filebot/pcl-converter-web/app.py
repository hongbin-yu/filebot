"""
PCL to PDF Converter Web Application
Windows Web应用调用命令行API进行PCL到PDF转换

功能：
1. 文件上传界面（支持.pcl文件）
2. 调用FileBot后端API进行转换
3. 显示转换进度和状态
4. 提供结果PDF下载
"""

import os
import requests
import time
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB限制
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['CONVERTED_FOLDER'] = os.path.join(os.path.dirname(__file__), 'converted')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# FileBot后端API配置
FILEBOT_API_URL = 'http://localhost:8000/api/v1'
FILEBOT_USERNAME = 'admin'
FILEBOT_PASSWORD = 'admin123'

# 确保上传和转换目录存在
for folder in [app.config['UPLOAD_FOLDER'], app.config['CONVERTED_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

def get_filebot_token():
    """获取FileBot API访问令牌"""
    try:
        login_url = f"{FILEBOT_API_URL}/auth/login"
        response = requests.post(
            login_url,
            data={'username': FILEBOT_USERNAME, 'password': FILEBOT_PASSWORD},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            app.logger.error(f"FileBot登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        app.logger.error(f"获取FileBot令牌失败: {str(e)}")
        return None

def convert_pcl_via_filebot(file_path, original_filename):
    """通过FileBot后端API转换PCL文件"""
    try:
        # 获取API令牌
        token = get_filebot_token()
        if not token:
            return {"success": False, "error": "无法连接到FileBot API"}
        
        # 准备文件上传
        upload_url = f"{FILEBOT_API_URL}/conversion/convert"
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (original_filename, f, 'application/octet-stream')
            }
            data = {
                'target_format': 'pdf',
                'async_mode': 'false'
            }
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.post(
                upload_url,
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                # FileBot返回转换后的文件内容（base64编码或URL）
                # 这里需要根据实际API响应调整
                if 'converted_file' in result:
                    # 假设返回的是base64编码的文件内容
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
        return {"success": False, "error": f"转换失败: {str(e)}"}

def convert_pcl_direct(file_path, original_filename):
    """直接调用pcltopdf命令行工具（备选方案）"""
    try:
        output_filename = f"{os.path.splitext(original_filename)[0]}.pdf"
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
        
        # 检查pcltopdf是否可用
        import subprocess
        try:
            subprocess.run(['pcltopdf', '--version'], capture_output=True, check=False)
        except FileNotFoundError:
            return {"success": False, "error": "pcltopdf命令行工具未安装"}
        
        # 执行转换
        cmd = ['pcltopdf', file_path, output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                return {"success": True, "output_path": output_path}
            else:
                return {"success": False, "error": "转换完成但输出文件未找到"}
        else:
            return {"success": False, "error": f"pcltopdf错误: {result.stderr}"}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "转换超时"}
    except Exception as e:
        return {"success": False, "error": f"直接转换失败: {str(e)}"}

@app.route('/')
def index():
    """主页面 - 文件上传表单"""
    return render_template('index.html')

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
    file.save(upload_path)
    
    app.logger.info(f"文件已上传: {filename} -> {upload_path}")
    
    # 选择转换方式
    conversion_method = request.form.get('conversion_method', 'filebot')
    
    if conversion_method == 'filebot':
        result = convert_pcl_via_filebot(upload_path, filename)
    else:
        result = convert_pcl_direct(upload_path, filename)
    
    if result.get('success'):
        # 准备下载链接
        output_path = result['output_path']
        download_filename = os.path.basename(output_path)
        return jsonify({
            "success": True,
            "message": "转换成功",
            "download_url": f"/download/{download_filename}",
            "original_filename": filename,
            "converted_filename": download_filename
        })
    else:
        # 清理上传的文件
        if os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify({"success": False, "error": result.get('error', '未知错误')})

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
    return jsonify({"status": "healthy", "service": "pcl-converter-web"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)