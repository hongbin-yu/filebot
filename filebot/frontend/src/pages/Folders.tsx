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

    // 创建所有文件夹的映射（使用path作为key，Folder主键是path）
    folders.forEach(folder => {
      folderMap.set(folder.path, {
        ...folder,
        children: [],
        level: 0,
        expanded: false
      });
    });

    // 构建树形结构
    folders.forEach(folder => {
      const treeItem = folderMap.get(folder.path)!;
      if (folder.parent_folder_path && folderMap.has(folder.parent_folder_path)) {
        const parent = folderMap.get(folder.parent_folder_path)!;
        if (!parent.children) {
          parent.children = [];
        }
        treeItem.level = parent.level + 1;
        parent.children.push(treeItem);
      } else {
        rootFolders.push(treeItem);
      }    });

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

  const handleDeleteFolder = async (folderPath: string) => {
    // 先查找文件夹信息，以便显示路径
    const folderToDelete = folders.find(f => f.path === folderPath);
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
      <div style={{marginLeft:16}}>
        {folders.map(folder => (
          <div key={folder.path} style={{marginBottom:8}}>
            <div className="fb-d-flex fb-align-center" style={{padding:8,backgroundColor:"#f9fafb",borderRadius:4}}>
              <button
                onClick={() => toggleFolderExpansion(folder.path)}
                className="text-muted fb-link" style={{marginRight:8}}
              >
                {folder.children && folder.children.length > 0 ? (
                  expandedFolders.has(folder.path) ? '▼' : '▶'
                ) : (
                  <span style={{width:16,display:"inline-block"}}>•</span>
                )}
              </button>
              <div style={{flex:1}}>
                <span style={{fontWeight:500}}>{folder.name}</span>
                {folder.description && (
                  <span className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginLeft:8}}>- {folder.description}</span>
                )}
                <div style={{fontSize:"0.75rem",lineHeight:"1rem",color:"#9ca3af",marginTop:4}}>
                  {folder.document_count !== undefined && (
                    <span>{folder.document_count} documents</span>
                  )}
                  {folder.total_size !== undefined && (
                    <span style={{marginLeft:8}}>• {formatFileSize(folder.total_size)}</span>
                  )}
                </div>
              </div>
              <div className="fb-d-flex" style={{display:"flex",gap:8}}>
                <button
                  onClick={() => setParentFolderId(folder.path)}
                  style={{paddingLeft:8,paddingRight:8,paddingTop:4,paddingBottom:4,fontSize:"0.75rem",lineHeight:"1rem",backgroundColor:"#dbeafe",color:"#1d4ed8",borderRadius:4}}
                  title="Create subfolder here"
                >
                  Add Subfolder
                </button>
                <button
                  onClick={() => handleDeleteFolder(folder.path)}
                  style={{paddingLeft:8,paddingRight:8,paddingTop:4,paddingBottom:4,fontSize:"0.75rem",lineHeight:"1rem",backgroundColor:"#fee2e2",color:"#b91c1c",borderRadius:4}}
                >
                  Delete
                </button>
              </div>
            </div>
            {folder.children && folder.children.length > 0 && expandedFolders.has(folder.path) && (
              <div style={{marginTop:4}}>
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
      <div className="fb-page-bg">
        <div style={{maxWidth:"72rem",marginLeft:"auto",marginRight:"auto"}}>
          <div className="fb-d-flex fb-align-center" style={{justifyContent:"center",height:256}}>
            <div className="text-muted">Loading applications...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fb-page-bg" style={{backgroundColor:"#f9fafb",padding:32}}>
      <div style={{maxWidth:"72rem",marginLeft:"auto",marginRight:"auto"}}>
        <div style={{marginBottom:32}}>
          <h1 style={{fontSize:"1.875rem",lineHeight:"2.25rem",fontWeight:700,color:"#1f2937"}}>Folders Management</h1>
          <p className="text-muted" style={{marginTop:8}}>Organize your documents into folders and subfolders</p>
        </div>

        {error && (
          <div style={{marginBottom:24,padding:16,backgroundColor:"#fef2f2",border:"1px solid #ddd",borderColor:"#fecaca",borderRadius:8}}>
            <div style={{color:"#b91c1c",marginBottom:8}}>{error}</div>
            <div className="fb-d-flex" style={{display:"flex",gap:8}}>
              <button
                onClick={() => {
                  setError(null);
                  fetchApps();
                }}
                style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#fee2e2",color:"#b91c1c",borderRadius:4,fontSize:"0.875rem",lineHeight:"1.25rem"}}
              >
                Retry
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#e5e7eb",color:"#374151",borderRadius:4,fontSize:"0.875rem",lineHeight:"1.25rem"}}
              >
                Refresh Page
              </button>
              {!localStorage.getItem('access_token') && (
                <button
                  onClick={() => window.location.href = '/login'}
                  style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#dbeafe",color:"#1d4ed8",borderRadius:4,fontSize:"0.875rem",lineHeight:"1.25rem"}}
                >
                  Go to Login
                </button>
              )}
            </div>
          </div>
        )}

        {/* App Selection */}
        <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:24,marginBottom:24}}>
          <h2 style={{fontSize:"1.25rem",lineHeight:"1.75rem",fontWeight:600,color:"#1f2937",marginBottom:16}}>Select Application</h2>
          <div className="row" style={{gap:16}}>
            <div>
              <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
                Application
              </label>
              <select
                style={{width:"100%",paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:6}}
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
        <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:24,marginBottom:24}}>
          <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
            <h2 style={{fontSize:"1.25rem",lineHeight:"1.75rem",fontWeight:600,color:"#1f2937"}}>Create New Folder</h2>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,backgroundColor:"#2563eb",color:"#fff",borderRadius:6}}
            >
              {showCreateForm ? 'Cancel' : 'New Folder'}
            </button>
          </div>

          {showCreateForm && (
            <div style={{marginTop:16,padding:16,border:"1px solid #ddd",borderColor:"#e5e7eb",borderRadius:8}}>
              <div style={{display:"grid",gridTemplateColumns:"repeat(1, 1fr)",gap:16}}>
                <div>
                  <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
                    Folder Name *
                  </label>
                  <input
                    type="text"
                    style={{width:"100%",paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:6}}
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    placeholder="Enter folder name"
                  />
                </div>
                <div>
                  <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
                    Parent Folder
                  </label>
                  <select
                    style={{width:"100%",paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:6}}
                    value={parentFolderId || ''}
                    onChange={(e) => setParentFolderId(e.target.value || undefined)}
                  >
                    <option value="">Root Level (No Parent)</option>
                    {folders.map(folder => (
                      <option key={folder.path} value={folder.path}>
                        {folder.name}
                      </option>
                    ))}
                  </select>
                  {parentFolderId && (
                    <p className="text-muted" style={{marginTop:8,fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                      Folder will be created under selected parent
                    </p>
                  )}
                </div>
              </div>
              <div style={{marginTop:16}}>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
                  Description (Optional)
                </label>
                <textarea
                  style={{width:"100%",paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:6}}
                  value={newFolderDescription}
                  onChange={(e) => setNewFolderDescription(e.target.value)}
                  placeholder="Enter folder description"
                  rows={2}
                />
              </div>
              <div className="fb-d-flex" style={{marginTop:24,justifyContent:"flex-end"}}>
                <button
                  onClick={handleCreateFolder}
                  disabled={!newFolderName.trim() || !selectedApp}
                  style={{paddingLeft:24,paddingRight:24,paddingTop:8,paddingBottom:8,backgroundColor:"#16a34a",color:"#fff",borderRadius:6}}
                >
                  Create Folder
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Folder Tree */}
        <div className="panel panel-default" style={{padding:24}}>
          <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
            <h2 style={{fontSize:"1.25rem",lineHeight:"1.75rem",fontWeight:600,color:"#1f2937"}}>Folder Structure</h2>
            <div className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem"}}>
              {folders.length} folder{folders.length !== 1 ? 's' : ''} total
            </div>
          </div>

          {loading ? (
            <div className="fb-d-flex fb-align-center" style={{justifyContent:"center",height:128}}>
              <div className="text-muted">Loading folders...</div>
            </div>
          ) : folders.length === 0 ? (
            <div className="text-center py-12 text-muted">
              {selectedApp ? (
                <>
                  <p style={{fontSize:"1.125rem",lineHeight:"1.75rem"}}>No folders found for this application.</p>
                  <p style={{marginTop:8}}>Click "New Folder" to create your first folder.</p>
                </>
              ) : (
                <p style={{fontSize:"1.125rem",lineHeight:"1.75rem"}}>Please select an application to view folders.</p>
              )}
            </div>
          ) : (
            <div style={{marginTop:16}}>
              {renderFolderTree(folderTree)}
            </div>
          )}
        </div>

        {/* Folder Statistics */}
        {folders.length > 0 && (
          <div style={{display:"grid",gridTemplateColumns:"repeat(1, 1fr)",marginTop:24,gap:16}}>
            <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:16}}>
              <h3 className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500}}>Total Folders</h3>
              <p style={{fontSize:"1.5rem",lineHeight:"2rem",fontWeight:700,color:"#1f2937",marginTop:4}}>{folders.length}</p>
            </div>
            <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:16}}>
              <h3 className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500}}>Total Documents</h3>
              <p style={{fontSize:"1.5rem",lineHeight:"2rem",fontWeight:700,color:"#1f2937",marginTop:4}}>
                {folders.reduce((total, folder) => total + (folder.document_count || 0), 0)}
              </p>
            </div>
            <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:16}}>
              <h3 className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500}}>Total Size</h3>
              <p style={{fontSize:"1.5rem",lineHeight:"2rem",fontWeight:700,color:"#1f2937",marginTop:4}}>
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