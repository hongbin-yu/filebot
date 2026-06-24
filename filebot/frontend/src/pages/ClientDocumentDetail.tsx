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
      <div className="fb-page-bg" style={{padding:24}}>
        <div className="container" style={{textAlign:"center",paddingTop:64,paddingBottom:64}}>
          <div className="fb-spinner"></div>
          <p className="text-muted" style={{marginTop:16}}>Loading document details...</p>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="fb-page-bg" style={{padding:24}}>
        <div className="container">
          <div className="panel panel-default" style={{padding:32,textAlign:"center",borderRadius:12}}>
            <h2 style={{fontSize:"1.5rem",fontWeight:700,color:"#dc2626",marginBottom:16}}>Load failed</h2>
            <p style={{color:"#374151",marginBottom:24}}>{error || 'Document not found'}</p>
            <button
              onClick={handleBack}
              className="btn btn-primary"
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
    <div className="fb-page-bg" style={{padding:24}}>
      <div className="container">
        {/* Breadcrumb navigation */}
        <div style={{marginBottom:24}}>
          <div className="fb-d-flex fb-align-center fb-gap-1 small text-muted" style={{marginBottom:16}}>
            <Link to="/apps" className="fb-link">App list</Link>
            <span>›</span>
            {app && (
              <>
                <Link to={`/apps/${app.slug || app.id}`} className="fb-link">
                  {app.name}
                </Link>
                <span>›</span>
              </>
            )}
            {folder && (
              <>
                <Link 
                  to={`/apps/${app?.slug || app?.id}/folders/${encodeURIComponent(folder.path)}/documents`} 
                  className="fb-link"
                >
                  {folder.name}
                </Link>
                <span>›</span>
              </>
            )}
            <span style={{color:"#374151"}}>{document.original_filename}</span>
          </div>
        </div>

        {/* Title and action buttons */}
        <div className="panel panel-default" style={{padding:24,marginBottom:24,borderRadius:12}}>
          <div className="fb-d-flex fb-justify-between fb-align-start">
            <div>
              <h1 style={{fontSize:"1.875rem",fontWeight:700,color:"#1f2937"}}>{document.original_filename}</h1>
              <div className="fb-d-flex fb-align-center fb-gap-2" style={{marginTop:12}}>
                <span className="label label-info" style={{borderRadius:9999}}>
                  {document.file_type.toUpperCase()}
                </span>
                <span className="text-muted">
                  Size: {formatFileSize(document.file_size)}
                </span>
                <span className="text-muted">
                  Uploaded: {new Date(document.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="fb-d-flex fb-gap-2">
              <button
                onClick={handleBack}
                className="btn btn-default"
              >
                Back
              </button>
              <button
                onClick={() => handleDownload('original')}
                className="btn btn-primary"
              >
                Download
              </button>
            </div>
          </div>
        </div>

        {/* Document preview area */}
        {isHtmlFile ? (
          <div className="panel panel-default" style={{borderRadius:12,overflow:"hidden"}}>
            <div style={{padding:24,borderBottom:"1px solid #e5e7eb"}}>
              <h2 style={{fontSize:"1.25rem",fontWeight:700,color:"#1f2937"}}>HTML Preview</h2>
            </div>
            <div style={{padding:24}}>
              {previewLoading ? (
                <div style={{textAlign:"center",paddingTop:48,paddingBottom:48}}>
                  <div className="fb-spinner" style={{width:32,height:32}}></div>
                  <p className="text-muted" style={{marginTop:12}}>Loading HTML content...</p>
                </div>
              ) : htmlContentUrl ? (
                <div style={{border:"1px solid #d1d5db",borderRadius:8,overflow:"hidden"}}>
                  <iframe
                    src={htmlContentUrl}
                    title={document.original_filename}
                    style={{width:"100%",height:600,border:0}}
                    sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                  />
                  <div style={{padding:16,borderTop:"1px solid #e5e7eb",textAlign:"center"}}>
                    <button
                      onClick={() => handleDownload('original')}
                      className="btn btn-primary"
                    >
                      Download HTML file
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{textAlign:"center",paddingTop:48,paddingBottom:48}}>
                  <p className="text-muted">Unable to load HTML preview</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="btn btn-default" style={{marginTop:16}}
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="panel panel-default" style={{padding:32,textAlign:"center",borderRadius:12}}>
            <div className="text-muted" style={{marginBottom:24}}>
              <svg style={{width:96,height:96,margin:"0 auto"}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <h3 style={{fontSize:"1.25rem",fontWeight:500,color:"#111827",marginBottom:8}}>
              File type preview not available
            </h3>
            <p className="text-muted" style={{marginBottom:24}}>
              Preview for {document.file_type.toUpperCase()} files is under development.
              You can download the file to view it locally.
            </p>
            <button
              onClick={() => handleDownload('original')}
              className="btn btn-primary"
            >
              Download {document.file_type.toUpperCase()} file
            </button>
          </div>
        )}

        {/* Footer */}
        <footer style={{marginTop:48,paddingTop:32,borderTop:"1px solid #e5e7eb",textAlign:"center",fontSize:"0.875rem"}} className="text-muted">
          <p>FileBot Client Portal • Document Details • {document.original_filename}</p>
        </footer>
      </div>
    </div>
  );
};

export default ClientDocumentDetail;