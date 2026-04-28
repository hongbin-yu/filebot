import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import appService from '../services/app.service';
import folderService from '../services/folder.service';
import documentService from '../services/document.service';

// 树状文件夹组件 (从ClientDocuments.tsx复制)
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

const ClientDashboard: React.FC = () => {
  const { appSlug } = useParams<{ appSlug: string }>();
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

  useEffect(() => {
    fetchData();
  }, [appSlug]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // 获取应用详情
      const appData = await appService.getAppById(appSlug || '');
      if (appData) {
        setApp(appData);
        
        // 获取文件夹树
        const treeData = await folderService.getFolderTree(appData.id);
        // 初始化所有节点为展开状态
        const initializeTree = (nodes: any[], level: number = 0): FolderTreeNode[] => {
          return nodes.map(node => ({
            ...node,
            expanded: true, // 默认展开所有节点
            level: level,
            children: node.children ? initializeTree(node.children, level + 1) : []
          }));
        };
        const initializedTree = initializeTree(treeData, 0);
        setFolderTree(initializedTree);
        
        // 如果没有选中文件夹，选择第一个文件夹
        if (initializedTree.length > 0 && !folder) {
          const firstFolder = findFirstFolder(initializedTree);
          if (firstFolder) {
            setFolder(firstFolder);
            // 获取该文件夹的文档，优先使用path
            const folderIdentifier = getFolderIdentifier(firstFolder);
            await fetchFolderDocuments(folderIdentifier);
          }
        } else if (folder) {
          // 如果已有选中文件夹，获取其文档
          const folderIdentifier = getFolderIdentifier(folder);
          await fetchFolderDocuments(folderIdentifier);
        }
        
        setLoading(false);
      }
    } catch (err: any) {
      console.error('获取数据失败:', err);
      setLoading(false);
    }
  };

  // 获取文件夹文档（支持路径和ID）
  const fetchFolderDocuments = async (folderIdentifier: string) => {
    try {
      const documentsData = await documentService.getDocuments(folderIdentifier, {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort_by: 'created_at',
        sort_order: 'desc'
      });
      setDocuments(documentsData);
      
      // 简单的分页逻辑
      if (documentsData.length < pageSize) {
        setTotalPages(currentPage);
      } else {
        setTotalPages(currentPage + 5);
      }
    } catch (err: any) {
      console.error('获取文档失败:', err);
      setDocuments([]);
    }
  };

  // 查找树中的第一个文件夹
  const findFirstFolder = (nodes: any[]): any | null => {
    for (const node of nodes) {
      return node;
    }
    return null;
  };

  // 递归查找文件夹节点
  const findFolderInTree = (nodes: FolderTreeNode[], folderIdentifier: string): FolderTreeNode | null => {
    for (const node of nodes) {
      // 匹配ID或path
      if (node.id === folderIdentifier || node.path === folderIdentifier) {
        return node;
      }
      if (node.children) {
        const found = findFolderInTree(node.children, folderIdentifier);
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
      for (const folderIdentifier of folderIdentifiers) {
        try {
          const documents = await documentService.getDocuments(folderIdentifier, {
            skip: 0,
            limit: 100, // 限制每个文件夹最多100个文档
            sort_by: 'created_at',
            sort_order: 'desc'
          });
          allDocuments.push(...documents);
        } catch (err) {
          console.error(`获取文件夹 ${folderIdentifier} 的文档失败:`, err);
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

  // 处理文件夹点击
  const handleFolderClick = async (folderIdentifier: string) => {
    // 查找文件夹详情
    const folderNode = findFolderInTree(folderTree, folderIdentifier);
    if (folderNode) {
      setFolder(folderNode);
      // 获取该文件夹的文档
      const targetIdentifier = getFolderIdentifier(folderNode);
      
      // 检查文件夹深度，如果深度>=6，获取所有子孙文档
      if (folderNode.level !== undefined && folderNode.level >= 6) {
        console.log(`📁 文件夹深度 ${folderNode.level} >= 6，获取所有子孙文档`);
        await fetchAllDescendantDocuments(folderNode);
      } else {
        await fetchFolderDocuments(targetIdentifier);
      }
      
      // 更新URL（可选，保持URL与状态同步）
      const encodedIdentifier = encodeFolderIdentifier(targetIdentifier);
      navigate(`/apps/${appSlug}/folders/${encodedIdentifier}/documents`, { replace: true });
    }
  };

  // 处理树节点展开/折叠
  const handleToggleExpand = (folderId: string) => {
    setFolderTree(prevTree => updateTreeExpansion(prevTree, folderId));
  };

  // 处理页面变化
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    if (folder) {
      const folderIdentifier = getFolderIdentifier(folder);
      fetchFolderDocuments(folderIdentifier);
    }
  };

  // 处理页面大小变化
  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
    if (folder) {
      const folderIdentifier = getFolderIdentifier(folder);
      fetchFolderDocuments(folderIdentifier);
    }
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

  // 处理搜索
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!searchQuery.trim()) {
      // 如果搜索查询为空，清除搜索结果
      setSearchResults(null);
      return;
    }
    
    if (!folder) {
      window.showWetAlert('请先选择一个文件夹');
      return;
    }
    
    setIsSearching(true);
    
    try {
      const results = await documentService.searchDocuments({
        q: searchQuery.trim(),
        folder_id: folder.id
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

  // 获取当前显示的文档（搜索结果或全部文档）
  const getDisplayDocuments = () => {
    return searchResults !== null ? searchResults : documents;
  };

  // 检查是否正在显示搜索结果
  const isShowingSearchResults = () => {
    return searchResults !== null && searchQuery.trim() !== '';
  };

  // 获取应用的索引字段（用于表格列）
  const getAppIndices = () => {
    if (!app || !app.settings || !app.settings.indices) {
      return []; // Smarti应用可能没有indices字段
    }
    return app.settings.indices;
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
            {folder && (
              <>
                <span>›</span>
                <span className="text-gray-700 font-medium">{folder?.name || '文件夹'}</span>
              </>
            )}
          </div>
          
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{app?.name || '应用详情'}</h1>
              <p className="text-gray-600 mt-2">
                {app?.description || '公共文档门户'}
                {folder && (
                  <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded">
                    {folder.document_count || 0} 个文档
                  </span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <Link 
                to="/apps"
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                返回应用列表
              </Link>
            </div>
          </div>
        </header>

        {/* 主要内容 - 两栏布局 */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">加载应用中...</p>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* 左侧文件夹树 - 占30% */}
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
                      currentFolderId={folder ? getFolderIdentifier(folder) : undefined}
                      onFolderClick={handleFolderClick}
                      onToggleExpand={handleToggleExpand}
                    />
                  </div>
                )}
                
                {/* 当前文件夹信息 */}
                {folder && (
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
                )}
              </div>
            </div>

            {/* 右侧文档表格 - 占70% */}
            <div className="lg:w-[70%]">
              {folder ? (
                <div className="bg-white rounded-xl shadow overflow-hidden">
                  <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h2 className="text-xl font-bold text-gray-800">文档列表</h2>
                        <p className="text-gray-600 text-sm mt-1">
                          文件夹: <span className="font-medium">{folder.name}</span>
                          {isShowingSearchResults() && (
                            <span className="ml-2 text-blue-600 font-medium">
                              (搜索结果)
                            </span>
                          )}
                        </p>
                      </div>
                      
                      {/* 搜索栏 */}
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
              ) : (
                <div className="bg-white rounded-xl shadow p-12 text-center">
                  <div className="text-gray-400 mb-6">
                    <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                    </svg>
                  </div>
                  <h3 className="text-xl font-medium text-gray-900 mb-2">请选择一个文件夹</h3>
                  <p className="text-gray-500 mb-6">点击左侧的文件夹树，查看其中的文档。</p>
                </div>
              )}
              
              {/* 当前文件夹统计信息 */}
              {folder && documents.length > 0 && (
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
              )}
            </div>
          </div>
        )}

        {/* 底部 */}
        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>FileBot Client Portal • {app?.name || '应用'} • {folder?.name || '请选择文件夹'}</p>
          <p className="mt-1">30/70分栏布局 • 左侧显示完整的文件夹树状视图 • 右侧显示文档表格</p>
        </footer>
      </div>
    </div>
  );
};

export default ClientDashboard;