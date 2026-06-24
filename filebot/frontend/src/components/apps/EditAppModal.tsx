import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import appService, { App } from '../../services/app.service';

interface EditAppModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updatedApp: App) => void;
  app: App | null;
}

const EditAppModal: React.FC<EditAppModalProps> = ({ isOpen, onClose, onSuccess, app }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<{
    name: string;
    slug: string;
    description: string;
    settings: { indices: string[] };
    redirect_url: string;
    icon: string;
    default_entry: string;
  }>({
    name: '',
    slug: '',
    description: '',
    settings: { indices: [] },
    redirect_url: '',
    icon: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [originalSlug, setOriginalSlug] = useState<string>('');

  // 当app数据变化时，初始化表单
  useEffect(() => {
    if (app) {
      // 安全处理settings对象，确保indices数组存在
      let settings = { indices: [] as string[] };
      if (app.settings) {
        // 如果app.settings有indices字段，使用它
        if (app.settings.indices && Array.isArray(app.settings.indices)) {
          settings.indices = app.settings.indices;
        } else {
          // 对于Smarti应用等没有indices字段的情况，创建空数组
          // 但保留其他settings字段
          settings = { ...app.settings, indices: [] };
        }
      }
      
      setFormData({
        name: app.name || '',
        slug: app.slug || '',
        description: app.description || '',
        settings: settings,
        redirect_url: app.redirect_url || '',
        icon: app.icon || ''
      });
      setOriginalSlug(app.slug || '');
      setError(null);
    }
  }, [app]);

  // 根据名称自动生成slug
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    setFormData(prev => ({
      ...prev,
      name,
      // 只有当用户没有手动修改过slug时才自动生成
      slug: prev.slug === originalSlug ? name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') : prev.slug
    }));
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      slug: e.target.value
    }));
  };

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      description: e.target.value
    }));
  };

  const handleIndicesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const indices = e.target.value.split(',').map(item => item.trim());
    setFormData(prev => ({
      ...prev,
      settings: { ...prev.settings, indices }
    }));
  };

  const handleRedirectUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      redirect_url: e.target.value
    }));
  };

  const handleIconChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      icon: e.target.value
    }));
  };

  const handleDefaultEntryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      default_entry: e.target.value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError(t('appModal.appNameRequiredError'));
      return;
    }
    if (!formData.slug.trim()) {
      setError(t('appModal.appSlugRequiredError'));
      return;
    }
    if (!app) {
      setError(t('appModal.appDataNotFound'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 构建更新后的settings对象
      // 对于Smarti应用，保留原始settings中的所有字段，只更新indices
      let updatedSettings = { ...formData.settings };
      
      // 过滤掉空的索引字段
      const filteredIndices = formData.settings.indices.filter(item => item.trim() !== '');
      
      // 如果原始应用有settings，并且不是标准indices结构（如Smarti应用）
      // 我们需要保留所有原始字段，只添加/更新indices
      if (app.settings && (!app.settings.indices || !Array.isArray(app.settings.indices))) {
        // 这是Smarti应用或非标准settings结构
        // 保留所有原始字段，添加indices数组
        updatedSettings = { ...app.settings, indices: filteredIndices };
      } else {
        // 标准应用，直接使用过滤后的indices
        updatedSettings.indices = filteredIndices;
      }
      
      const updatedApp = await appService.updateApp(app.id, {
        name: formData.name,
        slug: formData.slug,
        description: formData.description,
        settings: updatedSettings,
        redirect_url: formData.redirect_url,
        icon: formData.icon
      });
      onSuccess(updatedApp);
      onClose();
    } catch (err: any) {
      console.error('更新应用失败:', err);
      setError(err.response?.data?.detail || err.message || t('appModal.updateAppFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      name: '',
      slug: '',
      description: '',
      settings: { indices: [] },
      redirect_url: '',
      icon: ''
    });
    setError(null);
    onClose();
  };

  if (!isOpen || !app) return null;

  return (
    <div style={{position:"fixed",top:0,right:0,bottom:0,left:0,zIndex:50,overflowY:"auto"}}>
      {/* 背景遮罩 */}
      <div style={{opacity:0.3,position:"fixed",top:0,right:0,bottom:0,left:0,backgroundColor:"#000"}} onClick={handleCancel}></div>
      
      {/* 模态框 */}
      <div className="fb-d-flex fb-align-center fb-page-bg" style={{justifyContent:"center",padding:16}}>
        <div style={{position:"relative",backgroundColor:"#fff",borderRadius:8,boxShadow:"0 10px 15px -3px rgba(0,0,0,0.1)",width:"100%",maxWidth:448}}>
          {/* 标题 */}
          <div style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,borderBottom:"1px solid #e5e7eb"}}>
            <h3 style={{fontSize:"1.125rem",lineHeight:"1.75rem",fontWeight:600,color:"#111827"}}>{t('appModal.editApp')}</h3>
            <p className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginTop:4}}>{t('appModal.editAppSubtitle')}</p>
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit}>
            <div style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,display:"flex",flexDirection:"column",gap:16}}>
              {/* 错误提示 */}
              {error && (
                <div style={{backgroundColor:"#fef2f2",border:"1px solid #ddd",borderColor:"#fecaca",borderRadius:8,padding:12}}>
                  <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#991b1b"}}>{error}</p>
                </div>
              )}

              {/* 应用ID显示（只读） */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.appId')}
                </label>
                <input
                  type="text"
                  value={app.id}
                  className="text-muted" style={{width:"100%",paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:6,backgroundColor:"#f9fafb"}}
                  readOnly
                  disabled
                />
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>{t('appModal.appIdDescription')}</p>
              </div>

              {/* 应用名称 */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.appNameLabel')} <span style={{color:"#ef4444"}}>*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={handleNameChange}
                  className="form-control"
                  placeholder={t('appModal.appNamePlaceholder')}
                  disabled={loading}
                  autoFocus
                />
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>{t('appModal.appDisplayName')}</p>
              </div>

              {/* 应用标识 */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.appSlugLabel')} <span style={{color:"#ef4444"}}>*</span>
                </label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={handleSlugChange}
                  className="form-control"
                  placeholder={t('appModal.slugPlaceholder')}
                  disabled={loading}
                />
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>{t('appModal.slugUsageHint')}</p>
              </div>

              {/* 应用描述 */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.appDescriptionLabel')}
                </label>
                <textarea
                  value={formData.description}
                  onChange={handleDescriptionChange}
                  className="form-control"
                  placeholder={t('appModal.appDescriptionPlaceholder')}
                  rows={3}
                  disabled={loading}
                />
              </div>

              {/* 索引字段 */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.documentIndexFields')}
                </label>
                <input
                  type="text"
                  value={formData.settings.indices?.join(',') || ''}
                  onChange={handleIndicesChange}
                  className="form-control"
                  placeholder={t('appModal.indexFieldsPlaceholder')}
                  disabled={loading}
                />
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>{t('appModal.indexFieldsHint')}</p>
              </div>

              {/* 重定向URL - 用于统一仪表板 */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.redirectUrlLabel')}
                </label>
                <input
                  type="text"
                  value={formData.redirect_url}
                  onChange={handleRedirectUrlChange}
                  className="form-control"
                  placeholder={t('appModal.redirectUrlPlaceholder')}
                  disabled={loading}
                />
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                  {t('appModal.redirectUrlHint')}
                </p>
              </div>

              {/* Default Entry Path */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
Default Entry Path
                </label>
                <input
                  type="text"
                  value={formData.default_entry}
                  onChange={handleDefaultEntryChange}
                  className="form-control"
                  placeholder="e.g. canadasite"
                  disabled={loading}
                />
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
Optional default entry path. When set, clicking this app goes directly to /apps/:slug/:path
                </p>
              </div>

              {/* Icon */}
              <div>
                <label style={{display:"block",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151",marginBottom:4}}>
                  {t('appModal.iconLabel')}
                </label>
                <div className="fb-d-flex fb-align-center" style={{display:"flex",gap:8}}>
                  <input
                    type="text"
                    value={formData.icon}
                    onChange={handleIconChange}
                    style={{flex:1,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,border:"1px solid #ddd",borderColor:"#d1d5db",borderRadius:6}}
                    placeholder={t('appModal.iconPlaceholder')}
                    disabled={loading}
                  />
                  <div className="fb-d-flex fb-align-center" style={{width:40,height:40,backgroundColor:"#f3f4f6",borderRadius:8,justifyContent:"center"}}>
                    <span style={{fontSize:"1.125rem",lineHeight:"1.75rem"}}>{formData.icon || '📄'}</span>
                  </div>
                </div>
                <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                  {t('appModal.iconHint')}
                </p>
                <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:4}}>
                  <span style={{fontWeight:500}}>{t('appModal.examples')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>📁 {t('appModal.documentManagement')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>🌐 {t('appModal.webBotApp')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>🏛️ {t('appModal.governmentServices')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>🧾 {t('appModal.invoiceSystem')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>🔍 {t('appModal.dataAnalysis')}</span>
                </div>
              </div>

              {/* 创建信息（只读） */}
              <div style={{borderColor:"#f3f4f6",paddingTop:16,borderTop:"1px solid #e5e7eb"}}>
                <div className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem"}}>
                  <p>{t('appModal.creator')}: {app.created_by || t('common.unknown')}</p>
                  <p>{t('appModal.creationTime')}: {app.created_at ? new Date(app.created_at).toLocaleString() : t('common.unknown')}</p>
                  {app.updated_at && (
                    <p>{t('appModal.lastUpdated')}: {new Date(app.updated_at).toLocaleString()}</p>
                  )}
                </div>
              </div>
            </div>

            {/* 底部按钮 */}
            <div className="fb-d-flex" style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,borderTop:"1px solid #e5e7eb",backgroundColor:"#f9fafb",justifyContent:"flex-end",display:"flex",gap:12}}>
              <button
                type="button"
                onClick={handleCancel}
                style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,color:"#374151",backgroundColor:"#e5e7eb",borderRadius:6}}
                disabled={loading}
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,backgroundColor:"#2563eb",color:"#fff",borderRadius:6}}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="fb-spinner" style={{display:"inline-block",borderRadius:9999,height:16,width:16,borderBottomWidth:2,borderColor:"#fff",marginRight:8}}></span>
                    {t('appModal.saving')}
                  </>
                ) : t('appModal.saveChanges')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default EditAppModal;