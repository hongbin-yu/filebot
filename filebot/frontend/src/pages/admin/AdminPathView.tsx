import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import appService, { App } from '../../services/app.service';
import folderService, { Folder } from '../../services/folder.service';
import documentService, { Document } from '../../services/document.service';
import CreateFolderModal from '../../components/folders/CreateFolderModal';
import { showToast } from '../../components/common/ToastNotification';

const AdminPathView: React.FC = () => {
  // 获取URL参数：appSlug和路径通配符
  const { appSlug = '', '*': pathParam = '' } = useParams<{ appSlug: string; '*': string }>();
  const navigate = useNavigate();
  
  // 状态管理
  const [app, setApp] = useState<App | null>(null);
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [subfolders, setSubfolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 文档详情状态
  const [documentDetail, setDocumentDetail] = useState<Document | null>(null);
  
  // 创建文件夹模态框状态
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [allFolders, setAllFolders] = useState<Folder[]>([]);
  
  // 解析路径：判断是文件夹还是文档
  const isDocument = (): boolean => {
    if (!pathParam) return false;
    // 检查路径是否包含文件扩展名
    const hasExtension = /\.[a-zA-Z0-9]+$/.test(pathParam);
    return hasExtension;
  };
  
  // 获取完整路径
  const getFullPath = (): string => {
    if (!pathParam) {
      return `/${appSlug}`;
    }
    return `/${appSlug}/${pathParam}`;
  };
  
  // 加载路径内容
  const loadPathContents = async () => {
    if (!appSlug) {
      setError('App identifier cannot be empty');
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // 1. 获取应用信息
      const apps = await appService.getApps();
      const foundApp = apps.find(a => a.slug === appSlug || a.id === appSlug);
      if (!foundApp) {
        setError(`App "${appSlug}" not found`);
        setLoading(false);
        return;
      }
      setApp(foundApp);
      
      const fullPath = getFullPath();
      
      if (isDocument()) {
        // 文档模式：显示文档详情
        console.log('文档路径:', fullPath);
        
        try {
          // 通过路径搜索文档
          const searchResults = await documentService.searchDocuments({
            path: fullPath,
            limit: 1
          });
          
          if (searchResults.length > 0) {
            const doc = searchResults[0];
            setDocumentDetail(doc);
            setError(null);
          } else {
            setError(`Document not found at path "${fullPath}"`);
          }
        } catch (docError: any) {
          console.error('加载文档详情失败:', docError);
          setError(`Failed to load document details: ${docError.response?.data?.detail || docError.message || 'Unknown error'}`);
        }
      } else {
        // 文件夹模式：显示文件夹内容
        console.log('文件夹路径:', fullPath);
        
        // 2. 尝试通过路径获取文件夹详情
        try {
          const folderDetails = await folderService.getFolder(fullPath);
          setCurrentFolder(folderDetails);
        } catch (folderError) {
          console.warn('通过路径获取文件夹失败，可能是根目录或路径不存在:', folderError);
          // 如果是根目录（pathParam为空），创建虚拟根文件夹
          if (!pathParam) {
            setCurrentFolder({
              id: 'root',
              name: foundApp.name,
              description: foundApp.description || '',
              path: `/${appSlug}`,
              app_id: foundApp.id,
              app_slug: foundApp.slug,
              parent_folder_id: undefined,
              parent_folder_path: undefined,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              created_by: 'system',
              document_count: 0,
              total_size: 0,
              is_system_folder: true,
              order_index: 0
            });
          } else {
            setError(`Path "${fullPath}" does not exist or is not accessible`);
          }
        }
        
        // 3. 获取子文件夹列表（使用路径作为父文件夹路径）
        try {
          const foldersData = await folderService.getFolders(appSlug, {
            parent_folder_path: fullPath
          });
          setSubfolders(foldersData);
        } catch (foldersError) {
          console.warn('获取子文件夹失败:', foldersError);
          setSubfolders([]);
        }
        
        // 4. 获取所有文件夹（用于创建文件夹模态框）
        try {
          const allFoldersData = await folderService.getFolders(appSlug);
          setAllFolders(allFoldersData);
        } catch (allFoldersError) {
          console.warn('获取所有文件夹失败:', allFoldersError);
          setAllFolders([]);
        }
        
        // 5. 获取文档列表（使用路径作为文件夹路径）
        try {
          const docs = await documentService.getDocuments(fullPath);
          setDocuments(docs);
        } catch (docsError) {
          console.warn('获取文档列表失败:', docsError);
          setDocuments([]);
        }
      }
      
    } catch (err: any) {
      console.error('加载路径内容失败:', err);
      setError(`Failed to load path: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };
  
  // 处理文件夹点击
  const handleFolderClick = (folderPath: string) => {
    // 从完整路径中提取相对路径部分
    const relativePath = folderPath.replace(`/${appSlug}/`, '');
    navigate(`/admin/${appSlug}/${relativePath}`);
  };
  
  // 处理文档点击 - 使用path而非UUID
  const handleDocumentClick = (doc: any) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    navigate(`/admin/documents/${docPath.replace(/^\//, '')}`);
  };
  
  // 处理Go Up
  const handleNavigateUp = () => {
    if (!pathParam) {
      // 已经是根目录，Back to Apps
      navigate('/admin/apps');
      return;
    }
    
    // 移除路径的最后一部分
    const pathParts = pathParam.split('/').filter(Boolean);
    if (pathParts.length > 1) {
      const parentPath = pathParts.slice(0, -1).join('/');
      navigate(`/admin/${appSlug}/${parentPath}`);
    } else {
      // 返回到根目录（无路径参数）
      navigate(`/admin/${appSlug}`);
    }
  };
  
  // 处理创建文件夹
  const handleCreateFolder = async (data: {
    name: string;
    description?: string;
    parent_folder_id?: string;
    app_id: string;
  }) => {
    try {
      // 使用路径作为父文件夹标识符
      const parentFolderPath = data.parent_folder_path || getFullPath();
      
      // 调用folderService创建文件夹
      // 注意：FolderCreateRequest接口期望parent_folder_id和app_id
      // 但后端API可能支持parent_folder_path参数
      await folderService.createFolder({
        name: data.name,
        description: data.description,
        parent_folder_id: parentFolderPath, // 使用路径作为parent_folder_id
        app_id: data.app_id
      });
      
      // 关闭模态框
      setShowCreateFolderModal(false);
      
      // Reload当前路径内容
      await loadPathContents();
      
      // 显示成功消息（可以添加toast通知）
      showToast(`Folder "${data.name}" created successfully!`, 'success');
    } catch (err: any) {
      console.error('创建文件夹失败:', err);
      showToast(`Create folder failed: ${err.response?.data?.detail || err.message || 'Unknown error'}`, 'error');
      throw err; // 重新抛出错误，让模态框处理
    }
  };
  
  // 加载路径内容
  useEffect(() => {
    loadPathContents();
  }, [appSlug, pathParam]);
  
  // 错误状态
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">Load Failed</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <div className="flex justify-center space-x-3">
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Reload
            </button>
            <Link 
              to="/admin/apps"
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            >
              Back to Apps
            </Link>
          </div>
        </div>
      </div>
    );
  }
  
  // 加载状态
  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading path contents...</p>
          </div>
        </div>
      </div>
    );
  }
  
  // 确保应用数据已加载
  if (!app) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">Missing App Info</h3>
          <p className="text-yellow-700 mb-4">Failed to load app info. Please go back to the app list.</p>
          <Link 
            to="/admin/apps"
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Back to Apps
          </Link>
        </div>
      </div>
    );
  }
  
  // 文档模式
  if (isDocument()) {
    // 错误状态
    if (error) {
      return (
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <h3 className="text-lg font-medium text-red-800 mb-2">Document Load Failed</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <div className="flex justify-center space-x-3">
              <button 
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reload
              </button>
              <button 
                onClick={handleNavigateUp}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Go Up
              </button>
            </div>
          </div>
        </div>
      );
    }
    
    // 加载状态
    if (loading) {
      return (
        <div className="p-6">
          <div className="flex justify-center items-center h-64">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading document details...</p>
            </div>
          </div>
        </div>
      );
    }
    
    // 文档详情显示
    return (
      <div className="p-6">
        <div className="mb-6">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
            <Link to="/admin/apps" className="hover:text-blue-600">Apps</Link>
            <span>›</span>
            <Link to={`/admin/${appSlug}`} className="hover:text-blue-600">{app.name}</Link>
            <span>›</span>
            <span className="text-gray-700">Document Details</span>
          </div>
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                {documentDetail?.title || documentDetail?.original_filename || 'Document Details'}
              </h1>
              <p className="text-gray-600 mt-1">Path: {getFullPath()}</p>
            </div>
            <div className="flex space-x-3">
              <button 
                onClick={handleNavigateUp}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Go Up
              </button>
              <Link 
                to={`/admin/documents/${(documentDetail?.path || documentDetail?.storage_path || documentDetail?.id).replace(/^\//, '')}`}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Full Details
              </Link>
            </div>
          </div>
        </div>
        
        {/* 文档详情卡片 */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 基本信息 */}
              <div>
                <h3 className="font-medium text-gray-700 mb-3">Basic Info</h3>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-500">File Name</div>
                    <div className="font-medium">{documentDetail?.original_filename}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">File Type</div>
                    <div className="font-medium">{documentDetail?.file_type?.toUpperCase()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">File Size</div>
                    <div className="font-medium">
                      {(documentDetail?.file_size ? documentDetail.file_size / 1024 / 1024 : 0).toFixed(2)} MB
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Created</div>
                    <div className="font-medium">
                      {documentDetail?.created_at ? new Date(documentDetail.created_at).toLocaleString() : 'Unknown'}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* 状态信息 */}
              <div>
                <h3 className="font-medium text-gray-700 mb-3">Status</h3>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-500">Conversion</div>
                    <div className="font-medium">
                      <span className={`px-2 py-1 rounded text-xs ${
                        documentDetail?.conversion_status === 'completed' ? 'bg-green-100 text-green-800' :
                        documentDetail?.conversion_status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                        documentDetail?.conversion_status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {documentDetail?.conversion_status || 'pending'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Published</div>
                    <div className="font-medium">
                      <span className={`px-2 py-1 rounded text-xs ${
                        documentDetail?.publish_status === 'PUBLISHED' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {documentDetail?.publish_status || 'UNPUBLISHED'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Document ID</div>
                    <div className="font-mono text-sm">{documentDetail?.id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Storage Path</div>
                    <div className="font-mono text-sm truncate">{documentDetail?.storage_path || 'Not set'}</div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 描述 */}
            {documentDetail?.description && (
              <div className="mt-6 pt-6 border-t">
                <h3 className="font-medium text-gray-700 mb-2">Description</h3>
                <p className="text-gray-600">{documentDetail.description}</p>
              </div>
            )}
            
            {/* 操作按钮 */}
            <div className="mt-6 pt-6 border-t flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => {
                  if (documentDetail?.id) {
                    documentService.downloadDocument(documentDetail.id, 'original')
                      .then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = documentDetail.original_filename;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                      })
                      .catch(err => {
                        console.error('下载失败:', err);
                        showToast('Download failed: ' + (err.response?.data?.detail || err.message || 'Unknown error'), 'error');
                      });
                  }
                }}
              >
                Download Original
              </button>
              <button 
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                onClick={() => {
                  if (documentDetail?.id) {
                    const docNav = (documentDetail.path || documentDetail.storage_path || documentDetail.id).replace(/^\//, '');
                    navigate(`/admin/documents/${docNav}`);
                  }
                }}
              >
                View Full Details
              </button>
            </div>
          </div>
        </div>
        
        {/* 路径信息卡片 */}
        <div className="mt-6 bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
          <div className="flex items-center">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <span>Path: <code className="bg-gray-100 px-1 rounded">{getFullPath()}</code></span>
          </div>
          <div className="mt-2">
            This page uses the new path URL pattern to access documents. Click "Full Details" to view the complete document info page.
          </div>
        </div>
      </div>
    );
  }
  
  // 文件夹模式
  return (
    <div className="p-6">
      {/* 面包屑导航 */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/apps" className="hover:text-blue-600">Apps</Link>
          <span>›</span>
          <Link to={`/admin/${appSlug}`} className="hover:text-blue-600">{app.name}</Link>
          
          {/* 动态路径面包屑 */}
          {pathParam && pathParam.split('/').filter(Boolean).map((segment, index, array) => {
            const pathSoFar = array.slice(0, index + 1).join('/');
            return (
              <React.Fragment key={segment}>
                <span>›</span>
                <Link 
                  to={`/admin/${appSlug}/${pathSoFar}`}
                  className="hover:text-blue-600"
                >
                  {segment}
                </Link>
              </React.Fragment>
            );
          })}
        </div>
        
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              {currentFolder?.name || app.name}
            </h1>
            {currentFolder?.description && (
              <p className="text-gray-600 mt-1">{currentFolder.description}</p>
            )}
            <p className="text-sm text-gray-500 mt-1">Path: {getFullPath()}</p>
          </div>
          
          <div className="flex space-x-3">
            {pathParam && (
              <button 
                onClick={handleNavigateUp}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Go Up
              </button>
            )}
            <button 
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              onClick={() => window.location.reload()}
            >
              Refresh
            </button>
            <Link 
              to={`/admin/apps/${appSlug}?folder=${encodeURIComponent(getFullPath())}`}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Classic View
            </Link>
          </div>
        </div>
      </div>
      
      {/* 内容区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：子文件夹列表 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b">
              <h3 className="font-medium">Subfolders ({subfolders.length})</h3>
            </div>
            
            {subfolders.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                <p>No subfolders</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {subfolders.map(folder => (
                  <div 
                    key={folder.path || folder.name} 
                    className="p-4 hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleFolderClick(folder.path || `/${appSlug}/${folder.name}`)}
                  >
                    <div className="flex items-center">
                      <svg className="w-5 h-5 text-yellow-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                      </svg>
                      <div className="flex-1">
                        <div className="font-medium">{folder.name}</div>
                        {folder.description && (
                          <div className="text-sm text-gray-500">{folder.description}</div>
                        )}
                        <div className="text-xs text-gray-400 mt-1">
                          Path: {folder.path || 'Not set'}
                        </div>
                      </div>
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* 右侧：文档列表 */}
        <div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b">
              <h3 className="font-medium">Documents ({documents.length})</h3>
            </div>
            
            {documents.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p>No documents</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {documents.slice(0, 10).map(doc => (
                  <div 
                    key={doc.path || doc.storage_path || doc.name} 
                    className="p-4 hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleDocumentClick(doc)}
                  >
                    <div className="flex items-center">
                      <svg className="w-5 h-5 text-blue-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                      <div className="flex-1">
                        <div className="font-medium truncate">{doc.title || doc.original_filename}</div>
                        <div className="text-sm text-gray-500">
                          {doc.file_type.toUpperCase()} • {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                {documents.length > 10 && (
                  <div className="p-4 text-center border-t">
                    <Link 
                      to={`/admin/apps/${appSlug}/folders/${encodeURIComponent(getFullPath())}/documents`}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View all {documents.length} documents →
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* 快速操作 */}
          <div className="mt-6 bg-white rounded-lg shadow p-4">
            <h4 className="font-medium mb-3">Quick Actions</h4>
            <div className="space-y-2">
              <button 
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                onClick={() => navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(getFullPath())}`)}
              >
                Upload Documents
              </button>
              <button 
                className="w-full px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 text-sm"
                onClick={() => setShowCreateFolderModal(true)}
              >
                Create Subfolder
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* 路径信息卡片 */}
      <div className="mt-6 bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
        <div className="flex items-center">
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span>New URL Pattern: <code className="bg-gray-100 px-1 rounded">/admin/{appSlug}/{pathParam || ''}</code></span>
        </div>
        <div className="mt-2">
          This page uses the new path URL pattern. Click "Classic View" to switch back.
        </div>
      </div>
      
      {/* 创建文件夹模态框 */}
      {showCreateFolderModal && (
        <CreateFolderModal
          appSlug={appSlug}
          parentFolderPath={getFullPath()}
          onClose={() => setShowCreateFolderModal(false)}
          onSubmit={handleCreateFolder}
          folders={allFolders}
          mode="create"
        />
      )}
    </div>
  );
};

export default AdminPathView;