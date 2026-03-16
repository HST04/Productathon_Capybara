import React, { useState, useEffect } from 'react';
import { dashboardAPI } from '../services/api';
import { DashboardStats } from '../types';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await dashboardAPI.getStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard statistics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="container">
        <div className="error-message">
          {error || 'Failed to load dashboard'}
        </div>
      </div>
    );
  }

  return (
    <div className="container dashboard-container">
      <h2 className="dashboard-title">Dashboard</h2>

      {/* Key Metrics */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-value">{stats.total_leads}</div>
          <div className="metric-label">Total Leads</div>
        </div>

        <div className="metric-card metric-high">
          <div className="metric-value">{stats.high_priority_leads}</div>
          <div className="metric-label">High Priority</div>
        </div>

        <div className="metric-card metric-medium">
          <div className="metric-value">{stats.medium_priority_leads}</div>
          <div className="metric-label">Medium Priority</div>
        </div>

        <div className="metric-card metric-low">
          <div className="metric-value">{stats.low_priority_leads}</div>
          <div className="metric-label">Low Priority</div>
        </div>

        <div className="metric-card metric-conversion">
          <div className="metric-value">{stats.conversion_rate.toFixed(1)}%</div>
          <div className="metric-label">Conversion Rate</div>
        </div>
      </div>

      {/* Top Sources */}
      <section className="dashboard-section">
        <h3>Top Sources by Trust Score</h3>
        <div className="sources-table-container">
          <table className="sources-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Trust Score</th>
                <th>Lead Count</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_sources.map((source, idx) => (
                <tr key={idx}>
                  <td>{source.domain}</td>
                  <td>
                    <div className="trust-score-bar">
                      <div 
                        className="trust-score-fill" 
                        style={{ width: `${source.trust_score}%` }}
                      />
                    </div>
                    <span className="trust-score-value">{source.trust_score.toFixed(0)}</span>
                  </td>
                  <td>{source.lead_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
