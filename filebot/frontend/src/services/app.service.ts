import api from './api';

// 开发模式标志 - 设为true使用模拟数据，false使用真实API
const DEV_MODE = false;

export interface App {
  id: string;
  name: string;
  slug?: string;
  description?: string;
  settings?: {
    indices: string[];
  };
  redirect_url?: string;  // 重定向URL，用于集成WebBot等外部应用
  icon?: string;         // 图标URL或图标名称
  owner_id?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAppRequest {
  name: string;
  slug: string;
  description?: string;
  settings?: {
    indices: string[];
  };
  redirect_url?: string;  // 重定向URL，用于集成WebBot等外部应用
  icon?: string;         // 图标URL或图标名称
  owner_id?: string;
}

class AppService {
  // 获取所有应用
  async getApps(): Promise<App[]> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log('🔧 开发模式：使用模拟应用数据');
      
      const mockApps: App[] = [
        {
          id: 'service-canada',
          name: 'Service Canada',
          slug: 'service-canada',
          description: '加拿大服务局文档管理系统',
          created_at: '2026-03-20T10:00:00Z',
          updated_at: '2026-03-20T10:00:00Z'
        },
        {
          id: 'smart-invoice',
          name: 'Smart Invoice',
          slug: 'smart-invoice',
          description: '智能发票处理系统',
          created_at: '2026-03-21T14:30:00Z',
          updated_at: '2026-03-21T14:30:00Z'
        },
        {
          id: 'canada-site',
          name: 'Canada Site',
          slug: 'canada-site',
          description: '加拿大网站内容管理',
          created_at: '2026-03-26T11:00:00Z',
          updated_at: '2026-03-26T11:00:00Z'
        }
      ];
      
      console.log(`📊 返回 ${mockApps.length} 个模拟应用`);
      return mockApps;
    }
    
    // 生产模式：调用真实API
    const response = await api.get('/apps/');
    return response.data;
  }

  // 获取单个应用详情
  async getAppById(appId: string): Promise<App | null> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log('🔧 开发模式：getAppById, appId:', appId);
      
      const allApps = await this.getApps();
      const app = allApps.find(a => a.id === appId || a.slug === appId);
      
      if (app) {
        return app;
      }
      
      // 如果没找到，返回默认应用
      const mockApp: App = {
        id: appId,
        name: '示例应用',
        description: '模拟应用用于测试',
        created_at: '2026-03-28T10:00:00Z',
        updated_at: '2026-03-28T10:00:00Z'
      };
      
      return mockApp;
    }
    
    // 生产模式：调用真实API
    try {
      const response = await api.get(`/apps/${appId}`);
      return response.data;
    } catch (error) {
      console.error(`获取应用详情失败 (${appId}):`, error);
      throw error; // 抛出错误而不是返回null
    }
  }

  // 创建应用
  async createApp(data: CreateAppRequest): Promise<App> {
    console.log('🔧 createApp called with data:', data);
    
    // 从本地存储获取当前用户信息
    const userInfoStr = localStorage.getItem('user_info');
    let owner_id: string | undefined;
    
    if (userInfoStr) {
      try {
        const userInfo = JSON.parse(userInfoStr);
        owner_id = userInfo.id;
        console.log('🔧 Found user info in localStorage, owner_id:', owner_id);
      } catch (error) {
        console.warn('无法解析用户信息:', error);
      }
    } else {
      console.warn('⚠️  No user_info found in localStorage');
    }
    
    // 构建请求数据
    const requestData: any = {
      name: data.name,
      slug: data.slug,
      description: data.description,
      settings: data.settings || { indices: [] }
    };
    
    // 如果提供了owner_id，使用提供的值，否则使用当前用户ID
    if (data.owner_id) {
      requestData.owner_id = data.owner_id;
      console.log('🔧 Using owner_id from request data:', data.owner_id);
    } else if (owner_id) {
      requestData.owner_id = owner_id;
      console.log('🔧 Using owner_id from localStorage:', owner_id);
    } else {
      console.error('❌ No owner_id available! User might not be logged in.');
      throw new Error('无法确定应用所有者，请确保已登录。');
    }
    
    console.log('🔧 Sending request data:', requestData);
    const response = await api.post('/apps/', requestData);
    console.log('✅ createApp response:', response.data);
    return response.data;
  }

  // 更新应用
  async updateApp(appId: string, data: { 
    name?: string; 
    description?: string; 
    slug?: string;
    settings?: { indices: string[] };
    redirect_url?: string;
    icon?: string;
  }): Promise<App> {
    const response = await api.put(`/apps/${appId}`, data);
    return response.data;
  }

  // 删除应用
  async deleteApp(appId: string): Promise<void> {
    await api.delete(`/apps/${appId}`);
  }

  // 搜索应用
  async searchApps(params: {
    name?: string;
    description?: string;
    skip?: number;
    limit?: number;
  }): Promise<App[]> {
    const response = await api.get('/search/apps', { params });
    return response.data;
  }
}

export default new AppService();