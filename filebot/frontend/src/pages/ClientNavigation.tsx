import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AppService from '../services/app.service';
import DocumentService from '../services/document.service';
import FolderService from '../services/folder.service';
import { App } from '../services/app.service';
import { Document } from '../services/document.service';
import { Folder } from '../services/folder.service';

interface ThumbnailItem {
  id: string;
  documentId: string;
  title: string;
  thumbnailUrl: string;
  fullImageUrl: string;
  fileType: string;
  fileSize?: number;
  uploadedAt?: string;
}

const ClientNavigation: React.FC = () => {
  const { appSlug } = useParams<{ appSlug: string }>();
  const navigate = useNavigate();

  const [apps, setApps] = useState<App[]>([]);
  const [selectedApp, setSelectedApp] = useState<App | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [thumbnailItems, setThumbnailItems] = useState<ThumbnailItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');
  const [lightboxItem, setLightboxItem] = useState<ThumbnailItem | null>(null);

  const loadApps = useCallback(async () => {
    try {
      const appsData = await AppService.getApps();
      setApps(appsData);
      if (appSlug && appsData.length) {
        const found = appsData.find((a: App) => a.slug === appSlug);
        if (found) setSelectedApp(found);
        else setSelectedApp(appsData[0]);
      } else if (appsData.length) {
        setSelectedApp(appsData[0]);
      }
    } catch {
      setError('Failed to load applications list');
    }
  }, [appSlug]);

  const loadFolders = useCallback(async (slug: string) => {
    try {
      const data = await FolderService.getFolders(slug, { parent_folder_path: `/${slug}` });
      setFolders(data);
      setSelectedFolder(data.length ? data[0] : null);
    } catch {
      setError('Failed to load folders');
    }
  }, []);

  const loadDocuments = useCallback(async (folderId: string) => {
    if (!folderId) return;
    try {
      setLoading(true);
      const docs = await DocumentService.getDocuments(folderId);
      setDocuments(docs);
      setThumbnailItems(docs.map((doc: Document) => {
        const ident = doc.path || doc.storage_path || doc.id;
        const encoded = encodeURIComponent(ident);
        return {
          id: ident,
          documentId: ident,
          title: doc.title || doc.original_filename || 'Untitled',
          thumbnailUrl: `/api/v1/documents/${encoded}/thumbnail`,
          fullImageUrl: `/api/v1/documents/${encoded}/download`,
          fileType: doc.file_type || 'unknown',
          fileSize: doc.file_size,
          uploadedAt: doc.created_at
        };
      }));
    } catch {
      setError('Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const init = async () => { setLoading(true); await loadApps(); setLoading(false); };
    init();
  }, [loadApps]);

  useEffect(() => {
    if (selectedApp?.id) loadFolders(selectedApp.slug || selectedApp.id);
  }, [selectedApp, loadFolders]);

  useEffect(() => {
    if (selectedFolder?.path) loadDocuments(selectedFolder.path);
  }, [selectedFolder, loadDocuments]);

  const handleAppSelect = (app: App) => {
    setSelectedApp(app);
    if (appSlug !== app.slug) navigate(`/apps/${app.slug}/navigation`);
  };

  const filtered = thumbnailItems.filter(item =>
    item.title.toLowerCase().includes(filterText.toLowerCase())
  );

  if (loading && !selectedApp) {
    return (
      <div className="fb-loading" style={{ minHeight: '50vh' }}>
        <div className="text-center">
          <div className="spinner-border" role="status" style={{ width: '3rem', height: '3rem' }}>
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="text-muted" style={{ marginTop: 12 }}>Loading applications...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger" style={{ margin: 15 }}>
        <strong>Error</strong>
        <p>{error}</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="container-fluid" style={{ padding: 0 }}>
      <div className="row" style={{ minHeight: 'calc(100vh - 60px)' }}>
        {/* Sidebar */}
        <div className="col-md-3 col-lg-2 fb-sidebar" style={{ overflowY: 'auto', maxHeight: '100vh', background: '#f5f5f5', borderRight: '1px solid #ddd', padding: 15 }}>
          <div className="fb-sidebar-cat">Applications</div>
          <ul className="fb-sidebar-nav">
            {apps.map(app => (
              <li key={app.id}>
                <a href="#"
                  className={selectedApp?.id === app.id ? 'active' : ''}
                  onClick={e => { e.preventDefault(); handleAppSelect(app); }}
                >
                  {app.icon && <span style={{ marginRight: 6 }}>{app.icon}</span>}
                  {app.name}
                </a>
              </li>
            ))}
          </ul>

          {selectedApp && (
            <>
              <div className="fb-sidebar-cat">Folders</div>
              <ul className="fb-sidebar-nav">
                {folders.map(folder => (
                  <li key={folder.path}>
                    <a href="#"
                      className={selectedFolder?.path === folder.path ? 'active' : ''}
                      onClick={e => { e.preventDefault(); setSelectedFolder(folder); }}
                      style={{ fontSize: '0.9em' }}
                    >
                      📁 {folder.name}
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        {/* Main content */}
        <div className="col-md-9 col-lg-10" style={{ padding: 15, overflowY: 'auto', maxHeight: '100vh' }}>
          <div className="fb-page-header">
            <h2 style={{ margin: 0 }}>
              {selectedApp ? selectedApp.name : 'Select an Application'}
              {selectedFolder && <small className="text-muted"> / {selectedFolder.name}</small>}
            </h2>
          </div>

          {/* Filter */}
          <div className="row" style={{ marginBottom: 15 }}>
            <div className="col-sm-6">
              <div className="input-group">
                <input type="search" className="form-control"
                  placeholder="Filter documents by name..." value={filterText}
                  onChange={e => setFilterText(e.target.value)} />
                {filterText && (
                  <span className="input-group-btn">
                    <button className="btn btn-default" onClick={() => setFilterText('')}>✕</button>
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Stats bar */}
          <div className="alert alert-info" style={{ padding: '6px 12px', fontSize: '0.85em', marginBottom: 15 }}>
            <strong>{folders.length}</strong> folders |{' '}
            <strong>{documents.length}</strong> documents |{' '}
            <strong>{filtered.length}</strong> showing
          </div>

          {/* Content */}
          {loading ? (
            <div className="fb-loading" style={{ minHeight: 200 }}>
              <div className="text-center">
                <div className="spinner-border" role="status" style={{ width: '2rem', height: '2rem' }}>
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="text-muted" style={{ marginTop: 8 }}>Loading documents...</p>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="fb-empty-state">
              <p style={{ fontSize: '2em', marginBottom: 8 }}>📭</p>
              <p>{filterText ? 'Try adjusting your filter' : 'No documents in this folder'}</p>
            </div>
          ) : (
            <div className="row">
              {filtered.map(item => (
                <div className="col-xs-6 col-sm-4 col-md-3 col-lg-2" key={item.id}
                  style={{ marginBottom: 15 }}>
                  <div className="panel panel-default"
                    style={{ cursor: 'pointer', marginBottom: 0, transition: 'box-shadow .15s' }}
                    onClick={() => setLightboxItem(item)}
                    onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,.15)')}
                    onMouseLeave={e => (e.currentTarget.style.boxShadow = '')}>
                    <div className="panel-body text-center"
                      style={{ padding: 8, height: 130, overflow: 'hidden', background: '#f9f9f9' }}>
                      {item.thumbnailUrl ? (
                        <img src={item.thumbnailUrl} alt={item.title}
                          style={{ maxWidth: '100%', maxHeight: 114, objectFit: 'contain' }}
                          onError={e => {
                            (e.target as HTMLImageElement).style.display = 'none';
                            const p = (e.target as HTMLElement).parentElement;
                            if (p) p.innerHTML = '<div style="padding:30px 0;color:#999">📄<br><small>' + item.fileType.toUpperCase() + '</small></div>';
                          }} />
                      ) : (
                        <div style={{ padding: '30px 0', color: '#999' }}>
                          📄<br /><small>{item.fileType.toUpperCase()}</small>
                        </div>
                      )}
                    </div>
                    <div className="panel-body" style={{ padding: '8px 10px' }}>
                      <div className="fb-text-truncate" style={{ fontSize: '0.82em', fontWeight: 500 }}>
                        {item.title}
                      </div>
                      <div className="fb-d-flex fb-justify-between fb-align-center"
                        style={{ fontSize: '0.75em', color: '#999', marginTop: 4 }}>
                        <span>{item.fileSize ? `${(item.fileSize / 1024).toFixed(0)}KB` : ''}</span>
                        <span className="label label-default" style={{ fontSize: '0.85em' }}>{item.fileType}</span>
                      </div>
                    </div>
                    <div className="panel-footer" style={{ padding: '6px 10px' }}>
                      <button className="btn btn-default btn-xs btn-block"
                        onClick={e => { e.stopPropagation(); window.open(item.fullImageUrl, '_blank'); }}>
                        ⬇ Download
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Lightbox overlay */}
      {lightboxItem && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.85)', zIndex: 2000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column'
        }} onClick={() => setLightboxItem(null)}>
          <button className="btn btn-link"
            style={{ position: 'absolute', top: 20, right: 20, color: '#fff', fontSize: 28 }}
            onClick={() => setLightboxItem(null)}>✕</button>
          <img src={lightboxItem.fullImageUrl} alt={lightboxItem.title}
            style={{ maxWidth: '90vw', maxHeight: '85vh', objectFit: 'contain' }}
            onClick={e => e.stopPropagation()} />
          <div style={{ color: '#fff', marginTop: 15, fontSize: '0.95em' }}>
            {lightboxItem.title}
          </div>
          <a href={lightboxItem.fullImageUrl} download
            className="btn btn-primary" style={{ marginTop: 10 }}
            onClick={e => e.stopPropagation()}>
            ⬇ Download
          </a>
        </div>
      )}
    </div>
  );
};

export default ClientNavigation;
