import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import documentService from '../services/document.service';
import folderService from '../services/folder.service';
import appService from '../services/app.service';

interface Folder {
  id: string;
  name: string;
}

const Upload: React.FC = () => {
  const { appId, folderId: folderIdParam, drawerSlug: urlDrawerSlug } = useParams<{ appId: string; folderId?: string; drawerSlug?: string }>();
  const location = useLocation();
  const stateDrawerSlug = location.state?.drawerSlug;
  const stateDrawerInfo = location.state?.drawerInfo;
  const stateAppId = location.state?.appId;
  
  // 优先级：URL参数优先，否则使用导航状态
  const effectiveDrawerSlug = urlDrawerSlug || stateDrawerSlug;
  const effectiveAppId = stateAppId || appId;
  
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  
  // 解析folderId：从"uuid-slug"格式中提取实际的UUID
  const parseFolderId = (folderIdParam: string): string => {
    if (!folderIdParam) {
      return '';
    }
    
    // 如果参数包含"-"，则可能是"uuid-slug"格式
    if (folderIdParam.includes('-')) {
      // 检查是否以UUID开头（UUID格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
      const match = folderIdParam.match(uuidPattern);
      
      if (match) {
        return match[0];
      }
      
      // 如果不是标准UUID格式，尝试提取ID部分
      const parts = folderIdParam.split('-');
      return parts[0];
    }
    
    return folderIdParam;
  };

  const folderId = parseFolderId(folderIdParam || '');
  
  const [selectedFolder, setSelectedFolder] = useState<string>(folderId || '');
  const [folders, setFolders] = useState<Folder[]>([]);
  const [drawerInfo, setDrawerInfo] = useState<any>(null);
  const [tags, setTags] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [errors, setErrors] = useState<string[]>([]);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const navigate = useNavigate();

  React.useEffect(() => {
    console.log('🔧 useEffect触发:', { appId: effectiveAppId, folderId, drawerSlug: effectiveDrawerSlug, selectedFolder });
    if (effectiveAppId && (folderId || effectiveDrawerSlug)) {
      fetchFolders();
    } else {
      setErrors(['Cannot upload: Missing application or folder/drawer information. Please select a folder or drawer first.']);
    }
  }, [effectiveAppId, folderId, effectiveDrawerSlug]);

  // 响应folders变化：当抽屉上传模式时，自动选择第一个可用文件夹
  React.useEffect(() => {
    console.log('🔧 folders变化效果:', { 
      drawerSlug: effectiveDrawerSlug, 
      selectedFolder, 
      foldersCount: folders.length, 
      folders: folders.map(f => ({ id:  f.path, name: f.name })),
      hasDrawer: !!effectiveDrawerSlug
    });
    
    // 只在抽屉上传模式下处理自动选择
    if (effectiveDrawerSlug) {
      console.log(`🔧 抽屉上传模式自动选择检查: drawerSlug="${effectiveDrawerSlug}"`);
      
      // 检查当前选中的文件夹是否有效
      const currentSelectionValid = selectedFolder && 
                                   selectedFolder !== '' && 
                                   selectedFolder !== '0' && 
                                   folders.some(f => f.path === selectedFolder);
      
      // 如果当前选择无效或为空，且文件夹列表不为空，则自动选择第一个文件夹
      if (!currentSelectionValid && folders.length > 0) {
        const firstFolder = folders[0];
        console.log(`🔧 自动选择文件夹: "${firstFolder.name}" (ID: ${firstFolder.path})，原因:`, 
          !selectedFolder ? 'selectedFolder为空' : 
          selectedFolder === '' ? 'selectedFolder为空字符串' :
          selectedFolder === '0' ? 'selectedFolder为"0"' :
          '选中的文件夹不在列表中');
        
        // 确保ID转为字符串
        folderIdStr = firstFolder.path.toString();
        setSelectedFolder(folderIdStr);
        console.log(`✅ 已设置selectedFolder为: "${folderIdStr}"`);
      } else if (currentSelectionValid) {
        console.log(`ℹ️ 抽屉上传模式，已选中有效文件夹: "${selectedFolder}"`);
      } else if (folders.length === 0) {
        console.warn(`⚠️ 抽屉上传模式，但文件夹列表为空，无法自动选择`);
        // 设置错误信息，提示用户需要先创建文件夹
        setErrors(prev => [...prev.filter(e => !e.includes('No folders available')), 
          'No folders available in this drawer. Please create a folder first before uploading.']);
      }
    } else {
      console.log('ℹ️ 非抽屉上传模式，不进行自动选择');
    }
  }, [folders, effectiveDrawerSlug, selectedFolder]);

  const fetchFolders = async () => {
    try {
      console.log('🔧 fetchFolders开始执行:', { 
        appId: effectiveAppId, 
        drawerSlug: effectiveDrawerSlug, 
        selectedFolder, 
        folderId,
        hasAppId: !!effectiveAppId,
        hasDrawerSlug: !!effectiveDrawerSlug,
        hasFolderId: !!folderId
      });
      
      let data: any[] = [];
      if (effectiveAppId) {
        // 抽屉概念已被移除，直接获取应用的文件夹
        console.log(`📁 直接获取应用 "${effectiveAppId}" 的文件夹（抽屉已弃用）`);
        
        // 如果有folderId，尝试获取父文件夹路径
        let parentFolderPath = null;
        if (folderId) {
          try {
            const currentFolder = await folderService.getFolder(folderId);
            if (currentFolder) {
              parentFolderPath = currentFolder.path || currentFolder.path;
              console.log(`📂 找到当前文件夹路径: ${parentFolderPath}`);
            }
          } catch (e) {
            console.warn('获取当前文件夹详情失败:', e);
          }
        }
        
        // 直接调用folderService.getFolders，传递应用slug和可能的父文件夹路径
        console.log(`📂 调用 folderService.getFolders(appSlug="${effectiveAppId}", parentFolderPath=${parentFolderPath})`);
        data = await folderService.getFolders(effectiveAppId, parentFolderPath ? { parent_folder_path: parentFolderPath } : undefined);
        console.log(`📊 获取到文件夹 (${data.length} 个):`, data.map(f => ({ 
          name: f.name, 
          path: f.path,
          description: f.description 
        })));
        
        // 如果没有找到文件夹，记录警告
        if (data.length === 0) {
          console.warn(`⚠️ 应用 "${effectiveAppId}" 中没有文件夹`);
        }
        
        // 确保当前选中的文件夹在列表中
        if (folderId && !data.some(f => f.path === folderId)) {
          try {
            console.log(`🔍 当前folderId "${folderId}" 不在文件夹列表中，尝试获取文件夹详情`);
            // 如果当前文件夹不在列表中，尝试获取该文件夹详情
            const currentFolder = await folderService.getFolder(folderId);
            if (currentFolder) {
              console.log(`✅ 找到文件夹详情:`, { id: currentFolder.path, name: currentFolder.name });
              data.unshift(currentFolder);
            }
          } catch (e) {
            console.warn('Could not fetch current folder:', e);
          }
        }
      } else {
        console.error('❌ 缺少有效的appId，无法获取文件夹');
        setErrors(['Cannot upload: Missing application information. Please select an application first.']);
      }
      
      console.log(`📦 最终文件夹数据: ${data.length} 个文件夹`, data.map(f => ({ id:  f.path, name: f.name })));
      setFolders(data || []);
      
      // 抽屉上传模式：记录状态
      if (effectiveDrawerSlug) {
        console.log(`ℹ️ 抽屉上传模式总结: drawerSlug="${effectiveDrawerSlug}", selectedFolder="${selectedFolder}", folders=${data.length}`);
      }
    } catch (error) {
      console.error('❌ Failed to fetch folders:', error);
      setFolders([]);
      setErrors(prev => [...prev, 'Unable to load folders. Please check your permissions and try again.']);
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

    // 调试信息
    console.log('🔧 上传调试信息:', {
      appId: effectiveAppId,
      drawerSlug: effectiveDrawerSlug,
      folderId,
      selectedFolder,
      foldersCount: folders.length,
      foldersList: folders.map(f => ({ id:  f.path, name: f.name })),
      filesCount: files.length,
      firstFileName: files[0]?.name
    });

    setUploading(true);
    setErrors([]);
    setSuccessMessage('');
    
    // 验证文件夹选择（抽屉上传模式必须选择文件夹）
    // 如果抽屉上传模式但没有选中文件夹，尝试自动选择第一个可用文件夹
    let actualFolderId = selectedFolder;
    console.log(`🔧 上传前验证: drawerSlug="${effectiveDrawerSlug}", selectedFolder="${selectedFolder}", foldersCount=${folders.length}`);
    
    if (effectiveDrawerSlug) {
      // 抽屉上传模式：必须选择文件夹
      if (!actualFolderId || actualFolderId === '' || actualFolderId === '0') {
        console.warn(`⚠️ 抽屉上传模式验证: drawerSlug="${effectiveDrawerSlug}", selectedFolder为空或无效`);
        console.log(`📁 可用文件夹列表:`, folders.map(f => ({ id:  f.path, name: f.name })));
        
        // 尝试自动选择第一个文件夹（如果可用）
        if (folders.length > 0) {
          const firstFolder = folders[0];
          actualFolderId = firstFolder.path;
          console.log(`🔄 自动选择第一个文件夹: "${firstFolder.name}" (ID: ${actualFolderId})`);
          
          // 同时更新状态，以便UI反映这个选择
          setSelectedFolder(actualFolderId);
        } else {
          console.error(`❌ 抽屉上传失败: 抽屉中没有可用文件夹`);
          setErrors(['No folders available in this drawer. Please create a folder first before uploading.']);
          setUploading(false);
          return;
        }
      } else {
        // 检查选中的文件夹是否在列表中
        const folderExists = folders.some(f => f.path === actualFolderId);
        if (!folderExists) {
          console.warn(`⚠️ 选中的文件夹不在列表中: "${actualFolderId}"`);
          
          // 如果文件夹不在列表中但列表不为空，自动选择第一个
          if (folders.length > 0) {
            const firstFolder = folders[0];
            actualFolderId = firstFolder.path;
            console.log(`🔄 重新选择第一个文件夹: "${firstFolder.name}" (ID: ${actualFolderId})`);
            setSelectedFolder(actualFolderId);
          } else {
            console.error(`❌ 选中的文件夹不存在且没有其他可用文件夹`);
            setErrors(['The selected folder is not available. Please select a different folder or create a new one.']);
            setUploading(false);
            return;
          }
        }
      }
      
      // 最终检查（自动选择后）
      if (!actualFolderId) {
        console.error(`❌ 抽屉上传最终验证失败: 没有有效的文件夹ID`);
        setErrors(['Please select a folder for the drawer upload']);
        setUploading(false);
        return;
      }
      
      console.log(`✅ 抽屉上传验证通过: folderId="${actualFolderId}"`);
    }
    
    // 验证文件夹ID格式（必须是有效的UUID）
    if (actualFolderId && !actualFolderId.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)) {
      console.warn('⚠️ 选中的文件夹ID格式可能无效:', actualFolderId);
      // 不阻止上传，但记录警告
    }
    
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
          
          if (actualFolderId) {
            formData.append('folder_id', actualFolderId);
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
            folder_id: actualFolderId || '',
            title: undefined,
            description: description || undefined
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
        
        // 捕获导航所需的变量（闭包安全）
        const navAppId = effectiveAppId;
        const navFolderId = folderId;
        const navDrawerSlug = effectiveDrawerSlug;
        const navActualFolderId = actualFolderId;
        
        setTimeout(() => {
          setFiles([]);
          setProgress(0);
          setSelectedFolder('');
          setTags('');
          setDescription('');
          
          // 上传成功后导航逻辑
          console.log('🔧 上传成功，准备导航:', { appId: navAppId, folderId: navFolderId, drawerSlug: navDrawerSlug, selectedFolder, actualFolderId: navActualFolderId });
          
          // 情况1：抽屉上传模式（有drawerSlug）
          if (navAppId && navDrawerSlug) {
            // 如果选择了文件夹，导航到该文件夹的文档页面
            if (navActualFolderId) {
              console.log(`✅ 导航到文件夹文档页面: /${navAppId}/folders/${navActualFolderId}/documents`, { drawerSlug: navDrawerSlug, drawerInfo });
              navigate(`/${navAppId}/folders/${navActualFolderId}/documents`, { 
                state: { 
                  drawerSlug: navDrawerSlug,
                  drawerInfo: drawerInfo || null,
                  fromDrawer: true
                } 
              });
            } 
            // 如果没有选择文件夹，导航回抽屉页面
            else {
              console.log(`✅ 导航回抽屉页面: /${navAppId}/${navDrawerSlug}`);
              navigate(`/${navAppId}/${navDrawerSlug}`);
            }
          }
          // 情况2：文件夹上传模式（有folderId）
          else if (navAppId && navFolderId) {
            console.log(`✅ 导航到文件夹文档页面: /${navAppId}/folders/${navFolderId}/documents`);
            navigate(`/${navAppId}/folders/${navFolderId}/documents`);
          }
          // 情况3：其他情况，返回应用列表
          else {
            console.log('⚠️ 没有足够的路由信息，导航到应用列表');
            navigate('/');
          }
        }, 2000);
      } else {
        setSuccessMessage(`Uploaded ${files.length - errors.length} of ${files.length} files`);
      }
      
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
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
      {/* Breadcrumb Navigation */}
      {(effectiveAppId && (folderId || effectiveDrawerSlug)) && (
        <nav className="flex items-center text-sm text-gray-600 mb-4">
          <button
            onClick={() => navigate('/')}
            className="hover:text-blue-600"
          >
            Applications
          </button>
          <span className="mx-2">›</span>
          <button
            onClick={() => navigate(`/${effectiveAppId}`)}
            className="hover:text-blue-600"
          >
            {effectiveAppId ? `App ${effectiveAppId}` : 'Application'}
          </button>
          {drawerInfo ? (
            <>
              <span className="mx-2">›</span>
              <button
                onClick={() => navigate(`/${effectiveAppId}/${drawerInfo.slug || drawerInfo.id}`)}
                className="hover:text-blue-600"
              >
                {drawerInfo.name || 'Drawer'}
              </button>
              <span className="mx-2 text-xs text-gray-400">(drawer)</span>
            </>
          ) : folderId ? (
            <>
              <span className="mx-2">›</span>
              <button
                onClick={() => navigate(`/${effectiveAppId}/folders/${encodeURIComponent(folder?.path || folderId)}/documents`)}
                className="hover:text-blue-600"
              >
                Folder Documents
              </button>
              <span className="mx-2 text-xs text-gray-400">(folder)</span>
            </>
          ) : effectiveDrawerSlug ? (
            <>
              <span className="mx-2">›</span>
              <span className="text-gray-600">
                Drawer: {effectiveDrawerSlug}
                <span className="mx-2 text-xs text-gray-400">(slug only)</span>
              </span>
            </>
          ) : null}
          <span className="mx-2">›</span>
          <span className="font-medium text-gray-800">Upload</span>
        </nav>
      )}
      
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Upload Documents</h1>
      {effectiveAppId && (folderId || effectiveDrawerSlug) && (
        <p className="text-gray-600 mb-8">
          Uploading to <span className="font-medium">
            {drawerInfo ? `Drawer: ${drawerInfo.name}` : 'Folder'}
          </span> in <span className="font-medium">Application {effectiveAppId}</span>
        </p>
      )}
      
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
              Select Folder {effectiveDrawerSlug ? '(Required for Drawer Upload)' : '(Optional)'}
            </label>
            
            {/* 抽屉上传模式警告 */}
            {effectiveDrawerSlug && folders.length === 0 && (
              <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-yellow-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.998-.833-2.732 0L4.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span className="text-yellow-800 font-medium">
                    No folders available in this drawer
                  </span>
                </div>
                <p className="text-sm text-yellow-700 mt-1 ml-7">
                  You need to create a folder first before uploading documents to this drawer.
                </p>
              </div>
            )}
            
            {/* 抽屉上传模式成功信息 */}
            {effectiveDrawerSlug && selectedFolder && folders.length > 0 && (
              <div className="mb-3 p-2 bg-green-50 border border-green-200 rounded-lg text-sm">
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-green-800">
                    Auto-selected folder for drawer upload: <span className="font-medium">
                      {folders.find(f => f.path === selectedFolder)?.name || 'Unknown folder'}
                    </span>
                  </span>
                </div>
              </div>
            )}
            
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedFolder}
              onChange={(e) => setSelectedFolder(e.target.value)}
              disabled={uploading || (effectiveDrawerSlug && folders.length === 0)}
            >
              <option value="">No Folder (Uncategorized)</option>
              {folders.map((folder) => (
                <option key={folder.path || folder.name} value={folder.path}>
                  {folder.name}
                </option>
              ))}
            </select>
            <p className="text-sm text-gray-500 mt-1">
              {effectiveDrawerSlug 
                ? 'Documents will be uploaded to the selected folder in this drawer' 
                : 'Organize your documents by selecting an existing folder'}
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
            onClick={() => {
              if (effectiveAppId && folderId) {
                navigate(`/${effectiveAppId}/folders/${encodeURIComponent(folder?.path || folderId)}/documents`);
              } else {
                navigate('/');
              }
            }}
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
              disabled={uploading || files.length === 0 || (effectiveDrawerSlug && folders.length === 0)}
              className={`px-8 py-3 rounded-lg font-medium ${
                uploading || files.length === 0 || (effectiveDrawerSlug && folders.length === 0)
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
              ) : effectiveDrawerSlug && folders.length === 0 ? (
                <span className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.998-.833-2.732 0L4.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  No Folders Available
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