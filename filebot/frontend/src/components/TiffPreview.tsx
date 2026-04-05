import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Button,
  IconButton,
  CircularProgress,
  Alert,
  Slider,
  Chip,
  Divider,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  ToggleButton,
  ToggleButtonGroup
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Fullscreen as FullscreenIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  ViewList as ViewListIcon,
  GridView as GridViewIcon,
  FitScreen as FitScreenIcon
} from '@mui/icons-material';
import documentService from '../services/document.service';

interface TiffPreviewProps {
  documentId: string;
}

interface TiffInfo {
  document_id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  total_pages: number;
  format: string;
  page_dimensions: Array<{
    page_number: number;
    width: number;
    height: number;
    mode: string;
  }>;
  file_size_bytes: number;
}

const TiffPreview: React.FC<TiffPreviewProps> = ({ documentId }) => {
  const [tiffInfo, setTiffInfo] = useState<TiffInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');
  const [thumbnailSize, setThumbnailSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [previewQuality, setPreviewQuality] = useState<'thumbnail' | 'preview'>('preview');
  const [imageLoading, setImageLoading] = useState<Record<number, boolean>>({});

  useEffect(() => {
    fetchTiffInfo();
  }, [documentId]);

  const fetchTiffInfo = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 获取TIFF文件信息
      const info = await documentService.getTiffInfo(documentId);
      setTiffInfo(info);
      
      // 如果有页面信息，重置当前页码
      if (info.total_pages > 0) {
        setCurrentPage(1);
      }
    } catch (err: any) {
      setError(err.message || '获取TIFF文件信息失败');
      console.error('Error fetching TIFF info:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > (tiffInfo?.total_pages || 1)) return;
    setCurrentPage(newPage);
  };

  const handleZoomChange = (newZoom: number) => {
    setZoom(Math.max(0.1, Math.min(5, newZoom)));
  };

  const handleZoomIn = () => {
    handleZoomChange(zoom + 0.2);
  };

  const handleZoomOut = () => {
    handleZoomChange(zoom - 0.2);
  };

  const handleResetZoom = () => {
    setZoom(1);
  };

  const handleViewModeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newViewMode: 'single' | 'grid'
  ) => {
    if (newViewMode !== null) {
      setViewMode(newViewMode);
    }
  };

  const handleThumbnailSizeChange = (event: SelectChangeEvent) => {
    setThumbnailSize(event.target.value as 'small' | 'medium' | 'large');
  };

  const handlePreviewQualityChange = (event: SelectChangeEvent) => {
    setPreviewQuality(event.target.value as 'thumbnail' | 'preview');
  };

  const downloadPage = async (pageNumber: number, format: 'jpg' | 'pdf' | 'tiff') => {
    try {
      let blob: Blob;
      
      if (format === 'pdf') {
        // 使用现有的页面提取API
        blob = await documentService.extractTiffPages(documentId, [pageNumber], 'pdf');
      } else if (format === 'tiff') {
        blob = await documentService.extractTiffPages(documentId, [pageNumber], 'tiff');
      } else {
        // 下载预览图（jpg格式）
        const quality = previewQuality === 'preview' ? 'high' : 'low';
        blob = await documentService.getTiffPreview(documentId, pageNumber, quality);
      }
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const extension = format === 'pdf' ? 'pdf' : format === 'tiff' ? 'tiff' : 'jpg';
      a.download = `${tiffInfo?.original_filename.replace(/\.[^/.]+$/, '')}_page${pageNumber}.${extension}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('Download failed:', err);
      setError(`下载失败: ${err.message}`);
    }
  };

  const handleImageLoad = (pageNumber: number) => {
    setImageLoading(prev => ({ ...prev, [pageNumber]: false }));
  };

  const handleImageLoadStart = (pageNumber: number) => {
    setImageLoading(prev => ({ ...prev, [pageNumber]: true }));
  };

  const getThumbnailUrl = (pageNumber: number) => {
    const sizeMap = {
      small: 100,
      medium: 200,
      large: 300
    };
    const size = sizeMap[thumbnailSize];
    return documentService.getTiffThumbnailUrl(documentId, pageNumber, size, size);
  };

  const getPreviewUrl = (pageNumber: number) => {
    return documentService.getTiffPreviewUrl(documentId, pageNumber);
  };

  const getImageUrl = (pageNumber: number) => {
    return previewQuality === 'thumbnail' 
      ? getThumbnailUrl(pageNumber)
      : getPreviewUrl(pageNumber);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
        <Button 
          size="small" 
          onClick={fetchTiffInfo}
          startIcon={<RefreshIcon />}
          sx={{ ml: 2 }}
        >
          重试
        </Button>
      </Alert>
    );
  }

  if (!tiffInfo) {
    return (
      <Alert severity="warning">
        未找到TIFF文件信息
      </Alert>
    );
  }

  const { total_pages, page_dimensions } = tiffInfo;
  const currentPageDimensions = page_dimensions?.find(p => p.page_number === currentPage);

  return (
    <Box>
      {/* 控制栏 */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container alignItems="center" spacing={2}>
          <Grid
            component="div"
            size={{
              xs: 12,
              md: 6
            }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="subtitle1">
                页码: {currentPage} / {total_pages}
              </Typography>
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <IconButton 
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  size="small"
                >
                  <ChevronLeftIcon />
                </IconButton>
                
                <Slider
                  value={currentPage}
                  min={1}
                  max={total_pages}
                  step={1}
                  onChange={(_, value) => handlePageChange(value as number)}
                  sx={{ width: 120 }}
                  size="small"
                />
                
                <IconButton 
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= total_pages}
                  size="small"
                >
                  <ChevronRightIcon />
                </IconButton>
              </Box>

              {currentPageDimensions && (
                <Chip 
                  label={`${currentPageDimensions.width} × ${currentPageDimensions.height}`}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
          </Grid>
          
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, flexWrap: 'wrap' }}>
              {/* 缩放控制 */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Tooltip title="缩小">
                  <IconButton onClick={handleZoomOut} size="small">
                    <ZoomOutIcon />
                  </IconButton>
                </Tooltip>
                <Typography variant="body2" sx={{ minWidth: '40px', textAlign: 'center' }}>
                  {Math.round(zoom * 100)}%
                </Typography>
                <Tooltip title="放大">
                  <IconButton onClick={handleZoomIn} size="small">
                    <ZoomInIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="重置缩放">
                  <IconButton onClick={handleResetZoom} size="small">
                    <FitScreenIcon />
                  </IconButton>
                </Tooltip>
              </Box>

              {/* 视图模式 */}
              <ToggleButtonGroup
                value={viewMode}
                exclusive
                onChange={handleViewModeChange}
                size="small"
              >
                <ToggleButton value="single">
                  <Tooltip title="单页视图">
                    <ViewListIcon />
                  </Tooltip>
                </ToggleButton>
                <ToggleButton value="grid">
                  <Tooltip title="网格视图">
                    <GridViewIcon />
                  </Tooltip>
                </ToggleButton>
              </ToggleButtonGroup>

              {/* 缩略图尺寸 */}
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>缩略图尺寸</InputLabel>
                <Select
                  value={thumbnailSize}
                  label="缩略图尺寸"
                  onChange={handleThumbnailSizeChange}
                >
                  <MenuItem value="small">小</MenuItem>
                  <MenuItem value="medium">中</MenuItem>
                  <MenuItem value="large">大</MenuItem>
                </Select>
              </FormControl>

              {/* 预览质量 */}
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>预览质量</InputLabel>
                <Select
                  value={previewQuality}
                  label="预览质量"
                  onChange={handlePreviewQualityChange}
                >
                  <MenuItem value="thumbnail">缩略图</MenuItem>
                  <MenuItem value="preview">高质量</MenuItem>
                </Select>
              </FormControl>

              {/* 刷新按钮 */}
              <Tooltip title="刷新">
                <IconButton onClick={fetchTiffInfo} size="small">
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>
      </Paper>
      {/* 主预览区域 */}
      {viewMode === 'single' ? (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            minHeight: '500px',
            position: 'relative'
          }}>
            {imageLoading[currentPage] && (
              <CircularProgress sx={{ position: 'absolute' }} />
            )}
            
            <img
              src={getImageUrl(currentPage)}
              alt={`第 ${currentPage} 页`}
              style={{
                maxWidth: '100%',
                maxHeight: '600px',
                objectFit: 'contain',
                transform: `scale(${zoom})`,
                transition: 'transform 0.2s',
                cursor: zoom > 1 ? 'grab' : 'default'
              }}
              onLoad={() => handleImageLoad(currentPage)}
              onLoadStart={() => handleImageLoadStart(currentPage)}
            />
          </Box>
          
          {/* 页面操作按钮 */}
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 2 }}>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={() => downloadPage(currentPage, 'jpg')}
            >
              下载JPEG
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={() => downloadPage(currentPage, 'pdf')}
            >
              下载PDF
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={() => downloadPage(currentPage, 'tiff')}
            >
              下载TIFF
            </Button>
            <Button
              variant="contained"
              startIcon={<FullscreenIcon />}
              onClick={() => window.open(getImageUrl(currentPage), '_blank')}
            >
              全屏查看
            </Button>
          </Box>
        </Paper>
      ) : (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            所有页面 ({total_pages} 页)
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          <Grid container spacing={2}>
            {Array.from({ length: total_pages }, (_, i) => i + 1).map(pageNumber => (
              <Grid
                key={pageNumber}
                size={{
                  xs: 6,
                  sm: 4,
                  md: 3,
                  lg: 2
                }}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    border: pageNumber === currentPage ? 2 : 0,
                    borderColor: 'primary.main'
                  }}
                  onClick={() => {
                    setCurrentPage(pageNumber);
                    setViewMode('single');
                  }}
                >
                  <Box sx={{ position: 'relative' }}>
                    {imageLoading[pageNumber] && (
                      <CircularProgress 
                        size={24} 
                        sx={{ 
                          position: 'absolute', 
                          top: '50%', 
                          left: '50%',
                          transform: 'translate(-50%, -50%)'
                        }} 
                      />
                    )}
                    <CardMedia
                      component="img"
                      image={getThumbnailUrl(pageNumber)}
                      alt={`第 ${pageNumber} 页缩略图`}
                      sx={{ 
                        height: 120,
                        objectFit: 'contain',
                        opacity: imageLoading[pageNumber] ? 0.3 : 1
                      }}
                      onLoad={() => handleImageLoad(pageNumber)}
                      onLoadStart={() => handleImageLoadStart(pageNumber)}
                    />
                  </Box>
                  <CardContent sx={{ p: 1 }}>
                    <Typography variant="body2" align="center">
                      第 {pageNumber} 页
                    </Typography>
                    {page_dimensions?.[pageNumber - 1] && (
                      <Typography variant="caption" color="text.secondary" align="center" display="block">
                        {page_dimensions[pageNumber - 1].width} × {page_dimensions[pageNumber - 1].height}
                      </Typography>
                    )}
                  </CardContent>
                  <CardActions sx={{ p: 1, justifyContent: 'center' }}>
                    <Tooltip title="下载">
                      <IconButton 
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadPage(pageNumber, 'jpg');
                        }}
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}
      {/* 文件信息 */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          文件信息
        </Typography>
        <Divider sx={{ mb: 2 }} />
        
        <Grid container spacing={2}>
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Typography variant="body2" color="text.secondary">文件名</Typography>
            <Typography variant="body1">{tiffInfo.original_filename}</Typography>
          </Grid>
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Typography variant="body2" color="text.secondary">总页数</Typography>
            <Typography variant="body1">{tiffInfo.total_pages}</Typography>
          </Grid>
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Typography variant="body2" color="text.secondary">文件格式</Typography>
            <Typography variant="body1">{tiffInfo.format}</Typography>
          </Grid>
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Typography variant="body2" color="text.secondary">文件大小</Typography>
            <Typography variant="body1">
              {(tiffInfo.file_size_bytes / 1024).toFixed(2)} KB
            </Typography>
          </Grid>
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Typography variant="body2" color="text.secondary">MIME类型</Typography>
            <Typography variant="body1">{tiffInfo.mime_type}</Typography>
          </Grid>
          <Grid
            size={{
              xs: 12,
              md: 6
            }}>
            <Typography variant="body2" color="text.secondary">文档ID</Typography>
            <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
              {tiffInfo.document_id}
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default TiffPreview;