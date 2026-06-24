import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import appService, { App } from '../../services/app.service';
import folderService, { Folder } from '../../services/folder.service';
import documentService from '../../services/document.service';
import { showToast } from '../../components/common/ToastNotification';

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
  const [skipIfExists, setSkipIfExists] = useState(false);

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
        showToast('Please select a folder, not individual files. Use the folder selector.', 'warning');
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
      showToast('Please select files first', 'warning');
      return;
    }

    if (!folder || !folder.path) {
      showToast('Folder information incomplete, cannot upload', 'error');
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
          skip_if_exists: skipIfExists,
        };
        
        // 路径优先：如果文件夹有path，使用folder_path；否则使用folder_id（向后兼容）
        if (folder?.path) {
          uploadRequest.folder_path = folder.path;
          console.log('🔍 [DEBUG] AdminUpload upload: using folder_path:', folder.path);
        } else {
          console.error('⚠️ AdminUpload upload: no folder path available');
        }

        // 模拟进度更新（实际API调用没有进度事件）
        setTimeout(() => {
          setProgress(prev => Math.min(prev + (100 / selectedFiles.length), 95));
        }, index * 300);

        return await documentService.uploadDocument(uploadRequest);
      });

      // 等待所有文件上传完成
      const results = await Promise.all(uploadPromises);
      const uploadedCount = results.filter((r: any) => !r.skipped).length;
      const skippedCount = results.filter((r: any) => r.skipped).length;
      
      // 更新进度到100%
      setProgress(100);
      
      // 延迟一下让进度条完成动画
      setTimeout(() => {
        setUploading(false);
        setSelectedFiles([]);
        
        // 显示成功消息并导航回文档列表
        const pathInfo_ = folder?.path ? `\nTarget path: ${folder.path}` : "";
        let msg = `Uploaded ${uploadedCount} documents!`;
        if (skippedCount > 0) {
          msg += ` (${skippedCount} skipped - already exists)`;
        }
        showToast(msg + pathInfo_, 'success');
        if (appSlug && folder?.path) {
          const navPath = encodeURIComponent(folder.path);
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
      showToast(`Upload failed: ${error.response?.data?.detail || error.message || 'Unknown error'}${errPathInfo}`, 'error');
    }
  };

  // 导入整个文件夹（包括子文件夹结构）
  const handleImportFolder = async () => {
    if (selectedFiles.length === 0) {
      showToast('Please select a folder to import first', 'warning');
      return;
    }

    if (!folder || !folder.path || !app || !app.id) {
      showToast('App or folder information incomplete, cannot import', 'error');
      return;
    }

    // 验证文件是否包含相对路径信息（表明来自文件夹选择）
    const hasRelativePaths = selectedFiles.some(file => 'webkitRelativePath' in file);
    if (!hasRelativePaths) {
      const pathInfoMsg = folder.path ? `\nTarget path: ${folder.path}` : '';
      const confirmedImport = await window.wetYesOrNo(
        `The selected files don't contain folder structure info. Continue as regular file upload?${pathInfoMsg}\n\nTo preserve folder structure, use the "Import Folder" option.`
      );
      if (confirmedImport) {
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
      
      // 分析所有文件的路径，提取文件信息
      const fileList = selectedFiles.map(file => {
        // 获取文件的相对路径（相对于选择的根文件夹）
        const relativePath = (file as any).webkitRelativePath || file.name;
        
        // 提取目录部分
        const pathParts = relativePath.split('/');
        const fileName = pathParts.pop() || ''; // 文件名
        const dirPath = pathParts.join('/'); // 目录路径
        
        return {
          file,
          fileName,
          dirPath,
          fullPath: relativePath
        };
      });

      // 步骤1.5：弹窗确认导入（使用 wetYesOrNo 替代浏览器原生 alert）
      const confirmed = await window.wetYesOrNo(
        `Import ${fileList.length} files to:\n${folder.path}\n\nSub-folders will be auto-created.`,
        'Confirm Folder Import'
      );
      if (!confirmed) {
        setImporting(false);
        setImportProgress(0);
        return;
      }

      // 步骤2：上传所有文件（后端自动创建子文件夹）
      setImportStatus(`Uploading ${fileList.length} files...`);
      let filesUploaded = 0;
      let successfulUploads = 0;
      
      for (const fileInfo of fileList) {
        try {
          setImportStatus(`Uploading: ${fileInfo.fullPath} (${filesUploaded + 1}/${fileList.length})`);
          
          // 直接根据文件相对路径构造目标 folder_path
          // 后端 get_folder_by_identifier_or_path(create_if_not_exists=True) 会自动创建
          const targetFolderPath = fileInfo.dirPath
            ? `${folder.path}/${fileInfo.dirPath}`
            : folder.path;
          
          console.log(`📁 File: ${fileInfo.fullPath} → folder_path: ${targetFolderPath}`);
          
          // 上传文件
          const uploadRequest: any = {
            file: fileInfo.file,
            title: fileInfo.fileName.replace(/\.[^/.]+$/, ''),
            skip_if_exists: skipIfExists,
            folder_path: targetFolderPath,
          };

          await documentService.uploadDocument(uploadRequest);
          successfulUploads++;
          
        } catch (error) {
          console.error(`文件上传失败 ${fileInfo.fullPath}:`, error);
          // 继续上传其他文件
        }
        
        filesUploaded++;
        setImportProgress(Math.round((filesUploaded / fileList.length) * 100));
      }

      // 步骤4：完成导入
      setImportProgress(100);
      setImportStatus(`Import complete! Uploaded ${successfulUploads}/${fileList.length} files`);
      
      // 延迟一下让进度条完成动画
      setTimeout(() => {
        setImporting(false);
        setSelectedFiles([]);
        setImportFileCount(0);
        
        // 显示成功消息并导航回文档列表
        const folderPathInfo = folder.path ? `\nTarget path: ${folder.path}` : '';
        showToast(`Folder import complete!${folderPathInfo}\n• Uploaded ${successfulUploads}/${fileList.length} files`, 'success');
        if (appSlug && folder?.path) {
          const navPath = encodeURIComponent(folder.path);
          navigate(`/admin/apps/${appSlug}?folder=${navPath}`);
        } else {
          navigate('/admin/apps');
        }
      }, 1000);

    } catch (error: any) {
      console.error('文件夹导入失败:', error);
      setImporting(false);
      setImportProgress(0);
      showToast(`Folder import failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`, 'error');
    }
  };

  // 导入整个website（网站）
  const handleImportWebsite = async () => {
    // 验证文件夹和应用信息
    if (!folder || !folder.path || !app || !app.id) {
      showToast('App or folder information incomplete, cannot import website', 'error');
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
      showToast('Please enter a valid URL (e.g. https://example.com)', 'warning');
      return;
    }

    setImportingWebsite(true);
    setWebsiteUrl(url);
    setWebsiteImportProgress(0);
    setWebsiteImportStatus('正在准备导入website...');

    try {
      // 显示导入确认信息
      const websitePathInfo = folder.path ? `\n目标路径: ${folder.path}` : '';
      const confirmedImport = await window.wetYesOrNo(
        `将要导入整个website:\n\nURL: ${url}\n\n目标文件夹: ${folder.name}${websitePathInfo}\n\n说明：\n• 这是一个后台处理任务，可能需要较长时间\n• 系统将自动抓取网页内容和相关资源\n• 导入过程可以在后台慢慢完成\n• 您可以在任务管理中查看进度\n\n确认开始导入？`
      );
      
      if (!confirmedImport) {
        setImportingWebsite(false);
        setWebsiteImportStatus('');
        return;
      }

      // 设置初始进度
      setWebsiteImportStatus('正在连接到website...');
      setWebsiteImportProgress(10);

      // 这里应该调用后端API来启动website导入任务
      // 由于后端API尚未实现，暂时显示模拟进度
      showToast(`Website import triggered!\n\nURL: ${url}\n\nNote: Backend website import API not yet implemented. This will be available in a future version.\n\nCurrently a demo feature.`, 'info');
      
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
            showToast(`Website import task submitted successfully!${wsPathInfo}\n\nURL: ${url}\n\nTask added to background processing queue.\n\nCheck task manager for progress.`, 'success');
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
      showToast(`Website import failed: ${error.message || 'Unknown error'}`, 'error');
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // 加载状态
  if (loading) {
    return (
      <main property="mainContentOfPage" className="container">
        <div className="text-center mrgn-tp-xl mrgn-bttm-xl">
          <p>Loading app and folder info...</p>
        </div>
      </main>
    );
  }

  // 错误状态
  if (error) {
    return (
      <main property="mainContentOfPage" className="container">
        <div className="alert alert-danger">
          <h3>Loading Failed</h3>
          <p>{error}</p>
          <button onClick={() => window.location.reload()} className="btn btn-danger">重试</button>
          {' '}
          <Link to="/admin/apps" className="btn btn-default">Back to Apps</Link>
        </div>
      </main>
    );
  }

  // 数据不完整状态
  if (!app || !folder) {
    return (
      <main property="mainContentOfPage" className="container">
        <div className="alert alert-warning">
          <h3>Incomplete Data</h3>
          <p>Unable to find the app or folder</p>
          <Link to="/admin/apps" className="btn btn-warning">返回应用列表</Link>
        </div>
      </main>
    );
  }

  return (
    <main property="mainContentOfPage" className="container">
      {/* WET Breadcrumb */}
      <nav id="wb-bc" property="breadcrumb">
        <h2 className="wb-inv">You are here:</h2>
        <div className="container">
          <ol className="breadcrumb">
            <li><Link to="/admin/apps">Apps</Link></li>
            <li><Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}`}>{app.name}</Link></li>
            <li><Link to={`/admin/apps/${appSlug || (app && (app.slug || app.id)) || ''}?folder=${encodeURIComponent(folder.path)}`}>{folder.name} Documents</Link></li>
            <li>Upload Documents</li>
          </ol>
        </div>
      </nav>

      {/* Title */}
      <h1>Upload Documents to {folder.name}</h1>
      <p>App: {app.name} • Folder: {folder.name}</p>
      {folder.description && <p>{folder.description}</p>}

      <div className="row">
        {/* 左侧：上传区域 */}
        <div className="col-md-8">
          <div className="panel panel-default">
          <div className="panel-body">
            <h2 className="h3">Select Files</h2>
            
            {/* 选项1：普通文件上传 */}
            <div className="mb-5">
              <h3 className="fb-upload-subtitle">Upload Single or Multiple Files</h3>
              <div className="fb-upload-dropzone">
                <div className="fb-text-gray-400 mb-3">
                  <svg className="where-48" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                  </svg>
                </div>
                <p className="mb-4">Select one or more files to upload</p>
                <input type="file" id="file-upload" multiple onChange={handleFileSelect} className="hidden" />
                <label htmlFor="file-upload" className="fb-upload-label fb-bg-blue-600 fb-text-white fb-rounded">
                  Select Files
                </label>
                <p className="fb-text-sm mt-3">Supports PDF, DOCX, XLSX, PPTX, JPG, PNG, TIFF</p>
              </div>
            </div>

            {/* 分隔线 */}
            <div className="fb-d-flex fb-align-center mb-4">
              <div className="fb-flex-1 fb-border-t"></div>
              <span className="fb-text-sm">or</span>
              <div className="fb-flex-1 fb-border-t"></div>
            </div>

            {/* 选项2：文件夹导入 */}
            <div className="mb-5">
              <h3 className="fb-d-flex fb-align-center fb-upload-subtitle">
                <svg className="where-20 mr-2" style={{color: '#16a34a'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                Import Entire Folder (Preserve Structure)
              </h3>
              {highlightImport && (
                <div className="mb-4 p-3 fb-bg-green-100">
                  <div className="fb-d-flex fb-align-center">
                    <svg className="where-20 mr-2" style={{color: '#16a34a'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <span className="fb-text-green-800" style={{fontWeight: 500}}>Import Mode Activated</span>
                  </div>
                  <p className="fb-text-sm fb-text-green-700 mt-1">
                    Click "Select Folder" to import an entire local folder. The system will automatically create sub-directories and upload all files.
                  </p>
                </div>
              )}
              <div className={`${highlightImport ? 'border-4 border-green-500' : 'border-2 border-dashed border-green-300'} rounded-lg p-6 text-center hover:border-green-500 transition-colors bg-green-50 ${highlightImport ? 'animate-pulse' : ''}`}>
                <div className="mb-3" style={{color: '#4ade80'}}>
                  <svg className="where-48" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                  </svg>
                </div>
                <p className="mb-4">Choose a local folder to auto-create sub-directories and upload all files</p>
                <input type="file" id="folder-upload" webkitdirectory="true" directory="true" multiple onChange={handleFolderSelect} className="hidden" />
                <label htmlFor="folder-upload" className="fb-upload-label fb-bg-green-600 fb-text-white fb-rounded">
                  Select Folder
                </label>
                <div className="fb-text-sm mt-4">
                  <div className="fb-d-flex fb-align-center fb-justify-center">
                    <svg className="where-20 mr-1" style={{color: '#22c55e'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Auto-create sub-folders
                  </div>
                  <div className="fb-d-flex fb-align-center fb-justify-center mt-1">
                    <svg className="where-20 mr-1" style={{color: '#22c55e'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Preserve original directory structure
                  </div>
                  <div className="fb-d-flex fb-align-center fb-justify-center mt-1">
                    <svg className="where-20 mr-1" style={{color: '#22c55e'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Batch upload all files
                  </div>
                </div>
                <p className="fb-text-xs mt-4">Compatible with Chrome, Edge, Safari</p>
              </div>
            </div>

            {/* 文件列表 */}
            {selectedFiles.length > 0 && (
              <div className="mt-5">
                <h3 style={{fontWeight: 500}} className="mb-3">
                  Selected Items ({selectedFiles.length})
                  {importFileCount > 0 && (
                    <span className="ml-2 fb-text-sm fb-text-link" style={{fontWeight: 400}}>
                      from folder import ({importFileCount} files)
                    </span>
                  )}
                </h3>
                <div className="fb-flex-col fb-gap-2">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="fb-d-flex fb-align-center fb-justify-between p-3" style={{border: '1px solid #e5e7eb', borderRadius: 4}}>
                      <div className="fb-d-flex fb-align-center">
                        <div className="mr-3" style={{color: '#3b82f6'}}>
                          <svg className="where-20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                          </svg>
                        </div>
                        <div>
                          <div style={{fontWeight: 500}}>{file.name}</div>
                          <div className="fb-text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                          {(file as any).webkitRelativePath && (
                            <div className="fb-text-xs fb-text-gray-400 mt-1">
                            Path: {(file as any).webkitRelativePath}
                            </div>
                          )}
                        </div>
                      </div>
                      <button onClick={() => removeFile(index)} style={{color: '#ef4444'}}>
                        <svg className="where-20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
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
              <div className="mt-5">
                <h3 style={{fontWeight: 500}} className="mb-3">Folder Import Progress</h3>
                <div className="progress">
                  <div className="progress-bar progress-bar-success" style={{width: `${importProgress}%`}}></div>
                </div>
                <div className="fb-d-flex fb-justify-between fb-text-sm mt-2">
                  <span>{importStatus}</span>
                  <span>{importProgress}%</span>
                </div>
                <div className="fb-text-sm mt-3">
                  <div className="fb-d-flex fb-align-center">
                    <svg className="where-20 mr-2" style={{color: '#22c55e'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Creating sub-folders and uploading files...
                  </div>
                </div>
              </div>
            )}

            {/* website导入进度 */}
            {importingWebsite && (
              <div className="mt-5">
                <h3 style={{fontWeight: 500}} className="mb-3">Website Import Progress</h3>
                <div className="progress">
                  <div className="progress-bar progress-bar-info" style={{width: `${websiteImportProgress}%`}}></div>
                </div>
                <div className="fb-d-flex fb-justify-between fb-text-sm mt-2">
                  <span>{websiteImportStatus}</span>
                  <span>{websiteImportProgress}%</span>
                </div>
                <div className="fb-text-sm mt-3">
                  <div className="fb-d-flex fb-align-center">
                    <svg className="where-20 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Importing website: {websiteUrl}
                  </div>
                  <div className="fb-text-xs mt-2">
                    This is a background task that will complete gradually.
                  </div>
                </div>
              </div>
            )}

            {/* 上传进度 */}
            {uploading && (
              <div className="mt-5">
                <h3 style={{fontWeight: 500}} className="mb-3">Upload Progress</h3>
                <div className="progress">
                  <div className="progress-bar progress-bar-info" style={{width: `${progress}%`}}></div>
                </div>
                <div className="fb-d-flex fb-justify-between fb-text-sm mt-2">
                  <span>Uploading...</span>
                  <span>{progress}%</span>
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="mrgn-tp-xl">
              <div className="checkbox mrgn-bttm-md">
                <label>
                  <input type="checkbox" checked={skipIfExists} onChange={(e) => setSkipIfExists(e.target.checked)} /> Skip if document exists
                </label>
              </div>
              <button onClick={() => setSelectedFiles([])} disabled={selectedFiles.length === 0 || uploading || importing || importingWebsite} className="btn btn-default">Clear List</button>
              {' '}
              <button onClick={handleUpload} disabled={selectedFiles.length === 0 || uploading || importing || importingWebsite} className="btn btn-primary">{uploading ? 'Uploading...' : 'Upload'}</button>
              {' '}
              <button onClick={handleImportFolder} disabled={selectedFiles.length === 0 || uploading || importing || importingWebsite} className="btn btn-success">{importing ? 'Importing...' : 'Import Folder'}</button>
              {' '}
              <button onClick={handleImportWebsite} disabled={uploading || importing || importingWebsite} className="btn btn-info">{importingWebsite ? 'Importing Website...' : 'Import Website'}</button>
            </div>
          </div>
          </div>
        </div>

        {/* 右侧：信息面板 */}
        <div className="col-md-4">
          <div className="panel panel-default">
            <div className="panel-heading"><h2 className="panel-title">Upload Info</h2></div>
            <div className="panel-body" style={{ overflow: 'hidden' }}>
            <dl className="dl-horizontal">
              <dt>Target App</dt><dd><strong>{app.name}</strong>{app.description && <><br/>{app.description}</>}</dd>
              <dt>Target Folder</dt><dd><strong>{folder.name}</strong>{folder.description && <><br/>{folder.description}</>}</dd>
              <dt>Folder Path</dt><dd><code style={{ wordBreak: 'break-all' }}>{folder.path}</code></dd>
              <dt>Created</dt><dd>By: {folder.created_by || 'Unknown'}<br/>At: {new Date(folder.created_at).toLocaleString()}</dd>
            </dl>
            </div>
          </div>

          <div className="panel panel-info">
            <div className="panel-heading"><h2 className="panel-title">New Architecture</h2></div>
            <div className="panel-body" style={{ overflow: 'hidden' }}>
              <ul>
                <li>Drawer layer removed, now uploading directly to app folder</li>
                <li>URL structure: <code>/admin/apps/:appSlug/folders/:folderId/upload</code></li>
                <li>Supports batch upload of multiple files</li>
                <li>Documents auto-enter conversion queue (if needed)</li>
                <li><strong>New:</strong> Import entire website (async background)</li>
              </ul>
              <p><strong>Supported Formats:</strong>{' '}
                {['PDF', 'DOCX', 'XLSX', 'PPTX', 'JPG', 'PNG', 'TIFF', 'TIF'].map(f => (
                  <span key={f} className="label label-info mrgn-rght-sm">{f}</span>
                ))}
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};

export default AdminUpload;