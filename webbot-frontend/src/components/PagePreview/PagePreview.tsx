/**
 * 页面预览组件
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Visibility,
  Refresh,
  Download,
  OpenInNew,
  Code,
  CheckCircle,
  Error,
  Info,
} from '@mui/icons-material';
import { useComponentInstances } from '../../hooks/useComponents';
import { useEditorState } from '../../hooks/useEditorState';
import { renderPage } from '../../services/api';
import type { PageRenderResponse } from '../../services/api';

interface PagePreviewProps {
  /**
   * 预览模式激活状态
   */
  active: boolean;

  /**
   * 预览标题
   */
  title?: string;
}

const PagePreview: React.FC<PagePreviewProps> = ({ active, title = '页面预览' }) => {
  const { componentInstances } = useComponentInstances();
  const { previewMode } = useEditorState();

  const [renderedHtml, setRenderedHtml] = useState<string>('');
  const [renderResponse, setRenderResponse] = useState<PageRenderResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRenderTime, setLastRenderTime] = useState<string>('');
  const [iframeKey, setIframeKey] = useState(0);

  /**
   * 获取渲染数据
   */
  const getRenderData = useCallback(() => {
    return {
      component_instances: componentInstances.map(instance => ({
        id: instance.id,
        template_id: instance.template_id,
        configuration: instance.configuration,
        position: { x: instance.position_x, y: instance.position_y },
        alignment: instance.alignment || 'left',
      })),
      page_title: title,
      include_wet_boew: true,
      include_accessibility: true,
      include_admin_resources: false,
      include_header_footer: true,
    };
  }, [componentInstances, title]);

  /**
   * 执行页面渲染
   */
  const handleRenderPage = useCallback(async () => {
    if (componentInstances.length === 0) {
      setError('没有组件可以渲染。请先添加一些组件到画布。');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const renderData = getRenderData();
      const response = await renderPage(renderData);

      setRenderResponse(response);

      if (response.success) {
        setRenderedHtml(response.html);
        setLastRenderTime(new Date().toLocaleString());
        // 更新iframe key以强制重新加载
        setIframeKey(prev => prev + 1);
      } else {
        setError(response.error || '渲染失败，未知错误');
        setRenderedHtml(response.html);
      }
    } catch (err) {
      setError(`渲染错误: ${err}`);
      console.error('渲染页面失败:', err);
    } finally {
      setLoading(false);
    }
  }, [componentInstances, getRenderData]);

  /**
   * 在新窗口中打开预览
   */
  const handleOpenInNewWindow = () => {
    if (!renderedHtml) return;

    const newWindow = window.open('', '_blank');
    if (newWindow) {
      newWindow.document.write(renderedHtml);
      newWindow.document.close();
    }
  };

  /**
   * 下载HTML文件
   */
  const handleDownloadHtml = () => {
    if (!renderedHtml) return;

    const blob = new Blob([renderedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `webbot-page-${new Date().toISOString().slice(0, 10)}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /**
   * 组件变化时自动重新渲染（可选，可能需要防抖）
   */
  useEffect(() => {
    // 简单实现：当组件数量变化时自动重新渲染
    // 实际项目中应该使用防抖和更精细的依赖检测
    if (active && componentInstances.length > 0 && previewMode) {
      // 可以在这里添加自动重新渲染逻辑
      // 但为了性能，现在使用手动渲染按钮
    }
  }, [componentInstances, active, previewMode]);

  /**
   * 激活时自动渲染
   */
  useEffect(() => {
    if (active && componentInstances.length > 0) {
      // 延迟渲染以避免初始加载时的竞争条件
      const timer = setTimeout(() => {
        handleRenderPage();
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [active, componentInstances, handleRenderPage]);

  // 如果不激活，不渲染内容
  if (!active) {
    return null;
  }

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题栏 */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: 'primary.50',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Visibility color="primary" />
          <Typography variant="h6">{title}</Typography>
          <Chip
            label="Beta"
            size="small"
            color="primary"
            variant="outlined"
            sx={{ height: 20, fontSize: '0.7rem' }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="重新渲染">
            <IconButton
              size="small"
              onClick={handleRenderPage}
              disabled={loading || componentInstances.length === 0}
            >
              <Refresh fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="新窗口打开">
            <IconButton size="small" onClick={handleOpenInNewWindow} disabled={!renderedHtml}>
              <OpenInNew fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="下载HTML">
            <IconButton size="small" onClick={handleDownloadHtml} disabled={!renderedHtml}>
              <Download fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Paper>

      {/* 状态信息栏 */}
      {renderResponse && (
        <Paper
          elevation={0}
          sx={{
            p: 1.5,
            borderBottom: 1,
            borderColor: 'divider',
            bgcolor: renderResponse.success ? 'success.50' : 'error.50',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {renderResponse.success ? (
                <CheckCircle fontSize="small" color="success" />
              ) : (
                <Error fontSize="small" color="error" />
              )}
              <Typography variant="body2">
                {renderResponse.success ? '渲染成功' : '渲染失败'}
              </Typography>
              <Chip
                label={`${renderResponse.component_count} 个组件`}
                size="small"
                variant="outlined"
              />
              {renderResponse.alignment_stats && (
                <>
                  <Chip
                    label={`左: ${renderResponse.alignment_stats.left}`}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={`中: ${renderResponse.alignment_stats.center}`}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={`右: ${renderResponse.alignment_stats.right}`}
                    size="small"
                    variant="outlined"
                  />
                </>
              )}
            </Box>
            <Typography variant="caption" color="text.secondary">
              渲染时间: {lastRenderTime}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* 错误提示 */}
      {error && (
        <Alert severity="error" sx={{ m: 2, mb: 1 }}>
          {error}
        </Alert>
      )}

      {/* 加载状态 */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
          <Box sx={{ textAlign: 'center' }}>
            <CircularProgress size={40} />
            <Typography variant="body2" sx={{ mt: 2 }}>
              正在渲染页面...
            </Typography>
            <Typography variant="caption" color="text.secondary">
              处理 {componentInstances.length} 个组件
            </Typography>
          </Box>
        </Box>
      )}

      {/* 空状态 */}
      {!loading && componentInstances.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
          <Box sx={{ textAlign: 'center', maxWidth: 400 }}>
            <Visibility sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              暂无组件可预览
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              请先从左侧组件库拖拽一些组件到编辑画布。
            </Typography>
            <Button
              variant="outlined"
              startIcon={<Info />}
              onClick={() => window.open('http://localhost:5174', '_blank')}
            >
              查看编辑器
            </Button>
          </Box>
        </Box>
      )}

      {/* 预览内容 */}
      {!loading && renderedHtml && componentInstances.length > 0 && (
        <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              border: 'none',
            }}
          >
            <iframe
              key={iframeKey}
              srcDoc={renderedHtml}
              title="页面预览"
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                backgroundColor: 'white',
              }}
              sandbox="allow-same-origin allow-scripts"
            />
          </Box>
        </Box>
      )}

      {/* 底部信息栏 */}
      <Paper
        elevation={0}
        sx={{
          p: 1.5,
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'grey.50',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            实时预览 | WET-BOEW 标准 | 响应式设计
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="查看渲染统计">
              <IconButton size="small" onClick={() => console.log(renderResponse)}>
                <Code fontSize="small" />
              </IconButton>
            </Tooltip>
            <Typography variant="caption" color="text.secondary">
              {componentInstances.length} 个组件就绪
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default PagePreview;
