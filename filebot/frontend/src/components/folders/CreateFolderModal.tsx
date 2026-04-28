import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Folder } from '../../services/folder.service';
import { XMarkIcon, FolderIcon } from '@heroicons/react/24/outline';

interface CreateFolderModalProps {
  appSlug: string; // 应用slug（必需）
  parentFolderPath?: string | null; // 父文件夹路径（可选，路径格式）
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    parent_folder_id?: string; // 可以接收路径
    app_id: string; // 应用slug
  }) => Promise<void>;
  folders: Folder[];
  mode?: 'create' | 'edit';
  folderToEdit?: Folder | null;
}

const CreateFolderModal: React.FC<CreateFolderModalProps> = ({
  appSlug,
  parentFolderPath,
  onClose,
  onSubmit,
  folders,
  mode = 'create',
  folderToEdit = null
}) => {
  const { t } = useTranslation();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  // 直接使用路径，而不是UUID
  const [selectedParentFolderPath, setSelectedParentFolderPath] = useState<string | ''>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 直接使用parentFolderPath作为路径，尝试将UUID转换为路径
  useEffect(() => {
    if (!parentFolderPath) {
      setSelectedParentFolderPath('');
      return;
    }
    
    // 检查是否为UUID格式
    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(parentFolderPath);
    
    let finalPath = parentFolderPath;
    
    if (isUUID) {
      console.warn(`⚠️ CreateFolderModal收到UUID格式的parentFolderPath: ${parentFolderPath}，尝试转换为路径`);
      // 在folders中查找对应UUID的文件夹
      const foundFolder = folders.find(f => f.id === parentFolderPath);
      if (foundFolder?.path) {
        console.log(`✅ 找到对应路径: ${foundFolder.path}`);
        finalPath = foundFolder.path;
      } else {
        console.warn(`⚠️ 未找到UUID对应的文件夹，保留UUID格式: ${parentFolderPath}`);
      }
    }
    
    // 使用路径（或转换后的路径）
    setSelectedParentFolderPath(finalPath);
  }, [parentFolderPath, folders]);
  
  // 根据编辑模式初始化表单
  useEffect(() => {
    if (mode === 'edit' && folderToEdit) {
      setName(folderToEdit.name);
      setDescription(folderToEdit.description || '');
      
      // 确定父文件夹路径：优先使用parent_folder_path，否则尝试转换parent_folder_id
      let parentPath = folderToEdit.parent_folder_path || '';
      
      if (!parentPath && folderToEdit.parent_folder_id) {
        const parentId = folderToEdit.parent_folder_id;
        // 检查是否为UUID
        const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(parentId);
        if (isUUID) {
          // 尝试在folders中查找对应UUID的文件夹
          const foundFolder = folders.find(f => f.id === parentId);
          if (foundFolder?.path) {
            console.log(`✅ 编辑模式：找到父文件夹路径: ${foundFolder.path}`);
            parentPath = foundFolder.path;
          } else {
            console.warn(`⚠️ 编辑模式：未找到父文件夹UUID对应的路径: ${parentId}`);
            parentPath = parentId; // 保留UUID
          }
        } else {
          // 不是UUID，可能是路径
          parentPath = parentId;
        }
      }
      
      setSelectedParentFolderPath(parentPath);
    } else {
      // 创建模式，重置表单
      setName('');
      setDescription('');
      // parentFolderPath转换已经在上面useEffect中处理
    }
  }, [mode, folderToEdit, folders]);
  
  // 构建文件夹选择选项（使用路径）
  const getFolderOptions = () => {
    const options: { value: string; label: string; path: string }[] = [
      { value: '', label: t('folderModal.rootDirectoryOption'), path: '' }
    ];
    
    // 递归构建带缩进的选项
    const buildOptions = (folderList: Folder[], level = 0) => {
      folderList.forEach(folder => {
        const indent = '  '.repeat(level);
        // 使用folder.path作为value，如果path不存在则使用一个基于id的占位符
        const folderPath = folder.path || `/unknown/${folder.id}`;
        options.push({
          value: folderPath,
          label: `${indent}${folder.name}`,
          path: folderPath
        });
        
        // 查找子文件夹
        const children = folders.filter(f => f.parent_folder_id === folder.id);
        if (children.length > 0) {
          buildOptions(children, level + 1);
        }
      });
    };
    
    // 从根文件夹开始
    const rootFolders = folders.filter(f => !f.parent_folder_id);
    buildOptions(rootFolders);
    
    return options;
  };
  
  const folderOptions = getFolderOptions();
  
  // 获取当前选中的父文件夹信息（使用路径）
  const getSelectedParentInfo = () => {
    if (!selectedParentFolderPath) {
      return { name: t('folderModal.root'), path: `/${appSlug}` };
    }
    
    // 尝试通过路径查找文件夹
    const folder = folders.find(f => f.path === selectedParentFolderPath);
    if (folder) {
      return { name: folder.name, path: folder.path || folder.name };
    }
    
    // 如果找不到，可能是UUID格式或无效路径
    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(selectedParentFolderPath);
    if (isUUID) {
      // UUID格式，尝试通过id查找
      const folderById = folders.find(f => f.id === selectedParentFolderPath);
      if (folderById) {
        return { name: folderById.name, path: folderById.path || folderById.name };
      }
    }
    
    return { name: t('folderModal.unknownFolder'), path: selectedParentFolderPath };
  };
  
  const selectedParentInfo = getSelectedParentInfo();
  
  // 验证表单
  const validateForm = () => {
    if (!name.trim()) {
      setError(t('folderModal.folderNameRequired'));
      return false;
    }
    
    if (name.length > 100) {
      setError(t('folderModal.folderNameMaxLength'));
      return false;
    }
    
    if (description.length > 500) {
      setError(t('folderModal.descriptionMaxLength'));
      return false;
    }
    
    // 检查名称是否在同一父文件夹下已存在
    const existingFolder = folders.find(f => 
      f.name === name.trim() && 
      f.app_id === appSlug && // 使用appSlug
      (f.parent_folder_path === selectedParentFolderPath || 
       f.parent_folder_id === selectedParentFolderPath) // 支持路径或UUID
    );
    
    if (existingFolder) {
      // 在编辑模式下，如果找到的文件夹就是正在编辑的文件夹，那么是允许的（名称未改变）
      if (mode === 'edit' && folderToEdit && existingFolder.id === folderToEdit.id) {
        // 名称未改变，允许通过
      } else {
        setError(t('folderModal.duplicateFolderName'));
        return false;
      }
    }
    
    setError(null);
    return true;
  };
  
  // 处理提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const folderData = {
        name: name.trim(),
        description: description.trim() || undefined,
        parent_folder_id: selectedParentFolderPath || undefined, // 直接传递路径
        app_id: appSlug // 使用appSlug
      };
      
      await onSubmit(folderData);
      
      // 清空表单
      setName('');
      setDescription('');
      setSelectedParentFolderPath('');
      
      // 不需要手动关闭，父组件会在成功提交后关闭模态框
    } catch (err: any) {
      console.error('创建文件夹失败:', err);
      setError(err.response?.data?.detail || err.message || t('folderModal.createFolderFailed'));
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // 处理模态框背景点击
  const handleBackgroundClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };
  
  // 生成建议的路径预览
  const getPathPreview = () => {
    if (!name.trim()) return '';
    
    const nameSlug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    
    if (!selectedParentFolderPath) {
      // 根目录
      return `/${appSlug}/${nameSlug}`;
    } else {
      const parentFolder = folders.find(f => f.path === selectedParentFolderPath);
      if (parentFolder?.path) {
        // 如果父文件夹有path，直接使用它
        return `${parentFolder.path}/${nameSlug}`;
      } else {
        // 父文件夹没有path，直接使用selectedParentFolderPath
        return `${selectedParentFolderPath}/${nameSlug}`;
      }
    }
  };
  
  const pathPreview = getPathPreview();
  
  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackgroundClick}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden">
        {/* 模态框头部 */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <div className="flex items-center">
            <FolderIcon className="w-6 h-6 text-yellow-500 mr-2" />
            <h2 className="text-lg font-semibold text-gray-800">
              {mode === 'edit' ? t('folderModal.editFolder') : t('folderModal.createFolder')}
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
            disabled={isSubmitting}
          >
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        {/* 模态框内容 */}
        <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 140px)' }}>
          <form onSubmit={handleSubmit}>
            {/* 父文件夹信息 */}
            <div className="mb-6 p-3 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-800 mb-1">{t('folderModal.parentFolder')}</div>
              <div className="font-medium">{selectedParentInfo.name}</div>
              {selectedParentInfo.path && (
                <div className="text-sm text-blue-600 mt-1 truncate">
                  {t('folderModal.pathLabel')} {selectedParentInfo.path}
                </div>
              )}
            </div>
            
            {/* 文件夹名称 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('folderModal.folderNameLabel')}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setError(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={t('folderModal.folderNamePlaceholder')}
                autoFocus
                disabled={isSubmitting}
                maxLength={100}
              />
              <div className="text-xs text-gray-500 mt-1">
                {t('folderModal.folderNameHint')}
              </div>
            </div>
            
            {/* 路径预览 */}
            {name.trim() && (
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">{t('folderModal.pathPreview')}</div>
                <div className="font-mono text-sm text-gray-800 truncate">
                  {pathPreview}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {t('folderModal.pathPreviewHint')}
                </div>
              </div>
            )}
            
            {/* 文件夹描述 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('folderModal.descriptionLabel')}
              </label>
              <textarea
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  setError(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={t('folderModal.descriptionPlaceholder')}
                rows={3}
                disabled={isSubmitting}
                maxLength={500}
              />
              <div className="text-xs text-gray-500 mt-1">
                {t('folderModal.descriptionHint')}
              </div>
            </div>
            
            {/* 选择父文件夹 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('folderModal.selectParentFolderLabel')}
              </label>
              <select
                value={selectedParentFolderPath}
                onChange={(e) => setSelectedParentFolderPath(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isSubmitting}
              >
                {folderOptions.map(option => (
                  <option key={option.value || 'root'} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <div className="text-xs text-gray-500 mt-1">
                {t('folderModal.selectParentFolderHint')}
              </div>
            </div>
            
            {/* 错误信息 */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                <div className="text-sm text-red-800">{error}</div>
              </div>
            )}
            
            {/* 操作按钮 */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
                disabled={isSubmitting}
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isSubmitting || !name.trim()}
              >
                {isSubmitting ? (
                  <span className="flex items-center">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                    {mode === 'edit' ? t('folderModal.saving') : t('folderModal.creating')}
                  </span>
                ) : (
                  mode === 'edit' ? t('folderModal.saveChanges') : t('folderModal.createFolderButton')
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CreateFolderModal;