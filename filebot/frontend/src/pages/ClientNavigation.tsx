import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AppService from '../services/app.service';
import DocumentService from '../services/document.service';
import FolderService from '../services/folder.service';
import { App } from '../services/app.service';
import { Document } from '../services/document.service';
import { Folder } from '../services/folder.service';
// import LoadingSpinner from '../components/common/LoadingSpinner';
// import ErrorAlert from '../components/common/ErrorAlert';

// Define types for thumbnail grid items
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
  
  // State management
  const [apps, setApps] = useState<App[]>([]);
  const [selectedApp, setSelectedApp] = useState<App | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [thumbnailItems, setThumbnailItems] = useState<ThumbnailItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');
  
  // Services (already imported as instances)
  const appService = AppService;
  const documentService = DocumentService;
  const folderService = FolderService;
  
  // Load apps list for sidebar
  const loadApps = useCallback(async () => {
    try {
      const appsData = await appService.getApps();
      setApps(appsData);
      
      // If appSlug is provided in URL, select that app
      if (appSlug && appsData.length > 0) {
        const foundApp = appsData.find((app: App) => app.slug === appSlug);
        if (foundApp) {
          setSelectedApp(foundApp);
        } else {
          // If app not found, select first app
          setSelectedApp(appsData[0]);
        }
      } else if (appsData.length > 0) {
        // Select first app by default
        setSelectedApp(appsData[0]);
      }
    } catch (err) {
      console.error('Failed to load apps:', err);
      setError('Failed to load applications list');
    }
  }, [appSlug]);
  
  // Load folders for selected app
  const loadFolders = useCallback(async (appSlug: string) => {
    try {
      const foldersData = await folderService.getFolders(appSlug, { 
        parent_folder_path: `/${appSlug}`
      });
      setFolders(foldersData);
      
      // Select first folder by default, or root folder if exists
      const rootFolder = foldersData.find((folder: Folder) => !folder.parent_folder_id);
      if (rootFolder) {
        setSelectedFolder(rootFolder);
      } else if (foldersData.length > 0) {
        setSelectedFolder(foldersData[0]);
      } else {
        setSelectedFolder(null);
      }
    } catch (err) {
      console.error('Failed to load folders:', err);
      setError('Failed to load folders for selected application');
    }
  }, []);
  
  // Load documents for selected folder
  const loadDocuments = useCallback(async (folderId: string) => {
    if (!folderId) return;
    
    try {
      setLoading(true);
      const documentsData = await documentService.getDocuments(folderId);
      setDocuments(documentsData);
      
      // Convert documents to thumbnail items
      const thumbnails: ThumbnailItem[] = documentsData.map((doc: Document) => {
        const docIdent = doc.path || doc.storage_path || doc.id;
        const encodedDoc = encodeURIComponent(docIdent);
        return {
          id: doc.id,
          documentId: docIdent,
          title: doc.title || doc.original_filename || 'Untitled',
          thumbnailUrl: `/api/v1/documents/${encodedDoc}/thumbnail`,
          fullImageUrl: `/api/v1/documents/${encodedDoc}/download`,
          fileType: doc.file_type || 'unknown',
          fileSize: doc.file_size,
          uploadedAt: doc.created_at
        };
      });
      
      setThumbnailItems(thumbnails);
    } catch (err) {
      console.error('Failed to load documents:', err);
      setError('Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Initialize data
  useEffect(() => {
    const initData = async () => {
      setLoading(true);
      await loadApps();
      setLoading(false);
    };
    
    initData();
  }, [loadApps]);
  
  // When selected app changes, load its folders
  useEffect(() => {
    if (selectedApp?.id) {
      loadFolders(selectedApp.slug || selectedApp.id);
    }
  }, [selectedApp, loadFolders]);
  
  // When selected folder changes, load its documents
  useEffect(() => {
    if (selectedFolder?.id) {
      // 优先使用路径，如果不存在则使用ID
      const folderIdentifier = selectedFolder.path || selectedFolder.id;
      loadDocuments(folderIdentifier);
    }
  }, [selectedFolder, loadDocuments]);
  
  // Handle app selection
  const handleAppSelect = (app: App) => {
    setSelectedApp(app);
    // Update URL if app slug is different
    if (appSlug !== app.slug) {
      navigate(`/apps/${app.slug}/navigation`);
    }
  };
  
  // Handle folder selection
  const handleFolderSelect = (folder: Folder) => {
    setSelectedFolder(folder);
  };
  
  // Filter thumbnails based on search text
  const filteredThumbnails = thumbnailItems.filter(item =>
    item.title.toLowerCase().includes(filterText.toLowerCase())
  );
  
  // Handle thumbnail click - open lightbox
  const handleThumbnailClick = (item: ThumbnailItem) => {
    // TODO: Implement lightbox opening
    // For now, open the full image in a new tab
    window.open(item.fullImageUrl, '_blank');
  };
  
  // Handle filter change
  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterText(e.target.value);
  };
  
  // Initialize WET framework components
  useEffect(() => {
    // Wait for WET framework to be loaded
    const initWETComponents = () => {
      // Check if window.wb object exists
      if ((window as any).wb) {
        // Initialize lightbox if not already initialized
        const lightboxElements = document.querySelectorAll('[data-wb-lbx]');
        lightboxElements.forEach(el => {
          if (!el.classList.contains('wb-lbx-initialized')) {
            el.classList.add('wb-lbx-initialized');
            // Trigger WET initialization
            (window as any).wb.init(el);
          }
        });
        
        // Initialize filter if not already initialized
        const filterElements = document.querySelectorAll('[data-wb-filter]');
        filterElements.forEach(el => {
          if (!el.classList.contains('wb-filter-initialized')) {
            el.classList.add('wb-filter-initialized');
            (window as any).wb.init(el);
          }
        });
        
        console.log('WET components initialized');
      } else {
        // Retry after 500ms if WET not loaded yet
        setTimeout(initWETComponents, 500);
      }
    };
    
    // Start initialization
    initWETComponents();
    
    // Cleanup if needed
    return () => {
      // Cleanup if necessary
    };
  }, [filteredThumbnails]); // Re-initialize when thumbnails change
  
  if (loading && !selectedApp) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '50vh' }}>
        <div className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading applications...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="alert alert-danger m-3">
        <h5 className="alert-heading">Error</h5>
        <p>{error}</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }
  
  return (
    <div className="container-fluid p-0">
      <div className="row g-0" style={{ minHeight: 'calc(100vh - 60px)' }}>
        {/* Sidebar - Apps List */}
        <div className="col-md-3 col-lg-2 bg-light border-end" style={{ overflowY: 'auto', maxHeight: '100vh' }}>
          <div className="p-3">
            <h2 className="h5 mb-3">Applications</h2>
            <div className="list-group">
              {apps.map(app => (
                <button
                  key={app.id}
                  className={`list-group-item list-group-item-action ${selectedApp?.id === app.id ? 'active' : ''}`}
                  onClick={() => handleAppSelect(app)}
                  style={{ textAlign: 'left' }}
                >
                  <div className="d-flex align-items-center">
                    {app.icon && (
                      <i className={`bi bi-${app.icon} me-2`}></i>
                    )}
                    <div>
                      <div className="fw-medium">{app.name}</div>
                      {app.description && (
                        <small className="text-muted d-block">{app.description}</small>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
            
            {selectedApp && (
              <>
                <h3 className="h6 mt-4 mb-2">Folders</h3>
                <div className="list-group">
                  {folders.map(folder => (
                    <button
                      key={folder.id}
                      className={`list-group-item list-group-item-action ${selectedFolder?.id === folder.id ? 'active' : ''}`}
                      onClick={() => handleFolderSelect(folder)}
                      style={{ textAlign: 'left', fontSize: '0.9rem' }}
                    >
                      <div className="d-flex align-items-center">
                        <i className="bi bi-folder me-2"></i>
                        <span>{folder.name}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
        
        {/* Main Content Area */}
        <div className="col-md-9 col-lg-10 p-4" style={{ overflowY: 'auto', maxHeight: '100vh' }}>
          <div className="mb-4">
            <h1 className="h3">
              {selectedApp ? selectedApp.name : 'Select an Application'}
              {selectedFolder && <span className="text-muted"> / {selectedFolder.name}</span>}
            </h1>
            
            {/* Filter input using WET framework */}
            <div className="row mb-3">
              <div className="col-md-6">
                <div className="wb-filter" data-wb-filter='{
                  "filterType": "list",
                  "filterGroup": ".thumbnail-grid",
                  "filterItem": ".thumbnail-item",
                  "filterSelector": ".thumbnail-title"
                }'>
                  <div className="input-group">
                    <label htmlFor="filterInput" className="wb-inv">Filter documents by name</label>
                    <input
                      type="search"
                      id="filterInput"
                      className="form-control"
                      placeholder="Filter documents by name..."
                      value={filterText}
                      onChange={handleFilterChange}
                      data-wb-filter='{
                        "action": "filter",
                        "selector": ".thumbnail-item",
                        "filterGroup": ".thumbnail-grid",
                        "filterSelector": ".thumbnail-title"
                      }'
                    />
                    <button
                      className="btn btn-primary"
                      type="button"
                      onClick={() => setFilterText('')}
                      aria-label="Clear filter"
                    >
                      <i className="bi bi-x"></i>
                    </button>
                  </div>
                  <div className="wb-filter-results alert alert-info wb-invisible mt-2">
                    <p><span className="wb-filter-count">0</span> of <span className="wb-filter-total">0</span> documents match your filter.</p>
                  </div>
                </div>
              </div>
              <div className="col-md-6 text-end">
                <div className="btn-group" role="group">
                  <button className="btn btn-default" type="button" data-wb-filter='{"action": "showAll"}'>
                    <i className="bi bi-eye"></i> Show All
                  </button>
                  <button className="btn btn-default" type="button" data-wb-filter='{"action": "hideAll"}'>
                    <i className="bi bi-eye-slash"></i> Hide All
                  </button>
                </div>
              </div>
            </div>
            
            {/* Stats */}
            <div className="alert alert-info py-2 mb-3">
              <div className="row">
                <div className="col">
                  <small>
                    <i className="bi bi-folder me-1"></i>
                    <strong>{folders.length}</strong> folders
                  </small>
                </div>
                <div className="col">
                  <small>
                    <i className="bi bi-file-earmark me-1"></i>
                    <strong>{documents.length}</strong> documents
                  </small>
                </div>
                <div className="col">
                  <small>
                    <i className="bi bi-eye me-1"></i>
                    <strong>{filteredThumbnails.length}</strong> showing
                  </small>
                </div>
              </div>
            </div>
          </div>
          
          {/* Thumbnail Grid with WET Lightbox */}
          {loading ? (
            <div className="d-flex justify-content-center align-items-center py-5">
              <div className="text-center">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-2">Loading documents...</p>
              </div>
            </div>
          ) : filteredThumbnails.length === 0 ? (
            <div className="text-center py-5">
              <i className="bi bi-folder-x display-1 text-muted mb-3"></i>
              <h3 className="h5">No documents found</h3>
              <p className="text-muted">
                {filterText ? 'Try adjusting your filter' : 'Upload documents to see them here'}
              </p>
            </div>
          ) : (
            <>
              {/* WET Lightbox Gallery - Hidden links for lightbox */}
              <div className="wb-lbx hidden">
                {filteredThumbnails.map(item => (
                  <a
                    key={item.id}
                    href={item.fullImageUrl}
                    className="wb-lbx-item"
                    title={item.title}
                    data-wb-lbx={`{"type": "image", "url": "${item.fullImageUrl}", "title": "${item.title}"}`}
                    aria-label={`View ${item.title}`}
                  >
                    {/* Hidden link for lightbox */}
                  </a>
                ))}
              </div>
              
              {/* Thumbnail Grid */}
              <div className="thumbnail-grid row row-cols-2 row-cols-md-3 row-cols-lg-4 row-cols-xl-5 g-3">
                {filteredThumbnails.map((item, index) => (
                  <div key={item.id} className="col thumbnail-item" data-wb-filter-item>
                    <div 
                      className="card h-100 border shadow-sm thumbnail-card"
                      style={{ cursor: 'pointer' }}
                      onClick={() => {
                        // Open WET lightbox
                        const lightboxItems = document.querySelectorAll('.wb-lbx-item');
                        if (lightboxItems[index]) {
                          (lightboxItems[index] as HTMLElement).click();
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          const lightboxItems = document.querySelectorAll('.wb-lbx-item');
                          if (lightboxItems[index]) {
                            (lightboxItems[index] as HTMLElement).click();
                          }
                        }
                      }}
                    >
                      <div className="card-img-top bg-light d-flex align-items-center justify-content-center" 
                           style={{ height: '150px', overflow: 'hidden' }}>
                        {item.thumbnailUrl ? (
                          <img 
                            src={item.thumbnailUrl} 
                            alt={item.title}
                            className="img-fluid thumbnail-image"
                            style={{ objectFit: 'cover', width: '100%', height: '100%' }}
                            onError={(e) => {
                              // Fallback to file type icon if thumbnail fails to load
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                              const parent = target.parentElement;
                              if (parent) {
                                parent.innerHTML = `
                                  <div class="text-center">
                                    <i class="bi bi-file-earmark display-4 text-muted"></i>
                                    <div class="mt-2 small">${item.fileType.toUpperCase()}</div>
                                  </div>
                                `;
                              }
                            }}
                          />
                        ) : (
                          <div className="text-center">
                            <i className="bi bi-file-earmark display-4 text-muted"></i>
                            <div className="mt-2 small">{item.fileType.toUpperCase()}</div>
                          </div>
                        )}
                      </div>
                      <div className="card-body p-3">
                        <h6 className="card-title mb-1 thumbnail-title" style={{ fontSize: '0.85rem' }}>
                          {item.title.length > 30 ? item.title.substring(0, 30) + '...' : item.title}
                        </h6>
                        <div className="d-flex justify-content-between align-items-center">
                          <small className="text-muted">
                            {item.fileSize ? `${(item.fileSize / 1024).toFixed(1)} KB` : 'Unknown size'}
                          </small>
                          <span className="badge bg-secondary">{item.fileType}</span>
                        </div>
                      </div>
                      <div className="card-footer bg-transparent border-top-0 py-2">
                        <button 
                          className="btn btn-sm btn-outline-primary w-100"
                          onClick={(e) => {
                            e.stopPropagation();
                            window.open(item.fullImageUrl, '_blank');
                          }}
                        >
                          <i className="bi bi-download me-1"></i> Download
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          
          {/* Lightbox Modal (placeholder) */}
          <div className="modal fade" id="imageLightbox" tabIndex={-1} aria-hidden="true">
            <div className="modal-dialog modal-dialog-centered modal-xl">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title" id="lightboxTitle">Image Preview</h5>
                  <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div className="modal-body text-center">
                  <img id="lightboxImage" src="" alt="" className="img-fluid" />
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                  <a id="lightboxDownload" href="#" className="btn btn-primary" download>
                    <i className="bi bi-download me-1"></i> Download
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientNavigation;