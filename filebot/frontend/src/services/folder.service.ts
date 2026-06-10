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
  parent_folder_path?: string;
  path?: string;
  app_id: string; // 应用slug，不是UUID
}

export interface FolderUpdateRequest {
  name?: string;
  description?: string;
  parent_folder_path?: string;
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
    appIdentifier: string, 
    params?: {
      parent_folder_path?: string;
      app_slug?: string;
      path_starts_with?: string;
      app_id?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<Folder[]> {
    // 验证appSlug
    if (!appIdentifier || appIdentifier.trim() === '') {
      console.error('❌ [ERROR] folderService.getFolders: appIdentifier is empty');
      throw new Error('应用标识符不能为空');
    }

    // 准备请求参数 - 过滤掉空值
    const requestParams: any = {
      ...Object.fromEntries(
        Object.entries(params || {}).filter(([_, v]) => v !== undefined && v !== null && v !== '')
      )
    };

    // 始终传入 app_slug 以便后端做权限校验
    // 后端通过 app_slug 找到应用并检查用户是否有权访问
    if (!requestParams.app_slug) {
      requestParams.app_slug = appIdentifier;
    }

    console.log('🔍 [DEBUG] folderService.getFolders:', { appIdentifier, requestParams });

    const response = await api.get('/folders/', { 
      params: requestParams
    });

    console.log('🔍 [DEBUG] folderService.getFolders response:', {
      count: response.data?.length,
      sample: response.data?.slice(0, 3).map((f: Folder) => ({
        name: f.name,
        path: f.path
      })),
      status: response.status
    });

    return response.data;
  }

  /**
   * 获取单个文件夹详情 - 仅支持路径
   * @param folderPath 文件夹路径（如 "/boarding/canadasite/fr"）
   * @returns 文件夹详情
   */
  async getFolder(folderPath: string): Promise<Folder> {
    if (!folderPath) {
      throw new Error('文件夹路径不能为空');
    }

    console.log('🔍 [DEBUG] folderService.getFolder:', { folderPath });
    
    const normalizedPath = folderPath.startsWith('/') ? folderPath : '/' + folderPath;
    
    try {
      // 后端路由是 GET /by-path?path=...，用 query parameter 传参
      const response = await api.get('/folders/by-path', {
        params: { path: normalizedPath }
      });
      return response.data;
    } catch (error: any) {
      console.error('❌ folderService.getFolder error:', {
        folderPath,
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      });
      throw error;
    }
  }

  /**
   * Get folder by full path
   * @param folderPath 文件夹路径，如 "/boarding/canada-site/en"
   * @returns 文件夹对象
   */
  async getFolderByPath(folderPath: string): Promise<Folder> {
    console.log('🔍 [DEBUG] folderService.getFolderByPath:', { folderPath });
    const normalizedPath = folderPath.startsWith('/') ? folderPath : '/' + folderPath;
    return this.getFolder(normalizedPath);
  }



  /**
   * 创建文件夹
   * @param data 文件夹创建数据
   * @returns 创建的文件夹
   */
  async createFolder(data: FolderCreateRequest): Promise<Folder> {
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
    const cleanPath = folderPath.startsWith('/') ? folderPath.slice(1) : folderPath;
    await api.delete(`/folders/${cleanPath}`, {
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
    const response = await api.get(`/folders/tree/${appSlug}`);
    return response.data;
  }

  /**
   * 移动文件夹到另一父目录（递归更新所有子路径）
   * @param folderPath 要移动的文件夹路径（如 /boarding/canadasite/en/old-parent/subfolder）
   * @param targetParentPath 目标父文件夹路径（如 /boarding/canadasite/en/new-parent）
   * @returns 移动结果
   */
  async moveFolder(folderPath: string, targetParentPath: string): Promise<Folder> {
    console.log('🔍 [DEBUG] folderService.moveFolder:', { folderPath, targetParentPath });
    const response = await api.post(`/folders/${encodeURIComponent(folderPath)}/move`, null, {
      params: { target_parent_path: targetParentPath }
    });
    return response.data.folder;
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
   * 获取指定路径下所有子文件夹路径（递归，单DB查询）
   * 替代前端BFS循环调用，避免大量API请求
   * @param appSlug 应用slug
   * @param rootPath 根文件夹路径，如 /boarding/canadasite
   * @returns 路径列表（包含rootPath自身）
   */
  async getDescendantPaths(appSlug: string, rootPath: string): Promise<string[]> {
    console.log('🔍 [DEBUG] folderService.getDescendantPaths:', { appSlug, rootPath });
    const response = await api.get('/folders/descendant-paths', {
      params: { app_id: appSlug, root_path: rootPath }
    });
    const paths: string[] = response.data?.paths || [];
    console.log('🔍 [DEBUG] folderService.getDescendantPaths response:', { count: response.data?.count, paths: paths.slice(0, 5) });
    return paths;
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