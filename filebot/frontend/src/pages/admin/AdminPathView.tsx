import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import appService, { App } from '../../services/app.service';
import folderService, { Folder } from '../../services/folder.service';
import documentService, { Document } from '../../services/document.service';
import CreateFolderModal from '../../components/folders/CreateFolderModal';

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
      setError('应用标识符不能为空');
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
        setError(`应用 "${appSlug}" 不存在`);
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
            setError(`未找到路径为 "${fullPath}" 的文档`);
          }
        } catch (docError: any) {
          console.error('加载文档详情失败:', docError);
          setError(`无法加载文档详情: ${docError.response?.data?.detail || docError.message || '未知错误'}`);
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
            setError(`路径 "${fullPath}" 不存在或无法访问`);
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
      setError(`无法加载路径内容: ${err.response?.data?.detail || err.message || '未知错误'}`);
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
  
  // 处理返回上级
  const handleNavigateUp = () => {
    if (!pathParam) {
      // 已经是根目录，返回应用列表
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
      const parentFolderPath = data.parent_folder_id || getFullPath();
      
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
      
      // 重新加载当前路径内容
      await loadPathContents();
      
      // 显示成功消息（可以添加toast通知）
      window.showWetAlert(`文件夹 "${data.name}" 创建成功！`);
    } catch (err: any) {
      console.error('创建文件夹失败:', err);
      window.showWetAlert(`创建文件夹失败: ${err.response?.data?.detail || err.message || '未知错误'}`);
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
          <h3 className="text-lg font-medium text-red-800 mb-2">加载失败</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <div className="flex justify-center space-x-3">
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              重新加载
            </button>
            <Link 
              to="/admin/apps"
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            >
              返回应用列表
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
            <p className="mt-4 text-gray-600">加载路径内容中...</p>
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
          <h3 className="text-lg font-medium text-yellow-800 mb-2">应用信息缺失</h3>
          <p className="text-yellow-700 mb-4">无法加载应用信息，请返回应用列表重试。</p>
          <Link 
            to="/admin/apps"
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            返回应用列表
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
            <h3 className="text-lg font-medium text-red-800 mb-2">加载文档失败</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <div className="flex justify-center space-x-3">
              <button 
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                重新加载
              </button>
              <button 
                onClick={handleNavigateUp}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                返回上级
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
              <p className="mt-4 text-gray-600">加载文档详情中...</p>
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
            <Link to="/admin/apps" className="hover:text-blue-600">应用管理</Link>
            <span>›</span>
            <Link to={`/admin/${appSlug}`} className="hover:text-blue-600">{app.name}</Link>
            <span>›</span>
            <span className="text-gray-700">文档详情</span>
          </div>
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                {documentDetail?.title || documentDetail?.original_filename || '文档详情'}
              </h1>
              <p className="text-gray-600 mt-1">路径: {getFullPath()}</p>
            </div>
            <div className="flex space-x-3">
              <button 
                onClick={handleNavigateUp}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                返回上级
              </button>
              <Link 
                to={`/admin/documents/${(documentDetail?.path || documentDetail?.storage_path || documentDetail?.id).replace(/^\//, '')}`}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                完整详情
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
                <h3 className="font-medium text-gray-700 mb-3">基本信息</h3>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-500">文件名</div>
                    <div className="font-medium">{documentDetail?.original_filename}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">文件类型</div>
                    <div className="font-medium">{documentDetail?.file_type?.toUpperCase()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">文件大小</div>
                    <div className="font-medium">
                      {(documentDetail?.file_size ? documentDetail.file_size / 1024 / 1024 : 0).toFixed(2)} MB
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">创建时间</div>
                    <div className="font-medium">
                      {documentDetail?.created_at ? new Date(documentDetail.created_at).toLocaleString() : '未知'}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* 状态信息 */}
              <div>
                <h3 className="font-medium text-gray-700 mb-3">状态信息</h3>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-500">转换状态</div>
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
                    <div className="text-sm text-gray-500">发布状态</div>
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
                    <div className="text-sm text-gray-500">文档ID</div>
                    <div className="font-mono text-sm">{documentDetail?.id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">存储路径</div>
                    <div className="font-mono text-sm truncate">{documentDetail?.storage_path || '未设置'}</div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 描述 */}
            {documentDetail?.description && (
              <div className="mt-6 pt-6 border-t">
                <h3 className="font-medium text-gray-700 mb-2">描述</h3>
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
                        window.showWetAlert('下载失败: ' + (err.response?.data?.detail || err.message || '未知错误'));
                      });
                  }
                }}
              >
                下载原始文件
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
                查看完整详情
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
            <span>文档路径: <code className="bg-gray-100 px-1 rounded">{getFullPath()}</code></span>
          </div>
          <div className="mt-2">
            此页面使用新的路径URL模式访问文档。点击"完整详情"按钮可查看文档的完整信息页面。
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
          <Link to="/admin/apps" className="hover:text-blue-600">应用管理</Link>
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
            <p className="text-sm text-gray-500 mt-1">路径: {getFullPath()}</p>
          </div>
          
          <div className="flex space-x-3">
            {pathParam && (
              <button 
                onClick={handleNavigateUp}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                返回上级
              </button>
            )}
            <button 
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              onClick={() => window.location.reload()}
            >
              刷新
            </button>
            <Link 
              to={`/admin/apps/${appSlug}?folder=${encodeURIComponent(getFullPath())}`}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              传统视图
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
              <h3 className="font-medium">子文件夹 ({subfolders.length})</h3>
            </div>
            
            {subfolders.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                <p>暂无子文件夹</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {subfolders.map(folder => (
                  <div 
                    key={folder.id} 
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
                          路径: {folder.path || '未设置'}
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
              <h3 className="font-medium">文档 ({documents.length})</h3>
            </div>
            
            {documents.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p>暂无文档</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {documents.slice(0, 10).map(doc => (
                  <div 
                    key={doc.id} 
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
                      查看全部 {documents.length} 个文档 →
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* 快速操作 */}
          <div className="mt-6 bg-white rounded-lg shadow p-4">
            <h4 className="font-medium mb-3">快速操作</h4>
            <div className="space-y-2">
              <button 
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                onClick={() => navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(getFullPath())}`)}
              >
                上传文档
              </button>
              <button 
                className="w-full px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 text-sm"
                onClick={() => setShowCreateFolderModal(true)}
              >
                创建子文件夹
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
          <span>新URL模式: <code className="bg-gray-100 px-1 rounded">/admin/{appSlug}/{pathParam || ''}</code></span>
        </div>
        <div className="mt-2">
          此页面使用新的路径URL模式。点击"传统视图"按钮可切换到旧的查询参数模式。
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