import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import documentService, { Document } from '../services/document.service';
import folderService, { Folder } from '../services/folder.service';
import appService, { App } from '../services/app.service';

const ClientDocumentDetail: React.FC = () => {
  // Get identifier from URL (supports UUID and path)
  const splat = useParams()['*'] || '';
  const identifier = splat.startsWith('/') ? splat : '/' + splat;
  
  const navigate = useNavigate();
  
  const [document, setDocument] = useState<Document | null>(null);
  const [folder, setFolder] = useState<Folder | null>(null);
  const [app, setApp] = useState<App | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [htmlContentUrl, setHtmlContentUrl] = useState<string | null>(null);

  // Parse document identifier
  const getDocIdentifier = (): string => {
    // Remove the leading / from UUID
    const uuidPattern = /^\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    if (uuidPattern.test(identifier)) {
      return identifier.slice(1);
    }
    return identifier;
  };

  const docIdentifier = getDocIdentifier();

  useEffect(() => {
    const fetchDocument = async () => {
      if (!docIdentifier) {
        setError('Invalid document identifier');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        const data = await documentService.getDocumentByIdentifier(docIdentifier);
        setDocument(data);
        
        // Get folder and app info (prefer path)
        const folderIdentifier = data.folder_path || data.folder_id;
        if (folderIdentifier) {
          try {
            const folderData = await folderService.getFolder(folderIdentifier);
            setFolder(folderData);
            
            if (folderData.app_id) {
              const apps = await appService.getApps();
              const appData = apps.find((a: App) => a.id === folderData.app_id);
              if (appData) setApp(appData);
            }
          } catch (folderErr) {
            console.warn('Failed to get folder info:', folderErr);
          }
        }
      } catch (err: any) {
        console.error('Failed to fetch document details:', err);
        setError(err.message || 'Failed to load document');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [docIdentifier]);

  // Handle HTML preview content loading
  useEffect(() => {
    let currentBlobUrl: string | null = null;
    
    const loadHtmlContent = async () => {
      if (!document || document.file_type.toLowerCase() !== 'html') {
        return;
      }

      // If there's already a content URL, release it first
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
        currentBlobUrl = null;
      }
      
      if (htmlContentUrl) {
        setHtmlContentUrl(null);
      }

      setPreviewLoading(true);
      
      try {
        const docApiId = document.path || document.storage_path || document.id;
        const blob = await documentService.downloadDocument(docApiId, 'original');
        
        if (blob.size === 0) {
          const emptyHtml = '<html><body><h3>File is empty</h3></body></html>';
          const emptyBlob = new Blob([emptyHtml], { type: 'text/html' });
          const url = URL.createObjectURL(emptyBlob);
          currentBlobUrl = url;
          setHtmlContentUrl(url);
        } else {
          const url = URL.createObjectURL(blob);
          currentBlobUrl = url;
          setHtmlContentUrl(url);
        }
      } catch (error: any) {
        console.error('Failed to load HTML preview content:', error);
        const errorHtml = `<html><body>
          <h3 style="color: #d32f2f;">Failed to load HTML preview</h3>
          <p>Error: ${error.message || 'Unknown error'}</p>
        </body></html>`;
        const errorBlob = new Blob([errorHtml], { type: 'text/html' });
        const url = URL.createObjectURL(errorBlob);
        currentBlobUrl = url;
        setHtmlContentUrl(url);
      } finally {
        setPreviewLoading(false);
      }
    };

    loadHtmlContent();

    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [document]);

  const handleDownload = async (downloadType: 'original' | 'pdf' = 'original') => {
    if (!document) return;
    
    try {
      const docApiId = document.path || document.storage_path || document.id;
      const blob = await documentService.downloadDocument(docApiId, downloadType);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = `${document.original_filename}${downloadType === 'pdf' ? '.pdf' : ''}`;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (err: any) {
      console.error('Download failed:', err);
      window.showWetAlert('Download failed: ' + err.message);
    }
  };

  const handleBack = () => {
    if (folder && app) {
      navigate(`/apps/${app.slug || app.id}/folders/${encodeURIComponent(folder.path)}/documents`);
    } else {
      navigate('/apps');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
        <div className="max-w-4xl mx-auto text-center py-16">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading document details...</p>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <h2 className="text-2xl font-bold text-red-600 mb-4">Load failed</h2>
            <p className="text-gray-700 mb-6">{error || 'Document not found'}</p>
            <button
              onClick={handleBack}
              className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Back to document list
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isHtmlFile = document.file_type.toLowerCase() === 'html';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Breadcrumb navigation */}
        <div className="mb-6">
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-4">
            <Link to="/apps" className="hover:text-blue-600">App list</Link>
            <span>›</span>
            {app && (
              <>
                <Link to={`/apps/${app.slug || app.id}`} className="hover:text-blue-600">
                  {app.name}
                </Link>
                <span>›</span>
              </>
            )}
            {folder && (
              <>
                <Link 
                  to={`/apps/${app?.slug || app?.id}/folders/${encodeURIComponent(folder.path)}/documents`} 
                  className="hover:text-blue-600"
                >
                  {folder.name}
                </Link>
                <span>›</span>
              </>
            )}
            <span className="text-gray-700">{document.original_filename}</span>
          </div>
        </div>

        {/* Title and action buttons */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{document.original_filename}</h1>
              <div className="flex items-center space-x-3 mt-3">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {document.file_type.toUpperCase()}
                </span>
                <span className="text-gray-600">
                  Size: {formatFileSize(document.file_size)}
                </span>
                <span className="text-gray-600">
                  Uploaded: {new Date(document.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleBack}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={() => handleDownload('original')}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Download
              </button>
            </div>
          </div>
        </div>

        {/* Document preview area */}
        {isHtmlFile ? (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-800">HTML Preview</h2>
            </div>
            <div className="p-6">
              {previewLoading ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="mt-3 text-gray-600">Loading HTML content...</p>
                </div>
              ) : htmlContentUrl ? (
                <div className="border border-gray-300 rounded-lg overflow-hidden">
                  <iframe
                    src={htmlContentUrl}
                    title={document.original_filename}
                    className="w-full h-[600px] border-0"
                    sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                  />
                  <div className="p-4 border-t border-gray-200 text-center">
                    <button
                      onClick={() => handleDownload('original')}
                      className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Download HTML file
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-600">Unable to load HTML preview</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <div className="text-gray-400 mb-6">
              <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              File type preview not available
            </h3>
            <p className="text-gray-500 mb-6">
              Preview for {document.file_type.toUpperCase()} files is under development.
              You can download the file to view it locally.
            </p>
            <button
              onClick={() => handleDownload('original')}
              className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Download {document.file_type.toUpperCase()} file
            </button>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>FileBot Client Portal • Document Details • {document.original_filename}</p>
        </footer>
      </div>
    </div>
  );
};

export default ClientDocumentDetail;