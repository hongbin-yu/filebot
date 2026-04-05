import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/auth.service';
import './ClientLogin.css';

const ClientLogin: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // 使用现有的认证服务
      // 注意：实际部署中，可能需要为Client创建专门的登录端点
      const response = await authService.login({ username, password });
      
      // 检查用户是否有Client访问权限
      // 这里可以添加权限检查逻辑
      
      // 存储Client特定的标记（可选）
      if (rememberMe) {
        localStorage.setItem('client_remember', 'true');
      }
      
      // 导航到Client App选择页面 (APP-first导航)
      navigate('/client/apps');
      
    } catch (err: any) {
      console.error('Client登录失败:', err);
      
      // 提供友好的错误消息
      if (err.response?.status === 401) {
        setError('用户名或密码错误');
      } else if (err.response?.status === 403) {
        setError('此账户没有Client访问权限');
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.message) {
        setError(err.message);
      } else {
        setError('登录失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    // 演示账户（如果后端有配置）
    setUsername('demo-client');
    setPassword('demo123');
  };

  const handleBackToMain = () => {
    // 返回到主系统登录页
    navigate('/login');
  };

  return (
    <div className="client-login min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo和标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-lg mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-800">FileBot Client Portal</h1>
          <p className="text-gray-600 mt-2">PDF文档浏览门户</p>
        </div>
        
        {/* 登录卡片 */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Client登录</h2>
          <p className="text-gray-600 mb-6">请输入您的账户信息以访问PDF文档</p>
          
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              <div className="flex items-center">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span>{error}</span>
              </div>
            </div>
          )}
          
          <form onSubmit={handleSubmit}>
            <div className="space-y-5">
              {/* 用户名输入 */}
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                  用户名
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="输入用户名"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                  disabled={loading}
                  required
                />
              </div>
              
              {/* 密码输入 */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  密码
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入密码"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                  disabled={loading}
                  required
                />
              </div>
              
              {/* 记住我和忘记密码 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    disabled={loading}
                  />
                  <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                    记住我
                  </label>
                </div>
                
                <button
                  type="button"
                  className="text-sm text-blue-600 hover:text-blue-800"
                  onClick={() => alert('请联系管理员重置密码')}
                  disabled={loading}
                >
                  忘记密码?
                </button>
              </div>
              
              {/* 登录按钮 */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    登录中...
                  </div>
                ) : '登录'}
              </button>
              
              {/* 演示账户按钮 */}
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={loading}
                className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors text-sm"
              >
                使用演示账户
              </button>
            </div>
          </form>
          
          {/* 分隔线 */}
          <div className="my-6 flex items-center">
            <div className="flex-1 border-t border-gray-300"></div>
            <div className="mx-4 text-sm text-gray-500">或者</div>
            <div className="flex-1 border-t border-gray-300"></div>
          </div>
          
          {/* 返回主系统 */}
          <div className="text-center">
            <p className="text-gray-600 text-sm mb-3">需要管理系统访问权限?</p>
            <button
              type="button"
              onClick={handleBackToMain}
              className="text-blue-600 hover:text-blue-800 font-medium"
              disabled={loading}
            >
              返回主系统登录 →
            </button>
          </div>
        </div>
        
        {/* 页脚说明 */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>© 2026 FileBot Client Portal. 仅供授权用户使用。</p>
          <p className="mt-1">这是一个只读界面，仅用于浏览PDF文档。</p>
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-blue-700">
              <strong>注意：</strong> 此门户仅显示PDF格式文档。其他格式文档请联系管理员。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientLogin;