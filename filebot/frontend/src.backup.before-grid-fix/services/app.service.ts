import api from './api';
import axios from 'axios';

export interface App {
  id: string;
  name: string;
  description?: string;
  icon_url?: string;
  app_type: string;
  config?: Record<string, any>;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface HealthCheckResponse {
  status: string;
  service: string;
  database?: string;
  storage?: {
    available: boolean;
    free_space?: number;
    total_space?: number;
  };
}

export interface AppCreateRequest {
  name: string;
  description?: string;
  icon_url?: string;
  app_type: string;
  config?: Record<string, any>;
}

export interface AppUpdateRequest {
  name?: string;
  description?: string;
  icon_url?: string;
  config?: Record<string, any>;
  is_active?: boolean;
}

export interface Drawer {
  id: string;
  name: string;
  description?: string;
  app_id: string;
  drawer_type: string;
  config?: Record<string, any>;
  is_default: boolean;
  sort_order: number;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface DrawerCreateRequest {
  name: string;
  description?: string;
  drawer_type: string;
  config?: Record<string, any>;
  is_default?: boolean;
  sort_order?: number;
}

export interface DrawerUpdateRequest {
  name?: string;
  description?: string;
  drawer_type?: string;
  config?: Record<string, any>;
  is_default?: boolean;
  sort_order?: number;
}

class AppService {
  // 健康检查 - 使用完整URL，因为不在/api/v1路径下
  async healthCheck(): Promise<HealthCheckResponse> {
    // 创建临时的axios实例，不包含baseURL
    const tempAxios = axios.create({
      baseURL: 'http://localhost:8001',
      timeout: 5000
    });
    
    // 添加认证token
    const token = localStorage.getItem('access_token');
    if (token) {
      tempAxios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await tempAxios.get('/api/health');
    return response.data;
  }

  // 获取应用列表
  async getApps(params?: {
    app_type?: string;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<App[]> {
    const response = await api.get('/apps/', { params });
    return response.data;
  }

  // 获取单个应用详情
  async getAppById(appId: string): Promise<App> {
    const response = await api.get(`/apps/${appId}`);
    return response.data;
  }

  // 创建新应用
  async createApp(data: AppCreateRequest): Promise<App> {
    const response = await api.post('/apps/', data);
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

  // 获取应用统计
  async getAppStats(appId: string): Promise<any> {
    const response = await api.get(`/apps/${appId}/stats`);
    return response.data;
  }

  // 获取应用中的文档
  async getAppDocuments(appId: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<any[]> {
    const response = await api.get(`/apps/${appId}/documents`, { params });
    return response.data;
  }

  // 获取应用的抽屉
  async getAppDrawers(appId: string): Promise<Drawer[]> {
    const response = await api.get(`/apps/${appId}/drawers`);
    return response.data;
  }

  // 获取应用特定抽屉的详情
  async getAppDrawerById(appId: string, drawerId: string): Promise<Drawer> {
    const response = await api.get(`/apps/${appId}/drawers/${drawerId}`);
    return response.data;
  }

  // 搜索应用
  async searchApps(params: {
    name?: string;
    description?: string;
    app_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<App[]> {
    const response = await api.get('/search/apps', { params });
    return response.data;
  }
}

export default new AppService();