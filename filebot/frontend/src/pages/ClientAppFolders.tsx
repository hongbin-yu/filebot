import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import appService, { App } from '../services/app.service';
import authService from '../services/auth.service';
import folderService, { Folder } from '../services/folder.service';
import documentService, { Document } from '../services/document.service';
import PreviewOverlay from '../components/PreviewOverlay';
import CreateFolderModal from '../components/folders/CreateFolderModal';
import { showToast } from '../components/common/ToastNotification';

function formatSize(bytes: number): string {
  if (!bytes || bytes === 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0, size = bytes;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/**
 * 将文档路径转为公开发布路径（8003 发布服务器 URL 路径）。
 * 文档 path 存在多种内部前缀：/content/dam/...（无需处理）、
 * /publish/content/dam/...（剥 /publish）、/boarding/canadasite/content/...（剥 app 前缀）。
 * 统一规则：优先从 /content 开始截取；否则剥掉 /publish；否则原样。
 * 与后端 path_utils.get_publish_relative_path 保持一致。
 */
function toPublicPath(p: string): string {
  const ci = p.indexOf('/content');
  if (ci >= 0) return p.slice(ci);
  return p.replace(/^\/publish/, '');
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  try { return new Date(dateStr).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' }); }
  catch { return dateStr; }
}

const ClientAppFolders: React.FC = () => {
  const { appSlug, '*': wildcardPath } = useParams<{ appSlug: string; '*': string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [app, setApp] = useState<App | null>(null);
  const [appLoading, setAppLoading] = useState(true);
  const [appError, setAppError] = useState<string | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [subfolders, setSubfolders] = useState<Folder[]>([]);
  const [currentFolderPath, setCurrentFolderPath] = useState<string | null>(null);
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [foldersLoading, setFoldersLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [selectedAiTag, setSelectedAiTag] = useState('');
  const [aiTagCategories, setAiTagCategories] = useState<{ category: string; count: number }[]>([]);
  const [aiTagsLoading, setAiTagsLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewFileType, setPreviewFileType] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showMoveFolderModal, setShowMoveFolderModal] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [moveFolderTarget, setMoveFolderTarget] = useState('');
  const [moveFolderLoading, setMoveFolderLoading] = useState(false);
  const [moveFolderError, setMoveFolderError] = useState<string | null>(null);

  const openPreview = useCallback((url: string, fileType: string, e: React.MouseEvent) => { e.preventDefault(); setPreviewUrl(url); setPreviewFileType(fileType); }, []);

  useEffect(() => {
    if (!appSlug) return;
    (async () => {
      try { setAppLoading(true); setApp(await appService.getAppById(appSlug)); }
      catch (err: any) { setAppError(err?.response?.data?.detail || err.message || 'Failed to load app'); }
      finally { setAppLoading(false); }
    })();
  }, [appSlug]);

  useEffect(() => {
    if (!appSlug) return;
    (async () => {
      try {
        setFoldersLoading(true);
        const rootData = await folderService.getFolders(appSlug, {});
        setFolders(rootData);
      } catch { setFolders([]); }
      finally { setFoldersLoading(false); }
    })();
  }, [appSlug]);

  useEffect(() => {
    if (wildcardPath && wildcardPath.trim()) {
      setCurrentFolderPath('/' + wildcardPath.replace(/^\/+|\/+$/g, ''));
    } else { setCurrentFolderPath(null); setCurrentFolder(null); setSubfolders([]); setDocuments([]); }
  }, [wildcardPath, location.pathname]);

  useEffect(() => {
    if (!currentFolderPath || !appSlug) { setSubfolders([]); setCurrentFolder(null); return; }
    (async () => {
      try {
        const fullPath = '/' + appSlug + currentFolderPath;
        const allFolders = await folderService.getFolders(appSlug, { parent_folder_path: fullPath });
        let current: Folder | null = null;
        const subs: Folder[] = [];
        for (const f of allFolders) {
          if (f.path === fullPath) current = f;
          else if (f.parent_folder_path === fullPath) subs.push(f);
        }
        if (!current) { try { current = await folderService.getFolder(fullPath); } catch {} }
        const seen = new Set<string>();
        const uniqueSubs = subs.filter(f => { const k = f.path; if (seen.has(k)) return false; seen.add(k); return true; });
        setCurrentFolder(current);
        setSubfolders(uniqueSubs);
      } catch {}
    })();
  }, [currentFolderPath, appSlug]);

  useEffect(() => {
    if (!appSlug) { setDocuments([]); return; }
    if (!currentFolderPath) {
      setDocumentsLoading(true);
      (async () => {
        try {
          const skip = (currentPage - 1) * pageSize;
          const docs = await documentService.getDocumentsByPathPrefix('/' + appSlug, { skip, limit: pageSize });
          setTotalPages(Math.ceil(documentService.lastTotalCount / pageSize) || 1);
          setDocuments(docs);
        } catch { setDocuments([]); }
        finally { setDocumentsLoading(false); }
      })();
      return;
    }
    (async () => {
      setDocumentsLoading(true);
      try {
        const fullPath = '/' + appSlug + currentFolderPath;
        const skip = (currentPage - 1) * pageSize;
        const docs = await documentService.getDocumentsByPathPrefix(fullPath, { skip, limit: pageSize });
        setTotalPages(Math.ceil(documentService.lastTotalCount / pageSize) || 1);
        setDocuments(docs);
      } catch { setDocuments([]); }
      finally { setDocumentsLoading(false); }
    })();
  }, [currentFolderPath, appSlug, currentPage, pageSize]);

  const fetchAiTagCategories = useCallback(async () => {
    if (!appSlug || !currentFolderPath) { setAiTagCategories([]); setAiTagsLoading(false); return; }
    try {
      setAiTagsLoading(true);
      const fullPath = '/' + appSlug + currentFolderPath;
      const data = await documentService.getAiTagCategories(fullPath);
      setAiTagCategories(Array.isArray(data?.categories) ? data.categories : []);
    } catch { setAiTagCategories([]); }
    finally { setAiTagsLoading(false); }
  }, [appSlug, currentFolderPath]);

  // 切换文件夹时刷新 AI tag 分类下拉
  useEffect(() => {
    setSelectedAiTag('');
    fetchAiTagCategories();
  }, [fetchAiTagCategories]);

  const doSearch = useCallback(async (query: string, aiTag: string) => {
    if (!currentFolderPath) return;
    const fullPath = '/' + appSlug + currentFolderPath;
    if (!query.trim() && !aiTag.trim()) {
      setIsSearching(false);
      try {
        setDocumentsLoading(true);
        const skip = (currentPage - 1) * pageSize;
        const docs = await documentService.getDocumentsByPathPrefix(fullPath, { skip, limit: pageSize });
        setTotalPages(Math.ceil(documentService.lastTotalCount / pageSize) || 1);
        setDocuments(docs);
      } catch {}
      finally { setDocumentsLoading(false); }
      return;
    }
    try {
      setIsSearching(true);
      const params: any = { path: fullPath, limit: 1000 };
      if (query.trim()) params.q = query.trim();
      if (aiTag.trim()) params.ai_tag = aiTag.trim();
      const result = await documentService.searchDocumentsWithTotal(params);
      setDocuments(Array.isArray(result.documents) ? result.documents : []);
      setTotalPages(Math.ceil((result.total || 0) / pageSize) || 1);
    } catch {}
    finally { setIsSearching(false); }
  }, [currentFolderPath, appSlug, currentPage, pageSize]);

  const handleSearch = useCallback(async (query: string) => {
    setSearchQuery(query);
    doSearch(query, selectedAiTag);
  }, [doSearch, selectedAiTag]);

  const handleAiTagSelect = useCallback((tag: string) => {
    setSelectedAiTag(tag);
    doSearch(searchQuery, tag);
  }, [doSearch, searchQuery]);

  const handleAiTagClear = useCallback(() => {
    setSelectedAiTag('');
    doSearch(searchQuery, '');
  }, [doSearch, searchQuery]);

  const handleFolderClick = (folderPath: string) => {
    const appPrefix = '/' + appSlug;
    const relativePath = folderPath.startsWith(appPrefix) ? folderPath.slice(appPrefix.length) : folderPath;
    const cleanPath = relativePath.replace(/^\/+/, '');
    navigate(cleanPath ? `/apps/${appSlug}/${cleanPath}` : `/apps/${appSlug}`);
  };

  const handleDeleteDocument = async (doc: Document) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    const docName = doc.title || doc.original_filename || docPath;
    if (!(await window.wetYesOrNo(`Delete "${docName}"? This cannot be undone.`))) return;
    try {
      await documentService.deleteDocument(docPath);
      showToast(`🗑️ "${docName}" deleted`, 'success');
      setDocuments(prev => prev.filter(d => (d.path || d.storage_path || d.id) !== docPath));
    } catch (err: any) { showToast(`Delete failed: ${err.message || 'Unknown error'}`, 'error'); }
  };

  // Publish / Unpublish — 所有文档均支持
  const handleTogglePublish = async (doc: Document) => {
    const docPath = doc.path || doc.storage_path || doc.id;
    const docName = doc.title || doc.original_filename || docPath;
    const isPublished = doc.publish_status === 'PUBLISHED';
    const newStatus = isPublished ? 'UNPUBLISHED' : 'PUBLISHED';
    const action = isPublished ? 'unpublish' : 'publish';
    if (!(await window.wetYesOrNo(`${isPublished ? 'Unpublish' : 'Publish'} "${docName}"?`))) return;
    try {
      await documentService.updateDocument(docPath, { publish_status: newStatus as 'PUBLISHED' | 'UNPUBLISHED' });
      setDocuments(prev => prev.map(d =>
        (d.path || d.storage_path || d.id) === docPath ? { ...d, publish_status: newStatus as 'PUBLISHED' | 'UNPUBLISHED' } : d
      ));
      showToast(isPublished ? `📤 "${docName}" unpublished` : `📢 "${docName}" published`, 'success');
    } catch (err: any) {
      showToast(`${action === 'publish' ? 'Publish' : 'Unpublish'} failed: ${err.message || 'Unknown error'}`, 'error');
    }
  };

  const handlePreviewDocument = (doc: Document) => {
    const docPath = doc.path || doc.storage_path;
    navigate(`/documents/${(docPath || '').replace(/^\//, '')}`);
  };

  // Document editing
  const handleEditDoc = (doc: Document) => {
    setEditingDoc(doc);
    setEditTitle(doc.title || '');
    setEditDescription(doc.description || '');
  };

  const handleSaveEditDoc = async () => {
    if (!editingDoc) return;
    try {
      const docId = editingDoc.path || editingDoc.storage_path || editingDoc.id;
      const updatedDoc = await documentService.updateDocument(docId, {
        title: editTitle,
        description: editDescription
      });
      setDocuments(prev => prev.map(d =>
        (d.path || d.storage_path || d.id) === (updatedDoc.path || updatedDoc.storage_path || updatedDoc.id)
          ? { ...d, title: updatedDoc.title, description: updatedDoc.description }
          : d
      ));
      setEditingDoc(null);
      setEditTitle('');
      setEditDescription('');
      showToast('✅ Document updated', 'success');
    } catch (err: any) {
      console.error('更新文档失败:', err);
      showToast(`Update failed: ${err.message || 'Unknown error'}`, 'error');
    }
  };

  const handleCancelEditDoc = () => {
    setEditingDoc(null);
    setEditTitle('');
    setEditDescription('');
  };

  const buildBreadcrumbs = (): { name: string; path: string }[] => {
    const crumbs: { name: string; path: string }[] = [{ name: app?.name || appSlug || 'App', path: '/' + appSlug }];
    if (!currentFolderPath && !currentFolder) return crumbs;
    const segments = (currentFolderPath || currentFolder?.path || '').split('/').filter(Boolean);
    for (let i = 0; i < segments.length; i++) {
      crumbs.push({ name: segments[i], path: '/' + appSlug + '/' + segments.slice(0, i + 1).join('/') });
    }
    return crumbs;
  };

  // ── Folder Operations ──
  const handleCreateFolder = async (data: any) => {
    try {
      await folderService.createFolder(data);
      if (currentFolderPath && appSlug)
        setSubfolders(await folderService.getFolders(appSlug, { parent_folder_path: '/' + appSlug + currentFolderPath }));
    } catch (err) { console.error(err); throw err; }
  };

  const handleEditFolder = (folderPath: string) => {
    const f = folders.concat(subfolders).find(f => f.path === folderPath);
    if (!f) return;
    setEditingFolder(f); setShowEditModal(true);
  };

  const handleSaveEditFolder = async (data: any) => {
    if (!editingFolder?.path) return;
    try {
      await folderService.updateFolder(editingFolder.path, data);
      if (currentFolderPath && appSlug)
        setSubfolders(await folderService.getFolders(appSlug, { parent_folder_path: '/' + appSlug + currentFolderPath }));
      setShowEditModal(false); setEditingFolder(null);
    } catch (err) { console.error(err); throw err; }
  };

  const handleDeleteFolder = async (folderPath: string) => {
    if (!(await window.wetYesOrNo('Delete this folder? All documents inside will also be deleted.'))) return;
    try { await folderService.deleteFolder(folderPath, true); } catch {}
  };

  const handleMoveFolder = () => {
    const path = currentFolder?.path || currentFolderPath || '';
    if (!path) { if (typeof window.showWetAlert === 'function') window.showWetAlert('Please select a folder first'); return; }
    setMoveFolderTarget(''); setMoveFolderError(null); setShowMoveFolderModal(true);
  };

  const handleMoveFolderConfirm = async () => {
    const srcPath = currentFolder?.path || currentFolderPath || '';
    const target = moveFolderTarget.trim().replace(/\/$/, '');
    if (!target) { setMoveFolderError('Please enter a target parent folder path'); return; }
    if (srcPath === target) { setMoveFolderError('Cannot move folder to itself'); return; }
    if (target.startsWith(srcPath + '/')) { setMoveFolderError('Cannot move folder into its own subfolder'); return; }
    setMoveFolderLoading(true); setMoveFolderError(null);
    try { await folderService.moveFolder(srcPath, target); setShowMoveFolderModal(false); }
    catch (error: any) { setMoveFolderError(error?.response?.data?.detail || error.message || 'Move failed'); }
    finally { setMoveFolderLoading(false); }
  };

  if (appLoading)
    return <div className="fb-loading"><p className="text-muted">Loading app...</p></div>;

  if (appError || !app)
    return (
      <div className="container" style={{ paddingTop: 30 }}>
        <div className="alert alert-danger text-center">
          <h3>Error</h3>
          <p>{appError || 'Could not find the specified app.'}</p>
          <Link to="/apps" className="btn btn-danger">Back to App List</Link>
        </div>
      </div>
    );

  const breadcrumbs = buildBreadcrumbs();
  const rootFolders = currentFolderPath ? [] : folders.filter(f =>
    f.parent_folder_path === '/' + appSlug
  );

  return (
    <>
    <main property="mainContentOfPage" className="container">
      <PreviewOverlay url={previewUrl} fileType={previewFileType} onClose={() => { setPreviewUrl(null); setPreviewFileType(''); }} />

        {/* WET Breadcrumb */}
        <nav id="wb-bc" property="breadcrumb">
          <h2 className="wb-inv">You are here:</h2>
          <div className="container">
            <ol className="breadcrumb">
              <li><Link to="/apps">Apps</Link></li>
              {breadcrumbs.map((crumb, index) => (
                <li key={crumb.path}>
                  {index < breadcrumbs.length - 1
                    ? <a href="#" onClick={e => { e.preventDefault(); handleFolderClick(crumb.path); }}>{crumb.name}</a>
                    : crumb.name}
                </li>
              ))}
            </ol>
          </div>
        </nav>

        <div className="fb-page-header">
          <h1 style={{ margin: 0, fontSize: '1.5em' }}>{app.name}</h1>
          <p className="text-muted">{app.description}</p>
        </div>

        {/* Search */}
        <form onSubmit={e => { e.preventDefault(); handleSearch(searchQuery); }}
          className="input-group" style={{ marginBottom: 20 }}>
          <input type="text" className="form-control" placeholder="Search documents..."
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
          {searchQuery && (
            <span className="input-group-btn">
              <button type="button" className="btn btn-default"
                onClick={() => { setSearchQuery(''); handleSearch(''); }}>&times;</button>
            </span>
          )}
          <span className="input-group-btn">
            <button type="submit" className="btn btn-primary">Search</button>
          </span>
        </form>

        {/* AI Tag Filter — Dropdown */}
        <div className="input-group" style={{ marginBottom: 20 }}>
          <span className="input-group-addon">🏷️ AI Tag</span>
          <select className="form-control"
            value={selectedAiTag}
            onChange={e => handleAiTagSelect(e.target.value)}
            disabled={aiTagsLoading}>
            <option value="">{aiTagsLoading ? 'Loading...' : '-- All documents --'}</option>
            {Array.isArray(aiTagCategories) && aiTagCategories.map((cat, i) => (
              <option key={i} value={cat.category}>
                {cat.category} ({cat.count})
              </option>
            ))}
          </select>
          {selectedAiTag && (
            <span className="input-group-btn">
              <button type="button" className="btn btn-default"
                onClick={handleAiTagClear}>&times;</button>
            </span>
          )}
        </div>

        {/* Two-col layout */}
        <div className="row">
          {/* LEFT: Folders + AI Ops */}
          <div className="col-lg-4" style={{ marginBottom: 20 }}>
            <div className="panel panel-info">
              <div className="panel-heading fb-d-flex fb-justify-between fb-align-center">
                <h3 className="panel-title">Folders</h3>
                <span className="badge">{currentFolderPath ? subfolders.length : rootFolders.length}</span>
              </div>
              <div className="panel-body" style={{ padding: currentFolder && currentFolder.parent_folder_path ? '12px' : '8px 12px' }}>
                {currentFolder?.parent_folder_path && (
                  <button className="btn btn-default btn-sm btn-block" style={{ marginBottom: 10 }}
                    onClick={() => handleFolderClick(currentFolder.parent_folder_path!)}>
                    &larr; Up to parent
                  </button>
                )}
                {foldersLoading ? (
                  <p className="text-center text-muted small">Loading...</p>
                ) : (
                  <ul className="list-group">
                    {(currentFolderPath ? subfolders : rootFolders).map(folder => (
                      <li key={folder.path}
                        className={'list-group-item' + (currentFolderPath === folder.path ? ' active' : '')}
                        style={{ cursor: 'pointer' }}
                        onClick={() => handleFolderClick(folder.path || '')}>
                        <div className="fb-d-flex fb-align-center">
                          <span style={{ marginRight: 8, fontSize: '1.1em' }}>📁</span>
                          <div className="fb-flex-1" style={{ minWidth: 0 }}>
                            <strong className="fb-text-truncate" style={{ display: 'block' }}>{folder.name}</strong>
                            {folder.description && <small className="text-muted fb-text-truncate" style={{ display: 'block' }}>{folder.description}</small>}
                            {folder.document_count !== undefined && <small className="text-muted">{folder.document_count} doc{folder.document_count !== 1 ? 's' : ''}</small>}
                          </div>
                          <span className="glyphicon glyphicon-chevron-right text-muted"></span>
                        </div>
                      </li>
                    ))}
                    {(currentFolderPath ? subfolders : rootFolders).length === 0 && (
                      <li className="list-group-item text-center text-muted">No folders</li>
                    )}
                  </ul>
                )}
              </div>
            </div>

            {/* AI Operations (admin only) */}
            {authService.isAdmin() && (
              <div className="panel panel-warning">
                <div className="panel-heading"><h3 className="panel-title">AI Operations</h3></div>
                <div className="panel-body">
                  <div className="list-group">
                    <button className="list-group-item" onClick={() => setShowCreateModal(true)}>
                      <strong>Create Subfolder</strong>
                      <br/><small className="text-muted">Create a new subfolder in the current folder</small>
                    </button>
                    <button className="list-group-item"
                      onClick={() => navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(currentFolder?.path || currentFolderPath || '')}`)}>
                      <strong>Upload</strong>
                      <br/><small className="text-muted">Upload files to this folder</small>
                    </button>
                    <button className="list-group-item" style={{ borderLeft: '3px solid #337ab7' }}
                      onClick={() => handleEditFolder(currentFolder?.path || currentFolderPath || '')}>
                      <strong className="text-primary">Edit Folder</strong>
                      <br/><small className="text-muted">Edit folder name and description</small>
                    </button>
                    <button className="list-group-item" style={{ borderLeft: '3px solid #f0ad4e' }} onClick={handleMoveFolder}>
                      <strong style={{ color: '#f0ad4e' }}>Move Folder</strong>
                      <br/><small className="text-muted">Move this folder to a different parent</small>
                    </button>
                    <button className="list-group-item" style={{ borderLeft: '3px solid #d9534f' }}
                      onClick={() => handleDeleteFolder(currentFolder?.path || currentFolderPath || '')}>
                      <strong className="text-danger">Delete Folder</strong>
                      <br/><small className="text-muted">Delete this folder and all its contents</small>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT: Documents table */}
          <div className="col-lg-8">
            <div className="panel panel-success">
              <div className="panel-heading fb-d-flex fb-justify-between fb-align-center">
                <h3 className="panel-title">
                  {currentFolder ? `${currentFolder.name} — Documents` : 'Documents'}
                </h3>
                <span className="text-muted small">
                  {documents.length} doc{documents.length !== 1 ? 's' : ''}
                  {isSearching && <span className="label label-info" style={{ marginLeft: 6 }}>search</span>}
                </span>
              </div>

              {!currentFolderPath && Array.isArray(documents) && documents.length === 0 && !documentsLoading ? (
                <div className="panel-body text-center fb-empty-state">
                  <p style={{ fontSize: '2em' }}>📁</p>
                  <p className="text-muted">Select a folder from the left panel</p>
                </div>
              ) : documentsLoading ? (
                <div className="panel-body text-center fb-loading">
                  <p className="text-muted">Loading documents...</p>
                </div>
              ) : Array.isArray(documents) && documents.length === 0 ? (
                <div className="panel-body text-center fb-empty-state">
                  <p style={{ fontSize: '2em' }}>📄</p>
                  <p className="text-muted">No documents found under this folder</p>
                </div>
              ) : !Array.isArray(documents) ? (
                <div className="panel-body text-center fb-loading">
                  <p className="text-muted">Re-rendering...</p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-striped table-hover small" style={{ marginBottom: 0 }}>
                    <thead>
                      <tr>
                        <th style={{ width: 80 }}>Preview</th>
                        <th>Name</th>
                        <th style={{ width: 160 }}>Actions</th>
                        <th>Type</th>
                        <th className="text-right">Size</th>
                        <th>Created</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Array.isArray(documents) && documents.map(doc => {
                        const token = localStorage.getItem('access_token');
                        const encodedPath = encodeURIComponent(doc.path || doc.storage_path);
                        const publishUrl = doc.publish_status === 'PUBLISHED' && doc.path
                          ? `${window.location.protocol}//${window.location.hostname}${toPublicPath(doc.path)}`
                          : null;
                        const docViewUrl = publishUrl || (doc.file_type === 'html'
                          ? `/api/v1/documents/${encodedPath}/preview/html?token=${token}`
                          : `/api/v1/documents/${encodedPath}/download?preview=1&token=${token}`);
                        const isVideo = doc.file_type === 'video';
                        const isImage = isVideo || ['jpeg', 'jpg', 'png', 'gif', 'svg', 'tiff', 'tif'].includes(doc.file_type?.toLowerCase());
                        const thumbUrl = `/api/v1/documents/${encodedPath}/thumbnail?token=${token}`;
                        return (
                          <tr key={doc.path || doc.storage_path}>
                            <td className="text-center" style={{ verticalAlign: 'middle' }}>
                              {isImage ? (
                                <a href={isVideo ? undefined : docViewUrl}
                                  onClick={e => { e.preventDefault(); openPreview(docViewUrl, doc.file_type, e); }}
                                  target={isVideo ? undefined : (publishUrl ? '_blank' : undefined)}
                                  rel={isVideo ? undefined : 'noopener noreferrer'}
                                  style={isVideo ? { cursor: 'pointer' } : undefined}>
                                  <img src={thumbUrl} alt="thumbnail" loading="lazy"
                                    style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 4, border: '1px solid #ddd' }}
                                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                </a>
                              ) : (
                                <a href={docViewUrl} onClick={e => { if (publishUrl) return; openPreview(docViewUrl, doc.file_type, e); }}
                                  target={publishUrl ? '_blank' : undefined} rel="noopener noreferrer">
                                  <span className="glyphicon glyphicon-file text-muted" style={{ fontSize: 18 }}></span>
                                </a>
                              )}
                            </td>
                            <td>
                              <a href={isVideo ? undefined : docViewUrl}
                                onClick={isVideo ? (e => { e.preventDefault(); openPreview(docViewUrl, doc.file_type, e); })
                                         : (e => { if (publishUrl) return; openPreview(docViewUrl, doc.file_type, e); })}
                                target={isVideo ? undefined : (publishUrl ? '_blank' : undefined)}
                                rel={isVideo ? undefined : 'noopener noreferrer'}
                                style={isVideo ? { cursor: 'pointer' } : undefined}>
                                <strong>{doc.title || doc.original_filename || 'Untitled'}</strong>
                              </a>
                              <br /><small className="text-muted">
                                {(doc.parent_folder_path || doc.folder_path || '').replace('/' + appSlug, '')}
                              </small>
                            </td>
                            <td style={{ verticalAlign: 'middle' }}>
                              <div className="fb-d-flex fb-gap-1" style={{ gap: 4 }}>
                                {doc.publish_status === 'PUBLISHED' ? (
                                    <button className="btn btn-xs btn-warning"
                                      onClick={() => handleTogglePublish(doc)} title="Unpublish">Unpublish</button>
                                  ) : (
                                    <button className="btn btn-xs btn-success"
                                      onClick={() => handleTogglePublish(doc)} title="Publish">Publish</button>
                                  )
                                }
                                <button className="btn btn-xs btn-default"
                                  onClick={() => handleEditDoc(doc)} title="Edit">Edit</button>
                                <button className="btn btn-xs btn-danger"
                                  onClick={() => handleDeleteDocument(doc)} title="Delete">Delete</button>
                              </div>
                            </td>
                            {appSlug === 'publish' && (
                              <td className="text-center" style={{ verticalAlign: 'middle' }}>
                                <label className="switch" style={{ cursor: 'pointer', margin: 0, display: 'inline-block' }}>
                                  <input type="checkbox" checked={doc.publish_status === 'PUBLISHED'}
                                    onChange={async () => {
                                      const newStatus = doc.publish_status === 'PUBLISHED' ? 'UNPUBLISHED' : 'PUBLISHED';
                                      try {
                                        await documentService.updateDocument(doc.path || doc.storage_path, { publish_status: newStatus });
                                        setDocuments(prev => prev.map(d =>
                                          (d.path || d.storage_path) === (doc.path || doc.storage_path)
                                            ? { ...d, publish_status: newStatus } : d));
                                      } catch { console.error('Failed to update publish status'); }
                                    }} />
                                  <span className="slider round"></span>
                                </label>
                              </td>
                            )}
                            <td><span className="label label-default">{(doc.file_type || doc.mime_type || '-').split('/').pop()}</span></td>
                            <td className="text-right">{formatSize(doc.file_size)}</td>
                            <td><small>{formatDate(doc.created_at)}</small></td>
                            <td>
                              <span className={'label ' + (
                                doc.conversion_status === 'completed' ? 'label-success'
                                  : doc.conversion_status === 'failed' ? 'label-danger'
                                  : doc.conversion_status === 'processing' ? 'label-warning'
                                  : 'label-default')}>
                                {doc.conversion_status || 'pending'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {/* Pagination */}
                  {!isSearching && documents.length > 0 && (
                    <div className="panel-footer">
                      <div className="fb-d-flex fb-justify-between fb-align-center fb-wrap" style={{ gap: 8 }}>
                        <small className="text-muted">
                          Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
                          &middot; <strong>{documentService.lastTotalCount}</strong> total
                        </small>
                        <div className="fb-d-flex fb-align-center fb-gap-1">
                          <label className="small text-muted" style={{ marginBottom: 0, marginRight: 4 }}>Per page:</label>
                          <select className="form-control input-sm" value={pageSize}
                            onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                            style={{ width: 'auto' }}>
                            <option value={25}>25</option>
                            <option value={50}>50</option>
                            <option value={100}>100</option>
                          </select>
                        </div>
                        <div className="btn-group btn-group-xs">
                          <button className="btn btn-default" onClick={() => setCurrentPage(1)} disabled={currentPage <= 1}>&laquo;</button>
                          <button className="btn btn-default" onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage <= 1}>&lsaquo; Prev</button>
                          {(() => {
                            const pages: (number | string)[] = [];
                            if (totalPages <= 7) { for (let i = 1; i <= totalPages; i++) pages.push(i); }
                            else {
                              pages.push(1);
                              if (currentPage > 3) pages.push('...');
                              for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) pages.push(i);
                              if (currentPage < totalPages - 2) pages.push('...');
                              pages.push(totalPages);
                            }
                            return pages.map((p, idx) => p === '...'
                              ? <span key={`e${idx}`} className="btn btn-default btn-xs disabled">&hellip;</span>
                              : <button key={p} className={'btn btn-xs ' + (p === currentPage ? 'btn-primary' : 'btn-default')}
                                  onClick={() => setCurrentPage(p as number)}>{p}</button>
                            );
                          })()}
                          <button className="btn btn-default btn-xs" onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage >= totalPages}>Next &rsaquo;</button>
                          <button className="btn btn-default btn-xs" onClick={() => setCurrentPage(totalPages)} disabled={currentPage >= totalPages}>&raquo;</button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
    </main>

      {/* Modals */}
      {showCreateModal && (
        <CreateFolderModal appSlug={appSlug || ''}
          parentFolderPath={currentFolder?.path || currentFolderPath}
          folders={currentFolderPath ? subfolders : rootFolders}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateFolder} />
      )}
      {showEditModal && editingFolder && (
        <CreateFolderModal appSlug={appSlug || ''}
          parentFolderPath={editingFolder.parent_folder_path}
          folders={currentFolderPath ? subfolders : rootFolders}
          mode="edit" folderToEdit={editingFolder}
          onClose={() => { setShowEditModal(false); setEditingFolder(null); }}
          onSubmit={handleSaveEditFolder} />
      )}

      {/* Move Folder Modal */}
      {/* Edit Document Modal */}
      {editingDoc && (
        <div className="fb-d-flex fb-align-center fb-justify-center" style={{position:"fixed",top:0,right:0,bottom:0,left:0,background:"rgba(107,114,128,0.75)",zIndex:50,padding:16}}>
          <div className="panel panel-default" style={{width:"100%",maxWidth:680}}>
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
                    style={{ width: '100%' }}
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
                    style={{ width: '100%' }}
                  />
                </div>
                <div className="fb-d-flex fb-justify-end fb-gap-2" style={{marginTop:24}}>
                  <button
                    onClick={handleCancelEditDoc}
                    className="btn btn-default"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEditDoc}
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

      {showMoveFolderModal && (
        <div className="modal-overlay">
          <div className="modal-box" style={{ maxWidth: 520, margin: '60px auto' }}>
            <div className="panel panel-default" style={{ margin: 0 }}>
              <div className="panel-heading">
                <button className="close" onClick={() => setShowMoveFolderModal(false)}>&times;</button>
                <h3 className="panel-title">📦 Move Folder</h3>
              </div>
              <div className="panel-body">
                <p className="text-muted">Moving: <code>{currentFolder?.path || currentFolderPath}</code></p>
                <div className="form-group">
                  <label>Target Parent Folder Path</label>
                  <input type="text" className="form-control" value={moveFolderTarget}
                    onChange={e => setMoveFolderTarget(e.target.value)}
                    placeholder="e.g. /boarding/canadasite/en/new-parent"
                    disabled={moveFolderLoading} />
                  <small className="text-muted">Enter the full path of the target parent folder</small>
                </div>
                {moveFolderError && <div className="alert alert-danger small">{moveFolderError}</div>}
              </div>
              <div className="panel-footer text-right">
                <button className="btn btn-default" onClick={() => setShowMoveFolderModal(false)} disabled={moveFolderLoading}>Cancel</button>
                <button className="btn btn-warning" onClick={handleMoveFolderConfirm}
                  disabled={moveFolderLoading || !moveFolderTarget.trim()} style={{ marginLeft: 8 }}>
                  {moveFolderLoading ? 'Moving...' : '📦 Move'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ClientAppFolders;
