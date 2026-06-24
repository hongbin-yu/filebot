import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Folder } from '../../services/folder.service';
import { XMarkIcon, FolderIcon } from '@heroicons/react/24/outline';

interface CreateFolderModalProps {
  appSlug: string;
  parentFolderPath?: string | null;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    parent_folder_path?: string;
    path?: string;
    app_id: string;
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
      const foundFolder = folders.find(f => f.path === parentFolderPath);
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
      
      if (!parentPath && folderToEdit.parent_folder_path) {
        const parentPath2 = folderToEdit.parent_folder_path;
        // 检查是否为UUID
        const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(parentPath2);
        if (isUUID) {
          // 尝试在folders中查找对应UUID的文件夹
          const foundFolder = folders.find(f => f.path === parentPath2);
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
        const folderPath = folder.path || `/unknown/${folder.name}`;
        options.push({
          value: folderPath,
          label: `${indent}${folder.name}`,
          path: folderPath
        });
        
        // 查找子文件夹（使用 path 而非 id，Folder 主键是 path）
        const children = folders.filter(f => f.parent_folder_path === folder.path);
        if (children.length > 0) {
          buildOptions(children, level + 1);
        }
      });
    };
    
    // 从根文件夹开始
    const rootFolders = folders.filter(f => !f.parent_folder_path);
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
    
    // 如果不在已加载的文件夹列表中，从路径中提取名字
    // （防止 loadFolders 只取了顶层文件夹导致深层目录匹配不到）
    const pathParts = selectedParentFolderPath.split('/').filter(Boolean);
    const nameFromPath = pathParts[pathParts.length - 1] || selectedParentFolderPath;
    // 将下划线/中划线转为空格，首字母大写作为 fallback 显示名
    const displayName = nameFromPath
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
    
    return { name: displayName, path: selectedParentFolderPath };
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
      (f.parent_folder_path === selectedParentFolderPath)
    );
    
    if (existingFolder) {
      // 在编辑模式下，如果找到的文件夹就是正在编辑的文件夹，那么是允许的（名称未改变）
      if (mode === 'edit' && folderToEdit && existingFolder.path === folderToEdit.path) {
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
            const parentPath = selectedParentFolderPath || undefined;
      const autoPath = selectedParentFolderPath
        ? `${selectedParentFolderPath.replace(/\/+$/, '')}/${name.trim().replace(/\s+/g, '-').toLowerCase()}`
        : '';
      const folderData = {
        name: name.trim(),
        description: description.trim() || undefined,
        parent_folder_path: parentPath,
        path: autoPath,
        app_id: appSlug
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
      className="fb-modal-backdrop fb-d-flex fb-align-center" style={{justifyContent:"center",zIndex:50}}
      onClick={handleBackgroundClick}
    >
      <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 20px 25px -5px rgba(0,0,0,0.1)",width:"100%",maxWidth:448,maxHeight:"90vh",overflow:"hidden"}}>
        {/* 模态框头部 */}
        <div className="fb-d-flex fb-justify-between fb-align-center" style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,borderBottom:"1px solid #e5e7eb"}}>
          <div className="fb-d-flex fb-align-center">
            <FolderIcon style={{width:24,height:24,color:"#eab308",marginRight:8}} />
            <h2 style={{fontSize:"1.125rem",lineHeight:"1.75rem",fontWeight:600,color:"#1f2937"}}>
              {mode === 'edit' ? t('folderModal.editFolder') : t('folderModal.createFolder')}
            </h2>
          </div>
          <button 
            onClick={onClose}
            style={{padding:4,borderRadius:4}}
            disabled={isSubmitting}
          >
            <XMarkIcon className="text-muted" style={{width:20,height:20}} />
          </button>
        </div>
        
        {/* 模态框内容 */}
        <div style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,overflowY:"auto", maxHeight: 'calc(90vh - 140px)' }}>
          <form onSubmit={handleSubmit}>
            {/* 父文件夹信息 */}
            <div style={{marginBottom:24,padding:12,backgroundColor:"#eff6ff",borderRadius:8}}>
              <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#1e40af",marginBottom:4}}>{t('folderModal.parentFolder')}</div>
              <div style={{fontWeight:500}}>{selectedParentInfo.name}</div>
              {selectedParentInfo.path && (
                <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#2563eb",marginTop:4,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                  {t('folderModal.pathLabel')} {selectedParentInfo.path}
                </div>
              )}
            </div>
            
            {/* 文件夹名称 */}
            <div style={{marginBottom:16}}>
              <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                {t('folderModal.folderNameLabel')}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setError(null);
                }}
                className="form-control"
                placeholder={t('folderModal.folderNamePlaceholder')}
                autoFocus
                disabled={isSubmitting}
                maxLength={100}
              />
              <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                {t('folderModal.folderNameHint')}
              </div>
            </div>
            
            {/* 路径预览 */}
            {name.trim() && (
              <div style={{marginBottom:16,padding:12,backgroundColor:"#f9fafb",borderRadius:8}}>
                <div className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginBottom:4}}>{t('folderModal.pathPreview')}</div>
                <div style={{fontFamily:"ui-monospace, SFMono-Regular, monospace",fontSize:"0.875rem",lineHeight:"1.25rem",color:"#1f2937",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                  {pathPreview}
                </div>
                <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                  {t('folderModal.pathPreviewHint')}
                </div>
              </div>
            )}
            
            {/* 文件夹描述 */}
            <div style={{marginBottom:16}}>
              <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                {t('folderModal.descriptionLabel')}
              </label>
              <textarea
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  setError(null);
                }}
                className="form-control"
                placeholder={t('folderModal.descriptionPlaceholder')}
                rows={3}
                disabled={isSubmitting}
                maxLength={500}
              />
              <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                {t('folderModal.descriptionHint')}
              </div>
            </div>
            
            {/* 选择父文件夹 - 创建子文件夹时只读显示，创建根文件夹时可选 */}
            <div style={{marginBottom:24}}>
              <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                {t('folderModal.selectParentFolderLabel')}
              </label>
              {parentFolderPath ? (
                <div style={{width:"100%",paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,backgroundColor:"#f9fafb",border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:4,fontSize:"0.875rem",lineHeight:"1.25rem",color:"#374151"}}>
                  <span style={{fontWeight:500}}>{getSelectedParentInfo().name}</span>
                  <span style={{color:"#9ca3af",marginLeft:8}}>{getSelectedParentInfo().path}</span>
                </div>
              ) : (
                <select
                  value={selectedParentFolderPath}
                  onChange={(e) => setSelectedParentFolderPath(e.target.value)}
                  className="form-control"
                  disabled={isSubmitting}
                >
                  {folderOptions.map(option => (
                    <option key={option.value || 'root'} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              )}
              <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                {parentFolderPath ? t('folderModal.currentFolderAsParent') || '此文件夹为固定的父文件夹' : t('folderModal.selectParentFolderHint')}
              </div>
            </div>
            
            {/* 错误信息 */}
            {error && (
              <div style={{marginBottom:16,padding:12,backgroundColor:"#fef2f2",border:"1px solid #ddd",borderColor:"#fecaca",borderRadius:4}}>
                <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#991b1b"}}>{error}</div>
              </div>
            )}
            
            {/* 操作按钮 */}
            <div className="fb-d-flex" style={{justifyContent:"flex-end",display:"flex",gap:12,paddingTop:16,borderTop:"1px solid #e5e7eb"}}>
              <button
                type="button"
                onClick={onClose}
                style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",color:"#374151",borderRadius:4}}
                disabled={isSubmitting}
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,backgroundColor:"#2563eb",color:"#fff",borderRadius:4}}
                disabled={isSubmitting || !name.trim()}
              >
                {isSubmitting ? (
                  <span className="fb-d-flex fb-align-center">
                    <span className="fb-spinner" style={{borderRadius:9999,height:16,width:16,borderBottomWidth:2,borderColor:"#fff",marginRight:8}}></span>
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