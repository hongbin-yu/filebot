import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import appService, { App } from '../services/app.service';
import authService from '../services/auth.service';
import folderService, { Folder } from '../services/folder.service';
import documentService, { Document } from '../services/document.service';
import PreviewOverlay from '../components/PreviewOverlay';
import CreateFolderModal from '../components/folders/CreateFolderModal';

// Format file size
function formatSize(bytes: number): string {
  if (!bytes || bytes === 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

// Format date
function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch { return dateStr; }
}

const ClientAppFolders: React.FC = () => {
  const { appSlug, '*': wildcardPath } = useParams<{ appSlug: string; '*': string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // App state
  const [app, setApp] = useState<App | null>(null);
  const [appLoading, setAppLoading] = useState(true);
  const [appError, setAppError] = useState<string | null>(null);

  // Folder state
  const [folders, setFolders] = useState<Folder[]>([]);
  const [subfolders, setSubfolders] = useState<Folder[]>([]);
  const [currentFolderPath, setCurrentFolderPath] = useState<string | null>(null);
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [foldersLoading, setFoldersLoading] = useState(false);

  // Document state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // Preview overlay state
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

  // Open document preview in overlay
  const openPreview = useCallback((url: string, e: React.MouseEvent) => {
    e.preventDefault();
    setPreviewUrl(url);
  }, []);

  // Load app info
  useEffect(() => {
    if (!appSlug) return;
    const loadApp = async () => {
      try {
        setAppLoading(true);
        const appData = await appService.getAppById(appSlug);
        setApp(appData);
      } catch (err: any) {
        console.error('Failed to load app:', err);
        setAppError(err?.response?.data?.detail || err.message || 'Failed to load app');
      } finally {
        setAppLoading(false);
      }
    };
    loadApp();
  }, [appSlug]);

  // Load root folders
  useEffect(() => {
    if (!appSlug) return;
    const loadFolders = async () => {
      try {
        setFoldersLoading(true);
        const data = await folderService.getFolders(appSlug, {
          path_starts_with: '/' + appSlug,
          limit: 10000
        });
        setFolders(data);
      } catch (err) {
        console.error('Failed to load folders:', err);
        setFolders([]);
      } finally {
        setFoldersLoading(false);
      }
    };
    loadFolders();
  }, [appSlug]);

  // Sync URL wildcard path → folder state
  useEffect(() => {
    // wildcardPath contains everything after /apps/:appSlug/
    // e.g. URL /apps/boarding/canadasite/en → wildcardPath = "canadasite/en"
    // Store as relative path without app slug (matches URL structure)
    if (wildcardPath && wildcardPath.trim()) {
      const path = '/' + wildcardPath.replace(/^\/+|\/+$/g, '');
      setCurrentFolderPath(path);
    } else {
      setCurrentFolderPath(null);
      setCurrentFolder(null);
      setSubfolders([]);
      setDocuments([]);
    }
  }, [wildcardPath, location.pathname]);

  // Load subfolders when current folder changes
  useEffect(() => {
    if (!currentFolderPath || !appSlug) {
      setSubfolders([]);
      setCurrentFolder(null);
      return;
    }

    const loadFolderDetails = async () => {
      try {
        // Build full path including app slug for API calls
        const fullPath = '/' + appSlug + currentFolderPath;
        
        // Try to get folder by path
        const allFolders = await folderService.getFolders(appSlug, { parent_folder_path: fullPath });

        // Find the current folder among all folders
        let current: Folder | null = null;
        const subs: Folder[] = [];

        for (const f of allFolders) {
          if (f.path === fullPath) {
            current = f;
          } else if (f.parent_folder_path === fullPath) {
            subs.push(f);
          }
        }

        // If not found in this query, get it directly by path
        if (!current) {
          try {
            current = await folderService.getFolder(fullPath);
          } catch (err) {
            console.warn('Could not find current folder by path:', fullPath);
          }
        }

        // Deduplicate subs
        const seen = new Set<string>();
        const uniqueSubs = subs.filter(f => {
          const key = f.path;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        setCurrentFolder(current);
        setSubfolders(uniqueSubs);
      } catch (err) {
        console.error('Failed to load folder details:', err);
      }
    };

    loadFolderDetails();
  }, [currentFolderPath, appSlug]);

  // Load documents from current folder (or app root if no folder selected)
  useEffect(() => {
    if (!appSlug) {
      setDocuments([]);
      return;
    }
    // Root level: load docs from app's root path (e.g. /publish)
    if (!currentFolderPath) {
      setDocumentsLoading(true);
      (async () => {
        try {
          const fullPath = '/' + appSlug;
          const loadSkip = (currentPage - 1) * pageSize;
          const docs = await documentService.getDocumentsByFolderPath(fullPath, { skip: loadSkip, limit: pageSize });
          const total = documentService.lastTotalCount;
          setTotalPages(Math.ceil(total / pageSize) || 1);
          setDocuments(docs);
        } catch (err) {
          console.error('Failed to load root documents:', err);
          setDocuments([]);
        } finally {
          setDocumentsLoading(false);
        }
      })();
      return;
    }

    const loadAllDocumentsRecursive = async () => {
      setDocumentsLoading(true);
      try {
        const fullPath = '/' + appSlug + currentFolderPath;

        // 前三层只显示直属文档，更深层显示全部递归文档
        const pathDepth = currentFolderPath.split('/').filter(Boolean).length;
        const loadSkip = (currentPage - 1) * pageSize;
        let docs;
        if (pathDepth >= 3) {
          docs = await documentService.getDocumentsByPathPrefix(fullPath, { skip: loadSkip, limit: pageSize });
        } else {
          docs = await documentService.getDocumentsByFolderPath(fullPath, { skip: loadSkip, limit: pageSize });
        }

        const total = documentService.lastTotalCount;
        setTotalPages(Math.ceil(total / pageSize) || 1);
        setDocuments(docs);
      } catch (err) {
        console.error('Failed to load documents recursively:', err);
        setDocuments([]);
      } finally {
        setDocumentsLoading(false);
      }
    };

    loadAllDocumentsRecursive();
  }, [currentFolderPath, appSlug, currentPage, pageSize]);

  // Handle search (recursive: searches across all descendant folders)
  const handleSearch = useCallback(async (query: string) => {
    setSearchQuery(query);
    
    if (!currentFolderPath) return;
    const fullPath = '/' + appSlug + currentFolderPath;

    if (!query.trim()) {
      // Clear search - reload recursively (single API call)
      setIsSearching(false);
      try {
        setDocumentsLoading(true);
        const pathDepth = currentFolderPath.split('/').filter(Boolean).length;
        const skip = (currentPage - 1) * pageSize;
        let docs;
        if (pathDepth >= 3) {
          docs = await documentService.getDocumentsByPathPrefix(fullPath, { skip, limit: pageSize });
        } else {
          docs = await documentService.getDocumentsByFolderPath(fullPath, { skip, limit: pageSize });
        }
        const total = documentService.lastTotalCount;
        setTotalPages(Math.ceil(total / pageSize) || 1);
        setDocuments(docs);
      } catch (err) {
        console.error('Failed to reload documents:', err);
      } finally {
        setDocumentsLoading(false);
      }
      return;
    }

    try {
      setIsSearching(true);
      const results = await documentService.searchDocuments({
        q: query,
        path: fullPath,
        limit: 1000
      });
      setDocuments(results || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  }, [currentFolderPath, appSlug, currentPage, pageSize]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
  };

  const handleFolderClick = (folderPath: string) => {
    // Strip app slug prefix if present (API paths include it)
    const appPrefix = '/' + appSlug;
    const relativePath = folderPath.startsWith(appPrefix)
      ? folderPath.slice(appPrefix.length)
      : folderPath;
    
    const cleanPath = relativePath.replace(/^\/+/, '');
    if (!cleanPath) {
      navigate(`/apps/${appSlug}`, { replace: false });
    } else {
      navigate(`/apps/${appSlug}/${cleanPath}`, { replace: false });
    }
  };

  const handlePreviewDocument = (doc: Document) => {
    const docPath = doc.path || doc.storage_path;
    navigate(`/documents/${(docPath || '').replace(/^\//, '')}`);
  };

  // Build breadcrumbs from path
  const buildBreadcrumbs = (): { name: string; path: string }[] => {
    const crumbs: { name: string; path: string }[] = [];
    
    // Always include app name as first breadcrumb
    crumbs.push({
      name: app?.name || appSlug || 'App',
      path: '/' + appSlug
    });

    if (!currentFolderPath && !currentFolder) {
      return crumbs;
    }

    const path = currentFolderPath || currentFolder?.path || '';
    const segments = path.split('/').filter(Boolean);

    // Build from app root, not from segments alone
    for (let i = 0; i < segments.length; i++) {
      const subPath = '/' + appSlug + '/' + segments.slice(0, i + 1).join('/');
      crumbs.push({
        name: segments[i],
        path: subPath
      });
    }

    return crumbs;
  };

  // Loading state
  if (appLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading app...</div>
      </div>
    );
  }

  // Error state
  if (appError || !app) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">Error</h3>
          <p className="text-red-700 mb-4">{appError || 'Could not find the specified app.'}</p>
          <Link to="/apps" className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
            Back to App List
          </Link>
        </div>
      </div>
    );
  }

  const breadcrumbs = buildBreadcrumbs();
  const rootFolders = currentFolderPath ? [] : folders.filter(f => f.parent_folder_path === '/' + appSlug);

  // Folder icon SVG component
  const FolderIcon = ({ className }: { className?: string }) => (
    <svg className={className || 'w-5 h-5'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  );

  // ── Folder Operation Handlers ──

  const handleCreateFolder = async (data: { name: string; description?: string; parent_folder_path?: string; path?: string; app_id: string }) => {
    try {
      await folderService.createFolder(data);
      if (currentFolderPath && appSlug) {
        const fullPath = '/' + appSlug + currentFolderPath;
        const subs = await folderService.getFolders(appSlug, { parent_folder_path: fullPath });
        setSubfolders(subs);
      }
    } catch (err) {
      console.error('Failed to create folder:', err);
      throw err;
    }
  };

  const handleNavigateToUpload = (folderPath: string) => {
    navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(folderPath)}`);
  };

  const handleNavigateToDocuments = (folderPath: string) => {
    const encodedPath = encodeURIComponent(folderPath);
    navigate(`/apps/${appSlug}/folders/${encodedPath}/documents`);
  };

  const handleEditFolder = (folderPath: string) => {
    const allFolders = folders.concat(subfolders);
    const folderToEdit = allFolders.find(f => f.path === folderPath);
    if (!folderToEdit) return;
    setEditingFolder(folderToEdit);
    setShowEditModal(true);
  };

  const handleSaveEditFolder = async (data: { name: string; description?: string; parent_folder_path?: string }) => {
    if (!editingFolder || !editingFolder.path) return;
    try {
      await folderService.updateFolder(editingFolder.path, data);
      if (currentFolderPath && appSlug) {
        const fullPath = '/' + appSlug + currentFolderPath;
        const subs = await folderService.getFolders(appSlug, { parent_folder_path: fullPath });
        setSubfolders(subs);
        const updated = await folderService.getFolder(fullPath);
        if (updated) setCurrentFolder(updated);
      }
      setShowEditModal(false);
      setEditingFolder(null);
    } catch (err) {
      console.error('Failed to edit folder:', err);
      throw err;
    }
  };

  const handleDeleteFolder = async (folderPath: string) => {
    if (!window.confirm('Delete this folder? All documents inside will also be deleted.')) return;
    try {
      await folderService.deleteFolder(folderPath, true);
      // Reload subfolders from parent
      if (currentFolder?.parent_folder_path && appSlug) {
        const fullPath = '/' + appSlug + currentFolderPath;
        const subs = await folderService.getFolders(appSlug, { parent_folder_path: currentFolder.parent_folder_path });
        setSubfolders(subs);
      }
    } catch (err) {
      console.error('Failed to delete folder:', err);
    }
  };

  return (
    <>
      <PreviewOverlay url={previewUrl} onClose={() => setPreviewUrl(null)} />
      <div className="p-6">
      {/* Breadcrumb */}
      <div className="mb-4">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/apps" className="hover:text-blue-600">Apps</Link>
          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={crumb.path}>
              <span>›</span>
              {index < breadcrumbs.length - 1 ? (
                <button
                  type="button"
                  className="hover:text-blue-600 underline underline-offset-2"
                  onClick={() => handleFolderClick(crumb.path)}
                >
                  {crumb.name}
                </button>
              ) : (
                <span className="text-gray-700 font-medium">{crumb.name}</span>
              )}
            </React.Fragment>
          ))}
        </div>
        <h1 className="text-2xl font-bold text-gray-800">{app.name}</h1>
        <p className="text-gray-600 mt-1">{app.description}</p>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <form onSubmit={(e) => { e.preventDefault(); handleSearch(searchQuery); }} className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-24 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="absolute inset-y-0 right-0 flex items-center pr-2 space-x-1">
            {searchQuery && (
              <button
                type="button"
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                onClick={() => {
                  setSearchQuery('');
                  handleSearch('');
                }}
                title="Clear search"
              >
                ✕
              </button>
            )}
            <button
              type="submit"
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
            >
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Two-Column Layout */}
      <div className="flex space-x-6">
        {/* Left: Folders + AI Operations */}
        <div className="w-1/3 space-y-4">
          <div className="bg-white rounded-lg shadow">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h3 className="font-medium">Folders</h3>
              <span className="text-xs text-gray-400">
                {currentFolderPath ? subfolders.length : rootFolders.length} folders
              </span>
            </div>

            <div className="p-4">
              {currentFolder && currentFolder.parent_folder_path && (
                <button
                  className="w-full mb-3 p-2 border border-dashed border-gray-300 rounded-lg text-sm text-blue-600 hover:bg-blue-50 flex items-center justify-center"
                  onClick={() => handleFolderClick(currentFolder.parent_folder_path!)}
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                  </svg>
                  .. Up to parent
                </button>
              )}

              {foldersLoading ? (
                <div className="text-center py-4 text-gray-500 text-sm">Loading...</div>
              ) : (
                <div className="space-y-2">
                  {(currentFolderPath ? subfolders : rootFolders).map(folder => (
                    <div
                      key={folder.path}
                      className={`p-3 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors ${
                        currentFolderPath === folder.path ? 'bg-blue-50 border-blue-200' : ''
                      }`}
                      onClick={() => handleFolderClick(folder.path || '')}
                    >
                      <div className="flex items-center">
                        <FolderIcon className="w-5 h-5 text-yellow-500 mr-2 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{folder.name}</div>
                          {folder.description && (
                            <div className="text-xs text-gray-500 truncate mt-0.5">{folder.description}</div>
                          )}
                          {folder.document_count !== undefined && (
                            <div className="text-xs text-gray-400 mt-0.5">
                              {folder.document_count} document{folder.document_count !== 1 ? 's' : ''}
                            </div>
                          )}
                        </div>
                        <svg className="w-4 h-4 text-gray-400 shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  ))}

                  {(currentFolderPath ? subfolders : rootFolders).length === 0 && (
                    <p className="text-gray-500 text-center py-4 text-sm">No folders</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* AI Operations Card - only visible with write permission */}
          {authService.isAdmin() && (
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h3 className="font-medium">AI Operations</h3>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-1 gap-3">
                  <button
                    className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                    onClick={() => {
                      const parentPath = currentFolder?.path || currentFolderPath || '';
                      setShowCreateModal(true);
                    }}
                  >
                    <div className="font-medium">Create Subfolder</div>
                    <div className="text-sm text-gray-500">Create a new subfolder in the current folder</div>
                  </button>
                  <button
                    className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                    onClick={() => handleNavigateToUpload(currentFolder?.path || currentFolderPath || '')}
                  >
                    <div className="font-medium">Upload</div>
                    <div className="text-sm text-gray-500">Upload files to this folder</div>
                  </button>
                  <button
                    className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                    onClick={() => handleNavigateToDocuments(currentFolder?.path || currentFolderPath || '')}
                  >
                    <div className="font-medium">Documents</div>
                    <div className="text-sm text-gray-500">Browse documents in this folder</div>
                  </button>
                  <button
                    className="p-3 border rounded-lg hover:bg-blue-50 text-left border-blue-200"
                    onClick={() => handleEditFolder(currentFolder?.path || currentFolderPath || '')}
                  >
                    <div className="font-medium text-blue-600">Edit Folder</div>
                    <div className="text-sm text-blue-500">Edit folder name and description</div>
                  </button>
                  <button
                    className="p-3 border rounded-lg hover:bg-red-50 text-left border-red-200"
                    onClick={() => handleDeleteFolder(currentFolder?.path || currentFolderPath || '')}
                  >
                    <div className="font-medium text-red-600">Delete Folder</div>
                    <div className="text-sm text-red-500">Delete this folder and all its contents</div>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Documents (Data Table) */}
        <div className="w-2/3">
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h3 className="font-medium">
                {currentFolder ? (
                  <>{currentFolder.name} — Documents (including subfolders)</>
                ) : documents.length > 0 ? (
                  <>Root — Documents</>
                ) : (
                  'Select a Document'
                )}
              </h3>
              <div className="text-sm text-gray-500">
                {documents.length} document{documents.length !== 1 ? 's' : ''}
                {isSearching && <span className="ml-2 text-blue-500">(search results)</span>}
              </div>
            </div>

            {!currentFolderPath && documents.length === 0 && !documentsLoading ? (
              <div className="text-center py-8 text-gray-500">
                <FolderIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                <p>Select a folder from the left panel</p>
              </div>
            ) : documentsLoading ? (
              <div className="text-center py-8 text-gray-500">
                Loading documents...
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>No documents found under this folder</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="table table-striped table-hover w-full text-sm">
                  <thead>
                    <tr>
                      <th></th>
                      <th style={{width:'80px'}}>Preview</th>
                      {appSlug === 'publish' && <th style={{width:'10px'}}>Publish<br/>status</th>}
                      <th>Name</th>
                      <th>Type</th>
                      <th>Size</th>
                      <th>Created</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map(doc => {
                      const token = localStorage.getItem('access_token');
                      const encodedPath = encodeURIComponent(doc.path || doc.storage_path);
                      // Published documents open directly on port 8003
                      const publishUrl = doc.publish_status === 'PUBLISHED' && doc.path
                        ? `http://localhost:8003${doc.path.replace('/publish', '')}`
                        : null;
                      const docViewUrl = publishUrl || (doc.file_type === 'html'
                        ? `/api/v1/documents/${encodedPath}/preview/html?token=${token}`
                        : `/api/v1/documents/${encodedPath}/download?preview=1&token=${token}`);
                      return (
                      <tr key={doc.path || doc.storage_path}>
                        <td className="text-center">
                          <a href={docViewUrl} onClick={(e) => { if (publishUrl) return; openPreview(docViewUrl, e); }} title="Preview" target={publishUrl ? '_blank' : undefined} rel="noopener noreferrer">
                            <span className="glyphicon glyphicon-file text-muted" style={{cursor:'pointer'}}></span>
                          </a>
                        </td>
                        <td className="text-center" style={{width:'80px', height:'auto'}}>
                          {(() => {
                            const isImage = ['jpeg', 'jpg', 'png', 'gif', 'svg', 'tiff', 'tif'].includes(doc.file_type);
                            if (!isImage) {
                              return <span className="text-muted" style={{fontSize:'10px'}}>—</span>;
                            }
                            const thumbUrl = `/api/v1/documents/${encodedPath}/thumbnail?token=${token}`;
                            return (
                              <img
                                src={thumbUrl}
                                alt="thumbnail"
                                style={{width:'64px', height:'64px', objectFit:'cover', borderRadius:'4px', border:'1px solid #e5e7eb'}}
                                onError={(e) => {
                                  (e.target as HTMLImageElement).style.display = 'none';
                                  (e.target as HTMLImageElement).parentElement!.innerHTML = '<span class="text-muted" style="font-size:10px">—</span>';
                                }}
                                loading="lazy"
                              />
                            );
                          })()}
                        </td>
                        <td className="text-center">
                          {appSlug === 'publish' && (
                            <label className="switch" style={{cursor:'pointer', margin:0, verticalAlign:'middle', display:'inline-block'}}>
                              <input
                                type="checkbox"
                                checked={doc.publish_status === 'PUBLISHED'}
                                onChange={async () => {
                                  const newStatus = doc.publish_status === 'PUBLISHED' ? 'UNPUBLISHED' : 'PUBLISHED';
                                  try {
                                    await documentService.updateDocument(
                                      doc.path || doc.storage_path,
                                      { publish_status: newStatus }
                                    );
                                    // Refresh documents
                                    setDocuments(prev => prev.map(d =>
                                      (d.path || d.storage_path) === (doc.path || doc.storage_path)
                                        ? { ...d, publish_status: newStatus }
                                        : d
                                    ));
                                  } catch (err) {
                                    console.error('Failed to update publish status:', err);
                                  }
                                }}
                              />
                              <span className="slider round"></span>
                            </label>
                          )}
                        </td>
                        <td>
                          <a href={docViewUrl} onClick={(e) => { if (publishUrl) return; openPreview(docViewUrl, e); }} title="Preview" target={publishUrl ? '_blank' : undefined} rel="noopener noreferrer">
                            <div className="font-medium" style={{cursor:'pointer'}}>
                              {doc.title || doc.original_filename || 'Untitled'}
                            </div>
                          </a>
                          <div className="small text-muted">
                            {(doc.parent_folder_path || doc.folder_path || '').replace('/' + appSlug, '')}
                          </div>
                        </td>
                        <td>
                          <span className="label label-default">
                            {(doc.file_type || doc.mime_type || '-').split('/').pop() || '-'}
                          </span>
                        </td>
                        <td className="text-right">
                          {formatSize(doc.file_size)}
                        </td>
                        <td>
                          <span className="small">{formatDate(doc.created_at)}</span>
                        </td>
                        <td>
                          <span className={`label ${
                            doc.conversion_status === 'completed'
                              ? 'label-success'
                              : doc.conversion_status === 'failed'
                              ? 'label-danger'
                              : doc.conversion_status === 'processing'
                              ? 'label-warning'
                              : 'label-default'
                          }`}>
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
                <div className="bg-white px-6 py-4 border-t border-gray-200">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="text-sm text-gray-600">
                      Page <span className="font-medium">{currentPage}</span> of{' '}
                      <span className="font-medium">{totalPages}</span>
                      {' · '}
                      <span className="font-medium">{documentService.lastTotalCount}</span> total docs
                    </div>

                    <div className="flex items-center gap-2">
                      <label className="text-sm text-gray-600">Per page:</label>
                      <select
                        value={pageSize}
                        onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                        className="border border-gray-300 rounded px-2 py-1 text-sm"
                      >
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handlePageChange(1)}
                        disabled={currentPage <= 1}
                        className="px-2 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-40"
                      >
                        ««
                      </button>
                      <button
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage <= 1}
                        className="px-2 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-40"
                      >
                        « Prev
                      </button>

                      {(() => {
                        const pages: (number | string)[] = [];
                        const maxVisible = 7;
                        if (totalPages <= maxVisible) {
                          for (let i = 1; i <= totalPages; i++) pages.push(i);
                        } else {
                          pages.push(1);
                          if (currentPage > 3) pages.push('...');
                          const start = Math.max(2, currentPage - 1);
                          const end = Math.min(totalPages - 1, currentPage + 1);
                          for (let i = start; i <= end; i++) pages.push(i);
                          if (currentPage < totalPages - 2) pages.push('...');
                          pages.push(totalPages);
                        }
                        return pages.map((p, idx) =>
                          p === '...' ? (
                            <span key={`e${idx}`} className="px-2 py-1 text-sm text-gray-400">…</span>
                          ) : (
                            <button
                              key={p}
                              onClick={() => handlePageChange(p as number)}
                              className={`px-2 py-1 text-sm border rounded hover:bg-gray-100 ${
                                p === currentPage ? 'bg-blue-600 text-white hover:bg-blue-700 border-blue-600' : ''
                              }`}
                            >
                              {p}
                            </button>
                          )
                        );
                      })()}

                      <button
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage >= totalPages}
                        className="px-2 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-40"
                      >
                        Next »
                      </button>
                      <button
                        onClick={() => handlePageChange(totalPages)}
                        disabled={currentPage >= totalPages}
                        className="px-2 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-40"
                      >
                        »»
                      </button>
                    </div>
                  </div>
                </div>
              )}

              </div>
            )}
          </div>
        </div>
      </div>
    </div>

      {/* Create/Edit Folder Modal */}
      {showCreateModal && (
        <CreateFolderModal
          appSlug={appSlug || ''}
          parentFolderPath={currentFolder?.path || currentFolderPath}
          folders={currentFolderPath ? subfolders : rootFolders}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateFolder}
        />
      )}
      {showEditModal && editingFolder && (
        <CreateFolderModal
          appSlug={appSlug || ''}
          parentFolderPath={editingFolder.parent_folder_path}
          folders={currentFolderPath ? subfolders : rootFolders}
          mode="edit"
          folderToEdit={editingFolder}
          onClose={() => { setShowEditModal(false); setEditingFolder(null); }}
          onSubmit={handleSaveEditFolder}
        />
      )}
    </>
  );
};

export default ClientAppFolders;
