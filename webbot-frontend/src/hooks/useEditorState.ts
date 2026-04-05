/**
 * 编辑器状态钩子
 */

import { useEditorStore } from '../stores/editorStore';

/**
 * 编辑器状态钩子
 */
export function useEditorState() {
  const {
    selectedTemplateId,
    selectedInstanceId,
    canvasWidth,
    canvasHeight,
    previewMode,
    configDialogOpen,
    currentPageTitle,
    selectTemplate,
    selectInstance,
    setCanvasSize,
    togglePreviewMode,
    openConfigDialog,
    closeConfigDialog,
    getSelectedTemplate,
    getSelectedInstance,
  } = useEditorStore();

  /**
   * 清空选择
   */
  const clearSelection = () => {
    selectTemplate(null);
    selectInstance(null);
  };

  /**
   * 是否选中了任何内容
   */
  const hasSelection = selectedTemplateId !== null || selectedInstanceId !== null;

  /**
   * 获取画布背景样式
   */
  const getCanvasBackground = () => {
    if (previewMode) {
      return '#ffffff';
    }
    return '#f5f5f5';
  };

  /**
   * 获取画布网格样式
   */
  const getCanvasGrid = () => {
    if (previewMode) {
      return null;
    }
    return {
      backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.1) 1px, transparent 1px),
                       linear-gradient(90deg, rgba(0, 0, 0, 0.1) 1px, transparent 1px)`,
      backgroundSize: '20px 20px',
    };
  };

  return {
    // 状态
    selectedTemplateId,
    selectedInstanceId,
    canvasWidth,
    canvasHeight,
    previewMode,
    configDialogOpen,
    currentPageTitle,
    hasSelection,

    // 选择状态
    selectedTemplate: getSelectedTemplate(),
    selectedInstance: getSelectedInstance(),

    // Actions
    selectTemplate,
    selectInstance,
    clearSelection,
    setCanvasSize,
    togglePreviewMode,
    openConfigDialog,
    closeConfigDialog,

    // 工具函数
    getCanvasBackground,
    getCanvasGrid,
  };
}

/**
 * 拖拽管理钩子
 */
export function useDragAndDrop() {
  const { selectTemplate } = useEditorStore();

  /**
   * 开始拖拽组件
   */
  const startDrag = (templateId: string, event: React.DragEvent) => {
    event.dataTransfer.setData('text/plain', templateId);
    selectTemplate(templateId);
  };

  /**
   * 处理拖拽放置
   */
  const handleDrop = (
    event: React.DragEvent,
    onDropCallback: (templateId: string, position: { x: number; y: number }) => void
  ) => {
    event.preventDefault();
    const templateId = event.dataTransfer.getData('text/plain');
    if (templateId) {
      const rect = event.currentTarget.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      onDropCallback(templateId, { x, y });
    }
  };

  /**
   * 处理拖拽悬停
   */
  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  return {
    startDrag,
    handleDrop,
    handleDragOver,
  };
}
