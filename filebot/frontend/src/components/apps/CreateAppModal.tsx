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
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* 背景遮罩 */}
      <div className="fixed inset-0 bg-black opacity-30" onClick={handleCancel}></div>
      
      {/* 模态框 */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="relative bg-white rounded-lg shadow-lg w-full max-w-md">
          {/* 标题 */}
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold text-gray-900">{t('appModal.createAppTitle')}</h3>
            <p className="text-sm text-gray-600 mt-1">{t('appModal.appContainerDescription')}</p>
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 space-y-4">
              {/* 错误提示 */}
              {error && (
                <>
                  {/* Slug冲突智能提示 */}
                  {typeof error !== 'string' && error.type === 'slug_conflict' ? (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <p className="text-sm text-yellow-800 font-medium mb-2">
                        {error.message}
                      </p>
                      <div className="mt-2 p-3 bg-white rounded border border-yellow-100">
                        <p className="font-medium text-gray-800 mb-1">
                          {t('appModal.existingApp')}{error.existingApp.name}
                        </p>
                        <p className="text-xs text-gray-600 mb-2">
                          {t('appModal.id')} {error.existingApp.id}
                        </p>
                        <div className="text-xs text-gray-500 space-y-1 mb-3">
                          <p>{t('appModal.creator')} {error.existingApp.created_by || t('common.unknown')}</p>
                          <p>{t('appModal.creationTime')} {new Date(error.existingApp.created_at).toLocaleString()}</p>
                        </div>
                        <div className="mt-3 flex space-x-2">
                          <button
                            type="button"
                            onClick={() => handleDeleteAndRetry(error.existingApp.id)}
                            className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                            disabled={loading}
                          >
{t('appModal.deleteOldAppAndRetry')}
                          </button>
                          <button
                            type="button"
                            onClick={() => window.open(`/admin/apps/${error.existingApp.slug}`)}
                            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
{t('appModal.viewOldApp')}
                          </button>
                        </div>
                        <p className="text-xs text-yellow-700 mt-2">
                          {t('appModal.deleteTip')}
                        </p>
                      </div>
                    </div>
                  ) : typeof error !== 'string' && error.type === 'permission_denied' ? (
                    /* 权限不足错误提示 */
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      <p className="text-sm text-orange-800 font-medium mb-2">
                        {error.message}
                      </p>
                      <div className="mt-2 p-3 bg-white rounded border border-orange-100">
                        <p className="text-sm text-orange-700 mb-3">
                          {error.details}
                        </p>
                        {error.existingApp && (
                          <>
                            <p className="font-medium text-gray-800 mb-1">
                              {t('appModal.existingApp')}{error.existingApp.name}
                            </p>
                            <div className="text-xs text-gray-500 space-y-1 mb-3">
                              <p>{t('appModal.creator')} {error.existingApp.created_by || t('common.unknown')}</p>
                              <p>{t('appModal.ownerId')} {error.existingApp.owner_id}</p>
                            </div>
                          </>
                        )}
                        <div className="mt-3 space-y-2">
                          <p className="text-xs text-orange-700">
                            {t('appModal.suggestion')}
                          </p>
                          <div className="flex flex-col space-y-2">
                            <button
                              type="button"
                              onClick={() => {
                                // 自动修改slug，添加随机后缀
                                const newSlug = `${formData.slug}-${Math.random().toString(36).substring(2, 6)}`;
                                setFormData(prev => ({ ...prev, slug: newSlug }));
                                setError(null);
                              }}
                              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-left"
                            >
{t('appModal.modifySlugWithSuffix')}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setFormData(prev => ({ ...prev, slug: '' }));
                                setError(null);
                              }}
                              className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 text-left"
                            >
{t('appModal.clearSlugAndInput')}
                            </button>
                            <button
                              type="button"
                              onClick={() => window.open(`/admin/apps/${error.existingApp?.slug}`)}
                              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 text-left"
                              disabled={!error.existingApp}
                            >
{t('appModal.viewExistingAppDetails')}
                            </button>
                          </div>
                          <p className="text-xs text-orange-700 mt-2">
                            {t('appModal.noPermissionSuggestDifferentSlug')}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : typeof error !== 'string' && error.type === 'app_not_found' ? (
                    /* 应用不存在错误提示 */
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <p className="text-sm text-blue-800 font-medium mb-2">
                        {error.message}
                      </p>
                      <p className="text-sm text-blue-700">
                        {error.details}
                      </p>
                      <div className="mt-3">
                        <button
                          type="button"
                          onClick={() => {
                            setError(null);
                          }}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
{t('appModal.retryCreateApp')}
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* 普通错误提示 */
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm text-red-800">{typeof error === 'string' ? error : (error as any)?.message || 'Unknown error'}</p>
                    </div>
                  )}
                </>
              )}

              {/* 应用名称 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
{t('appModal.appNameLabel')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={handleNameChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('appModal.appNamePlaceholder')}
                  disabled={loading}
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1">{t('appModal.appDisplayName')}</p>
              </div>

              {/* 应用标识 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
{t('appModal.appSlugLabel')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={handleSlugChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('appModal.slugPlaceholder')}
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">{t('appModal.slugUsageHint')}</p>
              </div>

              {/* 应用描述 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('appModal.appDescriptionLabel')}
                </label>
                <textarea
                  value={formData.description}
                  onChange={handleDescriptionChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('appModal.appDescriptionPlaceholder')}
                  rows={3}
                  disabled={loading}
                />
              </div>

              {/* 索引字段 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
{t('appModal.documentIndexFields')}
                </label>
                <input
                  type="text"
                  value={formData.settings.indices.join(',')}
                  onChange={handleIndicesChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('appModal.indexFieldsPlaceholder')}
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">{t('appModal.indexFieldsHint')}</p>
              </div>

              {/* 重定向URL - 用于统一仪表板 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
{t('appModal.redirectUrlLabel')}
                </label>
                <input
                  type="text"
                  value={formData.redirect_url || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, redirect_url: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('appModal.redirectUrlPlaceholder')}
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {t('appModal.redirectUrlHint')}
                </p>
              </div>

              {/* Default Entry Path */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
Default Entry Path
                </label>
                <input
                  type="text"
                  value={(formData as any).default_entry || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, default_entry: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g. canadasite"
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
Optional default entry path. When set, clicking this app goes directly to /apps/:slug/:path
                </p>
              </div>

              {/* Icon */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
{t('appModal.iconLabel')}
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={formData.icon || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder={t('appModal.iconPlaceholder')}
                    disabled={loading}
                  />
                  <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                    <span className="text-lg">{formData.icon || '📄'}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {t('appModal.iconHint')}
                </p>
                <div className="text-xs text-gray-500 mt-1">
                  <span className="font-medium">{t('appModal.examples')}</span>
                  <span className="mx-2">{t('appModal.documentManagement')}</span>
                  <span className="mx-2">{t('appModal.webBotApp')}</span>
                  <span className="mx-2">{t('appModal.governmentServices')}</span>
                  <span className="mx-2">{t('appModal.invoiceSystem')}</span>
                  <span className="mx-2">{t('appModal.dataAnalysis')}</span>
                </div>
              </div>
            </div>

            {/* 底部按钮 */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end space-x-3">
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-300"
                disabled={loading}
              >
{t('common.cancel')}
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
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