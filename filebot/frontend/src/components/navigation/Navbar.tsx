import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../../services/auth.service';
import { useCopilot } from '../../contexts/CopilotContext';
import { changeLanguage, getCurrentLanguage } from '../../i18n';

const Navbar: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showAdminMenu, setShowAdminMenu] = useState(false);
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();
  const user = authService.getUserInfo();
  const isAdmin = authService.isAdmin();
  const { openCopilot } = useCopilot();
  const [currentLang, setCurrentLang] = useState(getCurrentLanguage());
  const [showLangMenu, setShowLangMenu] = useState(false);

  const switchLanguage = (lng: string) => {
    changeLanguage(lng);
    setCurrentLang(lng);
    setShowLangMenu(false);
  };

  const langLabels: Record<string, string> = { en: 'EN', fr: 'FR', zh: '中文' };

  useEffect(() => {
    if (isAuthenticated) {
      authService.getCurrentUser().catch(() => {});
    }
  }, []);

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  // Build WET-style main navigation items
  const navItems: { label: string; to?: string; icon?: React.ReactNode; admin?: boolean }[] = [
    { label: 'Dashboard', to: '/apps', icon: '🏠' },
    { label: 'Applications', to: '/admin/apps', icon: '📦' },
    { label: 'Task Monitor', to: '/admin/tasks', icon: '⏱' },
  ];

  const adminItems = [
    { label: 'User Groups', to: '/admin/groups' },
    { label: 'Permissions', to: '/admin/permissions' },
    { label: 'Users', to: '/admin/users' },
    { label: 'Institutions', to: '/admin/institutions' },
  ];

  return (
    <>
      {/* WET-style navigation bar */}
      <nav className="fb-navbar" role="navigation">
        <div className="container-fluid">
          <div className="fb-d-flex fb-align-center" style={{ minHeight: 50 }}>
            {/* Hamburger */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="btn btn-link visible-xs visible-sm"
              style={{ fontSize: 20, padding: '4px 8px', marginRight: 4 }}
              aria-label="Toggle menu"
            >
              {isMenuOpen ? '✕' : '☰'}
            </button>

            {/* Brand */}
            <Link to="/admin/apps" className="fb-brand" style={{ marginRight: 30 }}>
              FileBot
            </Link>

            {/* Desktop nav links */}
            <div className="hidden-xs hidden-sm fb-d-flex fb-align-center fb-gap-2" style={{ fontSize: '0.95em' }}>
              {navItems.map(item => (
                <Link key={item.to} to={item.to!} className="fb-d-flex fb-align-center"
                  style={{ padding: '8px 12px', color: '#555', textDecoration: 'none', borderRadius: 3 }}>
                  {item.label}
                </Link>
              ))}

              {/* Admin dropdown */}
              {isAdmin && (
                <div style={{ position: 'relative' }}>
                  <button
                    onClick={() => setShowAdminMenu(!showAdminMenu)}
                    className="fb-d-flex fb-align-center"
                    style={{ padding: '8px 12px', color: '#555', background: 'none', border: 'none', borderRadius: 3, cursor: 'pointer', fontSize: '0.95em' }}
                  >
                    Admin ▾
                  </button>
                  {showAdminMenu && (
                    <>
                      <div style={{ position: 'fixed', inset: 0, zIndex: 10 }} onClick={() => setShowAdminMenu(false)} />
                      <ul className="list-unstyled" style={{
                        position: 'absolute', left: 0, top: '100%', zIndex: 20,
                        background: '#fff', border: '1px solid #ddd', borderRadius: 4,
                        minWidth: 160, boxShadow: '0 2px 8px rgba(0,0,0,.1)'
                      }}>
                        {adminItems.map(item => (
                          <li key={item.to}>
                            <Link to={item.to} onClick={() => setShowAdminMenu(false)}
                              style={{ display: 'block', padding: '8px 16px', color: '#333', textDecoration: 'none' }}>
                              {item.label}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Spacer */}
            <div className="fb-flex-1" />

            {/* Right side controls */}
            <div className="fb-d-flex fb-align-center fb-gap-2">
              {/* Language switcher */}
              <div className="hidden-xs" style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowLangMenu(!showLangMenu)}
                  className="btn btn-default btn-sm"
                >
                  {langLabels[currentLang] || 'EN'} ▾
                </button>
                {showLangMenu && (
                  <>
                    <div style={{ position: 'fixed', inset: 0, zIndex: 10 }} onClick={() => setShowLangMenu(false)} />
                    <ul className="list-unstyled" style={{
                      position: 'absolute', right: 0, top: '100%', zIndex: 20,
                      background: '#fff', border: '1px solid #ddd', borderRadius: 4,
                      minWidth: 100, boxShadow: '0 2px 8px rgba(0,0,0,.1)'
                    }}>
                      {Object.entries(langLabels).map(([code, label]) => (
                        <li key={code}>
                          <button onClick={() => switchLanguage(code)}
                            className="btn btn-link btn-block text-left"
                            style={{ fontWeight: currentLang === code ? 'bold' : 'normal', color: currentLang === code ? '#2572b4' : '#333' }}>
                            {label}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>

              {isAuthenticated && user ? (
                <>
                  <span className="hidden-xs hidden-sm text-muted" style={{ fontSize: '0.9em' }}>
                    {user.full_name || user.username}
                  </span>
                  <button onClick={handleLogout} className="btn btn-link" title="Logout"
                    style={{ color: '#666', padding: '4px 8px' }}>
                    ⏻
                  </button>
                </>
              ) : (
                <Link to="/login" className="btn btn-link" style={{ color: '#2572b4' }}>Login</Link>
              )}

              {/* Assistant button */}
              <button className="btn btn-link hidden-xs" onClick={openCopilot}
                style={{ fontSize: '1.5em', padding: '0 6px' }} title="Chat">
                🗂️
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Slide-out sidebar menu (mobile) */}
      {isMenuOpen && (
        <>
          <div className="visible-xs visible-sm"
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 40 }}
            onClick={() => setIsMenuOpen(false)} />
          <div className="visible-xs visible-sm"
            style={{
              position: 'fixed', top: 0, left: 0, bottom: 0, width: '75%', maxWidth: 320,
              background: '#fff', zIndex: 50, overflowY: 'auto', boxShadow: '2px 0 12px rgba(0,0,0,.2)'
            }}>
            <div style={{ padding: 20 }}>
              <div className="fb-d-flex fb-justify-between fb-align-center" style={{ marginBottom: 24 }}>
                <strong style={{ fontSize: '1.2em' }}>Navigation</strong>
                <button onClick={() => setIsMenuOpen(false)} className="btn btn-link"
                  style={{ fontSize: 20, padding: 0 }}>✕</button>
              </div>

              <div className="fb-sidebar-cat">Main</div>
              <ul className="fb-sidebar-nav">
                {navItems.map(item => (
                  <li key={item.to}>
                    <Link to={item.to!} onClick={() => setIsMenuOpen(false)}>
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>

              {authService.isAdmin() && (
                <>
                  <div className="fb-sidebar-cat">Admin</div>
                  <ul className="fb-sidebar-nav">
                    {adminItems.map(item => (
                      <li key={item.to}>
                        <Link to={item.to} onClick={() => setIsMenuOpen(false)}>
                          {item.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {/* Mobile language switcher */}
              <div className="fb-sidebar-cat">Language</div>
              <div style={{ padding: '0 12px' }}>
                {Object.entries(langLabels).map(([code, label]) => (
                  <button key={code}
                    onClick={() => { switchLanguage(code); setIsMenuOpen(false); }}
                    className={`btn btn-sm ${currentLang === code ? 'btn-primary' : 'btn-default'}`}
                    style={{ marginRight: 4, marginBottom: 4 }}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default Navbar;
