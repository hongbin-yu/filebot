import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Folder } from '../../services/folder.service';
import { 
  ChevronRightIcon, 
  ChevronDownIcon, 
  FolderIcon, 
  FolderOpenIcon, 
  TrashIcon,
  ArrowsUpDownIcon,
  ArrowDownOnSquareIcon 
} from '@heroicons/react/24/outline';

interface FolderTreeProps {
  folders: Folder[];
  currentFolderId: string | null; // 当前选中的文件夹标识符（可以是UUID或path）
  onFolderSelect: (folderId: string) => void;
  onDeleteFolder?: (folderId: string) => void;
  onMoveFolder?: (folderId: string, targetParentFolderId?: string) => Promise<void>;
}

interface FolderTreeNode extends Folder {
  children: FolderTreeNode[];
  expanded: boolean;
  level: number;
}

// 拖放位置类型
type DropPosition = 'before' | 'after' | 'inside' | 'none';

// 拖拽状态接口
interface DragState {
  draggedFolderId: string | null;
  draggedFolderNode: FolderTreeNode | null;
  isDragging: boolean;
}

// 放置目标状态接口
interface DropTargetState {
  targetFolderId: string | null;
  position: DropPosition;
  isValid: boolean;
}

const FolderTree: React.FC<FolderTreeProps> = ({
  folders,
  currentFolderId,
  onFolderSelect,
  onDeleteFolder,
  onMoveFolder
}) => {
  const { t } = useTranslation();
  // 拖拽状态
  const [dragState, setDragState] = useState<DragState>({
    draggedFolderId: null,
    draggedFolderNode: null,
    isDragging: false
  });
  
  // 放置目标状态
  const [dropTarget, setDropTarget] = useState<DropTargetState>({
    targetFolderId: null,
    position: 'none',
    isValid: false
  });
  
  // 树节点状态
  const [treeNodes, setTreeNodes] = useState<FolderTreeNode[]>([]);
  
  // 构建树形结构
  const buildTree = (): FolderTreeNode[] => {
    // 创建节点映射
    const nodeMap = new Map<string, FolderTreeNode>();
    
    // 初始化所有节点
    folders.forEach(folder => {
      nodeMap.set(folder.path, {
        ...folder,
        id: folder.path,
        children: [],
        expanded: false,
        level: 0
      });
    });
    
    // 构建树（使用path作为key匹配父子关系）
    const tree: FolderTreeNode[] = [];
    
    nodeMap.forEach(node => {
      if (node.parent_folder_path) {
        const parent = nodeMap.get(node.parent_folder_path);
        if (parent) {
          parent.children.push(node);
          // 设置子节点的层级
          node.level = parent.level + 1;
        } else {
          // 父节点不存在，作为根节点
          tree.push(node);
        }
      } else {
        // 根节点
        tree.push(node);
      }
    });
    
    // 排序：先按是否为系统文件夹，再按order_index，最后按名称
    const sortNodes = (nodes: FolderTreeNode[]): FolderTreeNode[] => {
      return nodes.sort((a, b) => {
        // 系统文件夹在前
        if (a.is_system_folder && !b.is_system_folder) return -1;
        if (!a.is_system_folder && b.is_system_folder) return 1;
        
        // 按order_index排序
        if (a.order_index !== undefined && b.order_index !== undefined) {
          if (a.order_index < b.order_index) return -1;
          if (a.order_index > b.order_index) return 1;
        }
        
        // 按名称排序
        return a.name.localeCompare(b.name);
      });
    };
    
    // 递归排序
    const sortTree = (nodes: FolderTreeNode[]): FolderTreeNode[] => {
      const sorted = sortNodes(nodes);
      sorted.forEach(node => {
        if (node.children.length > 0) {
          node.children = sortTree(node.children);
        }
      });
      return sorted;
    };
    
    return sortTree(tree);
  };
  
  // 查找节点（支持UUID或path）
  const findNode = (nodes: FolderTreeNode[], folderIdentifier: string): FolderTreeNode | null => {
    for (const node of nodes) {
      // 支持UUID或path作为标识符
      if (node.path === folderIdentifier || node.path === folderIdentifier) return node;
      if (node.children.length > 0) {
        const found = findNode(node.children, folderIdentifier);
        if (found) return found;
      }
    }
    return null;
  };
  
  // 检查是否是有效的放置目标
  const isValidDropTarget = (draggedNode: FolderTreeNode | null, targetNode: FolderTreeNode | null, position: DropPosition): boolean => {
    if (!draggedNode || !targetNode) return false;
    
    // 不能拖拽到自己
    if (draggedNode.path === targetNode.path) return false;
    
    // 不能拖拽到自己的子文件夹中（防止循环）
    const isDescendant = (parentPath: string, nodePath: string, nodes: FolderTreeNode[]): boolean => {
      const node = findNode(nodes, parentId);
      if (!node) return false;
      
      const checkChildren = (children: FolderTreeNode[]): boolean => {
        for (const child of children) {
          if (child.path === nodePath) return true;
          if (child.children.length > 0 && checkChildren(child.children)) {
            return true;
          }
        }
        return false;
      };
      
      return checkChildren(node.children);
    };
    
    if (position === 'inside' && isDescendant(draggedNode.id, targetNode.id, treeNodes)) {
      return false;
    }
    
    // 系统文件夹可能不允许移动（取决于业务规则）
    if (targetNode.is_system_folder && position === 'inside') {
      // 通常不允许移动到系统文件夹中
      return false;
    }
    
    return true;
  };
  
  // 展开/收起节点
  const toggleExpand = (folderPath: string) => {
    const updateNode = (nodes: FolderTreeNode[]): FolderTreeNode[] => {
      return nodes.map(node => {
        if (node.path === folderPath) {
          return { ...node, expanded: !node.expanded };
        }
        
        if (node.children.length > 0) {
          return { ...node, children: updateNode(node.children) };
        }
        
        return node;
      });
    };
    
    setTreeNodes(prev => updateNode(prev));
  };
  
  // 递归展开到某个节点（支持UUID或path）
  const expandToFolder = (folderIdentifier: string, nodes: FolderTreeNode[]): FolderTreeNode[] => {
    return nodes.map(node => {
      let shouldExpand = false;
      
      // 检查是否是目标节点或其祖先
      const findPath = (currentNode: FolderTreeNode): boolean => {
        // 支持UUID或path作为标识符
        if (currentNode.id === folderIdentifier || currentNode.path === folderIdentifier) return true;
        
        for (const child of currentNode.children) {
          if (findPath(child)) return true;
        }
        
        return false;
      };
      
      shouldExpand = findPath(node);
      
      // 更新当前节点
      const updatedNode = {
        ...node,
        expanded: shouldExpand || node.expanded
      };
      
      // 递归更新子节点
      if (node.children.length > 0) {
        updatedNode.children = expandToFolder(folderIdentifier, node.children);
      }
      
      return updatedNode;
    });
  };
  
  // 初始化树节点
  useEffect(() => {
    const newTree = buildTree();
    if (currentFolderId) {
      setTreeNodes(expandToFolder(currentFolderId, newTree));
    } else {
      setTreeNodes(newTree);
    }
  }, [folders, currentFolderId]);
  
  // 拖拽开始事件
  const handleDragStart = (e: React.DragEvent, folderPath: string) => {
    const draggedNode = findNode(treeNodes, folderId);
    if (!draggedNode || draggedNode.is_system_folder) {
      e.preventDefault();
      return;
    }
    
    e.dataTransfer.setData('text/plain', folderId);
    e.dataTransfer.effectAllowed = 'move';
    
    setDragState({
      draggedFolderId: folderId,
      draggedFolderNode: draggedNode,
      isDragging: true
    });
    
    // 设置拖拽图片
    if (e.dataTransfer.setDragImage) {
      const dragImage = document.createElement('div');
      dragImage.textContent = draggedNode.name;
      dragImage.style.position = 'absolute';
      dragImage.style.left = '-1000px';
      dragImage.style.top = '-1000px';
      dragImage.style.background = 'white';
      dragImage.style.padding = '4px 8px';
      dragImage.style.border = '1px solid #ccc';
      dragImage.style.borderRadius = '4px';
      dragImage.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
      document.body.appendChild(dragImage);
      e.dataTransfer.setDragImage(dragImage, 0, 0);
      
      // 清理
      setTimeout(() => document.body.removeChild(dragImage), 0);
    }
  };
  
  // 拖拽经过事件
  const handleDragOver = (e: React.DragEvent, folderPath: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    const draggedNode = dragState.draggedFolderNode;
    const targetNode = findNode(treeNodes, folderId);
    
    if (!draggedNode || !targetNode) return;
    
    // 计算放置位置（基于鼠标在元素中的位置）
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const height = rect.height;
    
    let position: DropPosition = 'none';
    let isValid = false;
    
    // 计算放置位置
    if (y < height * 0.25) {
      position = 'before';
    } else if (y > height * 0.75) {
      position = 'after';
    } else {
      position = 'inside';
    }
    
    // 验证放置位置
    isValid = isValidDropTarget(draggedNode, targetNode, position);
    
    setDropTarget({
      targetFolderId: folderId,
      position,
      isValid
    });
    
    // 设置拖拽效果
    e.dataTransfer.dropEffect = isValid ? 'move' : 'none';
    
    // 如果拖拽到文件夹上且位置是inside，自动展开文件夹（延迟展开）
    if (position === 'inside' && isValid && !targetNode.expanded) {
      setTimeout(() => {
        toggleExpand(folderId);
      }, 800);
    }
  };
  
  // 拖拽离开事件
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // 清除放置目标状态
    setDropTarget({
      targetFolderId: null,
      position: 'none',
      isValid: false
    });
  };
  
  // 放置事件
  const handleDrop = async (e: React.DragEvent, folderPath: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    const draggedFolderId = dragState.draggedFolderId;
    const draggedNode = dragState.draggedFolderNode;
    const targetNode = findNode(treeNodes, folderId);
    
    if (!draggedFolderId || !draggedNode || !targetNode || !dropTarget.isValid) {
      resetDragState();
      return;
    }
    
    try {
      // 根据放置位置确定目标父文件夹ID
      let targetParentFolderId: string | undefined;
      
      if (dropTarget.position === 'inside') {
        // 放置到文件夹内部，成为其子文件夹
        targetParentFolderId = folderId;
      } else {
        // 放置为兄弟文件夹（前或后），保持相同的父文件夹
        targetParentFolderId = targetNode.parent_folder_path;
      }
      
      // 调用移动文件夹的API
      if (onMoveFolder) {
        await onMoveFolder(draggedFolderId, targetParentFolderId);
      }
      
      // 成功提示
      console.log(t('folderTree.moveSuccess', { from: draggedNode.name, to: targetNode.name }));
      
    } catch (error) {
      console.error(t('folderTree.moveFailed'), error);
      // 可以添加错误提示
    } finally {
      resetDragState();
    }
  };
  
  // 重置拖拽状态
  const resetDragState = () => {
    setDragState({
      draggedFolderId: null,
      draggedFolderNode: null,
      isDragging: false
    });
    
    setDropTarget({
      targetFolderId: null,
      position: 'none',
      isValid: false
    });
  };
  
  // 渲染树节点
  const renderTreeNode = (node: FolderTreeNode): React.ReactNode => {
    // 支持UUID或path作为标识符
    // 支持UUID或path作为标识符
    const isCurrent = node.path === currentFolderId || node.path === currentFolderId;
    const hasChildren = node.children.length > 0;
    const isDragged = dragState.draggedFolderId === node.path || dragState.draggedFolderId === node.path;
    const isDropTarget = dropTarget.targetFolderId === node.path || dropTarget.targetFolderId === node.path;
    
    return (
      <div key={node.path} className="relative">
        {/* 放置前的指示线 */}
        {isDropTarget && dropTarget.position === 'before' && dropTarget.isValid && (
          <div className="absolute left-0 right-0 top-0 h-0.5 bg-blue-500 z-10"></div>
        )}
        
        {/* 文件夹行 */}
        <div 
          className={`
            flex items-center py-2 px-2 rounded cursor-pointer transition-all duration-150
            ${isCurrent ? 'bg-blue-50 border border-blue-200' : ''}
            ${isDragged ? 'opacity-50 bg-gray-100' : ''}
            ${isDropTarget && dropTarget.position === 'inside' && dropTarget.isValid ? 'bg-blue-100 border border-blue-300' : ''}
            hover:bg-gray-100
          `}
          style={{ marginLeft: `${node.level * 16}px` }}
          onClick={() => onFolderSelect(node.path)}
          draggable={!node.is_system_folder}
          onDragStart={(e) => handleDragStart(e, node.path)}
          onDragOver={(e) => handleDragOver(e, node.path)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, node.path)}
        >
          {/* 展开/收起按钮 */}
          {hasChildren ? (
            <button 
              className="w-4 h-4 mr-1 flex-shrink-0 text-gray-500 hover:text-gray-700"
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(node.path);
              }}
            >
              {node.expanded ? (
                <ChevronDownIcon className="w-4 h-4" />
              ) : (
                <ChevronRightIcon className="w-4 h-4" />
              )}
            </button>
          ) : (
            <div className="w-5 mr-1"></div> // 占位，保持对齐
          )}
          
          {/* 文件夹图标 */}
          <div className="flex-shrink-0 mr-2">
            {node.expanded ? (
              <FolderOpenIcon className="w-5 h-5 text-yellow-500" />
            ) : (
              <FolderIcon className="w-5 h-5 text-yellow-500" />
            )}
          </div>
          
          {/* 文件夹信息 */}
          <div className="flex-1 min-w-0">
            <div className={`font-medium truncate ${isCurrent ? 'text-blue-600' : 'text-gray-800'}`}>
              {node.name}
              {dragState.isDragging && dragState.draggedFolderId === node.path && (
                <span className="ml-2 text-xs text-gray-500">{t('folderTree.dragging')}</span>
              )}
            </div>
            {/* Description removed as requested */}
          </div>
          
          {/* 文档计数 */}
          <div className="flex-shrink-0 mr-2 text-sm text-gray-500">
            {node.document_count || 0} {t('folderTree.documents')}
          </div>
          
          {/* 拖拽手柄（只在可拖拽时显示） */}
          {!node.is_system_folder && (
            <div 
              className="flex-shrink-0 p-1 text-gray-400 hover:text-blue-600 cursor-grab active:cursor-grabbing"
              title={t('folderTree.dragToMove')}
              onClick={(e) => e.stopPropagation()}
            >
              <ArrowsUpDownIcon className="w-4 h-4" />
            </div>
          )}
          
          {/* 删除按钮 */}
          {onDeleteFolder && !node.is_system_folder && (
            <button 
              className="flex-shrink-0 p-1 text-gray-400 hover:text-red-600"
              onClick={async (e) => {
                e.stopPropagation();
                const nodePathInfo = (node as any).path ? `\n目标路径: ${(node as any).path}` : '';
                const confirmed = await window.wetYesOrNo(
                  `${t('folderTree.confirmDelete', { name: node.name })}${nodePathInfo}`
                );
                if (confirmed) {
                  onDeleteFolder(node.path);
                }
              }}
              title={t('folderTree.deleteFolder')}
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          )}
        </div>
        
        {/* 放置后的指示线 */}
        {isDropTarget && dropTarget.position === 'after' && dropTarget.isValid && (
          <div className="absolute left-0 right-0 bottom-0 h-0.5 bg-blue-500 z-10"></div>
        )}
        
        {/* 子文件夹 */}
        {node.expanded && hasChildren && (
          <div className="relative">
            {/* 内部放置指示器（当拖拽到文件夹内部时） */}
            {isDropTarget && dropTarget.position === 'inside' && dropTarget.isValid && (
              <div className="absolute left-0 right-0 top-0 h-1 bg-blue-500 z-10"></div>
            )}
            {node.children.map(child => renderTreeNode(child))}
          </div>
        )}
      </div>
    );
  };
  
  // 全局拖拽结束事件
  useEffect(() => {
    const handleGlobalDragEnd = () => {
      resetDragState();
    };
    
    document.addEventListener('dragend', handleGlobalDragEnd);
    
    return () => {
      document.removeEventListener('dragend', handleGlobalDragEnd);
    };
  }, []);
  
  return (
    <div className="folder-tree">
      {/* 拖拽提示 */}
      {dragState.isDragging && (
        <div className="p-2 mb-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
          <div className="flex items-center">
            <ArrowDownOnSquareIcon className="w-4 h-4 mr-2" />
            <span>{t('folderTree.dragHint')}</span>
          </div>
        </div>
      )}
      
      {treeNodes.length === 0 ? (
        <div className="text-center py-6 text-gray-500">
          <FolderIcon className="w-12 h-12 mx-auto text-gray-300 mb-2" />
          <p>{t('folderTree.noFolders')}</p>
          <p className="text-sm mt-1">{t('folderTree.createFirstFolder')}</p>
        </div>
      ) : (
        <div className="space-y-1">
          {treeNodes.map(node => renderTreeNode(node))}
        </div>
      )}
      

    </div>
  );
};

export default FolderTree;