import React, { useState, useEffect } from 'react';
import folderService, { Folder, FolderTreeItem } from '../services/folder.service';
import appService, { App } from '../services/app.service';

const Folders: React.FC = () => {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [folderTree, setFolderTree] = useState<FolderTreeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<App | null>(null);
  const [apps, setApps] = useState<App[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [newFolderName, setNewFolderName] = useState('');
  const [newFolderDescription, setNewFolderDescription] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [parentFolderId, setParentFolderId] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchApps();
  }, []);

  useEffect(() => {
    if (selectedApp) {
      fetchFolders(selectedApp.slug || selectedApp.id);
    } else {
      setFolders([]);
      setFolderTree([]);
    }
  }, [selectedApp]);

  const fetchApps = async (retryCount = 0) => {
    try {
      setLoading(true);
      
      // 检查token是否已准备好（修复竞态条件）
      if (!localStorage.getItem('access_token') && retryCount === 0) {
        console.log('Token not ready, waiting 500ms before fetching apps...');
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      const data = await appService.getApps();
      setApps(data || []);
      if (data && data.length > 0) {
        setSelectedApp(data[0]);
      }
    } catch (err: any) {
      console.error('Failed to fetch apps:', err);
      
      // 如果是认证错误（401）且还可以重试，等待后重试一次
      if (err.response?.status === 401 && retryCount < 1) {
        console.log('Authentication error, retrying after 500ms...');
        await new Promise(resolve => setTimeout(resolve, 500));
        return fetchApps(retryCount + 1);
      }
      
      // 显示错误信息，但提供刷新按钮
      setError(
        'Failed to load applications. ' + 
        (err.response?.status === 401 
          ? 'Please ensure you are logged in. Try refreshing the page.' 
          : 'Please try again.')
      );
    } finally {
      setLoading(false);
    }
  };



  const fetchFolders = async (appSlug: string, retryCount = 0) => {
    try {
      setLoading(true);
      setError(null);
      // 使用应用slug获取文件夹，默认获取应用根目录下的文件夹
      const data = await folderService.getFolders(appSlug, { 
        parent_folder_path: `/${appSlug}` 
      });
      setFolders(data || []);
      // 构建简单的树形结构（这里简化处理，实际应该使用后端返回的树形结构）
      const treeData = buildFolderTree(data || []);
      setFolderTree(treeData);
    } catch (err: any) {
      console.error('Failed to fetch folders:', err);
      
      // 如果是认证错误（401）且还可以重试，等待后重试一次
      if (err.response?.status === 401 && retryCount < 1) {
        console.log('Authentication error in fetchFolders, retrying after 500ms...');
        await new Promise(resolve => setTimeout(resolve, 500));
        return fetchFolders(appSlug, retryCount + 1);
      }
      
      setError('Failed to load folders. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const buildFolderTree = (folders: Folder[]): FolderTreeItem[] => {
    const folderMap = new Map<string, FolderTreeItem>();
    const rootFolders: FolderTreeItem[] = [];

    // 创建所有文件夹的映射
    folders.forEach(folder => {
      folderMap.set(folder.id, {
        ...folder,
        children: [],
        level: 0,
        expanded: false
      });
    });

    // 构建树形结构
    folders.forEach(folder => {
      const treeItem = folderMap.get(folder.id)!;
      if (folder.parent_folder_id && folderMap.has(folder.parent_folder_id)) {
        const parent = folderMap.get(folder.parent_folder_id)!;
        if (!parent.children) {
          parent.children = [];
        }
        treeItem.level = parent.level + 1;
        parent.children.push(treeItem);
      } else {
        rootFolders.push(treeItem);
      }
    });

    return rootFolders;
  };

  const toggleFolderExpansion = (folderId: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId);
    } else {
      newExpanded.add(folderId);
    }
    setExpandedFolders(newExpanded);
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim() || !selectedApp) {
      setError('Folder name is required and an app must be selected.');
      return;
    }

    try {
      setLoading(true);
      await folderService.createFolder({
        name: newFolderName,
        description: newFolderDescription || undefined,
        parent_folder_id: parentFolderId,
        app_id: selectedApp.slug || selectedApp.id
      });

      // 刷新文件夹列表
      if (selectedApp) {
        await fetchFolders(selectedApp.slug || selectedApp.id);
      }

      // 重置表单
      setNewFolderName('');
      setNewFolderDescription('');
      setParentFolderId(undefined);
      setShowCreateForm(false);
      setError(null);
      
      // 可选的：显示成功消息（如果需要）
      // console.log('Created folder:', newFolder.name);
    } catch (err) {
      console.error('Failed to create folder:', err);
      setError('Failed to create folder. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    // 先查找文件夹信息，以便显示路径
    const folderToDelete = folders.find(f => f.id === folderId);
    const folderPathStr = folderToDelete?.path ? `\n目标路径: ${folderToDelete.path}` : '';
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete this folder? All subfolders and documents will be deleted.${folderPathStr}`);
    if (!confirmed) {
      return;
    }

    try {
      setLoading(true);
      
      if (!folderToDelete) {
        throw new Error('找不到要删除的文件夹');
      }
      
      // 使用文件夹路径进行删除（如果存在路径，否则使用ID）
      const folderPath = folderToDelete.path || folderToDelete.id;
      await folderService.deleteFolder(folderPath, true);
      
      // 刷新文件夹列表
      if (selectedApp) {
        await fetchFolders(selectedApp.slug || selectedApp.id);
      }
      setError(null);
    } catch (err) {
      console.error('Failed to delete folder:', err);
      setError('Failed to delete folder. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderFolderTree = (folders: FolderTreeItem[], level = 0) => {
    return (
      <div className="ml-4">
        {folders.map(folder => (
          <div key={folder.id} className="mb-2">
            <div className="flex items-center p-2 bg-gray-50 rounded hover:bg-gray-100">
              <button
                onClick={() => toggleFolderExpansion(folder.id)}
                className="mr-2 text-gray-500 hover:text-gray-700"
              >
                {folder.children && folder.children.length > 0 ? (
                  expandedFolders.has(folder.id) ? '▼' : '▶'
                ) : (
                  <span className="w-4 inline-block">•</span>
                )}
              </button>
              <div className="flex-1">
                <span className="font-medium">{folder.name}</span>
                {folder.description && (
                  <span className="text-gray-500 text-sm ml-2">- {folder.description}</span>
                )}
                <div className="text-xs text-gray-400 mt-1">
                  {folder.document_count !== undefined && (
                    <span>{folder.document_count} documents</span>
                  )}
                  {folder.total_size !== undefined && (
                    <span className="ml-2">• {formatFileSize(folder.total_size)}</span>
                  )}
                </div>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setParentFolderId(folder.id)}
                  className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  title="Create subfolder here"
                >
                  Add Subfolder
                </button>
                <button
                  onClick={() => handleDeleteFolder(folder.id)}
                  className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                >
                  Delete
                </button>
              </div>
            </div>
            {folder.children && folder.children.length > 0 && expandedFolders.has(folder.id) && (
              <div className="mt-1">
                {renderFolderTree(folder.children, level + 1)}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  if (loading && apps.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-500">Loading applications...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800">Folders Management</h1>
          <p className="text-gray-600 mt-2">Organize your documents into folders and subfolders</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-700 mb-2">{error}</div>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  setError(null);
                  fetchApps();
                }}
                className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm"
              >
                Retry
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm"
              >
                Refresh Page
              </button>
              {!localStorage.getItem('access_token') && (
                <button
                  onClick={() => window.location.href = '/login'}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
                >
                  Go to Login
                </button>
              )}
            </div>
          </div>
        )}

        {/* App Selection */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Select Application</h2>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Application
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={selectedApp?.id || ''}
                onChange={(e) => {
                  const app = apps.find(a => a.id === e.target.value);
                  setSelectedApp(app || null);
                }}
              >
                <option value="">Select an application</option>
                {apps.map(app => (
                  <option key={app.id} value={app.id}>
                    {app.name} {app.description && `- ${app.description}`}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Create Folder Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Create New Folder</h2>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {showCreateForm ? 'Cancel' : 'New Folder'}
            </button>
          </div>

          {showCreateForm && (
            <div className="mt-4 p-4 border border-gray-200 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Folder Name *
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    placeholder="Enter folder name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Parent Folder
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={parentFolderId || ''}
                    onChange={(e) => setParentFolderId(e.target.value || undefined)}
                  >
                    <option value="">Root Level (No Parent)</option>
                    {folders.map(folder => (
                      <option key={folder.id} value={folder.id}>
                        {folder.name}
                      </option>
                    ))}
                  </select>
                  {parentFolderId && (
                    <p className="mt-2 text-sm text-gray-500">
                      Folder will be created under selected parent
                    </p>
                  )}
                </div>
              </div>
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={newFolderDescription}
                  onChange={(e) => setNewFolderDescription(e.target.value)}
                  placeholder="Enter folder description"
                  rows={2}
                />
              </div>
              <div className="mt-6 flex justify-end">
                <button
                  onClick={handleCreateFolder}
                  disabled={!newFolderName.trim() || !selectedApp}
                  className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create Folder
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Folder Tree */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Folder Structure</h2>
            <div className="text-sm text-gray-500">
              {folders.length} folder{folders.length !== 1 ? 's' : ''} total
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-gray-500">Loading folders...</div>
            </div>
          ) : folders.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              {selectedApp ? (
                <>
                  <p className="text-lg">No folders found for this application.</p>
                  <p className="mt-2">Click "New Folder" to create your first folder.</p>
                </>
              ) : (
                <p className="text-lg">Please select an application to view folders.</p>
              )}
            </div>
          ) : (
            <div className="mt-4">
              {renderFolderTree(folderTree)}
            </div>
          )}
        </div>

        {/* Folder Statistics */}
        {folders.length > 0 && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-500">Total Folders</h3>
              <p className="text-2xl font-bold text-gray-800 mt-1">{folders.length}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-500">Total Documents</h3>
              <p className="text-2xl font-bold text-gray-800 mt-1">
                {folders.reduce((total, folder) => total + (folder.document_count || 0), 0)}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-500">Total Size</h3>
              <p className="text-2xl font-bold text-gray-800 mt-1">
                {formatFileSize(folders.reduce((total, folder) => total + (folder.total_size || 0), 0))}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Folders;