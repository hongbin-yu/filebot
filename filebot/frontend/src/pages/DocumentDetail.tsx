import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Container, 
  Paper, 
  Typography, 
  Box, 
  Button, 
  Grid, 
  Chip,
  Divider,
  CircularProgress,
  Alert,
  Breadcrumbs,
  Link as MuiLink,
  IconButton,
  Tooltip
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon
} from '@mui/icons-material';
import documentService, { Document } from '../services/document.service';
import folderService, { Folder } from '../services/folder.service';
import appService, { App } from '../services/app.service';
import TiffPreview from '../components/TiffPreview';
import { extractIdFromSlug } from '../utils/slugUtils';

const DocumentDetail: React.FC = () => {
  console.log('=== DocumentDetail组件开始渲染 ===');
  const { id: idParam } = useParams<{ id: string }>();
  console.log('DocumentDetail: useParams返回的idParam:', idParam);
  const navigate = useNavigate();
  
  // Parse document ID from possible slug format
  const parseDocumentId = (param: string | undefined): string => {
    console.log('DocumentDetail: parseDocumentId输入:', param);
    
    if (!param) {
      console.log('DocumentDetail: 参数为空，返回空字符串');
      return '';
    }
    
    // 如果是UUID格式（xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx），直接返回
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const match = param.match(uuidPattern);
    if (match) {
      console.log('DocumentDetail: 匹配到UUID格式，返回:', match[0]);
      return match[0];
    }
    
    // 如果参数包含'-'但不是标准UUID，尝试提取第一部分
    if (param.includes('-')) {
      const parts = param.split('-');
      const possibleUuid = parts[0];
      console.log('DocumentDetail: 参数包含"-"，提取第一部分:', possibleUuid);
      return possibleUuid;
    }
    
    console.log('DocumentDetail: 返回原始参数:', param);
    return param;
  };

  const id = parseDocumentId(idParam);
  console.log('DocumentDetail: 最终id:', id, '类型:', typeof id);
  
  const [document, setDocument] = useState<Document | null>(null);
  const [folder, setFolder] = useState<Folder | null>(null);
  const [app, setApp] = useState<App | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'info' | 'preview' | 'pages'>('info');
  const [htmlContentUrl, setHtmlContentUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [imagePreviewLoading, setImagePreviewLoading] = useState(false);
  const [imagePreviewError, setImagePreviewError] = useState<string | null>(null);

  // 根据文档类型计算布尔值（支持document为null的情况）
  const isImageFile = document?.file_type?.toLowerCase().match(/(tiff|tif|jpeg|jpg|png|bmp|gif)/) !== null;
  const isPdfFile = document?.file_type?.toLowerCase() === 'pdf';
  const isTiffFile = document?.file_type?.toLowerCase().match(/(tiff|tif)/) !== null;
  const isHtmlFile = document ? /html|htm/i.test(document.file_type || '') : false;
  const isPreviewableFile = isImageFile || isHtmlFile; // 可以预览的文件类型

  useEffect(() => {
    console.log('DocumentDetail: useEffect触发，依赖项[id]变化:', id);
    console.log('DocumentDetail: useParams的idParam:', idParam);
    console.log('DocumentDetail: 当前loading状态:', loading);
    
    const fetchDocument = async () => {
      console.log('DocumentDetail: fetchDocument开始执行');
      console.log('DocumentDetail: 检查id是否为空，id值为:', id);
      
      if (!id) {
        console.error('DocumentDetail: ID为空，无法获取文档');
        console.error('DocumentDetail: 设置错误状态和loading=false');
        setError('文档ID无效或为空。请检查URL是否正确。');
        setLoading(false);
        return;
      }
      
      try {
        console.log('DocumentDetail: 调用documentService.getDocumentById，ID:', id);
        console.log('DocumentDetail: 当前API基础URL:', documentService);
        setLoading(true);
        const data = await documentService.getDocumentById(id);
        console.log('DocumentDetail: 获取文档成功:', { 
          id: data.id, 
          filename: data.original_filename,
          type: data.file_type,
          size: data.file_size,
          folder_id: data.folder_id
        });
        setDocument(data);
        setError(null);
        
        // 如果是图像文件，默认显示预览标签页
        if (data.file_type?.toLowerCase().match(/(tiff|tif|jpeg|jpg|png|bmp|gif)/)) {
          setActiveTab('preview');
        }
        
        // 获取文件夹和应用信息以构建导航路径
        try {
          if (data.folder_id) {
            console.log('DocumentDetail: 获取文件夹信息，folder_id:', data.folder_id);
            const folderData = await folderService.getFolderById(data.folder_id);
            console.log('DocumentDetail: 获取文件夹成功:', { id: folderData.id, name: folderData.name, app_id: folderData.app_id });
            setFolder(folderData);
            
            // 获取应用信息
            if (folderData.app_id) {
              console.log('DocumentDetail: 获取应用信息，app_id:', folderData.app_id);
              const apps = await appService.getApps();
              const appData = apps.find(app => app.id === folderData.app_id || app.slug === folderData.app_id);
              if (appData) {
                console.log('DocumentDetail: 获取应用成功:', { id: appData.id, name: appData.name, slug: appData.slug });
                setApp(appData);
              } else {
                console.warn('DocumentDetail: 未找到对应的应用，app_id:', folderData.app_id);
              }
            }
          }
        } catch (folderErr: any) {
          console.warn('DocumentDetail: 获取文件夹或应用信息失败，但不影响主要功能:', folderErr);
          // 不设置错误状态，因为主要文档信息已加载
        }
      } catch (err: any) {
        console.error('DocumentDetail: 获取文档失败:', err);
        console.error('DocumentDetail: 错误状态码:', err.response?.status);
        console.error('DocumentDetail: 错误响应数据:', err.response?.data);
        console.error('DocumentDetail: 错误消息:', err.message);
        setError(err.message || '加载文档详情失败');
      } finally {
        console.log('DocumentDetail: fetchDocument完成，设置loading=false');
        setLoading(false);
      }
    };

    console.log('DocumentDetail: 立即调用fetchDocument');
    fetchDocument();
  }, [id]);

  const handleBack = () => {
    navigate(-1);
  };

  // 切换文档发布状态
  const handleTogglePublishStatus = async () => {
    if (!document) return;
    
    try {
      const currentStatus = document.publish_status || 'UNPUBLISHED';
      const newStatus = currentStatus === 'PUBLISHED' ? 'UNPUBLISHED' : 'PUBLISHED';
      
      console.log('切换发布状态:', {
        documentId: document.id,
        currentStatus,
        newStatus
      });
      
      // 调用API更新发布状态
      const updatedDocument = await documentService.updateDocument(document.id, {
        publish_status: newStatus
      });
      
      // 更新本地状态
      setDocument(updatedDocument);
      
      // 显示成功消息（可以替换为更优雅的通知）
      setError(null); // 清除任何现有错误
      console.log('发布状态更新成功:', updatedDocument.publish_status);
      
    } catch (err: any) {
      console.error('切换发布状态失败:', err);
      setError('更新发布状态失败: ' + err.message);
    }
  };

  const handleDownload = async (downloadType: 'original' | 'pdf' = 'original') => {
    if (!document) return;
    
    try {
      const blob = await documentService.downloadDocument(document.id, downloadType);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = `${document.original_filename}${downloadType === 'pdf' ? '.pdf' : ''}`;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (err: any) {
      console.error('Download failed:', err);
      setError('下载失败: ' + err.message);
    }
  };

  const handleDelete = async () => {
    if (!document || !window.confirm(`确定要删除文档 "${document.original_filename}" 吗？`)) {
      return;
    }
    
    try {
      await documentService.deleteDocument(document.id);
      navigate('/documents', { state: { message: '文档删除成功' } });
    } catch (err: any) {
      setError('删除失败: ' + err.message);
    }
  };

  const handleExtractPages = () => {
    if (!document) return;
    // TODO: 实现页面提取功能
    alert('页面提取功能开发中...');
  };

  // 处理HTML预览内容加载
  useEffect(() => {
    // 使用ref来跟踪当前的Blob URL，避免依赖循环
    let currentBlobUrl: string | null = null;
    
    const loadHtmlContent = async () => {
      if (!document || !isHtmlFile || activeTab !== 'preview') {
        return;
      }

      console.log('DocumentDetail: 开始加载HTML预览内容，文档ID:', document.id);
      
      // 如果已经有内容URL，先释放
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
        currentBlobUrl = null;
      }
      
      // 也清除状态中的URL
      if (htmlContentUrl) {
        setHtmlContentUrl(null);
      }

      setPreviewLoading(true);
      
      try {
        // 使用documentService下载文档内容（带认证）
        const blob = await documentService.downloadDocument(document.id, 'original');
        
        // 检查文件是否为空
        if (blob.size === 0) {
          console.warn('DocumentDetail: HTML文件大小为0，可能为空文件');
          // 创建空HTML的Blob
          const emptyHtml = '<html><body><h3>文件内容为空</h3><p>此HTML文件大小为0字节，可能是爬虫下载时出现问题。</p></body></html>';
          const emptyBlob = new Blob([emptyHtml], { type: 'text/html' });
          const url = URL.createObjectURL(emptyBlob);
          currentBlobUrl = url;
          setHtmlContentUrl(url);
        } else {
          // 检查Blob类型
          console.log('DocumentDetail: 下载的Blob信息:', {
            size: blob.size,
            type: blob.type,
            slice: blob.slice(0, 100).text ? '(可读取)' : '(不可直接读取)'
          });
          
          // 创建Blob URL
          const url = URL.createObjectURL(blob);
          currentBlobUrl = url;
          setHtmlContentUrl(url);
          console.log('DocumentDetail: HTML预览内容加载成功，Blob大小:', blob.size, 'Blob类型:', blob.type, 'Blob URL:', url);
        }
      } catch (error: any) {
        console.error('DocumentDetail: 加载HTML预览内容失败:', error);
        // 创建错误信息的HTML
        const errorHtml = `<html><body>
          <h3 style="color: #d32f2f;">加载HTML预览失败</h3>
          <p>错误信息: ${error.message || '未知错误'}</p>
          <p>请检查网络连接或文件是否损坏。</p>
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

    // 清理函数：组件卸载或依赖变化时释放Blob URL
    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [document, isHtmlFile, activeTab]);

  // 处理图片预览内容加载
  useEffect(() => {
    console.log('DocumentDetail: 图片预览useEffect触发', {
      documentId: document?.id,
      documentFileType: document?.file_type,
      isImageFile,
      isTiffFile,
      activeTab,
      hasDocument: !!document,
    });
    
    // 使用ref来跟踪当前的Blob URL，避免依赖循环
    let currentBlobUrl: string | null = null;
    
    const loadImageContent = async () => {
      console.log('DocumentDetail: loadImageContent调用', {
        documentId: document?.id,
        isImageFile,
        isTiffFile,
        activeTab,
      });
      
      if (!document || !isImageFile || isTiffFile || activeTab !== 'preview') {
        console.log('DocumentDetail: loadImageContent跳过，条件不满足:', {
          hasDocument: !!document,
          isImageFile,
          isTiffFile,
          activeTab,
        });
        return;
      }

      console.log('DocumentDetail: 开始加载图片预览内容，文档ID:', document.id);
      
      // 如果已经有内容URL，先释放
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
        currentBlobUrl = null;
      }
      
      // 清除状态中的URL和错误
      setImagePreviewUrl(null);
      setImagePreviewError(null);

      setImagePreviewLoading(true);
      
      try {
        // 检查文档是否有原始URL（来自网站爬虫）
        const hasOriginalUrl = document.metadata?.url || document.document_metadata?.url;
        const originalUrl = document.metadata?.url || document.document_metadata?.url;
        
        if (hasOriginalUrl && originalUrl) {
          // 从原始URL提取路径部分
          console.log('DocumentDetail: 文档有原始URL:', originalUrl);
          
          try {
            // 解析URL，获取路径部分
            const urlObj = new URL(originalUrl);
            const path = urlObj.pathname;
            
            if (path) {
              // 构建预览URL：如果路径以/content开头，直接使用；否则添加/content前缀
              let previewUrl;
              if (path.startsWith('/content/')) {
                // 路径已经是/content/...，直接使用
                previewUrl = path;
              } else {
                // 添加/content前缀
                previewUrl = `/content${path}`;
              }
              
              console.log('DocumentDetail: 使用路径映射URL:', previewUrl, '(原始路径:', path, ')');
              setImagePreviewUrl(previewUrl);
              
              // 不需要创建Blob URL，所以直接完成加载
              setImagePreviewLoading(false);
              return;
            }
          } catch (urlError) {
            console.warn('DocumentDetail: 解析原始URL失败，回退到Blob方案:', urlError);
          }
        }
        
        // 如果没有原始URL或解析失败，使用原有的Blob方案
        console.log('DocumentDetail: 使用Blob方案加载图片');
        const blob = await documentService.downloadDocument(document.id, 'original');
        
        // 检查文件是否为空
        if (blob.size === 0) {
          console.warn('DocumentDetail: 图片文件大小为0，可能为空文件');
          // 设置错误信息
          setImagePreviewError('图片文件为空或损坏');
        } else {
          // 检查Blob类型
          console.log('DocumentDetail: 下载的图片Blob信息:', {
            size: blob.size,
            type: blob.type,
          });
          
          // 创建Blob URL
          const url = URL.createObjectURL(blob);
          currentBlobUrl = url;
          setImagePreviewUrl(url);
          console.log('DocumentDetail: 图片预览内容加载成功，Blob大小:', blob.size, 'Blob类型:', blob.type, 'Blob URL:', url);
        }
      } catch (error: any) {
        console.error('DocumentDetail: 加载图片预览内容失败:', error);
        // 设置错误信息
        setImagePreviewError(`加载图片预览失败: ${error.message || '未知错误'}`);
      } finally {
        setImagePreviewLoading(false);
      }
    };

    loadImageContent();

    // 清理函数：组件卸载或依赖变化时释放Blob URL
    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [document, isImageFile, isTiffFile, activeTab]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  if (loading) {
    console.log('DocumentDetail: 显示加载状态，id:', id, 'idParam:', idParam);
    console.log('DocumentDetail: 当前URL:', window.location.href);
    console.log('DocumentDetail: 完整路由信息:', window.location);
    
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center', flexDirection: 'column', alignItems: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>正在加载文档详情...</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          ID: {id || '无'} | 参数: {idParam || '无'}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          当前URL: {window.location.pathname}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          如果长时间停留在此页面，请按F12查看控制台日志
        </Typography>
      </Container>
    );
  }

  if (error || !document) {
    console.log('DocumentDetail: 显示错误状态，error:', error, 'document:', document);
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || '文档不存在'}
          <Typography variant="body2" sx={{ mt: 1 }}>
            ID: {id || '无'} | 参数: {idParam || '无'}
          </Typography>
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack}>
          返回文档列表
        </Button>
      </Container>
    );
  }



  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* 面包屑导航 */}
      <Breadcrumbs sx={{ mb: 3 }}>
        {app && folder ? (
          [
            <MuiLink 
              key="app-manage"
              color="inherit" 
              onClick={() => navigate('/admin/apps')} 
              sx={{ cursor: 'pointer' }}
            >
              应用管理
            </MuiLink>,
            <MuiLink 
              key="app"
              color="inherit" 
              onClick={() => navigate(`/admin/apps/${app.slug || app.id}`)} 
              sx={{ cursor: 'pointer' }}
            >
              {app.name}
            </MuiLink>,
            <MuiLink 
              key="folder"
              color="inherit" 
              onClick={() => navigate(`/admin/apps/${app.slug || app.id}/folders/${folder.id}/documents`)} 
              sx={{ cursor: 'pointer' }}
            >
              {folder.name}
            </MuiLink>,
            <Typography key="filename" color="text.primary">{document.original_filename}</Typography>
          ]
        ) : folder ? (
          [
            <MuiLink 
              key="doc-list"
              color="inherit" 
              onClick={() => navigate('/documents')} 
              sx={{ cursor: 'pointer' }}
            >
              文档列表
            </MuiLink>,
            <Typography key="folder-name" color="text.primary">{folder.name}</Typography>,
            <Typography key="filename-2" color="text.primary">{document.original_filename}</Typography>
          ]
        ) : (
          [
            <MuiLink 
              key="doc-list-default"
              color="inherit" 
              onClick={() => navigate('/documents')} 
              sx={{ cursor: 'pointer' }}
            >
              文档列表
            </MuiLink>,
            <Typography key="filename-default" color="text.primary">{document.original_filename}</Typography>
          ]
        )}
      </Breadcrumbs>
      {/* 标题和操作按钮 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {document.original_filename}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip 
              label={document.file_type?.toUpperCase() || '未知格式'} 
              color="primary" 
              size="small" 
            />
            <Chip 
              label={formatFileSize(document.file_size)} 
              variant="outlined" 
              size="small" 
            />
            <Chip 
              label={document.conversion_status === 'completed' ? '已转换' : '未转换'} 
              color={document.conversion_status === 'completed' ? 'success' : 'warning'}
              size="small"
            />
            <Tooltip title="点击切换发布状态">
              <Chip 
                label={(document.publish_status || 'UNPUBLISHED') === 'PUBLISHED' ? '已发布' : '未发布'} 
                color={(document.publish_status || 'UNPUBLISHED') === 'PUBLISHED' ? 'success' : 'default'}
                variant={(document.publish_status || 'UNPUBLISHED') === 'PUBLISHED' ? 'filled' : 'outlined'}
                size="small"
                onClick={handleTogglePublishStatus}
                sx={{ cursor: 'pointer' }}
              />
            </Tooltip>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            startIcon={<ArrowBackIcon />} 
            onClick={handleBack}
            variant="outlined"
          >
            返回
          </Button>
          <Tooltip title="下载原始文件">
            <IconButton onClick={() => handleDownload('original')}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          {isPdfFile && (
            <Tooltip title="下载PDF版本">
              <IconButton onClick={() => handleDownload('pdf')}>
                <PdfIcon />
              </IconButton>
            </Tooltip>
          )}
          {isTiffFile && (
            <Tooltip title="提取TIFF页面">
              <Button 
                startIcon={<ImageIcon />} 
                onClick={handleExtractPages}
                variant="contained"
                color="secondary"
              >
                提取页面
              </Button>
            </Tooltip>
          )}
          <Tooltip title="删除文档">
            <IconButton onClick={handleDelete} color="error">
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      {/* 标签页导航 */}
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex' }}>
            <Button
              sx={{ 
                px: 3, 
                py: 2, 
                borderRadius: 0,
                borderBottom: activeTab === 'info' ? 2 : 0,
                borderColor: 'primary.main'
              }}
              onClick={() => {
                console.log('DocumentDetail: 切换到info标签');
                setActiveTab('info');
              }}
            >
              文档信息
            </Button>
            {(isImageFile || isHtmlFile) && (
              <Button
                sx={{ 
                  px: 3, 
                  py: 2, 
                  borderRadius: 0,
                  borderBottom: activeTab === 'preview' ? 2 : 0,
                  borderColor: 'primary.main'
                }}
                onClick={() => {
                  console.log('DocumentDetail: 切换到preview标签，文件类型:', document?.file_type);
                  setActiveTab('preview');
                }}
              >
                {isImageFile ? '图像预览' : 'HTML预览'}
              </Button>
            )}
            {(isPdfFile || isTiffFile) && (
              <Button
                sx={{ 
                  px: 3, 
                  py: 2, 
                  borderRadius: 0,
                  borderBottom: activeTab === 'pages' ? 2 : 0,
                  borderColor: 'primary.main'
                }}
                onClick={() => {
                  console.log('DocumentDetail: 切换到pages标签');
                  setActiveTab('pages');
                }}
              >
                页面管理
              </Button>
            )}
          </Box>
        </Box>
      </Paper>
      {/* 标签页内容 */}
      {activeTab === 'info' && (
        <Paper sx={{ p: 3 }}>
          <Grid container spacing={3}>
            <Grid
              size={{
                xs: 12,
                md: 6
              }}>
              <Typography variant="h6" gutterBottom>基本信息</Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">文件名</Typography>
                <Typography variant="body1">{document.original_filename}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">文件类型</Typography>
                <Typography variant="body1">{document.file_type?.toUpperCase() || '未知'}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">文件大小</Typography>
                <Typography variant="body1">{formatFileSize(document.file_size)}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">页数</Typography>
                <Typography variant="body1">{document.page_count || '未知'}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">上传时间</Typography>
                <Typography variant="body1">{formatDate(document.created_at)}</Typography>
              </Box>
            </Grid>
            
            <Grid
              size={{
                xs: 12,
                md: 6
              }}>
              <Typography variant="h6" gutterBottom>文档属性</Typography>
              <Divider sx={{ mb: 2 }} />
              
              {document.title && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">标题</Typography>
                  <Typography variant="body1">{document.title}</Typography>
                </Box>
              )}
              
              {document.description && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">描述</Typography>
                  <Typography variant="body1">{document.description}</Typography>
                </Box>
              )}
              
              {document.document_number && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">文档编号</Typography>
                  <Typography variant="body1">{document.document_number}</Typography>
                </Box>
              )}
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">转换状态</Typography>
                <Chip 
                  label={document.conversion_status === 'completed' ? '已完成' : '进行中'} 
                  color={document.conversion_status === 'completed' ? 'success' : 'warning'}
                  size="small"
                />
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">文档状态</Typography>
                <Chip 
                  label={document.status === 'active' ? '活跃' : '已归档'} 
                  color={document.status === 'active' ? 'success' : 'default'}
                  size="small"
                />
              </Box>
            </Grid>
          </Grid>
        </Paper>
      )}
      {activeTab === 'preview' && (isImageFile || isHtmlFile) && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            {isImageFile ? '图像预览' : 'HTML预览'}
          </Typography>
          <Divider sx={{ mb: 3 }} />
          
          {isImageFile ? (
            <>
              {isTiffFile ? (
                <TiffPreview documentId={document.id} />
              ) : (
                <Box sx={{ textAlign: 'center', p: 4 }}>
                  {imagePreviewLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
                      <CircularProgress />
                      <Typography sx={{ ml: 2 }}>正在加载图片...</Typography>
                    </Box>
                  ) : imagePreviewUrl ? (
                    <>
                      <img 
                        src={imagePreviewUrl}
                        alt={document.original_filename}
                        style={{ maxWidth: '100%', maxHeight: '600px', objectFit: 'contain' }}
                      />
                      <Box sx={{ mt: 2 }}>
                        <Button 
                          variant="contained" 
                          startIcon={<DownloadIcon />}
                          onClick={() => handleDownload('original')}
                        >
                          下载图像
                        </Button>
                      </Box>
                    </>
                  ) : imagePreviewError ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
                      <Alert severity="error">
                        <Typography>{imagePreviewError}</Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          请尝试刷新页面或下载文件查看。
                        </Typography>
                      </Alert>
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
                      <Alert severity="info">
                        <Typography>点击"图像预览"标签页时自动加载图片</Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          如果图片未自动加载，请确保文件存在且有内容。
                        </Typography>
                      </Alert>
                    </Box>
                  )}
                </Box>
              )}
            </>
          ) : isHtmlFile ? (
            <Box sx={{ width: '100%', height: '600px', border: '1px solid #e0e0e0', borderRadius: 1 }}>
              {previewLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Box sx={{ textAlign: 'center' }}>
                    <CircularProgress />
                    <Typography sx={{ mt: 2 }}>正在加载HTML内容...</Typography>
                  </Box>
                </Box>
              ) : htmlContentUrl ? (
                <>
                  <iframe
                    src={htmlContentUrl}
                    title={document.original_filename}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                    onLoad={(e) => console.log('DocumentDetail: iframe加载完成', htmlContentUrl, e)}
                    onError={(e) => console.error('DocumentDetail: iframe加载错误', htmlContentUrl, e)}
                  />
                  <Box sx={{ mt: 2, textAlign: 'center' }}>
                    <Button 
                      variant="contained" 
                      startIcon={<DownloadIcon />}
                      onClick={() => handleDownload('original')}
                    >
                      下载HTML文件
                    </Button>
                  </Box>
                </>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Alert severity="info">
                    <Typography>点击"HTML预览"标签页时自动加载内容</Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      如果内容未自动加载，请确保文件存在且有内容。
                    </Typography>
                  </Alert>
                </Box>
              )}
            </Box>
          ) : null}
        </Paper>
      )}
      {activeTab === 'pages' && (isPdfFile || isTiffFile) && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>页面管理</Typography>
          <Divider sx={{ mb: 3 }} />
          
          <Alert severity="info" sx={{ mb: 3 }}>
            {isTiffFile 
              ? 'TIFF页面管理功能正在开发中，将支持页面提取、预览和下载。'
              : 'PDF页面管理功能正在开发中，将支持页面预览、重命名和重新排序。'
            }
          </Alert>
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button 
              variant="contained" 
              startIcon={<ImageIcon />}
              onClick={handleExtractPages}
              disabled={!isTiffFile}
            >
              提取TIFF页面
            </Button>
            <Button 
              variant="outlined" 
              startIcon={<PdfIcon />}
              disabled={!isPdfFile}
            >
              导出为PDF
            </Button>
          </Box>
        </Paper>
      )}
      {/* 错误提示 */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Container>
  );
};

export default DocumentDetail;