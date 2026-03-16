import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { leadsAPI } from '../services/api';
import { Lead } from '../types';
import './NewLeadsQueue.css';

const NewLeadsQueue: React.FC = () => {
  const navigate = useNavigate();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNewLeads();
  }, []);

  const fetchNewLeads = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await leadsAPI.getLeads(
        { status: 'new' },
        { page: 1, page_size: 50, sort_by: 'created_at', sort_order: 'desc' }
      );
      setLeads(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch new leads');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#f44336';
      case 'medium': return '#ff9800';
      case 'low': return '#4caf50';
      default: return '#757575';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  };

  if (loading) {
    return (
      <div className="new-leads-queue">
        <div className="queue-header">
          <h2>New Leads</h2>
        </div>
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="new-leads-queue">
        <div className="queue-header">
          <h2>New Leads</h2>
        </div>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="new-leads-queue">
        <div className="queue-header">
          <h2>New Leads</h2>
        </div>
        <div className="empty-queue">
          <div className="empty-icon">✓</div>
          <h3>All caught up!</h3>
          <p>No new leads at the moment.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="new-leads-queue">
      <div className="queue-header">
        <h2>New Leads</h2>
        <div className="queue-count">{leads.length} new</div>
      </div>

      <div className="queue-list">
        {leads.map((lead) => (
          <div
            key={lead.id}
            className="queue-item"
            style={{ borderLeftColor: getPriorityColor(lead.priority) }}
            onClick={() => navigate(`/leads/${lead.id}`)}
          >
            <div className="queue-item-header">
              <div className="queue-item-priority" style={{ backgroundColor: getPriorityColor(lead.priority) }}>
                {lead.priority.charAt(0).toUpperCase()}
              </div>
              <div className="queue-item-company">
                <div className="company-name">{lead.company?.name || 'Unknown Company'}</div>
                {lead.company?.industry && (
                  <div className="company-industry">{lead.company.industry}</div>
                )}
              </div>
              <div className="queue-item-time">{formatTimeAgo(lead.created_at)}</div>
            </div>

            <div className="queue-item-event">
              {lead.event?.event_summary?.substring(0, 100) || 'No event details'}
              {lead.event?.event_summary && lead.event.event_summary.length > 100 && '...'}
            </div>

            {lead.event?.location && (
              <div className="queue-item-location">
                📍 {lead.event.location}
              </div>
            )}

            <div className="queue-item-footer">
              <div className="queue-item-score">
                Score: <strong>{lead.score}</strong>
              </div>
              <div className="queue-item-arrow">→</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NewLeadsQueue;
