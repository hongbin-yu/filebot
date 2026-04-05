import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import appService, { App, CreateAppRequest } from '../../services/app.service';
import CreateAppModal from '../../components/apps/CreateAppModal';
import EditAppModal from '../../components/apps/EditAppModal';

const AdminAppsDashboard: React.FC = () => {
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载应用数据
  useEffect(() => {
    const loadApps = async () => {
      try {
        setLoading(true);
        const appsData = await appService.getApps();
        setApps(appsData);
      } catch (err) {
        console.error('加载应用失败:', err);
        setError('无法加载应用列表，请检查网络连接或重新登录。');
      } finally {
        setLoading(false);
      }
    };

    loadApps();
  }, []);

  // 创建应用模态框状态
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  // 编辑应用模态框状态
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingApp, setEditingApp] = useState<App | null>(null);

  // 处理创建应用
  const handleCreateApp = () => {
    setIsCreateModalOpen(true);
  };

  // 处理创建成功
  const handleCreateSuccess = (newApp: App) => {
    // 将新应用添加到列表
    setApps(prevApps => [...prevApps, newApp]);
  };

  // 关闭模态框
  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
  };

  // 处理编辑成功
  const handleEditSuccess = (updatedApp: App) => {
    // 更新应用列表中的对应应用
    setApps(prevApps => prevApps.map(app => 
      app.id === updatedApp.id ? updatedApp : app
    ));
  };

  // 关闭编辑模态框
  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setEditingApp(null);
  };

  // 处理删除应用
  const handleDeleteApp = async (appId: string, appName: string) => {
    if (!window.confirm(`确定要删除应用 "${appName}" 吗？此操作将删除所有关联的文件夹和文档，且无法恢复。`)) {
      return;
    }

    try {
      await appService.deleteApp(appId);
      // 从列表中移除已删除的应用
      setApps(prevApps => prevApps.filter(app => app.id !== appId));
    } catch (err) {
      console.error('删除应用失败:', err);
      alert('删除应用失败，请稍后重试。');
    }
  };

  // 处理编辑应用
  const handleEditApp = (appId: string) => {
    const appToEdit = apps.find(app => app.id === appId);
    if (appToEdit) {
      setEditingApp(appToEdit);
      setIsEditModalOpen(true);
    } else {
      alert('找不到要编辑的应用');
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">应用管理</h1>
          <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={handleCreateApp}>
            + 创建应用
          </button>
        </div>
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">加载应用中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">应用管理</h1>
          <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={handleCreateApp}>
            + 创建应用
          </button>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">加载失败</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">应用管理</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={handleCreateApp}>
          + 创建应用
        </button>
      </div>

      {apps.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">暂无应用</h3>
          <p className="text-yellow-700 mb-4">您还没有创建任何应用，点击上方按钮创建第一个应用。</p>
          <button className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700" onClick={handleCreateApp}>
            创建第一个应用
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">所有应用 ({apps.length})</h2>
          </div>
          
          <div className="divide-y">
            {apps.map(app => (
              <div key={app.id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-center">
                  <div>
                    <Link 
                      to={`/admin/apps/${app.slug || app.id}`}
                      className="text-lg font-medium text-blue-600 hover:text-blue-800"
                    >
                      {app.name}
                    </Link>
                    <p className="text-gray-600 mt-1">{app.description || '暂无描述'}</p>
                    <div className="mt-2 text-sm text-gray-500">
                      <span>ID: {app.id}</span>
                      {app.slug && <span className="ml-4">Slug: {app.slug}</span>}
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button 
                      onClick={() => handleEditApp(app.id)}
                      className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    >
                      编辑
                    </button>
                    <button 
                      onClick={() => handleDeleteApp(app.id, app.name)}
                      className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-300"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-medium text-blue-800">新架构说明</h3>
        <p className="text-blue-700 mt-1">
          FileBot 已简化为两层结构：应用 → 文件夹 → 文档。抽屉层已移除。
        </p>
        <div className="mt-2 text-sm text-blue-600">
          <p>• Admin URL前缀：<code>/admin/apps</code></p>
          <p>• Client URL前缀：<code>/apps</code>（公共门户）</p>
          <p>• 数据已清空，从头开始</p>
        </div>
      </div>

      {/* 创建应用模态框 */}
      <CreateAppModal 
        isOpen={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        onSuccess={handleCreateSuccess}
      />

      {/* 编辑应用模态框 */}
      <EditAppModal 
        isOpen={isEditModalOpen}
        onClose={handleCloseEditModal}
        onSuccess={handleEditSuccess}
        app={editingApp}
      />
    </div>
  );
};

export default AdminAppsDashboard;