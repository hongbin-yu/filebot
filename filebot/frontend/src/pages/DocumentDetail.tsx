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

const DocumentDetail: React.FC = () => {
  console.log('=== DocumentDetail component starts rendering ===');
  const navigate = useNavigate();
  
  // 从URL获取标识符（支持UUID和路径）
  const splat = useParams()['*'] || '';
  const identifier = splat.startsWith('/') ? splat : '/' + splat;
  console.log('DocumentDetail: identifier from URL:', identifier);
  
  // 判断是否为UUID
  const uuidPattern = /^\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
  const isUuid = uuidPattern.test(identifier);
  const urlDocIdentifier = isUuid ? identifier.slice(1) : identifier; // UUID去掉前面加的/
  console.log('DocumentDetail: 最终标识符:', urlDocIdentifier, '类型:', isUuid ? 'UUID' : '路径');
  
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
  // 文档标识符：优先path，回退到UUID（用于后续API操作）
  const docApiIdentifier = document?.path || document?.storage_path || document?.id || '';
  
  const isImageFile = document?.file_type?.toLowerCase().match(/(tiff|tif|jpeg|jpg|png|bmp|gif)/) !== null;
  const isPdfFile = document?.file_type?.toLowerCase() === 'pdf';
  const isTiffFile = document?.file_type?.toLowerCase().match(/(tiff|tif)/) !== null;
  const isHtmlFile = document ? /html|htm/i.test(document.file_type || '') : false;
  const isPreviewableFile = isImageFile || isHtmlFile; // File types that can be previewed

  useEffect(() => {
    console.log('DocumentDetail: useEffect触发，标识符:', urlDocIdentifier);
    
    const fetchDocument = async () => {
      if (!urlDocIdentifier) {
        console.error('DocumentDetail: 标识符为空');
        setError('Document identifier is invalid or empty.');
        setLoading(false);
        return;
      }
      
      try {
        console.log('DocumentDetail: 获取文档:', urlDocIdentifier);
        setLoading(true);
        const data = await documentService.getDocumentByIdentifier(urlDocIdentifier);
        console.log('DocumentDetail: 获取文档成功:', { 
          path: data.path, 
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
          // 优先使用路径获取文件夹，避免UUID调用
          const folderIdentifier = data.folder_path || data.folder_id;
          if (folderIdentifier) {
            console.log('DocumentDetail: 获取文件夹信息，使用:', folderIdentifier);
            const folderData = await folderService.getFolder(folderIdentifier);
            console.log('DocumentDetail: 获取文件夹成功:', { path: folderData.path, name: folderData.name, app_id: folderData.app_id });
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
        setError(err.message || 'Failed to load document details');
      } finally {
        console.log('DocumentDetail: fetchDocument完成，设置loading=false');
        setLoading(false);
      }
    };

    console.log('DocumentDetail: 立即调用fetchDocument');
    fetchDocument();
  }, [urlDocIdentifier]);

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
        documentPath: document.path,
        currentStatus,
        newStatus
      });
      
      // 调用API更新发布状态
      const updatedDocument = await documentService.updateDocument(docApiIdentifier, {
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
      const blob = await documentService.downloadDocument(docApiIdentifier, downloadType);
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
    if (!document) return;
    const docPathStr = document.storage_path || document.path || '';
    const docPathInfo = docPathStr ? `\n存储路径: ${docPathStr}` : '';
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete document "${document.original_filename}"?${docPathInfo}`);
    if (!confirmed) {
      return;
    }
    
    try {
      await documentService.deleteDocument(docApiIdentifier);
      navigate('/documents', { state: { message: 'Document deleted successfully' } });
    } catch (err: any) {
      setError('Delete failed: ' + err.message);
    }
  };

  const handleExtractPages = () => {
    if (!document) return;
    // TODO: 实现页面提取功能
    window.showWetAlert('Page extraction feature is under development...');
  };

  // 处理HTML预览内容加载 - 使用后端preview/html端点（同源，/etc/designs等资源正常加载）
  useEffect(() => {
    if (!document || !isHtmlFile || activeTab !== 'preview') {
      return;
    }

    console.log('DocumentDetail: 设置HTML预览加载，文档路径:', document.path);
    setPreviewLoading(true);
    
    // 使用后端预览API URL（inline content-disposition，同源iframe可正常加载/etc/designs/canada/wet-boew/等资源）
    // 将token通过query参数传递，因为iframe无法设置Authorization header
    const token = localStorage.getItem('access_token');
    const encodedDocId = encodeURIComponent(docApiIdentifier);
    const apiUrl = token
      ? `/api/v1/documents/${encodedDocId}/preview/html?token=${encodeURIComponent(token)}`
      : `/api/v1/documents/${encodedDocId}/preview/html`;
    setHtmlContentUrl(apiUrl);
    
    // 简短延迟后移除loading状态
    const timer = setTimeout(() => {
      setPreviewLoading(false);
    }, 3000);
    
    return () => {
      clearTimeout(timer);
    };
  }, [document?.path, activeTab]);

  // Handle image preview content loading
  useEffect(() => {
    console.log('DocumentDetail: Image preview useEffect triggered', {
      documentPath: document?.path,
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
        documentPath: document?.path,
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

      console.log('DocumentDetail: Starting to load image preview content, document path:', document.path);
      
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
        console.log('DocumentDetail: Using blob scheme to load image');
        const blob = await documentService.downloadDocument(docApiIdentifier, 'original');
        
        // 检查文件是否为空
        if (blob.size === 0) {
          console.warn('DocumentDetail: Image file size is 0, may be empty file');
          // 设置错误信息
          setImagePreviewError('Image file is empty or corrupted');
        } else {
          // 检查Blob类型
          console.log('DocumentDetail: Downloaded image blob info:', {
            size: blob.size,
            type: blob.type,
          });
          
          // 创建Blob URL
          const url = URL.createObjectURL(blob);
          currentBlobUrl = url;
          setImagePreviewUrl(url);
          console.log('DocumentDetail: Image preview content loaded successfully, blob size:', blob.size, 'blob type:', blob.type, 'blob URL:', url);
        }
      } catch (error: any) {
        console.error('DocumentDetail: Failed to load image preview content:', error);
        // 设置错误信息
        setImagePreviewError(`Failed to load image preview: ${error.message || 'Unknown error'}`);
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
    console.log('DocumentDetail: 显示加载状态, identifier:', urlDocIdentifier);
    console.log('DocumentDetail: 当前URL:', window.location.href);
    console.log('DocumentDetail: 完整路由信息:', window.location);
    
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center', flexDirection: 'column', alignItems: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading document details...</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          identifier: {urlDocIdentifier || 'None'}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          Current URL: {window.location.pathname}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          If stuck on this page for a long time, press F12 to view console logs
        </Typography>
      </Container>
    );
  }

  if (error || !document) {
    console.log('DocumentDetail: 显示错误状态，error:', error, 'document:', document);
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || 'Document does not exist'}
          <Typography variant="body2" sx={{ mt: 1 }}>
            identifier: {urlDocIdentifier || 'None'}
          </Typography>
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack}>
          Back to Documents
        </Button>
      </Container>
    );
  }



  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Breadcrumb navigation */}
      <Breadcrumbs sx={{ mb: 3 }}>
        {app && folder ? (
          [
            <MuiLink 
              key="app-manage"
              color="inherit" 
              onClick={() => navigate('/admin/apps')} 
              sx={{ cursor: 'pointer' }}
            >
              App Management
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
              onClick={() => navigate(`/admin/apps/${app.slug || app.id}/folders/${encodeURIComponent(folder.path)}/documents`)} 
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
              Documents
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
              Documents
            </MuiLink>,
            <Typography key="filename-default" color="text.primary">{document.original_filename}</Typography>
          ]
        )}
      </Breadcrumbs>
      {/* Title and action buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {document.original_filename}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip 
              label={document.file_type?.toUpperCase() || 'Unknown Format'} 
              color="primary" 
              size="small" 
            />
            <Chip 
              label={formatFileSize(document.file_size)} 
              variant="outlined" 
              size="small" 
            />
            <Chip 
              label={document.conversion_status === 'completed' ? 'Converted' : 'Not Converted'} 
              color={document.conversion_status === 'completed' ? 'success' : 'warning'}
              size="small"
            />
            <Tooltip title="Click to toggle publish status">
              <Chip 
                label={(document.publish_status || 'UNPUBLISHED') === 'PUBLISHED' ? 'Published' : 'Not Published'} 
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
            Back
          </Button>
          <Tooltip title="Download Original File">
            <IconButton onClick={() => handleDownload('original')}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          {isPdfFile && (
            <Tooltip title="Download PDF version">
              <IconButton onClick={() => handleDownload('pdf')}>
                <PdfIcon />
              </IconButton>
            </Tooltip>
          )}
          {isTiffFile && (
            <Tooltip title="Extract TIFF pages">
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
          <Tooltip title="Delete document">
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
              Document Info
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
                {isImageFile ? 'Image Preview' : 'HTML Preview'}
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
                Page Management
              </Button>
            )}
          </Box>
        </Box>
      </Paper>
      {/* Tab content */}
      {activeTab === 'info' && (
        <Paper sx={{ p: 3 }}>
          <Grid container spacing={3}>
            <Grid
              size={{
                xs: 12,
                md: 6
              }}>
              <Typography variant="h6" gutterBottom>Basic Information</Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">File Name</Typography>
                <Typography variant="body1">{document.original_filename}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">File Type</Typography>
                <Typography variant="body1">{document.file_type?.toUpperCase() || 'Unknown'}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">File Size</Typography>
                <Typography variant="body1">{formatFileSize(document.file_size)}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Page Count</Typography>
                <Typography variant="body1">{document.page_count || 'Unknown'}</Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Upload Time</Typography>
                <Typography variant="body1">{formatDate(document.created_at)}</Typography>
              </Box>
            </Grid>
            
            <Grid
              size={{
                xs: 12,
                md: 6
              }}>
              <Typography variant="h6" gutterBottom>Document Properties</Typography>
              <Divider sx={{ mb: 2 }} />
              
              {document.title && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Title</Typography>
                  <Typography variant="body1">{document.title}</Typography>
                </Box>
              )}
              
              {document.description && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Description</Typography>
                  <Typography variant="body1">{document.description}</Typography>
                </Box>
              )}
              
              {document.document_number && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Document Number</Typography>
                  <Typography variant="body1">{document.document_number}</Typography>
                </Box>
              )}
              
              {/* Path Solution - Display document path information */}
              {(document.storage_path || document.path || document.parent_folder_path) && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Path Information</Typography>
                  <Box sx={{ mt: 1 }}>
                    {document.storage_path && (
                      <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">Storage Path:</Typography>
                        <Typography variant="body2">{document.storage_path}</Typography>
                      </Box>
                    )}
                    {document.path && (
                      <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">URL Path:</Typography>
                        <Typography variant="body2">{document.path}</Typography>
                      </Box>
                    )}
                    {document.parent_folder_path && (
                      <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">Parent Folder Path:</Typography>
                        <Typography variant="body2">{document.parent_folder_path}</Typography>
                      </Box>
                    )}
                  </Box>
                </Box>
              )}
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Conversion Status</Typography>
                <Chip 
                  label={document.conversion_status === 'completed' ? 'Completed' : 'In Progress'} 
                  color={document.conversion_status === 'completed' ? 'success' : 'warning'}
                  size="small"
                />
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Document Status</Typography>
                <Chip 
                  label={document.status === 'active' ? 'Active' : 'Archived'} 
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
            {isImageFile ? 'Image Preview' : 'HTML Preview'}
          </Typography>
          <Divider sx={{ mb: 3 }} />
          
          {isImageFile ? (
            <>
              {isTiffFile ? (
                <TiffPreview documentId={docApiIdentifier} />
              ) : (
                <Box sx={{ textAlign: 'center', p: 4 }}>
                  {imagePreviewLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
                      <CircularProgress />
                      <Typography sx={{ ml: 2 }}>Loading image...</Typography>
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
                          Download Image
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
                        <Typography>Image will load automatically when clicking the "Image Preview" tab</Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          If the image does not load automatically, ensure the file exists and has content.
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
                    <Typography sx={{ mt: 2 }}>Loading HTML content...</Typography>
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
                      Download HTML file
                    </Button>
                  </Box>
                </>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Alert severity="info">
                    <Typography>Content will load automatically when clicking the "HTML Preview" tab</Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      If content does not load automatically, ensure the file exists and has content.
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
          <Typography variant="h6" gutterBottom>Page Management</Typography>
          <Divider sx={{ mb: 3 }} />
          
          <Alert severity="info" sx={{ mb: 3 }}>
            {isTiffFile 
              ? 'TIFF page management feature is under development, will support page extraction, preview, and download.'
              : 'PDF page management feature is under development, will support page preview, renaming, and reordering.'
            }
          </Alert>
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button 
              variant="contained" 
              startIcon={<ImageIcon />}
              onClick={handleExtractPages}
              disabled={!isTiffFile}
            >
              Extract TIFF Pages
            </Button>
            <Button 
              variant="outlined" 
              startIcon={<PdfIcon />}
              disabled={!isPdfFile}
            >
              Export as PDF
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