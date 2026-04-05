import api from './api';

export interface Document {
  id: string;
  title?: string;
  description?: string;
  document_number?: string;
  status: string;
  type: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  mime_type: string;
  conversion_status: string;
  page_count?: number;
  folder_id: string;
  uploaded_by: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentUploadRequest {
  file: File;
  folder_id: string;
  title?: string;
  description?: string;
  document_type?: string;
}

export interface DocumentSearchParams {
  title?: string;
  description?: string;
  document_number?: string;
  status?: string;
  document_type?: string;
  conversion_status?: string;
  folder_id?: string;
  drawer_id?: string;
  app_id?: string;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: string;
}

class DocumentService {
  // 获取文档列表
  async getDocuments(params: DocumentSearchParams = {}): Promise<Document[]> {
    const response = await api.get('/documents/', { params });
    return response.data;
  }

  // 获取单个文档详情
  async getDocumentById(documentId: string): Promise<Document> {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  }

  // 上传文档
  async uploadDocument(data: DocumentUploadRequest): Promise<any> {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('folder_id', data.folder_id);
    if (data.title) formData.append('title', data.title);
    if (data.description) formData.append('description', data.description);
    if (data.document_type) formData.append('document_type', data.document_type);

    const response = await api.post('/documents/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // 更新文档信息
  async updateDocument(documentId: string, data: Partial<Document>): Promise<Document> {
    const response = await api.put(`/documents/${documentId}`, data);
    return response.data;
  }

  // 删除文档
  async deleteDocument(documentId: string): Promise<void> {
    await api.delete(`/documents/${documentId}`);
  }

  // 批量删除文档
  async batchDeleteDocuments(documentIds: string[]): Promise<void> {
    await api.post('/documents/batch/delete', { document_ids: documentIds });
  }

  // 批量归档文档
  async batchArchiveDocuments(documentIds: string[]): Promise<void> {
    await api.post('/documents/batch/archive', { document_ids: documentIds });
  }

  // 下载文档
  async downloadDocument(documentId: string, downloadType: 'original' | 'pdf' = 'original'): Promise<Blob> {
    const response = await api.get(`/documents/${documentId}/download`, {
      params: { download_type: downloadType },
      responseType: 'blob',
    });
    return response.data;
  }

  // 重试转换
  async retryConversion(documentId: string): Promise<void> {
    await api.post(`/documents/${documentId}/retry-conversion`);
  }

  // 搜索文档
  async searchDocuments(params: DocumentSearchParams): Promise<Document[]> {
    const response = await api.get('/search/documents', { params });
    return response.data;
  }

  // 高级搜索
  async advancedSearch(params: {
    search_mode?: 'and' | 'or';
    keywords?: string;
    search_fields?: string;
    folder_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<any> {
    const response = await api.get('/search/advanced', { params });
    return response.data;
  }

  // ========== TIFF相关方法 ==========

  // 获取TIFF文件信息
  async getTiffInfo(documentId: string): Promise<any> {
    const response = await api.get(`/documents/${documentId}/tiff-info`);
    return response.data;
  }

  // 获取TIFF缩略图URL
  getTiffThumbnailUrl(documentId: string, pageNumber: number, width: number = 200, height: number = 200): string {
    return `/documents/${documentId}/tiff-thumbnail/${pageNumber}?width=${width}&height=${height}`;
  }

  // 获取TIFF预览图URL
  getTiffPreviewUrl(documentId: string, pageNumber: number, maxWidth: number = 1200, maxHeight: number = 1600): string {
    return `/documents/${documentId}/tiff-preview/${pageNumber}?max_width=${maxWidth}&max_height=${maxHeight}`;
  }

  // 提取TIFF页面
  async extractTiffPages(documentId: string, pageNumbers: number[], outputFormat: 'pdf' | 'tiff' = 'pdf'): Promise<Blob> {
    const params = { page_numbers: pageNumbers, output_format: outputFormat };
    const response = await api.post(`/documents/${documentId}/extract-tiff-pages`, null, {
      params,
      responseType: 'blob',
    });
    return response.data;
  }

  // 获取TIFF缩略图（Blob格式）
  async getTiffThumbnail(documentId: string, pageNumber: number, width: number = 200, height: number = 200): Promise<Blob> {
    const response = await api.get(`/documents/${documentId}/tiff-thumbnail/${pageNumber}`, {
      params: { width, height },
      responseType: 'blob',
    });
    return response.data;
  }

  // 获取TIFF预览图（Blob格式）
  async getTiffPreview(documentId: string, pageNumber: number, quality: 'high' | 'low' = 'high'): Promise<Blob> {
    const maxWidth = quality === 'high' ? 1200 : 600;
    const maxHeight = quality === 'high' ? 1600 : 800;
    const response = await api.get(`/documents/${documentId}/tiff-preview/${pageNumber}`, {
      params: { max_width: maxWidth, max_height: maxHeight },
      responseType: 'blob',
    });
    return response.data;
  }
}

export default new DocumentService();