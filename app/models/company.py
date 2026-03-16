"""Company model for storing normalized company profiles."""

from sqlalchemy import Column, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from app.db.session import Base


class Company(Base):
    """Company Card represents a normalized company profile with metadata."""
    
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    name_variants = Column(ARRAY(Text), nullable=True)  # Alternative spellings
    cin = Column(String(50), nullable=True)
    gst = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    locations = Column(ARRAY(Text), nullable=True)  # Plant/office locations
    key_products = Column(ARRAY(Text), nullable=True)
    embedding_id = Column(String(100), nullable=True)  # Pinecone vector ID
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
