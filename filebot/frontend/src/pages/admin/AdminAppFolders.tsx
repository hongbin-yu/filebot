import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import appService, { App } from '../../services/app.service';
import folderService, { Folder, FolderCreateRequest } from '../../services/folder.service';
import documentService, { Document } from '../../services/document.service';
import { showToast } from '../../components/common/ToastNotification';
import aiService, { WebsiteCrawlRequest, SitemapImportRequest, SitemapImportResponse } from '../../services/ai.service';

import CreateFolderModal from '../../components/folders/CreateFolderModal';
import { ChevronRightIcon, ChevronDownIcon, FolderIcon, DocumentIcon } from '@heroicons/react/24/outline';

const AdminAppFolders: React.FC = () => {
  const { appSlug } = useParams<{ appSlug: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const search = location.search;
  
  // State
  const [app, setApp] = useState<App | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]); // 顶层文件夹（sidebar）
  const [allFolders, setAllFolders] = useState<Folder[]>([]); // 全部文件夹（dropdown）
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentFolderPath, _setCurrentFolderPath] = useState<string | null>(null);
  const [forwardStack, setForwardStack] = useState<string[]>([]);
  const setCurrentFolderPath = useCallback((newPath: string | null) => {
    console.log('🟢 setCurrentFolderPath:', newPath);
    _setCurrentFolderPath(newPath);
  }, []);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showImportWebsiteModal, setShowImportWebsiteModal] = useState(false);
  const [parentFolderPath, setParentFolderPath] = useState<string | null>(null);
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  
  // Website import form
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [crawlDepth, setCrawlDepth] = useState(1);
  const [importingWebsite, setImportingWebsite] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  
  // Folder search
  const [folderSearch, setFolderSearch] = useState('');
  
  // Sitemap import state
  const [sitemapUrl, setSitemapUrl] = useState('');
  const [sitemapDepth, setSitemapDepth] = useState(0);
  const [importingSitemap, setImportingSitemap] = useState(false);
  const [importTab, setImportTab] = useState<'website' | 'sitemap'>('website');
  
  // Current folder details
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [subfolders, setSubfolders] = useState<Folder[]>([]);
  
  // Document state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  
  // Load app info
  useEffect(() => {
    const loadAppInfo = async () => {
      if (!appSlug) return;
      
      try {
        setError(null);
        const appData = await appService.getAppById(appSlug);
        setApp(appData);
        
        // Load all folders
        if (appData) {
          await loadFolders(appSlug || appData.id, appData.id);
        }
      } catch (error: any) {
        console.error('Failed to load app info:', error);
        
        // Check error type
        if (error.response?.status === 403) {
          setError('No permission to access this app. It may belong to another user.');
        } else if (error.response?.status === 404) {
          setError('App not found. It may have been deleted or the URL may be incorrect.');
        } else {
          setError('Failed to load app info. Please try again later.');
        }
      } finally {
        setLoading(false);
      }
    };
    
    loadAppInfo();
  }, [appSlug]);
  
  // Load folders
  // Load top-level folders for sidebar
  const loadFolders = async (appIdentifier: string, appId?: string) => {
    try {
      const allFolderData = await folderService.getFolders(appIdentifier, {
        app_slug: appIdentifier,
        path_starts_with: '/' + appIdentifier,
        limit: 5000
      });
      // Sort by path depth: top-level folders first for the sidebar
      const topLevel = allFolderData.filter(f => f.parent_folder_path === '/' + appIdentifier);
      setFolders(topLevel);
      setAllFolders(allFolderData);
      
      // URL → state sync is handled by the [search] useEffect below.
      // Do NOT read folder from URL here — it captures stale `search` in closures,
      // which causes handleDeleteFolder to re-set currentFolderPath to the deleted folder.
    } catch (error) {
      console.error('Failed to load folders:', error);
    }
  };
  
  // Load folder details and subfolders when current folder changes
  useEffect(() => {
    const loadCurrentFolderDetails = async () => {
      if (!currentFolderPath) {
        console.log('📂 loadCurrentFolderDetails: no path, loading root documents');
        setCurrentFolder(null);
        setSubfolders([]);
        // Load root-level documents
        const rootPath = '/' + appSlug;
        try {
          const docs = await documentService.getDocumentsByFolderPath(rootPath, { limit: 1000 });
          docs.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
          setDocuments(docs);
        } catch (err) {
          console.error('Failed to load root documents:', err);
          setDocuments([]);
        }
        return;
      }
      
      console.log('📂 loadCurrentFolderDetails: starting', { currentFolderPath, appId: app?.id, appSlug });
      
      try {
        // Load folder details using path
        let folderDetails: Folder | null = null;
        try {
          folderDetails = await folderService.getFolder(currentFolderPath);
        } catch (err: any) {
          // getFolder可能因路径在DB中不存在而失败(如根路径/boarding)
          // 从已加载的folders数组中查找
          console.warn('⚠️ getFolder failed, trying local lookup:', currentFolderPath);
          folderDetails = allFolders.find(f => f.path === currentFolderPath) || null;
        }
        
        if (folderDetails) {
          setCurrentFolder(folderDetails);
        } else {
          console.warn('⚠️ Folder not found via API or local data, clearing current folder:', currentFolderPath);
          setCurrentFolder(null);
          // Clean up stale URL param
          setSearchParams(prev => {
            prev.delete('folder');
            return prev;
          });
        }
        
        // Load subfolders using parent_folder_path
        const subfoldersData = await folderService.getFolders(appSlug || app?.id || '', {
          parent_folder_path: currentFolderPath
        });
        setSubfolders(subfoldersData);
        
        // Load documents
        await loadDocuments(currentFolderPath);
      } catch (error) {
        console.error('Failed to load folder details:', error);
      }
    };
    
    loadCurrentFolderDetails();
  }, [currentFolderPath, app?.id, appSlug]);

  // Sync URL → state when search string changes (browser back/forward)
  useEffect(() => {
    const params = new URLSearchParams(search);
    const urlFolder = params.get('folder');
    console.log('🔍 URL search changed:', { 
      search,
      folder: urlFolder, 
      currentFolderPath,
      foldersCount: folders.length
    });
    
    if (urlFolder && urlFolder !== currentFolderPath) {
      console.log('🔍 Syncing URL→state: setting currentFolderPath to', urlFolder);
      setCurrentFolderPath(urlFolder);
    }
  }, [search]);
  
  // DEBUG: Watch currentFolderPath changes
  useEffect(() => {
    console.log('📂 currentFolderPath changed:', currentFolderPath);
  }, [currentFolderPath]);
  
  // Load documents
  const loadDocuments = async (folderPath: string) => {
    try {
      setDocumentsLoading(true);
      const docs = await documentService.getDocuments(folderPath);
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocuments([]);
    } finally {
      setDocumentsLoading(false);
    }
  };
  
  // Handle folder click
  const handleFolderClick = (folderPath: string) => {
    console.log('🍞 handleFolderClick:', { folderPath, currentFolderPath, foldersCount: folders.length });
    // Clear forward stack when navigating to a new folder
    setForwardStack([]);
    // Use navigate to update URL - append ?folder= to current path
    // IMPORTANT: navigate FIRST so URL updates trigger the sync effect
    navigate(`?folder=${encodeURIComponent(folderPath)}`, { replace: false });
  };
  
  // Handle forward navigation (re-enter a previously exited folder)
  const handleForward = () => {
    if (forwardStack.length === 0) return;
    const path = forwardStack[forwardStack.length - 1];
    setForwardStack(prev => prev.slice(0, -1));
    navigate(`?folder=${encodeURIComponent(path)}`, { replace: false });
  };
  
  // Handle create folder
  const handleCreateFolder = async (data: FolderCreateRequest) => {
    try {
      if (!app || !app.id) {
        showToast('App info not loaded yet. Please wait and try again.', 'error');
        return;
      }
      
      const folderData: FolderCreateRequest = {
        ...data,
        app_id: app.id
      };
      
      await folderService.createFolder(folderData);
      
      // Reload folders and current subfolders
      await loadFolders(appSlug || app.id, app.id);
      // If user is in a folder, reload its subfolders so the new one appears immediately
      if (currentFolderPath) {
        const subfoldersData = await folderService.getFolders(appSlug || app.id || '', {
          parent_folder_path: currentFolderPath
        });
        setSubfolders(subfoldersData);
      }
      
      setShowCreateModal(false);
    } catch (error) {
      console.error('Failed to create folder:', error);
      showToast('Failed to create folder. Check network or permissions.', 'error');
    }
  };
  
  // Handle delete folder
  const handleDeleteFolder = async (folderPath: string) => {
    // Check if folder has subfolders (use allFolders for deep folder detection)
    const subfoldersCount = allFolders.filter(f => f.parent_folder_path === folderPath).length;
    
    let recursive = false;
    
    if (subfoldersCount > 0) {
      // Ask user about recursive delete
      const folderName = allFolders.find(f => f.path === folderPath)?.name || 'This folder';
      const confirmMessage = `Folder "${folderName}" has ${subfoldersCount} subfolder(s).\n\n` +
                           `Click "OK" to recursively delete all subfolders and documents.\n` +
                           `Click "Cancel" to delete only the empty folder.`;
      
      if (!(await window.wetYesOrNo(confirmMessage))) {
        return;
      }
      
      recursive = true;
    } else {
      // No subfolders, simple confirmation
      if (!(await window.wetYesOrNo('Delete this folder? All documents inside will also be deleted.'))) {
        return;
      }
    }
    
    try {
      await folderService.deleteFolder(folderPath, recursive);
      
      // If deleting current folder, navigate to parent or root
      if (currentFolderPath === folderPath) {
        const folderToDelete = allFolders.find(f => f.path === folderPath);
        const parentPath = folderToDelete?.parent_folder_path ||
          // Derive parent from path if not found in allFolders
          (folderPath.lastIndexOf('/') > 0
            ? folderPath.substring(0, folderPath.lastIndexOf('/'))
            : null);
        setCurrentFolderPath(parentPath);
        // Also update URL so refresh doesn't hit 404 on deleted folder
        if (parentPath) {
          navigate(`?folder=${encodeURIComponent(parentPath)}`, { replace: true });
        } else {
          navigate('?', { replace: true });
        }
      }
      
      // Reload folders
      if (app) {
        await loadFolders(appSlug || app.id, app.id);
      }
    } catch (error: any) {
      console.error('Delete Folder Failed:', error);
      
      // Provide detailed error message
      if (error.response?.status === 400) {
        const errorDetail = error.response?.data?.detail || 'Folder is not empty';
        showToast(`Delete failed: ${errorDetail}\n\nPlease use the recursive delete option.`, 'error');
      } else {
        showToast('Failed to delete folder. It may not be empty or you may not have permission.', 'error');
      }
    }
  };
  
  // Handle preview document
  const handlePreviewDocument = (document: Document) => {
    console.log('Preview document:', document);
    // Navigate to document detail page using path (fallback to UUID)
    const docPath = document.path || document.storage_path || document.id;
    navigate(`/admin/documents/${docPath.replace(/^\//, '')}`);
  };
  
  // Handle push single document to WebBot
  const handleWebbotPush = async (document: Document) => {
    const docName = document.title || document.original_filename || 'this document';
    const confirmed = await window.wetYesOrNo(`Push "${docName}" to WebBot?`);
    if (!confirmed) return;

    try {
      const token = localStorage.getItem('access_token');
      const resp = await fetch('/api/v1/import-to-webbot/single', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          document_path: document.path,
          path_prefix: '/canadasite'
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        showToast(`WebBot push failed: ${err.detail || resp.statusText}`, 'error');
        return;
      }
      const result = await resp.json();
      showToast(`✅ WebBot: ${result.inserted} inserted, ${result.updated} updated`, 'success');
    } catch (error) {
      console.error('WebBot push error:', error);
      showToast('Failed to push to WebBot. Check network or server.', 'error');
    }
  };
  
  // Handle delete document
  const handleDeleteDocument = async (document: Document) => {
    if (!(await window.wetYesOrNo(`Delete document "${document.title || document.original_filename}"?`))) {
      return;
    }
    
    try {
      await documentService.deleteDocument(document.path);
      // Reload documents
      if (currentFolderPath) {
        await loadDocuments(currentFolderPath);
      }
      showToast('Document deleted successfully', 'success');
    } catch (error) {
      console.error('Failed to delete document:', error);
      showToast('Failed to delete document. Check network or permissions.', 'error');
    }
  };
  
  // Handle edit folder
  const handleEditFolder = async (folderPath: string) => {
    const folderToEdit = folders.find(f => f.path === folderPath);
    if (!folderToEdit) return;
    
    setEditingFolder(folderToEdit);
    setShowEditModal(true);
  };
  
  // Handle save edited folder
  const handleSaveEditFolder = async (data: {
    name: string;
    description?: string;
    parent_folder_path?: string;
  }) => {
    if (!editingFolder || !app || !editingFolder.path) return;
    
    try {
      // Call update folder API using path
      await folderService.updateFolder(editingFolder.path, data);
      
      // Reload folders
      await loadFolders(appSlug || app?.id || '', app?.id);
      
      // Update current folder state if editing current folder
      if (currentFolderPath === editingFolder.path) {
        const updatedCurrentFolder = await folderService.getFolder(editingFolder.path);
        if (updatedCurrentFolder) {
          setCurrentFolder(updatedCurrentFolder);
        }
      }
      
      // Close edit modal
      setShowEditModal(false);
      setEditingFolder(null);
      
      console.log('Folder updated successfully');
    } catch (error) {
      console.error('Failed to update folder:', error);
      showToast('Failed to update folder: ' + ((error as any).response?.data?.detail || 'Unknown error'), 'error');
      throw error;
    }
  };
  
  // Build breadcrumb path
  const buildBreadcrumbs = () => {
    if (!folders.length && !currentFolderPath && !app) return [];
    
    const breadcrumbs = [];
    
    let current = folders.find(f => f.path === currentFolderPath);
    
    if (current) {
      // Walk up via parent_folder_path (deepest → shallowest, unshift to reverse)
      while (current) {
        breadcrumbs.unshift({
          path: current.path,
          name: current.name,
        });
        
        if (current.parent_folder_path) {
          current = folders.find(f => f.path === current.parent_folder_path);
        } else {
          current = undefined;
        }
      }
    } else if (currentFolderPath) {
      // Fallback: build breadcrumbs from path segments
      const segments = currentFolderPath.split('/').filter(Boolean);
      // Skip first segment (app prefix); app breadcrumb already represents it
      const pathSegments = segments.slice(1);
      let accumulatedPath = '/' + segments[0]; // start with the skipped prefix
      for (const segment of pathSegments) {
        accumulatedPath += '/' + segment;
        const match = folders.find(f => f.path === accumulatedPath);
        breadcrumbs.push({
          path: accumulatedPath,
          name: match?.name || segment,
        });
      }
    }
    
    // Add app as root (last so it shows first via unshift)
    if (app) {
      breadcrumbs.unshift({
        path: 'app',
        name: app.name,
      });
    }
    
    // Remove duplicate first folder if it matches the app name
    // (DB paths have double prefix like /boarding/boarding/...)
    if (breadcrumbs.length >= 2 && breadcrumbs[0].path === 'app') {
      const firstFolder = breadcrumbs[1];
      if (firstFolder.name?.toLowerCase() === app?.name?.toLowerCase()) {
        breadcrumbs.splice(1, 1);
      }
    }
    
    return breadcrumbs;
  };
  
  // Handle navigate to documents
  const handleNavigateToDocuments = (folderPath: string) => {
    const encodedPath = encodeURIComponent(folderPath);
    navigate(`/admin/apps/${appSlug}/folders/${encodedPath}/documents`);
  };
  
  // Handle navigate to upload
  const handleNavigateToUpload = (folderPath: string) => {
    // 使用查询参数传递文件夹路径，避免 %2F 在 React Router 中的路径解析问题
    navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(folderPath)}`);
  };

  // Handle navigate to import folder
  const handleImportFolder = (folderPath: string) => {
    navigate(`/admin/apps/${appSlug}/upload?folder=${encodeURIComponent(folderPath)}&mode=import`);
  };

  // Handle move folder
  const handleMoveFolder = () => {
    const path = currentFolder?.path || currentFolderPath || '';
    if (!path) {
      showToast('Please select a folder first', 'warning');
      return;
    }
    setMoveFolderTarget('');
    setMoveFolderError(null);
    setShowMoveFolderModal(true);
  };

  const handleMoveFolderConfirm = async () => {
    const srcPath = currentFolder?.path || currentFolderPath || '';
    const target = moveFolderTarget.trim().replace(/\/$/, '');

    if (!target) {
      setMoveFolderError('Please enter a target parent folder path');
      return;
    }
    if (srcPath === target) {
      setMoveFolderError('Cannot move folder to itself');
      return;
    }
    if (target.startsWith(srcPath + '/')) {
      setMoveFolderError('Cannot move folder into its own subfolder');
      return;
    }

    setMoveFolderLoading(true);
    setMoveFolderError(null);
    try {
      const result = await folderService.moveFolder(srcPath, target);
      showToast('Folder moved successfully', 'success');
      setShowMoveFolderModal(false);
      // Refresh folder tree
      const appSlug = srcPath.split('/')[1];
      await loadFolders(appSlug);
      setCurrentFolderPath(target + '/' + (currentFolder?.name || ''));
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error.message || 'Move failed';
      setMoveFolderError(detail);
    } finally {
      setMoveFolderLoading(false);
    }
  };

  // Handle website import
  const handleImportWebsite = (folderPath: string) => {
    setShowImportWebsiteModal(true);
  };

  // Handle website crawl submission
  const handleSubmitImportWebsite = async () => {
    if (!websiteUrl.trim() || !currentFolderPath || !currentFolder || !app) {
      setImportError('Please fill in the URL and ensure a folder is selected');
      return;
    }
    
    // Validate URL
    try {
      new URL(websiteUrl);
    } catch {
      setImportError('Please enter a valid URL (e.g., https://example.com)');
      return;
    }
    
    setImportingWebsite(true);
    setImportError(null);
    
    try {
      // Build request
      const request: WebsiteCrawlRequest = {
        url: websiteUrl.trim(),
        depth: crawlDepth,
        folder_path: currentFolderPath,
        include_images: true,
        follow_external_links: false,
        respect_robots_txt: true
      };
      
      // Call backend API
      const response = await aiService.crawlWebsite(request);
      
      // Close import modal and show inline success notification
      setImportError(null);
      setImportSuccess(`Website crawl started! Task: ${response.task_id}`);
      
      // Close modal
      setShowImportWebsiteModal(false);
      setWebsiteUrl('');
      setCrawlDepth(1);
      // Auto-clear success message
      setTimeout(() => setImportSuccess(null), 8000);
    } catch (error: any) {
      console.error('Website import failed:', error);
      const detail = error.response?.data?.detail;
      const detailStr = Array.isArray(detail) ? detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ') : detail;
      setImportError(detailStr || error.message || 'Website import failed. Check network or backend service.');
    } finally {
      setImportingWebsite(false);
    }
  };

  // Export to WebBot state
  const [showExportWebBotModal, setShowExportWebBotModal] = useState(false);
  const [showMoveFolderModal, setShowMoveFolderModal] = useState(false);
  const [moveFolderTarget, setMoveFolderTarget] = useState('');
  const [moveFolderLoading, setMoveFolderLoading] = useState(false);
  const [moveFolderError, setMoveFolderError] = useState<string | null>(null);
  const [exportDepth, setExportDepth] = useState(1);
  const [exportingToWebBot, setExportingToWebBot] = useState(false);
  const [exportResult, setExportResult] = useState<any>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  
  // Handle export to WebBot
  const handleExportToWebBot = async () => {
    if (!currentFolderPath) {
      setExportError('Please select a folder first');
      return;
    }
    
    setExportingToWebBot(true);
    setExportError(null);
    setExportResult(null);
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/export/folder/${encodeURIComponent(currentFolderPath)}?include_documents=true&recursive=${exportDepth > 1}&token=${token}`);
      if (!response.ok) {
        throw new Error(`Export failed: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setExportResult(data);
    } catch (error: any) {
      console.error('Export to WebBot failed:', error);
      setExportError(error.message || 'Export failed. Check backend service.');
    } finally {
      setExportingToWebBot(false);
    }
  };

  // Handle actual import to WebBot (sends data to webbot_page table)
  const [importingToWebBot, setImportingToWebBot] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const handleImportToWebBot = async (e: React.MouseEvent) => {
    e.preventDefault();
    try {
      if (!currentFolderPath) {
        setExportError('Please select a folder first');
        return;
      }
      
      setImportingToWebBot(true);
      setExportError(null);
      setImportResult(null);
      
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/import-to-webbot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (token || '')
        },
        body: JSON.stringify({
          folder_path: currentFolderPath,
          recursive: exportDepth > 1
        })
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Import failed: ' + response.status);
      }
      const data = await response.json();
      setImportResult(data);
    } catch (error: any) {
      console.error('Import to WebBot failed:', error);
      setExportError(error && error.message ? error.message : 'Import failed. Check backend service.');
    } finally {
      setImportingToWebBot(false);
    }
  };

  // Handle sitemap import
  const handleSubmitImportSitemap = async () => {
    if (!sitemapUrl.trim() || !currentFolderPath || !app) {
      setImportError('Please fill in the sitemap URL and ensure a folder is selected');
      return;
    }
    try {
      new URL(sitemapUrl);
    } catch {
      setImportError('Please enter a valid sitemap URL (e.g., https://example.com/sitemap.xml)');
      return;
    }
    setImportingSitemap(true);
    setImportError(null);
    try {
      const request: SitemapImportRequest = {
        sitemap_url: sitemapUrl.trim(),
        folder_path: currentFolderPath,
        include_images: true,
        depth: sitemapDepth
      };
      const response: SitemapImportResponse = await aiService.importFromSitemap(request);
      setImportError(null);
      setImportSuccess(`Sitemap import started! Task: ${response.task_id}`);
      setShowImportWebsiteModal(false);
      setSitemapUrl('');
      setSitemapDepth(0);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const detailStr = Array.isArray(detail) ? detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ') : detail;
      setImportError(detailStr || error.message || 'Sitemap import failed');
    } finally {
      setImportingSitemap(false);
    }
  };
  
  // Render loading state
  if (loading) {
    return (
      <div className="p-6 text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="mt-4 text-gray-600">Loading folders...</p>
      </div>
    );
  }
  
  // Render error state
  if (!app) {
    const isPermissionError = error?.includes('permission');
    const errorTitle = isPermissionError ? 'No Access Permission' : 'App Not Found';
    
    return (
      <div className="p-6">
        <div className="mb-6">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
            <Link to="/admin/apps" className="hover:text-blue-600">Apps</Link>
            <span>›</span>
            <span className="text-gray-700">Unknown App</span>
          </div>
        </div>
        
        {isPermissionError ? (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-6 text-center">
            <h3 className="text-lg font-medium text-orange-800 mb-2">{errorTitle}</h3>
            <p className="text-orange-700 mb-4">{error || 'You do not have permission to access this app.'}</p>
            <div className="space-y-3">
              <Link to="/admin/apps" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-block">
                Back to App List
              </Link>
              <div className="mt-4 pt-4 border-t border-orange-100">
                <p className="text-sm text-orange-600 mb-2">To access this app:</p>
                <div className="space-y-2 text-sm text-orange-700">
                  <p>1. Log in with the app owner account</p>
                  <p>2. Contact an admin to grant access</p>
                  <p>3. Create your own app</p>
                </div>
                <button
                  onClick={() => navigate('/admin/apps?create=true')}
                  className="mt-3 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Create New App
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <h3 className="text-lg font-medium text-red-800 mb-2">{errorTitle}</h3>
            <p className="text-red-700 mb-4">{error || 'Could not find the specified app. Check the URL or go back.'}</p>
            <Link to="/admin/apps" className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
              Back to App List
            </Link>
          </div>
        )}
      </div>
    );
  }
  
  const breadcrumbs = buildBreadcrumbs();
  
  return (
    <div className="p-6 relative">
      {/* Inline success notification */}
      {importSuccess && (
        <div className="fixed top-4 right-4 z-50 bg-green-50 border border-green-300 rounded-lg p-4 shadow-lg max-w-md animate-slide-in">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            <div>
              <p className="text-sm font-medium text-green-800">{importSuccess}</p>
              <p className="text-xs text-green-600 mt-1">Check the Tasks page for progress.</p>
            </div>
            <button onClick={() => setImportSuccess(null)} className="ml-auto pl-3 text-green-400 hover:text-green-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
      {/* Breadcrumb Navigation */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/apps" className="hover:text-blue-600">Apps</Link>
          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={crumb.path}>
              <span>›</span>
              {index < breadcrumbs.length - 1 ? (
                <button
                  type="button"
                  className="hover:text-blue-600 underline underline-offset-2"
                  onClick={() => {
                    if (crumb.path === 'app') {
                      // Navigate to app root (clear folder selection)
                      if (currentFolderPath) {
                        setForwardStack(prev => [...prev, currentFolderPath]);
                      }
                      setCurrentFolderPath(null);
                      navigate('');
                    } else {
                      handleFolderClick(crumb.path);
                    }
                  }}
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
      
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Folder Management</h2>
        <div className="flex space-x-2">
          <button 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center"
            onClick={() => {
              setParentFolderPath(null);
              setShowCreateModal(true);
            }}
          >
            <span>+ Create Root Folder</span>
          </button>
          {currentFolderPath && (
            <button 
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center"
              onClick={() => {
                setParentFolderPath(currentFolderPath);
                setShowCreateModal(true);
              }}
            >
              <span>+ Create Subfolder</span>
            </button>
          )}
        </div>
      </div>
      
      {/* Two-Column Layout */}
      <div className="flex space-x-6">
        {/* Left: Subfolders + AI Operations */}
        <div className="w-1/3 space-y-4">
          {/* Subfolders Card */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h3 className="font-medium">Folders</h3>
              {currentFolder && (() => {
                const parentPath = currentFolder.parent_folder_path || (currentFolder.path ? currentFolder.path.substring(0, currentFolder.path.lastIndexOf('/')) : null);
                if (!parentPath || parentPath === '') return null;
                return (
                  <button
                    className="text-blue-600 hover:text-blue-800 text-xs ml-2"
                    onClick={() => {
                      setForwardStack(prev => [...prev, currentFolder.path]);
                      handleFolderClick(parentPath);
                    }}
                  >
                    ← Go to parent folder
                  </button>
                );
              })()}
              <button
                className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                disabled={forwardStack.length === 0}
                onClick={handleForward}
                title="Forward"
              >
                <svg className="w-4 h-4 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
            <div className="p-4">
              {(() => {
                // Show subfolders when a folder is selected, otherwise show all folders
                const displayFolders = currentFolder ? subfolders : folders;
                const showFilter = displayFolders.length > 30;
                const filteredFolders = folderSearch
                  ? displayFolders.filter(f => f.name.toLowerCase().includes(folderSearch.toLowerCase()))
                  : displayFolders;
                
                return (
                  <>
                    {showFilter && (
                      <div className="mb-3">
                        <input
                          type="text"
                          value={folderSearch}
                          onChange={e => setFolderSearch(e.target.value)}
                          placeholder="Filter folders..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    )}
                    {filteredFolders.length > 0 ? (
                      <div className="space-y-2">
                        {filteredFolders.map(folder => (
                          <div
                            key={folder.path || folder.id}
                            className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                            onClick={() => handleFolderClick(folder.path || '')}
                          >
                            <div className="flex items-center">
                              <FolderIcon className="w-5 h-5 text-yellow-500 mr-2" />
                              <div className="flex-1">
                                <div className="font-medium">{folder.name}</div>
                              </div>
                              <ChevronRightIcon className="w-5 h-5 text-gray-400" />
                            </div>
                          </div>
                        ))}
                        <div className="text-sm text-gray-500 mt-2">
                          {filteredFolders.length} folder{filteredFolders.length !== 1 ? 's' : ''} total
                          {folderSearch && filteredFolders.length !== displayFolders.length && (
                            <> (filtered from {displayFolders.length})</>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-500 text-center py-4">
                        {folderSearch ? 'No matching folders' : 'No folders yet'}
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
          </div>

          {/* AI Operations Card */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h3 className="font-medium">AI Operations</h3>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-1 gap-3">
                <button
                  className="p-3 border rounded-lg hover:bg-red-50 text-left border-red-200"
                  onClick={() => handleDeleteFolder(currentFolder?.path || currentFolderPath || '')}
                >
                  <div className="font-medium text-red-600">Delete Folder</div>
                  <div className="text-sm text-red-500">Delete this folder and all its contents</div>
                </button>
                <button
                  className="p-3 border rounded-lg hover:bg-gray-50 text-left"
                  onClick={() => {
                    setParentFolderPath(currentFolder?.path || currentFolderPath || '');
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
                  className="p-3 border rounded-lg hover:bg-green-50 text-left border-green-200"
                  onClick={() => handleImportFolder(currentFolder?.path || currentFolderPath || '')}
                >
                  <div className="font-medium text-green-600">Import Folder</div>
                  <div className="text-sm text-green-500">Import an entire folder from local drive</div>
                </button>
                <button
                  className="p-3 border rounded-lg hover:bg-amber-50 text-left border-amber-200"
                  onClick={handleMoveFolder}
                >
                  <div className="font-medium text-amber-600">Move Folder</div>
                  <div className="text-sm text-amber-500">Move this folder to a different parent</div>
                </button>
                <button
                  className="p-3 border rounded-lg hover:bg-purple-50 text-left border-purple-200"
                  onClick={() => handleImportWebsite(currentFolder?.path || currentFolderPath || '')}
                >
                  <div className="font-medium text-purple-600">Import Website</div>
                  <div className="text-sm text-purple-500">Crawl web pages and images from a URL</div>
                </button>
                <button
                  className="p-3 border rounded-lg hover:bg-indigo-50 text-left border-indigo-200"
                  onClick={() => {
                    if (!currentFolderPath) {
                      showToast('Please select a folder first', 'warning');
                      return;
                    }
                    setExportDepth(1);
                    setExportResult(null);
                    setExportError(null);
                    setShowExportWebBotModal(true);
                  }}
                >
                  <div className="font-medium text-indigo-600">Export to WebBot</div>
                  <div className="text-sm text-indigo-500">Export folder structure and pages to WebBot</div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Folder Content */}
        <div className="w-2/3">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              {currentFolder ? (
                <div className="flex justify-between items-start">
                  <details className="text-sm flex-1">
                    <summary className="cursor-pointer">
                      <h3 className="font-medium inline">{currentFolder.name} - Content</h3>
                    </summary>
                    <div className="mt-2 mb-2 text-xs text-gray-500 space-y-1 pl-1">
                      <div><span className="text-gray-400">Path:</span> <span className="font-mono">{currentFolder.path}</span></div>
                      <div><span className="text-gray-400">Created:</span> {new Date(currentFolder.created_at).toLocaleString()}</div>
                      {currentFolder.description && (
                        <div><span className="text-gray-400">Description:</span> {currentFolder.description}</div>
                      )}
                    </div>
                  </details>
                  <div className="text-sm text-gray-500 shrink-0 pt-0.5">
                    Documents ({documents.length})
                  </div>
                </div>
              ) : (
                <h3 className="font-medium">Root — Content</h3>
              )}
              {!currentFolder && (
                <div className="text-sm text-gray-500 shrink-0 pt-0.5">
                  Documents ({documents.length})
                </div>
              )}
            </div>
            
            <div className="p-4">
              {!currentFolder && documents.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <FolderIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <p>Select a folder from the left panel</p>
                </div>
              ) : (
                <>
                  {/* Documents */}
                  {documents.length > 0 && (
                    <div className="mb-6 border-t pt-6">
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Document</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uploaded</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {documents.map(doc => (
                              <tr key={doc.path || doc.storage_path || doc.name} className="hover:bg-gray-50">
                                <td className="px-6 py-4">
                                  <div>
                                    <div className="font-medium text-gray-900">{doc.title || doc.original_filename || 'Untitled'}</div>
                                    <div className="text-sm text-gray-500">{doc.original_filename}</div>
                                    {doc.folder_path && <div className="text-xs text-gray-400 font-mono mt-0.5">{doc.folder_path}</div>}
                                  </div>
                                </td>
                                <td className="px-6 py-4 text-right text-sm font-medium">
                                  <button 
                                    className="text-blue-600 hover:text-blue-900 mr-3"
                                    onClick={() => handlePreviewDocument(doc)}
                                  >
                                    Preview
                                  </button>
                                  {doc.file_type === 'HTML' && (
                                    <button type="button"
                                      className="text-purple-600 hover:text-purple-900 mr-3"
                                      onClick={() => handleWebbotPush(doc)}
                                    >
                                      Webbot
                                    </button>
                                  )}
                                  <button 
                                    className="text-red-600 hover:text-red-900"
                                    onClick={() => handleDeleteDocument(doc)}
                                  >
                                    Delete
                                  </button>
                                </td>
                                <td className="px-6 py-4">
                                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    {doc.file_type || 'Unknown'}
                                  </span>
                                </td>
                                <td className="px-6 py-4">
                                  {doc.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(2)} MB` : 'Unknown'}
                                </td>
                                <td className="px-6 py-4">
                                  {doc.created_at ? new Date(doc.created_at).toLocaleString() : 'Unknown'}
                                </td>
                                <td className="px-6 py-4">
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    doc.conversion_status === 'completed' ? 'bg-green-100 text-green-800' :
                                    doc.conversion_status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                                    doc.conversion_status === 'failed' ? 'bg-red-100 text-red-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {doc.conversion_status === 'completed' ? 'Completed' :
                                     doc.conversion_status === 'processing' ? 'Processing' :
                                     doc.conversion_status === 'failed' ? 'Failed' :
                                     'Pending'}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  
                  {documents.length === 0 && currentFolder && (
                    <div className="mb-6 border-t pt-6">
                      <h4 className="font-medium mb-3">Documents</h4>
                      <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
                        <DocumentIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                        <p>No documents in this folder</p>
                        <button 
                          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                          onClick={() => handleNavigateToUpload(currentFolder?.path || currentFolderPath || '')}
                        >
                          Upload First Document
                        </button>
                      </div>
                    </div>
                  )}
                  
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Create Folder Modal */}
      {showCreateModal && (
        <CreateFolderModal
          appId={app.id}
          appSlug={appSlug}
          parentFolderPath={parentFolderPath}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateFolder}
          folders={allFolders}
          mode="create"
        />
      )}
      
      {/* Edit Folder Modal */}
      {showEditModal && editingFolder && (
        <CreateFolderModal
          appId={app.id}
          appSlug={appSlug}
          parentFolderPath={editingFolder.parent_folder_path}
          onClose={() => {
            setShowEditModal(false);
            setEditingFolder(null);
          }}
          onSubmit={handleSaveEditFolder}
          folders={allFolders}
          mode="edit"
          folderToEdit={editingFolder}
        />
      )}
      
      {/* Export to WebBot Modal */}
      {showExportWebBotModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 overflow-y-auto py-8">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 my-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-indigo-800">Export to WebBot</h3>
                <button
                  onClick={() => setShowExportWebBotModal(false)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-4">
                <div className="bg-gray-50 p-3 rounded-md">
                  <p className="text-sm text-gray-600">
                    <strong>Folder:</strong> {currentFolderPath || 'Not selected'}
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Export Depth (1-20)
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={exportDepth}
                      onChange={(e) => setExportDepth(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                      className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      disabled={exportingToWebBot}
                    />
                    <span className="text-sm text-gray-500">
                      depth 1 = current folder only
                    </span>
                  </div>
                </div>
                
                {exportError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                    {exportError}
                  </div>
                )}
                
                <button
                  onClick={handleExportToWebBot}
                  disabled={exportingToWebBot || !currentFolderPath}
                  className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {exportingToWebBot ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                      Exporting...
                    </span>
                  ) : (
                    '🚀 Export'
                  )}
                </button>
                
                {exportResult && (
                  <div className="mt-4 border-t pt-4">
                    <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-3">
                      <p className="text-sm text-green-800">
                        📄 <strong>Documents:</strong> {exportResult.documents ? exportResult.documents.length : (exportResult.document_count || 0)}
                        {(exportResult.subfolder_count > 0 || (exportResult.subfolders || []).length > 0) && (
                          <> &nbsp;|&nbsp; 📁 <strong>Subfolders:</strong> {(exportResult.subfolders || []).length}</>
                        )}
                      </p>
                    </div>

                    {/* Preview of exported documents */}
                    {(exportResult.documents || []).length > 0 && (
                      <div className="mb-3">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">
                          Documents ({exportResult.documents.length})
                        </h4>
                        <div className="bg-gray-50 border border-gray-200 rounded-md p-3 max-h-60 overflow-y-auto">
                          {(exportResult.documents.slice(0, 10) || []).map((doc: any, i: number) => (
                            <div key={doc.path || i} className="text-xs text-gray-600 py-1 border-b border-gray-100 last:border-0">
                              <span className="font-medium">{doc.title || doc.path}</span>
                              <span className="text-gray-400 ml-2">{doc.mime_type || ''}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Import to WebBot button */}
                    <button
                      onClick={handleImportToWebBot}
                      disabled={importingToWebBot || !exportResult}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {importingToWebBot ? (
                        <span className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                          </svg>
                          Importing...
                        </span>
                      ) : (
                        '📥 Import to WebBot'
                      )}
                    </button>

                    {/* Import result display */}
                    {importResult && (
                      <div className="mt-3 bg-blue-50 border border-blue-200 rounded-md p-3">
                        <p className="text-sm text-blue-800">
                          ✅ <strong>Import complete:</strong>{' '}
                          {importResult.inserted} new pages{' '}
                          {importResult.updated > 0 && <>+ {importResult.updated} updated{' '}</>}
                          in WebBot{' '}
                          {importResult.skipped > 0 && <span className="text-gray-500">({importResult.skipped} skipped)</span>}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Move Folder Modal */}
      {showMoveFolderModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-xl mx-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-amber-800">Move Folder</h3>
                <button
                  onClick={() => setShowMoveFolderModal(false)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div className="bg-gray-50 p-3 rounded-md">
                  <p className="text-sm text-gray-600">
                    <strong>Moving:</strong> {currentFolder?.path || currentFolderPath}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Target Parent Folder Path
                  </label>
                  <input
                    type="text"
                    value={moveFolderTarget}
                    onChange={(e) => setMoveFolderTarget(e.target.value)}
                    placeholder="e.g. /boarding/canadasite/en/new-parent"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500"
                    disabled={moveFolderLoading}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Enter the full path of the target parent folder
                  </p>
                </div>

                {moveFolderError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                    {moveFolderError}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowMoveFolderModal(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                    disabled={moveFolderLoading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleMoveFolderConfirm}
                    disabled={moveFolderLoading || !moveFolderTarget.trim()}
                    className="flex-1 px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {moveFolderLoading ? (
                      <span className="flex items-center justify-center">
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                        </svg>
                        Moving...
                      </span>
                    ) : (
                      '📦 Move'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Import Website Modal */}
      {showImportWebsiteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-xl mx-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-purple-800">Import Content</h3>
                <button
                  onClick={() => setShowImportWebsiteModal(false)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  ✕
                </button>
              </div>
              
              {/* Tab switcher */}
              <div className="flex border-b border-gray-200 mb-4">
                <button
                  onClick={() => { setImportTab('website'); setImportError(null); }}
                  className={`px-4 py-2 text-sm font-medium border-b-2 ${
                    importTab === 'website'
                      ? 'border-purple-600 text-purple-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Website Crawl
                </button>
                <button
                  onClick={() => { setImportTab('sitemap'); setImportError(null); }}
                  className={`px-4 py-2 text-sm font-medium border-b-2 ${
                    importTab === 'sitemap'
                      ? 'border-green-600 text-green-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Sitemap Import
                </button>
              </div>
              
              {importTab === 'website' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Website URL
                    </label>
                    <input
                      type="url"
                      value={websiteUrl}
                      onChange={(e) => setWebsiteUrl(e.target.value)}
                      placeholder="https://example.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      disabled={importingWebsite}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Crawl Depth
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="range"
                        min="1"
                        max="5"
                        value={crawlDepth}
                        onChange={(e) => setCrawlDepth(parseInt(e.target.value))}
                        className="flex-1"
                        disabled={importingWebsite}
                      />
                      <span className="text-sm font-medium text-purple-600 w-8">{crawlDepth}</span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>1 (Homepage only)</span>
                      <span>3</span>
                      <span>5 (Deep crawl)</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      Depth {crawlDepth}: {getDepthDescription(crawlDepth)}
                    </p>
                  </div>
                  
                  <div className="bg-gray-50 p-3 rounded-md">
                    <p className="text-sm text-gray-600">
                      <strong>Target Folder:</strong> {currentFolder?.name || 'Not selected'} <br />
                      <strong>App:</strong> {app?.name || 'Unknown'}
                    </p>
                  </div>
                  
                  {importError && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3">
                      <p className="text-sm text-red-700">{importError}</p>
                    </div>
                  )}
                  
                  <div className="flex justify-end space-x-3 pt-4">
                    <button
                      onClick={() => setShowImportWebsiteModal(false)}
                      className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                      disabled={importingWebsite}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitImportWebsite}
                      disabled={importingWebsite || !websiteUrl.trim()}
                      className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                    >
                      {importingWebsite ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Importing...
                        </>
                      ) : (
                        'Start Import'
                      )}
                    </button>
                  </div>
                </div>
              )}
              
              {importTab === 'sitemap' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Sitemap URL
                    </label>
                    <input
                      type="url"
                      value={sitemapUrl}
                      onChange={(e) => setSitemapUrl(e.target.value)}
                      placeholder="https://www.canada.ca/sitemap.xml"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      disabled={importingSitemap}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter a sitemap.xml URL to bulk-import all listed pages
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Recursion Depth
                    </label>
                    <select
                      value={sitemapDepth}
                      onChange={(e) => setSitemapDepth(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      disabled={importingSitemap}
                    >
                      <option value={0}>0 - Sitemap URLs only (no link tracking)</option>
                      <option value={1}>1 - Sitemap URLs + direct child links</option>
                      <option value={2}>2 - Sitemap URLs + 2 levels deep</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Recommended: depth = 0 (sitemaps already contain all desired URLs)
                    </p>
                  </div>
                  
                  <div className="bg-gray-50 p-3 rounded-md">
                    <p className="text-sm text-gray-600">
                      <strong>Target Folder:</strong> {currentFolder?.name || 'Not selected'} <br />
                      <strong>App:</strong> {app?.name || 'Unknown'}
                    </p>
                  </div>
                  
                  {importError && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3">
                      <p className="text-sm text-red-700">{importError}</p>
                    </div>
                  )}
                  
                  <div className="flex justify-end space-x-3 pt-4">
                    <button
                      onClick={() => setShowImportWebsiteModal(false)}
                      className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                      disabled={importingSitemap}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitImportSitemap}
                      disabled={importingSitemap || !sitemapUrl.trim()}
                      className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                    >
                      {importingSitemap ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Importing...
                        </>
                      ) : (
                        'Start Sitemap Import'
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper: get depth description
const getDepthDescription = (depth: number): string => {
  const descriptions = [
    'Homepage only',
    'Homepage + direct links',
    'Homepage + 2 levels',
    'Homepage + 3 levels',
    'Deep crawl (may be slow)',
    'Very deep crawl (may be very slow)'
  ];
  return descriptions[Math.min(depth - 1, descriptions.length - 1)] || 'Custom depth';
};

export default AdminAppFolders;
