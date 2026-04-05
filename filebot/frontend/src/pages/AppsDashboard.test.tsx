import React from 'react';

const AppsDashboardTest: React.FC = () => {
  return (
    <div className="min-h-screen bg-green-100 flex flex-col items-center justify-center p-8">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
        <h1 className="text-2xl font-bold text-green-800 mb-4">✅ TEST SUCCESSFUL</h1>
        <p className="text-gray-700 mb-6">
          React is rendering correctly! This confirms the frontend framework is working.
        </p>
        
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 rounded border border-blue-200">
            <h2 className="font-semibold text-blue-800">Possible Issues:</h2>
            <ul className="mt-2 text-sm text-blue-700 space-y-1">
              <li>• API Authentication Failed (401 Error)</li>
              <li>• Token expired or missing</li>
              <li>• Backend API not running</li>
              <li>• JavaScript runtime error</li>
            </ul>
          </div>
          
          <div className="p-4 bg-yellow-50 rounded border border-yellow-200">
            <h2 className="font-semibold text-yellow-800">Next Steps:</h2>
            <ol className="mt-2 text-sm text-yellow-700 space-y-1">
              <li>1. Press F12 → Open Browser Developer Tools</li>
              <li>2. Check "Console" tab for JavaScript errors</li>
              <li>3. Check "Network" tab for failed requests</li>
              <li>4. Try direct login page: <code>/login</code></li>
              <li>5. Clear localStorage and refresh</li>
            </ol>
          </div>
          
          <div className="p-4 bg-green-50 rounded border border-green-200">
            <h2 className="font-semibold text-green-800">Quick Test:</h2>
            <p className="mt-2 text-sm text-green-700">
              If you can see this green page, React is working. The issue is likely:
              <strong> API authentication or data loading.</strong>
            </p>
          </div>
        </div>
        
        <button 
          onClick={() => window.location.href = '/login'}
          className="mt-6 w-full py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
        >
          Go to Login Page
        </button>
        
        <button 
          onClick={() => {
            localStorage.clear();
            window.location.reload();
          }}
          className="mt-3 w-full py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
        >
          Clear LocalStorage & Refresh
        </button>
      </div>
    </div>
  );
};

export default AppsDashboardTest;