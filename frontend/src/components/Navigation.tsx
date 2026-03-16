import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { SyncStatusIndicator } from './SyncStatusIndicator';
import './Navigation.css';

const Navigation: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <h1>HPCL Lead Intelligence</h1>
        </div>
        <ul className="nav-links">
          <li>
            <Link 
              to="/leads" 
              className={isActive('/leads') ? 'active' : ''}
            >
              Leads
            </Link>
          </li>
          <li>
            <Link 
              to="/dashboard" 
              className={isActive('/dashboard') ? 'active' : ''}
            >
              Dashboard
            </Link>
          </li>
          <li>
            <Link 
              to="/sources" 
              className={isActive('/sources') ? 'active' : ''}
            >
              Sources
            </Link>
          </li>
        </ul>
        <div className="nav-sync-status">
          <SyncStatusIndicator />
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
