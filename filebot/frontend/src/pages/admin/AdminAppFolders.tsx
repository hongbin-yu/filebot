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
  const [showEditDocModal, setShowEditDocModal] = useState(false);
  const [editingDocument, setEditingDocument] = useState<any>(null);
  const [editDocTitle, setEditDocTitle] = useState('');
  const [editDocDescription, setEditDocDescription] = useState('');
  const [editDocSaving, setEditDocSaving] = useState(false);
  
  // Website import form
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [crawlDepth, setCrawlDepth] = useState(1);
  const [skipIfPageExists, setSkipIfPageExists] = useState(true);
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
  // Load top-level folders for sidebar (direct children only, like ClientAppFolders)
  const loadFolders = async (appIdentifier: string, appId?: string) => {
    try {
      // Fetch only direct top-level folders: parent_folder_path = /{appSlug}
      const rootFolders = await folderService.getFolders(appIdentifier, { limit: 200 });
      setFolders(rootFolders);
      
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
          folderDetails = null;
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
    // Check if folder has subfolders via API (direct children only)
    let subfoldersCount = 0;
    try {
      const children = await folderService.getFolders(appSlug || app.id || '', {
        parent_folder_path: folderPath, limit: 1
      });
      // If children returned with limit=1, there's at least one subfolder
      if (children.length > 0) {
        // Get full count for the message
        const allChildren = await folderService.getFolders(appSlug || app.id || '', {
          parent_folder_path: folderPath, limit: 500
        });
        subfoldersCount = allChildren.length;
      }
    } catch (e) {
      console.warn('Failed to check subfolders:', e);
    }
    
    let recursive = false;
    
    if (subfoldersCount > 0) {
      // Ask user about recursive delete
      const folderName = currentFolder?.name || currentFolderPath?.split('/').pop() || 'This folder';
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
        const parentPath = currentFolder?.parent_folder_path ||
          // Derive parent from path if not found in state
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
  
  // Handle toggle publish status (Publish / Unpublish)
  const handleTogglePublish = async (document: Document) => {
    const isPublished = document.publish_status === 'PUBLISHED';
    const docName = document.title || document.original_filename || document.path;
    if (!(await window.wetYesOrNo(
      isPublished
        ? `Unpublish "${docName}"? It will no longer be publicly accessible.`
        : `Publish "${docName}"? It will be publicly accessible via its URL.`
    ))) {
      return;
    }

    try {
      const docId = document.path || document.storage_path || document.id;
      if (!docId) {
        showToast('Document has no identifier', 'error');
        return;
      }
      await documentService.updateDocument(docId, {
        publish_status: isPublished ? 'UNPUBLISHED' : 'PUBLISHED'
      });
      if (currentFolderPath) {
        await loadDocuments(currentFolderPath);
      }
      showToast(isPublished ? 'Document unpublished' : 'Document published', 'success');
    } catch (error) {
      console.error('Failed to toggle publish status:', error);
      showToast('Failed to update publish status. Check network or permissions.', 'error');
    }
  };

  // Handle edit document
  const handleEditDocument = (doc: any) => {
    setEditingDocument(doc);
    setEditDocTitle(doc.title || doc.original_filename || '');
    setEditDocDescription(doc.description || '');
    setShowEditDocModal(true);
  };

  const handleSaveEditDoc = async () => {
    if (!editingDocument || !editDocTitle.trim()) return;
    setEditDocSaving(true);
    try {
      await documentService.updateDocument(editingDocument.path || editingDocument.storage_path, {
        title: editDocTitle.trim(),
        description: editDocDescription.trim()
      });
      setShowEditDocModal(false);
      setEditingDocument(null);
      if (currentFolderPath) {
        await loadDocuments(currentFolderPath);
      }
      showToast('Document updated successfully', 'success');
    } catch (error) {
      console.error('Failed to update document:', error);
      showToast('Failed to update document', 'error');
    } finally {
      setEditDocSaving(false);
    }
  };

  // Handle edit folder
  const handleEditFolder = async (folderPath: string) => {
    const folderToEdit = currentFolder;
    if (!folderToEdit) return;
    
    setEditingFolder(folderToEdit);
    setShowEditModal(true);
  };
  
  // Handle save edited folder
  const handleSaveEditFolder = async (data: {
    name: string;
    description?: string;
    parent_folder_path?: string;
    thumbnail_size?: string;
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
    
    // 确认：爬取大型网站可能需要较长时间
    const siteName = new URL(websiteUrl).hostname;
    const depthDesc = getDepthDescription(crawlDepth);
    const confirmMsg =
      `⚠️ 即将爬取网站: ${siteName}\n\n` +
      `深度: ${crawlDepth} - ${depthDesc}\n` +
      `目标文件夹: ${currentFolder?.name || currentFolderPath}\n\n` +
      `重要提醒:\n` +
      `• 网站规模越大，所需时间越长\n` +
      `• 深度 ≥ 3 可能会爬取数百甚至上千页面\n` +
      `• 爬取期间请勿关闭此页面\n\n` +
      `确认开始爬取?`;
    if (!(await window.wetYesOrNo(confirmMsg, '⚠️ 确认爬取网站'))) {
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
        respect_robots_txt: true,
        skip_if_exists: skipIfPageExists
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
      setSkipIfPageExists(true);
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
      <main property="mainContentOfPage" className="container">
        <p className="mrgn-tp-xl">Loading folders...</p>
      </main>
    );
  }
  
  // Render error state
  if (!app) {
    const isPermissionError = error?.includes('permission');
    const errorTitle = isPermissionError ? 'No Access Permission' : 'App Not Found';
    
    return (
      <main property="mainContentOfPage" className="container">
        <nav id="wb-bc" property="breadcrumb">
          <h2 className="wb-inv">You are here:</h2>
          <div className="container">
            <ol className="breadcrumb">
              <li><Link to="/admin/apps">Apps</Link></li>
              <li>Unknown App</li>
            </ol>
          </div>
        </nav>
        
        {isPermissionError ? (
          <div className="alert alert-warning">
            <h3>{errorTitle}</h3>
            <p>{error || 'You do not have permission to access this app.'}</p>
            <Link to="/admin/apps" className="btn btn-primary">Back to App List</Link>
            <hr/>
            <p>To access this app:</p>
            <ol>
              <li>Log in with the app owner account</li>
              <li>Contact an admin to grant access</li>
              <li>Create your own app</li>
            </ol>
            <button onClick={() => navigate('/admin/apps?create=true')} className="btn btn-success">Create New App</button>
          </div>
        ) : (
          <div className="alert alert-danger">
            <h3>{errorTitle}</h3>
            <p>{error || 'Could not find the specified app. Check the URL or go back.'}</p>
            <Link to="/admin/apps" className="btn btn-danger">Back to App List</Link>
          </div>
        )}
      </main>
    );
  }
  
  const breadcrumbs = buildBreadcrumbs();
  
  return (
    <main property="mainContentOfPage" className="container">
      {/* Inline success notification */}
      {importSuccess && (
        <div className="alert alert-success">
          <p><strong>{importSuccess}</strong></p>
          <p className="small">Check the Tasks page for progress.</p>
          <button onClick={() => setImportSuccess(null)} className="close" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        </div>
      )}
      {/* WET Breadcrumb */}
      <nav id="wb-bc" property="breadcrumb">
        <h2 className="wb-inv">You are here:</h2>
        <div className="container">
          <ol className="breadcrumb">
            <li><Link to="/admin/apps">Apps</Link></li>
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={crumb.path}>
                {index < breadcrumbs.length - 1 ? (
                  <li><a href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (crumb.path === 'app') {
                        if (currentFolderPath) {
                          setForwardStack(prev => [...prev, currentFolderPath]);
                        }
                        setCurrentFolderPath(null);
                        navigate('');
                      } else {
                        handleFolderClick(crumb.path);
                      }
                    }}
                  >{crumb.name}</a></li>
                ) : (
                  <li>{crumb.name}</li>
                )}
              </React.Fragment>
            ))}
          </ol>
        </div>
      </nav>

      {/* Title */}
      <h1 property="name">{app.name}</h1>
      <p>{app.description}</p>

      {/* Folder Management bar */}
      <div className="row mrgn-tp-md mrgn-bttm-md">
        <div className="col-sm-6">
          <h2 className="h4">Folder Management</h2>
        </div>
        <div className="col-sm-6 text-right">
          <button 
            className="btn btn-primary"
            onClick={() => {
              setParentFolderPath(null);
              setShowCreateModal(true);
            }}
          >+ Create Root Folder</button>
          {' '}
          {currentFolderPath && (
            <button 
              className="btn btn-success"
              onClick={() => {
                setParentFolderPath(currentFolderPath);
                setShowCreateModal(true);
              }}
            >+ Create Subfolder</button>
          )}
        </div>
      </div>

      <div className="row">
        {/* Left: Subfolders + AI Operations */}
        <div className="col-md-3 aside">
          {/* Subfolders Card */}
          <div className="panel panel-info">
            <div className="panel-heading">
              <h3 className="panel-title">Folders</h3>
              <div className="pull-right">
                {currentFolder && (() => {
                  const parentPath = currentFolder.parent_folder_path || (currentFolder.path ? currentFolder.path.substring(0, currentFolder.path.lastIndexOf('/')) : null);
                  if (!parentPath || parentPath === '') return null;
                  return (
                    <button
                      className="btn btn-link btn-xs"
                      onClick={() => {
                        setForwardStack(prev => [...prev, currentFolder.path]);
                        handleFolderClick(parentPath);
                      }}
                    >← Parent</button>
                );
              })()}
                <button
                  className="btn btn-link btn-xs"
                  disabled={forwardStack.length === 0}
                  onClick={handleForward}
                  title="Forward"
                >→</button>
              </div>
            </div>
            <div className="panel-body">
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
                      <div style={{marginBottom:12}}>
                        <input
                          type="text"
                          value={folderSearch}
                          onChange={e => setFolderSearch(e.target.value)}
                          placeholder="Filter folders..."
                           style={{ width:"100%", paddingLeft:12, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:8, fontSize:"0.875rem" }}
                        />
                      </div>
                    )}
                    {filteredFolders.length > 0 ? (
                      <div className="fb-space-y" style={{gap:8}}>
                        {filteredFolders.map(folder => (
                          <div
                            key={folder.path || folder.id}
                            style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, cursor:"pointer" }}
                            onClick={() => handleFolderClick(folder.path || '')}
                          >
                            <div className="fb-d-flex fb-align-center">
                              <FolderIcon style={{ width:20, height:20, color:"#eab308", marginRight:8 }} />
                              <div style={{flex:1}}>
                                <div style={{fontWeight:500}}>
                                  {folder.name}
                                  {folder.thumbnail_size && (
                                    <span className="label label-info" style={{marginLeft:8,fontSize:'0.65rem',verticalAlign:'middle'}}>
                                      {folder.thumbnail_size}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <ChevronRightIcon style={{ width:20, height:20, color:"#9ca3af" }} />
                            </div>
                          </div>
                        ))}
                        <div  style={{ fontSize:"0.875rem", marginTop:8 }}>
                          {filteredFolders.length} folder{filteredFolders.length !== 1 ? 's' : ''} total
                          {folderSearch && filteredFolders.length !== displayFolders.length && (
                            <> (filtered from {displayFolders.length})</>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p  style={{ paddingTop:16 }}>
                        {folderSearch ? 'No matching folders' : 'No folders yet'}
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
          </div>

          {/* AI Operations Card */}
          <div className="panel panel-warning">
            <div className="panel-heading">
              <h3 className="panel-title">AI Operations</h3>
            </div>
            <div className="panel-body">
              <div style={{ display:"grid", gridTemplateColumns:"repeat(1, minmax(0, 1fr))", gap:12 }}>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, borderColor:"#fecaca" }}
                  onClick={() => handleDeleteFolder(currentFolder?.path || currentFolderPath || '')}
                >
                  <div style={{ fontWeight:500, color:"#dc2626" }}>Delete Folder</div>
                  <div style={{ fontSize:"0.875rem", color:"#ef4444" }}>Delete this folder and all its contents</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8 }}
                  onClick={() => {
                    setParentFolderPath(currentFolder?.path || currentFolderPath || '');
                    setShowCreateModal(true);
                  }}
                >
                  <div style={{fontWeight:500}}>Create Subfolder</div>
                  <div  style={{fontSize:"0.875rem"}}>Create a new subfolder in the current folder</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8 }}
                  onClick={() => handleNavigateToUpload(currentFolder?.path || currentFolderPath || '')}
                >
                  <div style={{fontWeight:500}}>Upload</div>
                  <div  style={{fontSize:"0.875rem"}}>Upload files to this folder</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8 }}
                  onClick={() => handleNavigateToDocuments(currentFolder?.path || currentFolderPath || '')}
                >
                  <div style={{fontWeight:500}}>Documents</div>
                  <div  style={{fontSize:"0.875rem"}}>Browse documents in this folder</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, borderColor:"#bfdbfe" }}
                  onClick={() => handleEditFolder(currentFolder?.path || currentFolderPath || '')}
                >
                  <div style={{ fontWeight:500, color:"#2563eb" }}>Edit Folder</div>
                  <div style={{ fontSize:"0.875rem", color:"#3b82f6" }}>Edit folder name and description</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, borderColor:"#bbf7d0" }}
                  onClick={() => handleImportFolder(currentFolder?.path || currentFolderPath || '')}
                >
                  <div style={{ fontWeight:500, color:"#16a34a" }}>Import Folder</div>
                  <div style={{ fontSize:"0.875rem", color:"#22c55e" }}>Import an entire folder from local drive</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, borderColor:"#fde68a" }}
                  onClick={handleMoveFolder}
                >
                  <div  style={{ fontWeight:500 }}>Move Folder</div>
                  <div  style={{ fontSize:"0.875rem" }}>Move this folder to a different parent</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, borderColor:"#e9d5ff" }}
                  onClick={() => handleImportWebsite(currentFolder?.path || currentFolderPath || '')}
                >
                  <div style={{ fontWeight:500, color:"#9333ea" }}>Import Website</div>
                  <div  style={{ fontSize:"0.875rem" }}>Crawl web pages and images from a URL</div>
                </button>
                <button
                   style={{ padding:12, border:"1px solid #e5e7eb", borderRadius:8, borderColor:"#c7d2fe" }}
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
                  <div style={{ fontWeight:500, color:"#4f46e5" }}>Export to WebBot</div>
                  <div  style={{ fontSize:"0.875rem" }}>Export folder structure and pages to WebBot</div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Folder Content */}
        <div className="col-md-9">
          <div className="panel panel-success">
            <div className="panel-heading">
              {currentFolder ? (
                <details>
                  <summary>
                    <h3 className="panel-title">{currentFolder.name}</h3>
                  </summary>
                  <div className="small mrgn-tp-sm">
                    <p><strong>Path:</strong> <code>{currentFolder.path}</code></p>
                    <p><strong>Created:</strong> {new Date(currentFolder.created_at).toLocaleString()}</p>
                    {currentFolder.description && (
                      <p><strong>Description:</strong> {currentFolder.description}</p>
                    )}
                    {currentFolder.thumbnail_size && (
                      <p><strong>Thumbnail Size:</strong> <code>{currentFolder.thumbnail_size}</code></p>
                    )}
                  </div>
                </details>
              ) : (
                <h3 className="panel-title">Root</h3>
              )}
            </div>
            
            <div className="panel-body">
              {!currentFolder && documents.length === 0 ? (
                <div  style={{ paddingTop:32 }}>
                  <FolderIcon  style={{ width:64, height:64, color:"#d1d5db", marginBottom:16 }} />
                  <p>Select a folder from the left panel</p>
                </div>
              ) : (
                <>
                  {/* Documents */}
                  {documents.length > 0 && (
                    <div style={{  paddingTop:24 ,  marginBottom:24, borderTop:"1px solid #e5e7eb"  }}>
                      <div className="table-responsive" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                        <table className="fb-divide-y" style={{ minWidth:"100%", "--divide-color":"#e5e7eb" }}>
                          <thead style={{background:"#f9fafb"}}>
                            <tr>
                              <th  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Documents <span className="badge pull-right">{documents.length} <span className="wb-inv">Documents</span></span></th>
                              <th  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Actions</th>
                              <th  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Type</th>
                              <th  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Size</th>
                              <th  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Uploaded</th>
                              <th  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Status</th>
                            </tr>
                          </thead>
                          <tbody className="table">
                            {documents.map(doc => (
                              <tr key={doc.path || doc.storage_path || doc.name} className="fb-hover-btn">
                                <td style={{ paddingLeft:24, paddingTop:16 }}>
                                  <div>
                                    <div className="fb-label">{doc.title || doc.original_filename || 'Untitled'}</div>
                                    <div  style={{fontSize:"0.875rem"}}>{doc.original_filename}</div>
                                    {doc.folder_path && <div  style={{ fontSize:"0.75rem", color:"#9ca3af", fontFamily:"monospace" }}>{doc.folder_path}</div>}
                                  </div>
                                </td>
                                <td  style={{ paddingLeft:24, paddingTop:16, fontSize:"0.875rem", fontWeight:500 }}>
                                  <button 
                                    style={{  marginRight:12 ,  color:"#2563eb"  }}
                                    onClick={() => handlePreviewDocument(doc)}
                                  >
                                    Preview
                                  </button>
                                  <button type="button"
                                    style={{  marginRight:12 ,  color:"#059669", fontSize:"0.875rem", fontWeight:500, background:"transparent", border:"none"  }}
                                    onClick={() => handleWebbotPush(doc)}
                                    title="Import this page to WebBot"
                                  >
                                    WebBot
                                  </button>
                                  <button 
                                    className="fb-link" style={{color:"#2563eb"}}
                                    onClick={() => handleEditDocument(doc)}
                                  >
                                    Edit
                                  </button>
                                  <button 
                                    className="fb-link" style={{color: doc.publish_status === 'PUBLISHED' ? '#d97706' : '#059669', fontWeight: 500}}
                                    onClick={() => handleTogglePublish(doc)}
                                    title={doc.publish_status === 'PUBLISHED' ? 'Unpublish this document' : 'Publish this document'}
                                  >
                                    {doc.publish_status === 'PUBLISHED' ? 'Unpublish' : 'Publish'}
                                  </button>
                                  <button 
                                    className="fb-link" style={{color:"#dc2626"}}
                                    onClick={() => handleDeleteDocument(doc)}
                                  >
                                    Delete
                                  </button>
                                </td>
                                <td style={{ paddingLeft:24, paddingTop:16 }}>
                                  <span className="fb-align-center" style={{ display:"inline-flex", borderRadius:"50%", fontSize:"0.75rem", fontWeight:500, background:"#dbeafe", color:"#1e40af" }}>
                                    {doc.file_type || 'Unknown'}
                                  </span>
                                </td>
                                <td style={{ paddingLeft:24, paddingTop:16 }}>
                                  {doc.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(2)} MB` : 'Unknown'}
                                </td>
                                <td style={{ paddingLeft:24, paddingTop:16 }}>
                                  {doc.created_at ? new Date(doc.created_at).toLocaleString() : 'Unknown'}
                                </td>
                                <td style={{ paddingLeft:24, paddingTop:16 }}>
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
                    <div style={{  paddingTop:24 ,  marginBottom:24, borderTop:"1px solid #e5e7eb"  }}>
                      <h4 style={{ fontWeight:500, marginBottom:12 }}>Documents</h4>
                      <div  style={{ paddingTop:32, background:"#f9fafb", borderRadius:8 }}>
                        <DocumentIcon  style={{ width:64, height:64, color:"#d1d5db", marginBottom:16 }} />
                        <p>No documents in this folder</p>
                        <button 
                          style={{ marginTop:16, paddingLeft:16, paddingTop:8, background:"#2563eb", color:"#ffffff", borderRadius:4 }}
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
          folders={folders}
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
          folders={folders}
          mode="edit"
          folderToEdit={editingFolder}
        />
      )}
      
      {/* Export to WebBot Modal */}
      {showExportWebBotModal && (
        <div className="fb-align-start fb-justify-center" style={{  background:"rgba" ,  position:"fixed", top:0, background:"#000000", display:"flex", zIndex:50, overflowY:"auto", paddingTop:32  }}>
          <div style={{  boxShadow:"0 20px 25px -5px rgba(0,0,0,0.1)" ,  background:"#ffffff", borderRadius:8, width:"100%", maxWidth:768  }}>
            <div style={{padding:24}}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h3 style={{ fontSize:"1.125rem", fontWeight:500, color:"#3730a3" }}>Export to WebBot</h3>
                <button
                  onClick={() => setShowExportWebBotModal(false)}
                  style={{ color:"#9ca3af" }}
                >
                  ✕
                </button>
              </div>
              
              <div className="fb-space-y" style={{gap:16}}>
                <div style={{ background:"#f9fafb", padding:12, borderRadius:6 }}>
                  <p  style={{fontSize:"0.875rem"}}>
                    <strong>Folder:</strong> {currentFolderPath || 'Not selected'}
                  </p>
                </div>
                
                <div>
                  <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                    Export Depth (1-20)
                  </label>
                  <div className="fb-d-flex fb-align-center fb-gap-1">
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={exportDepth}
                      onChange={(e) => setExportDepth(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                       style={{ width:80, paddingLeft:12, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6 }}
                      disabled={exportingToWebBot}
                    />
                    <span  style={{fontSize:"0.875rem"}}>
                      depth 1 = current folder only
                    </span>
                  </div>
                </div>
                
                {exportError && (
                  <div style={{ background:"#fef2f2", border:"1px solid #e5e7eb", borderColor:"#fecaca", color:"#b91c1c", paddingLeft:16, paddingTop:12, borderRadius:6, fontSize:"0.875rem" }}>
                    {exportError}
                  </div>
                )}
                
                <button
                  onClick={handleExportToWebBot}
                  disabled={exportingToWebBot || !currentFolderPath}
                  style={{ width:"100%", paddingLeft:16, paddingTop:8, background:"#4f46e5", color:"#ffffff", borderRadius:6 }}
                >
                  {exportingToWebBot ? (
                    <span className="fb-align-center fb-justify-center" style={{ display:"flex" }}>
                      <svg className="-ml-1 fb-spinner" style={{ marginRight:8, height:16, width:16, color:"#ffffff" }} fill="none" viewBox="0 0 24 24">
                        <circle style={{ opacity:0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path style={{opacity:0.75}} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                      Exporting...
                    </span>
                  ) : (
                    '🚀 Export'
                  )}
                </button>
                
                {exportResult && (
                  <div style={{ marginTop:16, borderTop:"1px solid #e5e7eb", paddingTop:16 }}>
                    <div style={{ background:"#f0fdf4", border:"1px solid #e5e7eb", borderColor:"#bbf7d0", borderRadius:6, padding:12, marginBottom:12 }}>
                      <p style={{ fontSize:"0.875rem", color:"#166534" }}>
                        📄 <strong>Documents:</strong> {exportResult.documents ? exportResult.documents.length : (exportResult.document_count || 0)}
                        {(exportResult.subfolder_count > 0 || (exportResult.subfolders || []).length > 0) && (
                          <> &nbsp;|&nbsp; 📁 <strong>Subfolders:</strong> {(exportResult.subfolders || []).length}</>
                        )}
                      </p>
                    </div>

                    {/* Preview of exported documents */}
                    {(exportResult.documents || []).length > 0 && (
                      <div style={{marginBottom:12}}>
                        <h4 className="fb-label" style={{display:"block",marginBottom:8}}>
                          Documents ({exportResult.documents.length})
                        </h4>
                        <div  style={{ background:"#f9fafb", border:"1px solid #e5e7eb", borderColor:"#e5e7eb", borderRadius:6, padding:12, overflowY:"auto" }}>
                          {(exportResult.documents.slice(0, 10) || []).map((doc: any, i: number) => (
                            <div key={doc.path || i}  style={{ fontSize:"0.75rem", paddingTop:4, borderBottom:"1px solid #e5e7eb" }}>
                              <span style={{fontWeight:500}}>{doc.title || doc.path}</span>
                              <span style={{ color:"#9ca3af", marginLeft:8 }}>{doc.mime_type || ''}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Import to WebBot button */}
                    <button
                      onClick={handleImportToWebBot}
                      disabled={importingToWebBot || !exportResult}
                      style={{ width:"100%", paddingLeft:16, paddingTop:8, background:"#16a34a", color:"#ffffff", borderRadius:6 }}
                    >
                      {importingToWebBot ? (
                        <span className="fb-align-center fb-justify-center" style={{ display:"flex" }}>
                          <svg className="-ml-1 fb-spinner" style={{ marginRight:8, height:16, width:16, color:"#ffffff" }} fill="none" viewBox="0 0 24 24">
                            <circle style={{ opacity:0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                            <path style={{opacity:0.75}} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                          </svg>
                          Importing...
                        </span>
                      ) : (
                        '📥 Import to WebBot'
                      )}
                    </button>

                    {/* Import result display */}
                    {importResult && (
                      <div style={{ marginTop:12, background:"#eff6ff", border:"1px solid #e5e7eb", borderColor:"#bfdbfe", borderRadius:6, padding:12 }}>
                        <p style={{ fontSize:"0.875rem", color:"#1e40af" }}>
                          ✅ <strong>Import complete:</strong>{' '}
                          {importResult.inserted} new pages{' '}
                          {importResult.updated > 0 && <>+ {importResult.updated} updated{' '}</>}
                          in WebBot{' '}
                          {importResult.skipped > 0 && <span >({importResult.skipped} skipped)</span>}
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
        <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center">
          <div style={{  boxShadow:"0 20px 25px -5px rgba(0,0,0,0.1)" ,  background:"#ffffff", borderRadius:8, width:"100%", maxWidth:576  }}>
            <div style={{padding:24}}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h3  style={{ fontSize:"1.125rem", fontWeight:500 }}>Move Folder</h3>
                <button
                  onClick={() => setShowMoveFolderModal(false)}
                  style={{ color:"#9ca3af" }}
                >
                  ✕
                </button>
              </div>

              <div className="fb-space-y" style={{gap:16}}>
                <div style={{ background:"#f9fafb", padding:12, borderRadius:6 }}>
                  <p  style={{fontSize:"0.875rem"}}>
                    <strong>Moving:</strong> {currentFolder?.path || currentFolderPath}
                  </p>
                </div>

                <div>
                  <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                    Target Parent Folder Path
                  </label>
                  <input
                    type="text"
                    value={moveFolderTarget}
                    onChange={(e) => setMoveFolderTarget(e.target.value)}
                    placeholder="e.g. /boarding/canadasite/en/new-parent"
                     style={{ width:"100%", paddingLeft:12, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6 }}
                    disabled={moveFolderLoading}
                  />
                  <p style={{ fontSize:"0.75rem", color:"#9ca3af", marginTop:4 }}>
                    Enter the full path of the target parent folder
                  </p>
                </div>

                {moveFolderError && (
                  <div style={{ background:"#fef2f2", border:"1px solid #e5e7eb", borderColor:"#fecaca", color:"#b91c1c", paddingLeft:16, paddingTop:12, borderRadius:6, fontSize:"0.875rem" }}>
                    {moveFolderError}
                  </div>
                )}

                <div style={{ display:"flex", gap:8 }}>
                  <button
                    onClick={() => setShowMoveFolderModal(false)}
                    style={{ flex:1, paddingLeft:16, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", color:"#374151", borderRadius:6 }}
                    disabled={moveFolderLoading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleMoveFolderConfirm}
                    disabled={moveFolderLoading || !moveFolderTarget.trim()}
                    style={{ flex:1, paddingLeft:16, paddingTop:8, background:"#d97706", color:"#ffffff", borderRadius:6 }}
                  >
                    {moveFolderLoading ? (
                      <span className="fb-align-center fb-justify-center" style={{ display:"flex" }}>
                        <svg className="-ml-1 fb-spinner" style={{ marginRight:8, height:16, width:16, color:"#ffffff" }} fill="none" viewBox="0 0 24 24">
                          <circle style={{ opacity:0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                          <path style={{opacity:0.75}} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
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
        <div className="fb-modal-backdrop fb-d-flex fb-align-center fb-justify-center">
          <div style={{  boxShadow:"0 20px 25px -5px rgba(0,0,0,0.1)" ,  background:"#ffffff", borderRadius:8, width:"100%", maxWidth:576  }}>
            <div style={{padding:24}}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
                <h3 style={{ fontSize:"1.125rem", fontWeight:500, color:"#6b21a8" }}>Import Content</h3>
                <button
                  onClick={() => setShowImportWebsiteModal(false)}
                  style={{ color:"#9ca3af" }}
                >
                  ✕
                </button>
              </div>
              
              {/* Tab switcher */}
              <div style={{ display:"flex", borderBottom:"1px solid #e5e7eb", borderColor:"#e5e7eb", marginBottom:16 }}>
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
                <div className="fb-space-y" style={{gap:16}}>
                  <div>
                    <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                      Website URL
                    </label>
                    <input
                      type="url"
                      value={websiteUrl}
                      onChange={(e) => setWebsiteUrl(e.target.value)}
                      placeholder="https://example.com"
                       style={{ width:"100%", paddingLeft:12, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6 }}
                      disabled={importingWebsite}
                    />
                  </div>
                  
                  <div>
                    <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                      Crawl Depth
                    </label>
                    <div className="fb-d-flex fb-align-center fb-gap-1">
                      <input
                        type="range"
                        min="1"
                        max="5"
                        value={crawlDepth}
                        onChange={(e) => setCrawlDepth(parseInt(e.target.value))}
                        style={{flex:1}}
                        disabled={importingWebsite}
                      />
                      <span style={{ fontSize:"0.875rem", fontWeight:500, color:"#9333ea", width:32 }}>{crawlDepth}</span>
                    </div>
                    <div className="fb-justify-between" style={{ display:"flex", fontSize:"0.75rem", marginTop:4 }}>
                      <span>1 (Homepage only)</span>
                      <span>3</span>
                      <span>5 (Deep crawl)</span>
                    </div>
                    <p  style={{ fontSize:"0.875rem", marginTop:4 }}>
                      Depth {crawlDepth}: {getDepthDescription(crawlDepth)}
                    </p>
                  </div>
                  
                  <div className="checkbox" style={{marginBottom:12}}>
                    <label>
                      <input
                        type="checkbox"
                        checked={skipIfPageExists}
                        onChange={(e) => setSkipIfPageExists(e.target.checked)}
                        disabled={importingWebsite}
                      />{' '}
                      Skip if page exists
                    </label>
                  </div>
                  
                  <div style={{ background:"#f9fafb", padding:12, borderRadius:6 }}>
                    <p  style={{fontSize:"0.875rem"}}>
                      <strong>Target Folder:</strong> {currentFolder?.name || 'Not selected'} <br />
                      <strong>App:</strong> {app?.name || 'Unknown'}
                    </p>
                  </div>
                  
                  {importError && (
                    <div style={{ background:"#fef2f2", border:"1px solid #e5e7eb", borderColor:"#fecaca", borderRadius:6, padding:12 }}>
                      <p style={{fontSize:"0.875rem",color:"#b91c1c"}}>{importError}</p>
                    </div>
                  )}
                  
                  <div className="fb-justify-end" style={{ display:"flex", columnGap:12, paddingTop:16 }}>
                    <button
                      onClick={() => setShowImportWebsiteModal(false)}
                      style={{ paddingLeft:16, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6, color:"#374151" }}
                      disabled={importingWebsite}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitImportWebsite}
                      disabled={importingWebsite || !websiteUrl.trim()}
                      className="fb-align-center" style={{ paddingLeft:16, paddingTop:8, background:"#9333ea", color:"#ffffff", borderRadius:6, display:"flex" }}
                    >
                      {importingWebsite ? (
                        <>
                          <div className="fb-spinner" style={{ borderRadius:"50%", height:16, width:16, borderBottomWidth:2, marginRight:8 }}></div>
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
                <div className="fb-space-y" style={{gap:16}}>
                  <div>
                    <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                      Sitemap URL
                    </label>
                    <input
                      type="url"
                      value={sitemapUrl}
                      onChange={(e) => setSitemapUrl(e.target.value)}
                      placeholder="https://www.canada.ca/sitemap.xml"
                      style={{ width:"100%", paddingLeft:12, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6 }}
                      disabled={importingSitemap}
                    />
                    <p  style={{fontSize:"0.75rem",marginTop:4}}>
                      Enter a sitemap.xml URL to bulk-import all listed pages
                    </p>
                  </div>
                  
                  <div>
                    <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                      Recursion Depth
                    </label>
                    <select
                      value={sitemapDepth}
                      onChange={(e) => setSitemapDepth(parseInt(e.target.value))}
                      style={{ width:"100%", paddingLeft:12, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6 }}
                      disabled={importingSitemap}
                    >
                      <option value={0}>0 - Sitemap URLs only (no link tracking)</option>
                      <option value={1}>1 - Sitemap URLs + direct child links</option>
                      <option value={2}>2 - Sitemap URLs + 2 levels deep</option>
                    </select>
                    <p  style={{fontSize:"0.75rem",marginTop:4}}>
                      Recommended: depth = 0 (sitemaps already contain all desired URLs)
                    </p>
                  </div>
                  
                  <div style={{ background:"#f9fafb", padding:12, borderRadius:6 }}>
                    <p  style={{fontSize:"0.875rem"}}>
                      <strong>Target Folder:</strong> {currentFolder?.name || 'Not selected'} <br />
                      <strong>App:</strong> {app?.name || 'Unknown'}
                    </p>
                  </div>
                  
                  {importError && (
                    <div style={{ background:"#fef2f2", border:"1px solid #e5e7eb", borderColor:"#fecaca", borderRadius:6, padding:12 }}>
                      <p style={{fontSize:"0.875rem",color:"#b91c1c"}}>{importError}</p>
                    </div>
                  )}
                  
                  <div className="fb-justify-end" style={{ display:"flex", columnGap:12, paddingTop:16 }}>
                    <button
                      onClick={() => setShowImportWebsiteModal(false)}
                      style={{ paddingLeft:16, paddingTop:8, border:"1px solid #e5e7eb", borderColor:"#d1d5db", borderRadius:6, color:"#374151" }}
                      disabled={importingSitemap}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitImportSitemap}
                      disabled={importingSitemap || !sitemapUrl.trim()}
                      className="fb-align-center" style={{ paddingLeft:16, paddingTop:8, background:"#16a34a", color:"#ffffff", borderRadius:6, display:"flex" }}
                    >
                      {importingSitemap ? (
                        <>
                          <div className="fb-spinner" style={{ borderRadius:"50%", height:16, width:16, borderBottomWidth:2, marginRight:8 }}></div>
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

      {/* Edit Document Modal */}
      {showEditDocModal && editingDocument && (
        <div className="modal-overlay">
          <div className="modal-box" style={{ maxWidth: 520, margin: '60px auto' }}>
            <div className="panel panel-default" style={{ margin: 0 }}>
              <div className="panel-heading">
                <button className="close" onClick={() => { setShowEditDocModal(false); setEditingDocument(null); }}>&times;</button>
                <h3 className="panel-title">✏️ Edit Document</h3>
              </div>
              <div className="panel-body">
                <div className="form-group">
                  <label>Title</label>
                  <input type="text" className="form-control" style={{ display: 'block', width: '100%', boxSizing: 'border-box' }}
                    value={editDocTitle}
                    onChange={e => setEditDocTitle(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea className="form-control" rows={3} style={{ display: 'block', width: '100%', boxSizing: 'border-box' }}
                    value={editDocDescription}
                    onChange={e => setEditDocDescription(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Path</label>
                  <code className="form-control" style={{ display: 'block', wordBreak: 'break-all', height: 'auto', minHeight: 34 }}>
                    {editingDocument.path || editingDocument.storage_path || '-'}
                  </code>
                </div>
                <div className="form-group">
                  <label>Folder Path</label>
                  <code className="form-control" style={{ display: 'block', wordBreak: 'break-all', height: 'auto', minHeight: 34 }}>
                    {editingDocument.folder_path || editingDocument.parent_folder_path || '-'}
                  </code>
                </div>
              </div>
              <div className="panel-footer text-right">
                <button className="btn btn-default"
                  onClick={() => { setShowEditDocModal(false); setEditingDocument(null); }}
                  disabled={editDocSaving}>Cancel</button>
                <button className="btn btn-primary" style={{ marginLeft: 8 }}
                  onClick={handleSaveEditDoc}
                  disabled={editDocSaving || !editDocTitle.trim()}>
                  {editDocSaving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
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
