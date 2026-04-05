import api from './api';

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
}

export interface DocumentUploadRequest {
  file: File;
  folder_id: string;
  title?: string;
  description?: string;
}

class DocumentService {
  // 获取文件夹中的文档
  async getDocumentsByFolderId(folderId: string, params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Document[]> {
    // 开发模式：使用模拟数据
    if (DEV_MODE) {
      console.log('🔧 开发模式：getDocumentsByFolderId, folderId:', folderId);
      
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
      
      console.log(`📊 返回 ${mockDocuments.length} 个模拟文档 (folder: ${folderId})`);
      return mockDocuments;
    }
    
    // 生产模式：调用真实API
    const response = await api.get('/documents/', { 
      params: {
        folder_id: folderId,
        ...params
      }
    });
    return response.data;
  }

  // 获取单个文档详情
  async getDocumentById(documentId: string): Promise<Document> {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  }

  // 上传文档
  async uploadDocument(data: DocumentUploadRequest): Promise<Document> {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('folder_id', data.folder_id);
    
    if (data.title) {
      formData.append('title', data.title);
    }
    if (data.description) {
      formData.append('description', data.description);
    }
    
    const response = await api.post('/documents/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  }

  // 更新文档
  async updateDocument(documentId: string, data: {
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
    const response = await api.put(`/documents/${documentId}`, data);
    return response.data;
  }

  // 删除文档
  async deleteDocument(documentId: string): Promise<void> {
    await api.delete(`/documents/${documentId}`);
  }

  // 搜索文档
  async searchDocuments(params: {
    q?: string;
    folder_id?: string;
    file_type?: string;
    conversion_status?: string;
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
    
    if (params.skip !== undefined) {
      searchParams.skip = params.skip;
    }
    
    if (params.limit !== undefined) {
      searchParams.limit = params.limit;
    }
    
    // 调用搜索端点：/search/documents
    const response = await api.get('/search/documents', { params: searchParams });
    return response.data;
  }

  // 获取文档的转换状态
  async getConversionStatus(documentId: string): Promise<any> {
    const response = await api.get(`/documents/${documentId}/conversion-status`);
    return response.data;
  }

  // 下载文档
  async downloadDocument(documentId: string, downloadType: string = 'original'): Promise<Blob> {
    const response = await api.get(`/documents/${documentId}/download`, {
      params: { download_type: downloadType },
      responseType: 'blob'
    });
    return response.data;
  }

  // 预览文档
  async previewDocument(documentId: string): Promise<Blob> {
    const response = await api.get(`/documents/${documentId}/preview`, {
      responseType: 'blob'
    });
    return response.data;
  }
}

export default new DocumentService();