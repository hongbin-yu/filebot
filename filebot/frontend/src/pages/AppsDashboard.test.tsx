import React from 'react';

const AppsDashboardTest: React.FC = () => {
  return (
    <div className="fb-d-flex fb-flex-col fb-align-center fb-justify-center" style={{minHeight:"100vh",background:"#dcfce7",padding:32}}>
      <div className="panel panel-default" style={{padding:32,maxWidth:448,width:"100%"}}>
        <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#166534",marginBottom:16}}>✅ TEST SUCCESSFUL</h1>
        <p style={{color:"#374151",marginBottom:24}}>
          React is rendering correctly! This confirms the frontend framework is working.
        </p>
        
        <div className="fb-gap-4">
          <div style={{padding:16,background:"#eff6ff",borderRadius:4,border:"1px solid #bfdbfe"}}>
            <h2 style={{fontWeight:600,color:"#1e40af"}}>Possible Issues:</h2>
            <ul style={{marginTop:8,fontSize:"0.875rem",color:"#1d4ed8"}}>
              <li>• API Authentication Failed (401 Error)</li>
              <li>• Token expired or missing</li>
              <li>• Backend API not running</li>
              <li>• JavaScript runtime error</li>
            </ul>
          </div>
          
          <div style={{padding:16,background:"#fef9c3",borderRadius:4,border:"1px solid #fde68a"}}>
            <h2 style={{fontWeight:600,color:"#854d0e"}}>Next Steps:</h2>
            <ol style={{marginTop:8,fontSize:"0.875rem",color:"#a16207"}}>
              <li>1. Press F12 → Open Browser Developer Tools</li>
              <li>2. Check "Console" tab for JavaScript errors</li>
              <li>3. Check "Network" tab for failed requests</li>
              <li>4. Try direct login page: <code>/login</code></li>
              <li>5. Clear localStorage and refresh</li>
            </ol>
          </div>
          
          <div style={{padding:16,background:"#f0fdf4",borderRadius:4,border:"1px solid #bbf7d0"}}>
            <h2 style={{fontWeight:600,color:"#166534"}}>Quick Test:</h2>
            <p style={{marginTop:8,fontSize:"0.875rem",color:"#15803d"}}>
              If you can see this green page, React is working. The issue is likely:
              <strong> API authentication or data loading.</strong>
            </p>
          </div>
        </div>
        
        <button 
          onClick={() => window.location.href = '/login'}
          className="btn btn-primary" style={{marginTop:24,width:"100%"}}
        >
          Go to Login Page
        </button>
        
        <button 
          onClick={() => {
            localStorage.clear();
            window.location.reload();
          }}
          className="btn btn-default" style={{marginTop:12,width:"100%"}}
        >
          Clear LocalStorage & Refresh
        </button>
      </div>
    </div>
  );
};

export default AppsDashboardTest;