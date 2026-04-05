import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import folderService, { Folder } from '../services/folder.service';
import appService, { App, Drawer } from '../services/app.service';
import { generateFolderSlug, extractAppIdFromSlug, generateDrawerSlug, extractDrawerIdFromSlug, toSlug } from '../utils/slugUtils';

const AppFolders: React.FC = () => {
  const { appId: appSlugParam, drawerSlug } = useParams<{ appId: string; drawerSlug?: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Extract the original appId from the slug, but keep the slug for URLs
  const appSlug = appSlugParam || '';
  
  // 从slug提取appId（始终使用当前URL中的标识）
  const extractedAppId = appSlug ? extractAppIdFromSlug(appSlug) || appSlug : null;
  const appId = extractedAppId;
  
  // 调试：显示当前路由参数和计算出的appId
  console.log('🔄 AppFolders路由参数:', { 
    appSlugParam, 
    appSlug, 
    extractedAppId,
    appId,
    locationStateAppId: location.state?.appId,
    drawerSlug 
  });
  
  const [folders, setFolders] = useState<Folder[]>([]);
  const [app, setApp] = useState<App | null>(null);
  const [drawers, setDrawers] = useState<Drawer[]>([]);
  const [selectedDrawer, setSelectedDrawer] = useState<Drawer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [newFolderName, setNewFolderName] = useState('');
  const [newFolderDescription, setNewFolderDescription] = useState('');
  const [newFolderParentId, setNewFolderParentId] = useState<string | undefined>(undefined);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  
  // 抽屉创建相关状态
  const [newDrawerName, setNewDrawerName] = useState('');
  const [newDrawerDescription, setNewDrawerDescription] = useState('');
  const [showCreateDrawerForm, setShowCreateDrawerForm] = useState(false);
  
  // 抽屉编辑和删除相关状态
  const [editingDrawer, setEditingDrawer] = useState<Drawer | null>(null);
  const [editDrawerName, setEditDrawerName] = useState('');
  const [editDrawerDescription, setEditDrawerDescription] = useState('');
  const [showEditDrawerForm, setShowEditDrawerForm] = useState(false);
  const [drawerToDelete, setDrawerToDelete] = useState<Drawer | null>(null);
  const [showDeleteDrawerConfirm, setShowDeleteDrawerConfirm] = useState(false);
  
  // 文件夹编辑相关状态
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  const [editFolderName, setEditFolderName] = useState('');
  const [editFolderDescription, setEditFolderDescription] = useState('');
  const [showEditFolderForm, setShowEditFolderForm] = useState(false);
  const [folderToDelete, setFolderToDelete] = useState<Folder | null>(null);
  const [showDeleteFolderConfirm, setShowDeleteFolderConfirm] = useState(false);
  
  // 文件夹移动相关状态
  const [movingFolder, setMovingFolder] = useState<Folder | null>(null);
  const [targetParentId, setTargetParentId] = useState('');
  const [showMoveFolderForm, setShowMoveFolderForm] = useState(false);
  
  // 获取应用的索引和自定义配置
  const appIndices = app?.config?.indices || [];
  const appCustomConfig = app?.config || {};
  // 检查是否有自定义配置字段（如"app-config"）
  const hasCustomConfig = Object.keys(appCustomConfig).some(key => 
    key !== 'indices' && appCustomConfig[key]
  );
  // 获取用于显示的自定义配置值（如"Report type"）
  const getCustomConfigDisplay = (): string => {
    if (!appCustomConfig) return '';
    
    // 优先查找包含"report"、"type"、"app-config"等关键词的字段
    const priorityKeys = ['app-config', 'report-type', 'report_type', 'reportType', 'type'];
    
    for (const key of priorityKeys) {
      if (appCustomConfig[key]) {
        return String(appCustomConfig[key]);
      }
    }
    
    // 返回第一个非indices的配置值
    for (const [key, value] of Object.entries(appCustomConfig)) {
      if (key !== 'indices' && value) {
        return `${key}: ${value}`;
      }
    }
    
    return '';
  };
  
  const customConfigDisplay = getCustomConfigDisplay();

  useEffect(() => {
    if (appId) {
      fetchAppAndFolders();
    }
  }, [appId, drawerSlug]);

  useEffect(() => {
    console.log('useEffect [appId, selectedDrawer]', { appId, selectedDrawer });
    if (appId && selectedDrawer) {
      console.log('calling fetchFolders');
      fetchFolders(appId, selectedDrawer.id);
    } else {
      console.log('skip fetchFolders - missing appId or selectedDrawer');
    }
  }, [appId, selectedDrawer]);

  const fetchAppAndFolders = async () => {
    console.log('fetchAppAndFolders called', { appId, drawerSlug });
    
    // 检查appId是否是保留路径（如client, login, register等）
    const reservedPaths = ['client', 'login', 'register', 'documents', 'folders', 'upload', 'apps'];
    if (appId && reservedPaths.includes(appId.toLowerCase())) {
      console.warn(`appId "${appId}" is a reserved path, redirecting to home`);
      if (appId.toLowerCase() === 'client') {
        navigate('/client/apps');
      } else {
        navigate('/');
      }
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // 获取应用详情
      const appData = await appService.getAppById(appId!);
      setApp(appData);
      
      // 获取应用的抽屉
      const drawersData = await appService.getAppDrawers(appId!);
      console.log('drawersData received', drawersData);
      setDrawers(drawersData || []);
      
      // 如果有drawerSlug参数，选择对应的抽屉；否则选择第一个抽屉
      if (drawerSlug && drawersData) {
        // 尝试匹配抽屉ID（支持完整UUID、短ID和slug格式）
        const extractedDrawerId = extractDrawerIdFromSlug(drawerSlug);
        const matchedDrawer = drawersData.find(d => {
          // 完全匹配完整UUID
          if (d.id === drawerSlug) return true;
          
          // 如果提取到短ID，匹配抽屉ID的前8字符（去掉连字符）
          if (extractedDrawerId) {
            const drawerShortId = d.id.replace(/-/g, '').substring(0, 8);
            return drawerShortId === extractedDrawerId;
          }
          
          // 如果无法提取短ID（可能是名称slug），尝试匹配抽屉名称的slug
          // 优先使用抽屉的slug字段，然后使用toSlug(d.name)
          // 例如：drawerSlug="en"，比较toSlug(d.name) === "en"
          if (d.slug === drawerSlug || toSlug(d.name) === drawerSlug) {
            console.log('Drawer matched by slug:', { drawerSlug, drawerSlugField: d.slug, drawerName: d.name });
            return true;
          }
          
          return false;
        });
        
        if (matchedDrawer) {
          console.log('matchedDrawer found', matchedDrawer);
          setSelectedDrawer(matchedDrawer);
        } else if (drawersData.length > 0) {
          console.log('no drawer matched, using first drawer', drawersData[0]);
          setSelectedDrawer(drawersData[0]);
        } else {
          console.log('no drawers available');
          setSelectedDrawer(null);
        }
      } else if (drawersData && drawersData.length > 0) {
        setSelectedDrawer(drawersData[0]);
      } else {
        setSelectedDrawer(null);
      }
    } catch (err: any) {
      console.error('Failed to fetch app details:', err);
      setError('Failed to load application details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchFolders = async (appId: string, drawerId: string) => {
    console.log('fetchFolders called', { appId, drawerId });
    try {
      setLoading(true);
      const data = await folderService.getFolders(appId, drawerId);
      console.log('folders data received', data);
      setFolders(data || []);
    } catch (err: any) {
      console.error('Failed to fetch folders:', err);
      setError('Failed to load folders. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFolderSelect = (folder: Folder) => {
    // 生成文件夹slug：小写，空格替换为'-'，法语重音字符替换为英文
    const folderSlug = generateFolderSlug(folder.name, folder.id);
    // 导航到该文件夹的文档页面，URL中包含slug
    // 传递appId作为状态，以便后端API调用
    navigate(`/${appSlug}/folders/${folder.id}-${folderSlug}/documents`, { 
      state: { appId: appId } 
    });
  };

  const generateUniqueFolderName = (baseName: string): string => {
    // Check if a folder with this name already exists
    const existingNames = new Set(folders.map(f => f.name.toLowerCase()));
    
    // If the name is unique, return it as-is
    if (!existingNames.has(baseName.toLowerCase())) {
      return baseName;
    }
    
    // Otherwise, try with incremental numbers
    let counter = 2;
    let candidate = `${baseName} ${counter}`;
    
    while (existingNames.has(candidate.toLowerCase())) {
      counter++;
      candidate = `${baseName} ${counter}`;
    }
    
    return candidate;
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim() || !appId || !selectedDrawer) {
      setError('Folder name is required and a drawer must be selected.');
      return;
    }

    // Generate a unique folder name if needed
    const uniqueFolderName = generateUniqueFolderName(newFolderName.trim());
    const actualFolderName = uniqueFolderName !== newFolderName.trim() ? uniqueFolderName : newFolderName.trim();

    try {
      setLoading(true);
      await folderService.createFolder({
        name: actualFolderName,
        description: newFolderDescription || undefined,
        app_id: appId,
        drawer_id: selectedDrawer.id
      });

      // 刷新文件夹列表
      await fetchFolders(appId, selectedDrawer.id);

      // 重置表单
      setNewFolderName('');
      setNewFolderDescription('');
      setShowCreateForm(false);
      setError(null);
      
      // Show info message if folder name was modified
      if (actualFolderName !== newFolderName.trim()) {
        setInfoMessage(`Folder name was adjusted to "${actualFolderName}" to avoid duplication.`);
        // Clear info message after 5 seconds
        setTimeout(() => setInfoMessage(null), 5000);
      }
    } catch (err) {
      console.error('Failed to create folder:', err);
      setError('Failed to create folder. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // 生成唯一的抽屉名称
  const generateUniqueDrawerName = (baseName: string): string => {
    // 检查是否已存在同名抽屉
    const existingNames = new Set(drawers.map(d => d.name.toLowerCase()));
    
    // 如果名称唯一，直接返回
    if (!existingNames.has(baseName.toLowerCase())) {
      return baseName;
    }
    
    // 否则尝试添加递增数字
    let counter = 2;
    let candidate = `${baseName} ${counter}`;
    
    while (existingNames.has(candidate.toLowerCase())) {
      counter++;
      candidate = `${baseName} ${counter}`;
    }
    
    return candidate;
  };

  // 创建抽屉
  const handleCreateDrawer = async () => {
    if (!newDrawerName.trim() || !appId) {
      setError('Drawer name is required.');
      return;
    }

    // 生成唯一的抽屉名称
    const uniqueDrawerName = generateUniqueDrawerName(newDrawerName.trim());
    const actualDrawerName = uniqueDrawerName !== newDrawerName.trim() ? uniqueDrawerName : newDrawerName.trim();

    try {
      setLoading(true);
      
      // 使用完整的应用ID（如果可用），否则使用原始appId
      const effectiveAppId = app?.id || appId;
      if (!effectiveAppId) {
        setError('Application ID is not available.');
        setLoading(false);
        return;
      }
      
      console.log('Creating drawer for app:', effectiveAppId, 'using app object:', app);
      
      // 调用API创建抽屉
      // 根据错误信息，后端期望请求体包含app_id字段
      const drawerData: any = {
        name: actualDrawerName,
        description: newDrawerDescription || '',
        drawer_type: 'document',
        config: {},
        is_default: drawers.length === 0,
        sort_order: drawers.length + 1,
        app_id: effectiveAppId // 添加app_id字段，后端需要这个字段
      };
      
      // 调试：记录完整的请求数据
      console.log('Creating drawer with data:', JSON.stringify(drawerData, null, 2));
      console.log('API endpoint: POST /apps/' + effectiveAppId + '/drawers');
      
      const newDrawer = await appService.createDrawer(effectiveAppId, drawerData);

      // 刷新抽屉列表
      await fetchAppAndFolders();
      
      // 重置表单
      setNewDrawerName('');
      setNewDrawerDescription('');
      setShowCreateDrawerForm(false);
      setError(null);
      
      // 如果抽屉名称被修改，显示提示信息
      if (actualDrawerName !== newDrawerName.trim()) {
        setInfoMessage(`Drawer name was adjusted to "${actualDrawerName}" to avoid duplication.`);
        setTimeout(() => setInfoMessage(null), 5000);
      }
    } catch (err: any) {
      console.error('Failed to create drawer:', err);
      console.error('Error response:', err.response?.data);
      
      // 显示更详细的错误信息
      let errorMessage = `Failed to create drawer: ${err.message}`;
      if (err.response?.data) {
        // 尝试提取具体的验证错误
        if (err.response.data.detail) {
          errorMessage = `Failed to create drawer: ${JSON.stringify(err.response.data.detail)}`;
        } else if (err.response.data.message) {
          errorMessage = `Failed to create drawer: ${err.response.data.message}`;
        } else {
          errorMessage = `Failed to create drawer: ${JSON.stringify(err.response.data)}`;
        }
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 编辑抽屉 - 打开编辑表单
  const handleEditDrawer = (drawer: Drawer) => {
    setEditingDrawer(drawer);
    setEditDrawerName(drawer.name);
    setEditDrawerDescription(drawer.description || '');
    setShowEditDrawerForm(true);
  };

  // 更新抽屉信息
  const handleUpdateDrawer = async () => {
    if (!editDrawerName.trim() || !editingDrawer || !appId) {
      setError('Drawer name is required.');
      return;
    }

    try {
      setLoading(true);
      const effectiveAppId = app?.id || appId;
      const drawerData: any = {
        name: editDrawerName.trim(),
        description: editDrawerDescription || '',
        updated_by: 'admin' // TODO: 使用当前用户
      };
      
      await appService.updateDrawer(effectiveAppId, editingDrawer.id, drawerData);
      
      // 刷新抽屉列表
      await fetchAppAndFolders();
      
      // 关闭编辑表单
      setShowEditDrawerForm(false);
      setEditingDrawer(null);
      setEditDrawerName('');
      setEditDrawerDescription('');
      setError(null);
      setInfoMessage('Drawer updated successfully.');
      setTimeout(() => setInfoMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to update drawer:', err);
      let errorMessage = `Failed to update drawer: ${err.message}`;
      if (err.response?.data?.detail) {
        errorMessage = `Failed to update drawer: ${JSON.stringify(err.response.data.detail)}`;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 删除抽屉 - 打开确认对话框
  const handleDeleteDrawerClick = (drawer: Drawer) => {
    setDrawerToDelete(drawer);
    setShowDeleteDrawerConfirm(true);
  };

  // 确认删除抽屉
  const handleConfirmDeleteDrawer = async () => {
    if (!drawerToDelete || !appId) return;

    try {
      setLoading(true);
      const effectiveAppId = app?.id || appId;
      
      // 检查抽屉是否包含文件夹（可选，后端可能已处理）
      // 这里可以添加警告：删除抽屉将同时删除所有文件夹和文档
      
      await appService.deleteDrawer(effectiveAppId, drawerToDelete.id);
      
      // 刷新抽屉列表
      await fetchAppAndFolders();
      
      // 如果当前选中的抽屉被删除，清空选择
      if (selectedDrawer?.id === drawerToDelete.id) {
        setSelectedDrawer(null);
      }
      
      // 关闭确认对话框
      setShowDeleteDrawerConfirm(false);
      setDrawerToDelete(null);
      setError(null);
      setInfoMessage('Drawer deleted successfully.');
      setTimeout(() => setInfoMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to delete drawer:', err);
      let errorMessage = `Failed to delete drawer: ${err.message}`;
      if (err.response?.data?.detail) {
        errorMessage = `Failed to delete drawer: ${JSON.stringify(err.response.data.detail)}`;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 编辑文件夹 - 打开编辑表单
  const handleEditFolderClick = (folder: Folder, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingFolder(folder);
    setEditFolderName(folder.name);
    setEditFolderDescription(folder.description || '');
    setShowEditFolderForm(true);
  };

  // 更新文件夹
  const handleUpdateFolder = async () => {
    if (!editingFolder || !appId || !selectedDrawer) {
      setError('Cannot update folder: missing app or drawer selection');
      return;
    }

    if (!editFolderName.trim()) {
      setError('Folder name is required');
      return;
    }

    try {
      setLoading(true);
      const effectiveAppId = app?.id || appId;
      await folderService.updateFolder(
        effectiveAppId,
        selectedDrawer.id,
        editingFolder.id,
        {
          name: editFolderName,
          description: editFolderDescription
        }
      );
      
      // 刷新文件夹列表
      await fetchFolders(appId, selectedDrawer.id);
      
      // 关闭编辑表单
      setShowEditFolderForm(false);
      setEditingFolder(null);
      setEditFolderName('');
      setEditFolderDescription('');
      setError(null);
      setInfoMessage('Folder updated successfully.');
      setTimeout(() => setInfoMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to update folder:', err);
      let errorMessage = `Failed to update folder: ${err.message}`;
      if (err.response?.data?.detail) {
        errorMessage = `Failed to update folder: ${JSON.stringify(err.response.data.detail)}`;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 删除文件夹确认处理
  const handleDeleteFolderClick = (folder: Folder, e: React.MouseEvent) => {
    e.stopPropagation();
    setFolderToDelete(folder);
    setShowDeleteFolderConfirm(true);
  };

  // 确认删除文件夹
  const handleConfirmDeleteFolder = async () => {
    if (!folderToDelete || !appId || !selectedDrawer) {
      setError('Cannot delete folder: missing app or drawer selection');
      return;
    }

    try {
      setLoading(true);
      const effectiveAppId = app?.id || appId;
      await folderService.deleteFolder(effectiveAppId, selectedDrawer.id, folderToDelete.id);
      
      // 刷新文件夹列表
      await fetchFolders(appId, selectedDrawer.id);
      
      // 关闭确认对话框
      setShowDeleteFolderConfirm(false);
      setFolderToDelete(null);
      setError(null);
      setInfoMessage('Folder deleted successfully.');
      setTimeout(() => setInfoMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to delete folder:', err);
      let errorMessage = `Failed to delete folder: ${err.message}`;
      if (err.response?.data?.detail) {
        errorMessage = `Failed to delete folder: ${JSON.stringify(err.response.data.detail)}`;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 移动文件夹处理 - 打开移动对话框
  const handleMoveFolderClick = (folder: Folder, e: React.MouseEvent) => {
    e.stopPropagation();
    setMovingFolder(folder);
    setTargetParentId('');
    setShowMoveFolderForm(true);
  };

  // 确认移动文件夹
  const handleConfirmMoveFolder = async () => {
    if (!movingFolder || !appId || !selectedDrawer) {
      setError('Cannot move folder: missing app or drawer selection');
      return;
    }

    try {
      setLoading(true);
      
      // 准备移动请求
      const moveRequest = {
        target_parent_folder_id: targetParentId || undefined
      };
      
      // 调用移动API
      const updatedFolder = await folderService.moveFolder(movingFolder.id, moveRequest.target_parent_folder_id);
      
      // 刷新文件夹列表
      await fetchFolders(appId, selectedDrawer.id);
      
      // 关闭移动对话框
      setShowMoveFolderForm(false);
      setMovingFolder(null);
      setTargetParentId('');
      setError(null);
      setInfoMessage(`Folder moved successfully to ${targetParentId ? 'parent folder: ' + targetParentId : 'root'}.`);
      setTimeout(() => setInfoMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to move folder:', err);
      let errorMessage = `Failed to move folder: ${err.message}`;
      if (err.response?.data?.detail) {
        errorMessage = `Failed to move folder: ${JSON.stringify(err.response.data.detail)}`;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  const getFolderIcon = (documentCount: number): string => {
    if (documentCount === 0) return '📁';
    if (documentCount < 5) return '📂';
    if (documentCount < 20) return '🗂️';
    return '📚';
  };

  if (loading && !app) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-600">Loading application details...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header with Breadcrumb */}
        <div className="mb-6">
          <nav className="flex items-center text-sm text-gray-600 mb-2">
            <button
              onClick={() => navigate('/')}
              className="hover:text-blue-600"
            >
              Applications
            </button>
            <span className="mx-2">›</span>
            <span className="font-medium text-gray-800">{app?.name || 'Application'}</span>
          </nav>
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{app?.name || 'Application'}</h1>
              <p className="text-gray-600 mt-1">{app?.description || 'Manage folders and documents'}</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
            >
              Back to Applications
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-700 mb-2">{error}</div>
            <button
              onClick={fetchAppAndFolders}
              className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm"
            >
              Retry
            </button>
          </div>
        )}
        
        {infoMessage && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-blue-700">{infoMessage}</div>
          </div>
        )}

        {/* Drawer/Index Selection */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            {appIndices.length > 0 ? 'Application Indices' : 'Select Drawer'}
          </h2>
          
          {appIndices.length > 0 ? (
            // 显示应用索引（如果定义了索引）
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {appIndices.map((indexName: string, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 border border-gray-200 rounded-lg bg-gray-50"
                  >
                    <div className="flex items-center mb-2">
                      <div className="text-xl mr-3">📊</div>
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-800">{indexName}</h3>
                        <p className="text-sm text-gray-600 mt-1">
                          {customConfigDisplay || 'No custom configuration'}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3">
                      <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                        Index {idx + 1}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="text-sm text-gray-500 mt-4">
                <p>This application uses indices for organization instead of drawers.</p>
                <p>Folders are organized by these index categories.</p>
              </div>
            </div>
          ) : (
            // 显示抽屉选择（如果没有索引）
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-700">
                  Drawers ({drawers.length})
                </h3>
                {!showCreateDrawerForm && (
                  <button
                    onClick={() => setShowCreateDrawerForm(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
                  >
                    + Add Drawer
                  </button>
                )}
              </div>
              
              {showCreateDrawerForm && (
                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-6">
                  <h3 className="text-lg font-medium text-gray-800 mb-4">Create New Drawer</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Drawer Name *
                      </label>
                      <input
                        type="text"
                        value={newDrawerName}
                        onChange={(e) => setNewDrawerName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., Reports, Documents, Archive"
                        autoFocus
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description (Optional)
                      </label>
                      <textarea
                        value={newDrawerDescription}
                        onChange={(e) => setNewDrawerDescription(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Describe what this drawer will contain"
                        rows={3}
                      />
                    </div>
                    
                    <div className="flex justify-end space-x-3 pt-2">
                      <button
                        onClick={() => {
                          setShowCreateDrawerForm(false);
                          setNewDrawerName('');
                          setNewDrawerDescription('');
                        }}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCreateDrawer}
                        disabled={!newDrawerName.trim() || loading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Creating...' : 'Create Drawer'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="mb-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                <div>Debug信息：</div>
                <div>App ID: {appId}</div>
                <div>App Slug参数: {appSlug}</div>
                <div>当前抽屉Slug参数: {drawerSlug || '无'}</div>
                <div>抽屉数量: {drawers.length}</div>
                <div>选中的抽屉: {selectedDrawer ? `${selectedDrawer.name} (${selectedDrawer.id})` : '无'}</div>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {drawers.map((drawer) => (
                  <div
                    key={drawer.id}
                    className={`relative p-4 border rounded-lg text-left transition-all ${selectedDrawer?.id === drawer.id ? 'bg-blue-50 border-blue-300 ring-2 ring-blue-100' : 'bg-gray-50 border-gray-200 hover:bg-gray-100'}`}
                  >
                    {/* 抽屉内容 - 可点击区域 */}
                    <button
                      onClick={() => {
                      console.log('Drawer clicked:', { 
                        drawerId: drawer.id, 
                        drawerName: drawer.name,
                        drawerSlug: drawer.slug,
                        appSlug,
                        appId,
                        navigateUrl: `/${appSlug}/${drawer.slug}`
                      });
                      navigate(`/${appSlug}/${drawer.slug}`, { state: { appId: appId } });
                    }}
                      className="w-full text-left"
                    >
                      <div className="flex items-center mb-2">
                        <div className="text-xl mr-3">🗄️</div>
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-800">{drawer.name}</h3>
                          {drawer.description && (
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">{drawer.description}</p>
                          )}
                        </div>
                      </div>
                      {drawer.is_default && (
                        <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          Default
                        </span>
                      )}
                    </button>
                    
                    {/* 操作按钮 */}
                    <div className="absolute top-2 right-2 flex space-x-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditDrawer(drawer);
                        }}
                        className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-md"
                        title="Edit drawer"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteDrawerClick(drawer);
                        }}
                        className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md"
                        title="Delete drawer"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* 编辑抽屉模态框 */}
              {showEditDrawerForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-800">Edit Drawer</h4>
                    </div>
                    <div className="p-6">
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Drawer Name *
                          </label>
                          <input
                            type="text"
                            value={editDrawerName}
                            onChange={(e) => setEditDrawerName(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., Reports, Documents, Archive"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description (Optional)
                          </label>
                          <textarea
                            value={editDrawerDescription}
                            onChange={(e) => setEditDrawerDescription(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Describe what this drawer will contain"
                            rows={3}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
                      <button
                        onClick={() => setShowEditDrawerForm(false)}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateDrawer}
                        disabled={!editDrawerName.trim() || loading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 删除抽屉确认对话框 */}
              {showDeleteDrawerConfirm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-800">Delete Drawer</h4>
                    </div>
                    <div className="p-6">
                      <p className="text-gray-700">
                        Are you sure you want to delete the drawer "<span className="font-medium">{drawerToDelete?.name}</span>"?
                      </p>
                      <p className="text-gray-600 mt-2 text-sm">
                        This action cannot be undone. All folders and documents in this drawer will be deleted.
                      </p>
                    </div>
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
                      <button
                        onClick={() => setShowDeleteDrawerConfirm(false)}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmDeleteDrawer}
                        disabled={loading}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Deleting...' : 'Delete Drawer'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 编辑文件夹模态框 */}
              {showEditFolderForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-800">Edit Folder</h4>
                    </div>
                    <div className="p-6">
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Folder Name *
                          </label>
                          <input
                            type="text"
                            value={editFolderName}
                            onChange={(e) => setEditFolderName(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., Reports, Documents, Archive"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description (Optional)
                          </label>
                          <textarea
                            value={editFolderDescription}
                            onChange={(e) => setEditFolderDescription(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Describe what this folder will contain"
                            rows={3}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
                      <button
                        onClick={() => {
                          setShowEditFolderForm(false);
                          setEditingFolder(null);
                          setEditFolderName('');
                          setEditFolderDescription('');
                        }}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateFolder}
                        disabled={!editFolderName.trim() || loading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 删除文件夹确认对话框 */}
              {showDeleteFolderConfirm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-800">Delete Folder</h4>
                    </div>
                    <div className="p-6">
                      <p className="text-gray-700">
                        Are you sure you want to delete the folder "<span className="font-medium">{folderToDelete?.name}</span>"?
                      </p>
                      <p className="text-gray-600 mt-2 text-sm">
                        This action cannot be undone. All subfolders and documents in this folder will be deleted.
                      </p>
                    </div>
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
                      <button
                        onClick={() => setShowDeleteFolderConfirm(false)}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmDeleteFolder}
                        disabled={loading}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Deleting...' : 'Delete Folder'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {drawers.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-4">🗄️</div>
                  <p className="text-lg">No drawers found for this application.</p>
                  <p className="mt-2">Please add a drawer first to organize folders.</p>
                  <div className="mt-6">
                    {showCreateDrawerForm ? (
                      <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 max-w-md mx-auto">
                        <h3 className="text-lg font-medium text-gray-800 mb-4">Create New Drawer</h3>
                        
                        <div className="space-y-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Drawer Name *
                            </label>
                            <input
                              type="text"
                              value={newDrawerName}
                              onChange={(e) => setNewDrawerName(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="e.g., Reports, Documents, Archive"
                              autoFocus
                            />
                          </div>
                          
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Description (Optional)
                            </label>
                            <textarea
                              value={newDrawerDescription}
                              onChange={(e) => setNewDrawerDescription(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Describe what this drawer will contain"
                              rows={3}
                            />
                          </div>
                          
                          <div className="flex justify-end space-x-3 pt-2">
                            <button
                              onClick={() => {
                                setShowCreateDrawerForm(false);
                                setNewDrawerName('');
                                setNewDrawerDescription('');
                              }}
                              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleCreateDrawer}
                              disabled={!newDrawerName.trim() || loading}
                              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {loading ? 'Creating...' : 'Create Drawer'}
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowCreateDrawerForm(true)}
                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                      >
                        Add a Drawer
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {drawerSlug && selectedDrawer && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">
                  {selectedDrawer.name}
                </h2>
                {selectedDrawer.description && (
                  <p className="text-gray-600 mt-1">{selectedDrawer.description}</p>
                )}
              </div>
              <button
                onClick={() => navigate(`/${appSlug}`)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Back to Drawers
              </button>
            </div>
            
            <div className="py-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div className="text-4xl mb-2">📁</div>
                  <h3 className="text-xl font-semibold text-gray-800">Folder Management</h3>
                  <p className="text-gray-600">
                    Manage folders in the <span className="font-medium">{selectedDrawer.name}</span> drawer
                  </p>
                </div>
                <div className="space-x-4">
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                  >
                    Create New Folder
                  </button>
                  <button
                    onClick={() => navigate(`/${appSlug}/${drawerSlug}/upload`)}
                    className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
                  >
                    Upload to this Drawer
                  </button>
                  <button
                    onClick={() => fetchFolders(appId!, selectedDrawer.id)}
                    className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
                  >
                    Refresh Folders
                  </button>
                </div>
              </div>
              
              {/* Folder List */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                  <h4 className="font-medium text-gray-800">Folders ({folders.length})</h4>
                </div>
                <div className="divide-y divide-gray-100">
                  {folders.length === 0 ? (
                    <div className="px-6 py-8 text-center text-gray-500">
                      <div className="text-3xl mb-2">📁</div>
                      <p className="text-lg">No folders yet</p>
                      <p className="mt-2">Click "Create New Folder" to add your first folder.</p>
                    </div>
                  ) : (
                    folders.map((folder) => (
                      <div key={folder.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div className="text-2xl mr-4">📁</div>
                            <div className="cursor-pointer" onClick={() => handleFolderSelect(folder)}>
                              <h5 className="font-medium text-gray-800 hover:text-blue-600">{folder.name}</h5>
                              {folder.description && (
                                <p className="text-sm text-gray-600 mt-1">{folder.description}</p>
                              )}
                              <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                                <span>ID: {folder.id.substring(0, 8)}...</span>
                                <span>Created by: {folder.created_by}</span>
                                <span>Created: {new Date(folder.created_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          </div>
                          <div className="space-x-2">
                            <button
                              onClick={(e) => handleEditFolderClick(folder, e)}
                              className="px-3 py-1 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
                            >
                              Edit
                            </button>
                            <button
                              onClick={(e) => handleMoveFolderClick(folder, e)}
                              className="px-3 py-1 text-sm border border-blue-300 text-blue-700 rounded hover:bg-blue-50"
                            >
                              Move
                            </button>
                            <button
                              onClick={(e) => handleDeleteFolderClick(folder, e)}
                              className="px-3 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
              
              {/* Create Folder Form */}
              {showCreateForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-800">Create New Folder</h4>
                    </div>
                    <div className="p-6">
                      {error && (
                        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">
                          {error}
                        </div>
                      )}
                      {infoMessage && (
                        <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-md">
                          {infoMessage}
                        </div>
                      )}
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Folder Name *
                          </label>
                          <input
                            type="text"
                            value={newFolderName}
                            onChange={(e) => setNewFolderName(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., Quarterly Reports, Project Docs"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description (Optional)
                          </label>
                          <textarea
                            value={newFolderDescription}
                            onChange={(e) => setNewFolderDescription(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Describe what this folder will contain"
                            rows={3}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Parent Folder (Optional)
                          </label>
                          <select
                            value={newFolderParentId || ''}
                            onChange={(e) => setNewFolderParentId(e.target.value || undefined)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="">No parent (root folder)</option>
                            {folders.map((folder) => (
                              <option key={folder.id} value={folder.id}>
                                {folder.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </div>
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
                      <button
                        onClick={() => setShowCreateForm(false)}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCreateFolder}
                        disabled={!newFolderName.trim() || loading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Creating...' : 'Create Folder'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Move Folder Form */}
              {showMoveFolderForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-800">Move Folder</h4>
                    </div>
                    <div className="p-6">
                      <div className="mb-4">
                        <p className="text-gray-700 mb-2">
                          Moving folder: <span className="font-medium">{movingFolder?.name}</span>
                        </p>
                        <p className="text-sm text-gray-600">
                          Enter the ID of the parent folder you want to move this folder to. 
                          Leave empty to move to root (no parent).
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          Note: Folder can only be moved within the same drawer.
                        </p>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Target Parent Folder ID (Optional)
                          </label>
                          <input
                            type="text"
                            value={targetParentId}
                            onChange={(e) => setTargetParentId(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., enter folder ID or leave empty for root"
                            autoFocus
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Enter the UUID of the target parent folder, or leave empty to move to drawer root.
                          </p>
                        </div>
                        {targetParentId && (
                          <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                            <p className="text-sm text-blue-700">
                              Folder will be moved to parent folder with ID: 
                              <code className="ml-1 text-xs">{targetParentId}</code>
                            </p>
                          </div>
                        )}
                        {!targetParentId && (
                          <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
                            <p className="text-sm text-gray-700">
                              Folder will be moved to drawer root (no parent).
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
                      <button
                        onClick={() => {
                          setShowMoveFolderForm(false);
                          setMovingFolder(null);
                          setTargetParentId('');
                        }}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmMoveFolder}
                        disabled={loading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Moving...' : 'Move Folder'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default AppFolders;