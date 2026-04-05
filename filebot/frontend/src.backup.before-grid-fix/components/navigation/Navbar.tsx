import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../../services/auth.service';
import { useCopilot } from '../../contexts/CopilotContext';

const Navbar: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();
  const user = authService.getUserInfo();
  const { openCopilot } = useCopilot();

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
            <Link to="/" className="text-2xl font-bold text-blue-600 hover:text-blue-800">
              FileBot
            </Link>
          </div>

          {/* Right Side: FileBot Icon for Chat Window Toggle */}
          <div className="flex items-center">
            <button
              className="text-3xl font-bold text-blue-600 hover:text-blue-800 focus:outline-none"
              onClick={openCopilot}
              title="Toggle FileBot Assistant Chat Window"
            >
              🗂️
            </button>
          </div>
        </div>

        {/* Dropdown Menu (for both mobile and desktop) */}
        {isMenuOpen && (
          <div className="bg-white shadow-lg border-t border-gray-100 py-4">
            <div className="flex flex-col space-y-3 px-4">
              {/* Navigation Links */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Navigation
                </h3>
                <Link to="/" className="block text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-2 rounded" onClick={() => setIsMenuOpen(false)}>
                  Dashboard
                </Link>
                <Link to="/documents" className="block text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-2 rounded" onClick={() => setIsMenuOpen(false)}>
                  Documents
                </Link>
                <Link to="/folders" className="block text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-2 rounded" onClick={() => setIsMenuOpen(false)}>
                  Folders
                </Link>
                <Link to="/upload" className="block text-gray-700 hover:text-blue-600 hover:bg-blue-50 p-2 rounded" onClick={() => setIsMenuOpen(false)}>
                  Upload
                </Link>
              </div>

              {/* User Section */}
              {isAuthenticated ? (
                <>
                  <div className="border-t border-gray-100 pt-4">
                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      User
                    </h3>
                    <div className="flex items-center p-2 bg-blue-50 rounded-lg">
                      <div className="p-2 bg-blue-100 rounded-full mr-3">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{user?.username || 'User'}</p>
                        <p className="text-sm text-gray-500">Welcome back!</p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        handleLogout();
                        setIsMenuOpen(false);
                      }}
                      className="w-full mt-3 bg-red-50 hover:bg-red-100 text-red-700 font-medium py-2 px-4 rounded-lg border border-red-200 transition-colors"
                    >
                      Logout
                    </button>
                  </div>
                </>
              ) : (
                <div className="border-t border-gray-100 pt-4">
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Account
                  </h3>
                  <div className="space-y-2">
                    <Link
                      to="/login"
                      className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Login
                    </Link>
                    <Link
                      to="/register"
                      className="block text-center border border-blue-600 text-blue-600 hover:bg-blue-50 font-medium py-2 px-4 rounded-lg transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Register
                    </Link>
                  </div>
                </div>
              )}

              {/* FileBot Assistant Quick Action */}
              <div className="border-t border-gray-100 pt-4">
                <button
                  className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-bold py-3 px-4 rounded-lg shadow-md transition-all transform hover:scale-[1.02]"
                  onClick={() => {
                    openCopilot();
                    setIsMenuOpen(false);
                  }}
                >
                  <span className="flex items-center justify-center">
                    <span className="text-xl mr-2">🗂️</span>
                    <span>Open FileBot Assistant</span>
                  </span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
    </>
  );
};

export default Navbar;