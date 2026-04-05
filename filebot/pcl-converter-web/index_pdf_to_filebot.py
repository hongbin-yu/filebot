#!/usr/bin/env python3
"""
FileBot PDF索引服务 - 将转换后的PDF文件索引到FileBot系统

功能：
1. 扫描PDF输出目录中的新PDF文件
2. 登录FileBot API获取访问令牌
3. 为每个PDF文件创建文档记录
4. 可选：删除已索引的对应PCL源文件

使用方式：
1. 设置为cron任务：*/5 * * * * cd /path && python3 index_pdf_to_filebot.py
"""

import os
import sys
import json
import time
import shutil
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ========== 配置 ==========
# FileBot API配置
FILEBOT_API_URL = "http://localhost:8000/api"
FILEBOT_USERNAME = "admin"  # 默认管理员用户名
FILEBOT_PASSWORD = "admin123"  # 默认管理员密码

# 文件目录配置
PDF_INPUT_DIR = "/mnt/c/workspace/pcl2pdf"          # PDF文件目录（PCL转换器输出）
PCL_PROCESSED_DIR = "/mnt/c/workspace/pcl_processed" # 已处理的PCL文件目录
PCL_FAILED_DIR = "/mnt/c/workspace/pcl_failed"       # 失败的PCL文件目录

# 索引配置
DEFAULT_FOLDER_NAME = "Auto-Imported PCL Documents"  # 默认文件夹名称
DEFAULT_APP_NAME = "PCL Import App"                  # 默认应用名称
DELETE_SOURCE_PCL = True                            # 索引成功后是否删除源PCL文件

# 日志配置
LOG_DIR = "/mnt/c/workspace/pcl_logs"
LOG_FILE = os.path.join(LOG_DIR, f"pdf_indexer_{datetime.now().strftime('%Y%m%d')}.log")

# 确保目录存在
for dir_path in [PDF_INPUT_DIR, PCL_PROCESSED_DIR, PCL_FAILED_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== FileBot API客户端 ==========

class FileBotClient:
    """FileBot API客户端"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.access_token = None
        self.headers = {"Content-Type": "application/json"}
        self.session = requests.Session()
        
    def login(self) -> bool:
        """登录到FileBot API"""
        try:
            login_url = f"{self.base_url}/auth/login"
            form_data = {
                "username": self.username,
                "password": self.password
            }
            
            # OAuth2密码模式需要form-data格式
            response = self.session.post(
                login_url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.info(f"登录成功: {self.username}")
                return True
            else:
                logger.error(f"登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False
    
    def ensure_authenticated(self):
        """确保已认证，如果未认证则尝试登录"""
        if not self.access_token:
            if not self.login():
                raise Exception("无法登录到FileBot API")
    
    def get_or_create_app(self, app_name: str) -> Optional[Dict[str, Any]]:
        """获取或创建应用"""
        self.ensure_authenticated()
        
        try:
            # 首先尝试获取现有应用
            apps_url = f"{self.base_url}/apps/"
            response = self.session.get(apps_url, headers=self.headers)
            
            if response.status_code == 200:
                apps = response.json()
                for app in apps:
                    if app.get("name") == app_name:
                        logger.info(f"找到现有应用: {app_name} (ID: {app.get('id')})")
                        return app
            
            # 没有找到，创建新应用
            create_url = f"{self.base_url}/apps/"
            app_data = {
                "name": app_name,
                "description": f"自动创建的PCL文档导入应用 - {datetime.now().strftime('%Y-%m-%d')}",
                "settings": {
                    "auto_import": True,
                    "source": "pcl_converter"
                }
            }
            
            response = self.session.post(
                create_url,
                json=app_data,
                headers=self.headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                app = response.json()
                logger.info(f"创建新应用: {app_name} (ID: {app.get('id')})")
                return app
            else:
                logger.error(f"创建应用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取/创建应用异常: {e}")
            return None
    
    def get_or_create_drawer(self, app_id: str, drawer_name: str = "Main Drawer") -> Optional[Dict[str, Any]]:
        """获取或创建抽屉"""
        self.ensure_authenticated()
        
        try:
            # 获取应用的抽屉
            drawers_url = f"{self.base_url}/drawers/?app_id={app_id}"
            response = self.session.get(drawers_url, headers=self.headers)
            
            if response.status_code == 200:
                drawers = response.json()
                for drawer in drawers:
                    if drawer.get("name") == drawer_name:
                        logger.info(f"找到现有抽屉: {drawer_name} (ID: {drawer.get('id')})")
                        return drawer
            
            # 创建新抽屉
            create_url = f"{self.base_url}/drawers/"
            drawer_data = {
                "app_id": app_id,
                "name": drawer_name,
                "description": "PCL文档主抽屉",
                "order_index": 1
            }
            
            response = self.session.post(
                create_url,
                json=drawer_data,
                headers=self.headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                drawer = response.json()
                logger.info(f"创建新抽屉: {drawer_name} (ID: {drawer.get('id')})")
                return drawer
            else:
                logger.error(f"创建抽屉失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取/创建抽屉异常: {e}")
            return None
    
    def get_or_create_folder(self, drawer_id: str, folder_name: str) -> Optional[Dict[str, Any]]:
        """获取或创建文件夹"""
        self.ensure_authenticated()
        
        try:
            # 获取抽屉的文件夹
            folders_url = f"{self.base_url}/folders/?drawer_id={drawer_id}"
            response = self.session.get(folders_url, headers=self.headers)
            
            if response.status_code == 200:
                folders = response.json()
                for folder in folders:
                    if folder.get("name") == folder_name:
                        logger.info(f"找到现有文件夹: {folder_name} (ID: {folder.get('id')})")
                        return folder
            
            # 创建新文件夹
            create_url = f"{self.base_url}/folders/"
            folder_data = {
                "drawer_id": drawer_id,
                "name": folder_name,
                "description": f"自动导入的PCL文档 - {datetime.now().strftime('%Y-%m-%d')}",
                "parent_folder_id": None
            }
            
            response = self.session.post(
                create_url,
                json=folder_data,
                headers=self.headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                folder = response.json()
                logger.info(f"创建新文件夹: {folder_name} (ID: {folder.get('id')})")
                return folder
            else:
                logger.error(f"创建文件夹失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取/创建文件夹异常: {e}")
            return None
    
    def create_document(self, folder_id: str, pdf_file_path: str, original_pcl_name: str = None) -> Optional[Dict[str, Any]]:
        """通过文件上传创建文档记录"""
        self.ensure_authenticated()
        
        try:
            # 获取文件信息
            file_path = Path(pdf_file_path)
            if not file_path.exists():
                logger.error(f"PDF文件不存在: {pdf_file_path}")
                return None
            
            filename = file_path.name
            
            # 使用原始PCL文件名作为文档标题（如果提供）
            if original_pcl_name:
                title = os.path.splitext(original_pcl_name)[0]
            else:
                title = os.path.splitext(filename)[0]
            
            # 准备表单数据（multipart/form-data）
            # 使用FileBot的上传端点：POST /api/documents/upload/
            upload_url = f"{self.base_url}/documents/upload/"
            
            # 构建multipart表单数据
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/pdf')
                }
                
                form_data = {
                    'folder_id': folder_id,
                    'title': title,
                    'description': f'自动从PCL转换的文档 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    'document_type': 'general'
                }
                
                # 发送请求（注意：headers中不要设置Content-Type，requests会自动设置multipart）
                response = self.session.post(
                    upload_url,
                    files=files,
                    data=form_data,
                    headers={k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
                )
            
            if response.status_code == 200 or response.status_code == 201:
                document = response.json()
                logger.info(f"上传文档成功: {filename} (ID: {document.get('id')})")
                return document
            else:
                logger.error(f"上传文档失败: {response.status_code} - {response.text}")
                # 调试：打印请求信息
                logger.debug(f"请求URL: {upload_url}")
                logger.debug(f"表单数据: {form_data}")
                return None
                
        except Exception as e:
            logger.error(f"创建文档记录异常: {e}", exc_info=True)
            return None
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            health_url = f"{self.base_url}/health"
            response = self.session.get(health_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False

# ========== 文件处理函数 ==========

def find_corresponding_pcl_file(pdf_filename: str) -> Optional[str]:
    """
    查找对应的PCL源文件
    
    在processed目录中查找与PDF文件同名的PCL文件
    """
    # 移除.pdf扩展名，添加.pcl扩展名
    pcl_filename = os.path.splitext(pdf_filename)[0] + ".pcl"
    
    # 首先在processed目录中查找
    processed_path = os.path.join(PCL_PROCESSED_DIR, pcl_filename)
    if os.path.exists(processed_path):
        return processed_path
    
    # 然后在processed目录中查找带时间戳前缀的文件
    # 文件名格式: processed_YYYYMMDD_HHMMSS_filename.pcl
    for filename in os.listdir(PCL_PROCESSED_DIR):
        if filename.endswith(pcl_filename) and filename.startswith("processed_"):
            return os.path.join(PCL_PROCESSED_DIR, filename)
    
    # 最后在failed目录中查找
    failed_path = os.path.join(PCL_FAILED_DIR, pcl_filename)
    if os.path.exists(failed_path):
        return failed_path
    
    # 在failed目录中查找带时间戳前缀的文件
    for filename in os.listdir(PCL_FAILED_DIR):
        if filename.endswith(pcl_filename) and filename.startswith("failed_"):
            return os.path.join(PCL_FAILED_DIR, filename)
    
    return None

def delete_pcl_file(pcl_path: str) -> bool:
    """删除PCL源文件"""
    try:
        if os.path.exists(pcl_path):
            os.remove(pcl_path)
            logger.info(f"删除PCL源文件: {pcl_path}")
            return True
        else:
            logger.warning(f"PCL源文件不存在，无法删除: {pcl_path}")
            return False
    except Exception as e:
        logger.error(f"删除PCL文件失败 {pcl_path}: {e}")
        return False

# ========== 主索引函数 ==========

def index_pdf_files(client: FileBotClient, folder_id: str) -> int:
    """扫描并索引PDF文件"""
    logger.info(f"开始扫描PDF目录: {PDF_INPUT_DIR}")
    
    # 扫描PDF文件
    pdf_files = []
    for filename in os.listdir(PDF_INPUT_DIR):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(PDF_INPUT_DIR, filename)
            pdf_files.append((filename, file_path))
    
    if not pdf_files:
        logger.info("未发现新的PDF文件")
        return 0
    
    logger.info(f"发现 {len(pdf_files)} 个PDF文件需要索引")
    
    indexed_count = 0
    failed_count = 0
    
    for pdf_filename, pdf_path in pdf_files:
        logger.info(f"索引文件: {pdf_filename}")
        
        # 查找对应的PCL源文件
        pcl_path = find_corresponding_pcl_file(pdf_filename)
        original_pcl_name = None
        if pcl_path:
            original_pcl_name = os.path.basename(pcl_path).replace("processed_", "").replace("failed_", "")
            # 移除时间戳前缀
            if "_" in original_pcl_name and original_pcl_name.count("_") >= 2:
                # 格式: YYYYMMDD_HHMMSS_filename.pcl
                parts = original_pcl_name.split("_", 2)
                if len(parts) == 3:
                    original_pcl_name = parts[2]
        
        # 创建文档记录
        document = client.create_document(folder_id, pdf_path, original_pcl_name)
        
        if document:
            logger.info(f"索引成功: {pdf_filename}")
            indexed_count += 1
            
            # 如果配置了删除源文件，并且找到了对应的PCL文件
            if DELETE_SOURCE_PCL and pcl_path:
                if delete_pcl_file(pcl_path):
                    logger.info(f"已删除源PCL文件: {pcl_path}")
                else:
                    logger.warning(f"删除源PCL文件失败: {pcl_path}")
        else:
            logger.error(f"索引失败: {pdf_filename}")
            failed_count += 1
    
    logger.info(f"索引完成: 成功 {indexed_count}, 失败 {failed_count}, 总计 {len(pdf_files)}")
    return indexed_count

# ========== 主程序 ==========

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("FileBot PDF索引服务启动")
    logger.info(f"PDF输入目录: {PDF_INPUT_DIR}")
    logger.info(f"PCL已处理目录: {PCL_PROCESSED_DIR}")
    logger.info(f"FileBot API: {FILEBOT_API_URL}")
    logger.info(f"删除源PCL文件: {DELETE_SOURCE_PCL}")
    logger.info("=" * 60)
    
    try:
        # 创建FileBot客户端
        client = FileBotClient(FILEBOT_API_URL, FILEBOT_USERNAME, FILEBOT_PASSWORD)
        
        # 测试API连接
        if not client.test_connection():
            logger.error("无法连接到FileBot API，请确保后端服务正在运行")
            return 1
        
        # 登录
        if not client.login():
            logger.error("登录FileBot API失败")
            return 1
        
        # 获取或创建应用、抽屉、文件夹
        app = client.get_or_create_app(DEFAULT_APP_NAME)
        if not app:
            logger.error("无法获取或创建应用")
            return 1
        
        drawer = client.get_or_create_drawer(app["id"])
        if not drawer:
            logger.error("无法获取或创建抽屉")
            return 1
        
        folder = client.get_or_create_folder(drawer["id"], DEFAULT_FOLDER_NAME)
        if not folder:
            logger.error("无法获取或创建文件夹")
            return 1
        
        logger.info(f"使用文件夹ID进行索引: {folder['id']}")
        
        # 执行索引
        indexed_count = index_pdf_files(client, folder["id"])
        
        if indexed_count > 0:
            logger.info(f"本次索引成功 {indexed_count} 个PDF文件")
        else:
            logger.info("本次没有文件需要索引或索引失败")
            
    except Exception as e:
        logger.error(f"服务执行异常: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())