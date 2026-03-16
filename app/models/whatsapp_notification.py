"""WhatsAppNotification model for logging notifications."""

from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base


class WhatsAppNotification(Base):
    """Log of WhatsApp notifications sent to sales officers."""
    
    __tablename__ = "whatsapp_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey('leads.id'), nullable=False)
    officer_id = Column(UUID(as_uuid=True), ForeignKey('sales_officers.id'), nullable=False)
    sent_at = Column(TIMESTAMP, server_default=func.now())
    template_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)  # 'sent', 'delivered', 'failed'
    
    # Relationships
    lead = relationship("Lead", backref="whatsapp_notifications")
    officer = relationship("SalesOfficer", backref="whatsapp_notifications")
