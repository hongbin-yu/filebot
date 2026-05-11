import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import appService from '../services/app.service';
import folderService from '../services/folder.service';
import documentService from '../services/document.service';
import PreviewOverlay from '../components/PreviewOverlay';

// Tree folder component
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
      <div key={node.path} className="select-none">
        <div
          className={`flex items-center py-2 px-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors ${
            currentFolderId === node.path ? 'bg-blue-50 border border-blue-200' : ''
          }`}
          style={{ paddingLeft: `${level * 20 + 12}px` }}
          onClick={() => onFolderClick(node.path || node.id)}
        >
          {/* Expand/collapse icon */}
          {node.children && node.children.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand(node.path);
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
          
          {/* Placeholder (no sub-folders) */}
          {(!node.children || node.children.length === 0) && (
            <div className="mr-7 w-5"></div>
          )}
          
          {/* Folder icon */}
          <div className="mr-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
              </svg>
            </div>
          </div>
          
          {/* Folder info */}
          <div className="flex-grow min-w-0">
            <div className="font-medium text-gray-800 truncate">{node.name}</div>
            <div className="text-xs text-gray-500 truncate">
              {node.document_count !== undefined && (
                <span className="mr-2">{node.document_count} docs</span>
              )}
              {node.total_size !== undefined && node.total_size > 0 && (
                <span>{(node.total_size / 1024 / 1024).toFixed(1)} MB</span>
              )}
            </div>
          </div>
        </div>
        
        {/* Recursively render sub-folders */}
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

const ClientDocuments: React.FC = () => {
  const { appSlug, folderId } = useParams<{ appSlug: string; folderId: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<any>(null);
  const [folder, setFolder] = useState<any>(null);
  const [folderTree, setFolderTree] = useState<FolderTreeNode[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);

  // Preview overlay state
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState<string>('');

  // Build preview URL based on file type
  const buildPreviewUrl = (doc: any): string | null => {
    const identifier = doc.path || doc.storage_path || doc.id;
    if (!identifier) return null;

    const encodedId = encodeURIComponent(identifier);
    const token = localStorage.getItem('access_token');
    const fileType = doc.file_type?.toLowerCase() || '';

    // HTML files: use dedicated preview endpoint (same origin, /etc/designs etc. load properly)
    if (fileType.match(/html?/)) {
      return token
        ? `/api/v1/documents/${encodedId}/preview/html?token=${encodeURIComponent(token)}`
        : `/api/v1/documents/${encodedId}/preview/html`;
    }

    // Images (non-TIFF): prefer original URL (from crawler), fallback to preview endpoint
    if (fileType.match(/(jpe?g|png|gif|bmp|webp|svg)/)) {
      const originalUrl = doc.document_metadata?.url || doc.metadata?.url;
      if (originalUrl) {
        try {
          const urlObj = new URL(originalUrl);
          return urlObj.pathname; // same-origin path
        } catch {}
      }
      return token
        ? `/api/v1/documents/${encodedId}/preview?token=${encodeURIComponent(token)}`
        : `/api/v1/documents/${encodedId}/preview`;
    }

    // TIFF: real-time convert to PDF for browser display
    if (fileType.match(/tiff?/)) {
      return token
        ? `/api/v1/documents/${encodedId}/download?download_type=pdf&token=${encodeURIComponent(token)}`
        : `/api/v1/documents/${encodedId}/download?download_type=pdf`;
    }

    // PDF & others: use download endpoint (browsers render PDF natively)
    return token
      ? `/api/v1/documents/${encodedId}/download?token=${encodeURIComponent(token)}`
      : `/api/v1/documents/${encodedId}/download`;
  };
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  
  // File upload and filter state
  const [fileTypeFilter, setFileTypeFilter] = useState<string>('all'); // all, image, document, media, component
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  useEffect(() => {
    fetchData();
  }, [appSlug, folderId, currentPage, pageSize]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch app details
      const appData = await appService.getAppById(appSlug || '');
      if (appData) {
        setApp(appData);
        
        // Fetch folder tree
        const treeData = await folderService.getFolderTree(appData.id);
        // Initialize all nodes as expanded (optional, adjust as needed)
        const initializeTree = (nodes: any[], level: number = 0): FolderTreeNode[] => {
          return nodes.map(node => ({
            ...node,
            expanded: true, // Expand all nodes by default
            level: level,
            children: node.children ? initializeTree(node.children, level + 1) : []
          }));
        };
        setFolderTree(initializeTree(treeData, 0));
        
        // Get current folder details (supports UUID or path)
        let currentFolderData = folder;
        if (folderId) {
          // Decode potential URL encoding (especially path with slashes)
          const folderIdentifier = decodeURIComponent(folderId);
          currentFolderData = await folderService.getFolder(folderIdentifier);
          setFolder(currentFolderData);
        } else if (treeData.length > 0) {
          // If no folderId, select the first folder
          const firstFolder = findFirstFolder(treeData);
          if (firstFolder) {
            currentFolderData = firstFolder;
            setFolder(firstFolder);
            // Update URL folderId (optional), prefer path
            const folderIdentifier = getFolderIdentifier(firstFolder);
            const encodedIdentifier = encodeFolderIdentifier(folderIdentifier);
            navigate(`/apps/${appSlug}/folders/${encodedIdentifier}`, { replace: true });
            return;
          }
        }
        
        // Fetch folder documents (with pagination)
        const targetFolderIdentifier = folderId || (folder ? getFolderIdentifier(folder) : '');
        if (targetFolderIdentifier) {
          // Check folder depth - if >=3 (department level), fetch all descendant docs
          const folderNode = findFolderInTree(folderTree, currentFolderData?.path || '');
          if (folderNode && folderNode.level !== undefined && folderNode.level >= 3) {
            console.log(`📁 Folder depth ${folderNode.level} >= 3 (department level), fetching all descendant docs`);
            await fetchAllDescendantDocuments(folderNode);
          } else {
            const documentsData = await documentService.getDocuments(targetFolderIdentifier, {
              skip: (currentPage - 1) * pageSize,
              limit: pageSize,
              sort_by: 'created_at',
              sort_order: 'desc'
            });
            setDocuments(documentsData);
            
            // Get total docs for pagination (simple pagination for now)
            // Assume array length < limit means last page
            if (documentsData.length < pageSize) {
              setTotalPages(currentPage);
            } else {
              // Temporarily set to current page + 5
              setTotalPages(currentPage + 5);
            }
          }
        }
        
        setLoading(false);
      }
    } catch (err: any) {
      console.error('Failed to fetch data:', err);
      setLoading(false);
    }
  };

  // Find the first folder in tree (for default selection)
  const findFirstFolder = (nodes: any[]): any | null => {
    for (const node of nodes) {
      return node;
    }
    return null;
  };

  // Get folder identifier (prefer path, fall back to id)
  const getFolderIdentifier = (folder: any): string => {
    return folder?.path || folder?.id || '';
  };

  // Encode folder identifier for URL (encode path)
  const encodeFolderIdentifier = (identifier: string): string => {
    // If path (starts with /), URI encode it
    if (identifier.startsWith('/')) {
      return encodeURIComponent(identifier);
    }
    return identifier;
  };

  // Recursively find folder node
  const findFolderInTree = (nodes: FolderTreeNode[], folderId: string): FolderTreeNode | null => {
    for (const node of nodes) {
      if (node.path === folderId) {
        return node;
      }
      if (node.children) {
        const found = findFolderInTree(node.children, folderId);
        if (found) return found;
      }
    }
    return null;
  };

  // Recursively get all descendant folder identifiers (path preferred)
  const getAllDescendantFolderIdentifiers = (node: FolderTreeNode): string[] => {
    const identifiers: string[] = [];
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        // Use path-first identifier
        const childIdentifier = getFolderIdentifier(child);
        identifiers.push(childIdentifier);
        identifiers.push(...getAllDescendantFolderIdentifiers(child));
      }
    }
    return identifiers;
  };

  // Fetch docs for folder and all descendants
  const fetchAllDescendantDocuments = async (folderNode: FolderTreeNode) => {
    try {
      // Get current folder and all descendant identifiers
      const currentFolderIdentifier = getFolderIdentifier(folderNode);
      const folderIdentifiers = [currentFolderIdentifier, ...getAllDescendantFolderIdentifiers(folderNode)];
      console.log(`📁 Fetching docs for ${folderIdentifiers.length} folders (depth ${folderNode.level})`);
      
      // Fetch docs for each folder
      const allDocuments: any[] = [];
      for (const folderId of folderIdentifiers) {
        try {
          const documents = await documentService.getDocuments(folderId, {
            skip: (currentPage - 1) * pageSize,
            limit: pageSize,
            sort_by: 'created_at',
            sort_order: 'desc'
          });
          allDocuments.push(...documents);
        } catch (err) {
          console.error(`Failed to fetch docs for folder ${folderId}:`, err);
        }
      }
      
      // Deduplicate by ID
      const uniqueDocuments = allDocuments.filter((doc, index, self) => 
        index === self.findIndex(d => d.path === doc.path)
      );
      
      console.log(`✅ Got ${uniqueDocuments.length} unique docs total`);
      setDocuments(uniqueDocuments);
      
      // Update pagination info
      setTotalPages(1);
      setCurrentPage(1);
    } catch (err: any) {
      console.error('Failed to fetch descendant docs:', err);
      setDocuments([]);
    }
  };

  // Toggle tree node expand state
  const updateTreeExpansion = (nodes: FolderTreeNode[], folderPath: string): FolderTreeNode[] => {
    return nodes.map(node => {
      if (node.path === folderPath) {
        return { ...node, expanded: !node.expanded };
      }
      if (node.children) {
        return { ...node, children: updateTreeExpansion(node.children, folderPath) };
      }
      return node;
    });
  };

  // Handle folder click
  const handleFolderClick = (folderIdentifier: string) => {
    const encodedIdentifier = encodeFolderIdentifier(folderIdentifier);
    navigate(`/apps/${appSlug}/folders/${encodedIdentifier}`);
  };

  // Handle tree node expand/collapse
  const handleToggleExpand = (folderId: string) => {
    setFolderTree(prevTree => updateTreeExpansion(prevTree, folderId));
  };

  // Handle page change
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Handle page size change
  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1); // Reset to page 1
  };

  // Handle document download
  const handleDownload = async (documentId: string, filename: string) => {
    try {
      console.log('Starting document download:', documentId, filename);
      const blob = await documentService.downloadDocument(documentId);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = filename;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
      console.log('Document download complete:', filename);
    } catch (err: any) {
      console.error('Download failed:', err);
      window.showWetAlert(`Download failed: ${err.message || 'Unknown error'}`);
    }
  };

  // Handle document preview (using lightbox overlay)
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

  // Handle file upload
  const handleFileUpload = async (files: FileList) => {
    if (!folderId && !folder?.path) {
      window.showWetAlert('Please select a folder first');
      return;
    }

    // Get folder identifier (path preferred)
    const targetFolderIdentifier = folderId || (folder ? getFolderIdentifier(folder) : '');
    if (!targetFolderIdentifier) {
      window.showWetAlert('Could not determine target folder');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    const uploadPromises = Array.from(files).map(async (file, index) => {
      try {
        // Build upload request, prefer folder_path
        const uploadRequest: any = {
          file,
          title: file.name.replace(/\.[^/.]+$/, ''), // Remove extension for title
          description: `Uploaded on ${new Date().toLocaleDateString()}`
        };
        
        // Path preferred: use folder_path if path, else folder_id (backward compat)
        if (targetFolderIdentifier.startsWith('/')) {
          uploadRequest.folder_path = targetFolderIdentifier;
          console.log('🔍 [DEBUG] ClientDocuments upload: using folder_path:', targetFolderIdentifier);
        } else {
          uploadRequest.folder_id = targetFolderIdentifier;
          console.warn('⚠️ ClientDocuments upload: using deprecated folder_id:', targetFolderIdentifier);
        }

        // Simulate upload progress (API may not support progress events)
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            const newProgress = prev + (10 / files.length);
            return newProgress > 90 ? 90 : newProgress;
          });
        }, 200);

        const document = await documentService.uploadDocument(uploadRequest);
        
        clearInterval(progressInterval);
        setUploadProgress(prev => prev + (10 / files.length)); // One more file done

        return document;
      } catch (error) {
        console.error(`File upload failed ${file.name}:`, error);
        return null;
      }
    });

    try {
      const results = await Promise.all(uploadPromises);
      setUploadProgress(100);
      
      // Wait 1 second showing completion status
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Refresh documents
      fetchData();
      
      const successCount = results.filter(r => r !== null).length;
      window.showWetAlert(`Upload complete! Success: ${successCount}, Failed: ${files.length - successCount}`);
    } catch (error) {
      console.error('Error during upload:', error);
      window.showWetAlert('Error during upload');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // Handle drag-and-drop events
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  // Handle file picker
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files);
      // Reset input to allow re-selecting same file
      e.target.value = '';
    }
  };

  // Filter documents function
  const filterDocuments = (docs: any[]) => {
    let filtered = [...docs];
    
    // Apply file type filter
    if (fileTypeFilter !== 'all') {
      filtered = filtered.filter(doc => {
        const fileType = doc.file_type?.toLowerCase() || '';
        
        switch (fileTypeFilter) {
          case 'image':
            return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'svg'].includes(fileType);
          case 'document':
            return ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'html', 'htm'].includes(fileType);
          case 'media':
            return ['mp4', 'avi', 'mov', 'wmv', 'mp3', 'wav', 'ogg'].includes(fileType);
          case 'component':
            // Component type may be based on metadata or other fields
            return doc.file_type === 'html' || doc.file_type === 'htm' || 
                   (doc.document_metadata && doc.document_metadata.component_type);
          default:
            return true;
        }
      });
    }
    
    return filtered;
  };

  // Handle file type filter change
  const handleFileTypeFilterChange = (type: string) => {
    setFileTypeFilter(type);
    // Note: we only set filter state, actual filtering is in getDisplayDocuments
  };

  // Handle path display - get from folder path or doc path
  const getCurrentPath = () => {
    return folder?.path || folder?.name || 'No folder selected';
  };

  // Get displayed docs (apply search and filter)
  const getDisplayDocuments = () => {
    const docsToDisplay = searchResults !== null ? searchResults : documents;
    return filterDocuments(docsToDisplay);
  };

  // Handle search
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!searchQuery.trim()) {
      // If search query is empty, clear results
      setSearchResults(null);
      return;
    }
    
    if (!folderId) {
      window.showWetAlert('Missing folder ID, cannot search');
      return;
    }
    
    setIsSearching(true);
    
    try {
      const results = await documentService.searchDocuments({
        q: searchQuery.trim(),
        folder_id: folderId
      });
      setSearchResults(results);
    } catch (error) {
      console.error('Search failed:', error);
      window.showWetAlert('Search failed, please try again');
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

  // Check if showing search results
  const isShowingSearchResults = () => {
    return searchResults !== null && searchQuery.trim() !== '';
  };

  return (
    <>
      <PreviewOverlay url={previewUrl} title={previewTitle} onClose={handleClosePreview} />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header breadcrumb navigation */}
        <header className="mb-8">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-4">
            <Link to="/apps" className="hover:text-blue-600">Apps</Link>
            <span>›</span>
            <Link to={`/apps/${appSlug}`} className="hover:text-blue-600">{app?.name || 'App'}</Link>
            {folder?.path && (() => {
              const segments = folder.path.split('/').filter(Boolean);
              let accumulatedPath = '';
              return segments.map((segment: string, index: number) => {
                accumulatedPath += '/' + segment;
                const isLast = index === segments.length - 1;
                return (
                  <React.Fragment key={segment}>
                    <span>›</span>
                    {isLast ? (
                      <span className="text-gray-700 font-medium">{folder?.name || segment}</span>
                    ) : (
                      <Link to={`/apps/${appSlug}/folders/${encodeURIComponent(accumulatedPath)}`} className="hover:text-blue-600">{segment}</Link>
                    )}
                  </React.Fragment>
                );
              });
            })()}
            {!folder?.path && folder?.name && (
              <>
                <span>›</span>
                <span className="text-gray-700 font-medium">{folder.name}</span>
              </>
            )}
          </div>
          
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{folder?.name || 'Browse Folders'}</h1>
              <p className="text-gray-600 mt-2">
                {app?.name} • {folder?.description || 'Browse folder contents'}
                {folder?.document_count !== undefined && (
                  <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded">
                    {folder.document_count} docs
                  </span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <Link 
                to={`/apps/${appSlug}`}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Back to App Home
              </Link>
            </div>
          </div>
        </header>

        {/* Main content - two column layout */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading folder contents...</p>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left folder tree - 1/3 */}
            <div className="lg:w-[30%]">
              <div className="bg-white rounded-xl shadow overflow-hidden">
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                  <h2 className="text-xl font-bold text-gray-800">Folder Tree</h2>
                  <p className="text-gray-600 text-sm mt-1">Full folder hierarchy with expand/collapse support</p>
                </div>
                
                {folderTree.length === 0 ? (
                  <div className="p-8 text-center">
                    <div className="text-gray-400 mb-4">
                      <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Folders</h3>
                    <p className="text-gray-500">This app has no folders.</p>
                  </div>
                ) : (
                  <div className="p-4 max-h-[600px] overflow-y-auto">
                    <FolderTree 
                      folders={folderTree}
                      currentFolderId={folderId ? decodeURIComponent(folderId) : (folder ? getFolderIdentifier(folder) : undefined)}
                      onFolderClick={handleFolderClick}
                      onToggleExpand={handleToggleExpand}
                    />
                  </div>
                )}
                
                {/* Current folder info */}
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  <h4 className="font-medium text-gray-700 text-sm mb-2">Current Folder</h4>
                  <div className="space-y-1 text-xs text-gray-600">
                    <div className="flex justify-between">
                      <span>Path:</span>
                      <span className="font-mono truncate max-w-[200px]" title={folder?.path}>{folder?.path || '/'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Docs:</span>
                      <span>{documents.length} </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Created:</span>
                      <span>{folder?.created_at ? new Date(folder.created_at).toLocaleDateString() : 'Unknown'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right docs panel - 2/3 */}
            <div className="lg:w-[70%]">
              <div className="bg-white rounded-xl shadow overflow-hidden">
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100">
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h2 className="text-xl font-bold text-gray-800">Documents</h2>
                        <p className="text-gray-600 text-sm mt-1">
                          Showing latest 100 docs
                          {isShowingSearchResults() && (
                            <span className="ml-2 text-blue-600 font-medium">
                              (Search results)
                            </span>
                          )}
                        </p>
                      </div>
                    </div>

                    {/* File actions toolbar */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Left: drag-and-drop zone */}
                        <div 
                          className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                            dragActive 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'border-gray-300 hover:border-blue-400 hover:bg-blue-25'
                          }`}
                          onDragEnter={handleDragEnter}
                          onDragLeave={handleDragLeave}
                          onDragOver={handleDragOver}
                          onDrop={handleDrop}
                        >
                          <div className="flex flex-col items-center justify-center h-full">
                            <div className="text-3xl mb-2">📁</div>
                            <p className="font-medium text-gray-700">Drag & drop files here to upload</p>
                            <p className="text-sm text-gray-500 mt-1">Supports images, documents, media files</p>
                            
                            <div className="mt-4">
                              <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer">
                                <span>Select Files</span>
                                <input 
                                  type="file" 
                                  multiple 
                                  className="hidden" 
                                  onChange={handleFileSelect}
                                  accept="image/*,.pdf,.doc,.docx,.txt,.mp4,.avi,.mov,.mp3,.html,.htm"
                                />
                              </label>
                            </div>
                            
                            {uploading && (
                              <div className="mt-4 w-full">
                                <div className="flex justify-between text-sm text-gray-600 mb-1">
                                  <span>Uploading...</span>
                                  <span>{Math.round(uploadProgress)}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${uploadProgress}%` }}
                                  ></div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Middle: path and type filter */}
                        <div className="space-y-4">
                          {/* Path display */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Current Path
                            </label>
                            <div className="flex items-center bg-white border border-gray-300 rounded-lg px-3 py-2">
                              <span className="text-gray-400 mr-2">📍</span>
                              <span className="text-gray-800 font-mono text-sm truncate" title={getCurrentPath()}>
                                {getCurrentPath()}
                              </span>
                            </div>
                          </div>

                          {/* File type filter */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              File Type Filter
                            </label>
                            <div className="flex flex-wrap gap-2">
                              {[
                                { id: 'all', label: 'All', icon: '📄' },
                                { id: 'image', label: 'Images', icon: '🖼️' },
                                { id: 'document', label: 'Documents', icon: '📝' },
                                { id: 'media', label: 'Media', icon: '🎬' },
                                { id: 'component', label: 'Components', icon: '🧩' }
                              ].map(type => (
                                <button
                                  key={type.id}
                                  type="button"
                                  onClick={() => handleFileTypeFilterChange(type.id)}
                                  className={`flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                    fileTypeFilter === type.id
                                      ? 'bg-blue-600 text-white'
                                      : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                                  }`}
                                >
                                  <span className="mr-1.5">{type.icon}</span>
                                  {type.label}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* Right: stats */}
                        <div className="bg-white border border-gray-200 rounded-lg p-4">
                          <h4 className="font-medium text-gray-700 text-sm mb-3">📊 Folder Stats</h4>
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Total Docs:</span>
                              <span className="font-medium">{documents.length}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Showing:</span>
                              <span className="font-medium">{getDisplayDocuments().length}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Folder Size:</span>
                              <span className="font-medium">
                                {(documents.reduce((sum, doc) => sum + doc.file_size, 0) / 1024 / 1024).toFixed(2)} MB
                              </span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Filter:</span>
                              <span className="font-medium">
                                {fileTypeFilter === 'all' ? 'All Types' : 
                                 fileTypeFilter === 'image' ? 'Images' :
                                 fileTypeFilter === 'document' ? 'Documents' :
                                 fileTypeFilter === 'media' ? 'Media' : 'Components'}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Search bar */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="text-sm text-gray-600">
                        Quick Search
                      </div>
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
                              Search
                            </>
                          ) : 'Search'}
                        </button>
                      </form>
                    </div>
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
                      <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
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
                          <tr key={doc.path || doc.storage_path || doc.name} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div>
                                <div className="font-medium text-gray-900">{doc.title}</div>
                                <div className="text-sm text-gray-500 truncate max-w-xs">{doc.original_filename}</div>
                                {doc.path && <div className="text-xs text-gray-400 truncate max-w-xs mt-0.5" title={doc.path}>{doc.path}</div>}
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
                                  Download
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
                        <div>
                          Total size: <span className="font-medium">
                            {(getDisplayDocuments().reduce((sum, doc) => sum + doc.file_size, 0) / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Current folder stats */}
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
                      <h4 className="text-sm font-medium text-gray-700">Total Docs</h4>
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
                      <h4 className="text-sm font-medium text-gray-700">PDF Docs</h4>
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
                      <h4 className="text-sm font-medium text-gray-700">Total Size</h4>
                      <p className="text-2xl font-bold text-gray-900">
                        {(documents.reduce((sum, doc) => sum + doc.file_size, 0) / 1024 / 1024).toFixed(1)} MB
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>FileBot Client Portal • {app?.name || 'App'} • {folder?.name || 'Folder'}</p>
          <p className="mt-1">Showing latest 100 docs • Left: full folder tree</p>
        </footer>
      </div>
    </div>
    </>
  );
};

export default ClientDocuments;