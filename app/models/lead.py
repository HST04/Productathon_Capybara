"""Lead model for storing scored and prioritized business opportunities."""

from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session
from typing import Optional, List
import uuid
from app.db.session import Base


class Lead(Base):
    """Lead represents a scored and prioritized business opportunity."""
    
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    score = Column(Integer, nullable=False)  # 0-100
    priority = Column(String(20), nullable=False)  # 'high', 'medium', 'low'
    assigned_to = Column(String(100), nullable=True)  # Sales officer ID/name
    territory = Column(String(100), nullable=True)
    status = Column(String(50), default='new')  # 'new', 'contacted', 'qualified', 'converted', 'rejected'
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    event = relationship("Event", backref="leads")
    company = relationship("Company", backref="leads")
    
    # CRUD Operations
    
    @classmethod
    def create(
        cls,
        db: Session,
        event_id: uuid.UUID,
        company_id: uuid.UUID,
        score: int,
        priority: str,
        assigned_to: Optional[str] = None,
        territory: Optional[str] = None,
        status: str = 'new'
    ) -> 'Lead':
        """
        Create a new lead.
        
        Args:
            db: Database session
            event_id: UUID of the associated event
            company_id: UUID of the associated company
            score: Lead score (0-100)
            priority: Priority level ('high', 'medium', 'low')
            assigned_to: Sales officer ID/name (optional)
            territory: Geographic territory (optional)
            status: Lead status (default: 'new')
        
        Returns:
            Created Lead instance
        """
        lead = cls(
            event_id=event_id,
            company_id=company_id,
            score=score,
            priority=priority,
            assigned_to=assigned_to,
            territory=territory,
            status=status
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead
    
    @classmethod
    def get_by_id(cls, db: Session, lead_id: uuid.UUID) -> Optional['Lead']:
        """
        Retrieve a lead by ID.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
        
        Returns:
            Lead instance or None if not found
        """
        return db.query(cls).filter(cls.id == lead_id).first()
    
    @classmethod
    def get_by_event_id(cls, db: Session, event_id: uuid.UUID) -> Optional['Lead']:
        """
        Retrieve a lead by event ID.
        
        Args:
            db: Database session
            event_id: UUID of the event
        
        Returns:
            Lead instance or None if not found
        """
        return db.query(cls).filter(cls.event_id == event_id).first()
    
    @classmethod
    def list_leads(
        cls,
        db: Session,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        territory: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List['Lead']:
        """
        List leads with optional filters.
        
        Args:
            db: Database session
            priority: Filter by priority ('high', 'medium', 'low')
            status: Filter by status
            assigned_to: Filter by assigned sales officer
            territory: Filter by territory
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            List of Lead instances
        """
        query = db.query(cls)
        
        if priority:
            query = query.filter(cls.priority == priority)
        if status:
            query = query.filter(cls.status == status)
        if assigned_to:
            query = query.filter(cls.assigned_to == assigned_to)
        if territory:
            query = query.filter(cls.territory == territory)
        
        return query.order_by(cls.created_at.desc()).limit(limit).offset(offset).all()
    
    @classmethod
    def update(
        cls,
        db: Session,
        lead_id: uuid.UUID,
        **kwargs
    ) -> Optional['Lead']:
        """
        Update a lead.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
            **kwargs: Fields to update
        
        Returns:
            Updated Lead instance or None if not found
        """
        lead = cls.get_by_id(db, lead_id)
        if not lead:
            return None
        
        for key, value in kwargs.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
        
        db.commit()
        db.refresh(lead)
        return lead
    
    @classmethod
    def delete(cls, db: Session, lead_id: uuid.UUID) -> bool:
        """
        Delete a lead.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
        
        Returns:
            True if deleted, False if not found
        """
        lead = cls.get_by_id(db, lead_id)
        if not lead:
            return False
        
        db.delete(lead)
        db.commit()
        return True
    
    @classmethod
    def count_leads(
        cls,
        db: Session,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> int:
        """
        Count leads with optional filters.
        
        Args:
            db: Database session
            priority: Filter by priority
            status: Filter by status
            assigned_to: Filter by assigned sales officer
        
        Returns:
            Count of matching leads
        """
        query = db.query(cls)
        
        if priority:
            query = query.filter(cls.priority == priority)
        if status:
            query = query.filter(cls.status == status)
        if assigned_to:
            query = query.filter(cls.assigned_to == assigned_to)
        
        return query.count()
