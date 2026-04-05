import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import documentService from '../services/document.service';
import folderService from '../services/folder.service';
import appService from '../services/app.service';
import { useNavigate } from 'react-router-dom';

interface Folder {
  id: number;
  name: string;
}

const Upload: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [folders, setFolders] = useState<Folder[]>([]);
  const [tags, setTags] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [errors, setErrors] = useState<string[]>([]);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const navigate = useNavigate();

  React.useEffect(() => {
    fetchFolders();
  }, []);

  const fetchFolders = async () => {
    try {
      let data: any[] = [];
      // 获取默认应用和抽屉的文件夹
      const apps = await appService.getApps();
      if (apps && apps.length > 0) {
        const firstApp = apps[0];
        const drawers = await appService.getAppDrawers(firstApp.id);
        if (drawers && drawers.length > 0) {
          const firstDrawer = drawers[0];
          data = await folderService.getFolders(firstApp.id, firstDrawer.id);
        }
      }
      setFolders(data || []);
    } catch (error) {
      console.error('Failed to fetch folders:', error);
      setFolders([]);
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setErrors([]);
    setSuccessMessage('');
    
    // Validate files
    const validFiles = acceptedFiles.filter(file => {
      // Check file size (max 100MB)
      if (file.size > 100 * 1024 * 1024) {
        setErrors(prev => [...prev, `${file.name} exceeds 100MB limit`]);
        return false;
      }
      
      // Check file type
      const allowedTypes = [
        'application/pdf',
        'image/jpeg', 'image/png', 'image/gif',
        'text/plain', 'text/csv',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip',
        'application/x-zip-compressed',
        'application/x-rar-compressed'
      ];
      
      if (!allowedTypes.some(type => file.type.includes(type.replace('*', '')))) {
        setErrors(prev => [...prev, `${file.name} has unsupported file type: ${file.type}`]);
        return false;
      }
      
      return true;
    });
    
    setFiles(prev => [...prev, ...validFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setErrors(['Please select at least one file to upload']);
      return;
    }

    setUploading(true);
    setErrors([]);
    setSuccessMessage('');
    
    const totalFiles = files.length;
    
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const progressValue = Math.round((i / totalFiles) * 100);
        setProgress(progressValue);
        
        try {
          // Prepare form data
          const formData = new FormData();
          formData.append('file', file);
          
          if (selectedFolder) {
            formData.append('folder_id', selectedFolder);
          }
          
          if (tags) {
            const tagList = tags.split(',').map(tag => tag.trim()).filter(tag => tag);
            formData.append('tags', JSON.stringify(tagList));
          }
          
          if (description) {
            formData.append('description', description);
          }
          
          // Upload file
          await documentService.uploadDocument({
            file,
            folder_id: selectedFolder || '',
            title: undefined,
            description: description || undefined,
            document_type: undefined
          });
          
          // Update progress
          const newProgress = Math.round(((i + 1) / totalFiles) * 100);
          setProgress(newProgress);
          
        } catch (error: any) {
          console.error(`Failed to upload ${file.name}:`, error);
          setErrors(prev => [...prev, `${file.name}: ${error.message || 'Upload failed'}`]);
        }
      }
      
      setProgress(100);
      
      if (errors.length === 0) {
        setSuccessMessage(`Successfully uploaded ${files.length} file(s)`);
        setTimeout(() => {
          setFiles([]);
          setProgress(0);
          setSelectedFolder('');
          setTags('');
          setDescription('');
          navigate('/documents');
        }, 2000);
      } else {
        setSuccessMessage(`Uploaded ${files.length - errors.length} of ${files.length} files`);
      }
      
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (file: File): string => {
    const type = file.type;
    if (type.includes('pdf')) return '📄';
    if (type.includes('image')) return '🖼️';
    if (type.includes('text') || type.includes('document')) return '📝';
    if (type.includes('spreadsheet') || type.includes('excel')) return '📊';
    if (type.includes('presentation') || type.includes('powerpoint')) return '📽️';
    if (type.includes('zip') || type.includes('archive')) return '📦';
    return '📎';
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">Upload Documents</h1>
      
      {/* Upload Zone */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors duration-300 ${
            isDragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />
          
          <div className="text-6xl mb-6">📤</div>
          <h3 className="text-2xl font-bold text-gray-800 mb-4">
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </h3>
          <p className="text-gray-600 mb-6">
            or click to select files from your computer
          </p>
          <button className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 font-medium">
            Select Files
          </button>
          <p className="text-sm text-gray-500 mt-4">
            Supports PDF, Images, Documents, Spreadsheets, Presentations, and Archives (max 100MB each)
          </p>
        </div>
      </div>

      {/* Selected Files */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-xl font-bold text-gray-800 mb-4">
            Selected Files ({files.length})
          </h3>
          
          <div className="space-y-4">
            {files.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center">
                  <span className="text-2xl mr-4">{getFileIcon(file)}</span>
                  <div>
                    <h4 className="font-medium text-gray-800">{file.name}</h4>
                    <p className="text-sm text-gray-600">
                      {formatFileSize(file.size)} • {file.type}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="text-red-600 hover:text-red-800"
                  disabled={uploading}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
          
          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex justify-between items-center">
              <span className="text-gray-700">Total size:</span>
              <span className="font-semibold">
                {formatFileSize(files.reduce((total, file) => total + file.size, 0))}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Upload Options */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h3 className="text-xl font-bold text-gray-800 mb-6">Upload Options</h3>
        
        <div className="space-y-6">
          {/* Folder Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Folder (Optional)
            </label>
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedFolder}
              onChange={(e) => setSelectedFolder(e.target.value)}
              disabled={uploading}
            >
              <option value="">No Folder (Uncategorized)</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id.toString()}>
                  {folder.name}
                </option>
              ))}
            </select>
            <p className="text-sm text-gray-500 mt-1">
              Organize your documents by selecting an existing folder
            </p>
          </div>
          
          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags (Optional)
            </label>
            <input
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., invoice, report, 2024"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              disabled={uploading}
            />
            <p className="text-sm text-gray-500 mt-1">
              Separate tags with commas for easy searching
            </p>
          </div>
          
          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description (Optional)
            </label>
            <textarea
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={3}
              placeholder="Add a description for these files..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={uploading}
            />
          </div>
        </div>
      </div>

      {/* Progress and Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        {uploading && (
          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">Upload Progress</span>
              <span className="text-sm font-semibold text-blue-600">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Error Messages */}
        {errors.length > 0 && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="font-medium text-red-800 mb-2">Upload Errors:</h4>
            <ul className="text-sm text-red-700 list-disc list-inside">
              {errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-green-800 font-medium">{successMessage}</span>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-between">
          <button
            onClick={() => navigate('/documents')}
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            disabled={uploading}
          >
            Cancel
          </button>
          
          <div className="flex space-x-4">
            {files.length > 0 && !uploading && (
              <button
                onClick={() => setFiles([])}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                disabled={uploading}
              >
                Clear All
              </button>
            )}
            
            <button
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
              className={`px-8 py-3 rounded-lg font-medium ${
                uploading || files.length === 0
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {uploading ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Uploading...
                </span>
              ) : (
                `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;