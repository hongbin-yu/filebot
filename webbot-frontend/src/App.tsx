/**
 * WebBot 组件编辑器 - 主应用
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Menu,
  MenuItem,
  ListItemText,
} from '@mui/material';
import { Preview, Edit, Cloud, Settings, BugReport, Refresh, Add, Save, FolderOpen } from '@mui/icons-material';
import EditorCanvas from './components/EditorCanvas/EditorCanvas';
import ComponentLibrary from './components/ComponentLibrary/ComponentLibrary';
import ComponentConfigDialog from './components/ComponentConfig/ComponentConfigDialog';
import { useEditorStore } from './stores/editorStore';
import { checkHealth, fetchPages, fetchPageById, createPage, updatePage, deletePage, type Page, type ComponentInstance } from './services/api';

function App() {
  const { previewMode, togglePreviewMode, currentPageId, currentPageTitle, componentInstances, 
          setCurrentPageId, setPages, setCurrentPageTitle, clearCurrentPage, setComponentInstances } = useEditorStore();
  const [apiHealth, setApiHealth] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [pages, setLocalPages] = useState<Page[]>([]);
  const [isLoadingPages, setIsLoadingPages] = useState(false);
  const [pageMenuAnchor, setPageMenuAnchor] = useState<null | HTMLElement>(null);

  /**
   * 加载页面列表
   */
  const loadPages = async () => {
    setIsLoadingPages(true);
    try {
      const fetchedPages = await fetchPages();
      setLocalPages(fetchedPages);
      setPages(fetchedPages);
    } catch (error) {
      console.error('加载页面列表失败:', error);
    } finally {
      setIsLoadingPages(false);
    }
  };

  /**
   * 创建新页面
   */
  const handleNewPage = async () => {
    try {
      const pageTitle = prompt('请输入页面标题:', `新页面 ${new Date().toLocaleDateString()}`);
      if (!pageTitle) return;

      const newPage = await createPage({
        title: pageTitle,
        language: 'en',
        status: 'draft',
        metadata: {
          componentInstances: [],
          createdWith: 'WebBot Editor',
        },
      });

      if (newPage) {
        // 清空当前画布，设置新页面
        clearCurrentPage();
        setCurrentPageId(newPage.id);
        setCurrentPageTitle(newPage.title);
        // 重新加载页面列表
        await loadPages();
        alert(`页面 "${pageTitle}" 创建成功！`);
      }
    } catch (error) {
      console.error('创建页面失败:', error);
      alert('创建页面失败，请检查API连接。');
    }
  };

  /**
   * 保存当前页面
   */
  const handleSavePage = async () => {
    if (!currentPageId) {
      alert('请先创建或选择一个页面。');
      return;
    }

    try {
      // 准备组件实例数据
      const componentInstancesData = componentInstances.map((instance: ComponentInstance) => ({
        id: instance.id,
        template_id: instance.template_id,
        configuration: instance.configuration,
        position_x: instance.position_x,
        position_y: instance.position_y,
        alignment: instance.alignment,
      }));

      // 更新页面，将组件实例存储在metadata中
      const updatedPage = await updatePage(currentPageId, {
        metadata: {
          componentInstances: componentInstancesData,
          lastSaved: new Date().toISOString(),
        },
      });

      if (updatedPage) {
        alert('页面保存成功！');
      }
    } catch (error) {
      console.error('保存页面失败:', error);
      alert('保存页面失败，请检查API连接。');
    }
  };



  /**
   * 打开页面菜单
   */
  const handlePageMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setPageMenuAnchor(event.currentTarget);
  };

  /**
   * 关闭页面菜单
   */
  const handlePageMenuClose = () => {
    setPageMenuAnchor(null);
  };

  /**
   * 选择页面
   */
  const handleSelectPage = async (page: Page) => {
    handlePageMenuClose();
    
    try {
      // 获取页面详情
      const pageDetail = await fetchPageById(page.id);
      if (!pageDetail) {
        alert(`无法加载页面: ${page.title}`);
        return;
      }

      // 设置当前页面
      setCurrentPageId(pageDetail.id);
      setCurrentPageTitle(pageDetail.title);

      // 从metadata中加载组件实例
      const metadata = pageDetail.metadata || {};
      const savedInstances = metadata.componentInstances as any[] || [];
      
      if (savedInstances.length > 0) {
        // 转换保存的数据为ComponentInstance格式
        const componentInstances = savedInstances.map(instance => ({
          id: instance.id,
          template_id: instance.template_id,
          page_id: pageDetail.id,
          position_x: instance.position_x || 0,
          position_y: instance.position_y || 0,
          alignment: instance.alignment || 'left',
          configuration: instance.configuration || {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }));
        
        setComponentInstances(componentInstances);
        alert(`已加载页面 "${pageDetail.title}"，包含 ${componentInstances.length} 个组件`);
      } else {
        // 清空组件实例
        setComponentInstances([]);
        alert(`已加载页面 "${pageDetail.title}" (无保存的组件)`);
      }
    } catch (error) {
      console.error('加载页面失败:', error);
      alert('加载页面失败，请检查控制台日志。');
    }
  };

  /**
   * 检查API健康状态
   */
  const checkApiHealth = async () => {
    setLoading(true);
    try {
      const isHealthy = await checkHealth();
      setApiHealth(isHealthy);
    } catch (error) {
      console.error('API健康检查失败:', error);
      setApiHealth(false);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 初始化时检查API状态
   */
  useEffect(() => {
    checkApiHealth();
  }, []);

  /**
   * 初始化时加载页面列表
   */
  useEffect(() => {
    if (apiHealth === true) {
      loadPages();
    }
  }, [apiHealth]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* 顶部应用栏 */}
      <AppBar
        position="static"
        color="default"
        elevation={0}
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Toolbar variant="dense">
          <Typography
            variant="h6"
            component="div"
            sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}
          >
            <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold', mr: 1 }}>
              WebBot
            </Box>
            组件编辑器
            <Chip
              label="Beta"
              size="small"
              color="primary"
              variant="outlined"
              sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
            />
            
            {/* 当前页面显示 */}
            {currentPageId && (
              <>
                <Box sx={{ mx: 1, color: 'text.secondary' }}>/</Box>
                <Chip
                  label={currentPageTitle || '未命名页面'}
                  size="small"
                  color="secondary"
                  variant="outlined"
                  sx={{ ml: 1, height: 24, fontSize: '0.75rem' }}
                />
              </>
            )}
          </Typography>

          {/* API状态指示器 */}
          {apiHealth !== null && (
            <Chip
              icon={
                loading ? <CircularProgress size={16} /> : apiHealth ? <Cloud /> : <BugReport />
              }
              label={loading ? '检查中...' : apiHealth ? 'API连接正常' : 'API连接失败'}
              color={loading ? 'default' : apiHealth ? 'success' : 'error'}
              size="small"
              variant="outlined"
              sx={{ mr: 2 }}
            />
          )}

          {/* 预览模式切换 */}
          <Button
            startIcon={previewMode ? <Edit /> : <Preview />}
            onClick={togglePreviewMode}
            variant={previewMode ? 'contained' : 'outlined'}
            color={previewMode ? 'primary' : 'inherit'}
            size="small"
            sx={{ mr: 1 }}
          >
            {previewMode ? '退出预览' : '预览模式'}
          </Button>

          {/* 页面管理分隔线 */}
          <Box sx={{ width: 1, height: 24, bgcolor: 'divider', mx: 1 }} />

          {/* 新建页面按钮 */}
          <Button
            startIcon={<Add />}
            onClick={handleNewPage}
            variant="outlined"
            color="inherit"
            size="small"
            sx={{ mr: 1 }}
            disabled={isLoadingPages || apiHealth !== true}
          >
            新建页面
          </Button>

          {/* 保存页面按钮 */}
          <Button
            startIcon={<Save />}
            onClick={handleSavePage}
            variant="outlined"
            color="inherit"
            size="small"
            sx={{ mr: 1 }}
            disabled={!currentPageId || isLoadingPages || apiHealth !== true}
          >
            保存页面
          </Button>

          {/* 页面选择下拉框 */}
          <Button
            startIcon={<FolderOpen />}
            variant="outlined"
            color="inherit"
            size="small"
            sx={{ mr: 1 }}
            disabled={pages.length === 0 || isLoadingPages || apiHealth !== true}
            onClick={handlePageMenuOpen}
            aria-controls="page-menu"
            aria-haspopup="true"
          >
            页面列表 ({pages.length})
          </Button>
          
          {/* 页面菜单 */}
          <Menu
            id="page-menu"
            anchorEl={pageMenuAnchor}
            open={Boolean(pageMenuAnchor)}
            onClose={handlePageMenuClose}
            PaperProps={{
              style: {
                maxHeight: 400,
                width: 300,
              },
            }}
          >
            {pages.length === 0 ? (
              <MenuItem disabled>暂无页面</MenuItem>
            ) : (
              pages.map(page => (
                <MenuItem key={page.id} onClick={() => handleSelectPage(page)}>
                  <ListItemText 
                    primary={page.title} 
                    secondary={`${page.id} • ${page.status}`}
                    primaryTypographyProps={{ noWrap: true }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </MenuItem>
              ))
            )}
          </Menu>

          {/* 刷新按钮 */}
          <IconButton size="small" onClick={checkApiHealth} title="刷新API状态">
            <Refresh fontSize="small" />
          </IconButton>

          {/* 设置按钮 */}
          <IconButton size="small" title="设置">
            <Settings fontSize="small" />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* 主体布局 */}
      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 左侧：组件库 - 固定宽度 */}
        <ComponentLibrary />
        
        {/* 中间：编辑器画布 - 占据剩余空间 */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <EditorCanvas />
        </Box>
      </Box>

      {/* 组件配置对话框 */}
      <ComponentConfigDialog />

      {/* 底部状态栏 */}
      <Box
        sx={{
          px: 2,
          py: 1,
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          bgcolor: 'grey.50',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          WET-BOEW 组件编辑器 | 专为加拿大政府网站设计
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="caption" color="text.secondary">
            后端: {apiHealth ? '在线' : '离线'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            版本: 0.1.0-alpha
          </Typography>
        </Box>
      </Box>

      {/* API连接失败提示 */}
      {apiHealth === false && (
        <Box
          sx={{
            position: 'fixed',
            bottom: 40,
            right: 16,
            bgcolor: 'error.main',
            color: 'white',
            p: 1.5,
            borderRadius: 1,
            boxShadow: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <BugReport fontSize="small" />
          <Typography variant="body2">
            WebBot API连接失败。请确保后端服务运行在 http://127.0.0.1:8000
          </Typography>
          <Button
            size="small"
            variant="contained"
            color="inherit"
            sx={{ ml: 1, color: 'error.main', bgcolor: 'white' }}
            onClick={checkApiHealth}
          >
            重试
          </Button>
        </Box>
      )}
    </Box>
  );
}

export default App;
