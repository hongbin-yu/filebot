import api from './api';

// 抽屉服务 - 已弃用
// 抽屉层已从FileBot架构中移除，现在使用两层结构：应用 → 文件夹 → 文档
// 此服务仅用于向后兼容，返回空数据或重定向到新API

console.warn('⚠️ drawer.service.ts 已弃用：抽屉层已从FileBot架构中移除');

export interface Drawer {
  id: string;
  name: string;
  description?: string;
  slug?: string;
  app_id: string;
  created_at?: string;
  updated_at?: string;
}

export interface ClientDrawer {
  id: string;
  name: string;
  description?: string;
  slug?: string;
  app_id: string;
  app_name: string;
  app_slug?: string;
  document_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ClientApp {
  id: string;
  name: string;
  description?: string;
  slug?: string;
  settings?: {
    indices?: string[];
    client_file_types?: string[];
  };
  drawer_count?: number;
  document_count?: number;
  created_at?: string;
  updated_at?: string;
}

class DrawerService {
  /**
   * 获取所有drawer（跨应用） - 已弃用
   * 抽屉层已移除，请使用folderService.getFolders(appId)替代
   */
  async getDrawers(): Promise<Drawer[]> {
    console.warn('⚠️ drawerService.getDrawers() 已弃用：抽屉层已移除');
    return [];
  }
  
  /**
   * 获取Client可访问的App列表 - 已弃用
   * 请使用appService.getApps()替代
   */
  async getClientApps(): Promise<ClientApp[]> {
    console.warn('⚠️ drawerService.getClientApps() 已弃用：请使用appService.getApps()');
    
    // 调用appService获取应用列表
    try {
      const response = await api.get('/apps/');
      return response.data.map((app: any) => ({
        id: app.id,
        name: app.name,
        description: app.description,
        slug: app.slug,
        settings: app.settings || {},
        drawer_count: 0,
        document_count: 0,
        created_at: app.created_at,
        updated_at: app.updated_at
      }));
    } catch (error) {
      console.error('获取App列表失败:', error);
      return [];
    }
  }
  
  /**
   * 获取App详情（包含索引配置） - 已弃用
   * 请使用appService.getAppById(appId)替代
   */
  async getAppWithSettings(appId: string): Promise<ClientApp | null> {
    console.warn(`⚠️ drawerService.getAppWithSettings(${appId}) 已弃用：请使用appService.getAppById()`);
    
    try {
      const response = await api.get(`/apps/${appId}`);
      const app = response.data;
      
      return {
        id: app.id,
        name: app.name,
        description: app.description,
        slug: app.slug,
        settings: app.settings || {},
        drawer_count: 0,
        document_count: 0,
        created_at: app.created_at,
        updated_at: app.updated_at
      };
    } catch (error) {
      console.error(`获取App详情失败 (${appId}):`, error);
      return null;
    }
  }
  
  /**
   * 获取指定App下的所有drawers - 已弃用
   * 抽屉层已移除，请使用folderService.getFolders(appId)替代
   */
  async getDrawersByApp(appId: string): Promise<Drawer[]> {
    console.warn(`⚠️ drawerService.getDrawersByApp(${appId}) 已弃用：抽屉层已移除，请使用folderService.getFolders()`);
    return [];
  }

  /**
   * 获取单个drawer详情 - 已弃用
   */
  async getDrawerById(drawerId: string): Promise<Drawer> {
    console.warn(`⚠️ drawerService.getDrawerById(${drawerId}) 已弃用：抽屉层已移除`);
    throw new Error('抽屉层已移除，此方法不再可用');
  }

  /**
   * 根据slug获取drawer - 已弃用
   */
  async getDrawerBySlug(slug: string): Promise<Drawer | null> {
    console.warn(`⚠️ drawerService.getDrawerBySlug(${slug}) 已弃用：抽屉层已移除`);
    return null;
  }

  /**
   * 获取drawer下的PDF文档统计 - 已弃用
   */
  async getDrawerDocumentStats(drawerId: string): Promise<{ total: number; pdf_count: number }> {
    console.warn(`⚠️ drawerService.getDrawerDocumentStats(${drawerId}) 已弃用：抽屉层已移除`);
    return { total: 0, pdf_count: 0 };
  }

  /**
   * 获取drawer下的所有文档（跨文件夹） - 已弃用
   * 请使用folderService.getFolderDocuments(folderId)或documentService.searchDocuments()替代
   */
  async getDrawerDocuments(drawerId: string, options?: any): Promise<any[]> {
    console.warn(`⚠️ drawerService.getDrawerDocuments(${drawerId}) 已弃用：抽屉层已移除`);
    return [];
  }

  /**
   * 获取drawer的页面索引数据（application indices） - 已弃用
   */
  async getDrawerPageIndices(drawerId: string): Promise<any[]> {
    console.warn(`⚠️ drawerService.getDrawerPageIndices(${drawerId}) 已弃用：抽屉层已移除`);
    return [];
  }
}

export default new DrawerService();