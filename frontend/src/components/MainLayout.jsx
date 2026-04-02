import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';
import '../styles/globals.css';

const MainLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState('overview');

  // Derive activeView from location
  useEffect(() => {
    const path = location.pathname;
    if (path === '/') setActiveView('overview');
    else if (path === '/upload') setActiveView('upload');
    else if (path === '/extraction') setActiveView('extraction');
    else if (path === '/ai_extraction') setActiveView('ai_extraction');
    else if (path === '/documents' || path.startsWith('/documents/')) setActiveView('documents');
    else if (path === '/master' || path.startsWith('/master/')) setActiveView('master_data');
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <Sidebar 
        activeView={activeView} 
        setActiveView={setActiveView} 
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        user={user}
        onLogout={handleLogout}
      />
      
      <main className="main-content">
        <Outlet context={{ activeView, setActiveView }} />
      </main>
    </div>
  );
};

export default MainLayout;
