import '@testing-library/jest-dom';

// 扩展expect以包含自定义匹配器
import { expect } from 'vitest';
import * as matchers from '@testing-library/jest-dom/matchers';

expect.extend(matchers);

// 全局测试配置
beforeEach(() => {
  // 重置DOM
  document.body.innerHTML = '';
  document.head.innerHTML = '';
});

// Mock全局对象
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// 清理测试后
afterEach(() => {
  vi.clearAllMocks();
});
