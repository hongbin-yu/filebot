import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import appService, { App, CreateAppRequest } from '../../services/app.service';
import CreateAppModal from '../../components/apps/CreateAppModal';
import EditAppModal from '../../components/apps/EditAppModal';
import { showToast } from '../../components/common/ToastNotification';

const AdminAppsDashboard: React.FC = () => {
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load application data
  useEffect(() => {
    const loadApps = async () => {
      try {
        setLoading(true);
        const appsData = await appService.getApps();
        setApps(appsData);
      } catch (err) {
        console.error('Failed to load applications:', err);
        setError('Unable to load application list. Please check your network connection or log in again.');
      } finally {
        setLoading(false);
      }
    };

    loadApps();
  }, []);

  // Create application modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  // Edit application modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingApp, setEditingApp] = useState<App | null>(null);

  // Handle create application
  const handleCreateApp = () => {
    setIsCreateModalOpen(true);
  };

  // Handle create success
  const handleCreateSuccess = (newApp: App) => {
    // Add new application to list
    setApps(prevApps => [...prevApps, newApp]);
  };

  // Close modal
  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
  };

  // Handle edit success
  const handleEditSuccess = (updatedApp: App) => {
    // Update corresponding application in list
    setApps(prevApps => prevApps.map(app => 
      app.id === updatedApp.id ? updatedApp : app
    ));
  };

  // Close edit modal
  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setEditingApp(null);
  };

  // Handle delete application
  const handleDeleteApp = async (appId: string, appName: string) => {
    const confirmed = await window.wetYesOrNo(`Are you sure you want to delete the application "${appName}"? This action will delete all associated folders and documents and cannot be undone.`);
    if (!confirmed) {
      return;
    }

    try {
      await appService.deleteApp(appId);
      // Remove deleted application from list
      setApps(prevApps => prevApps.filter(app => app.id !== appId));
    } catch (err) {
      console.error('Failed to delete application:', err);
      showToast('Failed to delete application. Please try again later.', 'error');
    }
  };

  // Handle edit application
  const handleEditApp = (appId: string) => {
    const appToEdit = apps.find(app => app.id === appId);
    if (appToEdit) {
      setEditingApp(appToEdit);
      setIsEditModalOpen(true);
    } else {
      showToast('Application to edit not found', 'error');
    }
  };

  if (loading) {
    return (
      <div style={{padding:24}}>
        <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}>
          <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>Application Management</h1>
          <button className="btn btn-primary" onClick={handleCreateApp}>
            + Create Application
          </button>
        </div>
        <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
          <div >
            <div className="fb-spinner" style={{height:48,width:48,borderWidth:2,borderColor:"#2563eb",borderRadius:"50%"}}></div>
            <p  style={{ marginTop:16 }}>Loading applications...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{padding:24}}>
        <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}>
          <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>Application Management</h1>
          <button className="btn btn-primary" onClick={handleCreateApp}>
            + Create Application
          </button>
        </div>
        <div  style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:24}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#991b1b",marginBottom:8}}>Load Failed</h3>
          <p style={{ color:"#b91c1c", marginBottom:16 }}>{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="btn btn-danger"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{padding:24}}>
      <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}>
        <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>Application Management</h1>
        <button className="btn btn-primary" onClick={handleCreateApp}>
          + Create Application
        </button>
      </div>

      {apps.length === 0 ? (
        <div  style={{background:"#fefce8",border:"1px solid #fef08a",borderRadius:8,padding:32}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#854d0e",marginBottom:8}}>No applications yet</h3>
          <p style={{ color:"#a16207", marginBottom:16 }}>You haven't created any applications yet. Click the button above to create your first application.</p>
          <button className="btn btn-warning" onClick={handleCreateApp}>
            Create First Application
          </button>
        </div>
      ) : (
        <div className="panel panel-default">
          <div style={{padding:16,borderBottom:"1px solid #e5e7eb"}}>
            <h2 style={{fontSize:"1.125rem",fontWeight:600}}>All Applications ({apps.length})</h2>
          </div>
          
          <div className="fb-divide-y">
            {apps.map(app => (
              <div key={app.id} className="fb-hover-btn" style={{padding:16}}>
                <div className="fb-d-flex fb-justify-between fb-align-center">
                  <div>
                    <Link 
                      to={`/admin/apps/${app.slug || app.id}`}
                      className="fb-link" style={{fontSize:"1.125rem",fontWeight:500,color:"#2563eb"}}
                    >
                      {app.name}
                    </Link>
                    <p  style={{ marginTop:4 }}>{app.description || 'No description'}</p>
                    <div  style={{ marginTop:8, fontSize:"0.875rem" }}>
                      <span>ID: {app.id}</span>
                      {app.slug && <span style={{marginLeft:16}}>Slug: {app.slug}</span>}
                    </div>
                  </div>
                  <div className="fb-d-flex fb-gap-1">
                    <Link
                      to={`/admin/permissions?resource_type=app&resource_id=${app.id}`}
                      className="fb-badge fb-badge-purple fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}
                    >
                      Permissions
                    </Link>
                    <button 
                      onClick={() => handleEditApp(app.id)}
                      className="fb-badge fb-badge-blue fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}
                    >
                      Edit
                    </button>
                    <button 
                      onClick={() => handleDeleteApp(app.id, app.name)}
                      className="fb-badge fb-badge-red fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{marginTop:32,padding:16,background:"#eff6ff",borderRadius:8}}>
        <h3 style={{ fontWeight:500, color:"#1e40af" }}>New Architecture Information</h3>
        <p style={{ color:"#1d4ed8", marginTop:4 }}>
          FileBot has been simplified to a two-layer structure: Application → Folder → Document. The drawer layer has been removed.
        </p>
        <div style={{ marginTop:8, fontSize:"0.875rem", color:"#2563eb" }}>
          <p>• Admin URL prefix: <code>/admin/apps</code></p>
          <p>• Client URL prefix: <code>/apps</code> (public portal)</p>
          <p>• Data has been cleared, starting from scratch</p>
        </div>
      </div>

      {/* Create Application Modal */}
      <CreateAppModal 
        isOpen={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        onSuccess={handleCreateSuccess}
      />

      {/* Edit Application Modal */}
      <EditAppModal 
        isOpen={isEditModalOpen}
        onClose={handleCloseEditModal}
        onSuccess={handleEditSuccess}
        app={editingApp}
      />
    </div>
  );
};

export default AdminAppsDashboard;