/**
 * 组件库侧边栏 - 简化版本
 */

import { Box, Typography, Paper, Chip, Divider, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { Category, DragIndicator } from '@mui/icons-material';

// 静态组件数据 - 匹配后端11个WET-BOEW组件
const staticComponents = [
  { id: 'wet-button-primary', name: '主要按钮', category: 'button', icon: '🔘', description: '加拿大政府标准主要按钮', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-input-text', name: '文本输入框', category: 'form', icon: '📝', description: '可访问性友好的文本输入框', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-title', name: '标题组件', category: 'content', icon: '🏷️', description: 'WET-BOEW标准标题', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-textarea', name: '文本区域', category: 'form', icon: '📄', description: '多行文本输入区域', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-feature-columns', name: '特征图片列', category: 'content', icon: '🖼️', description: '特征图片列组件', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-list', name: '列表组件', category: 'content', icon: '📋', description: 'WET-BOEW标准列表', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-embed-html', name: 'HTML嵌入', category: 'content', icon: '🌐', description: '嵌入自定义HTML代码', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-footnotes', name: '脚注组件', category: 'content', icon: '📌', description: '添加页面脚注', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-horizontal-line', name: '水平分割线', category: 'content', icon: '➖', description: '水平分割线组件', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-image', name: '图片组件', category: 'content', icon: '🖼️', description: '图片显示组件', tags: ['WET-BOEW', 'WCAG'] },
  { id: 'wet-button-secondary', name: '次要按钮', category: 'button', icon: '🔳', description: '加拿大政府标准次要按钮', tags: ['WET-BOEW', 'WCAG'] }
];

// 分类映射
const categoryMap: Record<string, string> = {
  'button': '按钮组件',
  'form': '表单组件', 
  'content': '内容组件',
  'navigation': '导航组件',
  'layout': '布局组件'
};

// 分类颜色
const categoryColors: Record<string, string> = {
  'button': '#1976d2',
  'form': '#d32f2f', 
  'content': '#388e3c',
  'navigation': '#7b1fa2',
  'layout': '#f57c00'
};

// 分类图标
const categoryIcons: Record<string, string> = {
  'button': '🔘',
  'form': '📝', 
  'content': '📄',
  'navigation': '🔗',
  'layout': '📦'
};

// 按分类分组
const componentsByCategory = staticComponents.reduce((acc, component) => {
  const category = component.category || 'content';
  if (!acc[category]) {
    acc[category] = [];
  }
  acc[category].push(component);
  return acc;
}, {} as Record<string, typeof staticComponents>);

const ComponentLibrary = () => {
  // 处理拖拽开始
  const handleDragStart = (event: React.DragEvent, componentId: string) => {
    event.dataTransfer.setData('text/plain', componentId);
    event.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <Box
      sx={{
        width: 240,
        height: '100vh',
        bgcolor: 'background.paper',
        borderRight: 1,
        borderColor: 'divider',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 标题栏 */}
      <Paper 
        elevation={0} 
        square 
        sx={{ 
          p: 2, 
          borderBottom: 1, 
          borderColor: 'divider',
          bgcolor: 'primary.main',
          color: 'white'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Category />
          <Typography variant="h6" component="div" sx={{ fontWeight: 'bold' }}>
            WET-BOEW 组件库
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)', mt: 0.5, display: 'block' }}>
          {staticComponents.length} 个可用组件
        </Typography>
      </Paper>

      {/* 组件列表 */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {Object.entries(componentsByCategory).map(([category, components]) => {
          const displayName = categoryMap[category] || category;
          const categoryColor = categoryColors[category] || '#757575';
          const categoryIcon = categoryIcons[category] || '📦';
          
          return (
            <Box key={category} sx={{ mb: 2 }}>
              {/* 分类标题 */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  p: 1,
                  borderRadius: 1,
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontSize: '1.2rem' }}>
                    {categoryIcon}
                  </Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: categoryColor }}>
                    {displayName}
                  </Typography>
                  <Chip 
                    label={components.length} 
                    size="small" 
                    sx={{ 
                      height: 20, 
                      fontSize: '0.7rem',
                      bgcolor: categoryColor,
                      color: 'white'
                    }}
                  />
                </Box>
              </Box>

              {/* 分类下的组件列表 */}
              <List dense disablePadding>
                {components.map((component) => (
                  <ListItem
                    key={component.id}
                    disablePadding
                    sx={{ 
                      mb: 0.5,
                      borderRadius: 1,
                      '&:hover': { 
                        bgcolor: 'action.hover',
                        transform: 'translateX(2px)',
                        transition: 'transform 0.1s'
                      },
                    }}
                    draggable
                    onDragStart={(e) => handleDragStart(e, component.id)}
                  >
                    <Paper
                      sx={{
                        width: '100%',
                        p: 1,
                        borderRadius: 1,
                        border: 1,
                        borderColor: 'divider',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        cursor: 'grab',
                        '&:active': { cursor: 'grabbing' },
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                        <DragIndicator 
                          fontSize="small" 
                          sx={{ 
                            color: 'text.secondary',
                            opacity: 0.6
                          }} 
                        />
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <Typography sx={{ fontSize: '1rem' }}>
                            {component.icon}
                          </Typography>
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                              {component.name}
                            </Typography>
                          }
                          secondaryTypographyProps={{ component: 'div' }}
                          secondary={
                            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
                              {component.tags.map(tag => (
                                <Chip 
                                  key={tag}
                                  label={tag} 
                                  size="small" 
                                  sx={{ 
                                    height: 16, 
                                    fontSize: '0.6rem',
                                    bgcolor: tag === 'WET-BOEW' ? 'primary.light' : 'success.light',
                                    color: tag === 'WET-BOEW' ? 'primary.contrastText' : 'success.contrastText'
                                  }}
                                />
                              ))}
                            </Box>
                          }
                        />
                      </Box>
                    </Paper>
                  </ListItem>
                ))}
              </List>
              <Divider sx={{ mt: 1 }} />
            </Box>
          );
        })}

        {/* 使用说明 */}
        <Paper 
          sx={{ 
            p: 2, 
            mt: 2, 
            bgcolor: 'info.light', 
            border: 1, 
            borderColor: 'info.main',
            borderRadius: 1
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 'medium', mb: 0.5 }}>
            如何使用？
          </Typography>
          <Typography variant="caption" color="text.secondary">
            1. 拖拽组件到"Drag components here"区域
            <br />
            2. 或点击区域添加组件
            <br />
            3. 双击组件进行配置
          </Typography>
        </Paper>
      </Box>

      {/* 底部信息 */}
      <Paper 
        elevation={0} 
        square 
        sx={{ 
          p: 1.5, 
          borderTop: 1, 
          borderColor: 'divider',
          bgcolor: 'grey.50',
          textAlign: 'center'
        }}
      >
        <Typography variant="caption" color="text.secondary">
          <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>
            WebBot Editor
          </Box>
          {' '}v0.1.0-alpha
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
          符合加拿大政府网页标准
        </Typography>
      </Paper>
    </Box>
  );
};

export default ComponentLibrary;