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

  const handleDelete = async (id: string) => {
    const targetDoc = documents.find(d => d.id === id);
    const docName = targetDoc?.original_filename || targetDoc?.title || 'this document';
    const docPathStr = targetDoc?.storage_path || targetDoc?.path || '';
    const docPathInfo = docPathStr ? `\n存储路径: ${docPathStr}` : '';
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete "${docName}"?${docPathInfo}`);
    if (!confirmed) {
      return;
    }
    
    try {
      await documentService.deleteDocument(id);
      setDocuments(documents.filter(doc => doc.id !== id));
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
                         (selectedFolder === 'uncategorized' && !doc.folder_id) ||
                         doc.folder_id === selectedFolder;
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

  const getAICategoryColor = (category?: string) => {
    if (!category) return 'gray';
    
    const colors: Record<string, string> = {
      'INVOICE': 'green',
      'CONTRACT': 'blue',
      'REPORT': 'purple',
      'RESUME': 'yellow',
      'TECHNICAL': 'indigo',
      'ADMIN': 'pink',
      'GENERAL': 'gray'
    };
    
    return colors[category] || 'gray';
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
    
    const statusConfig: Record<string, { color: string; text: string; icon: string }> = {
      'ai_classified': {
        color: 'bg-green-100 text-green-800',
        text: 'AI已分类',
        icon: '🤖'
      },
      'needs_manual': {
        color: 'bg-yellow-100 text-yellow-800',
        text: '待人工分类',
        icon: '👤'
      },
      'manual_classified': {
        color: 'bg-blue-100 text-blue-800',
        text: '人工已分类',
        icon: '👤✓'
      },
      'review_needed': {
        color: 'bg-orange-100 text-orange-800',
        text: '需审核',
        icon: '🔍'
      },
      'unclassified': {
        color: 'bg-gray-100 text-gray-800',
        text: '未分类',
        icon: '📄'
      }
    };
    
    const config = statusConfig[status.toLowerCase()] || statusConfig.unclassified;
    
    return (
      <div className="mt-2">
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
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
      <span className={`ml-2 px-3 py-1 rounded-full text-xs font-medium ${config.color}`}>
        {config.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading documents...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Documents</h1>
          <div className="mt-2 flex items-center">
            <span className="text-sm text-gray-600">
              {aiEnabled ? 'AI分类功能已启用' : '基础版本（无AI功能）'}
            </span>
            {getEditionBadge()}
          </div>
        </div>
        <Link
          to="/upload"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 flex items-center"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Upload Document
        </Link>
      </div>

      {/* AI功能说明条 */}
      {!aiEnabled && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-8">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">
                当前为<strong>基础版本</strong>，不包含AI分类功能。
                {edition === 'basic' && ' 如需AI功能，请升级到专业版或企业版。'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Documents
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Search by name or type..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <svg className="w-5 h-5 text-gray-400 absolute right-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Folder
            </label>
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedFolder}
              onChange={(e) => setSelectedFolder(e.target.value)}
            >
              <option value="all">All Folders</option>
              <option value="uncategorized">Uncategorized</option>
              {/* In a real app, you would map through folders here */}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search by Path
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Search by path (e.g., /content/dam/...)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={searchPath}
                onChange={(e) => setSearchPath(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex items-end">
            <button
              onClick={fetchDocuments}
              className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 flex items-center justify-center"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Documents Grid */}
      {filteredDocuments.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocuments.map((doc) => (
            <div key={doc.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow duration-300">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className="text-3xl">{getFileIcon(doc.file_type)}</div>
                  <div className="flex space-x-2">
                    <Link
                      to={`/documents/${(doc.path || doc.storage_path || doc.id).replace(/^\//, '')}`}
                      className="text-blue-600 hover:text-blue-800"
                      title="View Details"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </Link>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-600 hover:text-red-800"
                      title="Delete"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                <h3 className="text-lg font-semibold text-gray-800 mb-2 truncate">
                  {doc.title || doc.original_filename}
                </h3>
                
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Type: {doc.file_type}</span>
                  </div>
                  
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                    </svg>
                    <span>Size: {formatFileSize(doc.file_size)}</span>
                  </div>
                  
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span>Uploaded: {formatDate(doc.created_at)}</span>
                  </div>
                  
                  {/* AI分类信息（仅当启用时显示） */}
                  {aiEnabled && doc.ai_category && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="flex items-center mb-1">
                        <svg className="w-4 h-4 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <span className="font-medium text-purple-700">AI分类</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={`px-2 py-1 rounded text-xs font-medium bg-${getAICategoryColor(doc.ai_category)}-100 text-${getAICategoryColor(doc.ai_category)}-800`}>
                          {getAICategoryText(doc.ai_category)}
                        </span>
                        {doc.ai_confidence && (
                          <span className="text-xs text-gray-500">
                            置信度: {Math.round(doc.ai_confidence * 100)}%
                          </span>
                        )}
                      </div>
                      {getClassificationStatusBadge(doc.classification_status, doc.ai_confidence)}
                    </div>
                  )}
                </div>
                
                <div className="mt-6 pt-4 border-t border-gray-100">
                  <div className="flex justify-between">
                    <Link
                      to={`/documents/${(doc.path || doc.storage_path || doc.id).replace(/^\//, '')}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View Details →
                    </Link>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      doc.folder_id ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {doc.folder_id ? 'In Folder' : 'Uncategorized'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-6xl mb-6">📁</div>
          <h3 className="text-2xl font-bold text-gray-800 mb-4">
            {searchTerm || selectedFolder !== 'all' 
              ? 'No matching documents found' 
              : 'No documents yet'}
          </h3>
          <p className="text-gray-600 mb-8 max-w-md mx-auto">
            {searchTerm || selectedFolder !== 'all'
              ? 'Try adjusting your search terms or filters to find what you\'re looking for.'
              : 'Start by uploading your first document to manage it in FileBot.'}
          </p>
          <Link
            to="/upload"
            className="inline-block bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 font-medium"
          >
            Upload Your First Document
          </Link>
        </div>
      )}
      
      {/* Document Count */}
      <div className="mt-8 text-center text-gray-600">
        Showing {filteredDocuments.length} of {documents.length} documents
        {aiEnabled && ' • AI classification enabled'}
      </div>
    </div>
  );
};

export default Documents;