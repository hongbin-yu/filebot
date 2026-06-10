import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../../services/auth.service';
import { useCopilot } from '../../contexts/CopilotContext';
import { changeLanguage, getCurrentLanguage } from '../../i18n';

const Navbar: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();
  const user = authService.getUserInfo();
  const { openCopilot } = useCopilot();
  const [currentLang, setCurrentLang] = useState(getCurrentLanguage());
  const [showLangMenu, setShowLangMenu] = useState(false);

  const switchLanguage = (lng: string) => {
    changeLanguage(lng);
    setCurrentLang(lng);
    setShowLangMenu(false);
  };

  const langLabels: Record<string, string> = {
    en: 'EN',
    fr: 'FR',
    zh: '中文',
  };

  // 页面加载时获取完整用户信息（含 group 成员关系）
  useEffect(() => {
    if (isAuthenticated) {
      authService.getCurrentUser().catch(() => {/* 静默失败，使用缓存数据 */});
    }
  }, []);

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <>
    <nav className="bg-white shadow-md">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Left Side: App Logo/Brand with Hamburger Menu */}
          <div className="flex items-center space-x-4">
            {/* Hamburger Menu Button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-700 focus:outline-none"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
            
            {/* FileBot Text */}
            <Link to="/admin/apps" className="text-2xl font-bold text-blue-600 hover:text-blue-800">
              FileBot
            </Link>
          </div>

          {/* Right Side: Language + User Info + Logout + Chat */}
          <div className="flex items-center space-x-4">
            {/* Language Switcher */}
            <div className="relative">
              <button
                onClick={() => setShowLangMenu(!showLangMenu)}
                className="flex items-center text-sm text-gray-600 hover:text-blue-600 px-2 py-1 rounded border border-gray-300 hover:border-blue-400 transition-colors"
                title="Switch language"
              >
                <span>{langLabels[currentLang] || 'EN'}</span>
                <svg className="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showLangMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowLangMenu(false)} />
                  <div className="absolute right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-[100px]">
                    {Object.entries(langLabels).map(([code, label]) => (
                      <button
                        key={code}
                        onClick={() => switchLanguage(code)}
                        className={`block w-full text-left px-4 py-2 text-sm hover:bg-blue-50 first:rounded-t-lg last:rounded-b-lg ${currentLang === code ? 'text-blue-600 font-semibold bg-blue-50' : 'text-gray-700'}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
            {isAuthenticated && user ? (
              <>
                <span className="text-sm text-gray-700 font-medium hidden sm:inline">
                  {user.full_name || user.username}
                </span>
                <button
                  onClick={handleLogout}
                  className="flex items-center text-sm text-gray-500 hover:text-red-600 transition-colors"
                  title="Logout"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span className="hidden sm:inline ml-1">Logout</span>
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="text-sm font-medium text-blue-600 hover:text-blue-800"
              >
                Login
              </Link>
            )}
            <button
              className="text-3xl font-bold text-blue-600 hover:text-blue-800 focus:outline-none"
              onClick={openCopilot}
              title="Toggle FileBot Assistant Chat Window"
            >
              🗂️
            </button>
          </div>
        </div>

      </div>
      
      {/* Overlay and Sidebar Navigation Menu */}
      {isMenuOpen && (
        <>
          {/* Overlay */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={() => setIsMenuOpen(false)}
          />
          
          {/* Sidebar Navigation Menu - 30% screen width */}
          <div className="fixed inset-y-0 left-0 w-full md:w-1/2 lg:w-1/3 bg-white shadow-xl z-50 overflow-y-auto">
            <div className="p-6 h-full flex flex-col">
              {/* Sidebar Header */}
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-xl font-bold text-gray-800">Navigation</h2>
                <button
                  onClick={() => setIsMenuOpen(false)}
                  className="text-gray-500 hover:text-gray-700 p-2 rounded-full hover:bg-gray-100"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {/* Navigation Links */}
              <div className="space-y-2 mb-8">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Main Navigation
                </h3>
                <Link 
                  to="/apps" 
                  className="flex items-center text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-3 rounded-lg transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  <span className="font-medium">Dashboard</span>
                </Link>
                
                <Link 
                  to="/admin/apps" 
                  className="flex items-center text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-3 rounded-lg transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  <span className="font-medium">Applications</span>
                </Link>
                
                <Link 
                  to="/admin/tasks" 
                  className="flex items-center text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-3 rounded-lg transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="font-medium">Task Monitor</span>
                </Link>
                
  {authService.isAdmin() && (
                <>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 mt-6">
                  Admin
                </h3>
                <Link 
                  to="/admin/groups" 
                  className="flex items-center text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-3 rounded-lg transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span className="font-medium">User Groups</span>
                </Link>
                
                <Link 
                  to="/admin/permissions" 
                  className="flex items-center text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-3 rounded-lg transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span className="font-medium">Permissions</span>
                </Link>

                <Link 
                  to="/admin/users" 
                  className="flex items-center text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-3 rounded-lg transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span className="font-medium">Users</span>
                </Link>
                </>
              )}
                
                <div className="flex items-center text-gray-400 p-3 rounded-lg cursor-not-allowed">
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div>
                    <span className="font-medium">Documents</span>
                    <div className="text-xs text-gray-500 mt-1">
                      Available after selecting an application
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center text-gray-400 p-3 rounded-lg cursor-not-allowed">
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <div>
                    <span className="font-medium">Folders</span>
                    <div className="text-xs text-gray-500 mt-1">
                      Available after selecting an application
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center text-gray-400 p-3 rounded-lg cursor-not-allowed">
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <div>
                    <span className="font-medium">Upload</span>
                    <div className="text-xs text-gray-500 mt-1">
                      Available after selecting a folder
                    </div>
                  </div>
                </div>
              </div>
              
              {/* User Section */}
              {isAuthenticated ? (
                <div className="mt-auto">
                  <div className="border-t border-gray-200 pt-6">
                    <div className="flex items-center mb-6">
                      <div className="p-3 bg-blue-100 rounded-full mr-4">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-bold text-gray-900">{user?.username || 'User'}</p>
                        <p className="text-sm text-gray-500">Logged in</p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        handleLogout();
                        setIsMenuOpen(false);
                      }}
                      className="w-full bg-red-50 hover:bg-red-100 text-red-700 font-medium py-3 px-4 rounded-lg border border-red-200 transition-colors flex items-center justify-center"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      Logout
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-auto">
                  <div className="border-t border-gray-200 pt-6">
                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                      Account
                    </h3>
                    <div className="space-y-3">
                      <Link
                        to="/login"
                        className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors"
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Login
                      </Link>
                      <Link
                        to="/register"
                        className="block text-center border-2 border-blue-600 text-blue-600 hover:bg-blue-50 font-bold py-3 px-4 rounded-lg transition-colors"
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Create Account
                      </Link>
                    </div>
                  </div>
                </div>
              )}
              
              {/* FileBot Assistant Quick Action */}
              <div className="mt-8">
                <button
                  className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-bold py-4 px-4 rounded-xl shadow-lg transition-all transform hover:scale-[1.02]"
                  onClick={() => {
                    openCopilot();
                    setIsMenuOpen(false);
                  }}
                >
                  <span className="flex items-center justify-center">
                    <span className="text-2xl mr-3">🗂️</span>
                    <span className="text-lg">Open FileBot Assistant</span>
                  </span>
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </nav>
    </>
  );
};

export default Navbar;