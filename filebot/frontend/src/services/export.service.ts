import api from './api';

export interface ExportOptions {
  format?: 'json' | 'csv';
  include_apps?: boolean;
  include_folders?: boolean;
  include_documents?: boolean;
  include_metadata?: boolean;
  app_id?: string;
  folder_id?: string;
  skip?: number;
  limit?: number;
}

class ExportService {
  /**
   * 导出完整系统数据
   * @param options 导出选项
   * @returns 导出的JSON数据
   */
  async exportFull(options?: ExportOptions): Promise<any> {
    const params: any = {};
    
    if (options?.format) {
      params.format = options.format;
    }
    if (options?.include_apps !== undefined) {
      params.include_apps = options.include_apps;
    }
    if (options?.include_folders !== undefined) {
      params.include_folders = options.include_folders;
    }
    if (options?.include_documents !== undefined) {
      params.include_documents = options.include_documents;
    }
    if (options?.include_metadata !== undefined) {
      params.include_metadata = options.include_metadata;
    }
    if (options?.skip !== undefined) {
      params.skip = options.skip;
    }
    if (options?.limit !== undefined) {
      params.limit = options.limit;
    }
    
    const response = await api.get('/export/full', { params });
    return response.data;
  }

  /**
   * 导出指定应用的数据
   * @param appId 应用ID
   * @param options 导出选项
   * @returns 导出的JSON数据
   */
  async exportApp(appId: string, options?: ExportOptions): Promise<any> {
    const params: any = {};
    
    if (options?.format) {
      params.format = options.format;
    }
    if (options?.include_folders !== undefined) {
      params.include_folders = options.include_folders;
    }
    if (options?.include_documents !== undefined) {
      params.include_documents = options.include_documents;
    }
    if (options?.include_metadata !== undefined) {
      params.include_metadata = options.include_metadata;
    }
    if (options?.skip !== undefined) {
      params.skip = options.skip;
    }
    if (options?.limit !== undefined) {
      params.limit = options.limit;
    }
    
    const response = await api.get(`/export/app/${appId}`, { params });
    return response.data;
  }

  /**
   * 导出指定文件夹的数据
   * @param folderId 文件夹ID
   * @param options 导出选项
   * @returns 导出的JSON数据
   */
  async exportFolder(folderId: string, options?: ExportOptions): Promise<any> {
    const params: any = {};
    
    if (options?.format) {
      params.format = options.format;
    }
    if (options?.include_documents !== undefined) {
      params.include_documents = options.include_documents;
    }
    if (options?.include_metadata !== undefined) {
      params.include_metadata = options.include_metadata;
    }
    if (options?.skip !== undefined) {
      params.skip = options.skip;
    }
    if (options?.limit !== undefined) {
      params.limit = options.limit;
    }
    
    const response = await api.get(`/export/folder/${folderId}`, { params });
    return response.data;
  }

  /**
   * 自定义导出
   * @param options 导出选项
   * @returns 导出的JSON数据
   */
  async exportCustom(options: ExportOptions): Promise<any> {
    const response = await api.post('/export/custom', options);
    return response.data;
  }

  /**
   * 下载JSON数据为文件
   * @param data JSON数据
   * @param filename 文件名
   */
  downloadJson(data: any, filename: string): void {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.json') ? filename : `${filename}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
  }

  /**
   * 将JSON数据转换为CSV并下载
   * @param data JSON数据
   * @param filename 文件名
   */
  downloadAsCsv(data: any, filename: string): void {
    // 简单实现：如果数据是数组，转换为CSV
    let csvContent = '';
    
    if (Array.isArray(data)) {
      if (data.length === 0) {
        csvContent = 'No data';
      } else {
        // 获取表头
        const headers = Object.keys(data[0]);
        csvContent = headers.join(',') + '\n';
        
        // 添加数据行
        data.forEach(item => {
          const row = headers.map(header => {
            const value = item[header];
            // 处理包含逗号、引号的值
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
              return `"${value.replace(/"/g, '""')}"`;
            }
            return value !== null && value !== undefined ? String(value) : '';
          });
          csvContent += row.join(',') + '\n';
        });
      }
    } else {
      // 如果不是数组，尝试转换对象
      csvContent = 'Key,Value\n';
      Object.entries(data).forEach(([key, value]) => {
        const safeValue = typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
        csvContent += `${key},${safeValue}\n`;
      });
    }
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
  }

  /**
   * 生成默认文件名
   * @param type 导出类型：'full' | 'app' | 'folder'
   * @param id 相关ID（应用ID或文件夹ID）
   * @param timestamp 时间戳
   */
  generateFilename(type: 'full' | 'app' | 'folder', id?: string, timestamp?: string): string {
    const now = timestamp || new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    
    switch (type) {
      case 'full':
        return `filebot-full-export-${now}`;
      case 'app':
        return `filebot-app-${id || 'unknown'}-${now}`;
      case 'folder':
        return `filebot-folder-${id || 'unknown'}-${now}`;
      default:
        return `filebot-export-${now}`;
    }
  }

  /**
   * 导出应用数据并下载
   * @param appId 应用ID
   * @param appName 应用名称（用于文件名）
   * @param format 格式：'json' 或 'csv'
   */
  async exportAndDownloadApp(appId: string, appName: string, format: 'json' | 'csv' = 'json'): Promise<void> {
    try {
      console.log(`📤 开始导出应用数据: ${appName} (${appId})`);
      
      const data = await this.exportApp(appId, {
        format,
        include_folders: true,
        include_documents: true,
        include_metadata: true
      });
      
      const filename = this.generateFilename('app', appId);
      
      if (format === 'csv') {
        this.downloadAsCsv(data, filename);
      } else {
        this.downloadJson(data, filename);
      }
      
      console.log(`✅ 应用数据导出完成: ${filename}`);
    } catch (error) {
      console.error('❌ 应用数据导出失败:', error);
      throw error;
    }
  }

  /**
   * 导出文件夹数据并下载
   * @param folderId 文件夹ID
   * @param folderName 文件夹名称（用于文件名）
   * @param format 格式：'json' 或 'csv'
   */
  async exportAndDownloadFolder(folderId: string, folderName: string, format: 'json' | 'csv' = 'json'): Promise<void> {
    try {
      console.log(`📤 开始导出文件夹数据: ${folderName} (${folderId})`);
      
      const data = await this.exportFolder(folderId, {
        format,
        include_documents: true,
        include_metadata: true
      });
      
      const filename = this.generateFilename('folder', folderId);
      
      if (format === 'csv') {
        this.downloadAsCsv(data, filename);
      } else {
        this.downloadJson(data, filename);
      }
      
      console.log(`✅ 文件夹数据导出完成: ${filename}`);
    } catch (error) {
      console.error('❌ 文件夹数据导出失败:', error);
      throw error;
    }
  }
}

export default new ExportService();