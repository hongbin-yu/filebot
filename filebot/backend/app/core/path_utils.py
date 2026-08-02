"""
路径工具模块 - 处理文件路径生成、验证和管理

用于实现层次化路径存储系统：
{app_slug}/{folder_path}/{safe_filename}
"""
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


def clean_folder_path_for_static(app_slug: str, folder_path: str) -> str:
    """
    清理文件夹路径用于静态文件存储，防止路径重复
    
    Args:
        app_slug: 应用slug
        folder_path: 原始文件夹路径（可能以斜杠开头）
        
    Returns:
        清理后的文件夹路径，不重复包含应用slug
    """
    if not folder_path:
        return ''
    
    # 移除开头的斜杠
    if folder_path.startswith('/'):
        folder_path = folder_path[1:] if len(folder_path) > 1 else ''
    
    # 如果文件夹路径以应用slug开头，移除重复的应用slug部分
    # 例如：app_slug="boarding", folder_path="boarding/travel-and-tourism/..."
    # 结果应为："travel-and-tourism/..."
    slug_prefix = f"{app_slug}/"
    if folder_path.startswith(slug_prefix):
        folder_path = folder_path[len(slug_prefix):]
    
    # 如果清理后等于应用slug，返回空字符串
    if folder_path == app_slug:
        folder_path = ''
    
    return folder_path


def make_filename_safe(filename: str) -> str:
    """
    将文件名转换为安全格式
    
    移除或替换可能引起问题的字符：
    - 空格替换为下划线
    - 特殊字符替换为下划线
    - 保留点号（用于扩展名）
    - 转换为小写
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全化的文件名
    """
    if not filename:
        return str(uuid.uuid4())
    
    # 分离文件名和扩展名
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    
    # 处理文件名部分
    # 替换空格为下划线
    stem = stem.replace(' ', '_')
    
    # 移除或替换特殊字符（保留连字符、下划线）
    # 允许的字符：字母、数字、连字符、下划线、点号
    stem = re.sub(r'[^\w\-\.]', '_', stem)
    
    # 合并并转换为小写
    result = f"{stem}{suffix}".lower()
    
    # 确保文件名不为空
    if not result or result == suffix:  # 只有扩展名
        result = f"file_{uuid.uuid4().hex[:8]}{suffix}"
    
    return result


def ensure_directory_exists(directory_path: Path) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory_path: 目录路径
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败 {directory_path}: {e}")
        return False


def generate_unique_filename(base_filename: str, target_dir: Path) -> str:
    """
    在目标目录中生成唯一的文件名
    
    如果文件名已存在，添加数字后缀：
    file.jpg -> file-1.jpg -> file-2.jpg
    
    Args:
        base_filename: 基础文件名
        target_dir: 目标目录
        
    Returns:
        唯一的文件名
    """
    if not target_dir.exists():
        return base_filename
    
    stem = Path(base_filename).stem
    suffix = Path(base_filename).suffix
    
    counter = 1
    candidate = base_filename
    
    while (target_dir / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    
    return candidate


def generate_storage_paths(
    original_filename: str,
    app_slug: str,
    folder_path: str,
    data_root: Path
) -> Tuple[Path, str, str]:
    """
    为文档生成存储路径和URL路径
    
    Args:
        original_filename: 原始文件名
        app_slug: 应用slug（URL友好标识符）
        folder_path: 文件夹路径（如 "/travel-and-tourism/images"）
        data_root: 数据根目录
        
    Returns:
        (storage_path, url_path, safe_filename)
        storage_path: 物理存储路径（绝对路径）
        url_path: 公共URL路径
        safe_filename: 安全化的文件名（确保唯一）
    """
    # 安全化基础文件名
    base_safe_filename = make_filename_safe(original_filename)
    
    # 清理文件夹路径
    # 确保以斜杠开头，移除尾部斜杠
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path
    folder_path = folder_path.rstrip('/')
    
    # 避免app_slug与folder_path重复
    # 如果folder_path以/{app_slug}开头，移除重复部分
    if folder_path.startswith(f'/{app_slug}'):
        # 移除开头的/{app_slug}
        folder_path = folder_path[len(app_slug)+1:]  # +1 for the slash
        # 确保folder_path以斜杠开头（如果还有内容）
        if folder_path and not folder_path.startswith('/'):
            folder_path = '/' + folder_path
    
    # 构建目标目录路径
    # 格式: {data_root}/{app_slug}{folder_path}
    target_dir = data_root / f"{app_slug}{folder_path}"
    
    # 确保目录存在
    ensure_directory_exists(target_dir)
    
    # 生成唯一的文件名
    safe_filename = generate_unique_filename(base_safe_filename, target_dir)
    
    # 构建相对存储路径
    # 格式: {app_slug}{folder_path}/{safe_filename}
    relative_path = f"{app_slug}{folder_path}/{safe_filename}"
    
    # 构建绝对存储路径
    storage_path = data_root / relative_path
    
    # 构建URL路径
    # 格式: /{app_slug}{folder_path}/{safe_filename}
    # HTML等文档页面直接挂载，图片等资源文件保持/content/dam/
    url_path = f"/{app_slug}{folder_path}/{safe_filename}"
    
    # 移除 .html 后缀：URL 路径应使用干净路径
    # 磁盘文件（storage_path）仍保留 .html 扩展名
    url_path = re.sub(r'\.html?$', '', url_path)
    
    return storage_path, url_path, safe_filename


def extract_path_info(storage_path: str, data_root: Path) -> dict:
    """
    从存储路径提取信息
    
    Args:
        storage_path: 存储路径（绝对或相对）
        data_root: 数据根目录
        
    Returns:
        包含应用slug、文件夹路径、文件名的字典
    """
    try:
        # 转换为Path对象
        path_obj = Path(storage_path)
        
        # 如果是绝对路径，转换为相对于data_root的路径
        if path_obj.is_absolute():
            try:
                relative_path = path_obj.relative_to(data_root)
            except ValueError:
                # 不在data_root下
                return {
                    'app_slug': None,
                    'folder_path': None,
                    'filename': path_obj.name,
                    'is_valid': False
                }
        else:
            relative_path = path_obj
        
        # 分割路径部分
        parts = relative_path.parts
        
        if len(parts) < 2:
            # 至少需要应用slug和文件名
            return {
                'app_slug': None,
                'folder_path': None,
                'filename': relative_path.name,
                'is_valid': False
            }
        
        # 第一部分是应用slug
        app_slug = parts[0]
        
        # 最后一部分是文件名
        filename = parts[-1]
        
        # 中间部分是文件夹路径
        if len(parts) > 2:
            folder_parts = parts[1:-1]
            folder_path = '/' + '/'.join(folder_parts)
        else:
            folder_path = '/'
        
        return {
            'app_slug': app_slug,
            'folder_path': folder_path,
            'filename': filename,
            'is_valid': True
        }
        
    except Exception as e:
        return {
            'app_slug': None,
            'folder_path': None,
            'filename': None,
            'is_valid': False,
            'error': str(e)
        }


def move_file_with_backup(
    source_path: Path,
    target_path: Path,
    create_backup: bool = True
) -> bool:
    """
    移动文件并创建备份
    
    Args:
        source_path: 源文件路径
        target_path: 目标文件路径
        create_backup: 是否创建备份
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        # 确保目标目录存在
        ensure_directory_exists(target_path.parent)
        
        # 如果目标文件已存在，重命名现有文件
        if target_path.exists() and create_backup:
            backup_path = target_path.with_suffix(f"{target_path.suffix}.backup_{uuid.uuid4().hex[:8]}")
            target_path.rename(backup_path)
            print(f"已备份现有文件到: {backup_path}")
        
        # 移动文件
        source_path.rename(target_path)
        print(f"文件移动成功: {source_path} -> {target_path}")
        
        # 验证文件存在
        if target_path.exists():
            return True
        else:
            print(f"移动后文件不存在: {target_path}")
            return False
            
    except Exception as e:
        print(f"移动文件失败 {source_path} -> {target_path}: {e}")
        return False


def validate_path_system(document, db, settings) -> dict:
    """
    验证文档的路径系统状态
    
    Args:
        document: 文档对象
        db: 数据库会话
        settings: 应用设置
        
    Returns:
        验证结果字典
    """
    result = {
        'document_id': str(document.path),
        'original_filename': document.original_filename,
        'has_storage_path': bool(document.storage_path),
        'has_path': bool(document.path),
        'has_legacy_storage': bool(document.stored_filename),
        'is_valid': False,
        'issues': []
    }
    
    # 如果有新路径系统
    if document.storage_path:
        data_root = Path(settings.DATA_ROOT)
        storage_path = data_root / document.storage_path
        
        # 检查文件是否存在
        if storage_path.exists():
            result['storage_path_exists'] = True
            result['file_size'] = storage_path.stat().st_size
            
            # 验证路径信息
            path_info = extract_path_info(str(storage_path), data_root)
            if path_info['is_valid']:
                result['path_info'] = path_info
                result['is_valid'] = True
            else:
                result['issues'].append(f"路径信息无效: {path_info.get('error', '未知错误')}")
        else:
            result['storage_path_exists'] = False
            result['issues'].append(f"存储路径不存在: {storage_path}")
    
    # 如果有旧存储系统
    elif document.stored_filename:
        # 检查旧存储位置
        from app.routers.documents import get_document_file_path
        try:
            legacy_path = get_document_file_path(document, settings)
            if legacy_path and legacy_path.exists():
                result['legacy_path_exists'] = True
                result['legacy_file_size'] = legacy_path.stat().st_size
            else:
                result['legacy_path_exists'] = False
                result['issues'].append("旧存储路径不存在")
        except Exception as e:
            result['issues'].append(f"检查旧存储路径失败: {e}")
    
    else:
        result['issues'].append("无存储信息")
    
    return result


# ========== 静态文件管理函数 ==========

def get_static_relative_path(document, settings) -> Optional[str]:
    """
    计算文档在静态目录中的相对路径

    storage_path 可能是相对路径（相对 DATA_ROOT）也可能是绝对路径。
    统一转换为相对 DATA_ROOT 的相对路径，避免 pathlib 拼接绝对路径时
    覆盖 static_root，导致复制/删除操作落到源文件上（数据丢失风险）。
    """
    sp = document.storage_path
    if not sp:
        return None
    data_root = Path(settings.DATA_ROOT).resolve()
    p = Path(sp)
    if not p.is_absolute():
        p = data_root / p
    try:
        rel = os.path.relpath(p.resolve(), data_root)
    except ValueError:
        logger.warning(f"无法计算静态相对路径（跨盘符）: {sp}")
        return None
    if rel == '.' or rel.startswith('..'):
        logger.warning(f"storage_path 不在 DATA_ROOT 内，跳过静态操作: {sp}")
        return None
    return rel


def get_publish_relative_path(document) -> Optional[str]:
    """
    计算文档在发布目录中的相对路径（即 8003 公开 URL 路径）。

    文档 path 存在多种内部前缀风格：
      /content/dam/...                 （canada.ca 内容路径，无需处理）
      /publish/content/dam/...         （旧发布路径，剥掉 /publish）
      /boarding/canadasite/content/... （app 前缀，剥掉 /boarding/{site}）

    统一规则：优先从 path 中的 /content 开始截取；否则剥掉 /publish；
    否则原样（仅剥前导 /）。与前端 ClientAppFolders 的 toPublicPath 保持一致。

    Returns:
        发布目录相对路径（无前导 /），无法确定时返回 None
    """
    p = getattr(document, 'path', None)
    if not p:
        return None
    ci = p.find('/content')
    if ci >= 0:
        rel = p[ci:].lstrip('/')
    else:
        rel = p.replace('/publish', '', 1).lstrip('/')
    if not rel or rel.startswith('..') or rel.startswith('/'):
        logger.warning(f"无法计算发布相对路径: {p}")
        return None
    return rel


def copy_to_static_directory(
    document,
    settings,
    static_root: Optional[Path] = None
) -> Dict[str, Any]:
    """
    将已发布的文档复制到静态目录
    
    Args:
        document: 文档对象
        settings: 应用设置
        static_root: 静态文件根目录（可选，默认使用settings.STATIC_FILES_PATH）
        
    Returns:
        操作结果字典
    """
    try:
        if static_root is None:
            static_root = Path(settings.STATIC_FILES_PATH)
        
        # 确保静态目录存在
        ensure_directory_exists(static_root)
        
        # 获取文档的存储路径
        from app.routers.documents import get_document_file_path
        source_path = get_document_file_path(document, settings)
        
        if not source_path or not source_path.exists():
            return {
                'success': False,
                'error': f'源文件不存在: {source_path}',
                'document_id': str(document.path),
                'filename': document.original_filename
            }
        
        # 确定目标路径
        # 优先使用文档 path 的公开形式（去掉 /boarding/{site}、/publish 前缀），
        # 与 8003 发布服务器的 URL 结构保持一致；失败时回退 storage_path 计算。
        if document.storage_path:
            target_relative_path = get_publish_relative_path(document)
            if not target_relative_path:
                # 回退：从storage_path计算相对路径（兼容相对/绝对两种格式）
                target_relative_path = get_static_relative_path(document, settings)
            if not target_relative_path:
                return {
                    'success': False,
                    'error': '无法从 storage_path 计算静态相对路径',
                    'document_id': str(document.path)
                }
        else:
            # 旧系统：需要构建路径
            # 获取应用和文件夹信息
            folder = document.folder
            app = folder.app if folder else None
            
            if not app or not folder:
                return {
                    'success': False,
                    'error': '无法获取应用或文件夹信息',
                    'document_id': str(document.path)
                }
            
            # 构建路径：app_slug/folder_path/safe_filename
            safe_filename = make_filename_safe(document.original_filename)
            # 文件夹路径需要处理
            folder_path = folder.path if folder.path else f'/{folder.path}'
            # 清理路径，防止重复包含应用slug
            folder_path = clean_folder_path_for_static(app.slug, folder_path)
            
            target_relative_path = f"{app.slug}/{folder_path}/{safe_filename}" if folder_path else f"{app.slug}/{safe_filename}"
        
        # 构建完整目标路径
        target_path = static_root / target_relative_path
        
        # 确保目标目录存在
        ensure_directory_exists(target_path.parent)
        
        # 复制文件
        shutil.copy2(source_path, target_path)
        
        logger.info(f"已发布文档复制到静态目录: {document.path} -> {target_path}")
        
        # 可选：更新文档的path指向静态URL
        # 静态URL格式: /static/files/{target_relative_path}
        static_url = f"/static/files/{target_relative_path}"
        
        return {
            'success': True,
            'source_path': str(source_path),
            'target_path': str(target_path),
            'static_url': static_url,
            'document_id': str(document.path),
            'file_size': target_path.stat().st_size
        }
        
    except Exception as e:
        logger.error(f"复制到静态目录失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'document_id': str(document.path) if document else 'unknown'
        }


def remove_from_static_directory(
    document,
    settings,
    static_root: Optional[Path] = None
) -> Dict[str, Any]:
    """
    从静态目录删除文档（当文档取消发布时）
    
    Args:
        document: 文档对象
        settings: 应用设置
        static_root: 静态文件根目录（可选，默认使用settings.STATIC_FILES_PATH）
        
    Returns:
        操作结果字典
    """
    try:
        if static_root is None:
            static_root = Path(settings.STATIC_FILES_PATH)
        
        # 确定静态文件路径
        # 优先使用文档 path 的公开形式（与发布时 copy_to_static_directory 一致），
        # 保证 Unpublish 删除的位置 = Publish 复制的位置 = 8003 URL 的位置。
        if document.storage_path:
            target_relative_path = get_publish_relative_path(document)
            if not target_relative_path:
                # 回退：从storage_path计算相对路径（兼容相对/绝对两种格式）
                target_relative_path = get_static_relative_path(document, settings)
            if not target_relative_path:
                return {
                    'success': False,
                    'error': '无法从 storage_path 计算静态相对路径',
                    'document_id': str(document.path)
                }
        else:
            # 旧系统：需要构建路径
            folder = document.folder
            app = folder.app if folder else None
            
            if not app or not folder:
                return {
                    'success': False,
                    'error': '无法获取应用或文件夹信息',
                    'document_id': str(document.path)
                }
            
            safe_filename = make_filename_safe(document.original_filename)
            folder_path = folder.path if folder.path else f'/{folder.path}'
            # 清理路径，防止重复包含应用slug
            folder_path = clean_folder_path_for_static(app.slug, folder_path)
            
            target_relative_path = f"{app.slug}/{folder_path}/{safe_filename}" if folder_path else f"{app.slug}/{safe_filename}"
        
        target_path = static_root / target_relative_path
        
        # 检查文件是否存在并删除
        if target_path.exists():
            target_path.unlink()
            logger.info(f"已从静态目录删除文档: {document.path} -> {target_path}")
            
            # 可选：清理空目录
            try:
                # 检查父目录是否为空
                parent_dir = target_path.parent
                if parent_dir.exists() and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    logger.info(f"清理空目录: {parent_dir}")
            except Exception as dir_e:
                logger.debug(f"清理目录失败（可能非空）: {dir_e}")
            
            return {
                'success': True,
                'deleted_path': str(target_path),
                'document_id': str(document.path)
            }
        else:
            return {
                'success': True,
                'message': '静态文件不存在，无需删除',
                'document_id': str(document.path)
            }
            
    except Exception as e:
        logger.error(f"从静态目录删除失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'document_id': str(document.path) if document else 'unknown'
        }


def get_static_file_url(document, settings) -> Optional[str]:
    """
    获取文档的静态文件URL
    
    Args:
        document: 文档对象
        settings: 应用设置
        
    Returns:
        静态文件URL或None
    """
    try:
        if not document.storage_path:
            return None
        
        # 静态URL格式: /static/files/{storage_path}
        return f"/static/files/{document.storage_path}"
        
    except Exception:
        return None