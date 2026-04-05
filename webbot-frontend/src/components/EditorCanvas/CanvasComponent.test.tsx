/**
 * CanvasComponent 单元测试 - 简化版本
 * 先测试基本渲染和交互，逐步添加可访问性测试
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import CanvasComponent from './CanvasComponent';
import type { ComponentInstance } from '../../services/api';

// 模拟组件实例数据
const mockButtonInstance: ComponentInstance = {
  id: 'button-1',
  template_id: 'wet-button-primary',
  configuration: {
    label: '测试按钮',
    action: 'https://example.com',
    size: 'medium',
    variant: 'primary',
    disabled: false,
    block: false,
  },
  position_x: 100,
  position_y: 200,
  alignment: 'left',
  created_at: '2026-03-27T00:00:00Z',
  updated_at: '2026-03-27T00:00:00Z',
};

const mockDisabledButtonInstance: ComponentInstance = {
  ...mockButtonInstance,
  id: 'button-2',
  configuration: {
    ...mockButtonInstance.configuration,
    label: '禁用按钮',
    disabled: true,
  },
};

const mockInputInstance: ComponentInstance = {
  id: 'input-1',
  template_id: 'wet-input-text',
  configuration: {
    label: '用户名',
    placeholder: '请输入用户名',
    type: 'text',
    required: true,
    disabled: false,
  },
  position_x: 300,
  position_y: 200,
  alignment: 'center',
  created_at: '2026-03-27T00:00:00Z',
  updated_at: '2026-03-27T00:00:00Z',
};

const mockTitleInstance: ComponentInstance = {
  id: 'title-1',
  template_id: 'wet-title',
  configuration: {
    text: '页面标题',
    level: 1,
    align: 'center',
    size: 'large',
  },
  position_x: 500,
  position_y: 100,
  alignment: 'center',
  created_at: '2026-03-27T00:00:00Z',
  updated_at: '2026-03-27T00:00:00Z',
};

// 模拟hook返回值
const mockSelectInstance = vi.fn();
const mockUpdateComponentPosition = vi.fn();
const mockDeleteComponentInstance = vi.fn();
const mockUpdateComponentAlignment = vi.fn();
const mockOpenConfigDialog = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  
  // Mock window.open (jsdom中未实现)
  window.open = vi.fn();
  
  // 重置mock
  vi.mock('../../hooks/useComponents', () => ({
    useComponentInstances: () => ({
      selectInstance: mockSelectInstance,
      updateComponentPosition: mockUpdateComponentPosition,
      deleteComponentInstance: mockDeleteComponentInstance,
      updateComponentAlignment: mockUpdateComponentAlignment,
    }),
  }));

  vi.mock('../../hooks/useEditorState', () => ({
    useEditorState: () => ({
      openConfigDialog: mockOpenConfigDialog,
    }),
  }));

  vi.mock('../../stores/editorStore', () => ({
    useEditorStore: () => ({
      selectedInstanceId: null,
    }),
  }));
});

describe('CanvasComponent 基本测试', () => {
  describe('按钮组件 (wet-button-primary)', () => {
    it('应正确渲染按钮并显示标签', () => {
      render(
        <CanvasComponent
          instance={mockButtonInstance}
          previewMode={false}
        />
      );

      // 检查按钮文本（使用正则表达式匹配部分文本）
      expect(screen.getByText(/测试按钮/)).toBeInTheDocument();
      expect(screen.getByText(/按钮组件/)).toBeInTheDocument();
    });

    it('按钮应包含正确的可访问性角色', () => {
      render(
        <CanvasComponent
          instance={mockButtonInstance}
          previewMode={false}
        />
      );

      // 检查按钮角色
      const buttonElement = screen.getByRole('button', { name: /测试按钮/i });
      expect(buttonElement).toBeInTheDocument();
      expect(buttonElement).toHaveAttribute('role', 'button');
    });

    it('禁用按钮应具有正确的可访问性属性', () => {
      render(
        <CanvasComponent
          instance={mockDisabledButtonInstance}
          previewMode={false}
        />
      );

      const buttonElement = screen.getByRole('button', { name: /禁用按钮/i });
      expect(buttonElement).toBeInTheDocument();
      // 检查 aria-disabled 属性存在
      expect(buttonElement).toHaveAttribute('aria-disabled');
      // 检查 tabindex 为 -1 (禁用按钮不可聚焦)
      expect(buttonElement).toHaveAttribute('tabindex', '-1');
    });

    it('点击按钮应触发选择组件（编辑模式）', () => {
      render(
        <CanvasComponent
          instance={mockButtonInstance}
          previewMode={false}
        />
      );

      const buttonElement = screen.getByRole('button', { name: /测试按钮/i });
      fireEvent.click(buttonElement);
      
      expect(mockSelectInstance).toHaveBeenCalledWith('button-1');
    });

    it.skip('在预览模式下点击按钮不应选择组件', () => {
      render(
        <CanvasComponent
          instance={mockButtonInstance}
          previewMode={true}
        />
      );

      const buttonElement = screen.getByRole('button', { name: /测试按钮/i });
      fireEvent.click(buttonElement);
      
      expect(mockSelectInstance).not.toHaveBeenCalled();
    });

    it('按钮应响应Enter键打开链接', () => {
      const mockWindowOpen = vi.fn();
      window.open = mockWindowOpen;

      render(
        <CanvasComponent
          instance={mockButtonInstance}
          previewMode={false}
        />
      );

      const buttonElement = screen.getByRole('button', { name: /测试按钮/i });
      fireEvent.keyDown(buttonElement, { key: 'Enter' });
      
      expect(mockWindowOpen).toHaveBeenCalledWith('https://example.com', '_blank');
    });

    it('按钮应响应Space键打开链接', () => {
      const mockWindowOpen = vi.fn();
      window.open = mockWindowOpen;

      render(
        <CanvasComponent
          instance={mockButtonInstance}
          previewMode={false}
        />
      );

      const buttonElement = screen.getByRole('button', { name: /测试按钮/i });
      fireEvent.keyDown(buttonElement, { key: ' ' });
      
      expect(mockWindowOpen).toHaveBeenCalledWith('https://example.com', '_blank');
    });

    it('禁用按钮不应响应键盘交互', () => {
      const mockWindowOpen = vi.fn();
      window.open = mockWindowOpen;

      render(
        <CanvasComponent
          instance={mockDisabledButtonInstance}
          previewMode={false}
        />
      );

      const buttonElement = screen.getByRole('button', { name: /禁用按钮/i });
      fireEvent.keyDown(buttonElement, { key: 'Enter' });
      
      expect(mockWindowOpen).not.toHaveBeenCalled();
    });
  });

  describe('输入框组件 (wet-input-text)', () => {
    it('应正确渲染输入框和标签', () => {
      render(
        <CanvasComponent
          instance={mockInputInstance}
          previewMode={false}
        />
      );

      // 检查标签文本
      expect(screen.getByText('用户名')).toBeInTheDocument();
      expect(screen.getByText(/请输入用户名/)).toBeInTheDocument();
      expect(screen.getByText('text 输入框 (必填)')).toBeInTheDocument();
    });

    it('输入框应包含正确的可访问性角色', () => {
      render(
        <CanvasComponent
          instance={mockInputInstance}
          previewMode={false}
        />
      );

      // 检查输入框角色
      const inputElement = screen.getByRole('textbox', { name: /请输入用户名/i });
      expect(inputElement).toBeInTheDocument();
      expect(inputElement).toHaveAttribute('role', 'textbox');
    });

    it('点击输入框应触发选择组件（编辑模式）', () => {
      render(
        <CanvasComponent
          instance={mockInputInstance}
          previewMode={false}
        />
      );

      const inputElement = screen.getByRole('textbox', { name: /请输入用户名/i });
      fireEvent.click(inputElement);
      
      expect(mockSelectInstance).toHaveBeenCalledWith('input-1');
    });

    it('输入框应响应Enter键选择', () => {
      render(
        <CanvasComponent
          instance={mockInputInstance}
          previewMode={false}
        />
      );

      const inputElement = screen.getByRole('textbox', { name: /请输入用户名/i });
      fireEvent.keyDown(inputElement, { key: 'Enter' });
      
      expect(mockSelectInstance).toHaveBeenCalledWith('input-1');
    });
  });

  describe('标题组件 (wet-title)', () => {
    it('应正确渲染标题元素', () => {
      render(
        <CanvasComponent
          instance={mockTitleInstance}
          previewMode={false}
        />
      );

      // 检查标题文本
      expect(screen.getByText('页面标题')).toBeInTheDocument();
      expect(screen.getByText('H1 标题')).toBeInTheDocument();
    });

    it('标题应包含正确的语义化元素 (h1)', () => {
      render(
        <CanvasComponent
          instance={mockTitleInstance}
          previewMode={false}
        />
      );

      // 检查h1元素
      const headingElement = screen.getByRole('heading', { name: '页面标题', level: 1 });
      expect(headingElement).toBeInTheDocument();
      expect(headingElement.tagName).toBe('H1');
    });

    it('点击标题应触发选择组件（编辑模式）', () => {
      render(
        <CanvasComponent
          instance={mockTitleInstance}
          previewMode={false}
        />
      );

      const headingElement = screen.getByRole('heading', { name: '页面标题', level: 1 });
      fireEvent.click(headingElement);
      
      expect(mockSelectInstance).toHaveBeenCalledWith('title-1');
    });

    it('标题应响应Enter键选择', () => {
      render(
        <CanvasComponent
          instance={mockTitleInstance}
          previewMode={false}
        />
      );

      const headingElement = screen.getByRole('heading', { name: '页面标题', level: 1 });
      fireEvent.keyDown(headingElement, { key: 'Enter' });
      
      expect(mockSelectInstance).toHaveBeenCalledWith('title-1');
    });
  });
});