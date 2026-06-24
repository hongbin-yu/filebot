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

const statusBadge = (ok: boolean) =>
  ok ? { bg: '#d8f0d0', color: '#1a5e1a', text: 'Healthy' }
     : { bg: '#f9d0d0', color: '#8b0000', text: 'Issue' };

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    totalFolders: 0,
    recentDocuments: [],
    systemStatus: { api: 'unknown', database: 'unknown', storage: 'unknown' }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const documents = await documentService.searchDocuments({});
      let folders: any[] = [];
      try {
        const apps = await appService.getApps();
        if (apps?.length) {
          folders = await folderService.getFolders(apps[0].slug || apps[0].id, {
            parent_folder_path: `/${apps[0].slug || apps[0].id}`
          });
        }
      } catch { folders = []; }
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
    } catch {
      setStats(prev => ({
        ...prev,
        systemStatus: { api: 'unhealthy', database: 'unhealthy', storage: 'unhealthy' }
      }));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="fb-loading"><p className="text-muted">Loading dashboard...</p></div>;
  }

  const allHealthy = Object.values(stats.systemStatus).every(s => s === 'healthy');

  return (
    <div>
      <h1 style={{ fontSize: '1.8em', marginBottom: 20, color: '#333' }}>Dashboard</h1>

      {/* Stats row */}
      <div className="row">
        <div className="col-md-4">
          <div className="fb-panel">
            <div className="fb-panel-body">
              <div className="fb-d-flex fb-align-center">
                <span style={{ fontSize: '2em', marginRight: 15, color: '#2572b4' }}>📄</span>
                <div>
                  <div className="text-muted" style={{ fontSize: '0.85em' }}>Total Documents</div>
                  <div style={{ fontSize: '1.8em', fontWeight: 'bold', color: '#333' }}>{stats.totalDocuments}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="fb-panel">
            <div className="fb-panel-body">
              <div className="fb-d-flex fb-align-center">
                <span style={{ fontSize: '2em', marginRight: 15, color: '#278400' }}>📁</span>
                <div>
                  <div className="text-muted" style={{ fontSize: '0.85em' }}>Total Folders</div>
                  <div style={{ fontSize: '1.8em', fontWeight: 'bold', color: '#333' }}>{stats.totalFolders}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="fb-panel">
            <div className="fb-panel-body">
              <div className="fb-d-flex fb-align-center">
                <span style={{ fontSize: '2em', marginRight: 15, color: allHealthy ? '#278400' : '#d3080c' }}>
                  {allHealthy ? '✅' : '⚠️'}
                </span>
                <div style={{ color: allHealthy ? '#1a5e1a' : '#8b0000', fontWeight: 'bold' }}>
                  {allHealthy ? 'All systems operational' : 'Some issues detected'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="fb-panel">
        <div className="fb-panel-body">
          <h3 style={{ margin: '0 0 15px 0', fontSize: '1.2em', color: '#333' }}>System Status</h3>
          <div className="row">
            {(['api', 'database', 'storage'] as const).map(service => {
              const ok = stats.systemStatus[service] === 'healthy';
              const b = statusBadge(ok);
              return (
                <div className="col-md-4" key={service}>
                  <div style={{ padding: 12, borderRadius: 3, background: b.bg }}>
                    <div className="fb-d-flex fb-align-center">
                      <span className={`fb-status-dot ${ok ? 'fb-status-dot--ok' : 'fb-status-dot--err'}`} />
                      <strong style={{ textTransform: 'capitalize' }}>{service}</strong>
                    </div>
                    <div style={{ fontSize: '0.85em', marginTop: 4, color: b.color }}>{b.text}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent Documents */}
      <div className="fb-panel">
        <div className="fb-panel-body">
          <div className="fb-d-flex fb-justify-between fb-align-center" style={{ marginBottom: 15 }}>
            <h3 style={{ margin: 0, fontSize: '1.2em', color: '#333' }}>Recent Documents</h3>
            <Link to="/documents" style={{ color: '#2572b4', fontSize: '0.9em' }}>View All →</Link>
          </div>

          {stats.recentDocuments.length > 0 ? (
            <div className="table-responsive">
              <table className="table table-striped table-hover" style={{ marginBottom: 0 }}>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recentDocuments.map((doc: any) => (
                    <tr key={doc.path || doc.id}>
                      <td>
                        <span style={{ fontWeight: 500 }}>{doc.name || 'Unnamed Document'}</span>
                      </td>
                      <td>
                        <span className="label label-primary">{doc.file_type || 'Unknown'}</span>
                      </td>
                      <td className="text-muted">
                        {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'N/A'}
                      </td>
                      <td className="text-muted">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="fb-empty-state">
              <p style={{ fontSize: '2em', marginBottom: 10 }}>📄</p>
              <p>No documents uploaded yet.</p>
              <Link to="/upload" className="btn btn-primary" style={{ marginTop: 10 }}>
                Upload your first document
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
