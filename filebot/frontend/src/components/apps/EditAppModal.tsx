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
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* 背景遮罩 */}
      <div className="fixed inset-0 bg-black opacity-30" onClick={handleCancel}></div>
      
      {/* 模态框 */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="relative bg-white rounded-lg shadow-lg w-full max-w-md">
          {/* 标题 */}
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold text-gray-900">{t('appModal.editApp')}</h3>
            <p className="text-sm text-gray-600 mt-1">{t('appModal.editAppSubtitle')}</p>
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 space-y-4">
              {/* 错误提示 */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              {/* 应用ID显示（只读） */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('appModal.appId')}
                </label>
                <input
                  type="text"
                  value={app.id}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500"
                  readOnly
                  disabled
                />
                <p className="text-xs text-gray-500 mt-1">{t('appModal.appIdDescription')}</p>
              </div>

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
                  value={formData.settings.indices?.join(',') || ''}
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
                  value={formData.redirect_url}
                  onChange={handleRedirectUrlChange}
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
                  value={formData.default_entry}
                  onChange={handleDefaultEntryChange}
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
                    value={formData.icon}
                    onChange={handleIconChange}
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
                  <span className="mx-2">📁 {t('appModal.documentManagement')}</span>
                  <span className="mx-2">🌐 {t('appModal.webBotApp')}</span>
                  <span className="mx-2">🏛️ {t('appModal.governmentServices')}</span>
                  <span className="mx-2">🧾 {t('appModal.invoiceSystem')}</span>
                  <span className="mx-2">🔍 {t('appModal.dataAnalysis')}</span>
                </div>
              </div>

              {/* 创建信息（只读） */}
              <div className="pt-4 border-t border-gray-100">
                <div className="text-sm text-gray-500">
                  <p>{t('appModal.creator')}: {app.created_by || t('common.unknown')}</p>
                  <p>{t('appModal.creationTime')}: {app.created_at ? new Date(app.created_at).toLocaleString() : t('common.unknown')}</p>
                  {app.updated_at && (
                    <p>{t('appModal.lastUpdated')}: {new Date(app.updated_at).toLocaleString()}</p>
                  )}
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