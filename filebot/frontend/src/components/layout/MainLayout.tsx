import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../navigation/Navbar';

/**
 * MainLayout - Admin shell layout
 *
 * Uses Canada.ca WET/Bootstrap 3 grid conventions.
 * For client-facing pages, ClientLayout wraps with WET header/footer.
 */
const MainLayout: React.FC = () => {
  return (
    <div role="main" className="container">
      <Navbar />
      <div className="container-fluid" style={{ paddingTop: 20, paddingBottom: 40, minHeight: 'calc(100vh - 130px)' }}>
        <div className="row">
          <div className="col-xs-12">
            <Outlet />
          </div>
        </div>
      </div>
      <footer style={{ background: '#f5f5f5', borderTop: '1px solid #e0e0e0', padding: '16px 0' }}>
        <div className="container-fluid text-center text-muted">
          <small>FileBot © 2026 — Document Management System</small>
        </div>
      </footer>
    </div>
  );
};

export default MainLayout;
