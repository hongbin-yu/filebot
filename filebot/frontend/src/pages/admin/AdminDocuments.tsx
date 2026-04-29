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
        setError('Missing app or folder parameter');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // 1. Get app info
        const apps = await appService.getApps();
        const foundApp = apps.find(a => a.slug === appSlug || a.id === appSlug);
        if (!foundApp) {
          setError(`App "${appSlug}" not found`);
          setLoading(false);
          return;
        }
        setApp(foundApp);

        // 2. Get folder info - by identifier (UUID or path)
        const folderIdentifier = decodeURIComponent(folderId);
        const foundFolder = await folderService.getFolder(folderIdentifier);
        if (!foundFolder) {
          setError(`Folder "${folderIdentifier}" not found`);
          setLoading(false);
          return;
        }
        setFolder(foundFolder);

        // 3. Get document list
        const docs = await documentService.getDocuments(folderIdentifier);
        setDocuments(docs);

      } catch (err: any) {
        console.error('加载数据失败:', err);
        setError(`Failed to load data: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [appSlug, folderId]);

  // Preview document
  const handlePreview = (doc: any) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    navigate(`/admin/documents/${docPath.replace(/^\//, '')}`);
  };

  // Start editing document
  const handleEdit = (doc: Document) => {
    setEditingDoc(doc);
    setEditTitle(doc.title || '');
    setEditDescription(doc.description || '');
  };

  // Save edit
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
      window.showWetAlert(`Update failed: ${err.message || 'Unknown error'}`);
    }
  };

  // Cancel edit
  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditTitle('');
    setEditDescription('');
  };

  // Delete document
  const handleDelete = async (documentId: string) => {
    const targetDoc = documents.find(d => d.id === documentId);
    const docName = targetDoc?.original_filename || targetDoc?.title || 'this document';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\nPath: ${docPathStr}` : '';
    const confirmedDel = await window.wetYesOrNo(`Are you sure you want to delete "${docName}"? This cannot be undone.${docPathInfo}`);
    if (!confirmedDel) return;
    
    try {
      const deleteIdentifier = targetDoc?.path || targetDoc?.storage_path || documentId;
      await documentService.deleteDocument(deleteIdentifier);
      setDocuments(docs => docs.filter(doc => doc.id !== documentId));
      window.showWetAlert('Document deleted successfully');
    } catch (err: any) {
      console.error('删除文档失败:', err);
      window.showWetAlert(`Delete failed: ${err.message || 'Unknown error'}`);
    }
  };

  // Delete all documents
  const handleDeleteAllDocuments = async () => {
    if (documents.length === 0) {
      window.showWetAlert('No documents to delete in current folder');
      return;
    }
    
    const folderName = folder?.name || 'current folder';
    const folderPathStr = folder?.path ? `\nTarget path: ${folder.path}` : '';
    const confirmedAll = await window.wetYesOrNo(`Are you sure you want to delete all ${documents.length} documents in ${folderName}? This cannot be undone and will delete all files.${folderPathStr}`);
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
        window.showWetAlert(`Successfully deleted all ${deletedCount} documents`);
      } else {
        window.showWetAlert(`Done: ${deletedCount} deleted, ${failedCount} failed`);
      }
    } catch (err: any) {
      console.error('批量删除文档失败:', err);
      window.showWetAlert(`Batch delete failed: ${err.message || 'Unknown error'}`);
    } finally {
      setDeletingAll(false);
    }
  };

  // DataTable column definitions
  const columns = useMemo(() => [
    {
      name: 'Document',
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
      name: 'Type',
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
      name: 'Status',
      selector: (row: Document) => row.conversion_status,
      sortable: true,
      width: '100px',
      cell: (row: Document) => (
        <span className={`px-2 py-1 text-xs font-medium rounded ${
          row.conversion_status === 'completed' 
            ? 'bg-green-100 text-green-800' 
            : 'bg-yellow-100 text-yellow-800'
        }`}>
          {row.conversion_status === 'completed' ? 'Converted' : 'Pending'}
        </span>
      ),
    },
    {
      name: 'Size',
      selector: (row: Document) => row.file_size,
      sortable: true,
      width: '100px',
      format: (row: Document) => `${(row.file_size / 1024 / 1024).toFixed(2)} MB`,
    },
    {
      name: 'Upload Date',
      selector: (row: Document) => row.created_at,
      sortable: true,
      width: '120px',
      format: (row: Document) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      name: 'Actions',
      width: '180px',
      cell: (row: Document) => (
        <div className="flex space-x-2">
          <button 
            onClick={() => handlePreview(row)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            Preview
          </button>
          <button 
            onClick={() => handleEdit(row)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            Edit
          </button>
          <button 
            onClick={() => handleDelete(row.id)}
            className="text-red-600 hover:text-red-800 text-sm"
          >
            Delete
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ], []);

  // Loading state
  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading documents...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">Load Failed</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <div className="flex justify-center space-x-3">
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Reload
            </button>
            <Link 
              to="/admin/apps"
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            >
              Back to Apps
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Ensure app and folder data is loaded
  if (!app || !folder) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">Incomplete Data</h3>
          <p className="text-yellow-700 mb-4">Could not load app or folder info. Please go back to the app list and try again.</p>
          <Link 
            to="/admin/apps"
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Back to Apps
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Breadcrumb navigation */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/apps" className="hover:text-blue-600">Apps</Link>
          <span>›</span>
          <Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}`} className="hover:text-blue-600">{app.name}</Link>
          <span>›</span>
          <span className="text-gray-700">{folder.name} Documents</span>
        </div>
        
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{folder.name} Documents</h1>
            <p className="text-gray-600 mt-1">{folder.description || ''}</p>
          </div>
          <div className="flex space-x-3">
            <Link 
              to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}/upload?folder=${encodeURIComponent(folder?.path || folderId)}`}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              + Upload
            </Link>
            <button 
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              onClick={() => window.location.reload()}
            >
              Refresh
            </button>
            <button 
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleDeleteAllDocuments}
              disabled={documents.length === 0 || deletingAll}
            >
              {deletingAll ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                  Deleting...
                </>
              ) : (
                'Delete All'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Documents</div>
          <div className="text-2xl font-bold mt-1">{documents.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">PDF Documents</div>
          <div className="text-2xl font-bold mt-1">{documents.filter(d => d.file_type === 'pdf').length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Converted</div>
          <div className="text-2xl font-bold mt-1">{documents.filter(d => d.conversion_status === 'completed').length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Pages</div>
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
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Documents</h3>
          <p className="text-gray-500 mb-4">This folder has no documents yet. Upload the first document to get started.</p>
          <Link 
            to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}/upload?folder=${encodeURIComponent(folder?.path || folderId)}`}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Upload Documents
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

      {/* Edit document modal */}
      {editingDoc && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Edit Document</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Document Title
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
                    Description (optional)
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
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEdit}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-medium text-blue-800">New Architecture</h3>
        <p className="text-blue-700 mt-1">This page now directly shows documents under the selected folder. The drawer system has been removed.</p>
        <div className="mt-2 text-sm text-blue-600">
          <p>• URL: <code>/admin/apps/:appSlug/folders/:folderId/documents</code></p>
          <p>• Documents belong to folders, folders belong to apps</p>
          <p>• All historical data has been reset. This is a fresh start.</p>
        </div>
      </div>
    </div>
  );
};

export default AdminDocuments;
