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
        slug: name.toLowerCase().replace(/\s+/g, '-'),
        description: description,
        app_type: "document_management",
        owner_id: userInfo.id,
        settings: { indices: [] }
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
    const updatedIndices = currentIndices.filter((_: any, idx: number) => idx !== index);
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
        // 确保 settings 包含 indices 数组
        formDataToSend.settings = { indices: formDataToSend.config.indices || [] };
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
        ) as App[]
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
      
      // 确保configToSave包含indices数组（AppUpdateRequest.settings要求）
      if (!configToSave.indices) {
        configToSave.indices = [];
      }
      
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
      // 注意：AppUpdateRequest.settings 只需要 indices 数组，其他配置字段通过 config 传递
      await appService.updateApp(configuringApp.id, { 
        settings: { indices: configToSave.indices || [] },
        config: configToSave
      });
      
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

  const getAppColorStyle = (appType: string | undefined | null): Record<string, string> => {
    if (!appType) return { background: '#f9fafb', borderColor: '#e5e7eb' };
    
    try {
      switch (appType.toLowerCase()) {
        case 'document_management':
          return { background: '#eff6ff', borderColor: '#bfdbfe' };
        case 'sales':
          return { background: '#f0fdf4', borderColor: '#bbf7d0' };
        case 'hr':
          return { background: '#faf5ff', borderColor: '#e9d5ff' };
        case 'inventory':
          return { background: '#fefce8', borderColor: '#fef08a' };
        case 'finance':
          return { background: '#fef2f2', borderColor: '#fecaca' };
        case 'marketing':
          return { background: '#fdf2f8', borderColor: '#fbcfe8' };
        default:
          return { background: '#f9fafb', borderColor: '#e5e7eb' };
      }
    } catch (err) {
      console.warn('Error getting app color style for type:', appType, err);
      return { background: '#f9fafb', borderColor: '#e5e7eb' };
    }
  };

  if (loading) {
    return (
      <div className="fb-page-bg" style={{padding:32}}>
        <div className="container">
          <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
            <div className="text-muted">Loading applications...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fb-page-bg" style={{padding:16}}>
      <div className="container">
        {/* Header */}
        <div className="fb-d-flex fb-justify-between fb-align-start" style={{marginBottom:32}}>
          <div>
            <h1 style={{fontSize:"1.875rem",fontWeight:700,color:"#1f2937"}}>Applications</h1>
            <p className="text-muted" style={{marginTop:8}}>Select an application to manage its documents and folders</p>
          </div>
          <button
            onClick={handleOpenCreateModal}
            className="btn btn-success fb-d-flex fb-align-center fb-gap-1"
          >
            <svg style={{width:20,height:20}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create New Application
          </button>
        </div>

        {error && (
          <div className="alert alert-danger">
            <div style={{color:"#b91c1c",marginBottom:8}}>{error}</div>
            <div className="fb-d-flex fb-gap-2">
              <button
                onClick={fetchApps}
                className="btn btn-danger btn-xs" style={{background:"#fee2e2",color:"#b91c1c"}}
              >
                Retry
              </button>
              {error.includes('Authentication required') && (
                <button
                  onClick={() => window.location.href = '/login'}
                  className="btn btn-info btn-xs" style={{background:"#dbeafe",color:"#1d4ed8"}}
                >
                  Go to Login Page
                </button>
              )}
            </div>
          </div>
        )}

        {successMessage && (
          <div className="alert alert-success">
            <div style={{color:"#15803d",marginBottom:8}}>{successMessage}</div>
            <button
              onClick={() => setSuccessMessage(null)}
              className="btn btn-success btn-xs" style={{background:"#dcfce7",color:"#15803d"}}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* App Cards Grid */}
        {apps.length === 0 ? (
          <div className="panel panel-default text-center" style={{padding:32}}>
            <div style={{fontSize:"3rem",marginBottom:16}}>📱</div>
            <h2 style={{fontSize:"1.25rem",fontWeight:600,color:"#1f2937",marginBottom:8}}>No Applications Found</h2>
            <p className="text-muted" style={{marginBottom:16}}>
              {error ? 'Unable to load applications. Please check authentication.' : 'No applications have been created yet.'}
            </p>
            
            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row justify-center gap-4 mt-6">
              <button
                onClick={fetchApps}
                className="btn btn-primary"
              >
                Retry
              </button>
              
              {/* Create Application Button - only show if no error */}
              {!error && (
                <button
                  onClick={() => handleCreateApp("My First Application", "Default application created automatically")}
                  className="btn btn-success"
                >
                  Create First Application
                </button>
              )}
            </div>
            
            {/* Guide for new users */}
            {!error && (
              <div style={{marginTop:32,paddingTop:24,borderTop:"1px solid #e5e7eb",textAlign:"left"}}>
                <h3 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937",marginBottom:12}}>Getting Started</h3>
                <ul className="text-muted" style={{display:"flex",flexDirection:"column",gap:8}}>
                  <li className="fb-d-flex fb-align-start">
                    <span style={{color:"#22c55e",marginRight:8}}>✓</span>
                    <span><strong>Step 1:</strong> Create your first application to organize documents</span>
                  </li>
                  <li className="fb-d-flex fb-align-start">
                    <span style={{color:"#22c55e",marginRight:8}}>✓</span>
                    <span><strong>Step 2:</strong> Inside each application, create folders for categorization</span>
                  </li>
                  <li className="fb-d-flex fb-align-start">
                    <span style={{color:"#22c55e",marginRight:8}}>✓</span>
                    <span><strong>Step 3:</strong> Upload documents to folders for AI-powered organization</span>
                  </li>
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="row">
            {apps.map((app) => (
              <div
                key={app.id}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: 12,
                  boxShadow: '0 1px 2px 0 rgba(0,0,0,0.05)',
                  padding: 24,
                  cursor: 'pointer',
                  transition: 'all 200ms',
                  ...getAppColorStyle(app.app_type)
                }}
                className="fb-hover-btn"
                onMouseEnter={(e) => { e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'scale(1.02)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.boxShadow = '0 1px 2px 0 rgba(0,0,0,0.05)'; e.currentTarget.style.transform = 'scale(1)'; }}
                onClick={() => handleAppSelect(app)}
              >
                <div className="fb-d-flex fb-align-start" style={{marginBottom:16}}>
                  <div style={{fontSize:"1.875rem",marginRight:16}}>{getAppIcon(app.app_type)}</div>
                  <div style={{flex:1}}>
                    <h3 style={{fontSize:"1.125rem",fontWeight:700,color:"#1f2937"}}>{app.name}</h3>
                    {app.description && (
                      <p className="text-muted" style={{fontSize:"0.875rem",marginTop:4,display:"-webkit-box",WebkitLineClamp:2,WebkitBoxOrient:"vertical",overflow:"hidden"}}>{app.description}</p>
                    )}
                  </div>
                  <div>
                    {app.is_active ? (
                      <span className="label label-success" style={{borderRadius:9999,fontSize:"0.75rem"}}>
                        Active
                      </span>
                    ) : (
                      <span className="label label-default" style={{borderRadius:9999,fontSize:"0.75rem"}}>
                        Inactive
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="fb-d-flex fb-align-center fb-justify-between" style={{fontSize:"0.875rem",color:"#6b7280",marginTop:16,paddingTop:16,borderTop:"1px solid #e5e7eb"}}>
                  <div className="fb-d-flex fb-align-center">
                    <svg style={{width:16,height:16,marginRight:4}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span>{app.created_by}</span>
                  </div>
                  <div>
                    {app.created_at ? new Date(app.created_at).toLocaleDateString() : ''}
                  </div>
                </div>
                
                <div className="fb-d-flex fb-gap-1" style={{marginTop:16}}>

                  <button
                    onClick={(e) => handleEditApp(app, e)}
                    className="btn btn-link" style={{padding:"6px 12px",color:"#1d4ed8",border:"1px solid #bfdbfe",borderRadius:6}}
                    title="Edit application"
                  >
                    <svg style={{width:16,height:16}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => handleConfigureApp(app, e)}
                    className="btn btn-link" style={{padding:"6px 12px",color:"#7e22ce",border:"1px solid #e9d5ff",borderRadius:6}}
                    title="Configure application"
                  >
                    <svg style={{width:16,height:16}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => handleDeleteApp(app, e)}
                    className="btn btn-link" style={{padding:"6px 12px",color:"#b91c1c",border:"1px solid #fecaca",borderRadius:6}}
                    title="Delete application"
                  >
                    <svg style={{width:16,height:16}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          <div className="panel panel-default" style={{marginTop:32}}>
            <h2 style={{fontSize:"1.25rem",fontWeight:600,color:"#1f2937",marginBottom:16}}>Applications Overview</h2>
            <div className="row">
              <div style={{padding:16,background:"#eff6ff",borderRadius:8}}>
                <div className="fb-label" style={{color:"#1d4ed8",marginBottom:4}}>Total Applications</div>
                <div style={{fontSize:"1.5rem",fontWeight:700,color:"#1e40af"}}>{apps.length}</div>
              </div>
              <div style={{padding:16,background:"#f0fdf4",borderRadius:8}}>
                <div className="fb-label" style={{color:"#15803d",marginBottom:4}}>Active Applications</div>
                <div style={{fontSize:"1.5rem",fontWeight:700,color:"#166534"}}>
                  {apps.filter(app => app.is_active).length}
                </div>
              </div>
              <div style={{padding:16,background:"#faf5ff",borderRadius:8}}>
                <div className="fb-label" style={{color:"#7e22ce",marginBottom:4}}>Document Management</div>
                <div style={{fontSize:"1.5rem",fontWeight:700,color:"#6b21a8"}}>
                  {apps.filter(app => app.app_type?.toLowerCase()?.includes('document')).length}
                </div>
              </div>
              <div style={{padding:16,background:"#fefce8",borderRadius:8}}>
                <div className="fb-label" style={{color:"#a16207",marginBottom:4}}>Other Types</div>
                <div style={{fontSize:"1.5rem",fontWeight:700,color:"#854d0e"}}>
                  {apps.filter(app => !app.app_type?.toLowerCase()?.includes('document')).length}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Select an application to view and manage its folders and documents.</p>
          <p style={{marginTop:4}}>Each application has its own document organization system.</p>
        </div>
      </div>

      {/* Edit Application Modal */}
      {showEditModal && editingApp && (
        <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}} onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowEditModal(false);
            setEditingApp(null);
          }
        }}>
          <div className="panel panel-default" style={{width:"100%",maxWidth:448}}>
            <div style={{padding:24}}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h2 style={{fontSize:"1.25rem",fontWeight:700,color:"#1f2937"}}>Edit Application</h2>
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingApp(null);
                  }}
                  className="fb-link text-muted"
                  aria-label="Close"
                >
                  <svg style={{width:24,height:24}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div style={{display:"flex",flexDirection:"column",gap:16}}>
                <div>
                  <label className="fb-label">
                    Application Name
                  </label>
                  <input
                    type="text"
                    value={editForm.name || ''}
                    onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                    className="form-control"
                    placeholder="Enter application name"
                  />
                </div>
                
                <div>
                  <label className="fb-label">
                    Description
                  </label>
                  <textarea
                    value={editForm.description || ''}
                    onChange={(e) => setEditForm({...editForm, description: e.target.value})}
                    className="form-control"
                    rows={3}
                    placeholder="Enter application description"
                  />
                </div>
                
                <div className="fb-d-flex fb-align-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={editForm.is_active || false}
                    onChange={(e) => setEditForm({...editForm, is_active: e.target.checked})}
                    style={{height:16,width:16,color:"#2563eb"}}
                  />
                  <label htmlFor="is_active" style={{marginLeft:8,fontSize:"0.875rem",color:"#374151"}}>
                    Active
                  </label>
                </div>
                
                {/* Index Management Section */}
                <div style={{borderTop:"1px solid #e5e7eb",paddingTop:16,marginTop:16}}>
                  <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:12}}>
                    <div>
                      <h3 className="fb-label">Application Indices</h3>
                      <p style={{fontSize:"0.75rem",color:"#6b7280"}}>Add index names that will be stored in app_config table</p>
                    </div>
                    <button
                      type="button"
                      onClick={handleAddEmptyIndex}
                      className="btn btn-success btn-sm"
                    >
                      + Add Index
                    </button>
                  </div>
                  
                  {/* Display editable indices */}
                  {(editForm.config?.indices && editForm.config.indices.length > 0) ? (
                    <div style={{display:"flex",flexDirection:"column",gap:12,marginBottom:16}}>
                      {editForm.config!.indices.map((index: string, idx: number) => (
                        <div key={idx} className="fb-d-flex fb-align-center fb-gap-2">
                          <div className="fb-label" style={{minWidth:100}}>
                            index name:
                          </div>
                          <input
                            type="text"
                            value={index}
                            onChange={(e) => handleIndexNameChange(idx, e.target.value)}
                            className="form-control" style={{fontSize:"0.875rem"}}
                            placeholder="e.g. reporty type, report name, date"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveIndex(idx)}
                            className="fb-link" style={{padding:"6px 12px",color:"#ef4444",fontSize:"0.875rem"}}
                          >
                            Delete
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{fontSize:"0.875rem",color:"#6b7280",fontStyle:"italic",marginBottom:16}}>No indices added yet. Click "+ Add Index" to add new index fields.</p>
                  )}
                </div>
              </div>
              
              <div className="fb-d-flex fb-gap-2" style={{marginTop:24,justifyContent:"flex-end"}}>
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingApp(null);
                  }}
                  className="btn btn-default"
                  disabled={actionLoading}
                >
                  Cancel
                </button>

                <button
                  onClick={handleUpdateApp}
                  disabled={actionLoading}
                  className="btn btn-primary"
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
        <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}} onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowDeleteConfirm(false);
            setAppToDelete(null);
          }
        }}>
          <div className="panel panel-default" style={{width:"100%",maxWidth:448}}>
            <div style={{padding:24}}>
              <div className="text-center mb-6">
                <div className="fb-d-flex fb-align-center fb-justify-center" style={{margin:"0 auto",height:48,width:48,borderRadius:"50%",background:"#fee2e2",marginBottom:16}}>
                  <svg style={{height:24,width:24,color:"#dc2626"}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </div>
                <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:8}}>
                  <h2 style={{fontSize:"1.25rem",fontWeight:700,color:"#1f2937"}}>Delete Application</h2>
                  <button
                    onClick={() => {
                      setShowDeleteConfirm(false);
                      setAppToDelete(null);
                    }}
                    className="fb-link text-muted"
                    aria-label="Close"
                  >
                    <svg style={{width:24,height:24}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <p className="text-muted">
                  Are you sure you want to delete "<span className="font-semibold">{appToDelete.name}</span>"?
                </p>
                <p style={{color:"#dc2626",fontSize:"0.875rem",marginTop:8}}>
                  This action cannot be undone. All folders and documents in this application will also be deleted.
                </p>
              </div>
              
              <div className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setAppToDelete(null);
                  }}
                  className="btn btn-default"
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  disabled={actionLoading}
                  className="btn btn-danger"
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
        <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}} onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowConfigModal(false);
            setConfiguringApp(null);
          }
        }}>
          <div className="panel panel-default" style={{width:"100%",maxWidth:672,maxHeight:"90vh",overflowY:"auto"}}>
            <div style={{padding:24}}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h2 style={{fontSize:"1.25rem",fontWeight:700,color:"#1f2937",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",marginRight:16}}>Configure Application: {configuringApp.name}</h2>
                <button
                  onClick={() => {
                    setShowConfigModal(false);
                    setConfiguringApp(null);
                  }}
                  className="fb-link text-muted" style={{flexShrink:0}}
                  aria-label="Close"
                >
                  <svg style={{width:24,height:24}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div style={{display:"flex",flexDirection:"column",gap:24}}>
                <div>
                  <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#374151",marginBottom:12}}>General Settings</h3>
                  <div style={{display:"flex",flexDirection:"column",gap:16}}>
                    <div className="fb-d-flex fb-align-center fb-justify-between">
                      <label className="fb-label">
                        Enable Document Versioning
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.enableVersioning || false}
                        onChange={(e) => setConfigForm({...configForm, enableVersioning: e.target.checked})}
                        style={{height:20,width:20,color:"#2563eb"}}
                      />
                    </div>
                    
                    <div className="fb-d-flex fb-align-center fb-justify-between">
                      <label className="fb-label">
                        Auto-tag Documents
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.autoTagging || false}
                        onChange={(e) => setConfigForm({...configForm, autoTagging: e.target.checked})}
                        style={{height:20,width:20,color:"#2563eb"}}
                      />
                    </div>
                    
                    <div className="fb-d-flex fb-align-center fb-justify-between">
                      <label className="fb-label">
                        Enable AI Categorization
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.enableAICategorization || false}
                        onChange={(e) => setConfigForm({...configForm, enableAICategorization: e.target.checked})}
                        style={{height:20,width:20,color:"#2563eb"}}
                      />
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#374151",marginBottom:12}}>Storage Limits</h3>
                  <div style={{display:"flex",flexDirection:"column",gap:16}}>
                    <div>
                      <label className="fb-label">
                        Max File Size (MB)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        value={configForm.maxFileSize || 100}
                        onChange={(e) => setConfigForm({...configForm, maxFileSize: parseInt(e.target.value) || 100})}
                        className="form-control"
                        placeholder="Maximum file size in MB"
                      />
                      <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>Maximum allowed file size for uploads (1-1000 MB)</p>
                    </div>
                    
                    <div>
                      <label className="fb-label">
                        Storage Quota (GB)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={configForm.storageQuota || 10}
                        onChange={(e) => setConfigForm({...configForm, storageQuota: parseInt(e.target.value) || 10})}
                        className="form-control"
                        placeholder="Storage quota in GB"
                      />
                      <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>Total storage limit for this application (1-100 GB)</p>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#374151",marginBottom:12}}>Security Settings</h3>
                  <div style={{display:"flex",flexDirection:"column",gap:16}}>
                    <div className="fb-d-flex fb-align-center fb-justify-between">
                      <label className="fb-label">
                        Require Password for Downloads
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.requirePasswordForDownload || false}
                        onChange={(e) => setConfigForm({...configForm, requirePasswordForDownload: e.target.checked})}
                        style={{height:20,width:20,color:"#2563eb"}}
                      />
                    </div>
                    
                    <div className="fb-d-flex fb-align-center fb-justify-between">
                      <label className="fb-label">
                        Enable Audit Log
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.enableAuditLog || true}
                        onChange={(e) => setConfigForm({...configForm, enableAuditLog: e.target.checked})}
                        style={{height:20,width:20,color:"#2563eb"}}
                      />
                    </div>
                    
                    <div>
                      <label className="fb-label">
                        Allowed File Types
                      </label>
                      <input
                        type="text"
                        value={configForm.allowedFileTypes || ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.png"}
                        onChange={(e) => setConfigForm({...configForm, allowedFileTypes: e.target.value})}
                        className="form-control"
                        placeholder="Comma-separated file extensions"
                      />
                      <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>Example: .pdf,.doc,.jpg,.png (leave empty to allow all types)</p>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#374151",marginBottom:12}}>Custom Fields</h3>
                  <div style={{display:"flex",flexDirection:"column",gap:16}}>
                    <div style={{padding:16,background:"#f9fafb",borderRadius:6}}>
                      <p style={{fontSize:"0.875rem",color:"#4b5563",marginBottom:12}}>Add custom key-value pairs that can be used throughout the application. Example: "Report type" = "Monthly Reports"</p>
                      
                      <div style={{display:"flex",flexDirection:"column",gap:12}}>
                        {/* Display existing custom fields */}
                        {configForm.customFields && Object.entries(configForm.customFields).map(([key, value], index) => (
                          <div key={index} className="fb-d-flex fb-align-center fb-gap-1">
                            <input
                              type="text"
                              value={key}
                              onChange={(e) => handleCustomFieldKeyChange(index, e.target.value)}
                              className="form-control" style={{fontSize:"0.875rem"}}
                              placeholder="Field name"
                            />
                            <span className="text-muted">=</span>
                            <input
                              type="text"
                              value={value as string}
                              onChange={(e) => handleCustomFieldValueChange(index, e.target.value)}
                              className="form-control" style={{fontSize:"0.875rem"}}
                              placeholder="Field value"
                            />
                            <button
                              onClick={() => handleRemoveCustomField(index)}
                              className="fb-link" style={{padding:"6px 12px",color:"#dc2626"}}
                              type="button"
                            >
                              Delete
                            </button>
                          </div>
                        ))}
                        
                        {/* Add new field button */}
                        <button
                          onClick={handleAddCustomField}
                          className="btn btn-info btn-sm" style={{background:"#eff6ff"}}
                          type="button"
                        >
                          + Add Custom Field
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#374151",marginBottom:12}}>Advanced Settings</h3>
                  <div>
                    <label className="fb-label">
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
                      className="form-control" style={{fontFamily:"monospace",fontSize:"0.875rem"}}
                      rows={5}
                      placeholder='{"key": "value"}'
                    />
                    <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>Advanced users only. Invalid JSON will be ignored on save.</p>
                  </div>
                </div>
              </div>
              
              <div className="fb-d-flex fb-gap-2" style={{marginTop:32,justifyContent:"flex-end"}}>
                <button
                  onClick={() => {
                    setShowConfigModal(false);
                    setConfiguringApp(null);
                  }}
                  className="btn btn-default"
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveConfig}
                  disabled={actionLoading}
                  style={{padding:"4px 8px",background:"#9333ea",color:"#fff",borderRadius:6,border:"none"}} className="fb-hover-btn"
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
        <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}} onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowCreateModal(false);
            setNewAppForm({ name: '', description: '' });
          }
        }}>
          <div className="panel panel-default" style={{width:"100%",maxWidth:448}}>
            <div style={{padding:24}}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h2 style={{fontSize:"1.25rem",fontWeight:700,color:"#1f2937"}}>Create New Application</h2>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewAppForm({ name: '', description: '' });
                  }}
                  className="fb-link text-muted"
                  aria-label="Close"
                >
                  <svg style={{width:24,height:24}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div style={{display:"flex",flexDirection:"column",gap:16}}>
                <div>
                  <label className="fb-label">
                    Application Name <span style={{color:"#ef4444"}}>*</span>
                  </label>
                  <input
                    type="text"
                    value={newAppForm.name}
                    onChange={(e) => setNewAppForm({...newAppForm, name: e.target.value})}
                    className="form-control"
                    placeholder="Enter application name"
                    autoFocus
                  />
                  <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>Required. This will be displayed on the application card.</p>
                </div>
                
                <div>
                  <label className="fb-label">
                    Description
                  </label>
                  <textarea
                    value={newAppForm.description}
                    onChange={(e) => setNewAppForm({...newAppForm, description: e.target.value})}
                    className="form-control"
                    rows={3}
                    placeholder="Enter application description (optional)"
                  />
                  <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>Optional. Describe the purpose of this application.</p>
                </div>
                
                <div className="fb-d-flex fb-align-center">
                  <input
                    type="checkbox"
                    id="create_is_active"
                    checked={true}
                    readOnly
                    style={{height:16,width:16,color:"#2563eb"}}
                  />
                  <label htmlFor="create_is_active" style={{marginLeft:8,fontSize:"0.875rem",color:"#374151"}}>
                    Active (new applications are active by default)
                  </label>
                </div>
              </div>
              
              <div className="fb-d-flex fb-gap-2" style={{marginTop:24,justifyContent:"flex-end"}}>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewAppForm({ name: '', description: '' });
                  }}
                  className="btn btn-default"
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
                  className="btn btn-success"
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