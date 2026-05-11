import React, { useState, useEffect } from 'react';
import documentService from '../services/document.service';
import folderService from '../services/folder.service';
import appService from '../services/app.service';
import { Link } from 'react-router-dom';
import { Document } from '../services/document.service';

interface DashboardStats {
  totalDocuments: number;
  totalFolders: number;
  recentDocuments: Document[];
  systemStatus: {
    api: string;
    database: string;
    storage: string;
  };
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    totalFolders: 0,
    recentDocuments: [],
    systemStatus: {
      api: 'unknown',
      database: 'unknown',
      storage: 'unknown'
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch documents count
      const documents = await documentService.searchDocuments({});
      
      // Fetch folders using correct nested API path
      let folders: any[] = [];
      try {
        // First, get user's apps to know the app_slug
        const apps = await appService.getApps();
        if (apps && apps.length > 0) {
          const firstApp = apps[0];
          // Now get folders for this app using the app slug
          folders = await folderService.getFolders(firstApp.slug || firstApp.id, { 
            parent_folder_path: `/${firstApp.slug || firstApp.id}`
          });
        }
      } catch (folderError) {
        console.warn('Could not fetch folders, setting to empty:', folderError);
        folders = [];
      }
      
      // Check system status
      const health = await appService.healthCheck();
      
      setStats({
        totalDocuments: documents?.length || 0,
        totalFolders: folders?.length || 0,
        recentDocuments: documents?.slice(0, 5) || [],
        systemStatus: {
          api: health?.status === 'ok' ? 'healthy' : 'unhealthy',
          database: health?.database === 'connected' ? 'healthy' : 'unhealthy',
          storage: health?.storage?.available ? 'healthy' : 'unhealthy'
        }
      });
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setStats(prev => ({
        ...prev,
        systemStatus: {
          api: 'unhealthy',
          database: 'unhealthy',
          storage: 'unhealthy'
        }
      }));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-8">Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div style={{ padding: '0.5rem', backgroundColor: '#f0f9ff', borderRadius: '0.5rem' }}>
              <svg style={{ width: '1.75rem', height: '1.75rem', color: '#2563eb' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-gray-600 mb-1">Total Documents</p>
              <h2 className="text-2xl font-bold text-gray-800">{stats.totalDocuments}</h2>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div style={{ padding: '0.5rem', backgroundColor: '#f0fdf4', borderRadius: '0.5rem' }}>
              <svg style={{ width: '1.75rem', height: '1.75rem', color: '#16a34a' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-gray-600 mb-1">Total Folders</p>
              <h2 className="text-2xl font-bold text-gray-800">{stats.totalFolders}</h2>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div style={{ padding: '0.5rem', backgroundColor: '#f3e8ff', borderRadius: '0.5rem' }}>
              <svg style={{ width: '1.75rem', height: '1.75rem', color: '#9333ea' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: Object.values(stats.systemStatus).every(s => s === 'healthy') ? '#16a34a' : '#ef4444' }}>
                {Object.values(stats.systemStatus).every(s => s === 'healthy') 
                  ? 'All systems operational' 
                  : 'Some issues detected'}
              </h2>
            </div>
          </div>
        </div>
      </div>
      
      {/* System Status */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-4">System Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div style={{ padding: '1rem', borderRadius: '0.25rem', backgroundColor: stats.systemStatus.api === 'healthy' ? '#f0fdf4' : '#fef2f2' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ width: '0.75rem', height: '0.75rem', borderRadius: '9999px', marginRight: '0.75rem', backgroundColor: stats.systemStatus.api === 'healthy' ? '#22c55e' : '#ef4444' }}></div>
              <span style={{ fontWeight: '500' }}>API</span>
            </div>
            <p style={{ fontSize: '0.875rem', marginTop: '0.25rem', color: stats.systemStatus.api === 'healthy' ? '#16a34a' : '#ef4444' }}>
              {stats.systemStatus.api === 'healthy' ? 'Connected and responsive' : 'Connection issues'}
            </p>
          </div>
          
          <div style={{ padding: '1rem', borderRadius: '0.25rem', backgroundColor: stats.systemStatus.database === 'healthy' ? '#f0fdf4' : '#fef2f2' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ width: '0.75rem', height: '0.75rem', borderRadius: '9999px', marginRight: '0.75rem', backgroundColor: stats.systemStatus.database === 'healthy' ? '#22c55e' : '#ef4444' }}></div>
              <span style={{ fontWeight: '500' }}>Database</span>
            </div>
            <p style={{ fontSize: '0.875rem', marginTop: '0.25rem', color: stats.systemStatus.database === 'healthy' ? '#16a34a' : '#ef4444' }}>
              {stats.systemStatus.database === 'healthy' ? 'Connected and healthy' : 'Connection issues'}
            </p>
          </div>
          
          <div style={{ padding: '1rem', borderRadius: '0.25rem', backgroundColor: stats.systemStatus.storage === 'healthy' ? '#f0fdf4' : '#fef2f2' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ width: '0.75rem', height: '0.75rem', borderRadius: '9999px', marginRight: '0.75rem', backgroundColor: stats.systemStatus.storage === 'healthy' ? '#22c55e' : '#ef4444' }}></div>
              <span style={{ fontWeight: '500' }}>Storage</span>
            </div>
            <p style={{ fontSize: '0.875rem', marginTop: '0.25rem', color: stats.systemStatus.storage === 'healthy' ? '#16a34a' : '#ef4444' }}>
              {stats.systemStatus.storage === 'healthy' ? 'Available and writable' : 'Storage issues'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Recent Documents */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">Recent Documents</h2>
          <Link to="/documents" style={{ color: '#2563eb' }}>
            View All →
          </Link>
        </div>
        
        {stats.recentDocuments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Uploaded
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stats.recentDocuments.map((doc: any) => (
                  <tr key={doc.path || doc.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10">
                          <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {doc.name || 'Unnamed Document'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span style={{ paddingLeft: '0.5rem', paddingRight: '0.5rem', display: 'inline-flex', fontSize: '0.75rem', lineHeight: '1.25rem', fontWeight: '600', borderRadius: '9999px', backgroundColor: '#f0f9ff', color: '#1e40af' }}>
                        {doc.file_type || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <svg className="w-10 h-10 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-600">No documents uploaded yet.</p>
            <Link to="/upload" style={{ marginTop: '1rem', display: 'inline-block', backgroundColor: '#2563eb', color: 'white', paddingLeft: '1.5rem', paddingRight: '1.5rem', paddingTop: '0.5rem', paddingBottom: '0.5rem', borderRadius: '0.25rem' }}>
              Upload your first document
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;