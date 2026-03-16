"""Feedback Service for handling lead feedback and trust score updates."""

from typing import Optional
import uuid
from sqlalchemy.orm import Session
from app.models.feedback import Feedback
from app.models.lead import Lead
from app.models.event import Event
from app.models.signal import Signal
from app.services.source_registry import SourceRegistryManager


class FeedbackService:
    """Service for managing feedback and updating source trust scores."""
    
    def __init__(self, db: Session):
        self.db = db
        self.source_registry = SourceRegistryManager(db)
    
    def submit_feedback(
        self,
        lead_id: uuid.UUID,
        feedback_type: str,
        notes: Optional[str] = None,
        submitted_by: Optional[str] = None
    ) -> Feedback:
        """
        Submit feedback for a lead and update source trust score.
        
        Args:
            lead_id: UUID of the lead
            feedback_type: Type of feedback ('accepted', 'rejected', 'converted')
            notes: Optional notes from sales officer
            submitted_by: Sales officer ID/name (optional)
        
        Returns:
            Created Feedback instance
        
        Raises:
            ValueError: If lead not found or invalid feedback type
        """
        # Validate feedback type
        valid_types = ['accepted', 'rejected', 'converted']
        if feedback_type not in valid_types:
            raise ValueError(f"Invalid feedback type. Must be one of: {valid_types}")
        
        # Verify lead exists
        lead = Lead.get_by_id(self.db, lead_id)
        if not lead:
            raise ValueError(f"Lead with ID {lead_id} not found")
        
        # Create feedback
        feedback = Feedback.create(
            db=self.db,
            lead_id=lead_id,
            feedback_type=feedback_type,
            notes=notes,
            submitted_by=submitted_by
        )
        
        # Update source trust score
        self._update_source_trust_from_feedback(lead_id, feedback_type)
        
        return feedback
    
    def _update_source_trust_from_feedback(
        self,
        lead_id: uuid.UUID,
        feedback_type: str
    ) -> None:
        """
        Update source trust score based on feedback.
        
        Args:
            lead_id: UUID of the lead
            feedback_type: Type of feedback
        """
        # Get the source ID by traversing: Lead -> Event -> Signal -> Source
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return
        
        event = self.db.query(Event).filter(Event.id == lead.event_id).first()
        if not event:
            return
        
        signal = self.db.query(Signal).filter(Signal.id == event.signal_id).first()
        if not signal or not signal.source_id:
            return
        
        # Update trust score for the source
        self.source_registry.update_trust_score(
            source_id=str(signal.source_id),
            feedback_type=feedback_type
        )
    
    def get_feedback_for_lead(self, lead_id: uuid.UUID) -> list[Feedback]:
        """
        Get all feedback for a specific lead.
        
        Args:
            lead_id: UUID of the lead
        
        Returns:
            List of Feedback instances
        """
        return Feedback.get_by_lead_id(self.db, lead_id)
    
    def get_feedback_stats(
        self,
        submitted_by: Optional[str] = None
    ) -> dict:
        """
        Get feedback statistics.
        
        Args:
            submitted_by: Optional filter by submitter
        
        Returns:
            Dictionary with feedback counts by type
        """
        accepted = Feedback.count_by_type(
            self.db,
            feedback_type='accepted',
            submitted_by=submitted_by
        )
        rejected = Feedback.count_by_type(
            self.db,
            feedback_type='rejected',
            submitted_by=submitted_by
        )
        converted = Feedback.count_by_type(
            self.db,
            feedback_type='converted',
            submitted_by=submitted_by
        )
        
        total = accepted + rejected + converted
        
        return {
            'accepted': accepted,
            'rejected': rejected,
            'converted': converted,
            'total': total
        }
