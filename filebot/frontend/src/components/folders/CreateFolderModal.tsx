import React, { useState, useEffect } from 'react';
import { Folder } from '../../services/folder.service';
import { XMarkIcon, FolderIcon } from '@heroicons/react/24/outline';

interface CreateFolderModalProps {
  appId: string;
  parentFolderId?: string | null;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    parent_folder_id?: string;
    app_id: string;
  }) => Promise<void>;
  folders: Folder[];
  mode?: 'create' | 'edit';
  folderToEdit?: Folder | null;
}

const CreateFolderModal: React.FC<CreateFolderModalProps> = ({
  appId,
  parentFolderId,
  onClose,
  onSubmit,
  folders,
  mode = 'create',
  folderToEdit = null
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedParentFolderId, setSelectedParentFolderId] = useState<string | ''>(parentFolderId || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 根据编辑模式初始化表单
  useEffect(() => {
    if (mode === 'edit' && folderToEdit) {
      setName(folderToEdit.name);
      setDescription(folderToEdit.description || '');
      setSelectedParentFolderId(folderToEdit.parent_folder_id || '');
    } else {
      // 创建模式，重置表单
      setName('');
      setDescription('');
      setSelectedParentFolderId(parentFolderId || '');
    }
  }, [mode, folderToEdit, parentFolderId]);
  
  // 构建文件夹选择选项
  const getFolderOptions = () => {
    const options: { value: string; label: string; path: string }[] = [
      { value: '', label: '根目录（应用下）', path: '' }
    ];
    
    // 递归构建带缩进的选项
    const buildOptions = (folderList: Folder[], level = 0) => {
      folderList.forEach(folder => {
        const indent = '  '.repeat(level);
        options.push({
          value: folder.id,
          label: `${indent}${folder.name}`,
          path: folder.path || folder.name
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
  
  // 获取当前选中的父文件夹信息
  const getSelectedParentInfo = () => {
    if (!selectedParentFolderId) {
      return { name: '根目录', path: '应用根目录' };
    }
    
    const folder = folders.find(f => f.id === selectedParentFolderId);
    if (folder) {
      return { name: folder.name, path: folder.path || folder.name };
    }
    
    return { name: '未知文件夹', path: '' };
  };
  
  const selectedParentInfo = getSelectedParentInfo();
  
  // 验证表单
  const validateForm = () => {
    if (!name.trim()) {
      setError('文件夹名称不能为空');
      return false;
    }
    
    if (name.length > 100) {
      setError('文件夹名称不能超过100个字符');
      return false;
    }
    
    if (description.length > 500) {
      setError('描述不能超过500个字符');
      return false;
    }
    
    // 检查名称是否在同一父文件夹下已存在
    const existingFolder = folders.find(f => 
      f.name === name.trim() && 
      f.app_id === appId &&
      f.parent_folder_id === (selectedParentFolderId || null)
    );
    
    if (existingFolder) {
      // 在编辑模式下，如果找到的文件夹就是正在编辑的文件夹，那么是允许的（名称未改变）
      if (mode === 'edit' && folderToEdit && existingFolder.id === folderToEdit.id) {
        // 名称未改变，允许通过
      } else {
        setError('此位置下已存在同名的文件夹');
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
        parent_folder_id: selectedParentFolderId || undefined,
        app_id: appId
      };
      
      await onSubmit(folderData);
      
      // 清空表单
      setName('');
      setDescription('');
      setSelectedParentFolderId('');
      
      // 不需要手动关闭，父组件会在成功提交后关闭模态框
    } catch (err: any) {
      console.error('创建文件夹失败:', err);
      setError(err.response?.data?.detail || err.message || '创建文件夹失败');
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
    
    if (!selectedParentFolderId) {
      // 根目录
      return `/${appId}/${nameSlug}`;
    } else {
      const parentFolder = folders.find(f => f.id === selectedParentFolderId);
      if (parentFolder?.path) {
        return `${parentFolder.path}/${nameSlug}`;
      } else {
        return `/${appId}/.../${nameSlug}`;
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
              {mode === 'edit' ? '编辑文件夹' : '创建文件夹'}
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
              <div className="text-sm text-blue-800 mb-1">父文件夹</div>
              <div className="font-medium">{selectedParentInfo.name}</div>
              {selectedParentInfo.path && (
                <div className="text-sm text-blue-600 mt-1 truncate">
                  路径: {selectedParentInfo.path}
                </div>
              )}
            </div>
            
            {/* 文件夹名称 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                文件夹名称 *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setError(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="请输入文件夹名称"
                autoFocus
                disabled={isSubmitting}
                maxLength={100}
              />
              <div className="text-xs text-gray-500 mt-1">
                最多100个字符，名称应具有描述性
              </div>
            </div>
            
            {/* 路径预览 */}
            {name.trim() && (
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">路径预览</div>
                <div className="font-mono text-sm text-gray-800 truncate">
                  {pathPreview}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  系统将基于此路径存储文件夹中的文档
                </div>
              </div>
            )}
            
            {/* 文件夹描述 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                描述（可选）
              </label>
              <textarea
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  setError(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="请输入文件夹描述"
                rows={3}
                disabled={isSubmitting}
                maxLength={500}
              />
              <div className="text-xs text-gray-500 mt-1">
                最多500个字符，描述文件夹的用途和内容
              </div>
            </div>
            
            {/* 选择父文件夹 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择父文件夹（可选）
              </label>
              <select
                value={selectedParentFolderId}
                onChange={(e) => setSelectedParentFolderId(e.target.value)}
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
                留空将在应用根目录下创建文件夹
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
                取消
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isSubmitting || !name.trim()}
              >
                {isSubmitting ? (
                  <span className="flex items-center">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                    {mode === 'edit' ? '保存中...' : '创建中...'}
                  </span>
                ) : (
                  mode === 'edit' ? '保存更改' : '创建文件夹'
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