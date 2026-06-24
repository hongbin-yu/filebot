import api from './api';
import i18n from '../i18n';

// 开发模式标志 - 设为true使用模拟数据，false使用真实API
const DEV_MODE = false;

export interface Document {
  id: string;
  title: string;
  description?: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  folder_id: string;
  conversion_status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at?: string;
  pages?: number;
  publish_status?: 'PUBLISHED' | 'UNPUBLISHED';
  status?: string;
  // AI相关字段
  ai_category?: string;
  ai_confidence?: number;
  classification_status?: string;
  // 其他字段
  document_number?: string;
  type?: string;
  comments?: string;
  mime_type?: string;
  device_id?: string;
  storage_subfolder?: string;
  full_storage_path?: string;
  converted_pdf_path?: string;
  conversion_error?: string;
  page_count?: number;
  resolution?: string;
  document_metadata?: Record<string, any>;
  // 路径系统字段
  storage_path?: string;
  path?: string;          // 公共URL路径（原url_path）
  parent_folder_path?: string;
  ai_tags?: string[];
  ai_summary?: string;
  is_indexed?: boolean;
  is_archived?: boolean;
  uploaded_by?: string;
  created_by?: string;
  updated_by?: string;
  metadata?: any;
  // 路径相关字段
  folder_path?: string;
}

export interface DocumentUploadRequest {
  file: File;
  folder_id?: string;  // 已弃用，建议使用 folder_path
  folder_path?: string;  // 推荐使用路径
  title?: string;
  description?: string;
  skip_if_exists?: boolean;
}

class DocumentService {
  // 上一次 API 调用的总文档数（用于分页）
  private _lastTotalCount: number = 0;
  
  get lastTotalCount(): number {
    return this._lastTotalCount;
  }

  // 从 axios response 中提取 X-Total-Count 头
  private captureTotalCount(response: any): void {
    const header = response.headers?.['x-total-count'];
    console.log('📋 [X-Total-Count] headers:', Object.keys(response.headers || {}).filter(k => k.includes('total') || k.includes('count')), 'value:', header);
    this._lastTotalCount = header ? parseInt(header, 10) : 0;
  }

  // 获取文件夹中的文档 (兼容性方法)
  async getDocuments(folderIdentifier: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Document[]> {
    // 路径优先：如果是路径，使用getDocumentsByFolderPath，否则使用getDocumentsByFolderId
    if (folderIdentifier.startsWith('/')) {
      return this.getDocumentsByFolderPath(folderIdentifier, params);
    }
    return this.getDocumentsByFolderId(folderIdentifier, params);
  }

  // 获取文件夹中的文档（路径优先，推荐）
  async getDocumentsByFolderPath(folderPath: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Document[]> {
    // 如果文件夹路径为空，返回空数组
    if (!folderPath || folderPath.trim() === '') {
      console.warn('⚠️ documentService.getDocumentsByFolderPath: empty folderPath, returning empty array');
      return [];
    }
    
    // 确保路径以斜杠开头
    const normalizedPath = folderPath.startsWith('/') ? folderPath : '/' + folderPath;
    
    console.log('🔍 [DEBUG] documentService.getDocumentsByFolderPath:', { 
      folderPath: normalizedPath, 
      params,
      timestamp: new Date().toISOString() 
    });
    
    const response = await api.get('/documents/', { 
      params: {
        folder_path: normalizedPath,
        ...params
      }
    });
    
    // Capture total count from response header for pagination
    console.log('📋 [HEADERS] raw response headers:', response.headers);
    console.log('📋 [HEADERS] total-count keys:', Object.keys(response.headers || {}).filter((k: string) => k.toLowerCase().includes('total') || k.toLowerCase().includes('count')));
    console.log('📋 [HEADERS] x-total-count value:', response.headers?.['x-total-count'], '| X-Total-Count:', response.headers?.['X-Total-Count']);
    console.log('📋 [HEADERS] all keys:', Object.keys(response.headers || {}).slice(0, 20));
    this.captureTotalCount(response);
    
    console.log('🔍 [DEBUG] documentService.getDocumentsByFolderPath response:', {
      count: response.data?.length,
      totalCount: this._lastTotalCount,
      sample: response.data?.slice(0, 3).map((d: Document) => ({
        id: d.id,
        title: d.title,
        folder_id: d.folder_id,
        path: d.path
      })),
      status: response.status
    });
    
    return response.data;
  }

  // 按路径前缀获取所有子孙文档（递归，用 path_prefix LIKE 查询 Document.path）
  async getDocumentsByPathPrefix(folderPath: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Document[]> {
    if (!folderPath || folderPath.trim() === '') {
      console.warn('⚠️ documentService.getDocumentsByPathPrefix: empty folderPath, returning empty array');
      return [];
    }
    
    const normalizedPath = folderPath.startsWith('/') ? folderPath : '/' + folderPath;
    const response = await api.get('/documents/', { 
      params: {
        path_prefix: normalizedPath,
        ...params
      }
    });
    
    // Capture total count from response header for pagination
    this.captureTotalCount(response);
    
    return response.data;
  }

  // 获取文件夹中所有子孙文档（递归，单次API调用替代前端BFS + 多次文档查询）
  async getDocumentsRecursive(folderPath: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Document[]> {
    if (!folderPath || folderPath.trim() === '') {
      console.warn('⚠️ documentService.getDocumentsRecursive: empty folderPath, returning empty array');
      return [];
    }
    
    const normalizedPath = folderPath.startsWith('/') ? folderPath : '/' + folderPath;
    
    console.log('🔍 [DEBUG] documentService.getDocumentsRecursive:', { 
      folderPath: normalizedPath, 
      params,
      timestamp: new Date().toISOString()
    });
    
    const response = await api.get('/documents/by-folder-recursive', {
      params: {
        folder_path: normalizedPath,
        skip: params?.skip || 0,
        limit: params?.limit || 200,
      }
    });
    
    console.log('🔍 [DEBUG] documentService.getDocumentsRecursive response:', {
      count: response.data?.length,
      status: response.status
    });
    
    return response.data;
  }

  // 获取文件夹中的文档（基于ID，已弃用）
  async getDocumentsByFolderId(folderId: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Document[]> {
    console.warn('⚠️ documentService.getDocumentsByFolderId 已弃用，请使用 getDocumentsByFolderPath 方法（基于路径）');
    
    // 如果文件夹ID为空，返回空数组
    if (!folderId || folderId.trim() === '') {
      console.warn('⚠️ documentService.getDocumentsByFolderId: empty folderId, returning empty array');
      return [];
    }
    
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log(i18n.t('services.documentService.devModeGetDocuments', { folderId }), folderId);
      
      const mockDocuments: Document[] = [
        {
          id: 'doc-001',
          title: '服务使用指南',
          original_filename: 'Service-Guide-2026.pdf',
          file_type: 'pdf',
          file_size: 1024000,
          folder_id: folderId,
          conversion_status: 'completed',
          created_at: '2026-03-22T10:00:00Z',
          pages: 5
        },
        {
          id: 'doc-002',
          title: '隐私政策',
          original_filename: 'Privacy-Policy-v2.1.pdf',
          file_type: 'pdf',
          file_size: 512000,
          folder_id: folderId,
          conversion_status: 'completed',
          created_at: '2026-03-22T11:30:00Z',
          pages: 3
        },
        {
          id: 'doc-003',
          title: '用户协议',
          original_filename: 'User-Agreement-2026.pdf',
          file_type: 'pdf',
          file_size: 2048000,
          folder_id: folderId,
          conversion_status: 'completed',
          created_at: '2026-03-22T14:15:00Z',
          pages: 8
        }
      ];
      
      console.log(i18n.t('services.documentService.mockDocumentsReturned', { count: mockDocuments.length, folderId }));
      return mockDocuments;
    }
    
    // 生产模式：调用真实API
    console.log('🔍 [DEBUG] documentService.getDocumentsByFolderId (已弃用):', { folderId, params });
    
    const response = await api.get('/documents/', { 
      params: {
        folder_id: folderId,
        ...params
      }
    });
    
    console.log('🔍 [DEBUG] documentService.getDocumentsByFolderId response:', {
      count: response.data?.length,
      sample: response.data?.slice(0, 3).map((d: Document) => ({
        id: d.id,
        title: d.title,
        folder_id: d.folder_id
      })),
      status: response.status
    });
    
    return response.data;
  }

  // 获取单个文档详情（通过UUID，向后兼容）
  async getDocumentById(documentId: string): Promise<Document> {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  }

  // 获取单个文档详情（通过路径或UUID，推荐使用）
  // 注：后端 {document_identifier:path} 路由已支持多段路径（FastAPI path converter）
  async getDocumentByIdentifier(identifier: string): Promise<Document> {
    // 去掉前导斜杠避免 Vite proxy 对 %2F 的解码问题
    const cleanId = identifier.startsWith('/') ? identifier.slice(1) : identifier;
    const response = await api.get(`/documents/${cleanId}`);
    return response.data;
  }

  // 上传文档
  async uploadDocument(data: DocumentUploadRequest): Promise<Document> {
    const formData = new FormData();
    formData.append('file', data.file);
    
    // 路径优先：如果提供了folder_path，使用它；否则使用folder_id（向后兼容）
    if (data.folder_path) {
      formData.append('folder_path', data.folder_path);
      console.log('🔍 [DEBUG] documentService.uploadDocument: using folder_path:', data.folder_path);
    } else if (data.folder_id) {
      formData.append('folder_id', data.folder_id);
      console.warn('⚠️ documentService.uploadDocument: using deprecated folder_id, recommend using folder_path');
    } else {
      throw new Error('必须提供 folder_path 或 folder_id');
    }
    
    if (data.title) {
      formData.append('title', data.title);
    }
    if (data.description) {
      formData.append('description', data.description);
    }
    if (data.skip_if_exists) {
      formData.append('skip_if_exists', 'true');
    }
    
    console.log('🔍 [DEBUG] documentService.uploadDocument:', {
      hasFolderPath: !!data.folder_path,
      hasFolderId: !!data.folder_id,
      title: data.title,
      filename: data.file.name
    });
    
    const response = await api.post('/documents/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    console.log('🔍 [DEBUG] documentService.uploadDocument response:', {
      id: response.data.id,
      title: response.data.title,
      folder_id: response.data.folder_id,
      path: response.data.path
    });
    
    return response.data;
  }

  // 更新文档（支持path或UUID）
  async updateDocument(documentIdentifier: string, data: {
    title?: string;
    description?: string;
    publish_status?: 'PUBLISHED' | 'UNPUBLISHED';
    status?: string;
    document_number?: string;
    type?: string;
    comments?: string;
    conversion_status?: string;
    is_archived?: boolean;
    document_metadata?: Record<string, any>;
  }): Promise<Document> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.put(`/documents/${encoded}`, data);
    return response.data;
  }

  // 删除文档（支持path或UUID）
  async deleteDocument(documentIdentifier: string): Promise<void> {
    const encoded = encodeURIComponent(documentIdentifier);
    await api.delete(`/documents/${encoded}`);
  }

  // 搜索文档
  async getAiTagCategories(path?: string): Promise<{ categories: { category: string; count: number }[] }> {
    const params: any = { from: 'ai' };
    if (path) params.path = path;
    const response = await api.get('/search/categories', { params });
    return response.data;
  }

  async searchDocuments(params: {
    q?: string;
    folder_id?: string;
    file_type?: string;
    conversion_status?: string;
    path?: string;
    ai_tag?: string;
    skip?: number;
    limit?: number;
  }): Promise<Document[]> {
    // 将前端参数映射到后端搜索端点
    const searchParams: any = {};
    
    if (params.q) {
      searchParams.title = params.q; // 使用title参数进行搜索
    }
    
    if (params.folder_id) {
      searchParams.folder_id = params.folder_id;
    }
    
    if (params.file_type) {
      searchParams.file_type = params.file_type;
    }
    
    if (params.conversion_status) {
      searchParams.conversion_status = params.conversion_status;
    }
    
    if (params.path) {
      searchParams.path = params.path;
    }
    
    if (params.ai_tag) {
      searchParams.ai_tag = params.ai_tag;
    }
    
    if (params.skip !== undefined) {
      searchParams.skip = params.skip;
    }
    
    if (params.limit !== undefined) {
      searchParams.limit = params.limit;
    }
    
    // 调用搜索端点：/search/documents
    // 后端返回 { documents: Document[], total, skip, limit } 格式
    const response = await api.get<{ documents: Document[]; total: number; skip: number; limit: number }>('/search/documents', { params: searchParams });
    return response.data.documents || [];
  }

  async searchDocumentsWithTotal(params: {
    q?: string;
    folder_id?: string;
    file_type?: string;
    conversion_status?: string;
    path?: string;
    ai_tag?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ documents: Document[]; total: number }> {
    const searchParams: any = {};
    if (params.q) searchParams.title = params.q;
    if (params.folder_id) searchParams.folder_id = params.folder_id;
    if (params.file_type) searchParams.file_type = params.file_type;
    if (params.conversion_status) searchParams.conversion_status = params.conversion_status;
    if (params.path) searchParams.path = params.path;
    if (params.ai_tag) searchParams.ai_tag = params.ai_tag;
    if (params.skip !== undefined) searchParams.skip = params.skip;
    if (params.limit !== undefined) searchParams.limit = params.limit;
    const response = await api.get<{ documents: Document[]; total: number; skip: number; limit: number }>('/search/documents', { params: searchParams });
    return {
      documents: response.data.documents || [],
      total: response.data.total || 0
    };
  }

  // 获取文档的转换状态（支持path或UUID）
  async getConversionStatus(documentIdentifier: string): Promise<any> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.get(`/documents/${encoded}/conversion-status`);
    return response.data;
  }

  // 下载文档（支持path或UUID）
  async downloadDocument(documentIdentifier: string, downloadType: string = 'original'): Promise<Blob> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.get(`/documents/${encoded}/download`, {
      params: { download_type: downloadType },
      responseType: 'blob'
    });
    return response.data;
  }

  // 预览文档（支持path或UUID）
  async previewDocument(documentIdentifier: string): Promise<Blob> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.get(`/documents/${encoded}/preview`, {
      responseType: 'blob'
    });
    return response.data;
  }

  // TIFF相关方法（支持path或UUID）
  async getTiffInfo(documentIdentifier: string): Promise<any> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.get(`/documents/${encoded}/tiff-info`);
    return response.data;
  }

  async extractTiffPages(documentIdentifier: string, pageNumbers: number[], format: string = 'pdf'): Promise<Blob> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.post(`/documents/${encoded}/extract-pages`, 
      { page_numbers: pageNumbers, format },
      { responseType: 'blob' }
    );
    return response.data;
  }

  async getTiffPreview(documentIdentifier: string, pageNumber: number, quality: string = 'high'): Promise<Blob> {
    const encoded = encodeURIComponent(documentIdentifier);
    const response = await api.get(`/documents/${encoded}/preview/${pageNumber}`, {
      params: { quality },
      responseType: 'blob'
    });
    return response.data;
  }

  getTiffThumbnailUrl(documentIdentifier: string, pageNumber: number, width: number, height: number): string {
    const encoded = encodeURIComponent(documentIdentifier);
    return `${api.defaults.baseURL}/documents/${encoded}/thumbnail/${pageNumber}?width=${width}&height=${height}`;
  }

  getTiffPreviewUrl(documentIdentifier: string, pageNumber: number): string {
    const encoded = encodeURIComponent(documentIdentifier);
    return `${api.defaults.baseURL}/documents/${encoded}/preview/${pageNumber}`;
  }
}

export default new DocumentService();