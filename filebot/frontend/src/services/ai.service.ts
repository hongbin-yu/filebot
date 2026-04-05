/**
 * AI服务
 * 提供AI相关功能，如网站爬取、文档分类等
 */

import api from './api';

// 网站爬取请求接口
export interface WebsiteCrawlRequest {
  url: string;
  depth: number;
  folder_id: string;
  include_images?: boolean;
  follow_external_links?: boolean;
  respect_robots_txt?: boolean;
}

// 网站爬取响应接口
export interface WebsiteCrawlResponse {
  task_id: string;
  status: string;
  url: string;
  depth: number;
  estimated_pages?: number;
  started_at: string;
  message?: string;
}

// 网站爬取状态接口
export interface WebsiteCrawlStatus {
  task_id: string;
  status: string;
  url: string;
  depth: number;
  pages_crawled: number;
  pages_processed: number;
  images_crawled: number;
  errors: string[];
  started_at: string;
  updated_at: string;
  estimated_completion?: string;
}

// 网站爬取任务列表接口
export interface WebsiteCrawlTaskList {
  tasks: WebsiteCrawlStatus[];
  total: number;
  pending: number;
  active: number;
  completed: number;
  failed: number;
}

// AI分类请求接口
export interface AIClassifyRequest {
  document_id?: string;
  text?: string;
  model?: string;
  extract_text?: boolean;
}

// AI分类响应接口
export interface AIClassifyResponse {
  document_id?: string;
  success: boolean;
  category?: string;
  ai_category?: string;
  document_type?: string;
  confidence?: number;
  processing_time?: number;
  model?: string;
  raw_response?: string;
  error?: string;
  timestamp: string;
}

// AI分类类别接口
export interface AICategory {
  value: string;
  label: string;
  document_type: string;
}

const aiService = {
  /**
   * 爬取网站内容
   */
  async crawlWebsite(request: WebsiteCrawlRequest): Promise<WebsiteCrawlResponse> {
    const response = await api.post<WebsiteCrawlResponse>('/ai/crawl-website', request);
    return response.data;
  },

  /**
   * 获取网站爬取任务状态
   */
  async getCrawlStatus(taskId: string): Promise<WebsiteCrawlStatus> {
    const response = await api.get<WebsiteCrawlStatus>(`/ai/crawl-status/${taskId}`);
    return response.data;
  },

  /**
   * 获取所有网站爬取任务列表
   */
  async getCrawlTasks(params?: {
    limit?: number;
    offset?: number;
    status_filter?: string;
  }): Promise<WebsiteCrawlTaskList> {
    const response = await api.get<WebsiteCrawlTaskList>('/ai/crawl-tasks', { params });
    return response.data;
  },

  /**
   * 分类文档
   */
  async classifyDocument(request: AIClassifyRequest): Promise<AIClassifyResponse> {
    const response = await api.post<AIClassifyResponse>('/ai/classify', request);
    return response.data;
  },

  /**
   * 批量分类文档
   */
  async classifyDocumentsBatch(documentIds: string[]): Promise<AIClassifyResponse[]> {
    const response = await api.post<AIClassifyResponse[]>('/ai/classify-batch', { document_ids: documentIds });
    return response.data;
  },

  /**
   * 测试AI服务连接
   */
  async testConnection(): Promise<{
    status: string;
    service: string;
    url: string;
    default_model: string;
  }> {
    const response = await api.get('/ai/test-connection');
    return response.data;
  },

  /**
   * 获取可用的AI分类类别
   */
  async getCategories(): Promise<{
    categories: AICategory[];
    count: number;
  }> {
    const response = await api.get('/ai/categories');
    return response.data;
  }
};

export default aiService;