import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LeadList from './components/LeadList';
import LeadDossier from './components/LeadDossier';
import Dashboard from './components/Dashboard';
import SourceRegistry from './components/SourceRegistry';
import Navigation from './components/Navigation';
import { LowBandwidthMode } from './components/LowBandwidthMode';
import './App.css';

const App: React.FC = () => {
  return (
    <LowBandwidthMode>
      <Router>
        <div className="app">
          <Navigation />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Navigate to="/leads" replace />} />
              <Route path="/leads" element={<LeadList />} />
              <Route path="/leads/:leadId" element={<LeadDossier />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/sources" element={<SourceRegistry />} />
            </Routes>
          </main>
        </div>
      </Router>
    </LowBandwidthMode>
  );
};

export default App;
