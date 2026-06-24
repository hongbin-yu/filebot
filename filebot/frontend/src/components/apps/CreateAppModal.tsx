import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import appService, { App, CreateAppRequest } from '../../services/app.service';

interface CreateAppModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (app: App) => void;
}

// 智能错误类型
interface SlugConflictError {
  type: 'slug_conflict';
  message: string;
  existingApp: {
    id: string;
    name: string;
    slug: string;
    description: string | null;
    created_at: string;
    created_by: string | null;
    owner_id: string;
  };
}

// 权限不足错误
interface PermissionDeniedError {
  type: 'permission_denied';
  message: string;
  details: string;
  existingApp?: {
    id: string;
    name: string;
    slug: string;
    description: string | null;
    created_at: string;
    created_by: string | null;
    owner_id: string;
  };
}

// 应用不存在错误
interface AppNotFoundError {
  type: 'app_not_found';
  message: string;
  details: string;
}

type AppError = string | SlugConflictError | PermissionDeniedError | AppNotFoundError | null;

const CreateAppModal: React.FC<CreateAppModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<CreateAppRequest>({
    name: '',
    slug: '',
    description: '',
    settings: { indices: [] },
    redirect_url: '',
    icon: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AppError>(null);
  const [currentConflictError, setCurrentConflictError] = useState<SlugConflictError | null>(null);

  // 根据名称自动生成slug
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    setFormData(prev => ({
      ...prev,
      name,
      slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
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

    setLoading(true);
    setError(null);
    setCurrentConflictError(null);

    try {
      // 过滤掉空的索引字段
      const filteredFormData = {
        ...formData,
        settings: {
          ...formData.settings,
          indices: formData.settings.indices.filter(item => item.trim() !== '')
        }
      };
      
      const newApp = await appService.createApp(filteredFormData);
      onSuccess(newApp);
      // 重置表单
      setFormData({
        name: '',
        slug: '',
        description: '',
        settings: { indices: [] }
      });
      onClose();
    } catch (err: any) {
      console.error('创建应用失败:', err);
      
      // 检查是否为slug冲突错误
      if (err.response?.status === 400 && err.response?.data?.detail?.message) {
        const errorDetail = err.response.data.detail;
        if (errorDetail.conflict_type === 'slug' && errorDetail.existing_app) {
          // 智能slug冲突错误
          const slugConflictError = {
            type: 'slug_conflict' as const,
            message: errorDetail.message || t('appModal.slugAlreadyUsed'),
            existingApp: {
              id: errorDetail.existing_app.id,
              name: errorDetail.existing_app.name,
              slug: errorDetail.existing_app.slug,
              description: errorDetail.existing_app.description,
              created_at: errorDetail.existing_app.created_at,
              created_by: errorDetail.existing_app.created_by,
              owner_id: errorDetail.existing_app.owner_id
            }
          };
          setError(slugConflictError);
          setCurrentConflictError(slugConflictError);
          return;
        }
      }
      
      // 普通错误
      setError(err.response?.data?.detail?.message || err.response?.data?.detail || err.message || t('appModal.createAppFailed'));
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

  // 删除现有应用并重试
  const handleDeleteAndRetry = async (appId: string) => {
    setLoading(true);
    try {
      await appService.deleteApp(appId);
      // 重新提交表单
      await handleSubmit(new Event('submit') as unknown as React.FormEvent);
    } catch (err: any) {
      console.error('删除应用失败:', err);
      
      if (err.response?.status === 403) {
        // 权限不足错误
        setError({
          type: 'permission_denied',
          message: t('appModal.noPermissionToDeleteApp'),
          details: t('appModal.permissionDeniedDetails'),
          existingApp: currentConflictError?.existingApp // 保持现有应用信息显示
        });
      } else if (err.response?.status === 404) {
        // 应用不存在
        setError({
          type: 'app_not_found',
          message: t('appModal.appNotFoundOrDeleted'),
          details: t('appModal.appDeletedByOtherUser')
        });
      } else {
        // 其他错误
        setError(t('appModal.deleteExistingAppFailed') + (err.response?.status || t('common.unknown')));
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{position:"fixed",top:0,right:0,bottom:0,left:0,zIndex:50,overflowY:"auto"}}>
      {/* 背景遮罩 */}
      <div style={{opacity:0.3,position:"fixed",top:0,right:0,bottom:0,left:0,backgroundColor:"#000"}} onClick={handleCancel}></div>
      
      {/* 模态框 */}
      <div className="fb-d-flex fb-align-center fb-page-bg" style={{justifyContent:"center",padding:16}}>
        <div style={{position:"relative",backgroundColor:"#fff",borderRadius:8,boxShadow:"0 10px 15px -3px rgba(0,0,0,0.1)",width:"100%",maxWidth:448}}>
          {/* 标题 */}
          <div style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,borderBottom:"1px solid #e5e7eb"}}>
            <h3 style={{fontSize:"1.125rem",lineHeight:"1.75rem",fontWeight:600,color:"#111827"}}>{t('appModal.createAppTitle')}</h3>
            <p className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginTop:4}}>{t('appModal.appContainerDescription')}</p>
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit}>
            <div style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,display:"flex",flexDirection:"column",gap:16}}>
              {/* 错误提示 */}
              {error && (
                <>
                  {/* Slug冲突智能提示 */}
                  {typeof error !== 'string' && error.type === 'slug_conflict' ? (
                    <div style={{backgroundColor:"#fffbeb",border:"1px solid #ddd",borderColor:"#fef08a",borderRadius:8,padding:16}}>
                      <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#854d0e",fontWeight:500,marginBottom:8}}>
                        {error.message}
                      </p>
                      <div style={{borderColor:"#fef9c3",marginTop:8,padding:12,backgroundColor:"#fff",borderRadius:4,border:"1px solid #ddd"}}>
                        <p style={{fontWeight:500,color:"#1f2937",marginBottom:4}}>
                          {t('appModal.existingApp')}{error.existingApp.name}
                        </p>
                        <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginBottom:8}}>
                          {t('appModal.id')} {error.existingApp.id}
                        </p>
                        <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",display:"flex",flexDirection:"column",gap:4,marginBottom:12}}>
                          <p>{t('appModal.creator')} {error.existingApp.created_by || t('common.unknown')}</p>
                          <p>{t('appModal.creationTime')} {new Date(error.existingApp.created_at).toLocaleString()}</p>
                        </div>
                        <div className="fb-d-flex" style={{marginTop:12,display:"flex",gap:8}}>
                          <button
                            type="button"
                            onClick={() => handleDeleteAndRetry(error.existingApp.id)}
                            style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#dc2626",color:"#fff",fontSize:"0.875rem",lineHeight:"1.25rem",borderRadius:4}}
                            disabled={loading}
                          >
{t('appModal.deleteOldAppAndRetry')}
                          </button>
                          <button
                            type="button"
                            onClick={() => window.open(`/admin/apps/${error.existingApp.slug}`)}
                            style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#2563eb",color:"#fff",fontSize:"0.875rem",lineHeight:"1.25rem",borderRadius:4}}
                          >
{t('appModal.viewOldApp')}
                          </button>
                        </div>
                        <p style={{fontSize:"0.75rem",lineHeight:"1rem",color:"#a16207",marginTop:8}}>
                          {t('appModal.deleteTip')}
                        </p>
                      </div>
                    </div>
                  ) : typeof error !== 'string' && error.type === 'permission_denied' ? (
                    /* 权限不足错误提示 */
                    <div style={{backgroundColor:"#fff7ed",borderColor:"#fed7aa",border:"1px solid #ddd",borderRadius:8,padding:16}}>
                      <p style={{color:"#9a3412",fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,marginBottom:8}}>
                        {error.message}
                      </p>
                      <div style={{borderColor:"#ffedd5",marginTop:8,padding:12,backgroundColor:"#fff",borderRadius:4,border:"1px solid #ddd"}}>
                        <p style={{color:"#c2410c",fontSize:"0.875rem",lineHeight:"1.25rem",marginBottom:12}}>
                          {error.details}
                        </p>
                        {error.existingApp && (
                          <>
                            <p style={{fontWeight:500,color:"#1f2937",marginBottom:4}}>
                              {t('appModal.existingApp')}{error.existingApp.name}
                            </p>
                            <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",display:"flex",flexDirection:"column",gap:4,marginBottom:12}}>
                              <p>{t('appModal.creator')} {error.existingApp.created_by || t('common.unknown')}</p>
                              <p>{t('appModal.ownerId')} {error.existingApp.owner_id}</p>
                            </div>
                          </>
                        )}
                        <div style={{marginTop:12,display:"flex",flexDirection:"column",gap:8}}>
                          <p style={{color:"#c2410c",fontSize:"0.75rem",lineHeight:"1rem"}}>
                            {t('appModal.suggestion')}
                          </p>
                          <div className="fb-d-flex" style={{flexDirection:"column",display:"flex",gap:8}}>
                            <button
                              type="button"
                              onClick={() => {
                                // 自动修改slug，添加随机后缀
                                const newSlug = `${formData.slug}-${Math.random().toString(36).substring(2, 6)}`;
                                setFormData(prev => ({ ...prev, slug: newSlug }));
                                setError(null);
                              }}
                              className="text-left" style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#2563eb",color:"#fff",fontSize:"0.875rem",lineHeight:"1.25rem",borderRadius:4}}
                            >
{t('appModal.modifySlugWithSuffix')}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setFormData(prev => ({ ...prev, slug: '' }));
                                setError(null);
                              }}
                              className="bg-gray-600 text-left" style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,color:"#fff",fontSize:"0.875rem",lineHeight:"1.25rem",borderRadius:4}}
                            >
{t('appModal.clearSlugAndInput')}
                            </button>
                            <button
                              type="button"
                              onClick={() => window.open(`/admin/apps/${error.existingApp?.slug}`)}
                              className="text-left" style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#16a34a",color:"#fff",fontSize:"0.875rem",lineHeight:"1.25rem",borderRadius:4}}
                              disabled={!error.existingApp}
                            >
{t('appModal.viewExistingAppDetails')}
                            </button>
                          </div>
                          <p style={{color:"#c2410c",fontSize:"0.75rem",lineHeight:"1rem",marginTop:8}}>
                            {t('appModal.noPermissionSuggestDifferentSlug')}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : typeof error !== 'string' && error.type === 'app_not_found' ? (
                    /* 应用不存在错误提示 */
                    <div style={{backgroundColor:"#eff6ff",border:"1px solid #ddd",borderColor:"#bfdbfe",borderRadius:8,padding:16}}>
                      <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#1e40af",fontWeight:500,marginBottom:8}}>
                        {error.message}
                      </p>
                      <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#1d4ed8"}}>
                        {error.details}
                      </p>
                      <div style={{marginTop:12}}>
                        <button
                          type="button"
                          onClick={() => {
                            setError(null);
                          }}
                          style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,backgroundColor:"#2563eb",color:"#fff",fontSize:"0.875rem",lineHeight:"1.25rem",borderRadius:4}}
                        >
{t('appModal.retryCreateApp')}
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* 普通错误提示 */
                    <div style={{backgroundColor:"#fef2f2",border:"1px solid #ddd",borderColor:"#fecaca",borderRadius:8,padding:12}}>
                      <p style={{fontSize:"0.875rem",lineHeight:"1.25rem",color:"#991b1b"}}>{typeof error === 'string' ? error : (error as any)?.message || 'Unknown error'}</p>
                    </div>
                  )}
                </>
              )}

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
                  value={formData.settings.indices.join(',')}
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
                  value={formData.redirect_url || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, redirect_url: e.target.value }))}
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
                  value={(formData as any).default_entry || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, default_entry: e.target.value }))}
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
                    value={formData.icon || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
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
                  <span style={{marginLeft:8,marginRight:8}}>{t('appModal.documentManagement')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>{t('appModal.webBotApp')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>{t('appModal.governmentServices')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>{t('appModal.invoiceSystem')}</span>
                  <span style={{marginLeft:8,marginRight:8}}>{t('appModal.dataAnalysis')}</span>
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
{t('appModal.creating')}
                  </>
                ) : t('appModal.createApplication')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CreateAppModal;