import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { leadsAPI } from '../services/api';
import { Lead, LeadFilters, PaginationParams } from '../types';
import './LeadList.css';

const LeadList: React.FC = () => {
  const navigate = useNavigate();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [filters, setFilters] = useState<LeadFilters>({});
  const [searchTerm, setSearchTerm] = useState('');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);
  const pageSize = 20;
  
  // Sorting
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    fetchLeads();
  }, [filters, currentPage, sortBy, sortOrder]);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const pagination: PaginationParams = {
        page: currentPage,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      
      const response = await leadsAPI.getLeads(filters, pagination);
      setLeads(response.items);
      setTotalPages(response.total_pages);
      setTotalLeads(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch leads');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: keyof LeadFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || undefined,
    }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters(prev => ({
      ...prev,
      search: searchTerm || undefined,
    }));
    setCurrentPage(1);
  };

  const handleClearFilters = () => {
    setFilters({});
    setSearchTerm('');
    setCurrentPage(1);
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const getPriorityBadgeClass = (priority: string) => {
    return `priority-badge priority-${priority}`;
  };

  const getStatusBadgeClass = (status: string) => {
    return `status-badge status-${status}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  if (loading && leads.length === 0) {
    return (
      <div className="container">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="container lead-list-container">
      <div className="lead-list-header">
        <h2>Leads</h2>
        <div className="lead-count">
          {totalLeads} {totalLeads === 1 ? 'lead' : 'leads'}
        </div>
      </div>

      {/* Filters Section */}
      <div className="filters-section">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Search by company name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn btn-primary">
            Search
          </button>
        </form>

        <div className="filter-controls">
          <select
            value={filters.priority || ''}
            onChange={(e) => handleFilterChange('priority', e.target.value)}
            className="filter-select"
          >
            <option value="">All Priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={filters.status || ''}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="filter-select"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="converted">Converted</option>
            <option value="rejected">Rejected</option>
          </select>

          {(filters.priority || filters.status || filters.search) && (
            <button onClick={handleClearFilters} className="btn btn-secondary">
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* Leads Table */}
      {leads.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <h3>No leads found</h3>
          <p>Try adjusting your filters or check back later for new leads.</p>
        </div>
      ) : (
        <>
          {/* Desktop Table View */}
          <div className="leads-table-container">
            <table className="leads-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('priority')} className="sortable">
                    Priority {sortBy === 'priority' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('company_id')} className="sortable">
                    Company {sortBy === 'company_id' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th>Event</th>
                  <th onClick={() => handleSort('score')} className="sortable">
                    Score {sortBy === 'score' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('status')} className="sortable">
                    Status {sortBy === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('created_at')} className="sortable">
                    Created {sortBy === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <span className={getPriorityBadgeClass(lead.priority)}>
                        {lead.priority.toUpperCase()}
                      </span>
                    </td>
                    <td className="company-cell">
                      <div className="company-name">
                        {lead.company?.name || 'Unknown Company'}
                      </div>
                      {lead.company?.industry && (
                        <div className="company-industry text-muted text-small">
                          {lead.company.industry}
                        </div>
                      )}
                    </td>
                    <td className="event-cell">
                      <div className="event-summary">
                        {lead.event?.event_summary?.substring(0, 80) || 'No event details'}
                        {lead.event?.event_summary && lead.event.event_summary.length > 80 && '...'}
                      </div>
                      {lead.event?.location && (
                        <div className="event-location text-muted text-small">
                          📍 {lead.event.location}
                        </div>
                      )}
                    </td>
                    <td>
                      <div className="score-badge">{lead.score}</div>
                    </td>
                    <td>
                      <span className={getStatusBadgeClass(lead.status)}>
                        {lead.status}
                      </span>
                    </td>
                    <td className="date-cell">
                      {formatDate(lead.created_at)}
                    </td>
                    <td>
                      <Link to={`/leads/${lead.id}`} className="btn btn-small btn-primary">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          <div className="leads-cards">
            {leads.map((lead) => (
              <div 
                key={lead.id} 
                className={`lead-card priority-${lead.priority}`}
                onClick={() => navigate(`/leads/${lead.id}`)}
              >
                <div className="lead-card-header">
                  <div className="lead-card-company">
                    <div className="lead-card-company-name">
                      {lead.company?.name || 'Unknown Company'}
                    </div>
                    {lead.company?.industry && (
                      <div className="lead-card-industry">
                        {lead.company.industry}
                      </div>
                    )}
                  </div>
                  <div className="lead-card-badges">
                    <span className={getPriorityBadgeClass(lead.priority)}>
                      {lead.priority.toUpperCase()}
                    </span>
                    <span className={getStatusBadgeClass(lead.status)}>
                      {lead.status}
                    </span>
                  </div>
                </div>

                <div className="lead-card-event">
                  <div className="lead-card-event-text">
                    {lead.event?.event_summary?.substring(0, 120) || 'No event details'}
                    {lead.event?.event_summary && lead.event.event_summary.length > 120 && '...'}
                  </div>
                  {lead.event?.location && (
                    <div className="lead-card-location">
                      📍 {lead.event.location}
                    </div>
                  )}
                </div>

                <div className="lead-card-footer">
                  <div className="lead-card-meta">
                    <span className="lead-card-score">Score: {lead.score}</span>
                    <span className="lead-card-date">{formatDate(lead.created_at)}</span>
                  </div>
                  <button 
                    className="btn btn-small btn-primary lead-card-action"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/leads/${lead.id}`);
                    }}
                  >
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn btn-secondary"
              >
                Previous
              </button>
              
              <div className="pagination-info">
                Page {currentPage} of {totalPages}
              </div>
              
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LeadList;
