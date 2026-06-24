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
    parent_folder_path?: string;
    app_id: string;
  }) => {
    try {
      const parentFolderPath = data.parent_folder_path || getFullPath();
      
      await folderService.createFolder({
        name: data.name,
        description: data.description,
        parent_folder_path: parentFolderPath,
        path: parentFolderPath ? `${parentFolderPath.replace(/\/+$/, '')}/${data.name.trim().replace(/\s+/g, '-').toLowerCase()}` : '',
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
      <div style={{padding:24}}>
        <div  style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:24}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#991b1b",marginBottom:8}}>Load Failed</h3>
          <p style={{ color:"#b91c1c", marginBottom:16 }}>{error}</p>
          <div className="fb-d-flex fb-justify-center fb-gap-2">
            <button 
              onClick={() => window.location.reload()}
              className="btn btn-danger"
            >
              Reload
            </button>
            <Link 
              to="/admin/apps"
              className="btn btn-default"
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
      <div style={{padding:24}}>
        <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
          <div >
            <div className="fb-spinner" style={{height:48,width:48,borderWidth:2,borderColor:"#2563eb",borderRadius:"50%"}}></div>
            <p  style={{ marginTop:16 }}>Loading path contents...</p>
          </div>
        </div>
      </div>
    );
  }
  
  // 确保应用数据已加载
  if (!app) {
    return (
      <div style={{padding:24}}>
        <div  style={{background:"#fefce8",border:"1px solid #fef08a",borderRadius:8,padding:24}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#854d0e",marginBottom:8}}>Missing App Info</h3>
          <p style={{ color:"#a16207", marginBottom:16 }}>Failed to load app info. Please go back to the app list.</p>
          <Link 
            to="/admin/apps"
            className="btn btn-warning"
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
        <div style={{padding:24}}>
          <div  style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:24}}>
            <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#991b1b",marginBottom:8}}>Document Load Failed</h3>
            <p style={{ color:"#b91c1c", marginBottom:16 }}>{error}</p>
            <div className="fb-d-flex fb-justify-center fb-gap-2">
              <button 
                onClick={() => window.location.reload()}
                className="btn btn-danger"
              >
                Reload
              </button>
              <button 
                onClick={handleNavigateUp}
                className="btn btn-default"
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
        <div style={{padding:24}}>
          <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
            <div >
              <div className="fb-spinner" style={{height:48,width:48,borderWidth:2,borderColor:"#2563eb",borderRadius:"50%"}}></div>
              <p  style={{ marginTop:16 }}>Loading document details...</p>
            </div>
          </div>
        </div>
      );
    }
    
    // 文档详情显示
    return (
      <div style={{padding:24}}>
        <div style={{marginBottom:24}}>
          <div className="fb-d-flex fb-align-center" style={{gap:8,fontSize:"0.875rem",marginBottom:8}}>
            <Link to="/admin/apps" className="fb-link">Apps</Link>
            <span>›</span>
            <Link to={`/admin/${appSlug}`} className="fb-link">{app.name}</Link>
            <span>›</span>
            <span style={{color:"#374151"}}>Document Details</span>
          </div>
          <div className="fb-d-flex fb-justify-between fb-align-center">
            <div>
              <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>
                {documentDetail?.title || documentDetail?.original_filename || 'Document Details'}
              </h1>
              <p  style={{ marginTop:4 }}>Path: {getFullPath()}</p>
            </div>
            <div className="fb-d-flex fb-gap-2">
              <button 
                onClick={handleNavigateUp}
                className="btn btn-default"
              >
                Go Up
              </button>
              <Link 
                to={`/admin/documents/${(documentDetail?.path || documentDetail?.storage_path || documentDetail?.id).replace(/^\//, '')}`}
                className="btn btn-primary"
              >
                Full Details
              </Link>
            </div>
          </div>
        </div>
        
        {/* 文档详情卡片 */}
        <div className="panel panel-default" style={{overflow:"hidden"}}>
          <div style={{padding:24}}>
            <div className="row">
              {/* 基本信息 */}
              <div>
                <h3 className="fb-label" style={{ color:"#374151", marginBottom:12 }}>Basic Info</h3>
                <div className="fb-space-y" style={{gap:12}}>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>File Name</div>
                    <div style={{fontWeight:500}}>{documentDetail?.original_filename}</div>
                  </div>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>File Type</div>
                    <div style={{fontWeight:500}}>{documentDetail?.file_type?.toUpperCase()}</div>
                  </div>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>File Size</div>
                    <div style={{fontWeight:500}}>
                      {(documentDetail?.file_size ? documentDetail.file_size / 1024 / 1024 : 0).toFixed(2)} MB
                    </div>
                  </div>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>Created</div>
                    <div style={{fontWeight:500}}>
                      {documentDetail?.created_at ? new Date(documentDetail.created_at).toLocaleString() : 'Unknown'}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* 状态信息 */}
              <div>
                <h3 className="fb-label" style={{ color:"#374151", marginBottom:12 }}>Status</h3>
                <div className="fb-space-y" style={{gap:12}}>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>Conversion</div>
                    <div style={{fontWeight:500}}>
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
                    <div  style={{fontSize:"0.875rem"}}>Published</div>
                    <div style={{fontWeight:500}}>
                      <span className={`px-2 py-1 rounded text-xs ${
                        documentDetail?.publish_status === 'PUBLISHED' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {documentDetail?.publish_status || 'UNPUBLISHED'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>Document ID</div>
                    <div style={{ fontFamily:"monospace", fontSize:"0.875rem" }}>{documentDetail?.id}</div>
                  </div>
                  <div>
                    <div  style={{fontSize:"0.875rem"}}>Storage Path</div>
                    <div style={{ fontFamily:"monospace", fontSize:"0.875rem", overflow:"hidden" }}>{documentDetail?.storage_path || 'Not set'}</div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 描述 */}
            {documentDetail?.description && (
              <div style={{  paddingTop:24 ,  marginTop:24, borderTop:"1px solid #e5e7eb"  }}>
                <h3 className="fb-label" style={{ color:"#374151", marginBottom:8 }}>Description</h3>
                <p >{documentDetail.description}</p>
              </div>
            )}
            
            {/* 操作按钮 */}
            <div className="fb-justify-end" style={{  paddingTop:24 ,  marginTop:24, borderTop:"1px solid #e5e7eb", display:"flex", columnGap:12  }}>
              <button 
                className="btn btn-default"
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
                className="btn btn-primary"
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
        <div  style={{ marginTop:24, background:"#f9fafb", borderRadius:8, padding:16, fontSize:"0.875rem" }}>
          <div className="fb-d-flex fb-align-center">
            <svg style={{ width:16, height:16, marginRight:8 }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <span>Path: <code style={{ background:"#f3f4f6", paddingLeft:4, borderRadius:4 }}>{getFullPath()}</code></span>
          </div>
          <div style={{marginTop:8}}>
            This page uses the new path URL pattern to access documents. Click "Full Details" to view the complete document info page.
          </div>
        </div>
      </div>
    );
  }
  
  // 文件夹模式
  return (
    <div style={{padding:24}}>
      {/* 面包屑导航 */}
      <div style={{marginBottom:24}}>
        <div className="fb-d-flex fb-align-center" style={{gap:8,fontSize:"0.875rem",marginBottom:8}}>
          <Link to="/admin/apps" className="fb-link">Apps</Link>
          <span>›</span>
          <Link to={`/admin/${appSlug}`} className="fb-link">{app.name}</Link>
          
          {/* 动态路径面包屑 */}
          {pathParam && pathParam.split('/').filter(Boolean).map((segment, index, array) => {
            const pathSoFar = array.slice(0, index + 1).join('/');
            return (
              <React.Fragment key={segment}>
                <span>›</span>
                <Link 
                  to={`/admin/${appSlug}/${pathSoFar}`}
                  className="fb-link"
                >
                  {segment}
                </Link>
              </React.Fragment>
            );
          })}
        </div>
        
        <div className="fb-d-flex fb-justify-between fb-align-center">
          <div>
            <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>
              {currentFolder?.name || app.name}
            </h1>
            {currentFolder?.description && (
              <p  style={{ marginTop:4 }}>{currentFolder.description}</p>
            )}
            <p  style={{ fontSize:"0.875rem", marginTop:4 }}>Path: {getFullPath()}</p>
          </div>
          
          <div className="fb-d-flex fb-gap-2">
            {pathParam && (
              <button 
                onClick={handleNavigateUp}
                className="btn btn-default"
              >
                Go Up
              </button>
            )}
            <button 
              className="btn btn-default"
              onClick={() => window.location.reload()}
            >
              Refresh
            </button>
            <Link 
              to={`/admin/apps/${appSlug}?folder=${encodeURIComponent(getFullPath())}`}
              className="btn btn-primary"
            >
              Classic View
            </Link>
          </div>
        </div>
      </div>
      
      {/* 内容区域 */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(1, minmax(0, 1fr))", gap:24 }}>
        {/* 左侧：子文件夹列表 */}
        <div >
          <div className="panel panel-default" style={{overflow:"hidden"}}>
            <div style={{padding:16,borderBottom:"1px solid #e5e7eb"}}>
              <h3 style={{fontWeight:500}}>Subfolders ({subfolders.length})</h3>
            </div>
            
            {subfolders.length === 0 ? (
              <div  style={{ padding:32 }}>
                <svg  style={{ width:48, height:48, color:"#d1d5db", marginBottom:12 }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                <p>No subfolders</p>
              </div>
            ) : (
              <div style={{borderTop:"1px solid #e5e7eb"}}>
                {subfolders.map(folder => (
                  <div 
                    key={folder.path || folder.name} 
                    style={{ padding:16, cursor:"pointer" }}
                    onClick={() => handleFolderClick(folder.path || `/${appSlug}/${folder.name}`)}
                  >
                    <div className="fb-d-flex fb-align-center">
                      <svg style={{  marginRight:12 ,  width:20, height:20, color:"#eab308"  }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                      </svg>
                      <div style={{flex:1}}>
                        <div style={{fontWeight:500}}>{folder.name}</div>
                        {folder.description && (
                          <div  style={{fontSize:"0.875rem"}}>{folder.description}</div>
                        )}
                        <div style={{ fontSize:"0.75rem", color:"#9ca3af", marginTop:4 }}>
                          Path: {folder.path || 'Not set'}
                        </div>
                      </div>
                      <svg style={{ width:20, height:20, color:"#9ca3af" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
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
          <div className="panel panel-default" style={{overflow:"hidden"}}>
            <div style={{padding:16,borderBottom:"1px solid #e5e7eb"}}>
              <h3 style={{fontWeight:500}}>Documents ({documents.length})</h3>
            </div>
            
            {documents.length === 0 ? (
              <div  style={{ padding:32 }}>
                <svg  style={{ width:48, height:48, color:"#d1d5db", marginBottom:12 }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p>No documents</p>
              </div>
            ) : (
              <div style={{borderTop:"1px solid #e5e7eb"}}>
                {documents.slice(0, 10).map(doc => (
                  <div 
                    key={doc.path || doc.storage_path || doc.name} 
                    style={{ padding:16, cursor:"pointer" }}
                    onClick={() => handleDocumentClick(doc)}
                  >
                    <div className="fb-d-flex fb-align-center">
                      <svg style={{  marginRight:12 ,  width:20, height:20, color:"#3b82f6"  }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                      <div style={{flex:1}}>
                        <div style={{ fontWeight:500, overflow:"hidden" }}>{doc.title || doc.original_filename}</div>
                        <div  style={{fontSize:"0.875rem"}}>
                          {doc.file_type.toUpperCase()} • {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                {documents.length > 10 && (
                  <div  style={{ padding:16, borderTop:"1px solid #e5e7eb" }}>
                    <Link 
                      to={`/admin/apps/${appSlug}/folders/${encodeURIComponent(getFullPath())}/documents`}
                      className="fb-link" style={{fontSize:"0.875rem",color:"#2563eb"}}
                    >
                      View all {documents.length} documents →
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* 快速操作 */}
          <div style={{ marginTop:24, background:"#ffffff", borderRadius:8, boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)", padding:16 }}>
            <h4 style={{ fontWeight:500, marginBottom:12 }}>Quick Actions</h4>
            <div className="fb-space-y" style={{gap:8}}>
              <button 
                style={{ width:"100%", paddingLeft:16, paddingTop:8, background:"#2563eb", color:"#ffffff", borderRadius:4, fontSize:"0.875rem" }}
                onClick={() => navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(getFullPath())}`)}
              >
                Upload Documents
              </button>
              <button 
                style={{ width:"100%", paddingLeft:16, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:4, fontSize:"0.875rem" }}
                onClick={() => setShowCreateFolderModal(true)}
              >
                Create Subfolder
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* 路径信息卡片 */}
      <div  style={{ marginTop:24, background:"#f9fafb", borderRadius:8, padding:16, fontSize:"0.875rem" }}>
        <div className="fb-d-flex fb-align-center">
          <svg style={{ width:16, height:16, marginRight:8 }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span>New URL Pattern: <code style={{ background:"#f3f4f6", paddingLeft:4, borderRadius:4 }}>/admin/{appSlug}/{pathParam || ''}</code></span>
        </div>
        <div style={{marginTop:8}}>
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