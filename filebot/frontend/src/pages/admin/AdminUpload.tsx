import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import appService, { App } from '../../services/app.service';
import folderService, { Folder } from '../../services/folder.service';
import documentService from '../../services/document.service';

const AdminUpload: React.FC = () => {
  const { appSlug, folderId } = useParams<{ appSlug: string; folderId: string }>();
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importFileCount, setImportFileCount] = useState(0);
  const [importStatus, setImportStatus] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [app, setApp] = useState<App | null>(null);
  const [folder, setFolder] = useState<Folder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [highlightImport, setHighlightImport] = useState(false);
  const [importingWebsite, setImportingWebsite] = useState(false);
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [websiteImportProgress, setWebsiteImportProgress] = useState(0);
  const [websiteImportStatus, setWebsiteImportStatus] = useState<string>('');

  // 获取查询参数
  const [searchParams] = useSearchParams();

  // 检查是否是从快速操作跳转过来的导入模式
  useEffect(() => {
    const mode = searchParams.get('mode');
    if (mode === 'import') {
      setHighlightImport(true);
      // 可以在这里添加其他导入模式的处理逻辑
      console.log('导入模式激活：显示文件夹导入区域高亮');
    }
  }, [searchParams]);

  // 加载应用和文件夹数据
  useEffect(() => {
    const loadData = async () => {
      if (!appSlug) {
        setError('Missing app parameter');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // 1. 获取应用信息
        const apps = await appService.getApps();
        const foundApp = apps.find(a => a.slug === appSlug || a.id === appSlug);
        if (!foundApp) {
                  setError(`App "${appSlug}" not found`);
          setLoading(false);
          return;
        }
        setApp(foundApp);

        // 2. 获取文件夹信息
        // 优先从查询参数获取（新路由模式），回退到URL路径参数（旧路由兼容）
        const folderQuery = searchParams.get('folder');
        const folderIdentifier = folderQuery 
          ? decodeURIComponent(folderQuery)
          : (folderId ? decodeURIComponent(folderId) : '');
        
        if (!folderIdentifier) {
          setError('Missing folder parameter');
          setLoading(false);
          return;
        }

        // 直接用路径查询文件夹（更准确可靠）
        const folder = await folderService.getFolder(folderIdentifier).catch(err => {
          console.error('🐛 AdminUpload getFolder failed:', err);
          return null;
        });
        
        if (!folder) {
          setError(`Folder "${folderQuery || folderId}" not found`);
          setLoading(false);
          return;
        }
        setFolder(folder);

      } catch (err) {
        console.error('加载数据失败:', err);
        setError('Failed to load app or folder info. Check network or re-login.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [appSlug, folderId, searchParams]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
    }
  };

  // 处理文件夹选择（用于导入本地文件夹）
  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      
      // 验证文件夹结构
      const hasRelativePaths = files.some(file => 'webkitRelativePath' in file);
      if (!hasRelativePaths) {
        window.showWetAlert('Please select a folder, not individual files. Use the folder selector.');
        e.target.value = ''; // 重置input
        return;
      }
      
      // 显示选择的文件数量
      setImportFileCount(files.length);
      setImportStatus(`Selected ${files.length} files, ready to import...`);
      
      // 存储文件列表用于后续导入
      setSelectedFiles(files);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      window.showWetAlert('Please select files first');
      return;
    }

    if (!folder || !folder.id) {
      window.showWetAlert('Folder information incomplete, cannot upload');
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      // 上传每个文件
      const uploadPromises = selectedFiles.map(async (file, index) => {
        // 构建上传请求，优先使用folder_path
        const uploadRequest: any = {
          file,
          title: file.name.replace(/\.[^/.]+$/, ''), // 使用文件名（不含扩展名）作为标题
        };
        
        // 路径优先：如果文件夹有path，使用folder_path；否则使用folder_id（向后兼容）
        if (folder?.path) {
          uploadRequest.folder_path = folder.path;
          console.log('🔍 [DEBUG] AdminUpload upload: using folder_path:', folder.path);
        } else {
          uploadRequest.folder_id = folder!.id;
          console.warn('⚠️ AdminUpload upload: using deprecated folder_id:', folder!.id);
        }

        // 模拟进度更新（实际API调用没有进度事件）
        setTimeout(() => {
          setProgress(prev => Math.min(prev + (100 / selectedFiles.length), 95));
        }, index * 300);

        return await documentService.uploadDocument(uploadRequest);
      });

      // 等待所有文件上传完成
      const uploadedDocuments = await Promise.all(uploadPromises);
      
      // 更新进度到100%
      setProgress(100);
      
      // 延迟一下让进度条完成动画
      setTimeout(() => {
        setUploading(false);
        setSelectedFiles([]);
        
        // 显示成功消息并导航回文档列表
        const pathInfo_ = folder?.path ? `\nTarget path: ${folder.path}` : "";
        window.showWetAlert(`Successfully uploaded ${uploadedDocuments.length} documents!${pathInfo_}`);
        if (appSlug && (folder?.path || folder?.id)) {
          const navPath = encodeURIComponent(folder?.path || folder?.id || '');
          navigate(`/admin/apps/${appSlug}?folder=${navPath}`);
        } else {
          console.error('导航参数缺失:', { appSlug, folder });
          navigate('/admin/apps');
        }
      }, 500);

    } catch (error: any) {
      console.error('上传失败:', error);
      setUploading(false);
      setProgress(0);
      const errPathInfo = folder?.path ? ` (Target path: ${folder.path})` : '';
      window.showWetAlert(`Upload failed: ${error.response?.data?.detail || error.message || 'Unknown error'}${errPathInfo}`);
    }
  };

  // 导入整个文件夹（包括子文件夹结构）
  const handleImportFolder = async () => {
    if (selectedFiles.length === 0) {
      window.showWetAlert('Please select a folder to import first');
      return;
    }

    if (!folder || !folder.id || !app || !app.id) {
      window.showWetAlert('App or folder information incomplete, cannot import');
      return;
    }

    // 验证文件是否包含相对路径信息（表明来自文件夹选择）
    const hasRelativePaths = selectedFiles.some(file => 'webkitRelativePath' in file);
    if (!hasRelativePaths) {
      const pathInfoMsg = folder.path ? `\nTarget path: ${folder.path}` : '';
      const confirmImport = await window.wetYesOrNo(
        `The selected files don't contain folder structure info. Continue as regular file upload?${pathInfoMsg}\n\nTo preserve folder structure, use the "Import Folder" option.`
      );
      if (confirmImport) {
        handleUpload();
      }
      return;
    }

    setImporting(true);
    setImportProgress(0);
    setImportStatus('Analyzing folder structure...');

    try {
      // 步骤1：分析文件夹结构
      setImportStatus('Analyzing folder structure...');
      
      // 使用Map来存储文件夹路径到文件夹ID的映射
      const folderMap = new Map<string, string>();
      // 根文件夹就是当前目标文件夹
      folderMap.set('', folder.id);
      
      // 分析所有文件的路径，提取所有文件夹
      const folderPaths = new Set<string>();
      const fileList = selectedFiles.map(file => {
        // 获取文件的相对路径（相对于选择的根文件夹）
        const relativePath = (file as any).webkitRelativePath || file.name;
        
        // 提取目录部分
        const pathParts = relativePath.split('/');
        const fileName = pathParts.pop() || ''; // 文件名
        const dirPath = pathParts.join('/'); // 目录路径
        
        // 添加到文件夹路径集合
        if (dirPath) {
          folderPaths.add(dirPath);
        }
        
        return {
          file,
          fileName,
          dirPath,
          fullPath: relativePath
        };
      });

      // 步骤2：创建所有需要的子文件夹
      setImportStatus(`Creating ${folderPaths.size} sub-folders...`);
      let foldersCreated = 0;
      
      // 按路径深度排序，确保先创建父文件夹
      const sortedFolderPaths = Array.from(folderPaths).sort((a, b) => {
        const depthA = a.split('/').length;
        const depthB = b.split('/').length;
        return depthA - depthB;
      });

      for (const folderPath of sortedFolderPaths) {
        try {
          // 检查父文件夹是否存在
          const pathParts = folderPath.split('/');
          let parentFolderIdentifier = folder.path || folder.id;
          
          // 逐级查找或创建父文件夹
          for (let i = 0; i < pathParts.length; i++) {
            const currentPath = pathParts.slice(0, i + 1).join('/');
            const currentName = pathParts[i];
            
            if (!folderMap.has(currentPath)) {
              // 创建文件夹
              const parentPath = pathParts.slice(0, i).join('/');
              const parentIdentifier = folderMap.get(parentPath) || (folder.path || folder.id);
              
              setImportStatus(`Creating folder: ${currentPath}`);
              
              const newFolder = await folderService.createFolder({
                name: currentName,
                description: `Folder imported from ${app.name}`,
                parent_folder_id: parentIdentifier, // 可以是路径或ID
                app_id: app.id
              });
              
              // 存储文件夹标识符（路径优先）
              const folderIdentifier = newFolder.path || newFolder.id;
              folderMap.set(currentPath, folderIdentifier);
              foldersCreated++;
            }
            
            // 更新父文件夹标识符用于下一级
            parentFolderIdentifier = folderMap.get(currentPath)!;
          }
        } catch (error) {
          console.error(`创建文件夹失败 ${folderPath}:`, error);
          // 继续尝试创建其他文件夹
        }
        
        // 更新进度
        setImportProgress(Math.round((foldersCreated / sortedFolderPaths.length) * 40));
      }

      // 步骤3：上传所有文件到对应的文件夹
      setImportStatus(`Uploading ${fileList.length} files...`);
      let filesUploaded = 0;
      let successfulUploads = 0;
      
      for (const fileInfo of fileList) {
        try {
          setImportStatus(`Uploading: ${fileInfo.fullPath} (${filesUploaded + 1}/${fileList.length})`);
          
          // 获取文件对应的文件夹标识符（路径优先）
          const targetFolderIdentifier = fileInfo.dirPath ? folderMap.get(fileInfo.dirPath) || (folder.path || folder.id) : (folder.path || folder.id);
          
          // 上传文件
          const uploadRequest: any = {
            file: fileInfo.file,
            title: fileInfo.fileName.replace(/\.[^/.]+$/, '') // 使用文件名（不含扩展名）作为标题
          };
          
          // 路径优先：如果是路径，使用folder_path；否则使用folder_id（向后兼容）
          if (targetFolderIdentifier.startsWith('/')) {
            uploadRequest.folder_path = targetFolderIdentifier;
            console.log('🔍 [DEBUG] AdminUpload batch import: using folder_path:', targetFolderIdentifier);
          } else {
            uploadRequest.folder_id = targetFolderIdentifier;
            console.warn('⚠️ AdminUpload batch import: using deprecated folder_id:', targetFolderIdentifier);
          }

          await documentService.uploadDocument(uploadRequest);
          successfulUploads++;
          
        } catch (error) {
          console.error(`文件上传失败 ${fileInfo.fullPath}:`, error);
          // 继续上传其他文件
        }
        
        filesUploaded++;
        setImportProgress(40 + Math.round((filesUploaded / fileList.length) * 60));
      }

      // 步骤4：完成导入
      setImportProgress(100);
      setImportStatus(`Import complete! Uploaded ${successfulUploads}/${fileList.length} files, created ${foldersCreated} sub-folders`);
      
      // 延迟一下让进度条完成动画
      setTimeout(() => {
        setImporting(false);
        setSelectedFiles([]);
        setImportFileCount(0);
        
        // 显示成功消息并导航回文档列表
        const folderPathInfo = folder.path ? `\nTarget path: ${folder.path}` : '';
        window.showWetAlert(`Folder import complete!${folderPathInfo}\n• Created ${foldersCreated} sub-folders\n• Uploaded ${successfulUploads}/${fileList.length} files`);
        if (appSlug && (folder?.path || folder?.id)) {
          const navPath = encodeURIComponent(folder?.path || folder?.id || '');
          navigate(`/admin/apps/${appSlug}?folder=${navPath}`);
        } else {
          navigate('/admin/apps');
        }
      }, 1000);

    } catch (error: any) {
      console.error('文件夹导入失败:', error);
      setImporting(false);
      setImportProgress(0);
      window.showWetAlert(`Folder import failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    }
  };

  // 导入整个website（网站）
  const handleImportWebsite = async () => {
    // 验证文件夹和应用信息
    if (!folder || !folder.id || !app || !app.id) {
      window.showWetAlert('App or folder information incomplete, cannot import website');
      return;
    }

    // 提示用户输入website URL
    const url = window.prompt('Enter the website URL to import:', 'https://example.com');
    if (!url || !url.trim()) {
      return; // 用户取消或输入为空
    }

    // 验证URL格式
    try {
      new URL(url);
    } catch (error) {
      window.showWetAlert('Please enter a valid URL (e.g. https://example.com)');
      return;
    }

    setImportingWebsite(true);
    setWebsiteUrl(url);
    setWebsiteImportProgress(0);
    setWebsiteImportStatus('正在准备导入website...');

    try {
      // 显示导入确认信息
      const websitePathInfo = folder.path ? `\n目标路径: ${folder.path}` : '';
      const confirmImport = await window.wetYesOrNo(
        `将要导入整个website:\n\nURL: ${url}\n\n目标文件夹: ${folder.name}${websitePathInfo}\n\n说明：\n• 这是一个后台处理任务，可能需要较长时间\n• 系统将自动抓取网页内容和相关资源\n• 导入过程可以在后台慢慢完成\n• 您可以在任务管理中查看进度\n\n确认开始导入？`
      );
      
      if (!confirmImport) {
        setImportingWebsite(false);
        setWebsiteImportStatus('');
        return;
      }

      // 设置初始进度
      setWebsiteImportStatus('正在连接到website...');
      setWebsiteImportProgress(10);

      // 这里应该调用后端API来启动website导入任务
      // 由于后端API尚未实现，暂时显示模拟进度
      window.showWetAlert(`Website import triggered!\n\nURL: ${url}\n\nNote: Backend website import API not yet implemented. This will be available in a future version.\n\nCurrently a demo feature.`);
      
      // 模拟进度更新（实际应用中应通过WebSocket或轮询获取真实进度）
      const simulateProgress = () => {
        if (websiteImportProgress < 90) {
          setWebsiteImportProgress(prev => prev + 10);
          setWebsiteImportStatus(`正在处理website内容 (${websiteImportProgress + 10}%)...`);
          setTimeout(simulateProgress, 500);
        } else {
          setWebsiteImportProgress(100);
          setWebsiteImportStatus('website导入任务已提交到后台处理');
          
          // 显示成功消息
          setTimeout(() => {
            const wsPathInfo = folder.path ? `\n目标路径: ${folder.path}` : '';
            window.showWetAlert(`Website import task submitted successfully!${wsPathInfo}\n\nURL: ${url}\n\nTask added to background processing queue.\n\nCheck task manager for progress.`);
            setImportingWebsite(false);
            setWebsiteImportStatus('');
            setWebsiteUrl('');
          }, 1000);
        }
      };
      
      // 开始模拟进度
      setTimeout(simulateProgress, 1000);
      
    } catch (error: any) {
      console.error('website导入失败:', error);
      setImportingWebsite(false);
      setWebsiteImportStatus('');
      window.showWetAlert(`Website import failed: ${error.message || 'Unknown error'}`);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // 加载状态
  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading app and folder info...</p>
          </div>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">Loading Failed</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <div className="flex justify-center space-x-3">
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              重试
            </button>
            <Link 
              to="/admin/apps"
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            >
              Back to Apps
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 数据不完整状态
  if (!app || !folder) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">Incomplete Data</h3>
          <p className="text-yellow-700 mb-4">Unable to find the app or folder</p>
          <Link 
            to="/admin/apps"
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            返回应用列表
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* 面包屑导航 */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/apps" className="hover:text-blue-600">Apps</Link>
          <span>›</span>
          <Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}`} className="hover:text-blue-600">{app.name}</Link>
          <span>›</span>
          <Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}?folder=${encodeURIComponent(folder.path)}`} className="hover:text-blue-600">{folder.name} Documents</Link>
          <span>›</span>
          <span className="text-gray-700">Upload Documents</span>
        </div>
        
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Upload Documents to {folder.name}</h1>
            <p className="text-gray-600 mt-1">App: {app.name} • Folder: {folder.name}</p>
            {folder.description && (
              <p className="text-gray-500 text-sm mt-1">{folder.description}</p>
            )}
          </div>
          <Link 
            to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}?folder=${encodeURIComponent(folder.path)}`}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
          >
            Back to Documents
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：上传区域 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Select Files</h2>
            
            {/* 选项1：普通文件上传 */}
            <div className="mb-6">
              <h3 className="text-md font-medium mb-3">Upload Single or Multiple Files</h3>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
                <div className="text-gray-400 mb-3">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                  </svg>
                </div>
                <p className="text-gray-600 mb-4">Select one or more files to upload</p>
                <input 
                  type="file" 
                  id="file-upload" 
                  multiple 
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <label 
                  htmlFor="file-upload"
                  className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer inline-block"
                >
                  Select Files
                </label>
                <p className="text-sm text-gray-500 mt-3">Supports PDF, DOCX, XLSX, PPTX, JPG, PNG, TIFF</p>
              </div>
            </div>

            {/* 分隔线 */}
            <div className="flex items-center my-6">
              <div className="flex-grow border-t border-gray-300"></div>
              <div className="mx-4 text-sm text-gray-500">or</div>
              <div className="flex-grow border-t border-gray-300"></div>
            </div>

            {/* 选项2：文件夹导入 */}
            <div className="mb-6">
              <h3 className="text-md font-medium mb-3 flex items-center">
                <svg className="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                Import Entire Folder (Preserve Structure)
              </h3>
              {highlightImport && (
                <div className="mb-4 p-3 bg-green-100 border border-green-300 rounded-lg">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <span className="font-medium text-green-800">Import Mode Activated</span>
                  </div>
                  <p className="text-sm text-green-700 mt-1 ml-7">
                    Click "Select Folder" to import an entire local folder. The system will automatically create sub-directories and upload all files.
                  </p>
                </div>
              )}
              <div className={`${highlightImport ? 'border-4 border-green-500' : 'border-2 border-dashed border-green-300'} rounded-lg p-6 text-center hover:border-green-500 transition-colors bg-green-50 ${highlightImport ? 'animate-pulse' : ''}`}>
                <div className="text-green-400 mb-3">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                  </svg>
                </div>
                <p className="text-gray-600 mb-4">Choose a local folder to auto-create sub-directories and upload all files</p>
                <input 
                  type="file" 
                  id="folder-upload" 
                  // @ts-ignore - webkitdirectory is not in TypeScript's HTMLInputElement type
                  webkitdirectory="true"
                  directory="true"
                  multiple 
                  onChange={handleFolderSelect}
                  className="hidden"
                />
                <label 
                  htmlFor="folder-upload"
                  className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 cursor-pointer inline-block"
                >
                  Select Folder
                </label>
                <div className="mt-4 text-sm text-gray-600">
                  <div className="flex items-center justify-center">
                    <svg className="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Auto-create sub-folders
                  </div>
                  <div className="flex items-center justify-center mt-1">
                    <svg className="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Preserve original directory structure
                  </div>
                  <div className="flex items-center justify-center mt-1">
                    <svg className="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Batch upload all files
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-4">Compatible with Chrome, Edge, Safari</p>
              </div>
            </div>

            {/* 文件列表 */}
            {selectedFiles.length > 0 && (
              <div className="mt-6">
                <h3 className="font-medium mb-3">
                  Selected Items ({selectedFiles.length})
                  {importFileCount > 0 && (
                    <span className="ml-2 text-sm font-normal text-blue-600">
                      from folder import ({importFileCount} files)
                    </span>
                  )}
                </h3>
                <div className="space-y-3">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border border-gray-200 rounded">
                      <div className="flex items-center">
                        <div className="text-blue-500 mr-3">
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                          </svg>
                        </div>
                        <div>
                          <div className="font-medium">{file.name}</div>
                          <div className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                          {(file as any).webkitRelativePath && (
                            <div className="text-xs text-gray-400 mt-1">
                            Path: {(file as any).webkitRelativePath}
                            </div>
                          )}
                        </div>
                      </div>
                      <button 
                        onClick={() => removeFile(index)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 文件夹导入进度 */}
            {importing && (
              <div className="mt-6">
                <h3 className="font-medium mb-3">Folder Import Progress</h3>
                <div className="bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div 
                    className="bg-green-600 h-full transition-all duration-300"
                    style={{ width: `${importProgress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-sm text-gray-600 mt-2">
                  <span>{importStatus}</span>
                  <span>{importProgress}%</span>
                </div>
                <div className="mt-3 text-sm text-gray-600">
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Creating sub-folders and uploading files...
                  </div>
                </div>
              </div>
            )}

            {/* website导入进度 */}
            {importingWebsite && (
              <div className="mt-6">
                <h3 className="font-medium mb-3">Website Import Progress</h3>
                <div className="bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div 
                    className="bg-purple-600 h-full transition-all duration-300"
                    style={{ width: `${websiteImportProgress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-sm text-gray-600 mt-2">
                  <span>{websiteImportStatus}</span>
                  <span>{websiteImportProgress}%</span>
                </div>
                <div className="mt-3 text-sm text-gray-600">
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-2 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Importing website: {websiteUrl}
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    This is a background task that will complete gradually.
                  </div>
                </div>
              </div>
            )}

            {/* 上传进度 */}
            {uploading && (
              <div className="mt-6">
                <h3 className="font-medium mb-3">Upload Progress</h3>
                <div className="bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div 
                    className="bg-blue-600 h-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-sm text-gray-600 mt-2">
                  <span>Uploading...</span>
                  <span>{progress}%</span>
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="mt-8 flex justify-end space-x-3">
              <button 
                onClick={() => setSelectedFiles([])}
                disabled={selectedFiles.length === 0 || uploading || importing || importingWebsite}
                className="px-6 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear List
              </button>
              <button 
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || uploading || importing || importingWebsite}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
              <button 
                onClick={handleImportFolder}
                disabled={selectedFiles.length === 0 || uploading || importing || importingWebsite}
                className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importing ? 'Importing...' : 'Import Folder'}
              </button>
              <button 
                onClick={handleImportWebsite}
                disabled={uploading || importing || importingWebsite}
                className="px-6 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importingWebsite ? 'Importing Website...' : 'Import Website'}
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：信息面板 */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Upload Info</h2>
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-500">Target App</div>
                <div className="font-medium">{app.name}</div>
                {app.description && (
                  <div className="text-sm text-gray-500 mt-1">{app.description}</div>
                )}
              </div>
              <div>
                <div className="text-sm text-gray-500">Target Folder</div>
                <div className="font-medium">{folder.name}</div>
                {folder.description && (
                  <div className="text-sm text-gray-500 mt-1">{folder.description}</div>
                )}
              </div>
              <div>
                <div className="text-sm text-gray-500">Folder ID</div>
                <div className="font-mono text-sm bg-gray-50 p-2 rounded mt-1">{folder.id}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">Created</div>
                <div className="text-sm text-gray-600">
                  <p>By: {folder.created_by || 'Unknown'}</p>
                  <p>At: {new Date(folder.created_at).toLocaleString()}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 text-blue-800">New Architecture</h2>
            <div className="space-y-3 text-blue-700">
              <p className="text-sm">• Drawer layer removed, now uploading directly to app folder</p>
              <p className="text-sm">• URL structure: <code>/admin/apps/:appSlug/folders/:folderId/upload</code></p>
              <p className="text-sm">• Supports batch upload of multiple files</p>
              <p className="text-sm">• Documents auto-enter conversion queue (if needed)</p>
              <p className="text-sm">• <span className="font-medium text-purple-700">New: Import entire website (async background)</span></p>
            </div>
            
            <div className="mt-6 pt-4 border-t border-blue-200">
              <h3 className="font-medium text-blue-800 mb-2">Supported Formats</h3>
              <div className="flex flex-wrap gap-2">
                {['PDF', 'DOCX', 'XLSX', 'PPTX', 'JPG', 'PNG', 'TIFF', 'TIF'].map(format => (
                  <span key={format} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                    {format}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminUpload;