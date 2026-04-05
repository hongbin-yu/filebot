/**
 * WebBot 核心组件类型定义
 * 遵循 TypeScript 严格模式和 WET-BOEW/GCWeb 可访问性标准
 */

// ==================== 通用类型 ====================

/**
 * 组件基础属性
 */
export interface ComponentBaseProps {
  /** 组件唯一标识符 */
  id: string;
  /** 组件模板ID */
  templateId: string;
  /** 组件配置数据 */
  configuration: Record<string, unknown>;
  /** X坐标位置 */
  positionX: number;
  /** Y坐标位置 */
  positionY: number;
  /** 对齐方式 */
  alignment?: 'left' | 'center' | 'right';
}

/**
 * 可访问性属性 (WCAG 2.1 AA)
 */
export interface AccessibilityProps {
  /** 屏幕阅读器标签 (优先于可见标签) */
  ariaLabel?: string;
  /** 描述性文本 (aria-describedby) */
  ariaDescribedBy?: string;
  /** 组件状态 (checked, selected, expanded 等) */
  ariaPressed?: boolean | 'mixed';
  /** 组件是否禁用 */
  ariaDisabled?: boolean;
  /** 组件是否必填 */
  ariaRequired?: boolean;
  /** 组件是否无效 */
  ariaInvalid?: boolean | 'grammar' | 'spelling';
  /** 实时区域更新 */
  ariaLive?: 'off' | 'polite' | 'assertive';
  /** 组件角色 */
  role?: string;
  /** Tab索引 (用于自定义控件) */
  tabIndex?: number;
}

/**
 * 键盘事件处理
 */
export interface KeyboardEventHandlers {
  /** 按键按下事件 */
  onKeyDown?: (event: React.KeyboardEvent) => void;
  /** 按键释放事件 */
  onKeyUp?: (event: React.KeyboardEvent) => void;
  /** 按键按下事件 (用于自定义控件) */
  onKeyPress?: (event: React.KeyboardEvent) => void;
}

// ==================== 按钮组件 ====================

/**
 * 按钮尺寸类型
 */
export type ButtonSize = 'small' | 'medium' | 'large';

/**
 * 按钮变体类型
 */
export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'light'
  | 'dark';

/**
 * 按钮配置属性
 */
export interface ButtonConfig {
  /** 按钮显示文本 */
  label: string;
  /** 按钮动作URL (可选) */
  action?: string;
  /** 按钮尺寸 */
  size?: ButtonSize;
  /** 按钮变体样式 */
  variant?: ButtonVariant;
  /** 是否禁用按钮 */
  disabled?: boolean;
  /** 是否块级显示 (占满宽度) */
  block?: boolean;
  /** 自定义CSS类名 */
  className?: string;
  /** 按钮类型 (button, submit, reset) */
  type?: 'button' | 'submit' | 'reset';
  /** 按钮图标 (可选) */
  icon?: string;
  /** 图标位置 */
  iconPosition?: 'left' | 'right';
  /** 索引签名以支持Record<string, unknown> */
  [key: string]: unknown;
}

/**
 * 完整按钮属性
 */
export interface ButtonProps extends ButtonConfig, AccessibilityProps, KeyboardEventHandlers {
  /** 点击事件处理函数 */
  onClick?: (event: React.MouseEvent) => void;
  /** 焦点事件 */
  onFocus?: (event: React.FocusEvent) => void;
  /** 失焦事件 */
  onBlur?: (event: React.FocusEvent) => void;
  /** 鼠标进入事件 */
  onMouseEnter?: (event: React.MouseEvent) => void;
  /** 鼠标离开事件 */
  onMouseLeave?: (event: React.MouseEvent) => void;
  /** 加载状态 */
  loading?: boolean;
  /** 加载中文本 */
  loadingText?: string;
  /** 按钮标题 (tooltip) */
  title?: string;
}

// ==================== 输入框组件 ====================

/**
 * 输入框类型
 */
export type InputType =
  | 'text'
  | 'email'
  | 'password'
  | 'number'
  | 'tel'
  | 'url'
  | 'search'
  | 'date'
  | 'time';

/**
 * 输入框尺寸模式
 */
export type InputSizeMode = 'fixed' | 'full' | 'auto';

/**
 * 输入框配置属性
 */
export interface InputConfig {
  /** 输入框标签 */
  label: string;
  /** 占位符文本 */
  placeholder?: string;
  /** 输入框ID (用于关联label) */
  id?: string;
  /** 输入框名称 (表单提交) */
  name?: string;
  /** 输入框类型 */
  type?: InputType;
  /** 输入框值 */
  value?: string;
  /** 默认值 */
  defaultValue?: string;
  /** 是否必填 */
  required?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否只读 */
  readonly?: boolean;
  /** 自定义宽度 (像素) */
  width?: number;
  /** 尺寸模式 */
  sizeMode?: InputSizeMode;
  /** 最大长度 */
  maxLength?: number;
  /** 最小长度 */
  minLength?: number;
  /** 正则表达式模式 */
  pattern?: string;
  /** 自动完成类型 */
  autocomplete?: string;
  /** 自定义CSS类名 */
  className?: string;
  /** 索引签名以支持Record<string, unknown> */
  [key: string]: unknown;
}

/**
 * 完整输入框属性
 */
export interface InputProps extends InputConfig, AccessibilityProps, KeyboardEventHandlers {
  /** 值变化事件 */
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  /** 输入事件 */
  onInput?: (event: React.FormEvent<HTMLInputElement>) => void;
  /** 焦点事件 */
  onFocus?: (event: React.FocusEvent<HTMLInputElement>) => void;
  /** 失焦事件 */
  onBlur?: (event: React.FocusEvent<HTMLInputElement>) => void;
  /** 表单提交事件 */
  onSubmit?: (event: React.FormEvent) => void;
  /** 验证失败事件 */
  onInvalid?: (event: React.FormEvent<HTMLInputElement>) => void;
}

// ==================== 标题组件 ====================

/**
 * 标题级别
 */
export type HeadingLevel = 1 | 2 | 3 | 4 | 5 | 6;

/**
 * 标题对齐方式
 */
export type HeadingAlign = 'left' | 'center' | 'right' | 'justify';

/**
 * 标题配置属性
 */
export interface TitleConfig {
  /** 标题文本 */
  text: string;
  /** 标题级别 (h1-h6) */
  level?: HeadingLevel;
  /** 对齐方式 */
  align?: HeadingAlign;
  /** 标题大小 (覆盖级别默认大小) */
  size?: 'small' | 'medium' | 'large' | 'xlarge';
  /** 是否显示下划线 */
  underline?: boolean;
  /** 自定义CSS类名 */
  className?: string;
  /** 标题ID (用于锚点链接) */
  id?: string;
  /** 索引签名以支持Record<string, unknown> */
  [key: string]: unknown;
}

/**
 * 完整标题属性
 */
export interface TitleProps extends TitleConfig, AccessibilityProps {
  /** 无额外事件处理 */
}

// ==================== 列表组件 ====================

/**
 * 列表类型
 */
export type ListType = 'unordered' | 'ordered' | 'description';

/**
 * 列表项数据
 */
export interface ListItemData {
  /** 列表项文本 */
  text: string;
  /** 列表项ID (可选) */
  id?: string;
  /** 列表项描述 (用于描述列表) */
  description?: string;
  /** 列表项图标/图片URL (可选) */
  iconUrl?: string;
  /** 列表项链接URL (可选) */
  linkUrl?: string;
  /** 列表项链接文本 (可选) */
  linkText?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义CSS类名 */
  className?: string;
}

/**
 * 列表配置属性
 */
export interface ListConfig {
  /** 列表标题 */
  title?: string;
  /** 列表类型 */
  type?: ListType;
  /** 列表项数据 */
  items?: ListItemData[];
  /** 起始编号 (有序列表使用) */
  start?: number;
  /** 是否显示序号 */
  showNumbers?: boolean;
  /** 是否显示项目符号 */
  showBullets?: boolean;
  /** 是否紧凑显示 */
  compact?: boolean;
  /** 是否可排序 */
  sortable?: boolean;
  /** 最大显示项数 (0表示无限制) */
  maxItems?: number;
  /** 自定义CSS类名 */
  className?: string;
  /** 列表ID (用于可访问性) */
  id?: string;
  /** 索引签名以支持Record<string, unknown> */
  [key: string]: unknown;
}

/**
 * 完整列表属性
 */
export interface ListProps extends ListConfig, AccessibilityProps {
  /** 列表项点击事件 */
  onItemClick?: (item: ListItemData, index: number) => void;
  /** 列表项键盘事件 */
  onItemKeyDown?: (item: ListItemData, index: number, event: React.KeyboardEvent) => void;
  /** 列表排序变化事件 */
  onSortChange?: (items: ListItemData[]) => void;
}

// ==================== 事件类型 ====================

/**
 * 标准化键盘事件处理
 */
export interface StandardKeyboardEvents {
  /** 处理Enter键按下 (用于按钮激活) */
  handleEnterKey?: (event: React.KeyboardEvent) => void;
  /** 处理Space键按下 (用于按钮激活) */
  handleSpaceKey?: (event: React.KeyboardEvent) => void;
  /** 处理Escape键按下 (用于关闭/取消) */
  handleEscapeKey?: (event: React.KeyboardEvent) => void;
  /** 处理Tab键导航 */
  handleTabNavigation?: (event: React.KeyboardEvent) => void;
}

/**
 * 可访问性验证结果
 */
export interface AccessibilityValidation {
  /** 是否通过WCAG 2.1 AA验证 */
  wcagCompliant: boolean;
  /** 缺失的可访问性属性 */
  missingAttributes: string[];
  /** 键盘导航问题 */
  keyboardIssues: string[];
  /** 屏幕阅读器兼容性问题 */
  screenReaderIssues: string[];
  /** 对比度问题 */
  contrastIssues: string[];
}

// ==================== 类型守卫 ====================

/**
 * 检查是否为按钮配置
 */
export function isButtonConfig(config: Record<string, unknown>): config is ButtonConfig {
  return typeof config.label === 'string';
}

/**
 * 检查是否为输入框配置
 */
export function isInputConfig(config: Record<string, unknown>): config is InputConfig {
  return typeof config.label === 'string' && (!config.type || typeof config.type === 'string');
}

/**
 * 检查是否为标题配置
 */
export function isTitleConfig(config: Record<string, unknown>): config is TitleConfig {
  return typeof config.text === 'string';
}

/**
 * 检查是否为列表配置
 */
export function isListConfig(config: Record<string, unknown>): config is ListConfig {
  return !config.items || Array.isArray(config.items);
}

// ==================== 工具函数 ====================

/**
 * 生成按钮的可访问性属性
 */
export function generateButtonAccessibility(
  config: ButtonConfig,
  props: Partial<AccessibilityProps> = {}
): AccessibilityProps {
  const { label, disabled } = config;

  return {
    ariaLabel: props.ariaLabel || label,
    ariaDisabled: disabled || false,
    ariaPressed: props.ariaPressed,
    role: 'button',
    tabIndex: disabled ? -1 : 0,
    ...props,
  };
}

/**
 * 生成输入框的可访问性属性
 */
export function generateInputAccessibility(
  config: InputConfig,
  props: Partial<AccessibilityProps> = {}
): AccessibilityProps {
  const { label, required, disabled } = config;

  return {
    ariaLabel: props.ariaLabel || label,
    ariaRequired: required || false,
    ariaDisabled: disabled || false,
    ariaInvalid: props.ariaInvalid,
    role: 'textbox',
    ...props,
  };
}

/**
 * 生成列表的可访问性属性
 */
export function generateListAccessibility(
  config: ListConfig,
  props: Partial<AccessibilityProps> = {}
): AccessibilityProps {
  const { title, items = [] } = config;

  return {
    ariaLabel: props.ariaLabel || title || `包含 ${items.length} 项的列表`,
    role: props.role || 'list',
    tabIndex: props.tabIndex || 0,
    ...props,
  };
}

/**
 * 标准键盘事件处理函数
 */
export const keyboardHandlers: StandardKeyboardEvents = {
  handleEnterKey: event => {
    if (event.key === 'Enter' && !event.defaultPrevented) {
      event.preventDefault();
      // 触发点击事件
      if (event.currentTarget instanceof HTMLElement) {
        event.currentTarget.click();
      }
    }
  },

  handleSpaceKey: event => {
    if (event.key === ' ' && !event.defaultPrevented) {
      event.preventDefault();
      // 触发点击事件
      if (event.currentTarget instanceof HTMLElement) {
        event.currentTarget.click();
      }
    }
  },

  handleEscapeKey: event => {
    if (event.key === 'Escape' && !event.defaultPrevented) {
      event.preventDefault();
      // 通常用于关闭对话框或取消操作
      if (event.currentTarget instanceof HTMLElement) {
        event.currentTarget.blur();
      }
    }
  },
};

/**
 * 验证组件的可访问性
 */
export function validateAccessibility(
  componentType: 'button' | 'input' | 'title' | 'list',
  props: Record<string, unknown>
): AccessibilityValidation {
  const result: AccessibilityValidation = {
    wcagCompliant: true,
    missingAttributes: [],
    keyboardIssues: [],
    screenReaderIssues: [],
    contrastIssues: [],
  };

  // 基础验证
  if (!props['ariaLabel'] && !props['label'] && !props['text'] && !props['title']) {
    result.missingAttributes.push('aria-label 或可见标签');
    result.wcagCompliant = false;
  }

  // 组件特定验证
  if (componentType === 'button') {
    if (props['disabled'] && props['tabIndex'] !== -1) {
      result.keyboardIssues.push('禁用按钮应设置 tabIndex=-1');
      result.wcagCompliant = false;
    }

    if (!props['onKeyDown'] && !props['onClick']) {
      result.keyboardIssues.push('按钮缺少键盘事件处理');
      result.wcagCompliant = false;
    }
  }

  if (componentType === 'input') {
    if (props['required'] && !props['ariaRequired']) {
      result.missingAttributes.push('aria-required');
      result.wcagCompliant = false;
    }

    if (!props['id'] && props['label']) {
      result.screenReaderIssues.push('输入框缺少关联标签的ID');
      result.wcagCompliant = false;
    }
  }

  if (componentType === 'list') {
    if (!props['role'] || (props['role'] !== 'list' && props['role'] !== 'listbox')) {
      result.missingAttributes.push('role="list" 或 role="listbox"');
      result.wcagCompliant = false;
    }

    const items = props['items'] as any[];
    if (items && items.length > 0) {
      items.forEach((item, index) => {
        if (!item.text && !item['ariaLabel']) {
          result.screenReaderIssues.push(`列表项 ${index + 1} 缺少可见文本或 aria-label`);
          result.wcagCompliant = false;
        }
      });
    }
  }

  return result;
}
