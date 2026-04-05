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
  Link,
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
import TiffPreview from '../components/TiffPreview';

const DocumentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'info' | 'preview' | 'pages'>('info');

  useEffect(() => {
    const fetchDocument = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        const data = await documentService.getDocumentById(id);
        setDocument(data);
        setError(null);
        
        // 如果是图像文件，默认显示预览标签页
        if (data.file_type?.toLowerCase().match(/(tiff|tif|jpeg|jpg|png|bmp|gif)/)) {
          setActiveTab('preview');
        }
      } catch (err: any) {
        setError(err.message || '加载文档详情失败');
        console.error('Error fetching document:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [id]);

  const handleBack = () => {
    navigate(-1);
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

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error || !document) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || '文档不存在'}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack}>
          返回文档列表
        </Button>
      </Container>
    );
  }

  const isImageFile = document.file_type?.toLowerCase().match(/(tiff|tif|jpeg|jpg|png|bmp|gif)/);
  const isPdfFile = document.file_type?.toLowerCase() === 'pdf';
  const isTiffFile = document.file_type?.toLowerCase().match(/(tiff|tif)/);

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* 面包屑导航 */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link 
          color="inherit" 
          onClick={() => navigate('/documents')} 
          sx={{ cursor: 'pointer' }}
        >
          文档列表
        </Link>
        <Typography color="text.primary">{document.original_filename}</Typography>
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
              onClick={() => setActiveTab('info')}
            >
              文档信息
            </Button>
            {isImageFile && (
              <Button
                sx={{ 
                  px: 3, 
                  py: 2, 
                  borderRadius: 0,
                  borderBottom: activeTab === 'preview' ? 2 : 0,
                  borderColor: 'primary.main'
                }}
                onClick={() => setActiveTab('preview')}
              >
                图像预览
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
                onClick={() => setActiveTab('pages')}
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
            <Grid item xs={12} md={6}>
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
            
            <Grid item xs={12} md={6}>
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

      {activeTab === 'preview' && isImageFile && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>图像预览</Typography>
          <Divider sx={{ mb: 3 }} />
          
          {isTiffFile ? (
            <TiffPreview documentId={document.id} />
          ) : (
            <Box sx={{ textAlign: 'center', p: 4 }}>
              <img 
                src={`/api/v1/documents/${document.id}/download?download_type=original`}
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
            </Box>
          )}
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