"""Signal model for storing raw ingested data."""

from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base


class Signal(Base):
    """Signal represents raw data ingested from sources."""
    
    __tablename__ = "signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey('sources.id'), nullable=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    ingested_at = Column(TIMESTAMP, server_default=func.now())
    processed = Column(Boolean, default=False)
    processed_at = Column(TIMESTAMP, nullable=True)
    provenance = Column(JSONB, nullable=True)  # {method, timestamp, rate_limit_respected, etc}
    
    # Relationships
    source = relationship("Source", backref="signals")
