"""Event model for classified business events."""

from sqlalchemy import Column, String, Text, Boolean, Float, Date, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base


class Event(Base):
    """Event represents a classified business opportunity."""
    
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey('signals.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True)
    event_type = Column(String(100), nullable=True)  # 'expansion', 'tender', etc
    event_summary = Column(Text, nullable=False)
    location = Column(String(255), nullable=True)
    capacity = Column(String(100), nullable=True)
    deadline = Column(Date, nullable=True)
    intent_strength = Column(Float, nullable=True)  # 0.0 to 1.0
    is_lead_worthy = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    signal = relationship("Signal", backref="events")
    company = relationship("Company", backref="events")
