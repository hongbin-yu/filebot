import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import appService from '../services/app.service';

const ClientAppSelection: React.FC = () => {
  const navigate = useNavigate();
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApps();
  }, []);

  const fetchApps = async () => {
    try {
      setLoading(true);
      // 获取所有应用（Client门户显示所有应用）
      const data = await appService.getApps();
      setApps(data);
    } catch (err: any) {
      console.error('获取App列表失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAppClick = (app: any) => {
    // 如果应用有重定向URL，则重定向到外部URL
    if (app.redirect_url) {
      window.open(app.redirect_url, '_blank');
      return;
    }
    
    // 否则导航到该App的公共门户
    const appSlug = app.slug || app.id;
    navigate(`/apps/${appSlug}`);
  };

  // 获取应用图标显示
  const getAppIcon = (app: any) => {
    if (app.icon) {
      return app.icon;
    }
    // 默认图标：应用名称的首字母
    return app.name.charAt(0).toUpperCase();
  };

  // 获取应用类型显示
  const getAppType = (app: any) => {
    const icon = app.icon || '';
    const name = app.name || '';
    
    // 根据图标或名称判断应用类型
    if (icon.includes('🌐') || name.toLowerCase().includes('web') || name.toLowerCase().includes('bot')) {
      return 'WebBot应用';
    } else if (icon.includes('📁') || icon.includes('🗂️')) {
      return '文档管理';
    } else if (icon.includes('🏛️') || icon.includes('🏢')) {
      return '政府服务';
    } else if (icon.includes('🧾') || icon.includes('💸')) {
      return '发票系统';
    } else if (icon.includes('🔍') || icon.includes('📊')) {
      return '数据分析';
    } else {
      return '应用';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* 头部 */}
        <header className="mb-10">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">🏠 FileBot + WebBot 统一仪表板</h1>
              <p className="text-gray-600 mt-2">集成所有应用到单个界面 • 支持内部应用和外部重定向</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">统一门户</span>
              <Link 
                to="/admin/apps"
                className="px-4 py-2 border border-blue-600 text-blue-600 rounded hover:bg-blue-50"
              >
                管理后台
              </Link>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-700">
              <span className="font-medium">统一仪表板说明：</span>
              现在FileBot和WebBot应用集成到一个界面，支持图标显示和外部重定向。
              点击应用卡片即可访问内部应用或打开外部应用（如WebBot）。
            </p>
          </div>
        </header>

        {/* 统一仪表板标题 */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">🏠 FileBot + WebBot 统一仪表板</h2>
          <p className="text-gray-600">集成所有应用到一个界面，点击图标即可访问</p>
        </div>

        {/* 应用网格 */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">加载应用中...</p>
          </div>
        ) : apps.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="text-gray-400 mb-6">
              <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
              </svg>
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">暂无应用</h3>
            <p className="text-gray-500 mb-6">当前没有可用的应用。请联系管理员创建应用。</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {apps.map(app => (
              <div 
                key={app.id}
                className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer border border-gray-200 hover:border-blue-300 hover:transform hover:-translate-y-1"
                onClick={() => handleAppClick(app)}
              >
                <div className="p-6">
                  <div className="flex items-center mb-4">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center mr-4" 
                         style={{ 
                           backgroundColor: app.icon && app.icon.includes('🌐') ? '#E0F2FE' : 
                                         app.icon && app.icon.includes('🏛️') ? '#FEF3C7' :
                                         app.icon && app.icon.includes('🧾') ? '#DCFCE7' :
                                         '#E0E7FF'
                         }}>
                      <span className="text-2xl">
                        {getAppIcon(app)}
                      </span>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-gray-800">{app.name}</h3>
                      <div className="flex items-center mt-1">
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                          {getAppType(app)}
                        </span>
                        {app.redirect_url && (
                          <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                            外部应用
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <p className="text-gray-600 mb-4">{app.description || '暂无描述'}</p>
                  
                  {app.redirect_url && (
                    <div className="mb-4 p-2 bg-blue-50 rounded border border-blue-100">
                      <p className="text-xs text-blue-800 truncate">
                        <span className="font-medium">重定向到:</span> {app.redirect_url}
                      </p>
                    </div>
                  )}
                  
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500">
                      {app.redirect_url ? '点击打开外部应用' : '点击进入应用'}
                    </span>
                    <span className="text-blue-600 font-medium">
                      {app.redirect_url ? '↗' : '→'}
                    </span>
                  </div>
                </div>
                <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>ID: {app.id.substring(0, 8)}...</span>
                    {app.redirect_url ? (
                      <span className="text-blue-600">外部链接</span>
                    ) : (
                      <span>内部应用</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 底部信息 */}
        <footer className="mt-12 pt-8 border-t border-gray-200">
          <div className="text-center text-gray-500 text-sm">
            <p>🏠 FileBot + WebBot 统一仪表板 • 集成所有应用到单个界面</p>
            <p className="mt-1">
              支持内部应用和外部重定向应用（如WebBot） • 
              <span className="text-blue-600 ml-1">图标:</span> 
              <span className="mx-2">📁 文档管理</span>
              <span className="mx-2">🌐 WebBot应用</span>
              <span className="mx-2">🏛️ 政府服务</span>
              <span className="mx-2">🧾 发票系统</span>
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default ClientAppSelection;