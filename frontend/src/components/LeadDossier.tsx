import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { leadsAPI } from '../services/api';
import { LeadDossier as LeadDossierType } from '../types';
import FeedbackModal from './FeedbackModal';
import './LeadDossier.css';

const LeadDossier: React.FC = () => {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  
  const [dossier, setDossier] = useState<LeadDossierType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    if (leadId) {
      fetchDossier();
    }
  }, [leadId]);

  const fetchDossier = async () => {
    if (!leadId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await leadsAPI.getLeadDossier(leadId);
      setDossier(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch lead details');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedbackSubmit = () => {
    setShowFeedbackModal(false);
    // Refresh dossier to get updated status
    fetchDossier();
  };

  const handleScheduleMeeting = () => {
    // Create a calendar event or open scheduling interface
    const subject = `Meeting: ${dossier?.company.name}`;
    const body = `Discuss business opportunity regarding: ${dossier?.event?.event_summary}`;
    
    // For mobile, try to open native calendar
    if (navigator.userAgent.match(/iPhone|iPad|iPod|Android/i)) {
      // Simple alert for now - in production, integrate with calendar API
      alert('Schedule meeting feature - integrate with device calendar');
    } else {
      // For desktop, create mailto with meeting request
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }
  };

  const handleAddNote = async () => {
    if (!leadId || !noteText.trim()) return;
    
    setSavingNote(true);
    try {
      await leadsAPI.addLeadNotes(leadId, noteText.trim());
      setNoteText('');
      // Refresh dossier to show new note
      await fetchDossier();
    } catch (err) {
      console.error('Failed to add note:', err);
      alert('Failed to add note. Please try again.');
    } finally {
      setSavingNote(false);
    }
  };

  const getPriorityClass = (priority: string) => {
    return `priority-badge-large priority-${priority}`;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'confidence-high';
    if (confidence >= 60) return 'confidence-medium';
    return 'confidence-low';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSuggestedAction = () => {
    if (!dossier) return null;
    
    const { priority, event } = dossier;
    
    if (priority === 'high') {
      if (event.event_type?.toLowerCase().includes('tender')) {
        return 'Immediate action required: Contact company to discuss tender requirements and submit proposal before deadline.';
      }
      return 'High priority opportunity: Schedule meeting with decision makers within 48 hours.';
    }
    
    if (priority === 'medium') {
      return 'Follow up within 1 week: Research company needs and prepare customized product presentation.';
    }
    
    return 'Monitor and qualify: Gather more information about the opportunity before direct outreach.';
  };

  if (loading) {
    return (
      <div className="container">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error || !dossier) {
    return (
      <div className="container">
        <div className="error-message">
          {error || 'Lead not found'}
        </div>
        <button onClick={() => navigate('/leads')} className="btn btn-secondary">
          Back to Leads
        </button>
      </div>
    );
  }

  return (
    <div className="container dossier-container">
      {/* Header */}
      <div className="dossier-header">
        <button onClick={() => navigate('/leads')} className="btn btn-secondary back-btn">
          ← Back to Leads
        </button>
        
        <div className="dossier-title-section">
          <h1>{dossier.company.name}</h1>
          <div className="dossier-meta">
            <span className={getPriorityClass(dossier.priority)}>
              {dossier.priority.toUpperCase()} PRIORITY
            </span>
            <span className="score-badge-large">Score: {dossier.score}</span>
            <span className="status-badge-large status-{dossier.status}">
              {dossier.status}
            </span>
          </div>
        </div>

        <div className="dossier-actions">
          <button 
            onClick={() => setShowFeedbackModal(true)}
            className="btn btn-primary"
          >
            Submit Feedback
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dossier-grid">
        {/* Company Information */}
        <section className="dossier-card company-card">
          <h2 className="card-title">Company Information</h2>
          
          <div className="info-grid">
            <div className="info-item">
              <label>Company Name</label>
              <div className="info-value">{dossier.company.name}</div>
            </div>

            {dossier.company.industry && (
              <div className="info-item">
                <label>Industry</label>
                <div className="info-value">{dossier.company.industry}</div>
              </div>
            )}

            {dossier.company.cin && (
              <div className="info-item">
                <label>CIN</label>
                <div className="info-value">{dossier.company.cin}</div>
              </div>
            )}

            {dossier.company.gst && (
              <div className="info-item">
                <label>GST</label>
                <div className="info-value">{dossier.company.gst}</div>
              </div>
            )}

            {dossier.company.website && (
              <div className="info-item">
                <label>Website</label>
                <div className="info-value">
                  <a href={dossier.company.website} target="_blank" rel="noopener noreferrer">
                    {dossier.company.website}
                  </a>
                </div>
              </div>
            )}

            {dossier.company.address && (
              <div className="info-item full-width">
                <label>Address</label>
                <div className="info-value">{dossier.company.address}</div>
              </div>
            )}

            {dossier.company.locations && dossier.company.locations.length > 0 && (
              <div className="info-item full-width">
                <label>Locations</label>
                <div className="info-value">
                  {dossier.company.locations.map((loc, idx) => (
                    <span key={idx} className="location-tag">
                      📍 {loc}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {dossier.company.key_products && dossier.company.key_products.length > 0 && (
              <div className="info-item full-width">
                <label>Key Products</label>
                <div className="info-value">
                  {dossier.company.key_products.join(', ')}
                </div>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <h3>Quick Actions</h3>
            <div className="action-buttons">
              <a 
                href={`tel:${dossier.company.phone || '+91'}`} 
                className="action-btn action-btn-call"
                aria-label="Call company"
              >
                <span className="action-icon">📞</span>
                <span className="action-label">Call</span>
              </a>
              <a 
                href={`mailto:${dossier.company.email || `info@${dossier.company.website?.replace(/^https?:\/\//, '')}`}`}
                className="action-btn action-btn-email"
                aria-label="Email company"
              >
                <span className="action-icon">✉️</span>
                <span className="action-label">Email</span>
              </a>
              <button 
                className="action-btn action-btn-schedule"
                onClick={() => handleScheduleMeeting()}
                aria-label="Schedule meeting"
              >
                <span className="action-icon">📅</span>
                <span className="action-label">Schedule</span>
              </button>
              <a 
                href={dossier.company.website || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="action-btn action-btn-website"
                aria-label="Visit website"
              >
                <span className="action-icon">🌐</span>
                <span className="action-label">Website</span>
              </a>
            </div>
          </div>
        </section>

        {/* Event Details */}
        <section className="dossier-card event-card">
          <h2 className="card-title">Business Event</h2>
          
          <div className="event-summary">
            {dossier.event.event_summary}
          </div>

          <div className="info-grid">
            {dossier.event.event_type && (
              <div className="info-item">
                <label>Event Type</label>
                <div className="info-value">
                  <span className="event-type-badge">{dossier.event.event_type}</span>
                </div>
              </div>
            )}

            {dossier.event.location && (
              <div className="info-item">
                <label>Location</label>
                <div className="info-value">📍 {dossier.event.location}</div>
              </div>
            )}

            {dossier.event.capacity && (
              <div className="info-item">
                <label>Capacity/Scale</label>
                <div className="info-value">{dossier.event.capacity}</div>
              </div>
            )}

            {dossier.event.deadline && (
              <div className="info-item">
                <label>Deadline</label>
                <div className="info-value deadline">
                  ⏰ {new Date(dossier.event.deadline).toLocaleDateString('en-IN')}
                </div>
              </div>
            )}

            {dossier.event.intent_strength !== undefined && (
              <div className="info-item">
                <label>Intent Strength</label>
                <div className="info-value">
                  <div className="intent-bar">
                    <div 
                      className="intent-fill" 
                      style={{ width: `${dossier.event.intent_strength * 100}%` }}
                    />
                  </div>
                  <span className="intent-label">
                    {Math.round(dossier.event.intent_strength * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Source Links */}
          {dossier.source_links && dossier.source_links.length > 0 && (
            <div className="source-links">
              <h3>Source Links</h3>
              <ul>
                {dossier.source_links.map((link, idx) => (
                  <li key={idx}>
                    <a href={link} target="_blank" rel="noopener noreferrer">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Product Recommendations */}
        <section className="dossier-card products-card">
          <h2 className="card-title">Recommended Products</h2>
          
          {dossier.products && dossier.products.length > 0 ? (
            <div className="products-list">
              {dossier.products
                .sort((a, b) => a.rank - b.rank)
                .map((product) => (
                  <div key={product.id} className="product-item">
                    <div className="product-header">
                      <div className="product-name-section">
                        <span className="product-rank">#{product.rank}</span>
                        <h3 className="product-name">{product.product_name}</h3>
                        {product.uncertainty_flag && (
                          <span className="uncertainty-badge" title="Low confidence - verify with customer">
                            ⚠️ Uncertain
                          </span>
                        )}
                      </div>
                      <div className={`confidence-score ${getConfidenceColor(product.confidence_score * 100)}`}>
                        {Math.round(product.confidence_score * 100)}%
                      </div>
                    </div>
                    
                    <div className="product-reasoning">
                      <label>Reasoning:</label>
                      <p>{product.reasoning}</p>
                    </div>
                    
                    <div className="product-meta">
                      <span className="reason-code-badge">{product.reason_code}</span>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No product recommendations available</p>
            </div>
          )}
        </section>

        {/* Suggested Action */}
        <section className="dossier-card action-card">
          <h2 className="card-title">Suggested Action</h2>
          <div className="suggested-action">
            <div className="action-icon">💡</div>
            <p>{dossier.suggested_action || getSuggestedAction()}</p>
          </div>
        </section>

        {/* Lead Metadata */}
        <section className="dossier-card metadata-card">
          <h2 className="card-title">Lead Details</h2>
          
          <div className="info-grid">
            <div className="info-item">
              <label>Created</label>
              <div className="info-value">{formatDate(dossier.created_at)}</div>
            </div>

            <div className="info-item">
              <label>Last Updated</label>
              <div className="info-value">{formatDate(dossier.updated_at)}</div>
            </div>

            {dossier.assigned_to && (
              <div className="info-item">
                <label>Assigned To</label>
                <div className="info-value">{dossier.assigned_to}</div>
              </div>
            )}

            {dossier.territory && (
              <div className="info-item">
                <label>Territory</label>
                <div className="info-value">{dossier.territory}</div>
              </div>
            )}

            <div className="info-item">
              <label>Lead ID</label>
              <div className="info-value text-small text-muted">{dossier.id}</div>
            </div>
          </div>
        </section>

        {/* Lead Notes */}
        <section className="dossier-card notes-card">
          <h2 className="card-title">Notes</h2>
          
          <div className="notes-input-section">
            <textarea
              className="notes-input"
              placeholder="Add a note about this lead..."
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={3}
            />
            <button
              className="btn btn-primary"
              onClick={handleAddNote}
              disabled={!noteText.trim() || savingNote}
            >
              {savingNote ? 'Saving...' : 'Add Note'}
            </button>
          </div>

          {dossier.notes && dossier.notes.length > 0 && (
            <div className="notes-history">
              <h3>Previous Notes</h3>
              {dossier.notes.map((note) => (
                <div key={note.id} className="note-item">
                  <div className="note-content">{note.content}</div>
                  <div className="note-meta">
                    {note.created_by && <span className="note-author">{note.created_by}</span>}
                    <span className="note-date">{formatDate(note.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Feedback Modal */}
      {showFeedbackModal && (
        <FeedbackModal
          leadId={dossier.id}
          onClose={() => setShowFeedbackModal(false)}
          onSubmit={handleFeedbackSubmit}
        />
      )}
    </div>
  );
};

export default LeadDossier;
