/**
 * 编辑器状态管理 (Zustand)
 */

import { create } from 'zustand';
import type { ComponentTemplate, ComponentInstance, Page } from '../services/api';

// 编辑器状态接口
interface EditorState {
  // 组件模板
  componentTemplates: ComponentTemplate[];
  isLoadingTemplates: boolean;

  // 组件实例
  componentInstances: ComponentInstance[];

  // 页面管理
  currentPageId: string | null;
  pages: Page[];
  isLoadingPages: boolean;
  currentPageTitle: string;

  // 选择状态
  selectedTemplateId: string | null;
  selectedInstanceId: string | null;

  // 编辑器画布状态
  canvasWidth: number;
  canvasHeight: number;

  // 预览模式
  previewMode: boolean;

  // 配置对话框状态
  configDialogOpen: boolean;

  // Actions
  setComponentTemplates: (templates: ComponentTemplate[]) => void;
  setLoadingTemplates: (loading: boolean) => void;
  addComponentInstance: (instance: ComponentInstance) => void;
  updateComponentInstance: (instanceId: string, updates: Partial<ComponentInstance>) => void;
  removeComponentInstance: (instanceId: string) => void;
  selectTemplate: (templateId: string | null) => void;
  selectInstance: (instanceId: string | null) => void;
  setCanvasSize: (width: number, height: number) => void;
  togglePreviewMode: () => void;

  // 配置对话框Actions
  openConfigDialog: () => void;
  closeConfigDialog: () => void;

  // 页面管理Actions
  setCurrentPageId: (pageId: string | null) => void;
  setPages: (pages: Page[]) => void;
  setLoadingPages: (loading: boolean) => void;
  setCurrentPageTitle: (title: string) => void;
  clearCurrentPage: () => void;

  // 计算属性
  getSelectedTemplate: () => ComponentTemplate | null;
  getSelectedInstance: () => ComponentInstance | null;
  getCurrentPage: () => Page | null;
}

// 创建状态存储
export const useEditorStore = create<EditorState>((set, get) => ({
  // 初始状态
  componentTemplates: [],
  isLoadingTemplates: false,
  componentInstances: [],
  
  // 页面管理状态
  currentPageId: null,
  pages: [],
  isLoadingPages: false,
  currentPageTitle: '未命名页面',

  selectedTemplateId: null,
  selectedInstanceId: null,
  canvasWidth: 1920, // 全屏宽度，提供充足编辑空间
  canvasHeight: 1080, // 全屏高度，1080p标准
  previewMode: false,
  configDialogOpen: false, // 配置对话框默认关闭

  // Actions
  setComponentTemplates: templates => set({ componentTemplates: templates }),

  setLoadingTemplates: loading => set({ isLoadingTemplates: loading }),

  addComponentInstance: instance =>
    set(state => ({
      componentInstances: [...state.componentInstances, instance],
    })),

  setComponentInstances: (instances: ComponentInstance[]) => set({ componentInstances: instances }),

  updateComponentInstance: (instanceId, updates) =>
    set(state => ({
      componentInstances: state.componentInstances.map(instance =>
        instance.id === instanceId ? { ...instance, ...updates } : instance
      ),
    })),

  removeComponentInstance: instanceId =>
    set(state => ({
      componentInstances: state.componentInstances.filter(instance => instance.id !== instanceId),
      selectedInstanceId: state.selectedInstanceId === instanceId ? null : state.selectedInstanceId,
    })),

  selectTemplate: templateId => set({ selectedTemplateId: templateId }),

  selectInstance: instanceId => set({ selectedInstanceId: instanceId }),

  setCanvasSize: (width, height) => set({ canvasWidth: width, canvasHeight: height }),

  togglePreviewMode: () => set(state => ({ previewMode: !state.previewMode })),

  // 配置对话框Actions
  openConfigDialog: () => set({ configDialogOpen: true }),
  closeConfigDialog: () => set({ configDialogOpen: false }),

  // 页面管理Actions
  setCurrentPageId: (pageId) => set({ currentPageId: pageId }),
  setPages: (pages) => set({ pages }),
  setLoadingPages: (loading) => set({ isLoadingPages: loading }),
  setCurrentPageTitle: (title) => set({ currentPageTitle: title }),
  clearCurrentPage: () => set({ 
    currentPageId: null, 
    currentPageTitle: '未命名页面',
    componentInstances: [] 
  }),

  // 计算属性
  getSelectedTemplate: () => {
    const state = get();
    return (
      state.componentTemplates.find(template => template.id === state.selectedTemplateId) || null
    );
  },

  getSelectedInstance: () => {
    const state = get();
    return (
      state.componentInstances.find(instance => instance.id === state.selectedInstanceId) || null
    );
  },

  getCurrentPage: () => {
    const state = get();
    if (!state.currentPageId) return null;
    return state.pages.find(page => page.id === state.currentPageId) || null;
  },
}));
