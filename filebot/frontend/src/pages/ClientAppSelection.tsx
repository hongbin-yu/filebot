import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import appService from '../services/app.service';

const ClientAppSelection: React.FC = () => {
  const navigate = useNavigate();
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApps();
  }, []);

  const fetchApps = async () => {
    try {
      setLoading(true);
      const data = await appService.getApps();
      setApps(data);
    } catch (err: any) {
      console.error('Failed to fetch apps:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAppClick = (app: any) => {
    if (app.redirect_url) {
      window.location.href = app.redirect_url;
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
    if (app.icon) {
      return app.icon;
    }
    return (app.name || '').charAt(0).toUpperCase();
  };

  const getAppType = (app: any) => {
    const icon = app.icon || '';
    const name = app.name || '';
    if (icon.includes('🌐') || name.toLowerCase().includes('web') || name.toLowerCase().includes('bot')) {
      return 'WebBot';
    } else if (icon.includes('📁') || icon.includes('🗂️')) {
      return 'Documents';
    } else if (icon.includes('🏛️') || icon.includes('🏢')) {
      return 'Government';
    } else if (icon.includes('🧾') || icon.includes('💸')) {
      return 'Invoice';
    } else if (icon.includes('🔍') || icon.includes('📊')) {
      return 'Analytics';
    } else {
      return 'App';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="mb-10">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">🏠 Unified Dashboard</h1>
              <p className="text-gray-600 mt-2">All apps in one place - Supports internal apps and external redirects</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">Unified Portal</span>
              <Link 
                to="/admin/apps"
                className="px-4 py-2 border border-blue-600 text-blue-600 rounded hover:bg-blue-50"
              >
                Admin Panel
              </Link>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-700">
              <span className="font-medium">About this dashboard: </span>
              FileBot and WebBot apps are now integrated into a single interface with icon display and external redirect support.
              Click an app card to access the internal app or open an external app (e.g. WebBot).
            </p>
          </div>
        </header>

        {/* Apps Grid */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading apps...</p>
          </div>
        ) : apps.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="text-gray-400 mb-6">
              <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
              </svg>
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">No Apps Available</h3>
            <p className="text-gray-500 mb-6">There are no apps configured yet. Contact an administrator to create one.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {apps.map(app => (
              <div 
                key={app.id}
                className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer border border-gray-200 hover:border-blue-300 hover:transform hover:-translate-y-1"
                onClick={() => handleAppClick(app)}
              >
                <div className="p-6">
                  <div className="flex items-center mb-4">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center mr-4" 
                         style={{ 
                           backgroundColor: app.icon && app.icon.includes('🌐') ? '#E0F2FE' : 
                                         app.icon && app.icon.includes('🏛️') ? '#FEF3C7' :
                                         app.icon && app.icon.includes('🧾') ? '#DCFCE7' :
                                         '#E0E7FF'
                         }}>
                      <span className="text-2xl">
                        {getAppIcon(app)}
                      </span>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-gray-800">{app.name}</h3>
                      <div className="flex items-center mt-1">
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                          {getAppType(app)}
                        </span>
                        {app.redirect_url && (
                          <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                            External
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <p className="text-gray-600 mb-4">{app.description || 'No description'}</p>
                  
                  {app.redirect_url && (
                    <div className="mb-4 p-2 bg-blue-50 rounded border border-blue-100">
                      <p className="text-xs text-blue-800 truncate">
                        <span className="font-medium">Redirects to: </span> {app.redirect_url}
                      </p>
                    </div>
                  )}
                  
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500">
                      {app.redirect_url ? 'Click to open external app' : 'Click to enter'}
                    </span>
                    <span className="text-blue-600 font-medium">
                      {app.redirect_url ? '↗' : '→'}
                    </span>
                  </div>
                </div>
                <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>ID: {app.id.substring(0, 8)}...</span>
                    {app.redirect_url ? (
                      <span className="text-blue-600">External Link</span>
                    ) : (
                      <span>Internal</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-8 border-t border-gray-200">
          <div className="text-center text-gray-500 text-sm">
            <p>🏠 Unified Dashboard - All apps integrated in one interface</p>
            <p className="mt-1">
              Supports internal apps and external redirect apps (e.g. WebBot) - 
              <span className="text-blue-600 ml-1">Icons: </span> 
              <span className="mx-2">📁 Documents</span>
              <span className="mx-2">🌐 WebBot</span>
              <span className="mx-2">🏛️ Government</span>
              <span className="mx-2">🧾 Invoice</span>
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default ClientAppSelection;