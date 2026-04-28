import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import documentService, { Document } from '../services/document.service';
import folderService, { Folder } from '../services/folder.service';
import appService, { App } from '../services/app.service';

const ClientDocumentDetail: React.FC = () => {
  // 从URL获取标识符（支持UUID和路径）
  const splat = useParams()['*'] || '';
  const identifier = splat.startsWith('/') ? splat : '/' + splat;
  
  const navigate = useNavigate();
  
  const [document, setDocument] = useState<Document | null>(null);
  const [folder, setFolder] = useState<Folder | null>(null);
  const [app, setApp] = useState<App | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [htmlContentUrl, setHtmlContentUrl] = useState<string | null>(null);

  // 解析文档标识符
  const getDocIdentifier = (): string => {
    // UUID去掉前面加的/
    const uuidPattern = /^\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    if (uuidPattern.test(identifier)) {
      return identifier.slice(1);
    }
    return identifier;
  };

  const docIdentifier = getDocIdentifier();

  useEffect(() => {
    const fetchDocument = async () => {
      if (!docIdentifier) {
        setError('文档标识符无效');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        const data = await documentService.getDocumentByIdentifier(docIdentifier);
        setDocument(data);
        
        // 获取文件夹和应用信息（优先使用路径）
        const folderIdentifier = data.folder_path || data.folder_id;
        if (folderIdentifier) {
          try {
            const folderData = await folderService.getFolder(folderIdentifier);
            setFolder(folderData);
            
            if (folderData.app_id) {
              const apps = await appService.getApps();
              const appData = apps.find((a: App) => a.id === folderData.app_id);
              if (appData) setApp(appData);
            }
          } catch (folderErr) {
            console.warn('获取文件夹信息失败:', folderErr);
          }
        }
      } catch (err: any) {
        console.error('获取文档详情失败:', err);
        setError(err.message || '加载文档失败');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [docIdentifier]);

  // 处理HTML预览内容加载
  useEffect(() => {
    let currentBlobUrl: string | null = null;
    
    const loadHtmlContent = async () => {
      if (!document || document.file_type.toLowerCase() !== 'html') {
        return;
      }

      // 如果已经有内容URL，先释放
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
        currentBlobUrl = null;
      }
      
      if (htmlContentUrl) {
        setHtmlContentUrl(null);
      }

      setPreviewLoading(true);
      
      try {
        const docApiId = document.path || document.storage_path || document.id;
        const blob = await documentService.downloadDocument(docApiId, 'original');
        
        if (blob.size === 0) {
          const emptyHtml = '<html><body><h3>文件内容为空</h3></body></html>';
          const emptyBlob = new Blob([emptyHtml], { type: 'text/html' });
          const url = URL.createObjectURL(emptyBlob);
          currentBlobUrl = url;
          setHtmlContentUrl(url);
        } else {
          const url = URL.createObjectURL(blob);
          currentBlobUrl = url;
          setHtmlContentUrl(url);
        }
      } catch (error: any) {
        console.error('加载HTML预览内容失败:', error);
        const errorHtml = `<html><body>
          <h3 style="color: #d32f2f;">加载HTML预览失败</h3>
          <p>错误信息: ${error.message || '未知错误'}</p>
        </body></html>`;
        const errorBlob = new Blob([errorHtml], { type: 'text/html' });
        const url = URL.createObjectURL(errorBlob);
        currentBlobUrl = url;
        setHtmlContentUrl(url);
      } finally {
        setPreviewLoading(false);
      }
    };

    loadHtmlContent();

    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [document]);

  const handleDownload = async (downloadType: 'original' | 'pdf' = 'original') => {
    if (!document) return;
    
    try {
      const docApiId = document.path || document.storage_path || document.id;
      const blob = await documentService.downloadDocument(docApiId, downloadType);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = `${document.original_filename}${downloadType === 'pdf' ? '.pdf' : ''}`;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (err: any) {
      console.error('下载失败:', err);
      window.showWetAlert('下载失败: ' + err.message);
    }
  };

  const handleBack = () => {
    if (folder && app) {
      navigate(`/apps/${app.slug || app.id}/folders/${encodeURIComponent(folder.path)}/documents`);
    } else {
      navigate('/apps');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
        <div className="max-w-4xl mx-auto text-center py-16">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">加载文档详情中...</p>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <h2 className="text-2xl font-bold text-red-600 mb-4">加载失败</h2>
            <p className="text-gray-700 mb-6">{error || '文档不存在'}</p>
            <button
              onClick={handleBack}
              className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              返回文档列表
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isHtmlFile = document.file_type.toLowerCase() === 'html';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* 面包屑导航 */}
        <div className="mb-6">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-4">
            <Link to="/apps" className="hover:text-blue-600">应用列表</Link>
            <span>›</span>
            {app && (
              <>
                <Link to={`/apps/${app.slug || app.id}`} className="hover:text-blue-600">
                  {app.name}
                </Link>
                <span>›</span>
              </>
            )}
            {folder && (
              <>
                <Link 
                  to={`/apps/${app?.slug || app?.id}/folders/${encodeURIComponent(folder.path)}/documents`} 
                  className="hover:text-blue-600"
                >
                  {folder.name}
                </Link>
                <span>›</span>
              </>
            )}
            <span className="text-gray-700">{document.original_filename}</span>
          </div>
        </div>

        {/* 标题和操作按钮 */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{document.original_filename}</h1>
              <div className="flex items-center space-x-3 mt-3">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {document.file_type.toUpperCase()}
                </span>
                <span className="text-gray-600">
                  大小: {formatFileSize(document.file_size)}
                </span>
                <span className="text-gray-600">
                  上传时间: {new Date(document.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleBack}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                返回
              </button>
              <button
                onClick={() => handleDownload('original')}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                下载
              </button>
            </div>
          </div>
        </div>

        {/* 文档预览区域 */}
        {isHtmlFile ? (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-800">HTML 预览</h2>
            </div>
            <div className="p-6">
              {previewLoading ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="mt-3 text-gray-600">加载HTML内容中...</p>
                </div>
              ) : htmlContentUrl ? (
                <div className="border border-gray-300 rounded-lg overflow-hidden">
                  <iframe
                    src={htmlContentUrl}
                    title={document.original_filename}
                    className="w-full h-[600px] border-0"
                    sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                  />
                  <div className="p-4 border-t border-gray-200 text-center">
                    <button
                      onClick={() => handleDownload('original')}
                      className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      下载HTML文件
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-600">无法加载HTML预览</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    重试
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <div className="text-gray-400 mb-6">
              <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              文件类型预览暂不可用
            </h3>
            <p className="text-gray-500 mb-6">
              {document.file_type.toUpperCase()} 格式的文件预览功能正在开发中。
              您可以下载文件后在本地查看。
            </p>
            <button
              onClick={() => handleDownload('original')}
              className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              下载 {document.file_type.toUpperCase()} 文件
            </button>
          </div>
        )}

        {/* 底部 */}
        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>FileBot Client Portal • 文档详情 • {document.original_filename}</p>
        </footer>
      </div>
    </div>
  );
};

export default ClientDocumentDetail;