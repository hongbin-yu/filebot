import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
// react-data-table-component v7.x exports differently in CJS vs ESM
// Using namespace import + .default handles both Vite CJS/ESM interop modes
import RDT from 'react-data-table-component';
const DataTable = RDT.default || RDT;
import appService, { App } from '../../services/app.service';
import folderService, { Folder } from '../../services/folder.service';
import documentService, { Document } from '../../services/document.service';
import { showToast } from '../../components/common/ToastNotification';

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
        doc.path === updatedDoc.path ? updatedDoc : doc
      ));
      
      setEditingDoc(null);
      setEditTitle('');
      setEditDescription('');
    } catch (err: any) {
      console.error('更新文档失败:', err);
      showToast(`Update failed: ${err.message || 'Unknown error'}`, 'error');
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
    const targetDoc = documents.find(d => d.path === documentId);
    const docName = targetDoc?.original_filename || targetDoc?.title || 'this document';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\nPath: ${docPathStr}` : '';
    const confirmedDel = await window.wetYesOrNo(`Are you sure you want to delete "${docName}"? This cannot be undone.${docPathInfo}`);
    if (!confirmedDel) return;
    
    try {
      const deleteIdentifier = targetDoc?.path || targetDoc?.storage_path || documentId;
      await documentService.deleteDocument(deleteIdentifier);
      setDocuments(docs => docs.filter(doc => doc.path !== documentId));
      showToast('Document deleted successfully', 'success');
    } catch (err: any) {
      console.error('删除文档失败:', err);
      showToast(`Delete failed: ${err.message || 'Unknown error'}`, 'error');
    }
  };

  // Delete all documents
  const handleDeleteAllDocuments = async () => {
    if (documents.length === 0) {
      showToast('No documents to delete in current folder', 'info');
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
        showToast(`Successfully deleted all ${deletedCount} documents`, 'success');
      } else {
        showToast(`Done: ${deletedCount} deleted, ${failedCount} failed`, 'info');
      }
    } catch (err: any) {
      console.error('批量删除文档失败:', err);
      showToast(`Batch delete failed: ${err.message || 'Unknown error'}`, 'error');
    } finally {
      setDeletingAll(false);
    }
  };

  // Import single document to WebBot
  const handleImportToWebBot = async (doc: Document) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    const docName = doc.title || doc.original_filename || docPath;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/import-to-webbot/single', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({ document_path: docPath }),
      });
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `HTTP ${response.status}`);
      }
      const result = await response.json();
      if (result.inserted > 0) {
        showToast(`✅ "${docName}" imported to WebBot`, 'success');
      } else if (result.updated > 0) {
        showToast(`🔄 "${docName}" updated in WebBot`, 'success');
      } else {
        showToast(`⚠️ "${docName}" skipped`, 'info');
      }
    } catch (err: any) {
      console.error('Import to WebBot failed:', err);
      showToast(`Import failed: ${err.message || 'Unknown error'}`, 'error');
    }
  };

  // Toggle document publish status (Publish / Unpublish)
  const handleTogglePublish = async (doc: Document) => {
    const isPublished = doc.publish_status === 'PUBLISHED';
    const docName = doc.title || doc.original_filename || doc.path;
    const docUrl = doc.storage_path ? `\nURL: /${doc.storage_path.replace(/^\/+/, '')}` : '';
    const confirmed = await window.wetYesOrNo(
      isPublished
        ? `Unpublish "${docName}"? It will no longer be publicly accessible.${docUrl}`
        : `Publish "${docName}"? It will be publicly accessible via its URL.${docUrl}`
    );
    if (!confirmed) return;

    try {
      const docId = doc.path || doc.storage_path || doc.id;
      const updatedDoc = await documentService.updateDocument(docId, {
        publish_status: isPublished ? 'UNPUBLISHED' : 'PUBLISHED'
      });
      setDocuments(docs => docs.map(d => d.path === updatedDoc.path ? updatedDoc : d));
      showToast(isPublished ? 'Document unpublished' : 'Document published', 'success');
    } catch (err: any) {
      console.error('Toggle publish failed:', err);
      showToast(`Publish action failed: ${err.message || 'Unknown error'}`, 'error');
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
          <div className="fb-label">{row.title}</div>
          <div  style={{fontSize:"0.75rem"}}>{row.original_filename}</div>
        </div>
      ),
    },
    {
      name: 'Type',
      selector: (row: Document) => row.file_type,
      sortable: true,
      width: '80px',
      cell: (row: Document) => (
        <span className="badge" style={{padding:"4px 8px",fontSize:"0.75rem",fontWeight:500,background:"#f3f4f6",color:"#1f2937",borderRadius:4}}>
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
      width: '370px',
      cell: (row: Document) => (
        <div className="fb-d-flex fb-gap-1">
          <button type="button"
            onClick={() => handlePreview(row)}
            className="fb-link" style={{fontSize:"0.875rem",color:"#2563eb"}}
          >
            Preview
          </button>
          <button type="button"
            onClick={() => handleEdit(row)}
            className="fb-link" style={{fontSize:"0.875rem",color:"#2563eb"}}
          >
            Edit
          </button>
          <button type="button"
            onClick={() => handleTogglePublish(row)}
            className="fb-link" style={{fontSize:"0.875rem",fontWeight:500,color: row.publish_status === 'PUBLISHED' ? '#d97706' : '#059669',background:"transparent",border:"none",padding:0,cursor:"pointer"}}
            title={row.publish_status === 'PUBLISHED' ? 'Unpublish this document' : 'Publish this document'}
          >
            {row.publish_status === 'PUBLISHED' ? 'Unpublish' : 'Publish'}
          </button>
          <button type="button"
            onClick={() => handleImportToWebBot(row)}
            className="fb-link" style={{fontSize:"0.875rem",fontWeight:500,color:"#7c3aed",background:"transparent",border:"none",padding:0,cursor:"pointer"}}
            title="Import this page to WebBot"
          >
            WebBot
          </button>
          <button type="button"
            onClick={() => handleDelete(row.path)}
            className="fb-link" style={{fontSize:"0.875rem",color:"#dc2626"}}
          >
            Delete
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
    },
  ], []);

  // Loading state
  if (loading) {
    return (
      <div style={{padding:24}}>
        <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
          <div >
            <div className="fb-spinner" style={{height:48,width:48,borderWidth:2,borderColor:"#2563eb",borderRadius:"50%"}}></div>
            <p  style={{ marginTop:16 }}>Loading documents...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{padding:24}}>
        <div  style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:24}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#991b1b",marginBottom:8}}>Load Failed</h3>
          <p style={{ color:"#b91c1c", marginBottom:16 }}>{error}</p>
          <div className="fb-d-flex fb-justify-center fb-gap-2">
            <button 
              onClick={() => window.location.reload()}
              className="btn btn-danger"
            >
              Reload
            </button>
            <Link 
              to="/admin/apps"
              className="btn btn-default"
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
      <div style={{padding:24}}>
        <div  style={{background:"#fefce8",border:"1px solid #fef08a",borderRadius:8,padding:24}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#854d0e",marginBottom:8}}>Incomplete Data</h3>
          <p style={{ color:"#a16207", marginBottom:16 }}>Could not load app or folder info. Please go back to the app list and try again.</p>
          <Link 
            to="/admin/apps"
            className="btn btn-warning"
          >
            Back to Apps
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{padding:24}}>
      {/* Breadcrumb navigation */}
      <div style={{marginBottom:24}}>
        <div className="fb-d-flex fb-align-center" style={{gap:8,fontSize:"0.875rem",marginBottom:8}}>
          <Link to="/admin/apps" className="fb-link">Apps</Link>
          <span>›</span>
          <Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}`} className="fb-link">{app.name}</Link>
          <span>›</span>
          <span style={{color:"#374151"}}>{folder.name} Documents</span>
        </div>
        
        <div className="fb-d-flex fb-justify-between fb-align-center">
          <div>
            <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>{folder.name} Documents</h1>
            <p  style={{ marginTop:4 }}>{folder.description || ''}</p>
          </div>
          <div className="fb-d-flex fb-gap-2">
            <Link 
              to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}/upload?folder=${encodeURIComponent(folder?.path || folderId)}`}
              className="btn btn-primary"
            >
              + Upload
            </Link>
            <button 
              className="btn btn-default"
              onClick={() => window.location.reload()}
            >
              Refresh
            </button>
            <button 
              className="btn btn-danger" disabled
              onClick={handleDeleteAllDocuments}
              disabled={documents.length === 0 || deletingAll}
            >
              {deletingAll ? (
                <>
                  <span className="fb-spinner" style={{borderWidth:2,borderColor:"#ffffff",height:16,width:16,borderRadius:"50%",marginRight:8}}></span>
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
      <div className="row" style={{marginBottom:24}}>
        <div className="panel panel-default" style={{padding:16}}>
          <div  style={{fontSize:"0.875rem"}}>Total Documents</div>
          <div style={{ fontSize:"1.5rem", fontWeight:700, marginTop:4 }}>{documents.length}</div>
        </div>
        <div className="panel panel-default" style={{padding:16}}>
          <div  style={{fontSize:"0.875rem"}}>PDF Documents</div>
          <div style={{ fontSize:"1.5rem", fontWeight:700, marginTop:4 }}>{documents.filter(d => d.file_type === 'pdf').length}</div>
        </div>
        <div className="panel panel-default" style={{padding:16}}>
          <div  style={{fontSize:"0.875rem"}}>Converted</div>
          <div style={{ fontSize:"1.5rem", fontWeight:700, marginTop:4 }}>{documents.filter(d => d.conversion_status === 'completed').length}</div>
        </div>
        <div className="panel panel-default" style={{padding:16}}>
          <div  style={{fontSize:"0.875rem"}}>Total Pages</div>
          <div style={{ fontSize:"1.5rem", fontWeight:700, marginTop:4 }}>{documents.reduce((sum, d) => sum + (d.pages || d.page_count || 0), 0)}</div>
        </div>
      </div>

      {documents.length === 0 ? (
        <div className="panel panel-default" style={{padding:32}}>
          <div style={{ color:"#9ca3af", marginBottom:16 }}>
            <svg  style={{ width:64, height:64 }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
          </div>
          <h3 className="fb-label" style={{fontSize:"1.125rem",marginBottom:8}}>No Documents</h3>
          <p  style={{ marginBottom:16 }}>This folder has no documents yet. Upload the first document to get started.</p>
          <Link 
            to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}/upload?folder=${encodeURIComponent(folder?.path || folderId)}`}
            className="btn btn-primary"
          >
            Upload Documents
          </Link>
        </div>
      ) : (
        <div className="panel panel-default" style={{overflow:"hidden"}}>
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
        <div className="fb-d-flex fb-align-center fb-justify-center" style={{position:"fixed",top:0,right:0,bottom:0,left:0,background:"rgba(107,114,128,0.75)",zIndex:50,padding:16}}>
          <div className="panel panel-default" style={{width:"100%",maxWidth:448}}>
            <div style={{padding:24}}>
              <h3 className="fb-label" style={{fontSize:"1.125rem",marginBottom:16}}>Edit Document</h3>
              <div className="fb-space-y" style={{gap:16}}>
                <div>
                  <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                    Document Title
                  </label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="form-control"
                  />
                </div>
                <div>
                  <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                    Description (optional)
                  </label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={3}
                    className="form-control"
                  />
                </div>
                <div className="fb-d-flex fb-justify-end fb-gap-2" style={{marginTop:24}}>
                  <button
                    onClick={handleCancelEdit}
                    className="btn btn-default"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEdit}
                    className="btn btn-primary"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div style={{marginTop:32,padding:16,background:"#eff6ff",borderRadius:8}}>
        <h3 style={{ fontWeight:500, color:"#1e40af" }}>New Architecture</h3>
        <p style={{ color:"#1d4ed8", marginTop:4 }}>This page now directly shows documents under the selected folder. The drawer system has been removed.</p>
        <div style={{ marginTop:8, fontSize:"0.875rem", color:"#2563eb" }}>
          <p>• URL: <code>/admin/apps/:appSlug/folders/:folderId/documents</code></p>
          <p>• Documents belong to folders, folders belong to apps</p>
          <p>• All historical data has been reset. This is a fresh start.</p>
        </div>
      </div>
    </div>
  );
};

export default AdminDocuments;
