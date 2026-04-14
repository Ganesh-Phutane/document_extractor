import React from "react";
import {
  LayoutDashboard,
  Upload,
  Files,
  Sparkles,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Database,
  LayoutGrid,
} from "lucide-react";
import "../styles/components/Sidebar.css";

import { useNavigate, useLocation } from "react-router-dom";

const Sidebar = ({
  isCollapsed,
  setIsCollapsed,
  user,
  onLogout,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard, path: "/" },
    {
      id: "upload_extract",
      label: "Upload & Extract",
      icon: Sparkles,
      path: "/upload-extract",
    },
    {
      id: "master_data",
      label: "Master Data",
      icon: Database,
      path: "/master",
    },
    {
      id: "all_master",
      label: "All Master Data",
      icon: LayoutGrid,
      path: "/master/all",
    },
  ];

  const handleNav = (path) => {
    navigate(path);
  };

  const isActive = (item) => {
    const currentPath = location.pathname;
    if (item.id === 'overview') return currentPath === '/';
    // Match exact or starts with but not /master/all for /master
    if (item.id === 'master_data') return currentPath === '/master' || (currentPath.startsWith('/master/') && !currentPath.startsWith('/master/all'));
    return currentPath.startsWith(item.path);
  };

  return (
    <aside className={`sidebar glass ${isCollapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        {!isCollapsed && (
          <div className="sidebar-logo">
            <Sparkles size={20} color="var(--primary)" />
            <span style={{ fontSize: "15px" }}>DOC EXTRACTOR</span>
          </div>
        )}
        <button
          className="collapse-toggle"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const active = isActive(item);
          return (
            <button
              key={item.id}
              className={`nav-item ${active ? "active" : ""}`}
              onClick={() => handleNav(item.path)}
              title={item.label}
            >
              <item.icon size={20} />
              {!isCollapsed && <span>{item.label}</span>}
              {active && <div className="active-indicator" />}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {!isCollapsed && (
          <div className="user-profile">
            <div className="user-avatar">{user?.email?.[0].toUpperCase()}</div>
            <div className="user-info">
              <span className="user-name">User</span>
              <span className="user-email-small">{user?.email}</span>
            </div>
          </div>
        )}
        <button className="nav-item logout" onClick={onLogout} title="Logout">
          <LogOut size={20} />
          {!isCollapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
