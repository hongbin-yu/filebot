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
      console.log('✅ 文档列表:', folderDocuments.map(doc => ({ path: doc.path, title: doc.title, folder_path: doc.folder_path })));
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

  const handleDelete = async (docPath: string) => {
    const targetDoc = documents.find(d => d.path === docPath);
    const docName = targetDoc?.original_filename || targetDoc?.title || 'this document';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\n存储路径: ${docPathStr}` : '';
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete "${docName}"?${docPathInfo}`);
    if (!confirmed) {
      return;
    }
    
    try {
      await documentService.deleteDocument(docPath);
      setDocuments(documents.filter(doc => doc.path !== docPath));
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

  const getAICategoryStyle = (category?: string): { backgroundColor: string; color: string } => {
    const colorMap: Record<string, { backgroundColor: string; color: string }> = {
      green: { backgroundColor: '#dcfce7', color: '#166534' },
      blue: { backgroundColor: '#dbeafe', color: '#1e40af' },
      purple: { backgroundColor: '#f3e8ff', color: '#6b21a8' },
      yellow: { backgroundColor: '#fef3c7', color: '#854d0e' },
      indigo: { backgroundColor: '#e0e7ff', color: '#3730a3' },
      pink: { backgroundColor: '#fce7f3', color: '#9d174d' },
      gray: { backgroundColor: '#f3f4f6', color: '#1f2937' },
    };
    const colors: Record<string, string> = {
      'INVOICE': 'green',
      'CONTRACT': 'blue',
      'REPORT': 'purple',
      'RESUME': 'yellow',
      'TECHNICAL': 'indigo',
      'ADMIN': 'pink',
      'GENERAL': 'gray'
    };
    const colorName = (category ? colors[category] : null) || 'gray';
    return colorMap[colorName];
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
    
    const statusConfig: Record<string, { style: { backgroundColor: string; color: string }; text: string; icon: string }> = {
      'ai_classified': {
        style: { backgroundColor: '#dcfce7', color: '#166534' },
        text: 'AI已分类',
        icon: '🤖'
      },
      'needs_manual': {
        style: { backgroundColor: '#fef3c7', color: '#854d0e' },
        text: '待人工分类',
        icon: '👤'
      },
      'manual_classified': {
        style: { backgroundColor: '#dbeafe', color: '#1e40af' },
        text: '人工已分类',
        icon: '👤✓'
      },
      'review_needed': {
        style: { backgroundColor: '#ffedd5', color: '#9a3412' },
        text: '需审核',
        icon: '🔍'
      },
      'unclassified': {
        style: { backgroundColor: '#f3f4f6', color: '#1f2937' },
        text: '未分类',
        icon: '📄'
      }
    };
    
    const config = statusConfig[status.toLowerCase()] || statusConfig.unclassified;
    
    return (
      <div style={{marginTop:8}}>
        <span style={{paddingLeft:8,paddingRight:8,paddingTop:4,paddingBottom:4,borderRadius:9999,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...config.style}}>
          {config.icon} {config.text}
          {confidence !== undefined && ` (${Math.round(confidence * 100)}%)`}
        </span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="fb-page-bg">
        <div style={{maxWidth:"80rem",marginLeft:"auto",marginRight:"auto"}}>
          <div className="fb-d-flex fb-align-center" style={{justifyContent:"center",height:256}}>
            <div className="text-muted">Loading documents...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fb-page-bg" style={{backgroundColor:"#f9fafb",padding:32}}>
      <div style={{maxWidth:"80rem",marginLeft:"auto",marginRight:"auto"}}>
        {/* Breadcrumb Navigation */}
        <nav className="fb-d-flex fb-align-center text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginBottom:24}}>
          <button
            onClick={() => navigate('/')}
            className="fb-link"
          >
            Applications
          </button>
          <span style={{marginLeft:8,marginRight:8}}>›</span>
          <button
            onClick={() => navigate(`/${appSlug}`)}
            className="fb-link"
          >
            {app?.name || 'Application'}
          </button>
          {drawerSlug || drawerInfo ? (
            <>
              <span style={{marginLeft:8,marginRight:8}}>›</span>
              <button
                onClick={() => navigate(`/${appSlug}/${drawerSlug || drawerInfo?.slug || drawerInfo?.id}`)}
                className="fb-link"
              >
                {drawerInfo?.name || drawerSlug || 'Drawer'}
              </button>
              <span style={{marginLeft:8,marginRight:8}}>›</span>
              <span style={{fontWeight:500,color:"#1f2937"}}>{folder?.name || 'Folder'} Documents</span>
            </>
          ) : (
            <>
              <span style={{fontWeight:500,color:"#1f2937"}}>{folder?.name || 'Folder'} Documents</span>
            </>
          )}
        </nav>
        
        {/* Debug info for drawer breadcrumb */}
        {process.env.NODE_ENV === 'development' && (
          <div style={{fontSize:"0.75rem",lineHeight:"1rem",color:"#9ca3af",marginBottom:8}}>
            抽屉调试: drawerSlug="{drawerSlug}", drawerInfo={drawerInfo ? `已设置(${drawerInfo.name})` : 'null'}, location.state={location.state ? JSON.stringify(location.state) : 'null'}
          </div>
        )}

        {/* Header */}
        <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:32}}>
          <div>
            <h1 style={{fontSize:"1.875rem",lineHeight:"2.25rem",fontWeight:700,color:"#1f2937"}}>{folder?.name || 'Folder'} Documents</h1>
            <div style={{marginTop:8}}>
              <p className="text-muted">
                {app?.name ? `Application: ${app.name}` : ''} 
                {folder?.description && ` • ${folder.description}`}
              </p>
              <div className="text-muted fb-d-flex fb-align-center" style={{marginTop:4,fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                <span>
                  {aiEnabled ? 'AI分类功能已启用' : '基础版本（无AI功能）'}
                </span>
              <span style={{marginLeft:8,paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,borderRadius:9999,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...(edition === 'basic' ? {backgroundColor:'#f3f4f6',color:'#1f2937'} : edition === 'professional' ? {backgroundColor:'#dbeafe',color:'#1e40af'} : {backgroundColor:'#f3e8ff',color:'#6b21a8'})}}>
                  {edition === 'basic' ? '基础版' : edition === 'professional' ? '专业版' : '企业版'}
                </span>
              </div>
            </div>
          </div>
          <div className="fb-d-flex fb-gap-2" style={{display:"flex",gap:12,flexWrap:"wrap"}}>
            <button
              onClick={() => navigate(`/${appSlug}`)}
              style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",color:"#374151",borderRadius:6}}
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
              className="fb-d-flex fb-align-center" style={{backgroundColor:"#2563eb",color:"#fff",paddingLeft:24,paddingRight:24,paddingTop:8,paddingBottom:8,borderRadius:6}}
            >
              <svg style={{width:20,height:20,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Upload Document
            </button>
            
            {/* 导出数据按钮 */}
            <button
              onClick={handleExportFolder}
              disabled={exporting || !folder || !app}
              className="fb-d-flex fb-align-center" style={{backgroundColor:"#16a34a",color:"#fff",paddingLeft:24,paddingRight:24,paddingTop:8,paddingBottom:8,borderRadius:6}}
            >
              {exporting ? (
                <>
                  <svg className="fb-spinner" style={{marginLeft:-4,marginRight:12,height:20,width:20,color:"#fff"}} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle style={{opacity:0.25}} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path style={{opacity:0.75}} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Exporting...
                </>
              ) : (
                <>
                  <svg style={{width:20,height:20,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          <div style={{backgroundColor:"#fffbeb",borderLeftWidth:4,borderColor:"#facc15",padding:16,marginBottom:32}}>
            <div className="fb-d-flex">
              <div style={{flexShrink:0}}>
                <svg style={{height:20,width:20,color:"#facc15"}} viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div style={{marginLeft:12}}>
                <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#a16207"}}>
                  当前为<strong>基础版本</strong>，不包含AI分类功能。
                  {edition === 'basic' && ' 如需AI功能，请升级到专业版或企业版。'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div style={{marginBottom:32,padding:16,backgroundColor:"#fef2f2",border:"1px solid #ddd",borderColor:"#fecaca",borderRadius:8}}>
            <div className="fb-d-flex fb-align-center">
              <svg style={{width:20,height:20,color:"#dc2626",marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span style={{color:"#991b1b",fontWeight:500}}>{error}</span>
            </div>
            <div style={{marginTop:8,fontSize:"0.875rem",lineHeight:"1.25rem",color:"#b91c1c"}}>
              <p>可能的解决方案：</p>
              <ul style={{listStyleType:"disc",listStylePosition:"inside",marginTop:4}}>
                <li>请通过有效的文件夹访问文档列表</li>
                <li>检查URL中的文件夹ID格式是否正确</li>
                <li>返回<a href="/" style={{textDecoration:"underline",color:"#1d4ed8"}}>应用列表</a>重新选择文件夹</li>
              </ul>
            </div>
          </div>
        )}

        {/* Search and Stats */}
        <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:24,marginBottom:32}}>
          <div className="row" style={{gap:16}}>
            <div>
              <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
                Search Documents
              </label>
              <div style={{position:"relative"}}>
                <input
                  type="text"
                  placeholder="Search by name or type..."
                  style={{width:"100%",paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:8}}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <svg style={{width:20,height:20,color:"#9ca3af",position:"absolute",right:12,top:10}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
            
            <div style={{padding:16,backgroundColor:"#eff6ff",borderRadius:8}}>
              <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#1d4ed8",marginBottom:4}}>Total Documents</div>
              <div style={{fontSize:"1.5rem",lineHeight:"2rem",fontWeight:700,color:"#1e40af"}}>{documents.length}</div>
            </div>
            
            <div className="fb-d-flex" style={{alignItems:"flex-end"}}>
              <button
                onClick={fetchData}
                className="fb-d-flex fb-align-center" style={{width:"100%",backgroundColor:"#e5e7eb",color:"#374151",paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,borderRadius:8,justifyContent:"center"}}
              >
                <svg style={{width:20,height:20,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Documents List (Table View) */}
        {filteredDocuments.length > 0 ? (
          <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",overflow:"hidden"}}>
            <div style={{overflowX:"auto"}}>
              <table style={{minWidth:"100%",borderTop:"1px solid #e5e7eb",borderColor:"#e5e7eb"}}>
                <thead style={{backgroundColor:"#f9fafb"}}>
                  <tr>
                    <th scope="col" className="text-left text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                      Document
                    </th>
                    <th scope="col" className="text-left text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                      Type
                    </th>
                    <th scope="col" className="text-left text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                      Size
                    </th>
                    <th scope="col" className="text-left text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                      Uploaded
                    </th>
                    <th scope="col" className="text-left text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                      Status
                    </th>
                    <th scope="col" className="text-left text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody style={{backgroundColor:"#fff",borderTop:"1px solid #e5e7eb",borderColor:"#e5e7eb"}}>
                  {filteredDocuments.map((doc) => (
                    <tr key={doc.path || doc.storage_path || doc.title} style={{}}>
                      <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap"}}>
                        <div className="fb-d-flex fb-align-center">
                          <div style={{fontSize:"1.5rem",lineHeight:"2rem",marginRight:16}}>
                            {getFileIcon(doc.file_type)}
                          </div>
                          <div>
                            <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#111827",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:320}}>
                              {doc.title || doc.original_filename}
                            </div>
                            <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                              {doc.description || 'No description'}
                            </div>
                            {/* AI分类信息 */}
                            {aiEnabled && doc.ai_category && (
                              <div style={{marginTop:4}}>
                                <span style={{display:"inline-block",paddingLeft:8,paddingRight:8,paddingTop:4,paddingBottom:4,borderRadius:4,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...getAICategoryStyle(doc.ai_category)}}>
                                  {getAICategoryText(doc.ai_category)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                        {doc.file_type}
                      </td>
                      <td className="text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="text-muted" style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                        {formatDate(doc.created_at)}
                      </td>
                      <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap"}}>
                        <span style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,borderRadius:9999,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...(doc.folder_path ? {backgroundColor:'#dcfce7',color:'#166534'} : {backgroundColor:'#f3f4f6',color:'#1f2937'})}}>
                          {doc.folder_path ? 'In Folder' : 'Uncategorized'}
                        </span>
                        {getClassificationStatusBadge(doc.classification_status, doc.ai_confidence)}
                      </td>
                      <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500}}>
                        <div className="fb-d-flex" style={{display:"flex",gap:8}}>
                          <Link
                            to={`/documents/${(doc.path || doc.storage_path || doc.id).replace(/^\//, '')}`}
                            style={{color:"#1e3a5f"}}
                            title="View Details"
                          >
                            View
                          </Link>
                          <button
                            onClick={() => handleDelete(doc.path)}
                            style={{color:"#dc2626"}}
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
          <div className="text-center" style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:48}}>
            <div style={{fontSize:"3.75rem",lineHeight:1,marginBottom:24}}>📄</div>
            <h3 style={{fontSize:"1.5rem",lineHeight:"2rem",fontWeight:700,color:"#1f2937",marginBottom:16}}>
              {searchTerm 
                ? 'No matching documents found' 
                : 'No documents in this folder'}
            </h3>
            <p className="text-muted" style={{marginBottom:32,maxWidth:448,marginLeft:"auto",marginRight:"auto"}}>
              {searchTerm
                ? 'Try adjusting your search terms to find what you\'re looking for.'
                : 'Upload documents to this folder to start organizing them.'}
            </p>
            <Link
              to="/upload"
              style={{display:"inline-block",backgroundColor:"#2563eb",color:"#fff",paddingLeft:32,paddingRight:32,paddingTop:12,paddingBottom:12,borderRadius:8,fontWeight:500}}
            >
              Upload Documents
            </Link>
          </div>
        )}

        {/* Footer Stats */}
        <div className="text-center text-muted" style={{marginTop:32}}>
          <p>
            Showing {filteredDocuments.length} of {documents.length} documents in this folder
            {aiEnabled && ' • AI classification enabled'}
          </p>
          {folder && (
            <p style={{marginTop:8,fontSize:"0.875rem",lineHeight:"1.25rem"}}>
              Folder: <span style={{fontWeight:500}}>{folder.name}</span>
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