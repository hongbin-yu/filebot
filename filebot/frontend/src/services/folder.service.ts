import api from './api';

// 开发模式标志 - 设为true使用模拟数据，false使用真实API
const DEV_MODE = false;

export interface Folder {
  id: string;
  name: string;
  description?: string;
  parent_folder_id?: string;
  app_id: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  document_count?: number;
  total_size?: number;
  children?: Folder[];
  // 新添加的字段（根据后端模型）
  path?: string;
  is_system_folder?: boolean;
  order_index?: number;
}

export interface FolderCreateRequest {
  name: string;
  description?: string;
  parent_folder_id?: string;
  app_id: string;
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
  // 获取文件夹列表 - 基于应用ID
  async getFolders(appId: string, params?: {
    parent_folder_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<Folder[]> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log('🔧 开发模式：使用模拟文件夹数据, appId:', appId);
      
      // 基于appId返回不同的文件夹数据
      let mockFolders: Folder[] = [];
      
      if (appId.includes('canada-site')) {
        // Canada Site应用文件夹
        mockFolders = [
          {
            id: '123e4567-e89b-12d3-a456-426614174300',
            name: '网站公共文档',
            description: '网站共享PDF文档',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-22T09:15:00Z',
            updated_at: '2026-03-22T09:15:00Z',
            document_count: 5,
            total_size: 1500000
          },
          {
            id: '223e4567-e89b-12d3-a456-426614174301',
            name: '页面设计稿',
            description: '网站页面设计PDF稿',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-22T11:30:00Z',
            updated_at: '2026-03-22T11:30:00Z',
            document_count: 3,
            total_size: 900000
          },
          {
            id: '323e4567-e89b-12d3-a456-426614174302',
            name: '网站报告',
            description: '网站分析报告PDF',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-23T14:45:00Z',
            updated_at: '2026-03-23T14:45:00Z',
            document_count: 7,
            total_size: 2100000
          }
        ];
      } else if (appId.includes('service-canada')) {
        // Service Canada应用文件夹
        mockFolders = [
          {
            id: '123e4567-e89b-12d3-a456-426614174000',
            name: '公共文档',
            description: '共享PDF文档',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-22T09:15:00Z',
            updated_at: '2026-03-22T09:15:00Z',
            document_count: 5,
            total_size: 1500000
          },
          {
            id: '223e4567-e89b-12d3-a456-426614174001',
            name: '合同文件',
            description: '客户合同PDF',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-22T11:30:00Z',
            updated_at: '2026-03-22T11:30:00Z',
            document_count: 3,
            total_size: 900000
          },
          {
            id: '323e4567-e89b-12d3-a456-426614174002',
            name: '报告文档',
            description: '月度报告PDF',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-23T14:45:00Z',
            updated_at: '2026-03-23T14:45:00Z',
            document_count: 7,
            total_size: 2100000
          }
        ];
      } else {
        // 默认文件夹
        mockFolders = [
          {
            id: '123e4567-e89b-12d3-a456-426614174100',
            name: '公共文档',
            description: '共享PDF文档',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-22T09:15:00Z',
            updated_at: '2026-03-22T09:15:00Z',
            document_count: 5,
            total_size: 1500000
          },
          {
            id: '223e4567-e89b-12d3-a456-426614174101',
            name: '合同文件',
            description: '客户合同PDF',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-22T11:30:00Z',
            updated_at: '2026-03-22T11:30:00Z',
            document_count: 3,
            total_size: 900000
          },
          {
            id: '323e4567-e89b-12d3-a456-426614174102',
            name: '报告文档',
            description: '月度报告PDF',
            app_id: appId,
            created_by: 'admin',
            created_at: '2026-03-23T14:45:00Z',
            updated_at: '2026-03-23T14:45:00Z',
            document_count: 7,
            total_size: 2100000
          }
        ];
      }
      
      // 如果指定了parent_folder_id，返回子文件夹（模拟）
      if (params?.parent_folder_id) {
        mockFolders = mockFolders.map(f => ({
          ...f,
          parent_folder_id: params.parent_folder_id
        }));
      }
      
      console.log(`📊 返回 ${mockFolders.length} 个模拟文件夹 (app: ${appId})`);
      return mockFolders;
    }
    
    // 生产模式：调用真实API
    const response = await api.get('/folders/', { 
      params: {
        app_id: appId,
        ...params
      }
    });
    return response.data;
  }

  // 获取单个文件夹详情
  async getFolderById(folderId: string): Promise<Folder> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log('🔧 开发模式：getFolderById, folderId:', folderId);
      
      // 模拟文件夹数据
      const mockFolder: Folder = {
        id: folderId,
        name: '示例文件夹',
        description: '模拟文件夹用于测试',
        app_id: 'mock-app-id',
        created_by: 'admin',
        created_at: '2026-03-22T09:15:00Z',
        updated_at: '2026-03-22T09:15:00Z',
        document_count: 3,
        total_size: 1000000
      };
      
      return mockFolder;
    }
    
    // 生产模式：调用真实API
    const response = await api.get(`/folders/${folderId}`);
    return response.data;
  }

  // 创建文件夹
  async createFolder(data: FolderCreateRequest): Promise<Folder> {
    const response = await api.post('/folders/', data);
    return response.data;
  }

  // 更新文件夹
  async updateFolder(folderId: string, data: FolderUpdateRequest): Promise<Folder> {
    const response = await api.put(`/folders/${folderId}`, data);
    return response.data;
  }

  // 删除文件夹
  async deleteFolder(folderId: string, recursive: boolean = false): Promise<void> {
    await api.delete(`/folders/${folderId}`, {
      params: { recursive }
    });
  }

  // 获取应用文件夹树
  async getFolderTree(appIdentifier: string): Promise<FolderTreeItem[]> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log('🔧 开发模式：getFolderTree, appIdentifier:', appIdentifier);
      
      const mockTree: FolderTreeItem[] = [
        {
          id: '123e4567-e89b-12d3-a456-426614174300',
          name: '网站公共文档',
          description: '网站共享PDF文档',
          app_id: 'mock-app-id',
          created_by: 'admin',
          created_at: '2026-03-22T09:15:00Z',
          updated_at: '2026-03-22T09:15:00Z',
          document_count: 5,
          total_size: 1500000,
          level: 0,
          expanded: true,
          children: [
            {
              id: '123e4567-e89b-12d3-a456-426614174301',
              name: '子文件夹1',
              description: '子文件夹示例',
              app_id: 'mock-app-id',
              parent_folder_id: '123e4567-e89b-12d3-a456-426614174300',
              created_by: 'admin',
              created_at: '2026-03-22T11:30:00Z',
              updated_at: '2026-03-22T11:30:00Z',
              document_count: 2,
              total_size: 500000,
              level: 1,
              expanded: false
            }
          ]
        }
      ];
      
      return mockTree;
    }
    
    // 生产模式：调用真实API
    const response = await api.get(`/folders/app/${appIdentifier}/tree`);
    return response.data;
  }

  // 移动文件夹（同应用内移动，更新父文件夹ID）
  async moveFolder(folderId: string, targetParentFolderId?: string): Promise<Folder> {
    const request: MoveFolderRequest = {};
    
    if (targetParentFolderId) {
      request.target_parent_folder_id = targetParentFolderId;
    }
    
    const response = await api.patch(`/folders/${folderId}/move`, request);
    return response.data;
  }

  // 获取文件夹中的文档
  async getFolderDocuments(folderId: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<any[]> {
    const response = await api.get(`/folders/${folderId}/documents`, { params });
    return response.data;
  }

  // 获取文件夹统计
  async getFolderStats(folderId: string): Promise<any> {
    const response = await api.get(`/folders/${folderId}/stats`);
    return response.data;
  }

  // 搜索文件夹
  async searchFolders(params: {
    name?: string;
    description?: string;
    app_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<Folder[]> {
    const response = await api.get('/search/folders', { params });
    return response.data;
  }
}

export default new FolderService();