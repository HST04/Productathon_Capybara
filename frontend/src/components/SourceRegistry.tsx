import React, { useState, useEffect } from 'react';
import { sourcesAPI } from '../services/api';
import { Source } from '../types';
import './SourceRegistry.css';

const SourceRegistry: React.FC = () => {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await sourcesAPI.getSources();
      setSources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sources');
    } finally {
      setLoading(false);
    }
  };

  const getTrustTierClass = (tier: string) => {
    return `trust-tier trust-tier-${tier}`;
  };

  const getCategoryBadge = (category: string) => {
    const badges: Record<string, string> = {
      news: '📰',
      tender: '📋',
      company_site: '🏢',
    };
    return badges[category] || '📄';
  };

  const getAccessMethodBadge = (method: string) => {
    const badges: Record<string, string> = {
      rss: 'RSS',
      api: 'API',
      scrape: 'Scrape',
    };
    return badges[method] || method;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="container">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="error-message">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="container source-registry-container">
      <div className="source-registry-header">
        <h2>Source Registry</h2>
        <p className="source-registry-description">
          Monitor and manage data sources with dynamic trust scoring based on lead quality feedback.
        </p>
      </div>

      {sources.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📡</div>
          <h3>No sources configured</h3>
          <p>Sources will appear here as the system discovers new data sources.</p>
        </div>
      ) : (
        <div className="sources-grid">
          {sources.map((source) => (
            <div key={source.id} className="source-card">
              <div className="source-card-header">
                <div className="source-category">
                  <span className="category-icon">{getCategoryBadge(source.category)}</span>
                  <span className="category-label">{source.category.replace('_', ' ')}</span>
                </div>
                <span className={getTrustTierClass(source.trust_tier)}>
                  {source.trust_tier.toUpperCase()}
                </span>
              </div>

              <div className="source-domain">
                <a href={`https://${source.domain}`} target="_blank" rel="noopener noreferrer">
                  {source.domain}
                </a>
              </div>

              <div className="source-stats">
                <div className="source-stat">
                  <label>Trust Score</label>
                  <div className="trust-score-display">
                    <div className="trust-score-bar-large">
                      <div 
                        className="trust-score-fill-large" 
                        style={{ width: `${source.trust_score}%` }}
                      />
                    </div>
                    <span className="trust-score-number">{source.trust_score.toFixed(0)}</span>
                  </div>
                </div>

                <div className="source-stat">
                  <label>Access Method</label>
                  <span className="access-method-badge">
                    {getAccessMethodBadge(source.access_method)}
                  </span>
                </div>

                <div className="source-stat">
                  <label>Crawl Frequency</label>
                  <span>{source.crawl_frequency_minutes} min</span>
                </div>

                <div className="source-stat">
                  <label>Last Crawled</label>
                  <span>{formatDate(source.last_crawled_at)}</span>
                </div>

                <div className="source-stat">
                  <label>Robots.txt</label>
                  <span className={source.robots_txt_allowed ? 'status-allowed' : 'status-blocked'}>
                    {source.robots_txt_allowed ? '✓ Allowed' : '✗ Blocked'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SourceRegistry;
