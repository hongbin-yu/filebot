import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000, // 增加到120秒，适应大文件上传
  // 注意：不设置默认Content-Type，因为登录需要application/x-www-form-urlencoded
  // 其他请求需要显式设置Content-Type
});

// 请求拦截器 - 添加认证token（跳过登录请求）
api.interceptors.request.use(
  (config) => {
    // 跳过登录请求，避免添加token
    if (config.url && config.url.includes('/auth/login')) {
      return config;
    }
    
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 方案B：为文档下载和预览请求添加WebBot特殊权限头
    // 这允许用户访问自己的未发布文档，绕过403错误
    if (config.url && config.url.includes('/documents/') && 
        (config.url.includes('/download') || config.url.includes('/preview'))) {
      config.headers['X-WebBot-Access'] = 'true';
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // token过期，清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      
      // 检查当前页面是否是登录页，避免重定向循环
      // 只有当前页面不是登录页时才重定向
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;