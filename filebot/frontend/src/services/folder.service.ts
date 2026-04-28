import api from './api';
import i18n from '../i18n';

// 开发模式标志 - 设为true使用模拟数据，false使用真实API
// 注意：已移除所有模拟数据，开发模式使用真实API
const DEV_MODE = false;

export interface Folder {
  id: string;
  name: string;
  description?: string;
  parent_folder_id?: string;
  parent_folder_path?: string;  // 父文件夹路径
  app_id: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  document_count?: number;
  total_size?: number;
  children?: Folder[];
  // 路径系统字段
  path?: string;
  is_system_folder?: boolean;
  order_index?: number;
  // 新增字段：应用slug（用于前端过滤）
  app_slug?: string;
  // 应用路径
  app_path?: string;
}

export interface FolderCreateRequest {
  name: string;
  description?: string;
  parent_folder_id?: string;
  app_id: string; // 应用slug，不是UUID
}

export interface FolderUpdateRequest {
  name?: string;
  description?: string;
  parent_folder_id?: string;
}

export interface MoveFolderRequest {
  target_parent_folder_id?: string;  // 同应用内改变父文件夹
}

export interface FolderTreeItem extends Folder {
  children?: FolderTreeItem[];
  level: number;
  expanded?: boolean;
}

class FolderService {
  /**
   * 获取文件夹列表 - 基于应用slug
   * @param appSlug 应用slug（如 "boarding"），不是UUID
   * @param params 查询参数
   * @returns 文件夹列表
   */
  async getFolders(
    appSlug: string, 
    params?: {
      parent_folder_id?: string;
      parent_folder_path?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<Folder[]> {
    // 验证appSlug
    if (!appSlug || appSlug.trim() === '') {
      console.error('❌ [ERROR] folderService.getFolders: appSlug is empty');
      throw new Error('应用标识符不能为空');
    }

    // 检查是否意外传递了UUID
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(appSlug);
    if (isUuid) {
      console.warn(`⚠️ [WARNING] folderService.getFolders: appSlug "${appSlug}" appears to be a UUID. Expected a slug like "boarding"`);
    }

    // 准备请求参数
    const requestParams: any = {
      ...(params || {}),
      app_id: appSlug // 始终使用应用slug
    };

    // 调试日志
    console.log('🔍 [DEBUG] folderService.getFolders:', {
      appSlug,
      isUuid,
      requestParams,
      timestamp: new Date().toISOString()
    });

    // 调用API
    const response = await api.get('/folders/', { 
      params: requestParams
    });

    // 响应日志
    console.log('🔍 [DEBUG] folderService.getFolders response:', {
      count: response.data?.length,
      sample: response.data?.slice(0, 3).map((f: Folder) => ({
        id: f.id,
        name: f.name,
        path: f.path,
        app_id: f.app_id,
        app_slug: f.app_slug
      })),
      status: response.status
    });

    return response.data;
  }

  /**
   * 获取单个文件夹详情 - 支持路径或UUID
   * @param folderIdentifier 文件夹路径（如 "/boarding/canada-site"）或UUID
   * @returns 文件夹详情
   */
  async getFolder(folderIdentifier: string): Promise<Folder> {
    // 验证标识符格式
    if (!folderIdentifier) {
      throw new Error('Folder identifier cannot be empty');
    }

    console.log('🔍 [DEBUG] folderService.getFolder called with:', folderIdentifier);
    
    // 判断标识符类型：UUID 或 路径
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(folderIdentifier);
    const isPath = folderIdentifier.startsWith('/');
    
    let url: string;
    if (isUuid) {
      // UUID：使用通用端点
      url = `/folders/${folderIdentifier}`;
      console.log('🔍 [DEBUG] folderService.getFolder: UUID detected, using generic endpoint');
    } else if (isPath) {
      // 路径：使用专用路径端点
      // 确保路径以斜杠开头（已经是）
      const normalizedPath = folderIdentifier.startsWith('/') ? folderIdentifier : '/' + folderIdentifier;
      url = `/folders/by-path/${encodeURIComponent(normalizedPath)}`;
      console.log('🔍 [DEBUG] folderService.getFolder: Path detected, using by-path endpoint');
    } else {
      // 既不是UUID也不是路径：可能是其他标识符，尝试通用端点
      url = `/folders/${encodeURIComponent(folderIdentifier)}`;
      console.log('🔍 [DEBUG] folderService.getFolder: Unknown identifier type, trying generic endpoint');
    }
    
    console.log('🔍 [DEBUG] folderService.getFolder request URL:', url);
    
    try {
      const response = await api.get(url);
      
      console.log('🔍 [DEBUG] folderService.getFolder response:', {
        id: response.data.id,
        name: response.data.name,
        path: response.data.path,
        app_id: response.data.app_id,
        status: response.status
      });
      
      return response.data;
    } catch (error: any) {
      console.error('❌ folderService.getFolder error:', {
        url,
        folderIdentifier,
        identifierType: isUuid ? 'UUID' : (isPath ? 'Path' : 'Unknown'),
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
      throw error;
    }
  }

  /**
   * 获取文件夹详情 - 基于ID（已弃用，仅用于兼容）
   * @deprecated 请使用 getFolder 方法，基于路径
   */
  async getFolderById(folderId: string): Promise<Folder> {
    console.warn('⚠️ folderService.getFolderById 已弃用，请使用 getFolder 方法（基于路径）');
    return this.getFolder(folderId);
  }

  /**
   * 创建文件夹
   * @param data 文件夹创建数据
   * @returns 创建的文件夹
   */
  async createFolder(data: FolderCreateRequest): Promise<Folder> {
    // 验证app_id不是UUID格式
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(data.app_id);
    if (isUuid) {
      console.warn(`⚠️ folderService.createFolder: app_id "${data.app_id}" appears to be a UUID. Expected a slug like "boarding"`);
    }

    console.log('🔍 [DEBUG] folderService.createFolder:', data);
    const response = await api.post('/folders/', data);
    return response.data;
  }

  /**
   * 更新文件夹
   * @param folderPath 文件夹路径
   * @param data 更新数据
   * @returns 更新后的文件夹
   */
  async updateFolder(folderPath: string, data: FolderUpdateRequest): Promise<Folder> {
    console.log('🔍 [DEBUG] folderService.updateFolder:', { folderPath, data });
    const response = await api.put(`/folders/${encodeURIComponent(folderPath)}`, data);
    return response.data;
  }

  /**
   * 删除文件夹
   * @param folderPath 文件夹路径
   * @param recursive 是否递归删除子文件夹
   */
  async deleteFolder(folderPath: string, recursive: boolean = false): Promise<void> {
    console.log('🔍 [DEBUG] folderService.deleteFolder:', { folderPath, recursive });
    // 使用 by-path 端点以支持含斜杠的路径
    const encodedPath = encodeURIComponent(folderPath);
    await api.delete(`/folders/by-path/${encodedPath}`, {
      params: { recursive }
    });
  }

  /**
   * 获取应用文件夹树
   * @param appSlug 应用slug
   * @returns 文件夹树
   */
  async getFolderTree(appSlug: string): Promise<FolderTreeItem[]> {
    console.log('🔍 [DEBUG] folderService.getFolderTree:', appSlug);
    const response = await api.get(`/folders/app/${appSlug}/tree`);
    return response.data;
  }

  /**
   * 移动文件夹（同应用内移动）
   * @param folderPath 要移动的文件夹路径
   * @param targetParentFolderId 目标父文件夹ID（可选）
   * @returns 移动后的文件夹
   */
  async moveFolder(folderPath: string, targetParentFolderId?: string): Promise<Folder> {
    const request: MoveFolderRequest = {};
    
    if (targetParentFolderId) {
      request.target_parent_folder_id = targetParentFolderId;
    }
    
    console.log('🔍 [DEBUG] folderService.moveFolder:', { folderPath, request });
    const response = await api.patch(`/folders/${encodeURIComponent(folderPath)}/move`, request);
    return response.data;
  }

  /**
   * 获取文件夹中的文档
   * @param folderPath 文件夹路径
   * @param params 查询参数
   * @returns 文档列表
   */
  async getFolderDocuments(folderPath: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<any[]> {
    console.log('🔍 [DEBUG] folderService.getFolderDocuments:', { folderPath, params });
    const response = await api.get(`/folders/${encodeURIComponent(folderPath)}/documents`, { params });
    return response.data;
  }

  /**
   * 获取文件夹统计
   * @param folderPath 文件夹路径
   * @returns 统计信息
   */
  async getFolderStats(folderPath: string): Promise<any> {
    console.log('🔍 [DEBUG] folderService.getFolderStats:', folderPath);
    const response = await api.get(`/folders/${encodeURIComponent(folderPath)}/stats`);
    return response.data;
  }

  /**
   * 获取文件夹的祖先链（从根到当前文件夹，用于面包屑导航）
   * @param folderPath 文件夹路径，如 "/boarding/canada-site/en"
   * @returns 祖先文件夹列表
   */
  async getFolderAncestors(folderPath: string): Promise<Folder[]> {
    if (!folderPath || !folderPath.startsWith('/')) {
      console.warn('⚠️ folderService.getFolderAncestors: invalid folderPath:', folderPath);
      return [];
    }
    
    console.log('🔍 [BREADCRUMB] folderService.getFolderAncestors:', { folderPath });
    
    // 使用 query parameter 方式传递路径，避免 URL 编码 / 导致路由冲突
    const response = await api.get('/folders/ancestors-by-path', {
      params: { path: folderPath }
    });
    
    console.log('🔍 [BREADCRUMB] folderService.getFolderAncestors response:', {
      count: response.data?.length,
      names: response.data?.map((f: Folder) => f.name)
    });
    
    return response.data;
  }

  /**
   * 搜索文件夹
   * @param params 搜索参数
   * @returns 搜索结果
   */
  async searchFolders(params: {
    name?: string;
    description?: string;
    app_id?: string; // 应用slug，不是UUID
    skip?: number;
    limit?: number;
  }): Promise<Folder[]> {
    console.log('🔍 [DEBUG] folderService.searchFolders:', params);
    const response = await api.get('/search/folders', { params });
    return response.data;
  }
}

export default new FolderService();