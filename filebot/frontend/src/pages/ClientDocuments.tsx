import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import appService from '../services/app.service';
import folderService from '../services/folder.service';
import documentService from '../services/document.service';

// 树状文件夹组件
interface FolderTreeNode {
  id: string;
  name: string;
  description?: string;
  parent_folder_id?: string;
  children?: FolderTreeNode[];
  expanded?: boolean;
  level?: number;
  path?: string;
  document_count?: number;
  total_size?: number;
}

interface FolderTreeProps {
  folders: FolderTreeNode[];
  currentFolderId: string | undefined;
  onFolderClick: (folderId: string) => void;
  onToggleExpand: (folderId: string) => void;
}

const FolderTree: React.FC<FolderTreeProps> = ({
  folders,
  currentFolderId,
  onFolderClick,
  onToggleExpand
}) => {
  const renderTree = (nodes: FolderTreeNode[], level: number = 0) => {
    return nodes.map(node => (
      <div key={node.id} className="select-none">
        <div
          className={`flex items-center py-2 px-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors ${
            (currentFolderId === node.id || currentFolderId === node.path) ? 'bg-blue-50 border border-blue-200' : ''
          }`}
          style={{ paddingLeft: `${level * 20 + 12}px` }}
          onClick={() => onFolderClick(node.path || node.id)}
        >
          {/* 展开/折叠图标 */}
          {node.children && node.children.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand(node.id);
              }}
              className="mr-2 w-5 h-5 flex items-center justify-center text-gray-500 hover:text-gray-700"
            >
              {node.expanded ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
                </svg>
              )}
            </button>
          )}
          
          {/* 占位空间（无子文件夹的情况） */}
          {(!node.children || node.children.length === 0) && (
            <div className="mr-7 w-5"></div>
          )}
          
          {/* 文件夹图标 */}
          <div className="mr-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
              </svg>
            </div>
          </div>
          
          {/* 文件夹信息 */}
          <div className="flex-grow min-w-0">
            <div className="font-medium text-gray-800 truncate">{node.name}</div>
            <div className="text-xs text-gray-500 truncate">
              {node.document_count !== undefined && (
                <span className="mr-2">{node.document_count} 个文档</span>
              )}
              {node.total_size !== undefined && node.total_size > 0 && (
                <span>{(node.total_size / 1024 / 1024).toFixed(1)} MB</span>
              )}
            </div>
          </div>
        </div>
        
        {/* 递归渲染子文件夹 */}
        {node.expanded && node.children && node.children.length > 0 && (
          <div className="mt-1">
            {renderTree(node.children, level + 1)}
          </div>
        )}
      </div>
    ));
  };

  return (
    <div className="space-y-1">
      {renderTree(folders)}
    </div>
  );
};

const ClientDocuments: React.FC = () => {
  const { appSlug, folderId } = useParams<{ appSlug: string; folderId: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<any>(null);
  const [folder, setFolder] = useState<any>(null);
  const [folderTree, setFolderTree] = useState<FolderTreeNode[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  
  // 文件上传和过滤状态
  const [fileTypeFilter, setFileTypeFilter] = useState<string>('all'); // all, image, document, media, component
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  useEffect(() => {
    fetchData();
  }, [appSlug, folderId, currentPage, pageSize]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // 获取应用详情
      const appData = await appService.getAppById(appSlug || '');
      if (appData) {
        setApp(appData);
        
        // 获取文件夹树
        const treeData = await folderService.getFolderTree(appData.id);
        // 初始化所有节点为展开状态（可选，根据需求调整）
        const initializeTree = (nodes: any[], level: number = 0): FolderTreeNode[] => {
          return nodes.map(node => ({
            ...node,
            expanded: true, // 默认展开所有节点
            level: level,
            children: node.children ? initializeTree(node.children, level + 1) : []
          }));
        };
        setFolderTree(initializeTree(treeData, 0));
        
        // 获取当前文件夹详情（如果有folderId，支持UUID或path）
        let currentFolderData = folder;
        if (folderId) {
          // 解码可能的URL编码（特别是path包含斜杠的情况）
          const folderIdentifier = decodeURIComponent(folderId);
          currentFolderData = await folderService.getFolder(folderIdentifier);
          setFolder(currentFolderData);
        } else if (treeData.length > 0) {
          // 如果没有folderId，默认选择第一个文件夹
          const firstFolder = findFirstFolder(treeData);
          if (firstFolder) {
            currentFolderData = firstFolder;
            setFolder(firstFolder);
            // 更新URL中的folderId（可选），优先使用path
            const folderIdentifier = getFolderIdentifier(firstFolder);
            const encodedIdentifier = encodeFolderIdentifier(folderIdentifier);
            navigate(`/apps/${appSlug}/folders/${encodedIdentifier}`, { replace: true });
            return;
          }
        }
        
        // 获取文件夹文档（带分页）
        const targetFolderIdentifier = folderId || (folder ? getFolderIdentifier(folder) : '');
        if (targetFolderIdentifier) {
          // 检查文件夹深度，如果深度>=6，获取所有子孙文档
          const folderNode = findFolderInTree(folderTree, currentFolderData?.id || '');
          if (folderNode && folderNode.level !== undefined && folderNode.level >= 6) {
            console.log(`📁 文件夹深度 ${folderNode.level} >= 6，获取所有子孙文档`);
            await fetchAllDescendantDocuments(folderNode);
          } else {
            const documentsData = await documentService.getDocuments(targetFolderIdentifier, {
              skip: (currentPage - 1) * pageSize,
              limit: pageSize,
              sort_by: 'created_at',
              sort_order: 'desc'
            });
            setDocuments(documentsData);
            
            // 获取文档总数用于分页（需要后端支持总数查询，暂时使用简单分页）
            // 这里假设返回的数组长度小于limit时表示最后一页
            if (documentsData.length < pageSize) {
              setTotalPages(currentPage);
            } else {
              // 暂时设置为当前页+5，实际应该从API获取总数
              setTotalPages(currentPage + 5);
            }
          }
        }
        
        setLoading(false);
      }
    } catch (err: any) {
      console.error('获取数据失败:', err);
      setLoading(false);
    }
  };

  // 查找树中的第一个文件夹（用于默认选择）
  const findFirstFolder = (nodes: any[]): any | null => {
    for (const node of nodes) {
      return node;
    }
    return null;
  };

  // 获取文件夹标识符（优先使用path，其次使用id）
  const getFolderIdentifier = (folder: any): string => {
    return folder?.path || folder?.id || '';
  };

  // 编码文件夹标识符用于URL（对path进行编码）
  const encodeFolderIdentifier = (identifier: string): string => {
    // 如果是path（以/开头），进行URI编码
    if (identifier.startsWith('/')) {
      return encodeURIComponent(identifier);
    }
    return identifier;
  };

  // 递归查找文件夹节点
  const findFolderInTree = (nodes: FolderTreeNode[], folderId: string): FolderTreeNode | null => {
    for (const node of nodes) {
      if (node.id === folderId) {
        return node;
      }
      if (node.children) {
        const found = findFolderInTree(node.children, folderId);
        if (found) return found;
      }
    }
    return null;
  };

  // 递归获取文件夹的所有子孙文件夹标识符（路径优先）
  const getAllDescendantFolderIdentifiers = (node: FolderTreeNode): string[] => {
    const identifiers: string[] = [];
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        // 使用路径优先的标识符
        const childIdentifier = getFolderIdentifier(child);
        identifiers.push(childIdentifier);
        identifiers.push(...getAllDescendantFolderIdentifiers(child));
      }
    }
    return identifiers;
  };

  // 获取文件夹及其所有子孙文件夹的文档
  const fetchAllDescendantDocuments = async (folderNode: FolderTreeNode) => {
    try {
      // 获取当前文件夹和所有子孙文件夹的标识符
      const currentFolderIdentifier = getFolderIdentifier(folderNode);
      const folderIdentifiers = [currentFolderIdentifier, ...getAllDescendantFolderIdentifiers(folderNode)];
      console.log(`📁 获取 ${folderIdentifiers.length} 个文件夹的文档（深度 ${folderNode.level}）`);
      
      // 为每个文件夹获取文档
      const allDocuments: any[] = [];
      for (const folderId of folderIdentifiers) {
        try {
          const documents = await documentService.getDocuments(folderId, {
            skip: (currentPage - 1) * pageSize,
            limit: pageSize,
            sort_by: 'created_at',
            sort_order: 'desc'
          });
          allDocuments.push(...documents);
        } catch (err) {
          console.error(`获取文件夹 ${folderId} 的文档失败:`, err);
        }
      }
      
      // 去重（按ID）
      const uniqueDocuments = allDocuments.filter((doc, index, self) => 
        index === self.findIndex(d => d.id === doc.id)
      );
      
      console.log(`✅ 共获取 ${uniqueDocuments.length} 个文档`);
      setDocuments(uniqueDocuments);
      
      // 更新分页信息
      setTotalPages(1);
      setCurrentPage(1);
    } catch (err: any) {
      console.error('获取子孙文档失败:', err);
      setDocuments([]);
    }
  };

  // 更新树节点的展开状态
  const updateTreeExpansion = (nodes: FolderTreeNode[], folderId: string): FolderTreeNode[] => {
    return nodes.map(node => {
      if (node.id === folderId) {
        return { ...node, expanded: !node.expanded };
      }
      if (node.children) {
        return { ...node, children: updateTreeExpansion(node.children, folderId) };
      }
      return node;
    });
  };

  // 处理文件夹点击
  const handleFolderClick = (folderIdentifier: string) => {
    const encodedIdentifier = encodeFolderIdentifier(folderIdentifier);
    navigate(`/apps/${appSlug}/folders/${encodedIdentifier}`);
  };

  // 处理树节点展开/折叠
  const handleToggleExpand = (folderId: string) => {
    setFolderTree(prevTree => updateTreeExpansion(prevTree, folderId));
  };

  // 处理页面变化
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 处理页面大小变化
  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理文档下载
  const handleDownload = async (documentId: string, filename: string) => {
    try {
      console.log('开始下载文档:', documentId, filename);
      const blob = await documentService.downloadDocument(documentId);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = filename;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
      console.log('文档下载完成:', filename);
    } catch (err: any) {
      console.error('下载失败:', err);
      window.showWetAlert(`下载失败: ${err.message || '未知错误'}`);
    }
  };

  // 处理文档预览
  const handlePreview = (doc: any) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    window.open(`/documents/${docPath.replace(/^\//, '')}`, '_blank');
  };

  // 处理文件上传
  const handleFileUpload = async (files: FileList) => {
    if (!folderId && !folder?.id) {
      window.showWetAlert('请先选择一个文件夹');
      return;
    }

    // 获取文件夹标识符（路径优先）
    const targetFolderIdentifier = folderId || (folder ? getFolderIdentifier(folder) : '');
    if (!targetFolderIdentifier) {
      window.showWetAlert('无法确定目标文件夹');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    const uploadPromises = Array.from(files).map(async (file, index) => {
      try {
        // 构建上传请求，优先使用folder_path
        const uploadRequest: any = {
          file,
          title: file.name.replace(/\.[^/.]+$/, ""), // 移除扩展名作为标题
          description: `Uploaded on ${new Date().toLocaleDateString()}`
        };
        
        // 路径优先：如果是路径，使用folder_path；否则使用folder_id（向后兼容）
        if (targetFolderIdentifier.startsWith('/')) {
          uploadRequest.folder_path = targetFolderIdentifier;
          console.log('🔍 [DEBUG] ClientDocuments upload: using folder_path:', targetFolderIdentifier);
        } else {
          uploadRequest.folder_id = targetFolderIdentifier;
          console.warn('⚠️ ClientDocuments upload: using deprecated folder_id:', targetFolderIdentifier);
        }

        // 模拟上传进度（实际API可能不支持进度事件）
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            const newProgress = prev + (10 / files.length);
            return newProgress > 90 ? 90 : newProgress;
          });
        }, 200);

        const document = await documentService.uploadDocument(uploadRequest);
        
        clearInterval(progressInterval);
        setUploadProgress(prev => prev + (10 / files.length)); // 完成这个文件

        return document;
      } catch (error) {
        console.error(`文件上传失败 ${file.name}:`, error);
        return null;
      }
    });

    try {
      const results = await Promise.all(uploadPromises);
      setUploadProgress(100);
      
      // 等待1秒显示完成状态
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 刷新文档列表
      fetchData();
      
      const successCount = results.filter(r => r !== null).length;
      window.showWetAlert(`上传完成！成功: ${successCount} 个文件, 失败: ${files.length - successCount} 个文件`);
    } catch (error) {
      console.error('上传过程中出错:', error);
      window.showWetAlert('上传过程中出现错误');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // 处理拖放事件
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  // 处理文件选择器
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files);
      // 重置input以便可以选择相同文件再次上传
      e.target.value = '';
    }
  };

  // 过滤文档函数
  const filterDocuments = (docs: any[]) => {
    let filtered = [...docs];
    
    // 应用文件类型过滤
    if (fileTypeFilter !== 'all') {
      filtered = filtered.filter(doc => {
        const fileType = doc.file_type?.toLowerCase() || '';
        
        switch (fileTypeFilter) {
          case 'image':
            return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'svg'].includes(fileType);
          case 'document':
            return ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'html', 'htm'].includes(fileType);
          case 'media':
            return ['mp4', 'avi', 'mov', 'wmv', 'mp3', 'wav', 'ogg'].includes(fileType);
          case 'component':
            // 组件类型可能基于metadata或其他字段
            return doc.file_type === 'html' || doc.file_type === 'htm' || 
                   (doc.document_metadata && doc.document_metadata.component_type);
          default:
            return true;
        }
      });
    }
    
    return filtered;
  };

  // 处理文件类型过滤器变化
  const handleFileTypeFilterChange = (type: string) => {
    setFileTypeFilter(type);
    // 注意：这里我们只是设置了过滤器状态，实际过滤在getDisplayDocuments中应用
  };

  // 处理路径显示 - 从文件夹路径或文档路径获取
  const getCurrentPath = () => {
    return folder?.path || folder?.name || '未选择文件夹';
  };

  // 获取显示的文档（应用搜索和过滤）
  const getDisplayDocuments = () => {
    const docsToDisplay = searchResults !== null ? searchResults : documents;
    return filterDocuments(docsToDisplay);
  };

  // 处理搜索
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!searchQuery.trim()) {
      // 如果搜索查询为空，清除搜索结果
      setSearchResults(null);
      return;
    }
    
    if (!folderId) {
      window.showWetAlert('文件夹ID缺失，无法搜索');
      return;
    }
    
    setIsSearching(true);
    
    try {
      const results = await documentService.searchDocuments({
        q: searchQuery.trim(),
        folder_id: folderId
      });
      setSearchResults(results);
    } catch (error) {
      console.error('搜索失败:', error);
      window.showWetAlert('搜索失败，请稍后重试');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // 清除搜索
  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  // 检查是否正在显示搜索结果
  const isShowingSearchResults = () => {
    return searchResults !== null && searchQuery.trim() !== '';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 头部面包屑导航 */}
        <header className="mb-8">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-4">
            <Link to="/apps" className="hover:text-blue-600">应用列表</Link>
            <span>›</span>
            <Link to={`/apps/${appSlug}`} className="hover:text-blue-600">{app?.name || '应用'}</Link>
            <span>›</span>
            <span className="text-gray-700 font-medium">{folder?.name || '当前文件夹'}</span>
          </div>
          
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{folder?.name || '文件夹浏览'}</h1>
              <p className="text-gray-600 mt-2">
                {app?.name} • {folder?.description || '浏览文件夹内容和文档'}
                {folder?.document_count !== undefined && (
                  <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded">
                    {folder.document_count} 个文档
                  </span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <Link 
                to={`/apps/${appSlug}`}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                返回应用首页
              </Link>
            </div>
          </div>
        </header>

        {/* 主要内容 - 两栏布局 */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">加载文件夹内容中...</p>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* 左侧文件夹导航 - 占1/3 */}
            <div className="lg:w-[30%]">
              <div className="bg-white rounded-xl shadow overflow-hidden">
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                  <h2 className="text-xl font-bold text-gray-800">文件夹树状视图</h2>
                  <p className="text-gray-600 text-sm mt-1">完整的文件夹层级结构，支持展开/折叠</p>
                </div>
                
                {folderTree.length === 0 ? (
                  <div className="p-8 text-center">
                    <div className="text-gray-400 mb-4">
                      <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">无文件夹</h3>
                    <p className="text-gray-500">此应用没有文件夹。</p>
                  </div>
                ) : (
                  <div className="p-4 max-h-[600px] overflow-y-auto">
                    <FolderTree 
                      folders={folderTree}
                      currentFolderId={folderId ? decodeURIComponent(folderId) : (folder ? getFolderIdentifier(folder) : undefined)}
                      onFolderClick={handleFolderClick}
                      onToggleExpand={handleToggleExpand}
                    />
                  </div>
                )}
                
                {/* 当前文件夹信息 */}
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  <h4 className="font-medium text-gray-700 text-sm mb-2">当前文件夹信息</h4>
                  <div className="space-y-1 text-xs text-gray-600">
                    <div className="flex justify-between">
                      <span>路径:</span>
                      <span className="font-mono truncate max-w-[200px]" title={folder?.path}>{folder?.path || '/'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>文档数:</span>
                      <span>{documents.length} 个</span>
                    </div>
                    <div className="flex justify-between">
                      <span>创建时间:</span>
                      <span>{folder?.created_at ? new Date(folder.created_at).toLocaleDateString() : '未知'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 右侧文档列表 - 占2/3 */}
            <div className="lg:w-[70%]">
              <div className="bg-white rounded-xl shadow overflow-hidden">
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100">
                  <div className="space-y-4">
                    {/* 标题区域 */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h2 className="text-xl font-bold text-gray-800">文档列表</h2>
                        <p className="text-gray-600 text-sm mt-1">
                          显示最新100个文档
                          {isShowingSearchResults() && (
                            <span className="ml-2 text-blue-600 font-medium">
                              (搜索结果)
                            </span>
                          )}
                        </p>
                      </div>
                    </div>

                    {/* 文件操作功能区 */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* 左侧：拖放区域 */}
                        <div 
                          className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                            dragActive 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'border-gray-300 hover:border-blue-400 hover:bg-blue-25'
                          }`}
                          onDragEnter={handleDragEnter}
                          onDragLeave={handleDragLeave}
                          onDragOver={handleDragOver}
                          onDrop={handleDrop}
                        >
                          <div className="flex flex-col items-center justify-center h-full">
                            <div className="text-3xl mb-2">📁</div>
                            <p className="font-medium text-gray-700">拖放文件到此处上传</p>
                            <p className="text-sm text-gray-500 mt-1">支持图片、文档、媒体文件</p>
                            
                            <div className="mt-4">
                              <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer">
                                <span>选择文件</span>
                                <input 
                                  type="file" 
                                  multiple 
                                  className="hidden" 
                                  onChange={handleFileSelect}
                                  accept="image/*,.pdf,.doc,.docx,.txt,.mp4,.avi,.mov,.mp3,.html,.htm"
                                />
                              </label>
                            </div>
                            
                            {uploading && (
                              <div className="mt-4 w-full">
                                <div className="flex justify-between text-sm text-gray-600 mb-1">
                                  <span>上传中...</span>
                                  <span>{Math.round(uploadProgress)}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${uploadProgress}%` }}
                                  ></div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* 中间：路径和类型过滤 */}
                        <div className="space-y-4">
                          {/* 路径显示 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              当前路径
                            </label>
                            <div className="flex items-center bg-white border border-gray-300 rounded-lg px-3 py-2">
                              <span className="text-gray-400 mr-2">📍</span>
                              <span className="text-gray-800 font-mono text-sm truncate" title={getCurrentPath()}>
                                {getCurrentPath()}
                              </span>
                            </div>
                          </div>

                          {/* 文件类型过滤 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              文件类型过滤
                            </label>
                            <div className="flex flex-wrap gap-2">
                              {[
                                { id: 'all', label: '全部', icon: '📄' },
                                { id: 'image', label: '图片', icon: '🖼️' },
                                { id: 'document', label: '文档', icon: '📝' },
                                { id: 'media', label: '媒体', icon: '🎬' },
                                { id: 'component', label: '组件', icon: '🧩' }
                              ].map(type => (
                                <button
                                  key={type.id}
                                  type="button"
                                  onClick={() => handleFileTypeFilterChange(type.id)}
                                  className={`flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                    fileTypeFilter === type.id
                                      ? 'bg-blue-600 text-white'
                                      : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                                  }`}
                                >
                                  <span className="mr-1.5">{type.icon}</span>
                                  {type.label}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* 右侧：统计信息 */}
                        <div className="bg-white border border-gray-200 rounded-lg p-4">
                          <h4 className="font-medium text-gray-700 text-sm mb-3">📊 当前文件夹统计</h4>
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">文档总数:</span>
                              <span className="font-medium">{documents.length}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">显示文档:</span>
                              <span className="font-medium">{getDisplayDocuments().length}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">文件夹大小:</span>
                              <span className="font-medium">
                                {(documents.reduce((sum, doc) => sum + doc.file_size, 0) / 1024 / 1024).toFixed(2)} MB
                              </span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">当前过滤:</span>
                              <span className="font-medium">
                                {fileTypeFilter === 'all' ? '全部类型' : 
                                 fileTypeFilter === 'image' ? '图片' :
                                 fileTypeFilter === 'document' ? '文档' :
                                 fileTypeFilter === 'media' ? '媒体' : '组件'}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 搜索栏 */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="text-sm text-gray-600">
                        快速查找文档
                      </div>
                      <form onSubmit={handleSearch} className="flex items-center">
                        <div className="relative">
                          <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="搜索文档标题..."
                            className="w-full sm:w-64 px-4 py-2 pl-10 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                          <div className="absolute left-3 top-2.5 text-gray-400">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                          </div>
                          {searchQuery && (
                            <button
                              type="button"
                              onClick={handleClearSearch}
                              className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                              </svg>
                            </button>
                          )}
                        </div>
                        <button
                          type="submit"
                          disabled={isSearching}
                          className="ml-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                        >
                          {isSearching ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              搜索
                            </>
                          ) : '搜索'}
                        </button>
                      </form>
                    </div>
                  </div>
                  
                  {isShowingSearchResults() && (
                    <div className="mt-3 flex items-center justify-between bg-blue-50 p-3 rounded-lg">
                      <div className="text-sm text-blue-700">
                        <span className="font-medium">{searchResults?.length || 0}</span> 个搜索结果，关键词: "<span className="font-medium">{searchQuery}</span>"
                      </div>
                      <button
                        type="button"
                        onClick={handleClearSearch}
                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                      >
                        清除搜索
                      </button>
                    </div>
                  )}
                </div>
                
                {getDisplayDocuments().length === 0 ? (
                  <div className="p-12 text-center">
                    <div className="text-gray-400 mb-6">
                      <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                    </div>
                    <h3 className="text-xl font-medium text-gray-900 mb-2">
                      {isShowingSearchResults() ? '未找到搜索结果' : '暂无文档'}
                    </h3>
                    <p className="text-gray-500 mb-6">
                      {isShowingSearchResults() 
                        ? `没有找到与"${searchQuery}"相关的文档。请尝试其他关键词。`
                        : '此文件夹还没有任何文档。'}
                    </p>
                    {isShowingSearchResults() && (
                      <button
                        onClick={handleClearSearch}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                      >
                        清除搜索
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            文档名称
                          </th>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            类型
                          </th>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            大小
                          </th>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            页数
                          </th>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            上传时间
                          </th>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            操作
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {getDisplayDocuments().map(doc => (
                          <tr key={doc.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div>
                                <div className="font-medium text-gray-900">{doc.title}</div>
                                <div className="text-sm text-gray-500 truncate max-w-xs">{doc.original_filename}</div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                doc.file_type === 'pdf' ? 'bg-red-100 text-red-800' :
                                doc.file_type === 'html' || doc.file_type === 'htm' ? 'bg-green-100 text-green-800' :
                                doc.file_type === 'doc' || doc.file_type === 'docx' ? 'bg-blue-100 text-blue-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {doc.file_type.toUpperCase()}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {doc.pages || '-'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(doc.created_at).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <div className="flex space-x-2">
                                <button 
                                  onClick={() => handleDownload(doc.path || doc.storage_path || doc.id, doc.original_filename)}
                                  className="text-blue-600 hover:text-blue-900 px-3 py-1 bg-blue-50 hover:bg-blue-100 rounded text-sm"
                                >
                                  下载
                                </button>
                                <button 
                                  onClick={() => handlePreview(doc)}
                                  className="text-gray-600 hover:text-gray-900 px-3 py-1 bg-gray-50 hover:bg-gray-100 rounded text-sm"
                                >
                                  预览
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    
                    {/* 表格底部信息 */}
                    <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <div>
                          显示 <span className="font-medium">{getDisplayDocuments().length}</span> 个文档
                          {isShowingSearchResults() && (
                            <span className="ml-2 text-blue-600">
                              (搜索结果)
                            </span>
                          )}
                        </div>
                        <div>
                          总大小: <span className="font-medium">
                            {(getDisplayDocuments().reduce((sum, doc) => sum + doc.file_size, 0) / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              {/* 当前文件夹统计信息 */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl shadow p-4">
                  <div className="flex items-center">
                    <div className="mr-4">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">文档总数</h4>
                      <p className="text-2xl font-bold text-gray-900">{documents.length}</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow p-4">
                  <div className="flex items-center">
                    <div className="mr-4">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                        </svg>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">PDF文档</h4>
                      <p className="text-2xl font-bold text-gray-900">
                        {documents.filter(d => d.file_type === 'pdf').length}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow p-4">
                  <div className="flex items-center">
                    <div className="mr-4">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path>
                        </svg>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">总大小</h4>
                      <p className="text-2xl font-bold text-gray-900">
                        {(documents.reduce((sum, doc) => sum + doc.file_size, 0) / 1024 / 1024).toFixed(1)} MB
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 底部 */}
        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>FileBot Client Portal • {app?.name || '应用'} • {folder?.name || '文件夹'}</p>
          <p className="mt-1">显示最新100个文档 • 左侧显示完整的文件夹树状视图</p>
        </footer>
      </div>
    </div>
  );
};

export default ClientDocuments;