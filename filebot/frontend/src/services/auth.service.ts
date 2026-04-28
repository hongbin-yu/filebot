import api from './api';
import i18n from '../i18n';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
}

class AuthService {
  // 用户登录 - 支持两种调用方式
  async login(username: string, password: string): Promise<boolean>;
  async login(data: LoginRequest): Promise<TokenResponse>;
  async login(arg1: string | LoginRequest, arg2?: string): Promise<boolean | TokenResponse> {
    let username: string;
    let password: string;
    
    if (typeof arg1 === 'string' && typeof arg2 === 'string') {
      // 调用方式: login(username, password)
      username = arg1;
      password = arg2;
    } else if (typeof arg1 === 'object') {
      // 调用方式: login({username, password})
      username = (arg1 as LoginRequest).username;
      password = (arg1 as LoginRequest).password;
    } else {
      throw new Error('Invalid login arguments');
    }
    
    // 自动处理邮箱地址：如果输入包含@符号，提取用户名部分
    // 例如：demo@filebot.app → demo
    let finalUsername = username;
    if (username.includes('@')) {
      finalUsername = username.split('@')[0];
    }
    
    // 使用URLSearchParams创建application/x-www-form-urlencoded格式的数据
    const params = new URLSearchParams();
    params.append('username', finalUsername);
    params.append('password', password);
    
    console.log('Login attempt:', { finalUsername, password: '***' });
    console.log('Request data:', params.toString());
    
    const response = await api.post('/auth/login', params.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    console.log('Login response:', response.data);
    
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user_info', JSON.stringify(response.data.user));
      return true;
    }
    
    return false;
  }

  // 用户注册
  async register(data: RegisterRequest): Promise<any> {
    const response = await api.post('/auth/register', data);
    return response.data;
  }

  // 获取当前用户信息
  async getCurrentUser(): Promise<UserInfo> {
    const response = await api.get('/auth/me');
    const userInfo = response.data;
    localStorage.setItem('user_info', JSON.stringify(userInfo));
    return userInfo;
  }

  // 刷新token
  async refreshToken(): Promise<TokenResponse> {
    const response = await api.post('/auth/refresh');
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    return response.data;
  }

  // 退出登录
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    // 可以调用后端logout接口，但非必需
    // api.post('/auth/logout');
  }

  // 检查是否已登录
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }

  // 获取用户信息（从本地存储）
  getUserInfo(): UserInfo | null {
    const userStr = localStorage.getItem('user_info');
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  }
}

export default new AuthService();