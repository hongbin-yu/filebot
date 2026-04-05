/**
 * 组件管理钩子
 */

import { useEffect, useCallback } from 'react';
import { useEditorStore } from '../stores/editorStore';
import { fetchComponentTemplates } from '../services/api';

/**
 * 组件数据钩子
 */
export function useComponents() {
  const { componentTemplates, isLoadingTemplates, setComponentTemplates, setLoadingTemplates } =
    useEditorStore();

  /**
   * 加载组件模板
   */
  const loadTemplates = useCallback(async () => {
    console.log('🔄 开始加载组件模板...');
    setLoadingTemplates(true);
    try {
      const templates = await fetchComponentTemplates();
      console.log('✅ 加载组件模板完成，数量:', templates.length);
      setComponentTemplates(templates);
    } catch (error) {
      console.error('❌ 加载组件模板失败:', error);
    } finally {
      setLoadingTemplates(false);
      console.log('🏁 加载模板流程结束');
    }
  }, [setLoadingTemplates, setComponentTemplates]);

  /**
   * 按分类筛选组件
   */
  const getTemplatesByCategory = (category: string) => {
    return componentTemplates.filter(template => template.category === category);
  };

  /**
   * 按ID查找组件
   */
  const getTemplateById = (id: string) => {
    return componentTemplates.find(template => template.id === id) || null;
  };

  /**
   * 初始化加载
   */
  useEffect(() => {
    if (componentTemplates.length === 0 && !isLoadingTemplates) {
      loadTemplates();
    }
  }, [componentTemplates, isLoadingTemplates, loadTemplates]);

  return {
    componentTemplates,
    isLoadingTemplates,
    loadTemplates,
    getTemplatesByCategory,
    getTemplateById,
  };
}

/**
 * 组件实例管理钩子
 */
export function useComponentInstances() {
  const {
    componentInstances,
    addComponentInstance: addInstance,
    updateComponentInstance: updateInstance,
    removeComponentInstance: removeInstance,
    selectedInstanceId,
    selectInstance,
    canvasWidth,
  } = useEditorStore();

  // 根据x坐标计算对齐方式
  const calculateAlignmentFromX = (x: number): 'left' | 'center' | 'right' => {
    const componentWidth = 200; // 固定组件宽度
    const effectiveWidth = canvasWidth - componentWidth;
    const leftZone = effectiveWidth * 0.33;
    const centerZone = effectiveWidth * 0.66;

    if (x < leftZone) return 'left';
    if (x < centerZone) return 'center';
    return 'right';
  };

  // 根据对齐方式计算x坐标
  const calculateXFromAlignment = (alignment: 'left' | 'center' | 'right'): number => {
    const componentWidth = 200;
    switch (alignment) {
      case 'left':
        return 0;
      case 'center':
        return (canvasWidth - componentWidth) / 2;
      case 'right':
        return canvasWidth - componentWidth;
    }
  };

  /**
   * 添加组件实例
   */
  const addComponentInstance = (
    templateId: string,
    position: { x: number; y: number },
    configuration: Record<string, unknown>
  ) => {
    // 计算对齐方式
    const alignment = calculateAlignmentFromX(position.x);
    const alignedX = calculateXFromAlignment(alignment);

    // 创建临时实例
    const tempId = `instance-${Date.now()}`;
    const newInstance = {
      id: tempId,
      template_id: templateId,
      position_x: alignedX, // 使用对齐后的位置
      position_y: position.y,
      alignment, // 存储对齐方式
      configuration,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    addInstance(newInstance);
    selectInstance(tempId);
    return newInstance;
  };

  /**
   * 更新组件实例配置
   */
  const updateComponentConfig = (instanceId: string, config: Record<string, unknown>) => {
    updateInstance(instanceId, { configuration: config });
  };

  /**
   * 更新组件实例位置
   */
  const updateComponentPosition = (instanceId: string, x: number, y: number) => {
    updateInstance(instanceId, { position_x: x, position_y: y });
  };

  /**
   * 更新组件实例对齐方式
   */
  const updateComponentAlignment = (instanceId: string, alignment: 'left' | 'center' | 'right') => {
    const newX = calculateXFromAlignment(alignment);
    updateInstance(instanceId, { alignment, position_x: newX });
  };

  /**
   * 删除组件实例
   */
  const deleteComponentInstance = (instanceId: string) => {
    removeInstance(instanceId);
    if (selectedInstanceId === instanceId) {
      selectInstance(null);
    }
  };

  /**
   * 获取选中的实例
   */
  const getSelectedInstance = () => {
    return componentInstances.find(instance => instance.id === selectedInstanceId) || null;
  };

  return {
    componentInstances,
    selectedInstanceId,
    addComponentInstance,
    updateComponentConfig,
    updateComponentPosition,
    updateComponentAlignment,
    deleteComponentInstance,
    getSelectedInstance,
    selectInstance,
  };
}
