import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/auth.service';
import i18n from '../i18n';
import { useTranslation } from 'react-i18next';

const ClientLogin: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) { setError(t('clientLogin.enterUsernamePassword')); return; }
    try {
      setLoading(true); setError(null);
      const response = await authService.login({ username, password });
      if (rememberMe) localStorage.setItem('client_remember', 'true');
      navigate('/client/apps');
    } catch (err: any) {
      console.error(t('clientLogin.clientLoginFailed'), err);
      if (err.response?.status === 401) setError(t('clientLogin.invalidUsernamePassword'));
      else if (err.response?.status === 403) setError(t('clientLogin.noClientAccess'));
      else if (err.response?.data?.detail) setError(err.response.data.detail);
      else if (err.message) setError(err.message);
      else setError(t('clientLogin.loginFailed'));
    } finally { setLoading(false); }
  };

  const handleDemoLogin = () => { setUsername('demo-client'); setPassword('demo123'); };
  const handleBackToMain = () => navigate('/login');

  return (
    <div className="fb-page-bg">
      <div className="container">
        <div className="row">
          <div className="col-md-6 col-md-offset-3" style={{ paddingTop: 40 }}>
            <div className="text-center" style={{ marginBottom: 25 }}>
              <p style={{ fontSize: '3em', margin: 0 }}>📋</p>
              <h1>{t('clientLogin.portalTitle')}</h1>
              <p className="text-muted">{t('clientLogin.portalSubtitle')}</p>
            </div>

            <div className="panel panel-default">
              <div className="panel-body" style={{ padding: 30 }}>
                <h3 className="panel-title" style={{ marginBottom: 5 }}>{t('clientLogin.loginTitle')}</h3>
                <p className="text-muted" style={{ marginBottom: 20 }}>{t('clientLogin.loginInstruction')}</p>

                {error && <div className="alert alert-danger">{error}</div>}

                <form onSubmit={handleSubmit}>
                  <div className="form-group">
                    <label htmlFor="username">{t('clientLogin.usernameLabel')}</label>
                    <input id="username" type="text" className="form-control"
                      value={username} onChange={e => setUsername(e.target.value)}
                      placeholder={t('clientLogin.usernamePlaceholder')} disabled={loading} required />
                  </div>
                  <div className="form-group">
                    <label htmlFor="password">{t('clientLogin.passwordLabel')}</label>
                    <input id="password" type="password" className="form-control"
                      value={password} onChange={e => setPassword(e.target.value)}
                      placeholder={t('clientLogin.passwordPlaceholder')} disabled={loading} required />
                  </div>
                  <div className="checkbox">
                    <label>
                      <input type="checkbox" checked={rememberMe}
                        onChange={e => setRememberMe(e.target.checked)} disabled={loading} />
                      {t('clientLogin.rememberMe')}
                    </label>
                    <button type="button" className="btn btn-link btn-xs pull-right text-muted"
                      onClick={() => window.showWetAlert('Please contact the administrator to reset your password')}
                      disabled={loading}>{t('clientLogin.forgotPassword')}</button>
                  </div>

                  <button type="submit" className={'btn btn-primary btn-block' + (loading ? ' disabled' : '')}
                    disabled={loading} style={{ marginTop: 10 }}>
                    {loading ? t('clientLogin.signingIn') : t('clientLogin.signIn')}
                  </button>
                  <button type="button" onClick={handleDemoLogin} disabled={loading}
                    className="btn btn-default btn-block" style={{ marginTop: 8 }}>
                    {t('clientLogin.useDemoAccount')}
                  </button>
                </form>

                <hr />
                <div className="text-center">
                  <p className="text-muted" style={{ fontSize: '0.85em' }}>{t('clientLogin.needManagementAccess')}</p>
                  <button type="button" onClick={handleBackToMain} className="btn btn-link" disabled={loading}>
                    {t('clientLogin.backToMainLogin')} →
                  </button>
                </div>
              </div>
            </div>

            <div className="text-center text-muted" style={{ marginTop: 25, fontSize: '0.8em' }}>
              <p>© 2026 FileBot Client Portal. {t('clientLogin.footerForAuthorizedUsers')}</p>
              <p>{t('clientLogin.footerReadOnlyInterface')}</p>
              <div className="alert alert-info text-left" style={{ marginTop: 15, fontSize: '0.85em' }}>
                <strong>{t('clientLogin.note')}:</strong> {t('clientLogin.portalPdfOnly')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientLogin;
