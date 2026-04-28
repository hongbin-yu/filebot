import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
// react-data-table-component v7.x exports differently in CJS vs ESM
// Using namespace import + .default handles both Vite CJS/ESM interop modes
import RDT from 'react-data-table-component';
const DataTable = RDT.default || RDT;
import appService, { App } from '../../services/app.service';
import folderService, { Folder } from '../../services/folder.service';
import documentService, { Document } from '../../services/document.service';

const AdminDocuments: React.FC = () => {
  const { appSlug, folderId } = useParams<{ appSlug: string; folderId: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<App | null>(null);
  const [folder, setFolder] = useState<Folder | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [deletingAll, setDeletingAll] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      if (!appSlug || !folderId) {
        setError('缺少应用或文件夹参数');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // 1. 获取应用信息
        const apps = await appService.getApps();
        const foundApp = apps.find(a => a.slug === appSlug || a.id === appSlug);
        if (!foundApp) {
          setError(`应用 "${appSlug}" 不存在`);
          setLoading(false);
          return;
        }
        setApp(foundApp);

        // 2. 获取文件夹信息 - 直接通过标识符（UUID或路径）获取
        const folderIdentifier = decodeURIComponent(folderId);
        const foundFolder = await folderService.getFolder(folderIdentifier);
        if (!foundFolder) {
          setError(`文件夹 "${folderIdentifier}" 不存在`);
          setLoading(false);
          return;
        }
        setFolder(foundFolder);

        // 3. 获取文档列表
        const docs = await documentService.getDocuments(folderIdentifier);
        setDocuments(docs);

      } catch (err: any) {
        console.error('加载数据失败:', err);
        setError(`无法加载数据: ${err.response?.data?.detail || err.message || '未知错误'}`);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [appSlug, folderId]);

  // 预览文档
  const handlePreview = (doc: any) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    navigate(`/admin/documents/${docPath.replace(/^\//, '')}`);
  };

  // 开始编辑文档
  const handleEdit = (doc: Document) => {
    setEditingDoc(doc);
    setEditTitle(doc.title || '');
    setEditDescription(doc.description || '');
  };

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!editingDoc) return;
    
    try {
      const editDocId = editingDoc.path || editingDoc.storage_path || editingDoc.id;
      const updatedDoc = await documentService.updateDocument(editDocId, {
        title: editTitle,
        description: editDescription
      });
      
      setDocuments(docs => docs.map(doc => 
        doc.id === updatedDoc.id ? updatedDoc : doc
      ));
      
      setEditingDoc(null);
      setEditTitle('');
      setEditDescription('');
    } catch (err: any) {
      console.error('更新文档失败:', err);
      window.showWetAlert(`更新文档失败: ${err.message || '未知错误'}`);
    }
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditTitle('');
    setEditDescription('');
  };

  // 删除文档
  const handleDelete = async (documentId: string) => {
    const targetDoc = documents.find(d => d.id === documentId);
    const docName = targetDoc?.original_filename || targetDoc?.title || '此文档';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\n存储路径: ${docPathStr}` : '';
    const confirmedDel = await window.wetYesOrNo(`确定要删除 "${docName}" 吗？此操作不可撤销。${docPathInfo}`);
    if (!confirmedDel) return;
    
    try {
      const deleteIdentifier = targetDoc?.path || targetDoc?.storage_path || documentId;
      await documentService.deleteDocument(deleteIdentifier);
      setDocuments(docs => docs.filter(doc => doc.id !== documentId));
      window.showWetAlert('文档删除成功');
    } catch (err: any) {
      console.error('删除文档失败:', err);
      window.showWetAlert(`删除文档失败: ${err.message || '未知错误'}`);
    }
  };

  // 删除所有文档
  const handleDeleteAllDocuments = async () => {
    if (documents.length === 0) {
      window.showWetAlert('当前文件夹没有文档可删除');
      return;
    }
    
    const folderName = folder?.name || '当前文件夹';
    const folderPathStr = folder?.path ? `\n目标路径: ${folder.path}` : '';
    const confirmedAll = await window.wetYesOrNo(`确定要删除 ${folderName} 中的所有 ${documents.length} 个文档吗？此操作不可撤销，且会删除所有文件。${folderPathStr}`);
    if (!confirmedAll) return;
    
    try {
      setDeletingAll(true);
      let deletedCount = 0;
      let failedCount = 0;
      
      for (const doc of documents) {
        try {
          const deleteId = doc.path || doc.storage_path || doc.id;
          await documentService.deleteDocument(deleteId);
          deletedCount++;
        } catch (err: any) {
          console.error(`删除文档 ${doc.original_filename} 失败:`, err);
          failedCount++;
        }
      }
      
      setDocuments([]);
      
      if (failedCount === 0) {
        window.showWetAlert(`成功删除所有 ${deletedCount} 个文档`);
      } else {
        window.showWetAlert(`删除完成：成功删除 ${deletedCount} 个文档，${failedCount} 个文档删除失败`);
      }
    } catch (err: any) {
      console.error('批量删除文档失败:', err);
      window.showWetAlert(`批量删除失败: ${err.message || '未知错误'}`);
    } finally {
      setDeletingAll(false);
    }
  };

  // DataTable列定义
  const columns = useMemo(() => [
    {
      name: '文档',
      selector: (row: Document) => row.title,
      sortable: true,
      grow: 2,
      cell: (row: Document) => (
        <div>
          <div className="font-medium text-gray-900">{row.title}</div>
          <div className="text-xs text-gray-500">{row.original_filename}</div>
        </div>
      ),
    },
    {
      name: '类型',
      selector: (row: Document) => row.file_type,
      sortable: true,
      width: '80px',
      cell: (row: Document) => (
        <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
          {row.file_type.toUpperCase()}
        </span>
      ),
    },
    {
      name: '状态',
      selector: (row: Document) => row.conversion_status,
      sortable: true,
      width: '100px',
      cell: (row: Document) => (
        <span className={`px-2 py-1 text-xs font-medium rounded ${
          row.conversion_status === 'completed' 
            ? 'bg-green-100 text-green-800' 
            : 'bg-yellow-100 text-yellow-800'
        }`}>
          {row.conversion_status === 'completed' ? '已转换' : '待转换'}
        </span>
      ),
    },
    {
      name: '大小',
      selector: (row: Document) => row.file_size,
      sortable: true,
      width: '100px',
      format: (row: Document) => `${(row.file_size / 1024 / 1024).toFixed(2)} MB`,
    },
    {
      name: '上传时间',
      selector: (row: Document) => row.created_at,
      sortable: true,
      width: '120px',
      format: (row: Document) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      name: '操作',
      width: '180px',
      cell: (row: Document) => (
        <div className="flex space-x-2">
          <button 
            onClick={() => handlePreview(row)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            预览
          </button>
          <button 
            onClick={() => handleEdit(row)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            编辑
          </button>
          <button 
            onClick={() => handleDelete(row.id)}
            className="text-red-600 hover:text-red-800 text-sm"
          >
            删除
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ], []);

  // 加载状态
  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">加载文档列表中...</p>
          </div>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">加载失败</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <div className="flex justify-center space-x-3">
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              重新加载
            </button>
            <Link 
              to="/admin/apps"
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            >
              返回应用列表
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 确保应用和文件夹数据已加载
  if (!app || !folder) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">数据不完整</h3>
          <p className="text-yellow-700 mb-4">无法加载应用或文件夹信息，请返回应用列表重试。</p>
          <Link 
            to="/admin/apps"
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            返回应用列表
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* 面包屑导航 */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/apps" className="hover:text-blue-600">应用管理</Link>
          <span>›</span>
          <Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}`} className="hover:text-blue-600">{app.name}</Link>
          <span>›</span>
          <span className="text-gray-700">{folder.name} 文档</span>
        </div>
        
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{folder.name} 文档</h1>
            <p className="text-gray-600 mt-1">{folder.description || ''}</p>
          </div>
          <div className="flex space-x-3">
            <Link 
              to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}/upload?folder=${encodeURIComponent(folder?.path || folderId)}`}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              + 上传文档
            </Link>
            <button 
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              onClick={() => window.location.reload()}
            >
              刷新
            </button>
            <button 
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleDeleteAllDocuments}
              disabled={documents.length === 0 || deletingAll}
            >
              {deletingAll ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                  删除中...
                </>
              ) : (
                '删除所有文件'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">总文档数</div>
          <div className="text-2xl font-bold mt-1">{documents.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">PDF文档</div>
          <div className="text-2xl font-bold mt-1">{documents.filter(d => d.file_type === 'pdf').length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">转换完成</div>
          <div className="text-2xl font-bold mt-1">{documents.filter(d => d.conversion_status === 'completed').length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">总页数</div>
          <div className="text-2xl font-bold mt-1">{documents.reduce((sum, d) => sum + (d.pages || d.page_count || 0), 0)}</div>
        </div>
      </div>

      {documents.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">暂无文档</h3>
          <p className="text-gray-500 mb-4">此文件夹还没有任何文档。上传第一个文档开始使用。</p>
          <Link 
            to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}/upload?folder=${encodeURIComponent(folder?.path || folderId)}`}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            上传文档
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <DataTable
            columns={columns}
            data={documents}
            pagination
            paginationPerPage={20}
            paginationRowsPerPageOptions={[10, 20, 50, 100]}
            defaultSortFieldId={5}
            defaultSortAsc={false}
            highlightOnHover
            striped
            responsive
            noHeader
          />
        </div>
      )}

      {/* 编辑文档模态框 */}
      {editingDoc && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">编辑文档</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    文档标题
                  </label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    描述（可选）
                  </label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    onClick={handleCancelEdit}
                    className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSaveEdit}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    保存
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-medium text-blue-800">新架构说明</h3>
        <p className="text-blue-700 mt-1">
          此页面现在直接显示应用下的文件夹文档列表。抽屉层已完全移除。
        </p>
        <div className="mt-2 text-sm text-blue-600">
          <p>• URL结构：<code>/admin/apps/:appSlug/folders/:folderId/documents</code></p>
          <p>• 文档直接属于文件夹，文件夹直接属于应用</p>
          <p>• 所有历史数据已清空，这是全新开始</p>
        </div>
      </div>
    </div>
  );
};

export default AdminDocuments;
