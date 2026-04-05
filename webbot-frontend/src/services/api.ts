/**
 * WebBot API客户端服务
 * 后端运行在 http://127.0.0.1:8000，通过Vite代理转发
 */

const API_BASE_URL = '/api/v1';

// 组件模板接口
export interface ComponentTemplate {
  id: string;
  name: string;
  display_name: string;
  description: string;
  html_template: string;
  css_template?: string;
  js_template?: string;
  category: string;
  version: string;
  created_at: string;
  updated_at: string;
  icon?: string;
  properties?: Record<string, unknown>;
  dependencies?: unknown[];
  wet_boew_compliant?: boolean;
  accessibility_checked?: boolean;
  tags?: string[];
  author?: string;
  status?: string;
  usage_count?: number;
}

// 组件实例接口
export interface ComponentInstance {
  id: string;
  template_id: string;
  page_id?: string;
  position_x: number;
  position_y: number;
  alignment?: 'left' | 'center' | 'right'; // 新增：对齐方式
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * 获取所有组件模板
 */
export async function fetchComponentTemplates(): Promise<ComponentTemplate[]> {
  try {
    console.log(`🌐 调用组件模板API: ${API_BASE_URL}/components/templates`);
    const response = await fetch(`${API_BASE_URL}/components/templates`);
    console.log(`📡 API响应状态: ${response.status} ${response.statusText}`);
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }
    const data = await response.json();
    console.log(`📦 API响应数据:`, data);
    // 处理直接数组或包装在templates字段中的响应
    const templates = Array.isArray(data) ? data : data.templates || [];
    console.log(`🎯 解析后的模板数量: ${templates.length}`);
    return templates;
  } catch (error) {
    console.error('获取组件模板失败:', error);
    return [];
  }
}

/**
 * 根据ID获取组件模板
 */
export async function fetchComponentTemplateById(id: string): Promise<ComponentTemplate | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/components/templates/${id}`);
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`获取组件模板 ${id} 失败:`, error);
    return null;
  }
}

/**
 * 创建组件实例
 */
export async function createComponentInstance(
  templateId: string,
  position: { x: number; y: number },
  configuration: Record<string, unknown>
): Promise<ComponentInstance | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/components/instances`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        template_id: templateId,
        position_x: position.x,
        position_y: position.y,
        configuration,
      }),
    });
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('创建组件实例失败:', error);
    return null;
  }
}

/**
 * 更新组件实例
 */
export async function updateComponentInstance(
  instanceId: string,
  updates: Partial<ComponentInstance>
): Promise<ComponentInstance | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/components/instances/${instanceId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`更新组件实例 ${instanceId} 失败:`, error);
    return null;
  }
}

/**
 * 删除组件实例
 */
export async function deleteComponentInstance(instanceId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/components/instances/${instanceId}`, {
      method: 'DELETE',
    });
    return response.ok;
  } catch (error) {
    console.error(`删除组件实例 ${instanceId} 失败:`, error);
    return false;
  }
}

/**
 * 获取系统健康状态
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch('/health');
    if (!response.ok) return false;
    const data = await response.json();
    return data.status === 'healthy' && data.database === 'connected';
  } catch (error) {
    console.error('健康检查失败:', error);
    return false;
  }
}

/**
 * 页面渲染相关接口和函数
 */

// 页面渲染请求接口
export interface PageRenderRequest {
  component_instances: Array<{
    id: string;
    template_id: string;
    configuration: Record<string, unknown>;
    position?: { x: number; y: number };
    alignment?: 'left' | 'center' | 'right';
  }>;
  page_title?: string;
  include_wet_boew?: boolean;
  include_accessibility?: boolean;
  include_admin_resources?: boolean;
  include_header_footer?: boolean;
}

// 页面渲染响应接口
export interface PageRenderResponse {
  success: boolean;
  html: string;
  component_count: number;
  templates_used: string[];
  alignment_stats: {
    left: number;
    center: number;
    right: number;
  };
  render_time: string;
  error?: string;
}

/**
 * 渲染页面
 */
export async function renderPage(renderRequest: PageRenderRequest): Promise<PageRenderResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/components/render-page`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(renderRequest),
    });

    if (!response.ok) {
      throw new Error(`渲染API请求失败: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('页面渲染失败:', error);
    return {
      success: false,
      html: `<html><body><h1>渲染错误</h1><p>${error}</p></body></html>`,
      component_count: 0,
      templates_used: [],
      alignment_stats: { left: 0, center: 0, right: 0 },
      render_time: new Date().toISOString(),
      error: String(error),
    };
  }
}

/**
 * 页面管理相关接口和函数
 */

// 页面接口
export interface Page {
  id: string;
  title: string;
  content?: string;
  language: 'en' | 'fr';
  path?: string;
  parent_id?: string;
  other_lang_page_id?: string;
  status: 'draft' | 'published' | 'archived';
  metadata?: Record<string, unknown>;
  created_by?: string;
  created_at: string;
  last_modified: string;
  last_published?: string;
}

// 创建页面请求
export interface PageCreateRequest {
  title: string;
  content?: string;
  language?: 'en' | 'fr';
  path?: string;
  parent_id?: string;
  other_lang_page_id?: string;
  status?: 'draft' | 'published' | 'archived';
  metadata?: Record<string, unknown>;
}

// 更新页面请求
export interface PageUpdateRequest {
  title?: string;
  content?: string;
  language?: 'en' | 'fr';
  parent_id?: string;
  other_lang_page_id?: string;
  status?: 'draft' | 'published' | 'archived';
  metadata?: Record<string, unknown>;
}

/**
 * 获取所有页面
 */
export async function fetchPages(): Promise<Page[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/pages`);
    if (!response.ok) {
      throw new Error(`获取页面列表失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('获取页面列表失败:', error);
    return [];
  }
}

/**
 * 根据ID获取页面
 */
export async function fetchPageById(pageId: string): Promise<Page | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/pages/${encodeURIComponent(pageId)}`);
    if (!response.ok) {
      throw new Error(`获取页面失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`获取页面 ${pageId} 失败:`, error);
    return null;
  }
}

/**
 * 创建新页面
 */
export async function createPage(pageData: PageCreateRequest): Promise<Page | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/pages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(pageData),
    });
    if (!response.ok) {
      throw new Error(`创建页面失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('创建页面失败:', error);
    return null;
  }
}

/**
 * 更新页面
 */
export async function updatePage(pageId: string, updates: PageUpdateRequest): Promise<Page | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/pages/${encodeURIComponent(pageId)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      throw new Error(`更新页面失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`更新页面 ${pageId} 失败:`, error);
    return null;
  }
}

/**
 * 删除页面
 */
export async function deletePage(pageId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/pages/${encodeURIComponent(pageId)}`, {
      method: 'DELETE',
    });
    return response.ok;
  } catch (error) {
    console.error(`删除页面 ${pageId} 失败:`, error);
    return false;
  }
}

/**
 * 获取页面模板列表
 */
export async function fetchPageTemplates(): Promise<Page[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/pages/templates`);
    if (!response.ok) {
      throw new Error(`获取页面模板失败: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('获取页面模板失败:', error);
    return [];
  }
}
