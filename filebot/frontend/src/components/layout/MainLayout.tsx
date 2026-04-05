import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../navigation/Navbar';

const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Outlet />
      </main>
      <footer className="bg-gray-800 text-white py-4 mt-8">
        <div className="container mx-auto px-4 text-center">
          <p>FileBot © 2026 - Document Management System</p>
        </div>
      </footer>
    </div>
  );
};

export default MainLayout;