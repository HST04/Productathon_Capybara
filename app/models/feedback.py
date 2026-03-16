"""Feedback model for lead feedback collection."""

from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session
from typing import Optional, List
import uuid
from app.db.session import Base


class Feedback(Base):
    """Feedback on lead quality from sales officers."""
    
    __tablename__ = "feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey('leads.id'), nullable=False)
    feedback_type = Column(String(20), nullable=False)  # 'accepted', 'rejected', 'converted'
    notes = Column(Text, nullable=True)
    submitted_at = Column(TIMESTAMP, server_default=func.now())
    submitted_by = Column(String(100), nullable=True)  # Sales officer ID
    
    # Relationships
    lead = relationship("Lead", backref="feedback")
    
    # CRUD Operations
    
    @classmethod
    def create(
        cls,
        db: Session,
        lead_id: uuid.UUID,
        feedback_type: str,
        notes: Optional[str] = None,
        submitted_by: Optional[str] = None
    ) -> 'Feedback':
        """
        Create a new feedback entry.
        
        Args:
            db: Database session
            lead_id: UUID of the associated lead
            feedback_type: Type of feedback ('accepted', 'rejected', 'converted')
            notes: Optional notes from sales officer
            submitted_by: Sales officer ID/name (optional)
        
        Returns:
            Created Feedback instance
        """
        feedback = cls(
            lead_id=lead_id,
            feedback_type=feedback_type,
            notes=notes,
            submitted_by=submitted_by
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
    
    @classmethod
    def get_by_id(cls, db: Session, feedback_id: uuid.UUID) -> Optional['Feedback']:
        """
        Retrieve feedback by ID.
        
        Args:
            db: Database session
            feedback_id: UUID of the feedback
        
        Returns:
            Feedback instance or None if not found
        """
        return db.query(cls).filter(cls.id == feedback_id).first()
    
    @classmethod
    def get_by_lead_id(cls, db: Session, lead_id: uuid.UUID) -> List['Feedback']:
        """
        Retrieve all feedback for a specific lead.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
        
        Returns:
            List of Feedback instances
        """
        return db.query(cls).filter(cls.lead_id == lead_id).order_by(cls.submitted_at.desc()).all()
    
    @classmethod
    def list_feedback(
        cls,
        db: Session,
        feedback_type: Optional[str] = None,
        submitted_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List['Feedback']:
        """
        List feedback with optional filters.
        
        Args:
            db: Database session
            feedback_type: Filter by feedback type
            submitted_by: Filter by submitter
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            List of Feedback instances
        """
        query = db.query(cls)
        
        if feedback_type:
            query = query.filter(cls.feedback_type == feedback_type)
        if submitted_by:
            query = query.filter(cls.submitted_by == submitted_by)
        
        return query.order_by(cls.submitted_at.desc()).limit(limit).offset(offset).all()
    
    @classmethod
    def count_by_type(
        cls,
        db: Session,
        feedback_type: str,
        submitted_by: Optional[str] = None
    ) -> int:
        """
        Count feedback entries by type.
        
        Args:
            db: Database session
            feedback_type: Type of feedback to count
            submitted_by: Optional filter by submitter
        
        Returns:
            Count of matching feedback entries
        """
        query = db.query(cls).filter(cls.feedback_type == feedback_type)
        
        if submitted_by:
            query = query.filter(cls.submitted_by == submitted_by)
        
        return query.count()
