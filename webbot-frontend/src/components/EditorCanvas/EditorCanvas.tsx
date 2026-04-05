/**
 * 编辑器画布组件
 */

import React, { useRef, useState, useEffect } from 'react';
import { Box, Paper, Typography, IconButton, Tooltip, Button, Dialog, DialogTitle, DialogContent, List, ListItem, ListItemText, TextField, InputAdornment, CircularProgress, DialogActions } from '@mui/material';
import { Settings, Edit, Public, Add, Search, DragIndicator, Home } from '@mui/icons-material';
import { useEditorState, useDragAndDrop } from '../../hooks/useEditorState';
import { useComponentInstances } from '../../hooks/useComponents';
import CanvasComponent from './CanvasComponent';

const EditorCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLDivElement>(null);
  const { canvasWidth, canvasHeight, previewMode, currentPageTitle, getCanvasBackground, getCanvasGrid } =
    useEditorState();

  const { handleDrop, handleDragOver } = useDragAndDrop();
  const { componentInstances, addComponentInstance, selectInstance } = useComponentInstances();

  // 组件选择弹出窗口状态
  const [dialogOpen, setDialogOpen] = useState(false);
  const [components, setComponents] = useState<any[]>([]);
  const [filteredComponents, setFilteredComponents] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  /**
   * 处理放置事件
   */
  const handleCanvasDrop = (event: React.DragEvent) => {
    handleDrop(event, (templateId, position) => {
      // 添加新组件实例
      addComponentInstance(templateId, position, {});
    });
  };

  /**
   * 处理画布点击（取消选择）
   */
  const handleCanvasClick = () => {
    selectInstance(null);
  };

  /**
   * 打开组件选择对话框
   */
  const handleOpenDialog = async () => {
    setDialogOpen(true);
    setLoading(true);
    try {
      // 从后端获取组件列表（通过代理）
      const response = await fetch('/api/v1/components/templates');
      if (response.ok) {
        const data = await response.json();
        setComponents(data);
        setFilteredComponents(data);
      } else {
        console.error('获取组件列表失败:', response.status);
        // 使用默认组件列表作为后备
        const defaultComponents = [
          { id: 'wet-button-primary', name: 'Primary Button', description: '主要按钮组件' },
          { id: 'wet-input-text', name: 'Text Input', description: '文本输入框组件' },
          { id: 'wet-title', name: 'Title', description: '标题组件' },
        ];
        setComponents(defaultComponents);
        setFilteredComponents(defaultComponents);
      }
    } catch (error) {
      console.error('获取组件列表出错:', error);
      // 使用默认组件列表
      const defaultComponents = [
        { id: 'wet-button-primary', name: 'Primary Button', description: '主要按钮组件' },
        { id: 'wet-input-text', name: 'Text Input', description: '文本输入框组件' },
        { id: 'wet-title', name: 'Title', description: '标题组件' },
      ];
      setComponents(defaultComponents);
      setFilteredComponents(defaultComponents);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 关闭对话框
   */
  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSearchTerm('');
  };

  /**
   * 搜索组件
   */
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const term = event.target.value;
    setSearchTerm(term);
    if (term.trim() === '') {
      setFilteredComponents(components);
    } else {
      const filtered = components.filter(comp => 
        comp.name.toLowerCase().includes(term.toLowerCase()) || 
        comp.id.toLowerCase().includes(term.toLowerCase()) ||
        (comp.description && comp.description.toLowerCase().includes(term.toLowerCase()))
      );
      setFilteredComponents(filtered);
    }
  };

  /**
   * 选择组件并添加到画布
   */
  const handleSelectComponent = (componentId: string) => {
    // 计算添加到画布中心位置
    const centerX = canvasWidth / 2 - 100; // 假设组件宽度约200px
    const centerY = canvasHeight / 2 - 25; // 假设组件高度约50px
    
    addComponentInstance(componentId, { x: centerX, y: centerY }, {});
    handleCloseDialog();
  };

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'visible',
      }}
    >
      {/* 画布工具栏 */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography variant="h6">
          编辑器画布
          {previewMode && (
            <Typography component="span" variant="caption" sx={{ ml: 1, color: 'success.main' }}>
              (预览模式)
            </Typography>
          )}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          页面: {canvasWidth} × {canvasHeight + 440}px (含Header/Footer) | 组件: {componentInstances.length}
        </Typography>
      </Paper>

      {/* 画布区域 - 包含完整的WET-BOEW页面结构 */}
      <Box
        ref={canvasRef}
        sx={{
          flex: 1,
          position: 'relative',
          overflowX: 'auto',
          overflowY: 'auto',
          minWidth: '100%',
          bgcolor: getCanvasBackground(),
          ...getCanvasGrid(),
        }}
        onClick={handleCanvasClick}
      >
        {/* 完整的页面预览容器 */}
        <Box
          sx={{
            width: canvasWidth,
            minWidth: canvasWidth,
            m: 0,
            boxShadow: previewMode ? 'none' : 1,
            border: previewMode ? 'none' : '1px dashed',
            borderColor: 'divider',
            borderRadius: 1,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* 1. HEADER区域 - canada.ca主题header */}
          <Box
            component="header"
            role="banner"
            sx={{
              width: '100%',
              height: 140, // 增加高度以适应更复杂的布局
              bgcolor: '#26374a', // 加拿大政府蓝色
              color: 'white',
              p: 3,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              position: 'relative',
              borderBottom: '2px solid',
              borderColor: '#e31c3d', // 加拿大政府红色
            }}
          >
            {/* Header工具栏 */}
            {!previewMode && (
              <Box
                sx={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  display: 'flex',
                  gap: 1,
                }}
              >
                <Tooltip title="配置Header">
                  <IconButton size="small" sx={{ color: 'white', bgcolor: 'rgba(255,255,255,0.1)' }}>
                    <Settings fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            )}

            {/* Header内容 - 使用canada.ca主题布局 */}
            <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 3 }}>
              {/* 语言选择 - 右上角 */}
              <Box sx={{ flex: 1, minWidth: 120, display: 'flex', justifyContent: 'flex-end' }}>
                <Box
                  sx={{
                    display: 'flex',
                    gap: 2,
                    fontSize: '0.85rem',
                    bgcolor: 'rgba(0,0,0,0.2)',
                    borderRadius: 1,
                    px: 1.5,
                    py: 0.5,
                  }}
                >
                  <Box sx={{ color: 'white', fontWeight: 'bold', borderBottom: '2px solid white' }}>
                    English
                  </Box>
                  <Box sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Français</a>
                  </Box>
                </Box>
              </Box>

              {/* 加拿大政府Logo和品牌 */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 2, minWidth: 300 }}>
                <Box
                  sx={{
                    width: 260,
                    height: 48,
                    bgcolor: 'white',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#26374a',
                    fontWeight: 'bold',
                    fontSize: '0.95rem',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <Public sx={{ mr: 1.5, fontSize: '1.2rem', color: '#e31c3d' }} />
                  <Box>
                    <Box sx={{ fontSize: '0.8rem', fontWeight: 'normal' }}>Government of Canada</Box>
                    <Box sx={{ fontSize: '1rem', fontWeight: 'bold' }}>Gouvernement du Canada</Box>
                  </Box>
                  <Box sx={{ position: 'absolute', right: 10, fontSize: '0.7rem', color: '#666' }}>
                    <span className="wb-inv"> / </span>
                  </Box>
                </Box>
              </Box>

              {/* 搜索框 - 仿canada.ca搜索 */}
              <Box sx={{ flex: 3, minWidth: 350, maxWidth: 500 }}>
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 0.5,
                  }}
                >
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)', fontSize: '0.85rem', fontWeight: 'bold' }}>
                    Search
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0 }}>
                    <Box
                      component="input"
                      placeholder="Search Canada.ca"
                      sx={{
                        flex: 1,
                        p: '8px 12px',
                        borderRadius: '4px 0 0 4px',
                        border: '2px solid',
                        borderColor: 'transparent',
                        fontSize: '0.9rem',
                        bgcolor: 'white',
                        color: 'text.primary',
                        '&:focus': {
                          outline: 'none',
                          borderColor: '#e31c3d',
                        },
                      }}
                    />
                    <Box
                      component="button"
                      sx={{
                        bgcolor: '#e31c3d', // 加拿大政府红色
                        color: 'white',
                        border: 'none',
                        borderRadius: '0 4px 4px 0',
                        px: 2,
                        fontWeight: 'bold',
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.5,
                        '&:hover': {
                          bgcolor: '#c1112c',
                        },
                      }}
                    >
                      <Search sx={{ fontSize: '1rem' }} />
                      <span className="wb-inv">Search</span>
                    </Box>
                  </Box>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
                    Search tips: Use keywords, avoid special characters
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Header标签 */}
            {!previewMode && (
              <Typography
                variant="caption"
                sx={{
                  position: 'absolute',
                  bottom: 6,
                  left: 10,
                  color: 'rgba(255,255,255,0.7)',
                  fontSize: '0.7rem',
                  bgcolor: 'rgba(0,0,0,0.3)',
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                }}
              >
                canada.ca Theme Header (自动集成)
              </Typography>
            )}
          </Box>

          {/* 面包屑导航 - 仿canada.ca标准面包屑 */}
          {!previewMode && (
            <Box
              sx={{
                width: '100%',
                bgcolor: '#f8f9fa',
                borderBottom: '1px solid #dee2e6',
                px: 3,
                py: 2,
              }}
            >
              <Box
                sx={{
                  width: '100%',
                  maxWidth: 1200,
                  margin: '0 auto',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <Home sx={{ fontSize: '0.9rem', color: '#6c757d' }} />
                <Typography variant="body2" sx={{ color: '#6c757d' }}>
                  <a href="#" style={{ color: '#2e5274', textDecoration: 'none' }}>Canada.ca</a>
                </Typography>
                <Typography variant="body2" sx={{ color: '#6c757d' }}>/</Typography>
                <Typography variant="body2" sx={{ color: '#6c757d' }}>
                  <a href="#" style={{ color: '#2e5274', textDecoration: 'none' }}>Service Canada</a>
                </Typography>
                <Typography variant="body2" sx={{ color: '#6c757d' }}>/</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#26374a' }}>
                  {currentPageTitle || 'Generic Template test'}
                </Typography>
                
                {/* 修改日期 - 右侧 */}
                <Box sx={{ flex: 1, display: 'flex', justifyContent: 'flex-end' }}>
                  <Typography variant="caption" sx={{ color: '#6c757d', fontSize: '0.75rem' }}>
                    Date modified: 2026-02-09
                  </Typography>
                </Box>
              </Box>
            </Box>
          )}

          {/* 2. MAIN内容区域 - 可编辑的画布 */}
          <Box
            component="main"
            property="mainContentOfPage"
            resource="#wb-main"
            typeof="WebPageElement"
            sx={{
              position: 'relative',
              width: '100%',
              height: canvasHeight,
              minHeight: canvasHeight,
              bgcolor: '#e6f2ff', // 蓝色编辑区域
              overflow: 'hidden',
              borderBottom: previewMode ? 'none' : '1px dashed',
              borderColor: 'divider',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'flex-start',
              p: 3,
            }}
          >
            {/* 内容容器 - 始终包含固定的拖拽区域 */}
            <Box
              sx={{
                position: 'relative',
                width: '100%',
                maxWidth: 1200, // 标准内容宽度
                minHeight: 200, // 最小高度确保拖拽区可见
                bgcolor: 'background.paper', // 白色背景
                borderRadius: 2,
                boxShadow: previewMode ? 'none' : '0 2px 8px rgba(0,0,0,0.1)',
                border: previewMode ? '1px solid' : '2px dashed',
                borderColor: previewMode ? 'divider' : 'primary.main',
                overflow: 'auto',
                p: 0,
                display: 'flex',
                flexDirection: 'column',
              }}
              onDrop={handleCanvasDrop}
              onDragOver={handleDragOver}
            >
              {/* 组件渲染区域 - 在拖拽区前面（上方） */}
              {componentInstances.length > 0 && (
                <Box sx={{ p: 2, pb: 1 }}>
                  {componentInstances.map(instance => (
                    <CanvasComponent key={instance.id} instance={instance} previewMode={previewMode} />
                  ))}
                </Box>
              )}

              {/* 固定的拖拽区域 - 始终显示 */}
              {!previewMode && (
                <Box
                  sx={{
                    width: '100%',
                    minHeight: 120,
                    mt: componentInstances.length > 0 ? 0 : 0,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    bgcolor: componentInstances.length === 0 ? '#f8f9fa' : '#f0f7ff',
                    border: componentInstances.length === 0 ? '2px dashed #dee2e6' : '2px dashed #4d9fff',
                    borderRadius: componentInstances.length === 0 ? 1 : '0 0 4px 4px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    position: 'relative',
                    '&:hover': {
                      bgcolor: componentInstances.length === 0 ? '#e9ecef' : '#e1f0ff',
                      borderColor: componentInstances.length === 0 ? '#adb5bd' : '#2d8cff',
                    },
                  }}
                  onClick={handleOpenDialog}
                >
                  {/* 拖拽区域指示器 */}
                  <Box sx={{ position: 'absolute', top: 8, left: 8 }}>
                    <Typography variant="caption" sx={{ color: componentInstances.length === 0 ? '#6c757d' : '#2d8cff', fontWeight: 'bold', fontSize: '0.7rem' }}>
                      {componentInstances.length === 0 ? '拖放区域' : '继续拖放区域'}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                    <DragIndicator sx={{ color: componentInstances.length === 0 ? '#6c757d' : '#2d8cff', fontSize: '1.5rem' }} />
                    <Typography variant="h6" sx={{ color: componentInstances.length === 0 ? '#495057' : '#2d8cff', fontWeight: 'bold' }}>
                      Drag components here
                    </Typography>
                  </Box>
                  
                  <Typography variant="body2" sx={{ color: componentInstances.length === 0 ? '#6c757d' : '#4d9fff', textAlign: 'center', maxWidth: 400 }}>
                    {componentInstances.length === 0 
                      ? '拖放左侧组件到此区域，或点击此处添加组件' 
                      : '拖放更多组件到此处，或点击添加'}
                  </Typography>
                  
                  <Typography variant="caption" sx={{ display: 'block', mt: 2, color: componentInstances.length === 0 ? '#adb5bd' : '#8bc1ff' }}>
                    组件将插入到此区域前面（上方）
                  </Typography>
                </Box>
              )}

              {/* 添加组件浮动按钮 */}
              {!previewMode && componentInstances.length > 0 && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 16,
                    right: 16,
                    zIndex: 5,
                  }}
                >
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<Add />}
                    onClick={handleOpenDialog}
                    sx={{
                      borderRadius: 2,
                      boxShadow: 3,
                      px: 2,
                      py: 1,
                      fontWeight: 'bold',
                      textTransform: 'none',
                    }}
                  >
                    + 添加组件
                  </Button>
                </Box>
              )}
            </Box>
          </Box>

          {/* 3. FOOTER区域 - canada.ca主题footer */}
          <Box
            component="footer"
            role="contentinfo"
            sx={{
              width: '100%',
              minHeight: 300, // 增加高度以适应更复杂的内容
              bgcolor: '#333',
              color: 'white',
              position: 'relative',
              borderTop: '2px solid',
              borderColor: '#e31c3d', // 加拿大政府红色
            }}
          >
            {/* Footer工具栏 */}
            {!previewMode && (
              <Box
                sx={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  display: 'flex',
                  gap: 1,
                  zIndex: 10,
                }}
              >
                <Tooltip title="配置Footer">
                  <IconButton size="small" sx={{ color: 'white', bgcolor: 'rgba(255,255,255,0.1)' }}>
                    <Settings fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            )}

            {/* 主要footer部分 */}
            <Box
              sx={{
                bgcolor: '#555',
                p: 4,
              }}
            >
              <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
                <Typography variant="h3" sx={{ fontSize: '1.2rem', fontWeight: 'bold', mb: 2, color: 'white' }}>
                  Government of Canada
                </Typography>
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 4, mb: 3 }}>
                  <Box sx={{ flex: '1 1 200px' }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#e31c3d' }}>
                      Services
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Jobs</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Immigration and citizenship</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Travel and tourism</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Business</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Benefits</a>
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ flex: '1 1 200px' }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#e31c3d' }}>
                      Topics
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Health</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Taxes</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Environment</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>National security</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Culture and sport</a>
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ flex: '1 1 200px' }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#e31c3d' }}>
                      Departments
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>All contacts</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Departments and agencies</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>About government</a>
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                        <a href="#" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>Public service</a>
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              </Box>
            </Box>

            {/* 子footer部分 */}
            <Box
              sx={{
                bgcolor: '#222',
                p: 3,
              }}
            >
              <Box sx={{ maxWidth: 1200, mx: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 3 }}>
                {/* 链接 */}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Social media</a>
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Mobile applications</a>
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>About Canada.ca</a>
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Terms and conditions</a>
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Privacy</a>
                  </Typography>
                </Box>

                {/* 政府标志 */}
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      width: 100,
                      height: 35,
                      bgcolor: 'rgba(255,255,255,0.9)',
                      borderRadius: 1,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#222',
                      fontWeight: 'bold',
                      fontSize: '0.8rem',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                    }}
                  >
                    Canada
                  </Box>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', maxWidth: 120 }}>
                    Symbol of the Government of Canada
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* 底部版权信息 */}
            <Box
              sx={{
                bgcolor: '#111',
                p: 2,
                textAlign: 'center',
              }}
            >
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>
                © His Majesty the King in Right of Canada, as represented by the Minister of Digital Government, 2026
              </Typography>
            </Box>

            {/* Footer标签 */}
            {!previewMode && (
              <Typography
                variant="caption"
                sx={{
                  position: 'absolute',
                  bottom: 6,
                  left: 10,
                  color: 'rgba(255,255,255,0.5)',
                  fontSize: '0.7rem',
                  bgcolor: 'rgba(0,0,0,0.4)',
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                }}
              >
                canada.ca Theme Footer (自动集成)
              </Typography>
            )}
          </Box>
        </Box>

        {/* 画布网格指示器 */}
        {!previewMode && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 16,
              right: 16,
              bgcolor: 'background.paper',
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              p: 1,
            }}
          >
            <Typography variant="caption" color="text.secondary">
              页面结构: Header(120px) + Main({canvasHeight}px) + Footer(180px)
            </Typography>
          </Box>
        )}
      </Box>

      {/* 画布状态栏 */}
      <Paper
        elevation={0}
        sx={{
          p: 1,
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          提示: {previewMode ? '预览模式 - 只读' : '编辑模式 - 只有白色内容区域可以拖拽组件'}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          WET-BOEW 组件编辑器
        </Typography>
      </Paper>

      {/* 组件选择对话框 */}
      <Dialog 
        open={dialogOpen} 
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          插入组件
          <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'text.secondary' }}>
            选择WET-BOEW组件添加到编辑区域
          </Typography>
        </DialogTitle>
        
        <DialogContent>
          {/* 搜索框 */}
          <TextField
            fullWidth
            placeholder="搜索组件..."
            value={searchTerm}
            onChange={handleSearchChange}
            variant="outlined"
            size="small"
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

          {/* 组件列表 */}
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : filteredComponents.length === 0 ? (
            <Box sx={{ textAlign: 'center', p: 3, color: 'text.secondary' }}>
              <Typography variant="body2">未找到匹配的组件</Typography>
            </Box>
          ) : (
            <List sx={{ maxHeight: 300, overflow: 'auto' }}>
              {filteredComponents.map(component => (
                <ListItem
                  key={component.id}
                  button
                  onClick={() => handleSelectComponent(component.id)}
                  sx={{
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1,
                    '&:hover': {
                      bgcolor: 'action.hover',
                    },
                  }}
                >
                  <ListItemText
                    primary={
                      <Typography variant="body2" fontWeight="medium">
                        {component.name || component.id.replace('wet-', '').replace('-', ' ')}
                      </Typography>
                    }
                    secondary={
                      <Typography variant="caption" color="text.secondary">
                        {component.description || component.id}
                      </Typography>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Typography variant="caption" sx={{ flex: 1, color: 'text.secondary', ml: 2 }}>
            {filteredComponents.length} 个可用组件
          </Typography>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EditorCanvas;
