import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  AppBar,
  Toolbar,
  IconButton
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import apiClient from '../services/api';

interface Document {
  id: string;
  original_filename: string;
  path: string;
  file_type: string;
  mime_type: string;
  file_size: number;
  title?: string;
  document_metadata?: Record<string, any>;
}

const PathDocumentView: React.FC = () => {
  // 从URL通配符获取完整路径: /boarding/canadasite/en/...
  const { '*': wildcardPath = '' } = useParams<{ '*': string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 构建完整路径
  const fullPath = `/boarding/${wildcardPath}`;

  // 获取文档
  useEffect(() => {
    const fetchDocument = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.get(
          `/api/v1/documents/by-path-detail/${encodeURIComponent(fullPath)}`
        );
        setDocument(response.data as Document);
      } catch (err: any) {
        console.error('PathDocumentView: 获取文档失败:', err);
        if (err.response?.status === 404) {
          setError(`文档不存在: ${fullPath}`);
        } else {
          setError(`加载失败: ${err.message || '未知错误'}`);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [fullPath]);

  // 获取文档标识符（优先path）
  const getDocIdent = () => {
    if (!document) return '';
    return encodeURIComponent(document.path || document.storage_path || document.id);
  };

  // 获取预览URL（HTML文档）
  const getPreviewUrl = (): string | null => {
    if (!document || document.file_type !== 'HTML') return null;
    const token = localStorage.getItem('access_token');
    const encoded = getDocIdent();
    if (token) {
      return `/api/v1/documents/${encoded}/preview/html?token=${encodeURIComponent(token)}`;
    }
    return `/api/v1/documents/${encoded}/preview/html`;
  };

  // 下载文档
  const handleDownload = () => {
    if (!document) return;
    const token = localStorage.getItem('access_token');
    const encoded = getDocIdent();
    const url = token
      ? `/api/v1/documents/${encoded}/download?token=${encodeURIComponent(token)}`
      : `/api/v1/documents/${encoded}/download`;
    window.open(url, '_blank');
  };

  // 返回
  const handleBack = () => {
    navigate(-1);
  };

  // 加载中
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
        <Typography ml={2}>加载文档...</Typography>
      </Box>
    );
  }

  // 错误
  if (error || !document) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>
          返回
        </Button>
        <Alert severity="error">{error || '文档不存在'}</Alert>
      </Container>
    );
  }

  // 是否是HTML
  const isHtml = document.file_type === 'HTML';

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部工具栏 */}
      <AppBar position="sticky" color="default" elevation={1}>
        <Toolbar variant="dense">
          <IconButton edge="start" onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="subtitle1" noWrap sx={{ flexGrow: 1 }}>
            {document.title || document.original_filename}
          </Typography>
          <Button
            size="small"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            sx={{ mr: 1 }}
          >
            下载
          </Button>
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={() => window.location.reload()}
          >
            刷新
          </Button>
        </Toolbar>
      </AppBar>

      {/* 文档路径 */}
      <Box sx={{ px: 3, py: 1, bgcolor: 'grey.50', borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary">
          {document.path}
        </Typography>
      </Box>

      {/* 文档内容区域 */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {isHtml ? (
          <iframe
            src={getPreviewUrl() || ''}
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
            style={{
              width: '100%',
              flexGrow: 1,
              border: 'none',
            }}
            title="Document Preview"
          />
        ) : (
          <Box display="flex" justifyContent="center" alignItems="center" flexGrow={1}>
            <Alert severity="info">
              此文件类型 ({document.file_type}) 暂不支持直接预览。
              <Button size="small" onClick={handleDownload} sx={{ ml: 1 }}>
                下载查看
              </Button>
            </Alert>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default PathDocumentView;
