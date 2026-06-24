import React, { useState, useEffect } from 'react';
import documentService, { Document as ApiDocument } from '../services/document.service';
import featureService from '../services/feature.service';
import { Link } from 'react-router-dom';
import { generateDocumentSlug } from '../utils/slugUtils';

// 使用API的Document接口
type Document = ApiDocument;

const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchPath, setSearchPath] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<string>('all');
  const [edition, setEdition] = useState<string>('basic');

  useEffect(() => {
    fetchDocuments();
    checkAIStatus();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const searchParams: any = {};
      
      if (searchTerm) {
        searchParams.q = searchTerm;
      }
      
      if (searchPath) {
        searchParams.path = searchPath;
      }
      
      const data = await documentService.searchDocuments(searchParams);
      setDocuments(data || []);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkAIStatus = async () => {
    try {
      console.log('Checking AI classification status...');
      const enabled = await featureService.isAIClassificationEnabled();
      console.log('AI classification enabled:', enabled);
      setAiEnabled(enabled);
      
      // 获取当前版本
      const editionInfo = await featureService.getCurrentEdition();
      console.log('Current edition:', editionInfo);
      setEdition(editionInfo.edition);
    } catch (error) {
      console.error('Failed to check AI status:', error);
      setAiEnabled(false);
    }
  };

  const handleDelete = async (docPath: string) => {
    const targetDoc = documents.find(d => d.path === docPath);
    const docName = targetDoc?.original_filename || targetDoc?.title || 'this document';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\n存储路径: ${docPathStr}` : '';
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete "${docName}"?${docPathInfo}`);
    if (!confirmed) {
      return;
    }
    
    try {
      await documentService.deleteDocument(docPath);
      setDocuments(documents.filter(doc => doc.path !== docPath));
    } catch (error) {
      console.error('Failed to delete document:', error);
      window.showWetAlert('Failed to delete document. Please try again.');
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const docTitle = doc.title || doc.original_filename || '';
    const matchesSearch = docTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         doc.file_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFolder = selectedFolder === 'all' || 
                         (selectedFolder === 'uncategorized' && !doc.folder_path) ||
                         doc.folder_path === selectedFolder;
    return matchesSearch && matchesFolder;
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileIcon = (fileType: string): string => {
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('image')) return '🖼️';
    if (fileType.includes('text') || fileType.includes('document')) return '📝';
    if (fileType.includes('spreadsheet') || fileType.includes('excel')) return '📊';
    if (fileType.includes('presentation') || fileType.includes('powerpoint')) return '📽️';
    if (fileType.includes('zip') || fileType.includes('archive')) return '📦';
    return '📎';
  };

  const getAICategoryStyle = (category?: string): { backgroundColor: string; color: string } => {
    const colorMap: Record<string, { backgroundColor: string; color: string }> = {
      green: { backgroundColor: '#dcfce7', color: '#166534' },
      blue: { backgroundColor: '#dbeafe', color: '#1e40af' },
      purple: { backgroundColor: '#f3e8ff', color: '#6b21a8' },
      yellow: { backgroundColor: '#fef3c7', color: '#854d0e' },
      indigo: { backgroundColor: '#e0e7ff', color: '#3730a3' },
      pink: { backgroundColor: '#fce7f3', color: '#9d174d' },
      gray: { backgroundColor: '#f3f4f6', color: '#1f2937' },
    };
    const colors: Record<string, string> = {
      'INVOICE': 'green',
      'CONTRACT': 'blue',
      'REPORT': 'purple',
      'RESUME': 'yellow',
      'TECHNICAL': 'indigo',
      'ADMIN': 'pink',
      'GENERAL': 'gray'
    };
    
    const colorName = (category ? colors[category] : null) || 'gray';
    return colorMap[colorName];
  };

  const getAICategoryText = (category?: string) => {
    if (!category) return '未分类';
    
    const translations: Record<string, string> = {
      'INVOICE': '发票',
      'CONTRACT': '合同',
      'REPORT': '报告',
      'RESUME': '简历',
      'TECHNICAL': '技术文档',
      'ADMIN': '行政文档',
      'GENERAL': '通用文档'
    };
    
    return translations[category] || category;
  };

  const getClassificationStatusBadge = (status?: string, confidence?: number) => {
    if (!status || !aiEnabled) return null;
    
    const statusConfig: Record<string, { style: { backgroundColor: string; color: string }; text: string; icon: string }> = {
      'ai_classified': {
        style: { backgroundColor: '#dcfce7', color: '#166534' },
        text: 'AI已分类',
        icon: '🤖'
      },
      'needs_manual': {
        style: { backgroundColor: '#fef3c7', color: '#854d0e' },
        text: '待人工分类',
        icon: '👤'
      },
      'manual_classified': {
        style: { backgroundColor: '#dbeafe', color: '#1e40af' },
        text: '人工已分类',
        icon: '👤✓'
      },
      'review_needed': {
        style: { backgroundColor: '#ffedd5', color: '#9a3412' },
        text: '需审核',
        icon: '🔍'
      },
      'unclassified': {
        style: { backgroundColor: '#f3f4f6', color: '#1f2937' },
        text: '未分类',
        icon: '📄'
      }
    };
    
    const config = statusConfig[status.toLowerCase()] || statusConfig.unclassified;
    
    return (
      <div style={{marginTop:8}}>
        <span style={{paddingLeft:8,paddingRight:8,paddingTop:4,paddingBottom:4,borderRadius:9999,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...config.style}}>
          {config.icon} {config.text}
          {confidence !== undefined && ` (${Math.round(confidence * 100)}%)`}
        </span>
      </div>
    );
  };

  const getEditionBadge = () => {
    const editionConfig: Record<string, { color: string; text: string }> = {
      'basic': { color: 'bg-gray-100 text-gray-800', text: '基础版' },
      'professional': { color: 'bg-blue-100 text-blue-800', text: '专业版' },
      'enterprise': { color: 'bg-purple-100 text-purple-800', text: '企业版' }
    };
    
    const config = editionConfig[edition] || editionConfig.basic;
    
    return (
      <span style={{marginLeft:8,paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,borderRadius:9999,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...config.style}}>
        {config.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="fb-d-flex fb-align-center" style={{justifyContent:"center",height:256}}>
        <div className="text-muted">Loading documents...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:32}}>
        <div>
          <h1 style={{fontSize:"1.875rem",lineHeight:"2.25rem",fontWeight:700,color:"#1f2937"}}>Documents</h1>
          <div className="fb-d-flex fb-align-center" style={{marginTop:8}}>
            <span className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem"}}>
              {aiEnabled ? 'AI分类功能已启用' : '基础版本（无AI功能）'}
            </span>
            {getEditionBadge()}
          </div>
        </div>
        <Link
          to="/upload"
          className="fb-d-flex fb-align-center" style={{backgroundColor:"#2563eb",color:"#fff",paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,borderRadius:8}}
        >
          <svg style={{width:20,height:20,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Upload Document
        </Link>
      </div>

      {/* AI功能说明条 */}
      {!aiEnabled && (
        <div style={{backgroundColor:"#fffbeb",borderLeftWidth:4,borderColor:"#facc15",padding:16,marginBottom:32}}>
          <div className="fb-d-flex">
            <div style={{flexShrink:0}}>
              <svg style={{height:20,width:20,color:"#facc15"}} viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div style={{marginLeft:12}}>
              <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#a16207"}}>
                当前为<strong>基础版本</strong>，不包含AI分类功能。
                {edition === 'basic' && ' 如需AI功能，请升级到专业版或企业版。'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <div style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:24,marginBottom:32}}>
        <div style={{display:"grid",gridTemplateColumns:"repeat(1, 1fr)",gap:16}}>
          <div>
            <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
              Search Documents
            </label>
            <div style={{position:"relative"}}>
              <input
                type="text"
                placeholder="Search by name or type..."
                style={{width:"100%",paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:8}}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <svg style={{width:20,height:20,color:"#9ca3af",position:"absolute",right:12,top:10}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
          
          <div>
            <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
              Filter by Folder
            </label>
            <select
              style={{width:"100%",paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:8}}
              value={selectedFolder}
              onChange={(e) => setSelectedFolder(e.target.value)}
            >
              <option value="all">All Folders</option>
              <option value="uncategorized">Uncategorized</option>
              {/* In a real app, you would map through folders here */}
            </select>
          </div>
          
          <div>
            <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:8}}>
              Search by Path
            </label>
            <div style={{position:"relative"}}>
              <input
                type="text"
                placeholder="Search by path (e.g., /content/dam/...)"
                style={{width:"100%",paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:8}}
                value={searchPath}
                onChange={(e) => setSearchPath(e.target.value)}
              />
            </div>
          </div>
          
          <div className="fb-d-flex" style={{alignItems:"flex-end"}}>
            <button
              onClick={fetchDocuments}
              className="fb-d-flex fb-align-center" style={{width:"100%",backgroundColor:"#e5e7eb",color:"#374151",paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,borderRadius:8,justifyContent:"center"}}
            >
              <svg style={{width:20,height:20,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Documents Grid */}
      {filteredDocuments.length > 0 ? (
        <div style={{display:"grid",gridTemplateColumns:"repeat(1, 1fr)",gap:24}}>
          {filteredDocuments.map((doc) => (
            <div key={doc.path || doc.storage_path || doc.name} style={{transitionProperty:"box-shadow",backgroundColor:"#fff",borderRadius:8,boxShadow:"0 10px 15px -3px rgba(0,0,0,0.1)",transitionDuration:"300ms"}}>
              <div style={{padding:24}}>
                <div className="fb-d-flex fb-justify-between fb-align-start" style={{marginBottom:16}}>
                  <div style={{fontSize:"1.875rem",lineHeight:"2.25rem"}}>{getFileIcon(doc.file_type)}</div>
                  <div className="fb-d-flex" style={{display:"flex",gap:8}}>
                    <Link
                      to={`/documents/${(doc.path || doc.storage_path || doc.id).replace(/^\//, '')}`}
                      style={{color:"#1e40af"}}
                      title="View Details"
                    >
                      <svg style={{width:20,height:20}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </Link>
                    <button
                      onClick={() => handleDelete(doc.path)}
                      style={{color:"#991b1b"}}
                      title="Delete"
                    >
                      <svg style={{width:20,height:20}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                <h3 style={{fontSize:"1.125rem",lineHeight:"1.75rem",fontWeight:600,color:"#1f2937",marginBottom:8,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                  {doc.title || doc.original_filename}
                </h3>
                
                <div className="text-muted" style={{display:"flex",flexDirection:"column",gap:8,fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                  <div className="fb-d-flex fb-align-center">
                    <svg style={{width:16,height:16,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Type: {doc.file_type}</span>
                  </div>
                  
                  <div className="fb-d-flex fb-align-center">
                    <svg style={{width:16,height:16,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                    </svg>
                    <span>Size: {formatFileSize(doc.file_size)}</span>
                  </div>
                  
                  <div className="fb-d-flex fb-align-center">
                    <svg style={{width:16,height:16,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span>Uploaded: {formatDate(doc.created_at)}</span>
                  </div>
                  
                  {/* AI分类信息（仅当启用时显示） */}
                  {aiEnabled && doc.ai_category && (
                    <div style={{borderColor:"#f3f4f6",marginTop:12,paddingTop:12,borderTop:"1px solid #e5e7eb"}}>
                      <div className="fb-d-flex fb-align-center" style={{marginBottom:4}}>
                        <svg style={{color:"#9333ea",width:16,height:16,marginRight:8}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <span style={{color:"#7e22ce",fontWeight:500}}>AI分类</span>
                      </div>
                      <div className="fb-d-flex fb-align-center fb-justify-between">
                        <span style={{paddingLeft:8,paddingRight:8,paddingTop:4,paddingBottom:4,borderRadius:4,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...getAICategoryStyle(doc.ai_category)}}>
                          {getAICategoryText(doc.ai_category)}
                        </span>
                        {doc.ai_confidence && (
                          <span className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem"}}>
                            置信度: {Math.round(doc.ai_confidence * 100)}%
                          </span>
                        )}
                      </div>
                      {getClassificationStatusBadge(doc.classification_status, doc.ai_confidence)}
                    </div>
                  )}
                </div>
                
                <div style={{borderColor:"#f3f4f6",marginTop:24,paddingTop:16,borderTop:"1px solid #e5e7eb"}}>
                  <div className="fb-d-flex fb-justify-between">
                    <Link
                      to={`/documents/${(doc.path || doc.storage_path || doc.id).replace(/^\//, '')}`}
                      style={{color:"#1e40af",fontWeight:500}}
                    >
                      View Details →
                    </Link>
                    <span style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,borderRadius:9999,fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,...(doc.folder_path ? {backgroundColor:'#dcfce7',color:'#166534'} : {backgroundColor:'#f3f4f6',color:'#1f2937'})}}>
                      {doc.folder_path ? 'In Folder' : 'Uncategorized'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center" style={{backgroundColor:"#fff",borderRadius:8,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",padding:48}}>
          <div style={{fontSize:"3.75rem",lineHeight:1,marginBottom:24}}>📁</div>
          <h3 style={{fontSize:"1.5rem",lineHeight:"2rem",fontWeight:700,color:"#1f2937",marginBottom:16}}>
            {searchTerm || selectedFolder !== 'all' 
              ? 'No matching documents found' 
              : 'No documents yet'}
          </h3>
          <p className="text-muted" style={{marginBottom:32,maxWidth:448,marginLeft:"auto",marginRight:"auto"}}>
            {searchTerm || selectedFolder !== 'all'
              ? 'Try adjusting your search terms or filters to find what you\'re looking for.'
              : 'Start by uploading your first document to manage it in FileBot.'}
          </p>
          <Link
            to="/upload"
            style={{display:"inline-block",backgroundColor:"#2563eb",color:"#fff",paddingLeft:32,paddingRight:32,paddingTop:12,paddingBottom:12,borderRadius:8,fontWeight:500}}
          >
            Upload Your First Document
          </Link>
        </div>
      )}
      
      {/* Document Count */}
      <div className="text-center text-muted" style={{marginTop:32}}>
        Showing {filteredDocuments.length} of {documents.length} documents
        {aiEnabled && ' • AI classification enabled'}
      </div>
    </div>
  );
};

export default Documents;