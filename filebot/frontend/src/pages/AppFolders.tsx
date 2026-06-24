import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import folderService, { Folder } from '../services/folder.service';
import appService, { App } from '../services/app.service';
import { Drawer } from '../services/drawer.service';
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
      const data = await folderService.getFolders(appId, drawerId ? { parent_folder_id: drawerId } : undefined);
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
    // 使用folder.path作为标识（Folder主键是path）
    const folderPath = folder.path || folder.name;
    // 生成文件夹slug用于URL
    const folderSlug = generateFolderSlug(folder.name, folderPath);
    // 导航到该文件夹的文档页面，URL中包含slug和编码的路径
    navigate(`/${appSlug}/folders/${encodeURIComponent(folderPath)}-${folderSlug}/documents`, { 
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
        parent_folder_id: selectedDrawer.id
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
      // 使用文件夹路径（如果存在）否则使用ID
      const folderPath = editingFolder.path || editingFolder.id;
      await folderService.updateFolder(
        folderPath,
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
      // 使用文件夹路径（如果存在）否则使用ID
      const folderPath = folderToDelete.path || folderToDelete.id;
      await folderService.deleteFolder(folderPath, true); // true表示递归删除
      
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
        target_parent_folder_path: targetParentId || undefined
      };
      
      // 调用移动API
      const updatedFolder = await folderService.moveFolder(movingFolder.path, moveRequest.target_parent_folder_path);
      
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
      <div className="fb-page-bg" style={{padding:32}}>
        <div className="container">
          <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
            <div className="text-muted">Loading application details...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fb-page-bg" style={{padding:16}}>
      <div className="container">
        {/* Header with Breadcrumb */}
        <div style={{marginBottom:24}}>
          <nav className="fb-d-flex fb-align-center text-muted" style={{fontSize:"0.875rem",marginBottom:8}}>
            <button
              onClick={() => navigate('/')}
              className="fb-link"
            >
              Applications
            </button>
            <span className="mx-2">›</span>
            <span style={{fontWeight:500,color:"#1f2937"}}>{app?.name || 'Application'}</span>
          </nav>
          <div className="fb-d-flex fb-justify-between fb-align-center">
            <div>
              <h1 style={{fontSize:"1.875rem",fontWeight:700,color:"#1f2937"}}>{app?.name || 'Application'}</h1>
              <p className="text-muted" style={{marginTop:4}}>{app?.description || 'Manage folders and documents'}</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="btn btn-default btn-sm"
            >
              Back to Applications
            </button>
          </div>
        </div>

        {error && (
          <div className="alert alert-danger">
            <div style={{color:"#b91c1c",marginBottom:8}}>{error}</div>
            <button
              onClick={fetchAppAndFolders}
              className="btn btn-danger btn-xs" style={{background:"#fee2e2",color:"#b91c1c"}}
            >
              Retry
            </button>
          </div>
        )}
        
        {infoMessage && (
          <div className="alert alert-info">
            <div style={{color:"#1d4ed8"}}>{infoMessage}</div>
          </div>
        )}

        {/* Drawer/Index Selection */}
        <div className="panel panel-default" style={{marginBottom:24}}>
          <h2 style={{fontSize:"1.25rem",fontWeight:600,color:"#1f2937",marginBottom:16}}>
            {appIndices.length > 0 ? 'Application Indices' : 'Select Drawer'}
          </h2>
          
          {appIndices.length > 0 ? (
            // 显示应用索引（如果定义了索引）
            <div style={{display:"flex",flexDirection:"column",gap:16}}>
              <div className="row">
                {appIndices.map((indexName: string, idx: number) => (
                  <div
                    key={idx}
                    style={{padding:16,border:"1px solid #e5e7eb",borderRadius:8,background:"#f9fafb"}}
                  >
                    <div className="fb-d-flex fb-align-center" style={{marginBottom:8}}>
                      <div style={{fontSize:"1.25rem",marginRight:12}}>📊</div>
                      <div style={{flex:1}}>
                        <h3 style={{fontWeight:500,color:"#1f2937"}}>{indexName}</h3>
                        <p style={{fontSize:"0.875rem",color:"#4b5563",marginTop:4}}>
                          {customConfigDisplay || 'No custom configuration'}
                        </p>
                      </div>
                    </div>
                    <div style={{marginTop:12}}>
                      <span className="label label-info" style={{borderRadius:9999}}>
                        Index {idx + 1}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{fontSize:"0.875rem",color:"#6b7280",marginTop:16}}>
                <p>This application uses indices for organization instead of drawers.</p>
                <p>Folders are organized by these index categories.</p>
              </div>
            </div>
          ) : (
            // 显示抽屉选择（如果没有索引）
            <div>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#374151"}}>
                  Drawers ({drawers.length})
                </h3>
                {!showCreateDrawerForm && (
                  <button
                    onClick={() => setShowCreateDrawerForm(true)}
                    className="btn btn-primary btn-sm"
                  >
                    + Add Drawer
                  </button>
                )}
              </div>
              
              {showCreateDrawerForm && (
                <div className="panel panel-default" style={{marginBottom:24}}>
                  <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#1f2937",marginBottom:16}}>Create New Drawer</h3>
                  
                  <div style={{display:"flex",flexDirection:"column",gap:16}}>
                    <div>
                      <label className="fb-label">
                        Drawer Name *
                      </label>
                      <input
                        type="text"
                        value={newDrawerName}
                        onChange={(e) => setNewDrawerName(e.target.value)}
                        className="form-control"
                        placeholder="e.g., Reports, Documents, Archive"
                        autoFocus
                      />
                    </div>
                    
                    <div>
                      <label className="fb-label">
                        Description (Optional)
                      </label>
                      <textarea
                        value={newDrawerDescription}
                        onChange={(e) => setNewDrawerDescription(e.target.value)}
                        className="form-control"
                        placeholder="Describe what this drawer will contain"
                        rows={3}
                      />
                    </div>
                    
                    <div className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end",paddingTop:8}}>
                      <button
                        onClick={() => {
                          setShowCreateDrawerForm(false);
                          setNewDrawerName('');
                          setNewDrawerDescription('');
                        }}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCreateDrawer}
                        disabled={!newDrawerName.trim() || loading}
                        className="btn btn-primary" style={{opacity:undefined,disabled:undefined}}
                      >
                        {loading ? 'Creating...' : 'Create Drawer'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="alert alert-warning" style={{fontSize:"0.875rem"}}>
                <div>Debug信息：</div>
                <div>App ID: {appId}</div>
                <div>App Slug参数: {appSlug}</div>
                <div>当前抽屉Slug参数: {drawerSlug || '无'}</div>
                <div>抽屉数量: {drawers.length}</div>
                <div>选中的抽屉: {selectedDrawer ? `${selectedDrawer.name} (${selectedDrawer.id})` : '无'}</div>
              </div>
              
              <div className="row">
                {drawers.map((drawer) => (
                  <div
                    key={drawer.id}
                    style={{
                      position: 'relative',
                      padding: 16,
                      border: `1px solid ${selectedDrawer?.id === drawer.id ? '#93c5fd' : '#e5e7eb'}`,
                      borderRadius: 8,
                      textAlign: 'left',
                      transition: 'all 150ms',
                      background: selectedDrawer?.id === drawer.id ? '#eff6ff' : '#f9fafb',
                      boxShadow: selectedDrawer?.id === drawer.id ? '0 0 0 2px #dbeafe' : undefined
                    }}
                    className={selectedDrawer?.id !== drawer.id ? 'fb-hover-btn' : undefined}
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
                      style={{width:"100%",textAlign:"left"}}
                    >
                      <div className="fb-d-flex fb-align-center" style={{marginBottom:8}}>
                        <div style={{fontSize:"1.25rem",marginRight:12}}>🗄️</div>
                        <div style={{flex:1}}>
                          <h3 style={{fontWeight:500,color:"#1f2937"}}>{drawer.name}</h3>
                          {drawer.description && (
                            <p style={{fontSize:"0.875rem",color:"#4b5563",marginTop:4,display:"-webkit-box",WebkitLineClamp:2,WebkitBoxOrient:"vertical",overflow:"hidden"}}>{drawer.description}</p>
                          )}
                        </div>
                      </div>
                      {drawer.is_default && (
                        <span className="label label-info" style={{borderRadius:9999}}>
                          Default
                        </span>
                      )}
                    </button>
                    
                    {/* 操作按钮 */}
                    <div style={{position:"absolute",top:8,right:8,display:"flex",gap:4}}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditDrawer(drawer);
                        }}
                        className="fb-tree-icon" style={{padding:4,color:"#6b7280"}}
                        title="Edit drawer"
                      >
                        <svg style={{width:16,height:16}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteDrawerClick(drawer);
                        }}
                        className="fb-tree-icon" style={{padding:4,color:"#6b7280"}}
                        title="Delete drawer"
                      >
                        <svg style={{width:16,height:16}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* 编辑抽屉模态框 */}
              {showEditDrawerForm && (
                <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}}>
                  <div className="panel panel-default" style={{maxWidth:448,width:"100%"}}>
                    <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb"}}>
                      <h4 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}>Edit Drawer</h4>
                    </div>
                    <div style={{padding:24}}>
                      <div style={{display:"flex",flexDirection:"column",gap:16}}>
                        <div>
                          <label className="fb-label">
                            Drawer Name *
                          </label>
                          <input
                            type="text"
                            value={editDrawerName}
                            onChange={(e) => setEditDrawerName(e.target.value)}
                            className="form-control"
                            placeholder="e.g., Reports, Documents, Archive"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="fb-label">
                            Description (Optional)
                          </label>
                          <textarea
                            value={editDrawerDescription}
                            onChange={(e) => setEditDrawerDescription(e.target.value)}
                            className="form-control"
                            placeholder="Describe what this drawer will contain"
                            rows={3}
                          />
                        </div>
                      </div>
                    </div>
                    <div style={{padding:"24px 24px",borderTop:"1px solid #e5e7eb",background:"#f9fafb"}} className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                      <button
                        onClick={() => setShowEditDrawerForm(false)}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateDrawer}
                        disabled={!editDrawerName.trim() || loading}
                        className="btn btn-primary" style={{opacity:undefined,disabled:undefined}}
                      >
                        {loading ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 删除抽屉确认对话框 */}
              {showDeleteDrawerConfirm && (
                <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}}>
                  <div className="panel panel-default" style={{maxWidth:448,width:"100%"}}>
                    <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb"}}>
                      <h4 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}>Delete Drawer</h4>
                    </div>
                    <div style={{padding:24}}>
                      <p style={{color:"#374151"}}>
                        Are you sure you want to delete the drawer "<span className="font-medium">{drawerToDelete?.name}</span>"?
                      </p>
                      <p className="text-muted" style={{marginTop:8,fontSize:"0.875rem"}}>
                        This action cannot be undone. All folders and documents in this drawer will be deleted.
                      </p>
                    </div>
                    <div style={{padding:"24px 24px",borderTop:"1px solid #e5e7eb",background:"#f9fafb"}} className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                      <button
                        onClick={() => setShowDeleteDrawerConfirm(false)}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmDeleteDrawer}
                        disabled={loading}
                        className="btn btn-danger" style={{disabled:undefined}}
                      >
                        {loading ? 'Deleting...' : 'Delete Drawer'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 编辑文件夹模态框 */}
              {showEditFolderForm && (
                <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}}>
                  <div className="panel panel-default" style={{maxWidth:448,width:"100%"}}>
                    <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb"}}>
                      <h4 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}>Edit Folder</h4>
                    </div>
                    <div style={{padding:24}}>
                      <div style={{display:"flex",flexDirection:"column",gap:16}}>
                        <div>
                          <label className="fb-label">
                            Folder Name *
                          </label>
                          <input
                            type="text"
                            value={editFolderName}
                            onChange={(e) => setEditFolderName(e.target.value)}
                            className="form-control"
                            placeholder="e.g., Reports, Documents, Archive"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="fb-label">
                            Description (Optional)
                          </label>
                          <textarea
                            value={editFolderDescription}
                            onChange={(e) => setEditFolderDescription(e.target.value)}
                            className="form-control"
                            placeholder="Describe what this folder will contain"
                            rows={3}
                          />
                        </div>
                      </div>
                    </div>
                    <div style={{padding:"24px 24px",borderTop:"1px solid #e5e7eb",background:"#f9fafb"}} className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                      <button
                        onClick={() => {
                          setShowEditFolderForm(false);
                          setEditingFolder(null);
                          setEditFolderName('');
                          setEditFolderDescription('');
                        }}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateFolder}
                        disabled={!editFolderName.trim() || loading}
                        className="btn btn-primary" style={{opacity:undefined,disabled:undefined}}
                      >
                        {loading ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 删除文件夹确认对话框 */}
              {showDeleteFolderConfirm && (
                <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}}>
                  <div className="panel panel-default" style={{maxWidth:448,width:"100%"}}>
                    <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb"}}>
                      <h4 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}>Delete Folder</h4>
                    </div>
                    <div style={{padding:24}}>
                      <p style={{color:"#374151"}}>
                        Are you sure you want to delete the folder "<span className="font-medium">{folderToDelete?.name}</span>"?
                      </p>
                      <p className="text-muted" style={{marginTop:8,fontSize:"0.875rem"}}>
                        This action cannot be undone. All subfolders and documents in this folder will be deleted.
                      </p>
                    </div>
                    <div style={{padding:"24px 24px",borderTop:"1px solid #e5e7eb",background:"#f9fafb"}} className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                      <button
                        onClick={() => setShowDeleteFolderConfirm(false)}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmDeleteFolder}
                        disabled={loading}
                        className="btn btn-danger" style={{disabled:undefined}}
                      >
                        {loading ? 'Deleting...' : 'Delete Folder'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {drawers.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div style={{fontSize:"2.25rem",marginBottom:16}}>🗄️</div>
                  <p style={{fontSize:"1.125rem"}}>No drawers found for this application.</p>
                  <p style={{marginTop:8}}>Please add a drawer first to organize folders.</p>
                  <div style={{marginTop:24}}>
                    {showCreateDrawerForm ? (
                      <div className="panel panel-default" style={{margin:"0 auto",maxWidth:448}}>
                        <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#1f2937",marginBottom:16}}>Create New Drawer</h3>
                        
                        <div style={{display:"flex",flexDirection:"column",gap:16}}>
                          <div>
                            <label className="fb-label">
                              Drawer Name *
                            </label>
                            <input
                              type="text"
                              value={newDrawerName}
                              onChange={(e) => setNewDrawerName(e.target.value)}
                              className="form-control"
                              placeholder="e.g., Reports, Documents, Archive"
                              autoFocus
                            />
                          </div>
                          
                          <div>
                            <label className="fb-label">
                              Description (Optional)
                            </label>
                            <textarea
                              value={newDrawerDescription}
                              onChange={(e) => setNewDrawerDescription(e.target.value)}
                              className="form-control"
                              placeholder="Describe what this drawer will contain"
                              rows={3}
                            />
                          </div>
                          
                          <div className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end",paddingTop:8}}>
                            <button
                              onClick={() => {
                                setShowCreateDrawerForm(false);
                                setNewDrawerName('');
                                setNewDrawerDescription('');
                              }}
                              className="btn btn-default btn-sm"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleCreateDrawer}
                              disabled={!newDrawerName.trim() || loading}
                              className="btn btn-primary" style={{opacity:undefined,disabled:undefined}}
                            >
                              {loading ? 'Creating...' : 'Create Drawer'}
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowCreateDrawerForm(true)}
                        className="btn btn-primary"
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
          <div className="panel panel-default" style={{marginBottom:24}}>
            <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}>
              <div>
                <h2 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>
                  {selectedDrawer.name}
                </h2>
                {selectedDrawer.description && (
                  <p className="text-muted" style={{marginTop:4}}>{selectedDrawer.description}</p>
                )}
              </div>
              <button
                onClick={() => navigate(`/${appSlug}`)}
                className="btn btn-default btn-sm"
              >
                Back to Drawers
              </button>
            </div>
            
            <div style={{paddingTop:32,paddingBottom:32}}>
              <div className="fb-d-flex fb-align-center fb-justify-between" style={{marginBottom:24}}>
                <div>
                  <div style={{fontSize:"2.25rem",marginBottom:8}}>📁</div>
                  <h3 style={{fontSize:"1.25rem",fontWeight:600,color:"#1f2937"}}>Folder Management</h3>
                  <p className="text-muted">
                    Manage folders in the <span className="font-medium">{selectedDrawer.name}</span> drawer
                  </p>
                </div>
                <div className="fb-gap-3">
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="btn btn-primary"
                  >
                    Create New Folder
                  </button>
                  <button
                    onClick={() => navigate(`/${appSlug}/${drawerSlug}/upload`)}
                    className="btn btn-success"
                  >
                    Upload to this Drawer
                  </button>
                  <button
                    onClick={() => fetchFolders(appId!, selectedDrawer.id)}
                    className="btn btn-default"
                  >
                    Refresh Folders
                  </button>
                </div>
              </div>
              
              {/* Folder List */}
              <div className="panel panel-default" style={{overflow:"hidden"}}>
                <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb",background:"#f9fafb"}}>
                  <h4 style={{fontWeight:500,color:"#1f2937"}}>Folders ({folders.length})</h4>
                </div>
                <div className="divide-y divide-gray-100">
                  {folders.length === 0 ? (
                    <div className="px-6 py-8 text-center text-gray-500">
                      <div style={{fontSize:"1.875rem",marginBottom:8}}>📁</div>
                      <p style={{fontSize:"1.125rem"}}>No folders yet</p>
                      <p style={{marginTop:8}}>Click "Create New Folder" to add your first folder.</p>
                    </div>
                  ) : (
                    folders.map((folder) => (
                      <div key={folder.path || folder.name} className="fb-hover-btn" style={{padding:"24px 24px"}}>
                        <div className="fb-d-flex fb-align-center fb-justify-between">
                          <div className="fb-d-flex fb-align-center">
                            <div style={{fontSize:"1.5rem",marginRight:16}}>📁</div>
                            <div className="cursor-pointer" onClick={() => handleFolderSelect(folder)}>
                              <h5 className="fb-link" style={{fontWeight:500,color:"#1f2937"}}>{folder.name}</h5>
                              {folder.description && (
                                <p style={{fontSize:"0.875rem",color:"#4b5563",marginTop:4}}>{folder.description}</p>
                              )}
                              <div className="fb-d-flex fb-align-center fb-gap-3" style={{marginTop:8,fontSize:"0.75rem",color:"#6b7280"}}>
                                <span>路径: {(folder.path || folder.name).substring(0, 40)}...</span>
                                <span>Created by: {folder.created_by}</span>
                                <span>Created: {new Date(folder.created_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          </div>
                          <div className="fb-gap-1">
                            <button
                              onClick={(e) => handleEditFolderClick(folder, e)}
                              className="btn btn-default btn-xs"
                            >
                              Edit
                            </button>
                            <button
                              onClick={(e) => handleMoveFolderClick(folder, e)}
                              className="btn btn-info btn-xs"
                            >
                              Move
                            </button>
                            <button
                              onClick={(e) => handleDeleteFolderClick(folder, e)}
                              className="btn btn-danger btn-xs"
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
                <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}}>
                  <div className="panel panel-default" style={{maxWidth:448,width:"100%"}}>
                    <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb"}}>
                      <h4 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}>Create New Folder</h4>
                    </div>
                    <div style={{padding:24}}>
                      {error && (
                        <div className="alert alert-danger">
                          {error}
                        </div>
                      )}
                      {infoMessage && (
                        <div className="alert alert-success">
                          {infoMessage}
                        </div>
                      )}
                      <div style={{display:"flex",flexDirection:"column",gap:16}}>
                        <div>
                          <label className="fb-label">
                            Folder Name *
                          </label>
                          <input
                            type="text"
                            value={newFolderName}
                            onChange={(e) => setNewFolderName(e.target.value)}
                            className="form-control"
                            placeholder="e.g., Quarterly Reports, Project Docs"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="fb-label">
                            Description (Optional)
                          </label>
                          <textarea
                            value={newFolderDescription}
                            onChange={(e) => setNewFolderDescription(e.target.value)}
                            className="form-control"
                            placeholder="Describe what this folder will contain"
                            rows={3}
                          />
                        </div>
                        <div>
                          <label className="fb-label">
                            Parent Folder (Optional)
                          </label>
                          <select
                            value={newFolderParentId || ''}
                            onChange={(e) => setNewFolderParentId(e.target.value || undefined)}
                            className="form-control"
                          >
                            <option value="">No parent (root folder)</option>
                            {folders.map((folder) => (
                              <option key={folder.path || folder.name} value={folder.path}>
                                {folder.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </div>
                    <div style={{padding:"24px 24px",borderTop:"1px solid #e5e7eb",background:"#f9fafb"}} className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                      <button
                        onClick={() => setShowCreateForm(false)}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCreateFolder}
                        disabled={!newFolderName.trim() || loading}
                        className="btn btn-primary" style={{opacity:undefined,disabled:undefined}}
                      >
                        {loading ? 'Creating...' : 'Create Folder'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Move Folder Form */}
              {showMoveFolderForm && (
                <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center" style={{zIndex:50,padding:16}}>
                  <div className="panel panel-default" style={{maxWidth:448,width:"100%"}}>
                    <div style={{padding:"24px 24px",borderBottom:"1px solid #e5e7eb"}}>
                      <h4 style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}>Move Folder</h4>
                    </div>
                    <div style={{padding:24}}>
                      <div style={{marginBottom:16}}>
                        <p style={{color:"#374151",marginBottom:8}}>
                          Moving folder: <span className="font-medium">{movingFolder?.name}</span>
                        </p>
                        <p style={{fontSize:"0.875rem",color:"#4b5563"}}>
                          Enter the ID of the parent folder you want to move this folder to. 
                          Leave empty to move to root (no parent).
                        </p>
                        <p style={{fontSize:"0.875rem",color:"#6b7280",marginTop:4}}>
                          Note: Folder can only be moved within the same drawer.
                        </p>
                      </div>
                      <div style={{display:"flex",flexDirection:"column",gap:16}}>
                        <div>
                          <label className="fb-label">
                            Target Parent Folder ID (Optional)
                          </label>
                          <input
                            type="text"
                            value={targetParentId}
                            onChange={(e) => setTargetParentId(e.target.value)}
                            className="form-control"
                            placeholder="e.g., enter folder ID or leave empty for root"
                            autoFocus
                          />
                          <p style={{fontSize:"0.75rem",color:"#6b7280",marginTop:4}}>
                            Enter the UUID of the target parent folder, or leave empty to move to drawer root.
                          </p>
                        </div>
                        {targetParentId && (
                          <div style={{padding:12,background:"#eff6ff",border:"1px solid #bfdbfe",borderRadius:6}}>
                            <p style={{fontSize:"0.875rem",color:"#1d4ed8"}}>
                              Folder will be moved to parent folder with ID: 
                              <code style={{marginLeft:4,fontSize:"0.75rem"}}>{targetParentId}</code>
                            </p>
                          </div>
                        )}
                        {!targetParentId && (
                          <div style={{padding:12,background:"#f9fafb",border:"1px solid #e5e7eb",borderRadius:6}}>
                            <p style={{fontSize:"0.875rem",color:"#374151"}}>
                              Folder will be moved to drawer root (no parent).
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{padding:"24px 24px",borderTop:"1px solid #e5e7eb",background:"#f9fafb"}} className="fb-d-flex fb-gap-2" style={{justifyContent:"flex-end"}}>
                      <button
                        onClick={() => {
                          setShowMoveFolderForm(false);
                          setMovingFolder(null);
                          setTargetParentId('');
                        }}
                        className="btn btn-default btn-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmMoveFolder}
                        disabled={loading}
                        className="btn btn-primary" style={{opacity:undefined,disabled:undefined}}
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