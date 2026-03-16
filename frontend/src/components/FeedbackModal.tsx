import React, { useState } from 'react';
import { leadsAPI, APIError } from '../services/api';
import './FeedbackModal.css';

interface FeedbackModalProps {
  leadId: string;
  onClose: () => void;
  onSubmit: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ leadId, onClose, onSubmit }) => {
  const [feedbackType, setFeedbackType] = useState<'accepted' | 'rejected' | 'converted' | null>(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!feedbackType) {
      setError('Please select a feedback type');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await leadsAPI.submitFeedback(leadId, feedbackType, notes || undefined);
      onSubmit();
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to submit feedback. Please try again.');
      }
      setSubmitting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>Submit Feedback</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="modal-description">
              Your feedback helps improve lead quality and source trust scoring.
            </p>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            {/* Feedback Type Selection */}
            <div className="feedback-options">
              <label className="feedback-option-label">Select Feedback Type *</label>
              
              <div className="feedback-buttons">
                <button
                  type="button"
                  className={`feedback-btn feedback-accepted ${feedbackType === 'accepted' ? 'active' : ''}`}
                  onClick={() => setFeedbackType('accepted')}
                >
                  <span className="feedback-icon">✓</span>
                  <div className="feedback-text">
                    <strong>Accepted</strong>
                    <small>Valid lead, will pursue</small>
                  </div>
                </button>

                <button
                  type="button"
                  className={`feedback-btn feedback-converted ${feedbackType === 'converted' ? 'active' : ''}`}
                  onClick={() => setFeedbackType('converted')}
                >
                  <span className="feedback-icon">★</span>
                  <div className="feedback-text">
                    <strong>Converted</strong>
                    <small>Successfully closed deal</small>
                  </div>
                </button>

                <button
                  type="button"
                  className={`feedback-btn feedback-rejected ${feedbackType === 'rejected' ? 'active' : ''}`}
                  onClick={() => setFeedbackType('rejected')}
                >
                  <span className="feedback-icon">✗</span>
                  <div className="feedback-text">
                    <strong>Rejected</strong>
                    <small>Not relevant or inaccurate</small>
                  </div>
                </button>
              </div>
            </div>

            {/* Notes */}
            <div className="form-group">
              <label htmlFor="notes">Additional Notes (Optional)</label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any additional context or comments..."
                rows={4}
                className="form-textarea"
              />
            </div>

            {/* Feedback Impact Info */}
            {feedbackType && (
              <div className={`feedback-impact feedback-impact-${feedbackType}`}>
                <strong>Impact:</strong>
                {feedbackType === 'accepted' && (
                  <span> Source trust score will increase slightly (+1 point)</span>
                )}
                {feedbackType === 'converted' && (
                  <span> Source trust score will increase significantly (+2 points)</span>
                )}
                {feedbackType === 'rejected' && (
                  <span> Source trust score will decrease (-1 point)</span>
                )}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || !feedbackType}
            >
              {submitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FeedbackModal;
