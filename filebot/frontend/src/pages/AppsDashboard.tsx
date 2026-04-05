import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import appService, { App, AppUpdateRequest } from '../services/app.service';
import authService from '../services/auth.service';
import { generateApplicationSlug, toSlug } from '../utils/slugUtils';

const AppsDashboard: React.FC = () => {
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  
  // 应用管理状态
  const [editingApp, setEditingApp] = useState<App | null>(null);
  const [editForm, setEditForm] = useState<AppUpdateRequest>({});
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [appToDelete, setAppToDelete] = useState<App | null>(null);
  const [configuringApp, setConfiguringApp] = useState<App | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configForm, setConfigForm] = useState<Record<string, any>>({});
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAppForm, setNewAppForm] = useState({ name: '', description: '' });
  const [actionLoading, setActionLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [newIndexName, setNewIndexName] = useState<string>('');

  useEffect(() => {
    fetchApps();
  }, []);

  const fetchApps = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching applications...');
      const data = await appService.getApps();
      console.log('Apps data received:', data);
      setApps(data || []);
    } catch (err: any) {
      console.error('Failed to fetch apps:', err);
      console.error('Error details:', err.response?.data || err.message);
      
      // 检查是否是401认证错误
      if (err.response?.status === 401) {
        setError('Authentication required. Please login to access applications.');
      } else {
        setError(`Failed to load applications: ${getErrorMessage(err)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAppSelect = (app: App) => {
    // 生成应用slug并导航到该应用的文件夹页面
    // 构建现有应用slug集合（排除当前应用自身）
    const existingSlugs = new Set<string>();
    apps.forEach(a => {
      if (a.id !== app.id) { // 排除当前应用
        // 为每个其他应用生成其slug，用于重复检测
        const otherAppExistingSlugs = new Set<string>();
        apps.forEach(a2 => {
          if (a2.id !== a.id) {
            const baseSlug2 = toSlug(a2.name);
            otherAppExistingSlugs.add(baseSlug2);
          }
        });
        const otherAppSlug = generateApplicationSlug(a.name, a.id, otherAppExistingSlugs);
        existingSlugs.add(otherAppSlug);
      }
    });
    
    const appSlug = generateApplicationSlug(app.name, app.id, existingSlugs);
    // 传递原始appId作为导航状态，以便后端API调用
    navigate(`/${appSlug}`, { state: { appId: app.id } });
  };

  // 解析错误消息
  const getErrorMessage = (err: any): string => {
    if (!err) return 'Unknown error';
    
    // 优先使用err.message
    if (err.message && typeof err.message === 'string') {
      return err.message;
    }
    
    // 检查API响应错误
    if (err.response?.data) {
      const data = err.response.data;
      
      // 如果是数组（如422验证错误）
      if (Array.isArray(data.detail)) {
        return data.detail.map((item: any) => 
          `${item.loc?.join('.')}: ${item.msg}`
        ).join(', ');
      }
      
      // 如果是对象但不是数组
      if (data.detail && typeof data.detail === 'string') {
        return data.detail;
      }
      
      // 如果是普通对象
      if (typeof data === 'object') {
        try {
          return JSON.stringify(data);
        } catch {
          return 'Invalid error data format';
        }
      }
    }
    
    // 最后尝试字符串化整个错误
    try {
      return JSON.stringify(err);
    } catch {
      return 'Failed to parse error';
    }
  };

  const handleOpenCreateModal = () => {
    setNewAppForm({ name: '', description: '' });
    setShowCreateModal(true);
  };

  const handleCreateApp = async (name: string = "My Application", description: string = "New application") => {
    try {
      setActionLoading(true);
      setError(null);
      
      console.log('Starting create application...');
      
      // 获取当前用户信息
      const userInfo = authService.getUserInfo();
      console.log('User info:', userInfo);
      
      if (!userInfo || !userInfo.id) {
        console.log('User not authenticated, redirecting to login...');
        // 未登录，重定向到登录页
        window.location.href = '/login';
        return;
      }
      
      console.log('Creating application with owner_id:', userInfo.id);
      
      // 创建应用，包含owner_id
      const newApp = await appService.createApp({
        name: name,
        description: description,
        app_type: "document_management",
        owner_id: userInfo.id
      });
      
      console.log('Application created:', newApp);
      
      // 刷新应用列表
      await fetchApps();
      
      setSuccessMessage(`Application "${name}" created successfully!`);
      setTimeout(() => setSuccessMessage(null), 3000);
      
      // 可选：自动导航到新创建的应用
      // navigate(`/apps/${newApp.id}`);
      
    } catch (err: any) {
      console.error('Failed to create application:', err);
      // 详细记录错误信息
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        stack: err.stack
      });
      
      const errorMsg = getErrorMessage(err);
      console.log('Formatted error message:', errorMsg);
      setError(`Failed to create application: ${errorMsg}`);
    } finally {
      setActionLoading(false);
    }
  };

  // 打开编辑模态框
  const handleEditApp = (app: App, e?: React.MouseEvent) => {
    e?.stopPropagation();
    console.log('Opening edit modal for app (full object):', app);
    console.log('App config:', app.config);
    console.log('App settings:', app.settings);
    
    // 检查是否有settings字段，如果有，使用settings作为配置
    const appSettings = app.settings;
    const appConfig = app.config || appSettings || {};
    const indices = appConfig.indices || [];
    
    console.log('Using config/settings:', appConfig);
    console.log('Indices found:', indices);
    
    setEditingApp(app);
    setEditForm({
      name: app.name,
      description: app.description,
      is_active: app.is_active,
      config: {
        ...appConfig,
        indices: indices
      }
    });
    setShowEditModal(true);
    setNewIndexName('');  // 清空输入框
  };

  // 打开删除确认对话框
  const handleDeleteApp = (app: App, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setAppToDelete(app);
    setShowDeleteConfirm(true);
  };

  // 添加索引到应用配置
  const handleAddIndex = async () => {
    if (!editingApp) return;
    
    try {
      const indexName = prompt('Enter index name to add to app_config table:');
      if (!indexName || !indexName.trim()) {
        return; // 用户取消或输入为空
      }
      
      setActionLoading(true);
      setError(null);
      
      // 这里应该调用API来添加索引到app_config表
      // 暂时先显示成功消息
      const trimmedName = indexName.trim();
      setSuccessMessage(`Index "${trimmedName}" added to application configuration. (API integration pending)`);
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 3000);
      
    } catch (err: any) {
      console.error('Failed to add index:', err);
      setError(`Failed to add index: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  // 从输入框添加索引
  const handleAddIndexFromInput = () => {
    if (!newIndexName.trim()) {
      setError('Please enter an index name');
      return;
    }
    
    // 添加到editForm.config.indices数组
    const currentConfig = editForm.config || {};
    const currentIndices = currentConfig.indices || [];
    if (currentIndices.includes(newIndexName.trim())) {
      setError('Index name already exists');
      return;
    }
    
    const updatedIndices = [...currentIndices, newIndexName.trim()];
    setEditForm({ 
      ...editForm, 
      config: {
        ...currentConfig,
        indices: updatedIndices
      }
    });
    setNewIndexName('');
    setError(null);
  };

  // 移除索引
  const handleRemoveIndex = (index: number) => {
    const currentConfig = editForm.config || {};
    const currentIndices = currentConfig.indices || [];
    const updatedIndices = currentIndices.filter((_, idx) => idx !== index);
    setEditForm({ 
      ...editForm, 
      config: {
        ...currentConfig,
        indices: updatedIndices
      }
    });
  };

  // 更新索引名称
  const handleIndexNameChange = (index: number, newName: string) => {
    const currentConfig = editForm.config || {};
    const currentIndices = currentConfig.indices || [];
    const updatedIndices = [...currentIndices];
    updatedIndices[index] = newName;
    setEditForm({ 
      ...editForm, 
      config: {
        ...currentConfig,
        indices: updatedIndices
      }
    });
  };

  // 添加新的空索引
  const handleAddEmptyIndex = () => {
    const currentConfig = editForm.config || {};
    const currentIndices = currentConfig.indices || [];
    const updatedIndices = [...currentIndices, ''];
    setEditForm({ 
      ...editForm, 
      config: {
        ...currentConfig,
        indices: updatedIndices
      }
    });
  };

  // 更新应用
  const handleUpdateApp = async () => {
    if (!editingApp) return;
    
    try {
      setActionLoading(true);
      setError(null);
      
      // 清理数据：移除空索引
      const formDataToSend = { ...editForm };
      
      // 将 config 字段转换为 settings 字段，因为后端使用 settings 而非 config
      if (formDataToSend.config) {
        formDataToSend.settings = formDataToSend.config;
        delete formDataToSend.config;
      }
      
      if (formDataToSend.settings?.indices) {
        const cleanedIndices = formDataToSend.settings.indices
          .map((idx: string) => idx.trim())
          .filter((idx: string) => idx.length > 0);
        formDataToSend.settings.indices = cleanedIndices;
        console.log('Cleaned indices before save:', cleanedIndices);
      }
      
      // 调试日志：检查发送的数据
      console.log('Saving application with data:', {
        id: editingApp.id,
        formDataToSend,
        settings: formDataToSend.settings,
        indices: formDataToSend.settings?.indices
      });
      
      const result = await appService.updateApp(editingApp.id, formDataToSend);
      console.log('Update successful, response:', result);
      
      // 获取完整的应用数据（确保包含最新的config.indices）
      const updatedApp = await appService.getAppById(editingApp.id);
      console.log('Updated app details from API:', updatedApp);
      
      // 更新本地状态中的应用
      setApps(prevApps => 
        prevApps.map(app => 
          app.id === editingApp.id ? updatedApp : app
        )
      );
      
      // 注释掉fetchApps，因为它可能不返回完整的config数据
      // await fetchApps();
      
      // 关闭模态框并显示成功消息
      setShowEditModal(false);
      setEditingApp(null);
      setSuccessMessage(`Application "${editForm.name || editingApp.name}" updated successfully!`);
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 3000);
      
    } catch (err: any) {
      console.error('Failed to update application:', err);
      console.error('Error details:', err.response?.data || err.message);
      setError(`Failed to update application: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  // 确认删除应用
  const handleConfirmDelete = async () => {
    if (!appToDelete) return;
    
    try {
      setActionLoading(true);
      setError(null);
      
      await appService.deleteApp(appToDelete.id);
      
      // 刷新应用列表
      await fetchApps();
      
      // 关闭确认对话框并显示成功消息
      setShowDeleteConfirm(false);
      setAppToDelete(null);
      setSuccessMessage(`Application "${appToDelete.name}" deleted successfully!`);
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 3000);
      
    } catch (err: any) {
      console.error('Failed to delete application:', err);
      setError(`Failed to delete application: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  // 打开配置模态框
  const handleConfigureApp = (app: App, e?: React.MouseEvent) => {
    e?.stopPropagation();
    console.log('Opening config modal for app:', { 
      id: app.id, 
      name: app.name, 
      config: app.config,
      settings: app.settings 
    });
    setConfiguringApp(app);
    // 优先使用 app.settings，如果没有则使用 app.config
    const appSettings = app.settings;
    const appConfig = app.config || appSettings || {};
    console.log('Using config data:', appConfig);
    setConfigForm(appConfig);
    setShowConfigModal(true);
  };

  // 保存配置
  const handleSaveConfig = async () => {
    if (!configuringApp) return;
    
    try {
      setActionLoading(true);
      setError(null);
      
      // 准备要保存的配置数据
      const configToSave = { ...configForm };
      
      // 验证和清理配置数据
      // 确保maxFileSize是数字
      if (configToSave.maxFileSize) {
        configToSave.maxFileSize = Number(configToSave.maxFileSize);
        if (isNaN(configToSave.maxFileSize) || configToSave.maxFileSize < 1) {
          configToSave.maxFileSize = 100;
        }
      }
      
      // 确保storageQuota是数字
      if (configToSave.storageQuota) {
        configToSave.storageQuota = Number(configToSave.storageQuota);
        if (isNaN(configToSave.storageQuota) || configToSave.storageQuota < 1) {
          configToSave.storageQuota = 10;
        }
      }
      
      // 验证customConfig JSON
      if (configToSave.customConfig && typeof configToSave.customConfig === 'string') {
        try {
          // 尝试解析字符串形式的JSON
          const parsed = configToSave.customConfig.trim() ? JSON.parse(configToSave.customConfig) : {};
          configToSave.customConfig = parsed;
        } catch (jsonErr) {
          console.warn('Invalid JSON in customConfig, ignoring:', jsonErr);
          // 删除无效的customConfig
          delete configToSave.customConfig;
        }
      }
      
      // 确保布尔值是正确的类型
      const booleanFields = [
        'enableVersioning', 'autoTagging', 'enableAICategorization',
        'requirePasswordForDownload', 'enableAuditLog'
      ];
      booleanFields.forEach(field => {
        if (configToSave[field] !== undefined) {
          configToSave[field] = Boolean(configToSave[field]);
        }
      });
      
      // 发送更新请求 - 将config转换为settings，因为后端使用settings而非config
      await appService.updateApp(configuringApp.id, { settings: configToSave });
      
      // 刷新应用列表
      await fetchApps();
      
      // 关闭模态框并显示成功消息
      setShowConfigModal(false);
      setConfiguringApp(null);
      setSuccessMessage(`Configuration for "${configuringApp.name}" updated successfully!`);
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 3000);
      
    } catch (err: any) {
      console.error('Failed to update configuration:', err);
      setError(`Failed to update configuration: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  // 自定义字段处理函数
  const handleAddCustomField = () => {
    const currentFields = configForm.customFields || {};
    const newFields = { ...currentFields, [`new_field_${Date.now()}`]: '' };
    setConfigForm({ ...configForm, customFields: newFields });
  };

  const handleRemoveCustomField = (index: number) => {
    const currentFields = configForm.customFields || {};
    const keys = Object.keys(currentFields);
    if (index >= 0 && index < keys.length) {
      const keyToRemove = keys[index];
      const newFields = { ...currentFields };
      delete newFields[keyToRemove];
      setConfigForm({ ...configForm, customFields: newFields });
    }
  };

  const handleCustomFieldKeyChange = (index: number, newKey: string) => {
    const currentFields = configForm.customFields || {};
    const keys = Object.keys(currentFields);
    if (index >= 0 && index < keys.length) {
      const oldKey = keys[index];
      const value = currentFields[oldKey];
      const newFields = { ...currentFields };
      delete newFields[oldKey];
      newFields[newKey] = value;
      setConfigForm({ ...configForm, customFields: newFields });
    }
  };

  const handleCustomFieldValueChange = (index: number, newValue: string) => {
    const currentFields = configForm.customFields || {};
    const keys = Object.keys(currentFields);
    if (index >= 0 && index < keys.length) {
      const key = keys[index];
      const newFields = { ...currentFields, [key]: newValue };
      setConfigForm({ ...configForm, customFields: newFields });
    }
  };

  const getAppIcon = (appType: string | undefined | null): string => {
    if (!appType) return '📱';
    
    try {
      switch (appType.toLowerCase()) {
        case 'document_management':
          return '📄';
        case 'sales':
          return '💰';
        case 'hr':
          return '👥';
        case 'inventory':
          return '📦';
        case 'finance':
          return '💵';
        case 'marketing':
          return '📢';
        default:
          return '📱';
      }
    } catch (err) {
      console.warn('Error getting app icon for type:', appType, err);
      return '📱';
    }
  };

  const getAppColor = (appType: string | undefined | null): string => {
    if (!appType) return 'bg-gray-50 border-gray-200 hover:bg-gray-100';
    
    try {
      switch (appType.toLowerCase()) {
        case 'document_management':
          return 'bg-blue-50 border-blue-200 hover:bg-blue-100';
        case 'sales':
          return 'bg-green-50 border-green-200 hover:bg-green-100';
        case 'hr':
          return 'bg-purple-50 border-purple-200 hover:bg-purple-100';
        case 'inventory':
          return 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100';
        case 'finance':
          return 'bg-red-50 border-red-200 hover:bg-red-100';
        case 'marketing':
          return 'bg-pink-50 border-pink-200 hover:bg-pink-100';
        default:
          return 'bg-gray-50 border-gray-200 hover:bg-gray-100';
      }
    } catch (err) {
      console.warn('Error getting app color for type:', appType, err);
      return 'bg-gray-50 border-gray-200 hover:bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-600">Loading applications...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Applications</h1>
            <p className="text-gray-600 mt-2">Select an application to manage its documents and folders</p>
          </div>
          <button
            onClick={handleOpenCreateModal}
            className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create New Application
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-700 mb-2">{error}</div>
            <div className="flex space-x-3">
              <button
                onClick={fetchApps}
                className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm"
              >
                Retry
              </button>
              {error.includes('Authentication required') && (
                <button
                  onClick={() => window.location.href = '/login'}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
                >
                  Go to Login Page
                </button>
              )}
            </div>
          </div>
        )}

        {successMessage && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="text-green-700 mb-2">{successMessage}</div>
            <button
              onClick={() => setSuccessMessage(null)}
              className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* App Cards Grid */}
        {apps.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="text-5xl mb-4">📱</div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">No Applications Found</h2>
            <p className="text-gray-600 mb-4">
              {error ? 'Unable to load applications. Please check authentication.' : 'No applications have been created yet.'}
            </p>
            
            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row justify-center gap-4 mt-6">
              <button
                onClick={fetchApps}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
              
              {/* Create Application Button - only show if no error */}
              {!error && (
                <button
                  onClick={() => handleCreateApp("My First Application", "Default application created automatically")}
                  className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  Create First Application
                </button>
              )}
            </div>
            
            {/* Guide for new users */}
            {!error && (
              <div className="mt-8 pt-6 border-t border-gray-200 text-left">
                <h3 className="text-lg font-semibold text-gray-800 mb-3">Getting Started</h3>
                <ul className="space-y-2 text-gray-600">
                  <li className="flex items-start">
                    <span className="text-green-500 mr-2">✓</span>
                    <span><strong>Step 1:</strong> Create your first application to organize documents</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-green-500 mr-2">✓</span>
                    <span><strong>Step 2:</strong> Inside each application, create folders for categorization</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-green-500 mr-2">✓</span>
                    <span><strong>Step 3:</strong> Upload documents to folders for AI-powered organization</span>
                  </li>
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {apps.map((app) => (
              <div
                key={app.id}
                className={`border rounded-xl shadow-sm p-6 cursor-pointer transition-all duration-200 transform hover:scale-[1.02] hover:shadow-md ${getAppColor(app.app_type)}`}
                onClick={() => handleAppSelect(app)}
              >
                <div className="flex items-start mb-4">
                  <div className="text-3xl mr-4">{getAppIcon(app.app_type)}</div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-gray-800">{app.name}</h3>
                    {app.description && (
                      <p className="text-gray-600 text-sm mt-1 line-clamp-2">{app.description}</p>
                    )}
                  </div>
                  <div>
                    {app.is_active ? (
                      <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full">
                        Inactive
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center justify-between text-sm text-gray-500 mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span>{app.created_by}</span>
                  </div>
                  <div>
                    {new Date(app.created_at).toLocaleDateString()}
                  </div>
                </div>
                
                <div className="mt-4 flex space-x-2">

                  <button
                    onClick={(e) => handleEditApp(app, e)}
                    className="px-3 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
                    title="Edit application"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => handleConfigureApp(app, e)}
                    className="px-3 py-2 bg-purple-50 text-purple-700 border border-purple-200 rounded-md hover:bg-purple-100 transition-colors"
                    title="Configure application"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => handleDeleteApp(app, e)}
                    className="px-3 py-2 bg-red-50 text-red-700 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
                    title="Delete application"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Stats Section */}
        {apps.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Applications Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <div className="text-sm font-medium text-blue-700 mb-1">Total Applications</div>
                <div className="text-2xl font-bold text-blue-800">{apps.length}</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <div className="text-sm font-medium text-green-700 mb-1">Active Applications</div>
                <div className="text-2xl font-bold text-green-800">
                  {apps.filter(app => app.is_active).length}
                </div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <div className="text-sm font-medium text-purple-700 mb-1">Document Management</div>
                <div className="text-2xl font-bold text-purple-800">
                  {apps.filter(app => app.app_type?.toLowerCase()?.includes('document')).length}
                </div>
              </div>
              <div className="p-4 bg-yellow-50 rounded-lg">
                <div className="text-sm font-medium text-yellow-700 mb-1">Other Types</div>
                <div className="text-2xl font-bold text-yellow-800">
                  {apps.filter(app => !app.app_type?.toLowerCase()?.includes('document')).length}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Select an application to view and manage its folders and documents.</p>
          <p className="mt-1">Each application has its own document organization system.</p>
        </div>
      </div>

      {/* Edit Application Modal */}
      {showEditModal && editingApp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowEditModal(false);
            setEditingApp(null);
          }
        }}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">Edit Application</h2>
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingApp(null);
                  }}
                  className="text-gray-500 hover:text-gray-700"
                  aria-label="Close"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Application Name
                  </label>
                  <input
                    type="text"
                    value={editForm.name || ''}
                    onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter application name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={editForm.description || ''}
                    onChange={(e) => setEditForm({...editForm, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                    placeholder="Enter application description"
                  />
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={editForm.is_active || false}
                    onChange={(e) => setEditForm({...editForm, is_active: e.target.checked})}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
                    Active
                  </label>
                </div>
                
                {/* Index Management Section */}
                <div className="border-t pt-4 mt-4">
                  <div className="flex justify-between items-center mb-3">
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-1">Application Indices</h3>
                      <p className="text-xs text-gray-500">Add index names that will be stored in app_config table</p>
                    </div>
                    <button
                      type="button"
                      onClick={handleAddEmptyIndex}
                      className="px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
                    >
                      + Add Index
                    </button>
                  </div>
                  
                  {/* Display editable indices */}
                  {(editForm.config?.indices && editForm.config.indices.length > 0) ? (
                    <div className="space-y-3 mb-4">
                      {editForm.config!.indices.map((index: string, idx: number) => (
                        <div key={idx} className="flex items-center space-x-3">
                          <div className="text-sm font-medium text-gray-700 min-w-[100px]">
                            index name:
                          </div>
                          <input
                            type="text"
                            value={index}
                            onChange={(e) => handleIndexNameChange(idx, e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            placeholder="e.g. reporty type, report name, date"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveIndex(idx)}
                            className="px-3 py-2 text-red-500 hover:text-red-700 text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic mb-4">No indices added yet. Click "+ Add Index" to add new index fields.</p>
                  )}
                </div>
              </div>
              
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingApp(null);
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={actionLoading}
                >
                  Cancel
                </button>

                <button
                  onClick={handleUpdateApp}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Updating...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && appToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowDeleteConfirm(false);
            setAppToDelete(null);
          }
        }}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="p-6">
              <div className="text-center mb-6">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <h2 className="text-xl font-bold text-gray-800">Delete Application</h2>
                  <button
                    onClick={() => {
                      setShowDeleteConfirm(false);
                      setAppToDelete(null);
                    }}
                    className="text-gray-500 hover:text-gray-700"
                    aria-label="Close"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <p className="text-gray-600">
                  Are you sure you want to delete "<span className="font-semibold">{appToDelete.name}</span>"?
                </p>
                <p className="text-red-600 text-sm mt-2">
                  This action cannot be undone. All folders and documents in this application will also be deleted.
                </p>
              </div>
              
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setAppToDelete(null);
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Deleting...' : 'Delete Application'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Modal */}
      {showConfigModal && configuringApp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowConfigModal(false);
            setConfiguringApp(null);
          }
        }}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800 truncate mr-4">Configure Application: {configuringApp.name}</h2>
                <button
                  onClick={() => {
                    setShowConfigModal(false);
                    setConfiguringApp(null);
                  }}
                  className="text-gray-500 hover:text-gray-700 flex-shrink-0"
                  aria-label="Close"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-3">General Settings</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">
                        Enable Document Versioning
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.enableVersioning || false}
                        onChange={(e) => setConfigForm({...configForm, enableVersioning: e.target.checked})}
                        className="h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">
                        Auto-tag Documents
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.autoTagging || false}
                        onChange={(e) => setConfigForm({...configForm, autoTagging: e.target.checked})}
                        className="h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">
                        Enable AI Categorization
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.enableAICategorization || false}
                        onChange={(e) => setConfigForm({...configForm, enableAICategorization: e.target.checked})}
                        className="h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-3">Storage Limits</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max File Size (MB)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        value={configForm.maxFileSize || 100}
                        onChange={(e) => setConfigForm({...configForm, maxFileSize: parseInt(e.target.value) || 100})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Maximum file size in MB"
                      />
                      <p className="text-xs text-gray-500 mt-1">Maximum allowed file size for uploads (1-1000 MB)</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Storage Quota (GB)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={configForm.storageQuota || 10}
                        onChange={(e) => setConfigForm({...configForm, storageQuota: parseInt(e.target.value) || 10})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Storage quota in GB"
                      />
                      <p className="text-xs text-gray-500 mt-1">Total storage limit for this application (1-100 GB)</p>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-3">Security Settings</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">
                        Require Password for Downloads
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.requirePasswordForDownload || false}
                        onChange={(e) => setConfigForm({...configForm, requirePasswordForDownload: e.target.checked})}
                        className="h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">
                        Enable Audit Log
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.enableAuditLog || true}
                        onChange={(e) => setConfigForm({...configForm, enableAuditLog: e.target.checked})}
                        className="h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Allowed File Types
                      </label>
                      <input
                        type="text"
                        value={configForm.allowedFileTypes || ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.png"}
                        onChange={(e) => setConfigForm({...configForm, allowedFileTypes: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Comma-separated file extensions"
                      />
                      <p className="text-xs text-gray-500 mt-1">Example: .pdf,.doc,.jpg,.png (leave empty to allow all types)</p>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-3">Custom Fields</h3>
                  <div className="space-y-4">
                    <div className="bg-gray-50 p-4 rounded-md">
                      <p className="text-sm text-gray-600 mb-3">Add custom key-value pairs that can be used throughout the application. Example: "Report type" = "Monthly Reports"</p>
                      
                      <div className="space-y-3">
                        {/* Display existing custom fields */}
                        {configForm.customFields && Object.entries(configForm.customFields).map(([key, value], index) => (
                          <div key={index} className="flex items-center space-x-2">
                            <input
                              type="text"
                              value={key}
                              onChange={(e) => handleCustomFieldKeyChange(index, e.target.value)}
                              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                              placeholder="Field name"
                            />
                            <span className="text-gray-500">=</span>
                            <input
                              type="text"
                              value={value as string}
                              onChange={(e) => handleCustomFieldValueChange(index, e.target.value)}
                              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                              placeholder="Field value"
                            />
                            <button
                              onClick={() => handleRemoveCustomField(index)}
                              className="px-3 py-2 text-red-600 hover:text-red-800"
                              type="button"
                            >
                              Delete
                            </button>
                          </div>
                        ))}
                        
                        {/* Add new field button */}
                        <button
                          onClick={handleAddCustomField}
                          className="px-4 py-2 text-sm bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-md border border-blue-200"
                          type="button"
                        >
                          + Add Custom Field
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-3">Advanced Settings</h3>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Custom Configuration (JSON)
                    </label>
                    <textarea
                      value={configForm.customConfig ? JSON.stringify(configForm.customConfig, null, 2) : '{}'}
                      onChange={(e) => {
                        try {
                          // Try to parse JSON, but keep as string if invalid
                          const parsed = e.target.value.trim() ? JSON.parse(e.target.value) : {};
                          setConfigForm({...configForm, customConfig: parsed});
                        } catch {
                          // Keep the raw value for now, will be validated on save
                          setConfigForm({...configForm, customConfig: e.target.value});
                        }
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      rows={5}
                      placeholder='{"key": "value"}'
                    />
                    <p className="text-xs text-gray-500 mt-1">Advanced users only. Invalid JSON will be ignored on save.</p>
                  </div>
                </div>
              </div>
              
              <div className="mt-8 flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowConfigModal(false);
                    setConfiguringApp(null);
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveConfig}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create New Application Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowCreateModal(false);
            setNewAppForm({ name: '', description: '' });
          }
        }}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">Create New Application</h2>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewAppForm({ name: '', description: '' });
                  }}
                  className="text-gray-500 hover:text-gray-700"
                  aria-label="Close"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Application Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={newAppForm.name}
                    onChange={(e) => setNewAppForm({...newAppForm, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter application name"
                    autoFocus
                  />
                  <p className="text-xs text-gray-500 mt-1">Required. This will be displayed on the application card.</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={newAppForm.description}
                    onChange={(e) => setNewAppForm({...newAppForm, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                    placeholder="Enter application description (optional)"
                  />
                  <p className="text-xs text-gray-500 mt-1">Optional. Describe the purpose of this application.</p>
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="create_is_active"
                    checked={true}
                    readOnly
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="create_is_active" className="ml-2 text-sm text-gray-700">
                    Active (new applications are active by default)
                  </label>
                </div>
              </div>
              
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewAppForm({ name: '', description: '' });
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    if (!newAppForm.name.trim()) {
                      setError('Application name is required');
                      return;
                    }
                    await handleCreateApp(newAppForm.name, newAppForm.description || 'New application');
                    setShowCreateModal(false);
                    setNewAppForm({ name: '', description: '' });
                  }}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Creating...' : 'Create Application'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AppsDashboard;