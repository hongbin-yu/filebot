import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../../services/auth.service';
import { useCopilot } from '../../contexts/CopilotContext';

const Navbar: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();
  const user = authService.getCurrentUser();
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
          {/* Left Side: User Info */}
          <div className="flex items-center">
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <div className="flex items-center">
                  <div style={{ padding: '0.5rem', backgroundColor: '#f0f9ff', borderRadius: '9999px', marginRight: '0.75rem' }}>
                    <svg style={{ width: '2rem', height: '2rem', color: '#2563eb' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <span className="text-gray-700">
                    Welcome, {user?.username || 'User'}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  style={{ backgroundColor: '#ef4444', color: 'white', paddingLeft: '1rem', paddingRight: '1rem', paddingTop: '0.5rem', paddingBottom: '0.5rem', borderRadius: '0.25rem' }}
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <Link
                  to="/login"
                  className="text-gray-700 hover:text-blue-600"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  style={{ backgroundColor: '#3b82f6', color: 'white', paddingLeft: '1rem', paddingRight: '1rem', paddingTop: '0.5rem', paddingBottom: '0.5rem', borderRadius: '0.25rem' }}
                >
                  Register
                </Link>
              </div>
            )}
          </div>

          {/* Center: Navigation Menu */}
          <div className="hidden md:flex items-center space-x-6">
            <Link to="/" className="text-gray-700 hover:text-blue-600">
              Dashboard
            </Link>
            <Link to="/documents" className="text-gray-700 hover:text-blue-600">
              Documents
            </Link>
            <Link to="/folders" className="text-gray-700 hover:text-blue-600">
              Folders
            </Link>
            <Link to="/upload" className="text-gray-700 hover:text-blue-600">
              Upload
            </Link>
          </div>

          {/* Right Side: FileBot Button */}
          <div className="flex items-center">
            <button
              className="text-3xl font-bold text-blue-600 hover:text-blue-800 focus:outline-none"
              onClick={openCopilot}
            >
              FileBot 🗂️
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
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
          </div>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden bg-white py-4">
            <div className="flex flex-col space-y-4">
              {/* FileBot Button for Mobile */}
              <button
                className="text-2xl font-bold text-blue-600 hover:text-blue-800 text-left p-2 bg-blue-50 rounded-lg mb-2"
                onClick={() => {
                  openCopilot();
                  setIsMenuOpen(false);
                }}
              >
                FileBot 🗂️ - Open Assistant
              </button>
              
              <Link to="/" className="text-gray-700 hover:text-blue-600" onClick={() => setIsMenuOpen(false)}>
                Dashboard
              </Link>
              <Link to="/documents" className="text-gray-700 hover:text-blue-600" onClick={() => setIsMenuOpen(false)}>
                Documents
              </Link>
              <Link to="/folders" className="text-gray-700 hover:text-blue-600" onClick={() => setIsMenuOpen(false)}>
                Folders
              </Link>
              <Link to="/upload" className="text-gray-700 hover:text-blue-600" onClick={() => setIsMenuOpen(false)}>
                Upload
              </Link>

              {isAuthenticated ? (
                <>
                  <div className="flex items-center text-gray-700 pt-4 border-t">
                    <div className="p-2 bg-blue-100 rounded-full mr-3">
                      <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <span>
                      Welcome, {user?.username || 'User'}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      handleLogout();
                      setIsMenuOpen(false);
                    }}
                    style={{ backgroundColor: '#ef4444', color: 'white', paddingLeft: '1rem', paddingRight: '1rem', paddingTop: '0.5rem', paddingBottom: '0.5rem', borderRadius: '0.25rem' }}
                  >
                    Logout
                  </button>
                </>
              ) : (
                <div className="flex flex-col space-y-2 pt-4 border-t">
                  <Link
                    to="/login"
                    className="text-gray-700 hover:text-blue-600"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Login
                  </Link>
                  <Link
                    to="/register"
                    style={{ backgroundColor: '#3b82f6', color: 'white', paddingLeft: '1rem', paddingRight: '1rem', paddingTop: '0.5rem', paddingBottom: '0.5rem', borderRadius: '0.25rem', textAlign: 'center' }}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
    </>
  );
};

export default Navbar;