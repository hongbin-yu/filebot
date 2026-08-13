import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import appService from '../services/app.service';
import authService from '../services/auth.service';

const ClientAppSelection: React.FC = () => {
  const navigate = useNavigate();
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApps();
    if (authService.isAuthenticated()) {
      authService.getCurrentUser().catch(() => {});
    }
  }, []);

  const fetchApps = async () => {
    try {
      setLoading(true);
      const data = await appService.getClientApps();
      setApps(data);
    } catch (err: any) {
      console.error('Failed to fetch apps:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAppClick = (app: any) => {
    if (app.redirect_url) {
      var url = app.redirect_url;
      if (url.indexOf('localhost:8000') >= 0 || url.indexOf('127.0.0.1:8000') >= 0) {
        var token = localStorage.getItem('access_token');
        if (token) {
          var sep = url.indexOf('?') >= 0 ? '&' : '?';
          url = url + sep + 'token=' + encodeURIComponent(token);
        }
      }
      window.location.href = url;
      return;
    }
    const appSlug = app.slug || app.id;
    if (app.default_entry) {
      navigate(`/apps/${appSlug}/${app.default_entry}`);
    } else {
      navigate(`/apps/${appSlug}`);
    }
  };

  const getAppIcon = (app: any) => {
    return app.icon || (app.name || '').charAt(0).toUpperCase();
  };

  const getAppType = (app: any) => {
    const name = (app.name || '').toLowerCase();
    if (name.includes('web') || name.includes('bot')) return 'WebBot';
    if (name.includes('doc')) return 'Documents';
    if (name.includes('gov')) return 'Government';
    if (name.includes('invoice')) return 'Invoice';
    return 'App';
  };

  const isAdmin = authService.isAdmin();

  return (
    <div>
      {/* Header */}
      <div className="fb-page-header">
        <div className="fb-d-flex fb-justify-between fb-align-center">
          <h1 className="fb-apps-title">
            🏠 WebFileBot
          </h1>
          <div className="fb-d-flex fb-align-center fb-gap-2">
            {authService.isAuthenticated() ? (
              <>
                <button
                  onClick={() => { authService.logout(); window.location.href = '/login'; }}
                  className="btn btn-default"
                >
                  Logout
                </button>
                {isAdmin && (
                  <Link to="/admin/apps" className="btn btn-primary">
                    Admin Panel
                  </Link>
                )}
              </>
            ) : (
              <Link to="/login" className="btn btn-primary">Login</Link>
            )}
          </div>
        </div>
        <div className="alert alert-info mt-4">
          FileBot and WebBot apps are integrated into a single interface. Click an app card to access it.
        </div>
      </div>

      {/* Apps Grid */}
      {loading ? (
        <div className="fb-loading">
          <div className="text-center">
            <div className="spinner-border fb-spinner-lg" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="text-muted mt-3">Loading apps...</p>
          </div>
        </div>
      ) : apps.length === 0 ? (
        <div className="fb-panel">
          <div className="fb-panel-body fb-empty-state">
            <p className="fb-apps-empty-icon">🏢</p>
            <h3>No Apps Available</h3>
            <p className="text-muted">There are no apps configured yet. Contact an administrator to create one.</p>
          </div>
        </div>
      ) : (
        <div className="row fb-apps-grid">
          {apps.map(app => (
            <div className="col-md-4 fb-apps-grid-col" key={app.id}>
              <div onClick={() => handleAppClick(app)}
                className="panel panel-info fb-apps-card"
              >
                <div className="panel-body fb-apps-card-body">
                  <div className="fb-d-flex fb-align-center fb-apps-card-row">
                    <span className="fb-apps-card-icon">
                      {getAppIcon(app)}
                    </span>
                    <div className="fb-flex-1">
                      <h3 className="fb-apps-card-title">
                        {app.name}
                      </h3>
                      <div className="fb-apps-card-labels">
                        <span className="label label-default">{getAppType(app)}</span>
                        {app.redirect_url && (
                          <span className="label label-primary ml-1">External</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <p className="text-muted mb-3">
                    {app.description || 'No description'}
                  </p>
                  {app.redirect_url && (
                    <div className="alert alert-info fb-apps-card-alert">
                      <span className="fb-text-truncate">
                        Redirects to: {app.redirect_url}
                      </span>
                    </div>
                  )}
                  <div className="fb-d-flex fb-justify-between fb-align-center text-muted fb-apps-card-footer">
                    <span>{app.redirect_url ? 'Click to open external app' : 'Click to enter'}</span>
                    <span className="fb-apps-card-arrow">
                      {app.redirect_url ? '↗' : '→'}
                    </span>
                  </div>
                </div>
                <div className="panel-footer fb-apps-card-pf">
                  ID: {app.id.substring(0, 8)}... &nbsp;|&nbsp;
                  {app.redirect_url ? 'External Link' : 'Internal App'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ClientAppSelection;
