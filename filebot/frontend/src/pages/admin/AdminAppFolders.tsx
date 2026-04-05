import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import appService, { App } from '../../services/app.service';
import folderService, { Folder, FolderCreateRequest } from '../../services/folder.service';
import aiService, { WebsiteCrawlRequest } from '../../services/ai.service';
import FolderTree from '../../components/folders/FolderTree';
import CreateFolderModal from '../../components/folders/CreateFolderModal';
import { ChevronRightIcon, ChevronDownIcon, FolderIcon, DocumentIcon } from '@heroicons/react/24/outline';

const AdminAppFolders: React.FC = () => {
  const { appSlug } = useParams<{ appSlug: string }>();
  const navigate = useNavigate();
  
  // 状态管理
  const [app, setApp] = useState<App | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showImportWebsiteModal, setShowImportWebsiteModal] = useState(false);
  const [parentFolderId, setParentFolderId] = useState<string | null>(null);
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  
  // 导入网站表单状态
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [crawlDepth, setCrawlDepth] = useState(1);
  const [importingWebsite, setImportingWebsite] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  
  // 当前文件夹详情
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [subfolders, setSubfolders] = useState<Folder[]>([]);
  
  // 加载应用信息
  useEffect(() => {
    const loadAppInfo = async () => {
      if (!appSlug) return;
      
      try {
        setError(null);
        const appData = await appService.getAppById(appSlug);
        setApp(appData);
        
        // 加载所有文件夹
        if (appData) {
          await loadFolders(appData.id || appSlug);
        }
      } catch (error: any) {
        console.error('加载应用信息失败:', error);
        
        // 检查错误类型
        if (error.response?.status === 403) {
          setError('没有权限访问此应用。此应用可能属于其他用户。');
        } else if (error.response?.status === 404) {
          setError('应用不存在，可能已被删除或URL不正确。');
        } else {
          setError('加载应用信息失败，请稍后重试。');
        }
      } finally {
        setLoading(false);
      }
    };
    
    loadAppInfo();
  }, [appSlug]);
  
  // 加载文件夹
  const loadFolders = async (appIdentifier: string) => {
    try {
      const foldersData = await folderService.getFolders(appIdentifier);
      setFolders(foldersData);
      
      // 如果没有当前文件夹，设置第一个根文件夹为当前文件夹
      if (!currentFolderId && foldersData.length > 0) {
        const rootFolder = foldersData.find(f => !f.parent_folder_id);
        if (rootFolder) {
          setCurrentFolderId(rootFolder.id);
        } else if (foldersData[0]) {
          setCurrentFolderId(foldersData[0].id);
        }
      }
    } catch (error) {
      console.error('加载文件夹失败:', error);
    }
  };
  
  // 当当前文件夹变化时，加载其详情和子文件夹
  useEffect(() => {
    const loadCurrentFolderDetails = async () => {
      if (!currentFolderId) return;
      
      try {
        // 加载当前文件夹详情
        const folderDetails = await folderService.getFolderById(currentFolderId);
        setCurrentFolder(folderDetails);
        
        // 加载子文件夹
        const subfoldersData = await folderService.getFolders(app?.id || appSlug || '', {
          parent_folder_id: currentFolderId
        });
        setSubfolders(subfoldersData);
      } catch (error) {
        console.error('加载文件夹详情失败:', error);
      }
    };
    
    loadCurrentFolderDetails();
  }, [currentFolderId, app?.id, appSlug]);
  
  // 处理文件夹点击
  const handleFolderClick = (folderId: string) => {
    setCurrentFolderId(folderId);
  };
  
  // 处理创建文件夹
  const handleCreateFolder = async (data: FolderCreateRequest) => {
    try {
      // 确保应用ID正确
      const folderData: FolderCreateRequest = {
        ...data,
        app_id: app?.id || appSlug || ''
      };
      
      await folderService.createFolder(folderData);
      
      // 重新加载文件夹
      if (app) {
        await loadFolders(app.id);
      }
      
      setShowCreateModal(false);
    } catch (error) {
      console.error('创建文件夹失败:', error);
      alert('创建文件夹失败，请检查网络或权限');
    }
  };
  
  // 处理删除文件夹
  const handleDeleteFolder = async (folderId: string) => {
    // 检查文件夹是否有子文件夹
    const subfoldersCount = folders.filter(f => f.parent_folder_id === folderId).length;
    
    let recursive = false;
    
    if (subfoldersCount > 0) {
      // 询问用户是否递归删除
      const folderName = folders.find(f => f.id === folderId)?.name || '此文件夹';
      const confirmMessage = `文件夹 "${folderName}" 包含 ${subfoldersCount} 个子文件夹。\n\n` +
                           `选择"确定"递归删除所有子文件夹及其文档。\n` +
                           `选择"取消"只删除空文件夹。`;
      
      if (!window.confirm(confirmMessage)) {
        return; // 用户取消
      }
      
      recursive = true;
    } else {
      // 没有子文件夹，简单确认
      if (!confirm('确定要删除这个文件夹吗？文件夹内的所有文档也将被删除。')) {
        return;
      }
    }
    
    try {
      await folderService.deleteFolder(folderId, recursive);
      
      // 如果删除的是当前文件夹，导航到父文件夹或根目录
      if (currentFolderId === folderId) {
        const folderToDelete = folders.find(f => f.id === folderId);
        setCurrentFolderId(folderToDelete?.parent_folder_id || null);
      }
      
      // 重新加载文件夹
      if (app) {
        await loadFolders(app.id);
      }
    } catch (error: any) {
      console.error('删除文件夹失败:', error);
      
      // 提供更详细的错误信息
      if (error.response?.status === 400) {
        const errorDetail = error.response?.data?.detail || '文件夹不为空';
        alert(`删除失败: ${errorDetail}\n\n请使用递归删除选项。`);
      } else {
        alert('删除文件夹失败，文件夹可能不为空或没有权限');
      }
    }
  };
  
  // 处理编辑文件夹
  const handleEditFolder = async (folderId: string) => {
    const folderToEdit = folders.find(f => f.id === folderId);
    if (!folderToEdit) return;
    
    setEditingFolder(folderToEdit);
    setShowEditModal(true);
  };
  
  // 处理保存编辑后的文件夹
  const handleSaveEditFolder = async (data: {
    name: string;
    description?: string;
    parent_folder_id?: string;
  }) => {
    if (!editingFolder || !app) return;
    
    try {
      // 调用更新文件夹API
      await folderService.updateFolder(editingFolder.id, data);
      
      // 重新加载文件夹
      await loadFolders(app.id);
      
      // 如果编辑的是当前文件夹，更新当前文件夹状态
      if (currentFolderId === editingFolder.id) {
        const updatedCurrentFolder = folders.find(f => f.id === editingFolder.id);
        if (updatedCurrentFolder) {
          setCurrentFolder(updatedCurrentFolder);
        }
      }
      
      // 关闭编辑模态框
      setShowEditModal(false);
      setEditingFolder(null);
      
      console.log('文件夹更新成功');
    } catch (error) {
      console.error('更新文件夹失败:', error);
      alert('更新文件夹失败：' + (error as any).response?.data?.detail || '未知错误');
      throw error;
    }
  };
  
  // 处理移动文件夹
  const handleMoveFolder = async (folderId: string, targetParentFolderId?: string) => {
    try {
      // 调用API移动文件夹
      await folderService.moveFolder(folderId, targetParentFolderId);
      
      // 重新加载文件夹以更新树形结构
      if (app) {
        await loadFolders(app.id);
      }
      
      // 如果移动的是当前文件夹，更新当前文件夹ID
      if (currentFolderId === folderId && targetParentFolderId) {
        // 移动到新位置后，可能需要重新选择
        setCurrentFolderId(folderId);
      }
      
      // 显示成功消息
      console.log('文件夹移动成功');
    } catch (error) {
      console.error('移动文件夹失败:', error);
      alert('移动文件夹失败：' + (error as any).response?.data?.detail || '未知错误');
      throw error; // 重新抛出错误，让FolderTree组件可以处理
    }
  };
  
  // 构建面包屑路径
  const buildBreadcrumbs = () => {
    if (!currentFolderId || !folders.length) return [];
    
    const breadcrumbs = [];
    let current = folders.find(f => f.id === currentFolderId);
    
    while (current) {
      breadcrumbs.unshift({
        id: current.id,
        name: current.name,
        path: current.id === currentFolderId ? undefined : `/admin/apps/${appSlug}?folder=${current.id}`
      });
      
      if (current.parent_folder_id) {
        current = folders.find(f => f.id === current.parent_folder_id);
      } else {
        current = null;
      }
    }
    
    // 添加应用作为根
    if (app) {
      breadcrumbs.unshift({
        id: 'app',
        name: app.name,
        path: `/admin/apps/${appSlug}`
      });
    }
    
    return breadcrumbs;
  };
  
  // 处理导航到文档列表
  const handleNavigateToDocuments = (folderId: string) => {
    navigate(`/admin/apps/${appSlug}/folders/${folderId}/documents`);
  };
  
  // 处理导航到上传页面
  const handleNavigateToUpload = (folderId: string) => {
    navigate(`/admin/apps/${appSlug}/folders/${folderId}/upload`);
  };

  // 处理导航到文件夹导入页面
  const handleImportFolder = (folderId: string) => {
    navigate(`/admin/apps/${appSlug}/folders/${folderId}/upload?mode=import`);
  };

  // 处理导入网站
  const handleImportWebsite = (folderId: string) => {
    setShowImportWebsiteModal(true);
  };

  // 提交导入网站表单
  const handleSubmitImportWebsite = async () => {
    if (!websiteUrl.trim() || !currentFolderId || !app) {
      setImportError('请填写URL并确保已选择文件夹');
      return;
    }
    
    // 验证URL格式
    try {
      new URL(websiteUrl);
    } catch {
      setImportError('请输入有效的URL（如 https://example.com）');
      return;
    }
    
    setImportingWebsite(true);
    setImportError(null);
    
    try {
      // 构建请求
      const request: WebsiteCrawlRequest = {
        url: websiteUrl.trim(),
        depth: crawlDepth,
        folder_id: currentFolderId,
        include_images: true,
        follow_external_links: false,
        respect_robots_txt: true
      };
      
      // 调用后端API
      const response = await aiService.crawlWebsite(request);
      
      // 显示成功消息
      alert(`网站爬取任务已开始！\n任务ID: ${response.task_id}\nURL: ${response.url}\n深度: ${response.depth}\n状态: ${response.status}\n\n任务将在后台执行，您可以继续其他操作。`);
      
      // 关闭模态框
      setShowImportWebsiteModal(false);
      setWebsiteUrl('');
      setCrawlDepth(1);
    } catch (error: any) {
      console.error('导入网站失败:', error);
      setImportError(
        error.response?.data?.detail || 
        error.message || 
        '导入网站失败，请检查网络连接或后端服务'
      );
    } finally {
      setImportingWebsite(false);
    }
  };
  
  // 渲染加载状态
  if (loading) {
    return (
      <div className="p-6 text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="mt-4 text-gray-600">加载文件夹管理中...</p>
      </div>
    );
  }
  
  // 渲染错误状态
  if (!app) {
    const isPermissionError = error?.includes('没有权限');
    const errorTitle = isPermissionError ? '没有访问权限' : '应用不存在';
    
    return (
      <div className="p-6">
        <div className="mb-6">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
            <Link to="/admin/apps" className="hover:text-blue-600">应用管理</Link>
            <span>›</span>
            <span className="text-gray-700">未知应用</span>
          </div>
        </div>
        
        {isPermissionError ? (
          // 权限错误 - 橙色主题
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-6 text-center">
            <h3 className="text-lg font-medium text-orange-800 mb-2">{errorTitle}</h3>
            <p className="text-orange-700 mb-4">{error || '您没有权限访问此应用。'}</p>
            <div className="space-y-3">
              <Link to="/admin/apps" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-block">
                返回应用列表
              </Link>
              <div className="mt-4 pt-4 border-t border-orange-100">
                <p className="text-sm text-orange-600 mb-2">如果您需要访问此应用，可以：</p>
                <div className="space-y-2 text-sm text-orange-700">
                  <p>1. 使用应用所有者的账户登录</p>
                  <p>2. 联系管理员为您添加访问权限</p>
                  <p>3. 创建自己的新应用</p>
                </div>
                <button
                  onClick={() => navigate('/admin/apps?create=true')}
                  className="mt-3 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  创建新应用
                </button>
              </div>
            </div>
          </div>
        ) : (
          // 应用不存在错误 - 红色主题
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <h3 className="text-lg font-medium text-red-800 mb-2">{errorTitle}</h3>
            <p className="text-red-700 mb-4">{error || '无法找到指定的应用，请检查URL或返回应用列表。'}</p>
            <Link to="/admin/apps" className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
              返回应用列表
            </Link>
          </div>
        )}
      </div>
    );
  }
  
  const breadcrumbs = buildBreadcrumbs();
  
  return (
    <div className="p-6">
      {/* 面包屑导航 */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/apps" className="hover:text-blue-600">应用管理</Link>
          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={crumb.id}>
              <span>›</span>
              {crumb.path ? (
                <Link to={crumb.path} className="hover:text-blue-600">
                  {crumb.name}
                </Link>
              ) : (
                <span className="text-gray-700 font-medium">{crumb.name}</span>
              )}
            </React.Fragment>
          ))}
        </div>
        <h1 className="text-2xl font-bold text-gray-800">{app.name}</h1>
        <p className="text-gray-600 mt-1">{app.description}</p>
      </div>
      
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">文件夹管理</h2>
        <div className="flex space-x-2">
          <button 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center"
            onClick={() => {
              setParentFolderId(null);
              setShowCreateModal(true);
            }}
          >
            <span>+ 创建根文件夹</span>
          </button>
          {currentFolderId && (
            <button 
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center"
              onClick={() => {
                setParentFolderId(currentFolderId);
                setShowCreateModal(true);
              }}
            >
              <span>+ 在此文件夹下创建</span>
            </button>
          )}
        </div>
      </div>
      
      {/* 两栏布局 */}
      <div className="flex space-x-6">
        {/* 左侧：文件夹树 */}
        <div className="w-1/3">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h3 className="font-medium">文件夹树</h3>
            </div>
            <div className="p-4">
              {folders.length === 0 ? (
                <p className="text-gray-500 text-center py-4">暂无文件夹</p>
              ) : (
                <FolderTree
                  folders={folders}
                  currentFolderId={currentFolderId}
                  onFolderSelect={handleFolderClick}
                  onDeleteFolder={handleDeleteFolder}
                  onMoveFolder={handleMoveFolder}
                />
              )}
            </div>
          </div>
        </div>
        
        {/* 右侧：当前文件夹内容 */}
        <div className="w-2/3">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b flex justify-between items-center">
              <h3 className="font-medium">
                {currentFolder ? `${currentFolder.name} 的内容` : '选择文件夹'}
              </h3>
              {currentFolder && (
                <div className="flex space-x-2">
                  <button 
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                    onClick={() => handleNavigateToUpload(currentFolder.id)}
                  >
                    上传文档
                  </button>
                  <button 
                    className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                    onClick={() => handleNavigateToDocuments(currentFolder.id)}
                  >
                    查看文档
                  </button>
                </div>
              )}
            </div>
            
            <div className="p-4">
              {!currentFolder ? (
                <div className="text-center py-8 text-gray-500">
                  <FolderIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <p>请从左侧选择一个文件夹</p>
                </div>
              ) : (
                <>
                  {/* 文件夹信息 */}
                  <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-2">文件夹信息</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">名称:</span> 
                        <span className="ml-2 font-medium">{currentFolder.name}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">创建者:</span> 
                        <span className="ml-2">{currentFolder.created_by}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">路径:</span> 
                        <span className="ml-2 font-mono text-sm">{currentFolder.path || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">创建时间:</span> 
                        <span className="ml-2">{new Date(currentFolder.created_at).toLocaleString()}</span>
                      </div>
                      {currentFolder.description && (
                        <div className="col-span-2">
                          <span className="text-gray-500">描述:</span> 
                          <span className="ml-2">{currentFolder.description}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* 子文件夹列表 */}
                  {subfolders.length > 0 && (
                    <div className="mb-6">
                      <h4 className="font-medium mb-3">子文件夹 ({subfolders.length})</h4>
                      <div className="space-y-2">
                        {subfolders.map(folder => (
                          <div 
                            key={folder.id} 
                            className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                            onClick={() => handleFolderClick(folder.id)}
                          >
                            <div className="flex items-center">
                              <FolderIcon className="w-5 h-5 text-yellow-500 mr-2" />
                              <div className="flex-1">
                                <div className="font-medium">{folder.name}</div>
                                {folder.description && (
                                  <div className="text-sm text-gray-500">{folder.description}</div>
                                )}
                              </div>
                              <ChevronRightIcon className="w-5 h-5 text-gray-400" />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* AI 操作 */}
                  <div className="border-t pt-4">
                    <h4 className="font-medium mb-3">AI 操作</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <button 
                        className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                        onClick={() => {
                          setParentFolderId(currentFolder.id);
                          setShowCreateModal(true);
                        }}
                      >
                        <div className="font-medium">创建子文件夹</div>
                        <div className="text-sm text-gray-500">在当前文件夹下创建新文件夹</div>
                      </button>
                      <button 
                        className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                        onClick={() => handleNavigateToUpload(currentFolder.id)}
                      >
                        <div className="font-medium">上传文档</div>
                        <div className="text-sm text-gray-500">上传文件到此文件夹</div>
                      </button>
                      <button 
                        className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                        onClick={() => handleNavigateToDocuments(currentFolder.id)}
                      >
                        <div className="font-medium">查看文档</div>
                        <div className="text-sm text-gray-500">浏览此文件夹中的文档</div>
                      </button>
                      <button 
                        className="p-3 border rounded-lg hover:bg-blue-50 text-left border-blue-200"
                        onClick={() => handleEditFolder(currentFolder.id)}
                      >
                        <div className="font-medium text-blue-600">编辑文件夹</div>
                        <div className="text-sm text-blue-500">修改文件夹名称和描述</div>
                      </button>
                      <button 
                        className="p-3 border rounded-lg hover:bg-red-50 text-left border-red-200"
                        onClick={() => handleDeleteFolder(currentFolder.id)}
                      >
                        <div className="font-medium text-red-600">删除文件夹</div>
                        <div className="text-sm text-red-500">删除此文件夹及其所有内容</div>
                      </button>
                      <button 
                        className="p-3 border rounded-lg hover:bg-green-50 text-left border-green-200"
                        onClick={() => handleImportFolder(currentFolder.id)}
                      >
                        <div className="font-medium text-green-600">导入文件夹</div>
                        <div className="text-sm text-green-500">从本地驱动器导入整个文件夹</div>
                      </button>
                      <button 
                        className="p-3 border rounded-lg hover:bg-purple-50 text-left border-purple-200"
                        onClick={() => handleImportWebsite(currentFolder.id)}
                      >
                        <div className="font-medium text-purple-600">导入网站</div>
                        <div className="text-sm text-purple-500">爬取指定URL的网页和图像</div>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* 创建文件夹模态框 */}
      {showCreateModal && (
        <CreateFolderModal
          appId={app.id}
          parentFolderId={parentFolderId}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateFolder}
          folders={folders}
          mode="create"
        />
      )}
      
      {/* 编辑文件夹模态框 */}
      {showEditModal && editingFolder && (
        <CreateFolderModal
          appId={app.id}
          parentFolderId={editingFolder.parent_folder_id}
          onClose={() => {
            setShowEditModal(false);
            setEditingFolder(null);
          }}
          onSubmit={handleSaveEditFolder}
          folders={folders}
          mode="edit"
          folderToEdit={editingFolder}
        />
      )}
      
      {/* 导入网站模态框 */}
      {showImportWebsiteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-purple-800">导入网站</h3>
              <button
                onClick={() => setShowImportWebsiteModal(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  网站URL
                </label>
                <input
                  type="url"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={importingWebsite}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  爬取深度
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={crawlDepth}
                    onChange={(e) => setCrawlDepth(parseInt(e.target.value))}
                    className="flex-1"
                    disabled={importingWebsite}
                  />
                  <span className="text-sm font-medium text-purple-600 w-8">{crawlDepth}</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1 (仅首页)</span>
                  <span>3</span>
                  <span>5 (深度爬取)</span>
                </div>
                <p className="text-sm text-gray-600 mt-1">
                  深度 {crawlDepth}: {getDepthDescription(crawlDepth)}
                </p>
              </div>
              
              <div className="bg-gray-50 p-3 rounded-md">
                <p className="text-sm text-gray-600">
                  <strong>目标文件夹:</strong> {currentFolder?.name || '未选择'} <br />
                  <strong>应用:</strong> {app?.name || '未知'}
                </p>
              </div>
              
              {importError && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <p className="text-sm text-red-700">{importError}</p>
                </div>
              )}
              
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={() => setShowImportWebsiteModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  disabled={importingWebsite}
                >
                  取消
                </button>
                <button
                  onClick={handleSubmitImportWebsite}
                  disabled={importingWebsite || !websiteUrl.trim()}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {importingWebsite ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      导入中...
                    </>
                  ) : (
                    '开始导入'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// 辅助函数：获取深度描述
const getDepthDescription = (depth: number): string => {
  const descriptions = [
    '仅首页',
    '首页 + 直接链接',
    '首页 + 2层链接',
    '首页 + 3层链接',
    '深度爬取（可能较慢）',
    '非常深度爬取（可能非常慢）'
  ];
  return descriptions[Math.min(depth - 1, descriptions.length - 1)] || '自定义深度';
};

export default AdminAppFolders;