import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link, useLocation } from 'react-router-dom';
import documentService, { Document as ApiDocument } from '../services/document.service';
import folderService, { Folder } from '../services/folder.service';
import appService, { App } from '../services/app.service';
import featureService from '../services/feature.service';
import exportService from '../services/export.service';
import { extractIdFromSlug, extractAppIdFromSlug, generateFolderSlug, generateDocumentSlug } from '../utils/slugUtils';

type Document = ApiDocument;

const AppDocuments: React.FC = () => {
  const { appId: appSlugParam, folderId: folderIdParam } = useParams<{ appId: string; folderId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Extract the original appId from the slug
  // 优先使用导航状态中的appId（从AppFolders传递），否则尝试从slug提取
  const stateAppId = location.state?.appId;
  const extractedAppId = appSlugParam ? extractAppIdFromSlug(appSlugParam) || appSlugParam : null;
  const appId = stateAppId || extractedAppId;
  const appSlug = appSlugParam || '';
  
  // 获取当前路径用于后备slug提取
  const currentPath = window.location.pathname;
  
  // 紧急修复：如果appSlug为空，尝试从URL路径提取
  const getEffectiveAppSlug = () => {
    if (appSlug && appSlug !== 'undefined' && appSlug !== 'null') {
      return appSlug;
    }
    
    // 尝试从当前路径提取应用slug
    const path = currentPath;
    
    // 匹配路径模式：/appSlug/folders/folderId/documents
    const pattern1 = /^\/([^\/]+)\/folders\/[^\/]+\/documents$/;
    const match1 = path.match(pattern1);
    if (match1 && match1[1]) {
      return match1[1];
    }
    
    // 匹配路径模式：/appSlug/folders/folderId
    const pattern2 = /^\/([^\/]+)\/folders\/[^\/]+$/;
    const match2 = path.match(pattern2);
    if (match2 && match2[1]) {
      return match2[1];
    }
    
    // 简单提取第一个部分
    const matchSimple = path.match(/^\/([^\/]+)/);
    return matchSimple ? matchSimple[1] : '';
  };
  
  const effectiveAppSlug = getEffectiveAppSlug();
  
  // 验证folderIdParam
  if (!folderIdParam) {
    console.error('folderIdParam为空！');
  }
  
  // 生成上传路径（如果folder已加载，使用path；否则用原始param并编码）
  const [uploadPath, setUploadPath] = React.useState(`/${effectiveAppSlug}/folders/${encodeURIComponent(folderIdParam)}/upload`);

  // 当folder加载后更新uploadPath
  React.useEffect(() => {
    if (folder?.path) {
      setUploadPath(`/${effectiveAppSlug}/folders/${encodeURIComponent(folder.path)}/upload`);
    }
  }, [folder?.path, effectiveAppSlug]);
  
  const [documents, setDocuments] = useState<Document[]>([]);
  const [folder, setFolder] = useState<Folder | null>(null);
  const [app, setApp] = useState<App | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [edition, setEdition] = useState<string>('basic');
  const [error, setError] = useState<string | null>(null);
  const [drawerSlug, setDrawerSlug] = useState<string>('');
  const [drawerInfo, setDrawerInfo] = useState<any>(null);
  const [exporting, setExporting] = useState(false);

  // 根据文件夹ID推断抽屉slug（模拟数据专用）
  const getDrawerSlugFromFolderId = (folderId: string): string => {
    if (!folderId) return '';
    
    // 模拟数据中的文件夹ID模式
    if (folderId.includes('174100') || folderId.includes('174101') || folderId.includes('174102')) {
      return 'en'; // 英文抽屉
    } else if (folderId.includes('174200') || folderId.includes('174201') || folderId.includes('174202')) {
      return 'fr'; // 法文抽屉
    } else if (folderId.includes('174300') || folderId.includes('174301') || folderId.includes('174302')) {
      return 'website-content'; // 网站内容抽屉
    }
    return '';
  };

  // 解析folderId：支持UUID或路径
  const parseFolderId = (folderIdParam: string): string => {
    console.log('🔧 解析folderId参数:', folderIdParam);
    
    if (!folderIdParam) {
      console.warn('⚠️ folderIdParam为空');
      return '';
    }
    
    // 首先解码参数（如果它是编码的路径）
    const decodedParam = decodeURIComponent(folderIdParam);
    console.log('🔧 解码后的参数:', decodedParam);
    
    // 检查是否是路径（以/开头）
    if (decodedParam.startsWith('/')) {
      console.log('✅ 识别为路径:', decodedParam);
      return decodedParam;
    }
    
    // 如果参数包含"-"，则可能是"uuid-slug"格式
    if (decodedParam.includes('-')) {
      // 检查是否以UUID开头（UUID格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
      const match = decodedParam.match(uuidPattern);
      if (match) {
        console.log('✅ 提取到UUID:', match[0]);
        return match[0]; // 返回UUID部分
      }
      
      // 如果不是标准UUID格式，尝试提取ID部分
      const parts = decodedParam.split('-');
      // 假设ID是第一部分（或前几部分）
      const extractedId = parts[0];
      console.log('⚠️ 非标准格式，提取ID部分:', extractedId);
      return extractedId;
    }
    
    console.log('ℹ️ 直接使用参数:', decodedParam);
    return decodedParam;
  };

  const folderId = parseFolderId(folderIdParam || '');
  
  // 验证folderId是否为有效格式
  const isValidFolderId = (id: string): boolean => {
    if (!id || id.trim() === '') return false;
    
    // 开发模式：放宽验证，允许各种ID格式用于测试
    const DEV_MODE = true;
    
    // 检查是否为有效的UUID格式
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (uuidPattern.test(id)) {
      return true;
    }
    
    // 检查是否为数字ID（可能用于模拟数据）
    const numericPattern = /^\d+$/;
    if (numericPattern.test(id)) {
      return true;
    }
    
    // 检查是否可能为模拟数据ID（以mock-开头）
    if (id.startsWith('mock-')) {
      return true;
    }
    
    // 检查是否可能为模拟数据ID（以folder-开头）
    if (id.startsWith('folder-')) {
      console.warn('⚠️ 模拟文件夹ID格式（开发模式允许）:', id);
      return true;
    }
    
    // 开发模式：允许"folder"等简单ID用于测试
    if (DEV_MODE) {
      console.warn('⚠️ 非标准文件夹ID格式（开发模式允许）:', id);
      return true;
    }
    
    console.warn('❌ 无效的folderId格式:', id);
    return false;
  };

  // 导出文件夹数据
  const handleExportFolder = async () => {
    if (!folderId || !folder || !app) {
      setError('无法导出：缺少文件夹或应用信息');
      return;
    }

    try {
      setExporting(true);
      setError(null);
      
      console.log(`📤 开始导出文件夹数据: ${folder.name} (${folderId})`);
      
      await exportService.exportAndDownloadFolder(
        folderId,
        folder.name || 'unknown-folder'
      );
      
      console.log(`✅ 文件夹数据导出完成`);
    } catch (error: any) {
      console.error('❌ 导出失败:', error);
      setError(`导出失败: ${error.message || '未知错误'}`);
    } finally {
      setExporting(false);
    }
  };

  // 导出应用数据
  const handleExportApp = async () => {
    if (!appId || !app) {
      setError('无法导出：缺少应用信息');
      return;
    }

    try {
      setExporting(true);
      setError(null);
      
      console.log(`📤 开始导出应用数据: ${app.name} (${appId})`);
      
      await exportService.exportAndDownloadApp(
        appId,
        app.name || 'unknown-app'
      );
      
      console.log(`✅ 应用数据导出完成`);
    } catch (error: any) {
      console.error('❌ 导出失败:', error);
      setError(`导出失败: ${error.message || '未知错误'}`);
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    if (appId && folderId) {
      fetchData();
    }
  }, [appId, folderId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 从导航状态中获取抽屉信息
      console.log('🔧 完整location对象:', location);
      console.log('🔧 location.state:', location.state);
      console.log('🔧 location.pathname:', location.pathname);
      
      let newDrawerSlug = '';
      let newDrawerInfo = null;
      
      if (location.state) {
        console.log('🔧 导航状态:', location.state);
        if (location.state.drawerSlug) {
          newDrawerSlug = location.state.drawerSlug;
          console.log('✅ 从导航状态获取drawerSlug:', newDrawerSlug);
        }
        if (location.state.drawerInfo) {
          newDrawerInfo = location.state.drawerInfo;
          console.log('✅ 从导航状态获取drawerInfo:', newDrawerInfo);
        }
      } else {
        console.log('⚠️ location.state为空，无法获取抽屉信息');
      }
      
      // 后备方案：根据文件夹ID推断抽屉slug
      if (!newDrawerSlug && folderId) {
        const inferredSlug = getDrawerSlugFromFolderId(folderId);
        if (inferredSlug) {
          newDrawerSlug = inferredSlug;
          console.log('🔍 根据文件夹ID推断抽屉slug:', inferredSlug, 'folderId:', folderId);
        }
      }
      
      // 设置抽屉状态
      setDrawerSlug(newDrawerSlug);
      setDrawerInfo(newDrawerInfo);
      
      console.log('📊 最终抽屉状态:', { drawerSlug: newDrawerSlug, drawerInfo: newDrawerInfo });
      
      console.log('🔧 fetchData参数:', { appId, folderId, folderIdParam, appSlugParam, currentPath, locationState: location.state });
      
      // 验证folderId
      if (!folderId || !isValidFolderId(folderId)) {
        const errorMsg = `无效的文件夹ID: ${folderId}。请通过有效的文件夹访问文档列表。`;
        console.error('❌', errorMsg);
        setError(errorMsg);
        setLoading(false);
        return;
      }
      
      console.log('📋 文件夹ID详情:', {
        rawFolderIdParam: folderIdParam,
        parsedFolderId: folderId,
        isValid: isValidFolderId(folderId),
        isUUID: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(folderId)
      });
      
      // 获取应用详情
      if (appId) {
        const appData = await appService.getAppById(appId);
        setApp(appData);
      }
      
      // 获取文件夹详情
      if (folderId) {
        try {
          const folderData = await folderService.getFolder(folderId);
          setFolder(folderData);
          console.log('📁 文件夹详情:', folderData);
        } catch (folderError) {
          console.warn('Could not fetch folder details:', folderError);
          // 继续执行，只是没有文件夹详情
        }
      }
      
      // 获取该文件夹的文档
      console.log('📋 获取文档，folder_id:', folderId);
      console.log('📋 调用documentService.getDocuments({ folder_id:', folderId, '})');
      const folderDocuments = await documentService.getDocuments(folderId);
      console.log('✅ 获取到文档数量:', folderDocuments.length);
      console.log('📄 文档列表:', folderDocuments.map(doc => ({ id: doc.id, title: doc.title, folder_id: doc.folder_id })));
      setDocuments(folderDocuments);
      
      // 检查AI状态
      const enabled = await featureService.isAIClassificationEnabled();
      setAiEnabled(enabled);
      
      // 获取版本
      const editionInfo = await featureService.getCurrentEdition();
      setEdition(editionInfo.edition);
      
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setError(`获取数据失败: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    const targetDoc = documents.find(d => d.id === id);
    const docName = targetDoc?.original_filename || targetDoc?.title || 'this document';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\n存储路径: ${docPathStr}` : '';
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete "${docName}"?${docPathInfo}`);
    if (!confirmed) {
      return;
    }
    
    try {
      await documentService.deleteDocument(id);
      setDocuments(documents.filter(doc => doc.id !== id));
    } catch (error) {
      console.error('Failed to delete document:', error);
      window.showWetAlert('Failed to delete document. Please try again.');
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const docTitle = doc.title || doc.original_filename || '';
    return docTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
           doc.file_type.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileIcon = (fileType: string): string => {
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('image')) return '🖼️';
    if (fileType.includes('text') || fileType.includes('document')) return '📝';
    if (fileType.includes('spreadsheet') || fileType.includes('excel')) return '📊';
    if (fileType.includes('presentation') || fileType.includes('powerpoint')) return '📽️';
    if (fileType.includes('zip') || fileType.includes('archive')) return '📦';
    return '📎';
  };

  const getAICategoryColor = (category?: string) => {
    if (!category) return 'gray';
    
    const colors: Record<string, string> = {
      'INVOICE': 'green',
      'CONTRACT': 'blue',
      'REPORT': 'purple',
      'RESUME': 'yellow',
      'TECHNICAL': 'indigo',
      'ADMIN': 'pink',
      'GENERAL': 'gray'
    };
    
    return colors[category] || 'gray';
  };

  const getAICategoryText = (category?: string) => {
    if (!category) return '未分类';
    
    const translations: Record<string, string> = {
      'INVOICE': '发票',
      'CONTRACT': '合同',
      'REPORT': '报告',
      'RESUME': '简历',
      'TECHNICAL': '技术文档',
      'ADMIN': '行政文档',
      'GENERAL': '通用文档'
    };
    
    return translations[category] || category;
  };

  const getClassificationStatusBadge = (status?: string, confidence?: number) => {
    if (!status || !aiEnabled) return null;
    
    const statusConfig: Record<string, { color: string; text: string; icon: string }> = {
      'ai_classified': {
        color: 'bg-green-100 text-green-800',
        text: 'AI已分类',
        icon: '🤖'
      },
      'needs_manual': {
        color: 'bg-yellow-100 text-yellow-800',
        text: '待人工分类',
        icon: '👤'
      },
      'manual_classified': {
        color: 'bg-blue-100 text-blue-800',
        text: '人工已分类',
        icon: '👤✓'
      },
      'review_needed': {
        color: 'bg-orange-100 text-orange-800',
        text: '需审核',
        icon: '🔍'
      },
      'unclassified': {
        color: 'bg-gray-100 text-gray-800',
        text: '未分类',
        icon: '📄'
      }
    };
    
    const config = statusConfig[status.toLowerCase()] || statusConfig.unclassified;
    
    return (
      <div className="mt-2">
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
          {config.icon} {config.text}
          {confidence !== undefined && ` (${Math.round(confidence * 100)}%)`}
        </span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-600">Loading documents...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center text-sm text-gray-600 mb-6">
          <button
            onClick={() => navigate('/')}
            className="hover:text-blue-600"
          >
            Applications
          </button>
          <span className="mx-2">›</span>
          <button
            onClick={() => navigate(`/${appSlug}`)}
            className="hover:text-blue-600"
          >
            {app?.name || 'Application'}
          </button>
          {drawerSlug || drawerInfo ? (
            <>
              <span className="mx-2">›</span>
              <button
                onClick={() => navigate(`/${appSlug}/${drawerSlug || drawerInfo?.slug || drawerInfo?.id}`)}
                className="hover:text-blue-600"
              >
                {drawerInfo?.name || drawerSlug || 'Drawer'}
              </button>
              <span className="mx-2">›</span>
              <span className="font-medium text-gray-800">{folder?.name || 'Folder'} Documents</span>
            </>
          ) : (
            <>
              <span className="font-medium text-gray-800">{folder?.name || 'Folder'} Documents</span>
            </>
          )}
        </nav>
        
        {/* Debug info for drawer breadcrumb */}
        {process.env.NODE_ENV === 'development' && (
          <div className="text-xs text-gray-400 mb-2">
            抽屉调试: drawerSlug="{drawerSlug}", drawerInfo={drawerInfo ? `已设置(${drawerInfo.name})` : 'null'}, location.state={location.state ? JSON.stringify(location.state) : 'null'}
          </div>
        )}

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">{folder?.name || 'Folder'} Documents</h1>
            <div className="mt-2">
              <p className="text-gray-600">
                {app?.name ? `Application: ${app.name}` : ''} 
                {folder?.description && ` • ${folder.description}`}
              </p>
              <div className="mt-1 text-sm text-gray-500 flex items-center">
                <span>
                  {aiEnabled ? 'AI分类功能已启用' : '基础版本（无AI功能）'}
                </span>
                <span className={`ml-2 px-3 py-1 rounded-full text-xs font-medium ${
                  edition === 'basic' ? 'bg-gray-100 text-gray-800' :
                  edition === 'professional' ? 'bg-blue-100 text-blue-800' :
                  'bg-purple-100 text-purple-800'
                }`}>
                  {edition === 'basic' ? '基础版' : edition === 'professional' ? '专业版' : '企业版'}
                </span>
              </div>
            </div>
          </div>
          <div className="flex space-x-3 flex-wrap gap-2">
            <button
              onClick={() => navigate(`/${appSlug}`)}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
            >
              Back to Folders
            </button>
            
            {/* 主Upload按钮 - Button组件（最终修复方案） */}
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation(); // 阻止事件冒泡
                // 使用navigate函数进行客户端导航，传递抽屉信息（如果可用）
                const navState: any = {};
                if (drawerSlug) {
                  navState.drawerSlug = drawerSlug;
                }
                if (drawerInfo) {
                  navState.drawerInfo = drawerInfo;
                }
                // 同时传递appId以确保一致性
                if (appId) {
                  navState.appId = appId;
                }
                console.log('🔧 上传导航状态:', navState);
                navigate(uploadPath, { state: Object.keys(navState).length > 0 ? navState : undefined });
              }}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 flex items-center"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Upload Document
            </button>
            
            {/* 导出数据按钮 */}
            <button
              onClick={handleExportFolder}
              disabled={exporting || !folder || !app}
              className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Exporting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Export Folder
                </>
              )}
            </button>

          </div>
        </div>

        {/* AI功能说明条 */}
        {!aiEnabled && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-8">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">
                  当前为<strong>基础版本</strong>，不包含AI分类功能。
                  {edition === 'basic' && ' 如需AI功能，请升级到专业版或企业版。'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-red-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-red-800 font-medium">{error}</span>
            </div>
            <div className="mt-2 text-sm text-red-700">
              <p>可能的解决方案：</p>
              <ul className="list-disc list-inside mt-1">
                <li>请通过有效的文件夹访问文档列表</li>
                <li>检查URL中的文件夹ID格式是否正确</li>
                <li>返回<a href="/" className="underline text-blue-700">应用列表</a>重新选择文件夹</li>
              </ul>
            </div>
          </div>
        )}

        {/* Search and Stats */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Documents
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search by name or type..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <svg className="w-5 h-5 text-gray-400 absolute right-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
            
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-sm font-medium text-blue-700 mb-1">Total Documents</div>
              <div className="text-2xl font-bold text-blue-800">{documents.length}</div>
            </div>
            
            <div className="flex items-end">
              <button
                onClick={fetchData}
                className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 flex items-center justify-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Documents List (Table View) */}
        {filteredDocuments.length > 0 ? (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Document
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Uploaded
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredDocuments.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="text-2xl mr-4">
                            {getFileIcon(doc.file_type)}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                              {doc.title || doc.original_filename}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {doc.description || 'No description'}
                            </div>
                            {/* AI分类信息 */}
                            {aiEnabled && doc.ai_category && (
                              <div className="mt-1">
                                <span className={`inline-block px-2 py-1 rounded text-xs font-medium bg-${getAICategoryColor(doc.ai_category)}-100 text-${getAICategoryColor(doc.ai_category)}-800`}>
                                  {getAICategoryText(doc.ai_category)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {doc.file_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(doc.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          doc.folder_id ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {doc.folder_id ? 'In Folder' : 'Uncategorized'}
                        </span>
                        {getClassificationStatusBadge(doc.classification_status, doc.ai_confidence)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex space-x-2">
                          <Link
                            to={`/documents/${(doc.path || doc.storage_path || doc.id).replace(/^\//, '')}`}
                            className="text-blue-600 hover:text-blue-900"
                            title="View Details"
                          >
                            View
                          </Link>
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="text-red-600 hover:text-red-900"
                            title="Delete"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="text-6xl mb-6">📄</div>
            <h3 className="text-2xl font-bold text-gray-800 mb-4">
              {searchTerm 
                ? 'No matching documents found' 
                : 'No documents in this folder'}
            </h3>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              {searchTerm
                ? 'Try adjusting your search terms to find what you\'re looking for.'
                : 'Upload documents to this folder to start organizing them.'}
            </p>
            <Link
              to="/upload"
              className="inline-block bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 font-medium"
            >
              Upload Documents
            </Link>
          </div>
        )}

        {/* Footer Stats */}
        <div className="mt-8 text-center text-gray-600">
          <p>
            Showing {filteredDocuments.length} of {documents.length} documents in this folder
            {aiEnabled && ' • AI classification enabled'}
          </p>
          {folder && (
            <p className="mt-2 text-sm">
              Folder: <span className="font-medium">{folder.name}</span>
              {folder.document_count !== undefined && ` • ${folder.document_count} total documents`}
              {folder.total_size !== undefined && ` • ${formatFileSize(folder.total_size)} total size`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AppDocuments;