import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import appService from '../services/app.service';
import folderService from '../services/folder.service';
import documentService from '../services/document.service';
import type { Folder } from '../services/folder.service';
import PreviewOverlay from '../components/PreviewOverlay';

const ClientDashboard: React.FC = () => {
  const { appSlug } = useParams<{ appSlug: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<any>(null);
  const [childFolders, setChildFolders] = useState<Folder[]>([]);
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [allFolders, setAllFolders] = useState<Folder[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState<string>('');
  const [previewFileType, setPreviewFileType] = useState<string>('');

  useEffect(() => { fetchData(); }, [appSlug]);

  const fetchRootFolders = async () => {
    try {
      const rootPath = '/' + appSlug;
      const folders = await folderService.getFolders(appSlug || '', { parent_folder_path: rootPath, limit: 1000 });
      setAllFolders(folders || []);
      setChildFolders(folders || []);
    } catch (err) { console.error('Failed to fetch root folders:', err); setChildFolders([]); }
  };

  const fetchChildFolders = async (parentFolderPath: string) => {
    try {
      const children = await folderService.getFolders(appSlug || '', { parent_folder_path: parentFolderPath, limit: 1000 });
      setAllFolders(prev => {
        const existing = new Map(prev.map(f => [f.path, f]));
        (children || []).forEach(f => existing.set(f.path, f));
        return Array.from(existing.values());
      });
      setChildFolders(children || []);
    } catch (err) { console.error('Failed to fetch child folders:', err); setChildFolders([]); }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const appData = await appService.getAppById(appSlug || '');
      if (appData) { setApp(appData); await fetchRootFolders(); }
    } catch (err) { console.error('Failed to fetch data:', err); }
    finally { setLoading(false); }
  };

  const fetchFolderDocuments = async (folderPath: string, overridePage?: number, overrideSize?: number) => {
    const p = overridePage ?? currentPage;
    const s = overrideSize ?? pageSize;
    try {
      const docs = await documentService.getDocumentsByFolderPath(folderPath, {
        skip: (p - 1) * s, limit: s, sort_by: 'created_at', sort_order: 'desc'
      });
      setDocuments(docs);
      setTotalPages(docs.length < s ? p : p + 5);
    } catch (err) { console.error('Failed to fetch docs:', err); setDocuments([]); }
  };

  const handleFolderClick = (folder: Folder) => navigate(`/apps${folder.path}`);

  const navigateToBreadcrumb = async (targetPath: string) => {
    let target = allFolders.find((f: Folder) => f.path === targetPath);
    if (!target) {
      try {
        target = await folderService.getFolder(targetPath);
        if (target) setAllFolders(prev => { const m = new Map(prev.map(f => [f.path, f])); m.set(target.path, target); return Array.from(m.values()); });
      } catch {}
    }
    if (target) { setCurrentFolder(target); setCurrentPage(1); await fetchChildFolders(targetPath); await fetchFolderDocuments(targetPath); }
    else { setCurrentFolder(null); setDocuments([]); setCurrentPage(1); await fetchChildFolders(targetPath); }
  };

  const backToParent = async () => {
    if (!currentFolder) return;
    const parentPath = currentFolder.parent_folder_path;
    if (parentPath) {
      let parent = allFolders.find((f: Folder) => f.path === parentPath);
      if (!parent) { try { parent = await folderService.getFolder(parentPath); if (parent) setAllFolders(prev => { const m = new Map(prev.map(f => [f.path, f])); m.set(parent.path, parent); return Array.from(m.values()); }); } catch {} }
      if (parent) { setCurrentFolder(parent); await fetchChildFolders(parentPath); await fetchFolderDocuments(parentPath); return; }
      else { setCurrentFolder(null); await fetchChildFolders(parentPath); await fetchFolderDocuments(parentPath); return; }
    }
    setCurrentFolder(null); await fetchRootFolders(); setDocuments([]);
  };

  const handlePageChange = (page: number) => { setCurrentPage(page); if (currentFolder) fetchFolderDocuments(currentFolder.path || '', page, pageSize); };
  const handlePageSizeChange = (size: number) => { setPageSize(size); setCurrentPage(1); if (currentFolder) fetchFolderDocuments(currentFolder.path || '', 1, size); };

  const handleDownload = async (documentId: string, filename: string) => {
    try {
      const blob = await documentService.downloadDocument(documentId);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a'); a.href = url; a.download = filename;
      window.document.body.appendChild(a); a.click();
      window.URL.revokeObjectURL(url); window.document.body.removeChild(a);
    } catch (err: any) { if (typeof window.showWetAlert === 'function') window.showWetAlert(`Download failed: ${err.message || 'Unknown error'}`); }
  };

  const buildPreviewUrl = (doc: any): string | null => {
    const identifier = doc.path || doc.storage_path || doc.id;
    if (!identifier) return null;
    const encodedId = encodeURIComponent(identifier);
    const token = localStorage.getItem('access_token');
    const ft = doc.file_type?.toLowerCase() || '';
    if (ft.match(/html?/)) return token ? `/api/v1/documents/${encodedId}/preview/html?token=${encodeURIComponent(token)}` : `/api/v1/documents/${encodedId}/preview/html`;
    if (ft.match(/(jpe?g|png|gif|bmp|webp|svg)/)) {
      const originalUrl = doc.document_metadata?.url || doc.metadata?.url;
      if (originalUrl) { try { return new URL(originalUrl).pathname; } catch {} }
      return token ? `/api/v1/documents/${encodedId}/preview?token=${encodeURIComponent(token)}` : `/api/v1/documents/${encodedId}/preview`;
    }
    if (ft.match(/tiff?/)) return token ? `/api/v1/documents/${encodedId}/download?download_type=pdf&token=${encodeURIComponent(token)}` : `/api/v1/documents/${encodedId}/download?download_type=pdf`;
    return token ? `/api/v1/documents/${encodedId}/download?token=${encodeURIComponent(token)}` : `/api/v1/documents/${encodedId}/download`;
  };

  const handlePreview = (doc: any) => { const url = buildPreviewUrl(doc); if (url) { setPreviewUrl(url); setPreviewTitle(doc.title || doc.original_filename || 'Document Preview'); setPreviewFileType(doc.file_type || ''); } };
  const handleClosePreview = () => { setPreviewUrl(null); setPreviewTitle(''); setPreviewFileType(''); };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    if (!currentFolder) { if (typeof window.showWetAlert === 'function') window.showWetAlert('Please select a folder'); return; }
    setIsSearching(true);
    try { const results = await documentService.searchDocuments({ q: searchQuery.trim(), path: currentFolder.path }); setSearchResults(results); }
    catch { if (typeof window.showWetAlert === 'function') window.showWetAlert('Search failed, please try again'); setSearchResults([]); }
    finally { setIsSearching(false); }
  };

  const handleClearSearch = () => { setSearchQuery(''); setSearchResults(null); };
  const getDisplayDocuments = () => searchResults !== null ? searchResults : documents;
  const isShowingSearchResults = () => searchResults !== null && searchQuery.trim() !== '';

  const fileTypeLabel = (ft: string) => {
    const t = (ft || '').toLowerCase();
    if (t.includes('pdf')) return 'label-danger';
    if (t.includes('html') || t.includes('htm')) return 'label-success';
    if (t.includes('doc')) return 'label-info';
    return 'label-default';
  };

  return (
    <div className="fb-page-bg">
      <div className="container">
        {/* Breadcrumb */}
        <div className="fb-d-flex fb-align-center fb-gap-1 text-muted" style={{ marginBottom: 12, fontSize: '0.85em' }}>
          <Link to="/apps">Apps</Link>
          <span>&rsaquo;</span>
          <Link to={`/apps/${appSlug}`}>{app?.name || 'App'}</Link>
          {currentFolder?.path && (() => {
            const segments = currentFolder.path.split('/').filter(Boolean).slice(1);
            if (!segments.length) return null;
            let accumulatedPath = '/' + appSlug;
            return segments.map((segment, index) => {
              accumulatedPath += '/' + segment;
              const isLast = index === segments.length - 1;
              return (<React.Fragment key={segment}><span>&rsaquo;</span>
                {isLast ? <span className="text-muted">{currentFolder?.name || segment}</span>
                  : <a href="#" onClick={e => { e.preventDefault(); navigateToBreadcrumb(accumulatedPath); }}>{segment}</a>}
              </React.Fragment>);
            });
          })()}
        </div>

        {/* Header */}
        <div className="fb-page-header">
          <div className="fb-d-flex fb-justify-between fb-align-center">
            <div>
              <h1 style={{ margin: 0, fontSize: '1.6em' }}>{app?.name || 'App Details'}</h1>
              <p className="text-muted" style={{ marginTop: 4 }}>
                {app?.description || 'Public Document Portal'}
                {currentFolder && <span className="label label-primary" style={{ marginLeft: 10 }}>{documents.length} docs</span>}
              </p>
            </div>
            <Link to="/apps" className="btn btn-default">Back to Apps</Link>
          </div>
        </div>

        {/* Loading state */}
        {loading ? (
          <div className="fb-loading">
            <div className="text-center">
              <div className="spinner-border" role="status" style={{ width: '3rem', height: '3rem' }}>
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="text-muted" style={{ marginTop: 12 }}>Loading app...</p>
            </div>
          </div>
        ) : (
          <div className="row">
            {/* Left sidebar — folder list (col-lg-4 ≈ 33%) */}
            <div className="col-lg-4" style={{ marginBottom: 15 }}>
              <div className="panel panel-default">
                <div className="panel-heading">
                  <h3 className="panel-title">{currentFolder ? currentFolder.name : 'Folders'}</h3>
                  <p className="text-muted" style={{ fontSize: '0.8em', marginTop: 2 }}>
                    {currentFolder ? 'Sub-folders' : 'Root folders'}
                  </p>
                </div>

                {currentFolder && (
                  <div className="panel-body" style={{ paddingBottom: 0 }}>
                    <button onClick={backToParent} className="btn btn-link btn-sm" style={{ padding: 0 }}>
                      &larr; .. / {currentFolder.parent_folder_path ? 'Parent folder' : 'Root'}
                    </button>
                    <hr style={{ margin: '8px 0' }} />
                  </div>
                )}

                {childFolders.length === 0 ? (
                  <div className="panel-body text-center fb-empty-state">
                    <p style={{ fontSize: '2em' }}>📁</p>
                    <p>No sub-folders</p>
                    <small className="text-muted">This folder has no sub-folders.</small>
                  </div>
                ) : (
                  <ul className="list-group" style={{ maxHeight: 500, overflowY: 'auto' }}>
                    {childFolders.map(folder => (
                      <li key={folder.path} className={'list-group-item' + (currentFolder?.path === folder.path ? ' active' : '')}
                        style={{ cursor: 'pointer' }}
                        onClick={() => handleFolderClick(folder)}>
                        <div className="fb-d-flex fb-align-center">
                          <span style={{ marginRight: 8, fontSize: '1.2em' }}>📁</span>
                          <div>
                            <strong>{folder.name}</strong>
                            <br />
                            <small className="text-muted">
                              {folder.document_count !== undefined && <span>{folder.document_count} docs</span>}
                              {folder.total_size > 0 && <span> &middot; {(folder.total_size / 1024 / 1024).toFixed(1)} MB</span>}
                            </small>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}

                {currentFolder && (
                  <div className="panel-footer text-muted" style={{ fontSize: '0.8em' }}>
                    <div>Path: <code>{currentFolder?.path || '/'}</code></div>
                    <div>Docs: {documents.length} &middot; Created: {currentFolder?.created_at ? new Date(currentFolder.created_at).toLocaleDateString() : 'Unknown'}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Right side — document table (col-lg-8 ≈ 67%) */}
            <div className="col-lg-8">
              {currentFolder ? (
                <div className="panel panel-default">
                  <div className="panel-heading">
                    <div className="fb-d-flex fb-justify-between fb-align-center fb-wrap">
                      <div>
                        <h3 className="panel-title">Documents</h3>
                        <small className="text-muted">
                          Folder: <strong>{currentFolder.name}</strong>
                          {isShowingSearchResults() && <span className="label label-info" style={{ marginLeft: 6 }}>Search results</span>}
                        </small>
                      </div>
                      <form onSubmit={handleSearch} className="fb-d-flex fb-align-center fb-gap-1" style={{ marginTop: 5 }}>
                        <div className="input-group input-group-sm" style={{ maxWidth: 220 }}>
                          <input type="text" className="form-control" value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)} placeholder="Search titles..." />
                          {searchQuery && (
                            <span className="input-group-btn">
                              <button type="button" className="btn btn-default" onClick={handleClearSearch}>&times;</button>
                            </span>
                          )}
                        </div>
                        <button type="submit" className="btn btn-primary btn-sm" disabled={isSearching}>
                          {isSearching ? 'Searching...' : 'Search'}
                        </button>
                      </form>
                    </div>
                    {isShowingSearchResults() && (
                      <div className="alert alert-info" style={{ marginTop: 10, padding: '6px 12px', fontSize: '0.85em' }}>
                        <strong>{searchResults?.length || 0}</strong> results for "<strong>{searchQuery}</strong>"
                        <button className="btn btn-link btn-xs" onClick={handleClearSearch} style={{ float: 'right' }}>Clear search</button>
                      </div>
                    )}
                  </div>

                  {getDisplayDocuments().length === 0 ? (
                    <div className="panel-body text-center fb-empty-state">
                      <p style={{ fontSize: '2em' }}>📄</p>
                      <p>{isShowingSearchResults() ? `No results for "${searchQuery}"` : 'No documents in this folder'}</p>
                      {isShowingSearchResults() && <button onClick={handleClearSearch} className="btn btn-default btn-sm">Clear search</button>}
                    </div>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-striped table-hover" style={{ marginBottom: 0 }}>
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Size</th>
                            <th>Pages</th>
                            <th>Upload</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {getDisplayDocuments().map(doc => (
                            <tr key={doc.path || doc.storage_path}>
                              <td>
                                <strong>{doc.title}</strong>
                                <br /><small className="text-muted fb-text-truncate" style={{ maxWidth: 200 }}>{doc.original_filename}</small>
                              </td>
                              <td><span className={'label ' + fileTypeLabel(doc.file_type)}>{(doc.file_type || '').toUpperCase()}</span></td>
                              <td>{((doc.file_size || 0) / 1024 / 1024).toFixed(2)} MB</td>
                              <td>{doc.pages || '-'}</td>
                              <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                              <td>
                                <div className="btn-group btn-group-xs">
                                  <button className="btn btn-primary"
                                    onClick={() => handleDownload(doc.path || doc.storage_path, doc.original_filename)}>
                                    Download
                                  </button>
                                  <button className="btn btn-default"
                                    onClick={() => handlePreview(doc)}>
                                    Preview
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <div className="panel-footer">
                    <div className="fb-d-flex fb-justify-between fb-align-center text-muted" style={{ fontSize: '0.85em' }}>
                      <span>
                        Showing <strong>{getDisplayDocuments().length}</strong> docs
                        {isShowingSearchResults() && <span className="label label-info" style={{ marginLeft: 6 }}>Search</span>}
                      </span>
                      <div className="fb-d-flex fb-align-center fb-gap-1">
                        <select className="form-control input-sm" value={pageSize}
                          onChange={e => handlePageSizeChange(Number(e.target.value))} style={{ width: 'auto' }}>
                          <option value={25}>25</option>
                          <option value={50}>50</option>
                          <option value={100}>100</option>
                        </select>
                      </div>
                    </div>
                    {!isShowingSearchResults() && totalPages > 1 && (
                      <div className="fb-d-flex fb-justify-between fb-align-center" style={{ marginTop: 8, fontSize: '0.85em' }}>
                        <span className="text-muted">Page {currentPage} of {totalPages}</span>
                        <div className="btn-group btn-group-xs">
                          <button className="btn btn-default" onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage <= 1}>Prev</button>
                          <button className="btn btn-default" onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage >= totalPages}>Next</button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="panel panel-default">
                  <div className="panel-body text-center fb-empty-state">
                    <p style={{ fontSize: '3em', marginBottom: 10 }}>📁</p>
                    <h3>Select a Folder</h3>
                    <p className="text-muted">Choose a folder from the left sidebar to view its documents.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <hr />
        <p className="text-center text-muted" style={{ fontSize: '0.8em' }}>
          FileBot Client Portal &middot; {app?.name || 'App'}
        </p>

        <PreviewOverlay url={previewUrl} title={previewTitle} fileType={previewFileType} onClose={handleClosePreview} />
      </div>
    </div>
  );
};

export default ClientDashboard;
