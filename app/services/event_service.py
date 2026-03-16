"""Event service for CRUD operations on Event entities."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid
import logging

from app.models.event import Event

logger = logging.getLogger(__name__)


class EventService:
    """Service for managing Event entities with CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_event(
        self,
        signal_id: uuid.UUID,
        event_summary: str,
        company_id: Optional[uuid.UUID] = None,
        event_type: Optional[str] = None,
        location: Optional[str] = None,
        capacity: Optional[str] = None,
        deadline: Optional[datetime] = None,
        intent_strength: Optional[float] = None,
        is_lead_worthy: bool = False
    ) -> Event:
        """
        Create a new Event.
        
        Args:
            signal_id: UUID of the source signal
            event_summary: Summary of the business event
            company_id: Optional UUID of associated company
            event_type: Optional event category (expansion, tender, etc.)
            location: Optional location of the event
            capacity: Optional capacity or scale information
            deadline: Optional deadline date
            intent_strength: Optional intent strength score (0.0 to 1.0)
            is_lead_worthy: Whether this event represents a business opportunity
        
        Returns:
            Created Event object
        """
        event = Event(
            signal_id=signal_id,
            company_id=company_id,
            event_type=event_type,
            event_summary=event_summary,
            location=location,
            capacity=capacity,
            deadline=deadline,
            intent_strength=intent_strength,
            is_lead_worthy=is_lead_worthy
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Created event {event.id} for signal {signal_id}")
        return event
    
    def get_event_by_id(self, event_id: uuid.UUID) -> Optional[Event]:
        """Get event by ID."""
        return self.db.query(Event).filter(Event.id == event_id).first()
    
    def get_events_by_signal(self, signal_id: uuid.UUID) -> List[Event]:
        """Get all events associated with a signal."""
        return self.db.query(Event).filter(Event.signal_id == signal_id).all()
    
    def get_events_by_company(self, company_id: uuid.UUID) -> List[Event]:
        """Get all events associated with a company."""
        return self.db.query(Event).filter(Event.company_id == company_id).all()
    
    def get_lead_worthy_events(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Event]:
        """
        Get all lead-worthy events.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            List of lead-worthy Event objects
        """
        query = self.db.query(Event).filter(Event.is_lead_worthy == True)
        query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update_event(
        self,
        event_id: uuid.UUID,
        **kwargs
    ) -> Optional[Event]:
        """
        Update event fields.
        
        Args:
            event_id: Event ID
            **kwargs: Fields to update
        
        Returns:
            Updated Event object or None if not found
        """
        event = self.get_event_by_id(event_id)
        if not event:
            return None
        
        # Update allowed fields
        allowed_fields = {
            'company_id', 'event_type', 'event_summary', 'location',
            'capacity', 'deadline', 'intent_strength', 'is_lead_worthy'
        }
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(event, key, value)
        
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def delete_event(self, event_id: uuid.UUID) -> bool:
        """
        Delete an event.
        
        Args:
            event_id: Event ID
        
        Returns:
            True if deleted, False if not found
        """
        event = self.get_event_by_id(event_id)
        if event:
            self.db.delete(event)
            self.db.commit()
            return True
        return False
    
    def count_events(
        self,
        lead_worthy_only: bool = False,
        company_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Count events with optional filters.
        
        Args:
            lead_worthy_only: Only count lead-worthy events
            company_id: Filter by company
        
        Returns:
            Count of events
        """
        query = self.db.query(Event)
        
        if lead_worthy_only:
            query = query.filter(Event.is_lead_worthy == True)
        
        if company_id:
            query = query.filter(Event.company_id == company_id)
        
        return query.count()
