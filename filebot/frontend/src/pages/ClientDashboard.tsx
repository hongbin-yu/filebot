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
  // Cache all folders locally so we can filter by path client-side
  const [allFolders, setAllFolders] = useState<Folder[]>([]);

  useEffect(() => {
    fetchData();
  }, [appSlug]);

  // Fetch root folders: get immediate children of /{appSlug}
  const fetchRootFolders = async () => {
    try {
      const rootPath = '/' + appSlug;
      console.log('📁 fetchRootFolders: sending parent_folder_path=', rootPath);
      const folders = await folderService.getFolders(appSlug || '', {
        parent_folder_path: rootPath,
        limit: 1000
      });
      console.log('📁 fetchRootFolders: got', folders?.length, 'folders');
      setAllFolders(folders || []);
      setChildFolders(folders || []);
    } catch (err) {
      console.error('📁 Failed to fetch root folders:', err);
      setChildFolders([]);
    }
  };

  // Fetch child folders by parent path: call backend with parent_folder_path
  const fetchChildFolders = async (parentFolderPath: string) => {
    try {
      const children = await folderService.getFolders(appSlug || '', {
        parent_folder_path: parentFolderPath,
        limit: 1000
      });
      // Accumulate in cache
      setAllFolders(prev => {
        const existing = new Map(prev.map(f => [f.path, f]));
        (children || []).forEach(f => existing.set(f.path, f));
        return Array.from(existing.values());
      });
      setChildFolders(children || []);
    } catch (err) {
      console.error('Failed to fetch child folders:', err);
      setChildFolders([]);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch app details
      const appData = await appService.getAppById(appSlug || '');
      if (appData) {
        setApp(appData);
        
        // Fetch/refresh all folders and filter root level
        await fetchRootFolders();
        setLoading(false);
      }
    } catch (err: any) {
      console.error('Failed to fetch data:', err);
      setLoading(false);
    }
  };

  // Fetch folder documents by path
  // Accepts optional page/size to avoid stale closure values after setState
  const fetchFolderDocuments = async (folderPath: string, overridePage?: number, overrideSize?: number) => {
    const p = overridePage ?? currentPage;
    const s = overrideSize ?? pageSize;
    try {
      // Always use recursive query to show all descendant documents
      let documentsData = await documentService.getDocumentsByFolderPath(folderPath, {
        skip: (p - 1) * s,
        limit: s,
        sort_by: 'created_at',
        sort_order: 'desc'
      });
      
      setDocuments(documentsData);
      
      // Simple pagination logic
      if (documentsData.length < s) {
        setTotalPages(p);
      } else {
        setTotalPages(p + 5);
      }
    } catch (err: any) {
      console.error('Failed to fetch docs:', err);
      setDocuments([]);
    }
  };

  // Navigate into a folder — navigates to the URL-based view (ClientAppFolders)
  const handleFolderClick = async (folder: Folder) => {
    // Navigate to the URL for this folder (e.g., /apps/boarding/canadasite)
    // folder.path format: /boarding/canadasite
    navigate(`/apps${folder.path}`);
  };

  // Navigate to a specific breadcrumb ancestor folder
  const navigateToBreadcrumb = async (targetPath: string) => {
    // Try to find in cache first
    let target = allFolders.find((f: Folder) => f.path === targetPath);
    if (!target) {
      try {
        target = await folderService.getFolder(targetPath);
        if (target) {
          setAllFolders(prev => {
            const existing = new Map(prev.map(f => [f.path, f]));
            existing.set(target.path, target);
            return Array.from(existing.values());
          });
        }
      } catch {
        // Intermediate path — no folder record
      }
    }
    if (target) {
      setCurrentFolder(target);
      setCurrentPage(1);
      await fetchChildFolders(targetPath);
      await fetchFolderDocuments(targetPath);
    } else {
      // Root level (app root, no folder record) — just show subfolders, no documents
      setCurrentFolder(null);
      setDocuments([]);
      setCurrentPage(1);
      await fetchChildFolders(targetPath);
    }
  };

  // Navigate back to parent folder using parent_folder_path
  const backToParent = async () => {
    if (!currentFolder) return;
    
    const parentPath = currentFolder.parent_folder_path;
    if (parentPath) {
      // Try to find parent folder in cache; if not, fetch from API
      let parent = allFolders.find((f: Folder) => f.path === parentPath);
      if (!parent) {
        try {
          parent = await folderService.getFolder(parentPath);
          if (parent) {
            setAllFolders(prev => {
              const existing = new Map(prev.map(f => [f.path, f]));
              existing.set(parent.path, parent);
              return Array.from(existing.values());
            });
          }
        } catch {
          // No folder record — intermediate path
        }
      }
      
      if (parent) {
        // Parent folder exists as a record
        setCurrentFolder(parent);
        await fetchChildFolders(parentPath);
        await fetchFolderDocuments(parentPath);
        return;
      } else {
        // Intermediate path (no folder record, e.g. /boarding/canadasite/fr)
        // Navigate to the parent path — show documents at this path
        setCurrentFolder(null);
        await fetchChildFolders(parentPath);
        await fetchFolderDocuments(parentPath);
        return;
      }
    }
    
    // Go back to root
    setCurrentFolder(null);
    await fetchRootFolders();
    setDocuments([]);
  };

  // Handle page change — pass page override to avoid stale closure
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    if (currentFolder) {
      fetchFolderDocuments(currentFolder.path || '', page, pageSize);
    }
  };

  // Handle page size change — pass size override
  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
    if (currentFolder) {
      fetchFolderDocuments(currentFolder.path || '', 1, size);
    }
  };

  // Handle document download
  const handleDownload = async (documentId: string, filename: string) => {
    try {
      console.log('Starting download:', documentId, filename);
      const blob = await documentService.downloadDocument(documentId);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = filename;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
      console.log('Download complete:', filename);
    } catch (err: any) {
      console.error('Download failed:', err);
      if (typeof window.showWetAlert === 'function') {
        window.showWetAlert(`Download failed: ${err.message || 'Unknown error'}`);
      }
    }
  };

  // Preview overlay state
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState<string>('');

  // Build preview URL based on file type (matches ClientDocuments logic)
  const buildPreviewUrl = (doc: any): string | null => {
    const identifier = doc.path || doc.storage_path || doc.id;
    if (!identifier) return null;

    const encodedId = encodeURIComponent(identifier);
    const token = localStorage.getItem('access_token');
    const fileType = doc.file_type?.toLowerCase() || '';

    // HTML files: use dedicated preview endpoint
    if (fileType.match(/html?/)) {
      return token
        ? `/api/v1/documents/${encodedId}/preview/html?token=${encodeURIComponent(token)}`
        : `/api/v1/documents/${encodedId}/preview/html`;
    }

    // Images (non-TIFF): prefer original URL from crawler, fallback to preview
    if (fileType.match(/(jpe?g|png|gif|bmp|webp|svg)/)) {
      const originalUrl = doc.document_metadata?.url || doc.metadata?.url;
      if (originalUrl) {
        try {
          const urlObj = new URL(originalUrl);
          return urlObj.pathname;
        } catch {}
      }
      return token
        ? `/api/v1/documents/${encodedId}/preview?token=${encodeURIComponent(token)}`
        : `/api/v1/documents/${encodedId}/preview`;
    }

    // TIFF: convert to PDF for browser display
    if (fileType.match(/tiff?/)) {
      return token
        ? `/api/v1/documents/${encodedId}/download?download_type=pdf&token=${encodeURIComponent(token)}`
        : `/api/v1/documents/${encodedId}/download?download_type=pdf`;
    }

    // PDF & others: download endpoint (browsers render PDF natively)
    return token
      ? `/api/v1/documents/${encodedId}/download?token=${encodeURIComponent(token)}`
      : `/api/v1/documents/${encodedId}/download`;
  };

  // Handle document preview (lightbox overlay)
  const handlePreview = (doc: any) => {
    const url = buildPreviewUrl(doc);
    if (url) {
      setPreviewUrl(url);
      setPreviewTitle(doc.title || doc.original_filename || 'Document Preview');
    }
  };

  // Close preview overlay
  const handleClosePreview = () => {
    setPreviewUrl(null);
    setPreviewTitle('');
  };

  // Handle search (uses path, not folder_id)
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    
    if (!currentFolder) {
      if (typeof window.showWetAlert === 'function') {
        window.showWetAlert('Please select a folder');
      }
      return;
    }
    
    setIsSearching(true);
    
    try {
      const results = await documentService.searchDocuments({
        q: searchQuery.trim(),
        path: currentFolder.path
      });
      setSearchResults(results);
    } catch (error) {
      console.error('Search failed:', error);
      if (typeof window.showWetAlert === 'function') {
        window.showWetAlert('Search failed, please try again');
      }
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  // Get currently displayed docs (search results or all)
  const getDisplayDocuments = () => {
    return searchResults !== null ? searchResults : documents;
  };

  // Check if showing search results
  const isShowingSearchResults = () => {
    return searchResults !== null && searchQuery.trim() !== '';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header breadcrumb navigation */}
        <header className="mb-8">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-4">
            <Link to="/apps" className="hover:text-blue-600">Apps</Link>
            <span>›</span>
            <Link to={`/apps/${appSlug}`} className="hover:text-blue-600">{app?.name || 'App'}</Link>
            {currentFolder?.path && (() => {
              // Skip the first segment (app slug) since app name is already shown
              const segments = currentFolder.path.split('/').filter(Boolean).slice(1);
              if (segments.length === 0) return null;
              let accumulatedPath = '/' + appSlug;
              return segments.map((segment, index) => {
                accumulatedPath += '/' + segment;
                const isLast = index === segments.length - 1;
                return (
                  <React.Fragment key={segment}>
                    <span>›</span>
                    {isLast ? (
                      <span className="text-gray-700 font-medium">{currentFolder?.name || segment}</span>
                    ) : (
                      <button
                        onClick={() => navigateToBreadcrumb(accumulatedPath)}
                        className="hover:text-blue-600 cursor-pointer bg-transparent border-none p-0 text-sm"
                      >
                        {segment}
                      </button>
                    )}
                  </React.Fragment>
                );
              });
            })()}
            {!currentFolder?.path && currentFolder?.name && (
              <>
                <span>›</span>
                <span className="text-gray-700 font-medium">{currentFolder.name}</span>
              </>
            )}
          </div>
          
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{app?.name || 'App Details'}</h1>
              <p className="text-gray-600 mt-2">
                {app?.description || 'Public Document Portal'}
                {currentFolder && (
                  <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded">
                    {documents.length} docs
                  </span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <Link 
                to="/apps"
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Back to Apps
              </Link>
            </div>
          </div>
        </header>

        {/* Main content - two column layout */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading app...</p>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left sidebar - flat folder list (30%) */}
            <div className="lg:w-[30%]">
              <div className="bg-white rounded-xl shadow overflow-hidden">
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                  <h2 className="text-xl font-bold text-gray-800">
                    {currentFolder ? currentFolder.name : 'Folders'}
                  </h2>
                  <p className="text-gray-600 text-sm mt-1">
                    {currentFolder ? 'Sub-folders' : 'Root folders'}
                  </p>
                </div>
                
                {/* Back to parent button */}
                {currentFolder && (
                  <div className="px-4 pt-3">
                    <button
                      onClick={backToParent}
                      className="flex items-center w-full px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                      </svg>
                      .. / {currentFolder.parent_folder_path ? 'Parent folder' : 'Root'}
                    </button>
                    <hr className="my-2 border-gray-200" />
                  </div>
                )}
                
                {childFolders.length === 0 ? (
                  <div className="p-8 text-center">
                    <div className="text-gray-400 mb-4">
                      <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Sub-folders</h3>
                    <p className="text-gray-500">This folder has no sub-folders.</p>
                  </div>
                ) : (
                  <div className="p-4 max-h-[600px] overflow-y-auto">
                    <div className="space-y-1">
                      {childFolders.map(folder => (
                        <div key={folder.path}>
                          <div
                            className={`flex items-center py-2 px-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors ${
                              currentFolder?.path === folder.path ? 'bg-blue-50 border border-blue-200' : ''
                            }`}
                            onClick={() => handleFolderClick(folder)}
                          >
                            {/* Folder icon */}
                            <div className="mr-3">
                              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                </svg>
                              </div>
                            </div>
                            
                            {/* Folder info */}
                            <div className="flex-grow min-w-0">
                              <div className="font-medium text-gray-800 truncate">{folder.name}</div>
                              <div className="text-xs text-gray-500 truncate">
                                {folder.document_count !== undefined && (
                                  <span className="mr-2">{folder.document_count} docs</span>
                                )}
                                {folder.total_size !== undefined && folder.total_size > 0 && (
                                  <span>{(folder.total_size / 1024 / 1024).toFixed(1)} MB</span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Current folder info */}
                {currentFolder && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50">
                    <h4 className="font-medium text-gray-700 text-sm mb-2">Current Folder</h4>
                    <div className="space-y-1 text-xs text-gray-600">
                      <div className="flex justify-between">
                        <span>Path:</span>
                        <span className="font-mono truncate max-w-[200px]" title={currentFolder?.path}>{currentFolder?.path || '/'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Docs:</span>
                        <span>{documents.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Created:</span>
                        <span>{currentFolder?.created_at ? new Date(currentFolder.created_at).toLocaleDateString() : 'Unknown'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right side - document table (70%) */}
            <div className="lg:w-[70%]">
              {currentFolder ? (
                <div className="bg-white rounded-xl shadow overflow-hidden">
                  <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h2 className="text-xl font-bold text-gray-800">Documents</h2>
                        <p className="text-gray-600 text-sm mt-1">
                          Folder: <span className="font-medium">{currentFolder.name}</span>
                          {isShowingSearchResults() && (
                            <span className="ml-2 text-blue-600 font-medium">
                              (Search results)
                            </span>
                          )}
                        </p>
                      </div>
                      
                      {/* Search bar */}
                      <form onSubmit={handleSearch} className="flex items-center">
                        <div className="relative">
                          <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search document titles..."
                            className="w-full sm:w-64 px-4 py-2 pl-10 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                          <div className="absolute left-3 top-2.5 text-gray-400">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                          </div>
                          {searchQuery && (
                            <button
                              type="button"
                              onClick={handleClearSearch}
                              className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
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
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                              Search
                            </>
                          ) : 'Search'}
                        </button>
                      </form>
                    </div>
                    
                    {isShowingSearchResults() && (
                      <div className="mt-3 flex items-center justify-between bg-blue-50 p-3 rounded-lg">
                        <div className="text-sm text-blue-700">
                          <span className="font-medium">{searchResults?.length || 0}</span> search results, keyword: "<span className="font-medium">{searchQuery}</span>"
                        </div>
                        <button
                          type="button"
                          onClick={handleClearSearch}
                          className="text-sm text-blue-600 hover:text-blue-800 underline"
                        >
                          Clear search
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {getDisplayDocuments().length === 0 ? (
                    <div className="p-12 text-center">
                      <div className="text-gray-400 mb-6">
                        <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <h3 className="text-xl font-medium text-gray-900 mb-2">
                        {isShowingSearchResults() ? 'No search results found' : 'No documents'}
                      </h3>
                      <p className="text-gray-500 mb-6">
                        {isShowingSearchResults() 
                          ? `No documents found matching "${searchQuery}". Try other keywords.`
                          : 'This folder has no documents yet.'}
                      </p>
                      {isShowingSearchResults() && (
                        <button
                          onClick={handleClearSearch}
                          className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                        >
                          Clear search
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Name
                            </th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Type
                            </th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Size
                            </th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Pages
                            </th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Upload Date
                            </th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Actions
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {getDisplayDocuments().map(doc => (
                            <tr key={doc.path || doc.storage_path} className="hover:bg-gray-50">
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
                                    onClick={() => handleDownload(doc.path || doc.storage_path, doc.original_filename)}
                                    className="text-blue-600 hover:text-blue-900 px-3 py-1 bg-blue-50 hover:bg-blue-100 rounded text-sm"
                                  >
                                    Download
                                  </button>
                                  <button 
                                    onClick={() => handlePreview(doc)}
                                    className="text-gray-600 hover:text-gray-900 px-3 py-1 bg-gray-50 hover:bg-gray-100 rounded text-sm"
                                  >
                                    Preview
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      
                      {/* Table footer info */}
                      <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
                        <div className="flex items-center justify-between text-sm text-gray-500">
                          <div>
                            Showing <span className="font-medium">{getDisplayDocuments().length}</span> docs
                            {isShowingSearchResults() && (
                              <span className="ml-2 text-blue-600">
                                (Search results)
                              </span>
                            )}
                          </div>
                          <div className="flex items-center space-x-2">
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
                        </div>
                      </div>
                      
                      {/* Pagination */}
                      {!isShowingSearchResults() && totalPages > 1 && (
                        <div className="bg-white px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                          <div className="text-sm text-gray-500">
                            Page {currentPage} of {totalPages}
                          </div>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handlePageChange(currentPage - 1)}
                              disabled={currentPage <= 1}
                              className="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Previous
                            </button>
                            <button
                              onClick={() => handlePageChange(currentPage + 1)}
                              disabled={currentPage >= totalPages}
                              className="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Next
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-white rounded-xl shadow p-12 text-center">
                  <div className="text-gray-400 mb-6">
                    <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-medium text-gray-900 mb-2">Select a Folder</h3>
                  <p className="text-gray-500 mb-6">Choose a folder from the left sidebar to view its documents.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>FileBot Client Portal • {app?.name || 'App'} • {currentFolder?.name || 'Select a Folder'}</p>
          <p className="mt-1">30/70 two-column layout • Left: flat folder list • Right: document table</p>
        </footer>
        {/* Preview Overlay (lightbox) */}
        <PreviewOverlay url={previewUrl} onClose={handleClosePreview} />
      </div>
    </div>
  );
};

export default ClientDashboard;
