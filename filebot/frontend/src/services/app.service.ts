import api from './api';
import i18n from '../i18n';

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
  config?: Record<string, any>; // 应用配置
  app_type?: string;           // 应用类型：document_management, web_app, etc.
  is_active?: boolean;         // 应用是否激活
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
  settings: {
    indices: string[];
  };
  app_type?: string;     // 应用类型：document_management, web_app, etc.
  is_active?: boolean;   // 应用是否激活
  config?: Record<string, any>; // 应用配置
  redirect_url?: string;  // 重定向URL，用于集成WebBot等外部应用
  icon?: string;         // 图标URL或图标名称
  owner_id?: string;
}

export interface AppUpdateRequest {
  name?: string;
  description?: string;
  slug?: string;
  settings?: { indices: string[] };
  config?: Record<string, any>;
  app_type?: string;
  is_active?: boolean;
  redirect_url?: string;
  icon?: string;
}

class AppService {
  // 获取所有应用
  async getApps(): Promise<App[]> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log(i18n.t('services.appService.devModeMockData'));
      
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
      
      console.log(i18n.t('services.appService.mockAppsReturned', { count: mockApps.length }));
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
      console.error(i18n.t('services.appService.fetchAppDetailFailed', { appId }), error);
      throw error; // 抛出错误而不是返回null
    }
  }

  // 创建应用
  async createApp(data: CreateAppRequest): Promise<App> {
    console.log(i18n.t('services.appService.createAppCalled'), data);
    
    // 从本地存储获取当前用户信息
    const userInfoStr = localStorage.getItem('user_info');
    let owner_id: string | undefined;
    
    if (userInfoStr) {
      try {
        const userInfo = JSON.parse(userInfoStr);
        owner_id = userInfo.id;
        console.log(i18n.t('services.appService.foundUserInfo', { ownerId: owner_id }), owner_id);
      } catch (error) {
        console.warn(i18n.t('services.appService.cannotParseUserInfo'), error);
      }
    } else {
      console.warn(i18n.t('services.appService.noUserInfoWarning'));
    }
    
    // 构建请求数据
    const requestData: any = {
      name: data.name,
      slug: data.slug,
      description: data.description,
      settings: data.settings || { indices: [] },
      app_type: data.app_type,
      is_active: data.is_active,
      config: data.config
    };
    
    // 如果提供了owner_id，使用提供的值，否则使用当前用户ID
    if (data.owner_id) {
      requestData.owner_id = data.owner_id;
      console.log(i18n.t('services.appService.usingOwnerIdFromRequest', { ownerId: data.owner_id }), data.owner_id);
    } else if (owner_id) {
      requestData.owner_id = owner_id;
      console.log(i18n.t('services.appService.usingOwnerIdFromLocalStorage', { ownerId: owner_id }), owner_id);
    } else {
      console.error(i18n.t('services.appService.noOwnerIdError'));
      throw new Error(i18n.t('services.appService.cannotDetermineOwner'));
    }
    
    console.log(i18n.t('services.appService.sendingRequestData'), requestData);
    const response = await api.post('/apps/', requestData);
    console.log(i18n.t('services.appService.createAppResponse'), response.data);
    return response.data;
  }

  // 更新应用
  async updateApp(appId: string, data: AppUpdateRequest): Promise<App> {
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

  // Drawer相关方法 - 已弃用（抽屉层已移除）
  async getAppDrawers(appId: string): Promise<any[]> {
    console.warn(`⚠️ appService.getAppDrawers(${appId}) 已弃用：抽屉层已移除`);
    return [];
  }

  async createDrawer(_appId: string, _data: any): Promise<any> {
    console.warn('⚠️ appService.createDrawer() 已弃用：抽屉层已移除');
    throw new Error('抽屉层已移除，此方法不再可用');
  }

  async updateDrawer(appId: string, drawerId: string, data: any): Promise<any> {
    console.warn(`⚠️ appService.updateDrawer(${appId}, ${drawerId}) 已弃用：抽屉层已移除`);
    throw new Error('抽屉层已移除，此方法不再可用');
  }

  async deleteDrawer(appId: string, drawerId: string): Promise<void> {
    console.warn(`⚠️ appService.deleteDrawer(${appId}, ${drawerId}) 已弃用：抽屉层已移除`);
    throw new Error('抽屉层已移除，此方法不再可用');
  }

  // 健康检查
  async healthCheck(): Promise<any> {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      return { status: 'error', message: 'Health check failed' };
    }
  }
}

export default new AppService();