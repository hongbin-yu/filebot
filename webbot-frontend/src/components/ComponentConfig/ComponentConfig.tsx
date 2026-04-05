/**
 * 组件配置面板（包含预览功能）
 */

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Divider,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Slider,
  Select,
  MenuItem,
} from '@mui/material';
import { useEditorState } from '../../hooks/useEditorState';
import { useComponentInstances } from '../../hooks/useComponents';
import type { ListConfig } from '../../types/components';

interface ColumnData {
  title?: string;
  description?: string;
  imageUrl?: string;
  imageAlt?: string;
  [key: string]: string | undefined;
}

interface ComponentConfigProps {
  /**
   * 是否作为对话框内容渲染
   * 如果为true，则只渲染配置表单，不包含外部容器和标题
   */
  asDialogContent?: boolean;
}

const ComponentConfig: React.FC<ComponentConfigProps> = ({ asDialogContent = false }) => {
  const { selectedInstance, previewMode } = useEditorState();
  const { updateComponentConfig, updateComponentAlignment } = useComponentInstances();

  // 如果没有选中的组件，显示空状态
  if (!selectedInstance) {
    if (asDialogContent) {
      // 对话框模式下，返回简单的提示
      return (
        <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
          <Typography variant="body1" gutterBottom>
            未选择组件
          </Typography>
          <Typography variant="body2">点击画布上的组件进行选择和配置</Typography>
        </Box>
      );
    } else {
      // 侧边栏模式下，返回完整空状态
      return (
        <Box
          sx={{
            width: 320,
            height: '100vh',
            bgcolor: 'background.paper',
            borderLeft: 1,
            borderColor: 'divider',
          }}
        >
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">组件配置</Typography>
          </Box>
          <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
            <Typography variant="body1" gutterBottom>
              未选择组件
            </Typography>
            <Typography variant="body2">点击画布上的组件进行选择和配置</Typography>
          </Box>
        </Box>
      );
    }
  }

  /**
   * 处理配置更新
   */
  const handleConfigChange = (key: string, value: string | number | boolean) => {
    const newConfig = { ...selectedInstance.configuration, [key]: value };
    updateComponentConfig(selectedInstance.id, newConfig);
  };

  /**
   * 处理对齐方式更新
   */
  const handleAlignmentChange = (alignment: 'left' | 'center' | 'right') => {
    updateComponentAlignment(selectedInstance.id, alignment);
  };

  /**
   * 渲染配置字段
   */
  const renderConfigFields = () => {
    const config = selectedInstance.configuration || {};

    // 根据组件类型渲染不同的配置字段
    if (selectedInstance.template_id === 'wet-button-primary') {
      return (
        <>
          <TextField
            fullWidth
            label="按钮文本"
            value={config.label || '点击这里'}
            onChange={e => handleConfigChange('label', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <FormControl fullWidth margin="normal">
            <FormLabel>按钮大小</FormLabel>
            <Select
              value={config.size || 'medium'}
              onChange={e => handleConfigChange('size', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="small">小 (约150px)</MenuItem>
              <MenuItem value="medium">中 (约200px)</MenuItem>
              <MenuItem value="large">大 (约250px)</MenuItem>
              <MenuItem value="custom">自定义宽度</MenuItem>
            </Select>
          </FormControl>

          {/* 自定义宽度输入框 */}
          {(config.size === 'custom' || config.width) && (
            <TextField
              fullWidth
              label="自定义宽度 (px)"
              type="number"
              value={config.width || 200}
              onChange={e => handleConfigChange('width', parseInt(e.target.value) || 200)}
              margin="normal"
              disabled={previewMode}
              InputProps={{
                inputProps: {
                  min: 50,
                  max: 800,
                  step: 10,
                },
              }}
              helperText="输入50-800之间的像素值"
            />
          )}

          <FormControl fullWidth margin="normal">
            <FormLabel>按钮变体</FormLabel>
            <Select
              value={config.variant || 'primary'}
              onChange={e => handleConfigChange('variant', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="primary">主要</MenuItem>
              <MenuItem value="secondary">次要</MenuItem>
              <MenuItem value="success">成功</MenuItem>
              <MenuItem value="danger">危险</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="按钮动作 (URL)"
            value={config.action || ''}
            onChange={e => handleConfigChange('action', e.target.value)}
            margin="normal"
            disabled={previewMode}
            placeholder="https://example.com"
            helperText="输入按钮点击后跳转的URL地址"
          />
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.disabled || false}
                  onChange={e => handleConfigChange('disabled', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="禁用状态"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.block || false}
                  onChange={e => handleConfigChange('block', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="块级显示"
            />
          </FormGroup>
        </>
      );
    }

    if (selectedInstance.template_id === 'wet-input-text') {
      return (
        <>
          <TextField
            fullWidth
            label="字段标签"
            value={config.label || '输入框'}
            onChange={e => handleConfigChange('label', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <TextField
            fullWidth
            label="占位符文本"
            value={config.placeholder || '请输入内容...'}
            onChange={e => handleConfigChange('placeholder', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <TextField
            fullWidth
            label="字段ID"
            value={config.id || `input-${selectedInstance.id.slice(0, 4)}`}
            onChange={e => handleConfigChange('id', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <TextField
            fullWidth
            label="字段名称"
            value={config.name || `field_${selectedInstance.id.slice(0, 4)}`}
            onChange={e => handleConfigChange('name', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <FormControl fullWidth margin="normal">
            <FormLabel>输入类型</FormLabel>
            <Select
              value={config.type || 'text'}
              onChange={e => handleConfigChange('type', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="text">文本</MenuItem>
              <MenuItem value="email">邮箱</MenuItem>
              <MenuItem value="password">密码</MenuItem>
              <MenuItem value="number">数字</MenuItem>
              <MenuItem value="tel">电话</MenuItem>
            </Select>
          </FormControl>

          {/* 宽度控制 */}
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 2 }}>
            <TextField
              fullWidth
              label="宽度 (px)"
              type="number"
              value={config.width || 200}
              onChange={e => handleConfigChange('width', parseInt(e.target.value) || 200)}
              margin="normal"
              disabled={previewMode}
              InputProps={{
                inputProps: {
                  min: 100,
                  max: 600,
                  step: 10,
                },
              }}
              helperText="输入框宽度"
            />
            <FormControl fullWidth margin="normal">
              <FormLabel>尺寸模式</FormLabel>
              <Select
                value={config.sizeMode || 'fixed'}
                onChange={e => handleConfigChange('sizeMode', e.target.value)}
                disabled={previewMode}
                size="small"
              >
                <MenuItem value="fixed">固定宽度</MenuItem>
                <MenuItem value="full">全宽</MenuItem>
                <MenuItem value="auto">自动宽度</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.required || false}
                  onChange={e => handleConfigChange('required', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="必填字段"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.disabled || false}
                  onChange={e => handleConfigChange('disabled', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="禁用状态"
            />
          </FormGroup>
        </>
      );
    }

    if (selectedInstance.template_id === 'wet-title') {
      return (
        <>
          <TextField
            fullWidth
            label="标题文本"
            value={config.text || '这是一个标题'}
            onChange={e => handleConfigChange('text', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <FormControl fullWidth margin="normal">
            <FormLabel>标题级别</FormLabel>
            <Select
              value={config.level || 'h2'}
              onChange={e => handleConfigChange('level', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="h1">H1 (一级标题)</MenuItem>
              <MenuItem value="h2">H2 (二级标题)</MenuItem>
              <MenuItem value="h3">H3 (三级标题)</MenuItem>
              <MenuItem value="h4">H4 (四级标题)</MenuItem>
              <MenuItem value="h5">H5 (五级标题)</MenuItem>
              <MenuItem value="h6">H6 (六级标题)</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <FormLabel>对齐方式</FormLabel>
            <Select
              value={config.align || 'left'}
              onChange={e => handleConfigChange('align', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="left">左对齐</MenuItem>
              <MenuItem value="center">居中对齐</MenuItem>
              <MenuItem value="right">右对齐</MenuItem>
              <MenuItem value="justify">两端对齐</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <FormLabel>显示大小</FormLabel>
            <Select
              value={config.size || 'medium'}
              onChange={e => handleConfigChange('size', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="small">小</MenuItem>
              <MenuItem value="medium">中</MenuItem>
              <MenuItem value="large">大</MenuItem>
              <MenuItem value="x-large">特大</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="CSS类名"
            value={config.className || ''}
            onChange={e => handleConfigChange('className', e.target.value)}
            margin="normal"
            disabled={previewMode}
            placeholder="例如: page-title, section-header"
            helperText="可选的CSS类名，用于自定义样式"
          />
        </>
      );
    }

    if (selectedInstance.template_id === 'wet-textarea') {
      return (
        <>
          <TextField
            fullWidth
            label="字段标签"
            value={config.label || '内容编辑'}
            onChange={e => handleConfigChange('label', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <TextField
            fullWidth
            label="占位符文本"
            value={config.placeholder || '请输入内容...'}
            onChange={e => handleConfigChange('placeholder', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <TextField
            fullWidth
            label="字段ID"
            value={config.id || `textarea-${selectedInstance.id.slice(0, 4)}`}
            onChange={e => handleConfigChange('id', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <TextField
            fullWidth
            label="字段名称"
            value={config.name || `textarea_${selectedInstance.id.slice(0, 4)}`}
            onChange={e => handleConfigChange('name', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              fullWidth
              label="行数"
              type="number"
              value={config.rows || 5}
              onChange={e => handleConfigChange('rows', parseInt(e.target.value) || 5)}
              margin="normal"
              disabled={previewMode}
              InputProps={{
                inputProps: {
                  min: 1,
                  max: 20,
                  step: 1,
                },
              }}
            />
            <TextField
              fullWidth
              label="列数"
              type="number"
              value={config.cols || 50}
              onChange={e => handleConfigChange('cols', parseInt(e.target.value) || 50)}
              margin="normal"
              disabled={previewMode}
              InputProps={{
                inputProps: {
                  min: 10,
                  max: 200,
                  step: 5,
                },
              }}
            />
          </Box>
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.required || false}
                  onChange={e => handleConfigChange('required', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="必填字段"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.disabled || false}
                  onChange={e => handleConfigChange('disabled', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="禁用状态"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.readonly || false}
                  onChange={e => handleConfigChange('readonly', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="只读模式"
            />
          </FormGroup>
        </>
      );
    }

    if (selectedInstance.template_id === 'wet-feature-columns') {
      // 解析列数据
      const columns = config.columns
        ? typeof config.columns === 'string'
          ? JSON.parse(config.columns)
          : config.columns
        : [];
      const columnSize = config.columnSize || '4';

      const handleColumnsChange = (newColumns: ColumnData[]) => {
        handleConfigChange('columns', JSON.stringify(newColumns));
      };

      const addColumn = () => {
        const newColumns = [
          ...columns,
          { title: `列 ${columns.length + 1}`, description: '', imageUrl: '' },
        ];
        handleColumnsChange(newColumns);
      };

      const removeColumn = (index: number) => {
        const newColumns = [...columns];
        newColumns.splice(index, 1);
        handleColumnsChange(newColumns);
      };

      const updateColumn = (index: number, field: string, value: string) => {
        const newColumns = [...columns];
        if (!newColumns[index]) newColumns[index] = {};
        newColumns[index][field] = value;
        handleColumnsChange(newColumns);
      };

      return (
        <>
          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}
          >
            <Typography variant="subtitle2">列配置</Typography>
            <Button size="small" onClick={addColumn} disabled={previewMode}>
              添加列
            </Button>
          </Box>

          {columns.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              暂无列数据，点击"添加列"开始配置
            </Typography>
          ) : (
            <>
              {columns.map((column: ColumnData, index: number) => (
                <Paper key={index} sx={{ p: 2, mb: 2, border: '1px solid #eee' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mb: 1,
                    }}
                  >
                    <Typography variant="subtitle2">列 {index + 1}</Typography>
                    <Button
                      size="small"
                      color="error"
                      onClick={() => removeColumn(index)}
                      disabled={previewMode || columns.length <= 1}
                    >
                      删除
                    </Button>
                  </Box>
                  <TextField
                    fullWidth
                    label="标题"
                    value={column.title || ''}
                    onChange={e => updateColumn(index, 'title', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                  />
                  <TextField
                    fullWidth
                    label="描述"
                    value={column.description || ''}
                    onChange={e => updateColumn(index, 'description', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                    multiline
                    rows={2}
                  />
                  <TextField
                    fullWidth
                    label="图片URL"
                    value={column.imageUrl || ''}
                    onChange={e => updateColumn(index, 'imageUrl', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                    placeholder="https://example.com/image.jpg"
                  />
                  <TextField
                    fullWidth
                    label="图片替代文本"
                    value={column.imageAlt || ''}
                    onChange={e => updateColumn(index, 'imageAlt', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                    placeholder="图片描述"
                  />
                </Paper>
              ))}
            </>
          )}

          <FormControl fullWidth margin="normal">
            <FormLabel>每列宽度</FormLabel>
            <Select
              value={columnSize}
              onChange={e => handleConfigChange('columnSize', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="2">2/12 (窄)</MenuItem>
              <MenuItem value="3">3/12</MenuItem>
              <MenuItem value="4">4/12 (默认)</MenuItem>
              <MenuItem value="6">6/12 (半宽)</MenuItem>
              <MenuItem value="12">12/12 (全宽)</MenuItem>
            </Select>
            <Typography variant="caption" color="text.secondary">
              Bootstrap网格系统: 每列占用的列数 (总共12列)
            </Typography>
          </FormControl>

          <TextField
            fullWidth
            label="CSS类名"
            value={config.className || ''}
            onChange={e => handleConfigChange('className', e.target.value)}
            margin="normal"
            disabled={previewMode}
            helperText="额外的CSS类名"
          />
        </>
      );
    }

    if (selectedInstance.template_id === 'wet-list') {
      // 列表配置
      const items: Array<{ text: string; description?: string; linkUrl?: string }> = 
        config.items && Array.isArray(config.items) ? config.items : [];
      
      const handleItemsChange = (newItems: typeof items) => {
        handleConfigChange('items', newItems);
      };

      const addItem = () => {
        const newItems = [...items, { text: `列表项 ${items.length + 1}` }];
        handleItemsChange(newItems);
      };

      const removeItem = (index: number) => {
        const newItems = [...items];
        newItems.splice(index, 1);
        handleItemsChange(newItems);
      };

      const updateItem = (index: number, field: string, value: string) => {
        const newItems = [...items];
        if (!newItems[index]) newItems[index] = { text: '' };
        newItems[index][field] = value;
        handleItemsChange(newItems);
      };

      return (
        <>
          <TextField
            fullWidth
            label="列表标题"
            value={config.title || ''}
            onChange={e => handleConfigChange('title', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
          <FormControl fullWidth margin="normal">
            <FormLabel>列表类型</FormLabel>
            <Select
              value={config.type || 'unordered'}
              onChange={e => handleConfigChange('type', e.target.value)}
              disabled={previewMode}
            >
              <MenuItem value="unordered">无序列表 (项目符号)</MenuItem>
              <MenuItem value="ordered">有序列表 (数字编号)</MenuItem>
              <MenuItem value="description">描述列表 (术语定义)</MenuItem>
            </Select>
          </FormControl>

          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, mt: 3 }}
          >
            <Typography variant="subtitle2">列表项</Typography>
            <Button size="small" onClick={addItem} disabled={previewMode}>
              添加项
            </Button>
          </Box>

          {items.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              暂无列表项，点击"添加项"开始配置
            </Typography>
          ) : (
            <>
              {items.map((item, index) => (
                <Paper key={index} sx={{ p: 2, mb: 2, border: '1px solid #eee' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mb: 1,
                    }}
                  >
                    <Typography variant="subtitle2">项 {index + 1}</Typography>
                    <Button
                      size="small"
                      color="error"
                      onClick={() => removeItem(index)}
                      disabled={previewMode || items.length <= 1}
                    >
                      删除
                    </Button>
                  </Box>
                  <TextField
                    fullWidth
                    label="项目文本"
                    value={item.text || ''}
                    onChange={e => updateItem(index, 'text', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                    required
                  />
                  <TextField
                    fullWidth
                    label="描述 (用于描述列表)"
                    value={item.description || ''}
                    onChange={e => updateItem(index, 'description', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                    multiline
                    rows={2}
                  />
                  <TextField
                    fullWidth
                    label="链接URL (可选)"
                    value={item.linkUrl || ''}
                    onChange={e => updateItem(index, 'linkUrl', e.target.value)}
                    margin="dense"
                    disabled={previewMode}
                    placeholder="https://example.com"
                  />
                </Paper>
              ))}
            </>
          )}

          <FormControl fullWidth margin="normal">
            <FormLabel>起始编号 (有序列表)</FormLabel>
            <TextField
              type="number"
              value={config.start || 1}
              onChange={e => handleConfigChange('start', parseInt(e.target.value) || 1)}
              disabled={previewMode || config.type !== 'ordered'}
              InputProps={{
                inputProps: {
                  min: 1,
                  max: 100,
                },
              }}
              helperText="仅有序列表有效"
            />
          </FormControl>

          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.showBullets !== false}
                  onChange={e => handleConfigChange('showBullets', e.target.checked)}
                  disabled={previewMode || config.type !== 'unordered'}
                />
              }
              label="显示项目符号"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.showNumbers !== false}
                  onChange={e => handleConfigChange('showNumbers', e.target.checked)}
                  disabled={previewMode || config.type !== 'ordered'}
                />
              }
              label="显示编号"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!config.compact}
                  onChange={e => handleConfigChange('compact', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="紧凑显示"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!config.sortable}
                  onChange={e => handleConfigChange('sortable', e.target.checked)}
                  disabled={previewMode}
                />
              }
              label="可排序"
            />
          </FormGroup>

          <TextField
            fullWidth
            label="最大显示项数"
            type="number"
            value={config.maxItems || 0}
            onChange={e => handleConfigChange('maxItems', parseInt(e.target.value) || 0)}
            margin="normal"
            disabled={previewMode}
            InputProps={{
              inputProps: {
                min: 0,
                max: 100,
              },
            }}
            helperText="0表示无限制"
          />

          <TextField
            fullWidth
            label="CSS类名"
            value={config.className || ''}
            onChange={e => handleConfigChange('className', e.target.value)}
            margin="normal"
            disabled={previewMode}
          />
        </>
      );
    }

    // 默认配置字段
    return (
      <>
        <TextField
          fullWidth
          label="组件标识"
          value={config.id || selectedInstance.id}
          onChange={e => handleConfigChange('id', e.target.value)}
          margin="normal"
          disabled={previewMode}
        />
        <TextField
          fullWidth
          label="CSS类名"
          value={config.className || ''}
          onChange={e => handleConfigChange('className', e.target.value)}
          margin="normal"
          disabled={previewMode}
        />

        {/* 宽度控制 - 所有组件通用 */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            fullWidth
            label="宽度 (px)"
            type="number"
            value={
              config.width || (config.size === 'small' ? 150 : config.size === 'large' ? 250 : 200)
            }
            onChange={e => handleConfigChange('width', parseInt(e.target.value) || 200)}
            margin="normal"
            disabled={previewMode}
            InputProps={{
              inputProps: {
                min: 50,
                max: 800,
                step: 10,
              },
            }}
            helperText="组件宽度"
          />
          <FormControl fullWidth margin="normal">
            <FormLabel>尺寸</FormLabel>
            <Select
              value={config.size || 'medium'}
              onChange={e => handleConfigChange('size', e.target.value)}
              disabled={previewMode}
              size="small"
            >
              <MenuItem value="small">小</MenuItem>
              <MenuItem value="medium">中</MenuItem>
              <MenuItem value="large">大</MenuItem>
              <MenuItem value="custom">自定义</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <FormControl fullWidth margin="normal">
          <FormLabel>可见性</FormLabel>
          <Select
            value={config.visibility || 'visible'}
            onChange={e => handleConfigChange('visibility', e.target.value)}
            disabled={previewMode}
          >
            <MenuItem value="visible">可见</MenuItem>
            <MenuItem value="hidden">隐藏</MenuItem>
            <MenuItem value="conditional">条件显示</MenuItem>
          </Select>
        </FormControl>
        <Box sx={{ mt: 2 }}>
          <FormLabel>透明度</FormLabel>
          <Slider
            value={config.opacity !== undefined ? config.opacity * 100 : 100}
            onChange={(_, value) => handleConfigChange('opacity', (value as number) / 100)}
            valueLabelDisplay="auto"
            min={0}
            max={100}
            disabled={previewMode}
          />
        </Box>
      </>
    );
  };

  // 渲染配置表单内容（不含外部容器）
  const renderConfigForm = () => (
    <>
      <Typography variant="subtitle2" gutterBottom sx={{ mt: 1 }}>
        基本属性
      </Typography>
      {renderConfigFields()}

      <Divider sx={{ my: 3 }} />

      <Typography variant="subtitle2" gutterBottom>
        对齐方式
      </Typography>
      <FormControl fullWidth margin="normal">
        <FormLabel>选择对齐</FormLabel>
        <Select
          value={selectedInstance.alignment || 'left'}
          onChange={e => handleAlignmentChange(e.target.value as 'left' | 'center' | 'right')}
          disabled={previewMode}
        >
          <MenuItem value="left">左对齐</MenuItem>
          <MenuItem value="center">居中对齐</MenuItem>
          <MenuItem value="right">右对齐</MenuItem>
        </Select>
      </FormControl>

      <Divider sx={{ my: 3 }} />

      <Typography variant="subtitle2" gutterBottom>
        高级选项
      </Typography>
      <FormGroup>
        <FormControlLabel
          control={<Checkbox checked={false} disabled={previewMode} />}
          label="响应式布局"
        />
        <FormControlLabel
          control={<Checkbox checked={false} disabled={previewMode} />}
          label="可访问性支持"
        />
        <FormControlLabel
          control={<Checkbox checked={false} disabled={previewMode} />}
          label="移动端优化"
        />
      </FormGroup>

      {previewMode && (
        <Box sx={{ mt: 3, p: 2, bgcolor: 'warning.50', borderRadius: 1 }}>
          <Typography variant="caption" color="warning.main">
            预览模式 - 配置只读
          </Typography>
        </Box>
      )}
    </>
  );

  // 渲染操作按钮
  const renderActionButtons = () => (
    <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
      <Button fullWidth variant="contained" color="primary" disabled={previewMode} sx={{ mb: 1 }}>
        保存配置
      </Button>
      <Button fullWidth variant="outlined" color="inherit" disabled={previewMode}>
        重置为默认
      </Button>
    </Box>
  );

  // 如果作为对话框内容渲染
  if (asDialogContent) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, overflow: 'auto', flex: 1 }}>{renderConfigForm()}</Box>
        {renderActionButtons()}
      </Box>
    );
  }

  // 否则渲染为侧边栏（保持向后兼容）
  return (
    <Box
      sx={{
        width: 320,
        height: '100vh',
        bgcolor: 'background.paper',
        borderLeft: 1,
        borderColor: 'divider',
      }}
    >
      {/* 标题栏 */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: selectedInstance ? 'primary.50' : 'background.paper',
        }}
      >
        <Typography variant="h6" gutterBottom>
          组件配置
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {selectedInstance.template_id}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          实例ID: {selectedInstance.id.slice(0, 8)}...
        </Typography>
      </Paper>

      {/* 配置表单 */}
      <Box sx={{ p: 2, overflow: 'auto', height: 'calc(100vh - 180px)' }}>{renderConfigForm()}</Box>

      {/* 操作按钮 */}
      {renderActionButtons()}
    </Box>
  );
};

export default ComponentConfig;
