/**
 * 画布上的单个组件实例
 */

import React, { useState, useRef } from 'react';
import { Box, Paper, IconButton, Typography } from '@mui/material';
import { Delete, Edit, DragHandle } from '@mui/icons-material';
import type { ComponentInstance } from '../../services/api';
import { useComponentInstances } from '../../hooks/useComponents';
import { useEditorState } from '../../hooks/useEditorState';
import { useEditorStore } from '../../stores/editorStore';
import type { ButtonConfig, InputConfig, TitleConfig, ListConfig } from '../../types/components';
import { generateButtonAccessibility, generateInputAccessibility, generateListAccessibility } from '../../types/components';

interface CanvasComponentProps {
  instance: ComponentInstance;
  previewMode: boolean;
}

const CanvasComponent: React.FC<CanvasComponentProps> = ({ instance, previewMode }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const {
    updateComponentPosition,
    deleteComponentInstance,
    selectInstance,
    selectedInstanceId,
    updateComponentAlignment,
  } = useComponentInstances();

  const { openConfigDialog } = useEditorState();
  const { canvasWidth } = useEditorStore();

  const isSelected = selectedInstanceId === instance.id;

  // 计算组件宽度
  const getComponentWidth = () => {
    const config = instance.configuration || {};

    // 如果有自定义宽度，使用自定义宽度
    if (config.width && typeof config.width === 'number') {
      return config.width;
    }

    // 根据size属性决定宽度
    const size = config.size || 'medium';
    switch (size) {
      case 'small':
        return 150; // 小尺寸
      case 'large':
        return 250; // 大尺寸
      case 'medium':
      default:
        return 200; // 中尺寸（默认）
    }
  };

  const componentWidth = getComponentWidth();

  // 计算组件位置
  const getComponentPosition = () => {
    // 如果有对齐方式，使用对齐方式计算位置
    if (instance.alignment) {
      switch (instance.alignment) {
        case 'left':
          return { left: 0, top: instance.position_y };
        case 'center':
          return { left: (canvasWidth - componentWidth) / 2, top: instance.position_y };
        case 'right':
          return { left: canvasWidth - componentWidth, top: instance.position_y };
        default:
          return { left: instance.position_x, top: instance.position_y };
      }
    }

    // 没有对齐方式，使用坐标位置
    return { left: instance.position_x, top: instance.position_y };
  };

  const position = getComponentPosition();

  // 根据x坐标计算对齐方式
  const calculateAlignmentFromX = (x: number): 'left' | 'center' | 'right' => {
    const leftZone = canvasWidth * 0.33;
    const centerZone = canvasWidth * 0.66;

    if (x < leftZone) return 'left';
    if (x < centerZone) return 'center';
    return 'right';
  };

  // 根据对齐方式计算x坐标
  const calculateXFromAlignment = (alignment: 'left' | 'center' | 'right'): number => {
    switch (alignment) {
      case 'left':
        return 0;
      case 'center':
        return (canvasWidth - componentWidth) / 2;
      case 'right':
        return canvasWidth - componentWidth;
    }
  };

  // 拖拽状态引用
  const dragStateRef = useRef({
    startX: 0,
    startY: 0,
    startPosX: instance.position_x,
    startPosY: instance.position_y,
    isDragging: false,
  });

  /**
   * 处理鼠标按下开始拖拽
   */
  const handleMouseDown = (event: React.MouseEvent) => {
    if (previewMode) return;

    event.stopPropagation();
    selectInstance(instance.id);
    setIsDragging(true);

    // 获取当前实际位置（基于对齐方式或坐标）
    const currentX = instance.alignment
      ? calculateXFromAlignment(instance.alignment)
      : instance.position_x;
    const currentY = instance.position_y;

    dragStateRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startPosX: currentX,
      startPosY: currentY,
      isDragging: true,
    };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!dragStateRef.current.isDragging) return;

      const deltaX = moveEvent.clientX - dragStateRef.current.startX;
      const deltaY = moveEvent.clientY - dragStateRef.current.startY;
      const newX = Math.max(
        0,
        Math.min(canvasWidth - componentWidth, dragStateRef.current.startPosX + deltaX)
      );
      const newY = Math.max(0, dragStateRef.current.startPosY + deltaY);

      // 拖拽过程中暂时使用坐标位置
      updateComponentPosition(instance.id, newX, newY);
    };

    const handleMouseUp = () => {
      if (!dragStateRef.current.isDragging) return;

      dragStateRef.current.isDragging = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      setIsDragging(false);

      // 计算最终位置
      const currentX = instance.position_x;
      const alignment = calculateAlignmentFromX(currentX);

      // 更新对齐方式
      updateComponentAlignment(instance.id, alignment);

      // 计算对齐后的精确位置
      const alignedX = calculateXFromAlignment(alignment);
      updateComponentPosition(instance.id, alignedX, instance.position_y);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  /**
   * 处理组件点击
   */
  const handleClick = (event: React.MouseEvent) => {
    event.stopPropagation();
    selectInstance(instance.id);
    openConfigDialog(); // 打开配置对话框
  };

  /**
   * 处理删除组件
   */
  const handleDelete = (event: React.MouseEvent) => {
    event.stopPropagation();
    deleteComponentInstance(instance.id);
  };

  /**
   * 渲染组件预览
   */
  const renderComponentPreview = () => {
    const config = instance.configuration || {};

    // 根据模板类型渲染不同的预览
    if (instance.template_id === 'wet-button-primary') {
      // 类型安全的按钮配置
      const buttonConfig: ButtonConfig = {
        label: typeof config.label === 'string' ? config.label : '点击这里',
        action: typeof config.action === 'string' ? config.action : undefined,
        size:
          config.size === 'small' || config.size === 'medium' || config.size === 'large'
            ? config.size
            : 'medium',
        variant:
          config.variant === 'primary' ||
          config.variant === 'secondary' ||
          config.variant === 'success' ||
          config.variant === 'danger' ||
          config.variant === 'warning' ||
          config.variant === 'info' ||
          config.variant === 'light' ||
          config.variant === 'dark'
            ? config.variant
            : 'primary',
        disabled: typeof config.disabled === 'boolean' ? config.disabled : false,
        block: typeof config.block === 'boolean' ? config.block : false,
        className: typeof config.className === 'string' ? config.className : undefined,
      };

      const { label, action, size, variant, disabled, block } = buttonConfig;

      // 生成可访问性属性 (WCAG 2.1 AA 标准)
      const accessibilityProps = generateButtonAccessibility(buttonConfig, {
        ariaLabel: label,
        ariaDisabled: disabled,
      });

      const sizeStyles = {
        small: { fontSize: '0.75rem', padding: '4px 12px', minHeight: '32px' },
        medium: { fontSize: '0.875rem', padding: '8px 16px', minHeight: '40px' },
        large: { fontSize: '1rem', padding: '12px 24px', minHeight: '48px' },
      };

      const variantStyles = {
        primary: { backgroundColor: '#007bff', color: 'white' },
        secondary: { backgroundColor: '#6c757d', color: 'white' },
        success: { backgroundColor: '#28a745', color: 'white' },
        danger: { backgroundColor: '#dc3545', color: 'white' },
        warning: { backgroundColor: '#ffc107', color: '#212529' },
        info: { backgroundColor: '#17a2b8', color: 'white' },
        light: { backgroundColor: '#f8f9fa', color: '#212529', border: '1px solid #dee2e6' },
        dark: { backgroundColor: '#343a40', color: 'white' },
      };

      // 键盘事件处理 (在预览模式下仍保持可访问性)
      const handleKeyDown = (event: React.KeyboardEvent) => {
        if (disabled) return;

        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          if (action) {
            window.open(action, '_blank');
          }
        }

        // 可选的: 在预览中触发选择组件
        if (event.key === 'Enter') {
          selectInstance(instance.id);
        }
      };

      return (
        <Box
          className={instance.template_id}
          sx={{
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
          }}
        >
          <Box
            component="div" // 明确使用div，但添加button角色
            {...accessibilityProps}
            onKeyDown={handleKeyDown}
            onClick={() => {
              if (disabled) return;
              if (action) {
                window.open(action, '_blank');
              }
              // 在编辑器中，点击组件会选中它
              if (!previewMode) {
                selectInstance(instance.id);
              }
            }}
            sx={{
              ...sizeStyles[size],
              ...variantStyles[variant],
              borderRadius: '4px',
              border: 'none',
              cursor: disabled ? 'not-allowed' : 'pointer',
              textAlign: 'center',
              width: block ? '100%' : 'auto',
              opacity: disabled ? 0.65 : 1,
              fontWeight: 'bold',
              outline: 'none',
              '&:focus-visible': {
                outline: '2px solid #007bff',
                outlineOffset: '2px',
              },
              '&:hover': !disabled
                ? {
                    filter: 'brightness(0.9)',
                  }
                : {},
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              userSelect: 'none',
            }}
          >
            {label}
            {action && ' →'}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            按钮组件{action && ' (链接)'}
            {disabled && ' (已禁用)'}
          </Typography>
        </Box>
      );
    }

    if (instance.template_id === 'wet-input-text') {
      // 类型安全的输入框配置
      const inputConfig: InputConfig = {
        label: typeof config.label === 'string' ? config.label : '输入框',
        placeholder: typeof config.placeholder === 'string' ? config.placeholder : '请输入内容...',
        type:
          config.type === 'text' ||
          config.type === 'email' ||
          config.type === 'password' ||
          config.type === 'number' ||
          config.type === 'tel' ||
          config.type === 'url' ||
          config.type === 'search' ||
          config.type === 'date' ||
          config.type === 'time'
            ? config.type
            : 'text',
        required: typeof config.required === 'boolean' ? config.required : false,
        disabled: typeof config.disabled === 'boolean' ? config.disabled : false,
        id: `input-${instance.id}`,
        name: typeof config.name === 'string' ? config.name : `input-${instance.id}`,
      };

      const { label, placeholder, type, required, disabled } = inputConfig;

      // 生成可访问性属性
      const accessibilityProps = generateInputAccessibility(inputConfig, {
        ariaLabel: label,
        ariaRequired: required,
        ariaDisabled: disabled,
      });

      return (
        <Box
          className={instance.template_id}
          sx={{
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}
          role="group"
          aria-labelledby={`label-${instance.id}`}
        >
          <Typography
            variant="body2"
            fontWeight="medium"
            gutterBottom
            id={`label-${instance.id}`}
            component="label"
            htmlFor={`input-${instance.id}`}
          >
            {label}
            {required && <span aria-hidden="true"> *</span>}
          </Typography>
          <Box
            component="div"
            {...accessibilityProps}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (disabled) return;
              // 模拟输入框的键盘交互
              if (e.key === 'Enter' && !previewMode) {
                selectInstance(instance.id);
              }
            }}
            onClick={() => {
              if (disabled) return;
              if (!previewMode) {
                selectInstance(instance.id);
              }
            }}
            sx={{
              border: '1px solid #ced4da',
              borderRadius: '4px',
              padding: '8px 12px',
              backgroundColor: disabled ? '#e9ecef' : 'white',
              color: disabled ? '#6c757d' : 'inherit',
              fontSize: '0.875rem',
              width: '100%',
              boxSizing: 'border-box',
              cursor: disabled ? 'not-allowed' : 'text',
              outline: 'none',
              '&:focus-visible': {
                borderColor: '#007bff',
                boxShadow: '0 0 0 2px rgba(0,123,255,0.25)',
              },
              '&:hover': !disabled
                ? {
                    borderColor: '#80bdff',
                  }
                : {},
              minHeight: '40px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {placeholder}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            {type} 输入框{disabled && ' (已禁用)'}
            {required && ' (必填)'}
          </Typography>
        </Box>
      );
    }

    if (instance.template_id === 'wet-title') {
      // 类型安全的标题配置
      const titleConfig: TitleConfig = {
        text: typeof config.text === 'string' ? config.text : '这是一个标题',
        level:
          config.level === 1 ||
          config.level === 2 ||
          config.level === 3 ||
          config.level === 4 ||
          config.level === 5 ||
          config.level === 6
            ? config.level
            : 2,
        align:
          config.align === 'left' ||
          config.align === 'center' ||
          config.align === 'right' ||
          config.align === 'justify'
            ? config.align
            : 'left',
        size:
          config.size === 'small' ||
          config.size === 'medium' ||
          config.size === 'large' ||
          config.size === 'xlarge'
            ? config.size
            : 'medium',
      };

      const { text, level, align, size } = titleConfig;

      // 标题元素映射
      const HeadingComponent = `h${level}` as keyof JSX.IntrinsicElements;

      const sizeStyles = {
        small: { fontSize: '1rem', fontWeight: 600 },
        medium: { fontSize: '1.5rem', fontWeight: 700 },
        large: { fontSize: '2rem', fontWeight: 800 },
        xlarge: { fontSize: '2.5rem', fontWeight: 900 },
      };

      const alignStyles = {
        left: { textAlign: 'left' },
        center: { textAlign: 'center' },
        right: { textAlign: 'right' },
        justify: { textAlign: 'justify' },
      };

      return (
        <Box
          className={instance.template_id}
          sx={{
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            width: '100%',
          }}
        >
          <HeadingComponent
            style={{
              ...sizeStyles[size],
              ...alignStyles[align],
              width: '100%',
              lineHeight: 1.2,
              color: '#212529',
              margin: 0,
              padding: 0,
            }}
            id={`title-${instance.id}`}
            tabIndex={0} // 允许标题通过键盘聚焦 (用于可访问性)
            onClick={() => {
              if (!previewMode) {
                selectInstance(instance.id);
              }
            }}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (e.key === 'Enter' && !previewMode) {
                selectInstance(instance.id);
              }
            }}
            aria-label={text}
          >
            {text}
          </HeadingComponent>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            H{level} 标题
          </Typography>
        </Box>
      );
    }

    if (instance.template_id === 'wet-textarea') {
      const label = config.label || '内容编辑';
      const placeholder = config.placeholder || '请输入内容...';
      const rows = config.rows || 5;
      const cols = config.cols || 50;
      const disabled = config.disabled || false;
      const readonly = config.readonly || false;

      // 根据行数计算高度
      const rowHeight = 24;
      const textareaHeight = rows * rowHeight + 40;

      return (
        <Box
          sx={{
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}
        >
          <Typography variant="body2" fontWeight="medium" gutterBottom>
            {label}
          </Typography>
          <Box
            sx={{
              border: '1px solid #ced4da',
              borderRadius: '4px',
              padding: '8px 12px',
              backgroundColor: disabled ? '#e9ecef' : 'white',
              color: disabled ? '#6c757d' : 'inherit',
              fontSize: '0.875rem',
              width: '100%',
              height: `${textareaHeight}px`,
              overflow: 'hidden',
              boxSizing: 'border-box',
              opacity: readonly ? 0.7 : 1,
              cursor: disabled ? 'not-allowed' : 'text',
            }}
          >
            {placeholder}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            富文本编辑器 ({rows}行 × {cols}列)
          </Typography>
        </Box>
      );
    }

    if (instance.template_id === 'wet-feature-columns') {
      const columns = config.columns
        ? typeof config.columns === 'string'
          ? JSON.parse(config.columns)
          : config.columns
        : [];
      const columnSize = config.columnSize || '4';

      // 计算列数
      const columnCount = Array.isArray(columns) ? columns.length : 0;

      return (
        <Box
          sx={{
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}
        >
          <Typography variant="body2" fontWeight="medium" gutterBottom>
            特征图片列
          </Typography>
          <Box
            sx={{
              display: 'flex',
              gap: 1,
              width: '100%',
              height: '100%',
              alignItems: 'stretch',
            }}
          >
            {Array.from({ length: Math.min(columnCount, 3) }).map((_, index) => (
              <Box
                key={index}
                sx={{
                  flex: 1,
                  border: '1px dashed #ccc',
                  borderRadius: '4px',
                  padding: '8px',
                  backgroundColor: '#f8f9fa',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minHeight: '80px',
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  列 {index + 1}
                </Typography>
                {columns[index] && columns[index].title && (
                  <Typography variant="caption" fontWeight="medium" sx={{ mt: 0.5 }}>
                    {columns[index].title}
                  </Typography>
                )}
              </Box>
            ))}
            {columnCount > 3 && (
              <Box
                sx={{
                  flex: 1,
                  border: '1px dashed #ccc',
                  borderRadius: '4px',
                  padding: '8px',
                  backgroundColor: '#f8f9fa',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  +{columnCount - 3}列
                </Typography>
              </Box>
            )}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            列布局 ({columnCount}列, 每列{columnSize}/12)
          </Typography>
        </Box>
      );
    }

    if (instance.template_id === 'wet-list') {
      // 类型安全的列表配置
      const listConfig: ListConfig = {
        title: typeof config.title === 'string' ? config.title : '列表标题',
        type:
          config.type === 'unordered' ||
          config.type === 'ordered' ||
          config.type === 'description'
            ? config.type
            : 'unordered',
        items: config.items && Array.isArray(config.items) ? config.items : [],
        start: typeof config.start === 'number' ? config.start : undefined,
        showNumbers: typeof config.showNumbers === 'boolean' ? config.showNumbers : undefined,
        showBullets: typeof config.showBullets === 'boolean' ? config.showBullets : undefined,
        compact: typeof config.compact === 'boolean' ? config.compact : undefined,
        sortable: typeof config.sortable === 'boolean' ? config.sortable : undefined,
        maxItems: typeof config.maxItems === 'number' ? config.maxItems : undefined,
        className: typeof config.className === 'string' ? config.className : undefined,
        id: typeof config.id === 'string' ? config.id : undefined,
      };

      const { title, type, items = [], compact, showBullets, showNumbers } = listConfig;

      // 生成可访问性属性
      const accessibilityProps = generateListAccessibility(listConfig, {
        tabIndex: 0,
      });

      // 键盘事件处理
      const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          if (!previewMode) {
            selectInstance(instance.id);
          }
        }
      };

      // 列表项数量
      const itemCount = items.length;
      const displayItems = items.slice(0, 5); // 最多显示5项

      // 列表样式
      const listStyles = {
        unordered: { listStyleType: showBullets !== false ? 'disc' : 'none' },
        ordered: { listStyleType: showNumbers !== false ? 'decimal' : 'none' },
        description: {},
      };

      return (
        <Box
          className={instance.template_id}
          sx={{
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}
          {...accessibilityProps}
          onKeyDown={handleKeyDown}
          onClick={() => {
            if (!previewMode) {
              selectInstance(instance.id);
            }
          }}
          tabIndex={0}
        >
          {title && (
            <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
              {title}
            </Typography>
          )}
          
          <Box
            component={type === 'description' ? 'dl' : type === 'ordered' ? 'ol' : 'ul'}
            sx={{
              listStyle: 'none',
              padding: 0,
              margin: 0,
              width: '100%',
              maxHeight: '200px',
              overflowY: 'auto',
              flex: 1,
              ...listStyles[type],
              ...(compact && { marginBottom: 0 }),
            }}
          >
            {displayItems.length > 0 ? (
              displayItems.map((item, index) => {
                if (type === 'description') {
                  return (
                    <Box key={index} sx={{ mb: 1 }}>
                      <Typography variant="body2" component="dt" fontWeight="medium">
                        {item.text || `项目 ${index + 1}`}
                      </Typography>
                      {item.description && (
                        <Typography variant="body2" component="dd" color="text.secondary" sx={{ ml: 2 }}>
                          {item.description}
                        </Typography>
                      )}
                    </Box>
                  );
                } else {
                  return (
                    <Box
                      key={index}
                      component="li"
                      sx={{
                        py: 0.5,
                        borderBottom: index < displayItems.length - 1 ? '1px solid #eee' : 'none',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      <Typography variant="body2">
                        {item.text || `列表项 ${index + 1}`}
                      </Typography>
                      {item.linkUrl && (
                        <Typography variant="caption" color="primary" sx={{ ml: 1 }}>
                          →
                        </Typography>
                      )}
                    </Box>
                  );
                }
              })
            ) : (
              <Box
                sx={{
                  py: 3,
                  textAlign: 'center',
                  color: 'text.secondary',
                }}
              >
                <Typography variant="body2">暂无列表项</Typography>
                <Typography variant="caption">点击配置添加项目</Typography>
              </Box>
            )}
          </Box>
          
          {itemCount > 5 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              显示 5/{itemCount} 项
            </Typography>
          )}
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            {type === 'unordered' ? '无序列表' : type === 'ordered' ? '有序列表' : '描述列表'}
            {compact && ' (紧凑)'}
          </Typography>
        </Box>
      );
    }

    // 其他组件的通用预览
    return (
      <Box
        className={instance.template_id}
        sx={{
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
        }}
      >
        <Typography variant="body2" fontWeight="medium" gutterBottom>
          {instance.template_id.replace('wet-', '').replace('-', ' ')}
        </Typography>
        {config.id && (
          <Typography variant="caption" color="text.secondary">
            ID: {config.id}
          </Typography>
        )}
        {config.label && (
          <Typography variant="caption" color="text.secondary">
            {config.label}
          </Typography>
        )}
      </Box>
    );
  };

  return (
    <Box
      sx={{
        position: 'absolute',
        left: position.left,
        top: position.top,
        cursor: isDragging ? 'grabbing' : 'grab',
        zIndex: isSelected ? 10 : 1,
        transition: isDragging ? 'none' : 'all 0.2s',
        opacity: isDragging ? 0.8 : 1,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
    >
      <Paper
        elevation={isSelected ? 8 : 2}
        sx={{
          position: 'relative',
          width: componentWidth,
          minHeight: 120,
          border: 2,
          borderColor: isSelected ? 'primary.main' : 'transparent',
          bgcolor: 'background.paper',
          '&:hover': {
            borderColor: isHovered && !previewMode ? 'primary.light' : undefined,
          },
        }}
      >
        {/* 组件内容 */}
        {renderComponentPreview()}

        {/* 操作工具栏 (非预览模式显示) */}
        {!previewMode && (isHovered || isSelected) && (
          <Box
            sx={{
              position: 'absolute',
              top: -36,
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'space-between',
              bgcolor: 'background.paper',
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              p: 0.5,
              boxShadow: 2,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <IconButton
                size="small"
                onMouseDown={handleMouseDown}
                sx={{
                  cursor: 'grab',
                  bgcolor: 'primary.light',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'primary.main',
                  },
                }}
                title="拖拽移动组件"
              >
                <DragHandle fontSize="small" />
              </IconButton>
              <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                拖拽移动
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <IconButton
                size="small"
                title="编辑配置"
                onClick={e => {
                  e.stopPropagation();
                  selectInstance(instance.id);
                  openConfigDialog();
                }}
                sx={{
                  bgcolor: 'grey.100',
                  '&:hover': { bgcolor: 'grey.200' },
                }}
              >
                <Edit fontSize="small" />
              </IconButton>
              <IconButton
                size="small"
                onClick={handleDelete}
                color="error"
                title="删除组件"
                sx={{
                  bgcolor: 'error.light',
                  color: 'white',
                  '&:hover': { bgcolor: 'error.main' },
                }}
              >
                <Delete fontSize="small" />
              </IconButton>
            </Box>
          </Box>
        )}

        {/* 对齐方式指示器 */}
        {isSelected && !previewMode && (
          <Box
            sx={{
              position: 'absolute',
              bottom: -20,
              right: 0,
              bgcolor: 'primary.main',
              color: 'white',
              px: 1,
              py: 0.25,
              borderRadius: 0.5,
              fontSize: '0.75rem',
            }}
          >
            {instance.alignment || calculateAlignmentFromX(instance.position_x)}
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default CanvasComponent;
